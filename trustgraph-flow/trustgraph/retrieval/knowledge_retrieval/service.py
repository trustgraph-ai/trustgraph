"""
Knowledge retrieval service.  Takes concepts, seed entities, or
explicit graph node URIs and returns a ranked subgraph via embedding
lookup, graph traversal, and cross-encoder reranking.
"""

import logging

from ... schema import (
    KnowledgeRetrievalRequest, KnowledgeRetrievalResponse, RetrievedEdge,
)
from ... base import (
    KnowledgeRetrievalService,
    EmbeddingsClientSpec,
    GraphEmbeddingsClientSpec,
    TriplesClientSpec,
    RerankerClientSpec,
)

from . traversal import TraversalEngine

logger = logging.getLogger(__name__)

default_ident = "knowledge-retrieval"


class Processor(KnowledgeRetrievalService):

    def __init__(self, **params):

        super(Processor, self).__init__(**params)

        self.register_specification(
            EmbeddingsClientSpec(
                request_name="embeddings-request",
                response_name="embeddings-response",
            )
        )

        self.register_specification(
            GraphEmbeddingsClientSpec(
                request_name="graph-embeddings-request",
                response_name="graph-embeddings-response",
            )
        )

        self.register_specification(
            TriplesClientSpec(
                request_name="triples-request",
                response_name="triples-response",
            )
        )

        self.register_specification(
            RerankerClientSpec(
                request_name="reranker-request",
                response_name="reranker-response",
            )
        )

    async def retrieve(self, workspace, request, flow):

        engine = TraversalEngine(
            embeddings_client=flow("embeddings-request"),
            graph_embeddings_client=flow("graph-embeddings-request"),
            triples_client=flow("triples-request"),
            reranker_client=flow("reranker-request"),
            collection=workspace,
            entity_limit=request.entity_limit,
            triple_limit=request.triple_limit,
            max_path_length=request.max_path_length,
            edge_limit=request.edge_limit,
            max_reranker_input=request.max_reranker_input,
            languages=request.languages,
            graph=request.graph,
        )

        # Priority: entities > concepts
        if request.entities:
            logger.info(
                f"Using {len(request.entities)} entities, "
                "skipping embedding lookup"
            )
            seed_entities = list(request.entities)
            concepts = request.concepts or [
                e.rsplit('/', 1)[-1].rsplit('#', 1)[-1]
                for e in request.entities
            ]

        elif request.concepts:
            logger.info(
                f"Finding entities for {len(request.concepts)} concepts"
            )
            concepts = list(request.concepts)
            seed_entities = await engine.find_seed_entities(concepts)

        else:
            return KnowledgeRetrievalResponse(
                edges=[],
                seed_entities=[],
                concepts=[],
            )

        if not seed_entities:
            logger.info("No seed entities found")
            return KnowledgeRetrievalResponse(
                edges=[],
                seed_entities=[],
                concepts=concepts,
            )

        edge_dicts = await engine.hop_and_filter(seed_entities, concepts)

        edge_dicts.sort(key=lambda e: e["score"], reverse=True)
        edge_dicts = edge_dicts[:request.edge_limit]

        edges = [
            RetrievedEdge(
                s=e["s"],
                p=e["p"],
                o=e["o"],
                s_label=e["s_label"],
                p_label=e["p_label"],
                o_label=e["o_label"],
                score=e["score"],
                concept=e["concept"],
            )
            for e in edge_dicts
        ]

        logger.info(
            f"Knowledge retrieval complete: {len(edges)} edges, "
            f"{len(seed_entities)} seeds"
        )

        return KnowledgeRetrievalResponse(
            edges=edges,
            seed_entities=seed_entities,
            concepts=concepts,
        )

    @staticmethod
    def add_args(parser):
        KnowledgeRetrievalService.add_args(parser)


def run():
    Processor.launch(default_ident, __doc__)
