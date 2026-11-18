
import logging

from trustgraph.schema import TraversalStep

from . common import (
    HandlerError, get_param, get_param_list, get_param_int,
    parse_param_json, term_to_str, get_input_artifact,
)

logger = logging.getLogger(__name__)


def _parse_traversal_instructions(params):
    raw = parse_param_json(params, "traversal-instructions", list)
    if not raw:
        return None
    steps = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise HandlerError(
                f"traversal-instructions[{i}] must be an object, "
                f"got {type(item).__name__}"
            )
        steps.append(TraversalStep(
            types=item.get("types", []),
            relationships=item.get("relationships", []),
            graphs=item.get("graphs", []),
        ))
    return steps


class ConceptExtractionHandler:

    async def execute(self, params, input_artifacts, flow):

        query = get_param(params, "query")

        logger.info(f"Concept extraction: {query[:80]}...")

        concept_extraction = flow("concept-extraction-request")

        concepts = await concept_extraction.extract(
            query, timeout=300,
        )

        return "KeywordsArtifact", {
            "keywords": concepts,
            "query": query,
        }


class KnowledgeRetrievalHandler:

    async def execute(self, params, input_artifacts, flow):

        keywords_artifact = get_input_artifact(
            input_artifacts, "KeywordsArtifact",
        )

        if keywords_artifact:
            concepts = keywords_artifact.get("keywords", [])
        else:
            concepts = get_param_list(params, "concepts")

        entities_param = get_param(params, "entities", required=False)
        entities = [
            e.strip() for e in entities_param.split(",")
            if e.strip()
        ] if entities_param else []

        if not concepts and not entities:
            raise HandlerError(
                "knowledge-retrieval requires at least one of: "
                "KeywordsArtifact input, 'concepts' parameter, "
                "or 'entities' parameter"
            )

        collection = get_param(params, "collection", required=False) \
            or "default"
        entity_limit = get_param_int(params, "entity-limit", 50)
        triple_limit = get_param_int(params, "triple-limit", 30)
        max_path_length = get_param_int(params, "max-path-length", 2)
        edge_limit = get_param_int(params, "edge-limit", 25)
        max_reranker_input = get_param_int(
            params, "max-reranker-input", 350,
        )
        languages = get_param_list(params, "languages")
        graph = get_param(params, "graph", required=False) or ""

        logger.info(
            f"Knowledge retrieval: {len(concepts)} concepts, "
            f"{len(entities)} seed entities, "
            f"collection={collection}"
        )

        knowledge_retrieval = flow("knowledge-retrieval-request")

        response = await knowledge_retrieval.retrieve(
            concepts=concepts or None,
            entities=entities or None,
            collection=collection,
            entity_limit=entity_limit,
            triple_limit=triple_limit,
            max_path_length=max_path_length,
            edge_limit=edge_limit,
            max_reranker_input=max_reranker_input,
            languages=languages or None,
            graph=graph,
            timeout=300,
        )

        triples = [
            {
                "s": e.s, "p": e.p, "o": e.o,
                "s_label": e.s_label, "p_label": e.p_label,
                "o_label": e.o_label,
                "score": e.score, "concept": e.concept,
            }
            for e in response.edges
        ]

        return "SubgraphArtifact", {
            "triples": triples,
            "seed_entities": response.seed_entities,
        }


class GraphRagQueryHandler:

    async def execute(self, params, input_artifacts, flow):

        query = get_param(params, "query")

        collection = get_param(params, "collection", required=False) \
            or "default"
        entity_limit = get_param_int(params, "entity-limit", 0)
        triple_limit = get_param_int(params, "triple-limit", 0)
        max_subgraph_size = get_param_int(params, "max-subgraph-size", 0)
        max_path_length = get_param_int(params, "max-path-length", 0)
        edge_score_limit = get_param_int(params, "edge-score-limit", 0)
        edge_limit = get_param_int(params, "edge-limit", 0)
        max_reranker_input = get_param_int(
            params, "max-reranker-input", 0,
        )
        grounding_seeds = get_param_list(params, "grounding-seeds")
        graph_seeds = get_param_list(params, "graph-seeds")
        languages = get_param_list(params, "languages")
        traversal_instructions = _parse_traversal_instructions(params)
        graph = get_param(params, "graph", required=False) or None

        logger.info(
            f"Graph RAG query: {query[:80]}... "
            f"collection={collection}"
        )

        graph_rag = flow("graph-rag-request")

        response = await graph_rag.rag(
            query=query,
            collection=collection,
            entity_limit=entity_limit,
            triple_limit=triple_limit,
            max_subgraph_size=max_subgraph_size,
            max_path_length=max_path_length,
            edge_score_limit=edge_score_limit,
            edge_limit=edge_limit,
            max_reranker_input=max_reranker_input,
            grounding_seeds=grounding_seeds or None,
            graph_seeds=graph_seeds or None,
            languages=languages or None,
            traversal_instructions=traversal_instructions,
            graph=graph,
            timeout=300,
        )

        return "TextBlobArtifact", {
            "text": response,
            "query": query,
        }


class GraphEmbeddingsQueryHandler:

    async def execute(self, params, input_artifacts, flow):

        query = get_param(params, "query")
        limit = get_param_int(params, "limit", 20)
        collection = get_param(params, "collection", required=False) \
            or "default"
        rdf_type = get_param(params, "rdf-type", required=False) or ""
        attributes = parse_param_json(params, "attributes", dict)

        logger.info(
            f"Graph embeddings query: {query[:80]}... "
            f"collection={collection}"
        )

        embeddings = flow("embeddings-request")
        vectors = await embeddings.embed([query], timeout=300)

        if not vectors:
            raise HandlerError("Embeddings service returned no vectors")

        graph_embeddings = flow("graph-embeddings-request")
        entities = await graph_embeddings.query(
            vector=vectors[0],
            limit=limit,
            collection=collection,
            rdf_type=rdf_type,
            attributes=attributes,
            timeout=300,
        )

        results = [
            {
                "entity": term_to_str(e.entity) if e.entity else "",
                "score": e.score,
                "rdf_type": e.rdf_type,
                "attributes": e.attributes,
            }
            for e in entities
        ]

        logger.info(
            f"Graph embeddings query: {len(results)} matches"
        )

        return "EntityListArtifact", {
            "entities": results,
            "query": query,
        }


class EntityTriplesQueryHandler:

    async def execute(self, params, input_artifacts, flow):

        entity_list = get_input_artifact(
            input_artifacts, "EntityListArtifact",
        )

        if entity_list:
            entities = [
                e.get("entity", "")
                for e in entity_list.get("entities", [])
                if e.get("entity")
            ]
        else:
            entity_param = get_param(params, "entity", required=False)
            entities_param = get_param(params, "entities", required=False)
            entities = []
            if entity_param:
                entities.append(entity_param.strip())
            if entities_param:
                entities.extend(
                    e.strip() for e in entities_param.split(",")
                    if e.strip()
                )

        if not entities:
            raise HandlerError(
                "entity-triples-query requires at least one of: "
                "EntityListArtifact input, 'entity' parameter, "
                "or 'entities' parameter"
            )

        limit = get_param_int(params, "limit", 50)
        direction = get_param(
            params, "direction", required=False,
        ) or "both"
        collection = get_param(params, "collection", required=False) \
            or "default"
        g = get_param(params, "graph", required=False) or None

        logger.info(
            f"Entity triples query: {len(entities)} entities, "
            f"limit={limit}, direction={direction}, "
            f"collection={collection}"
        )

        triples_client = flow("triples-request")
        seen = set()
        triples = []

        for entity_uri in entities:
            if direction in ("outbound", "both"):
                results = await triples_client.query(
                    s=entity_uri, limit=limit,
                    collection=collection, g=g,
                    timeout=300,
                )
                for t in results:
                    key = (str(t.s), str(t.p), str(t.o))
                    if key not in seen:
                        seen.add(key)
                        triples.append({
                            "s": str(t.s), "p": str(t.p), "o": str(t.o),
                        })

            if direction in ("inbound", "both"):
                results = await triples_client.query(
                    o=entity_uri, limit=limit,
                    collection=collection, g=g,
                    timeout=300,
                )
                for t in results:
                    key = (str(t.s), str(t.p), str(t.o))
                    if key not in seen:
                        seen.add(key)
                        triples.append({
                            "s": str(t.s), "p": str(t.p), "o": str(t.o),
                        })

        logger.info(
            f"Entity triples query: {len(triples)} unique triples"
        )

        return "SubgraphArtifact", {
            "triples": triples,
            "seed_entities": entities,
        }
