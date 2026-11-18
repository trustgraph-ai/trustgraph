
"""
Graph RAG service.  Composes concept extraction, knowledge retrieval,
document tracing, and LLM synthesis into a full retrieval-augmented
generation pipeline.
"""

import logging

from ... schema import GraphRagQuery, GraphRagResponse, Error, Source
from ... schema import Triples, Metadata
from ... provenance import GRAPH_RETRIEVAL
from . graph_rag import GraphRag
from ... base import FlowProcessor, ConsumerSpec, ProducerSpec
from ... base import ConceptExtractionClientSpec
from ... base import KnowledgeRetrievalClientSpec
from ... base import TriplesClientSpec
from ... base import PromptClientSpec
from ... base import LibrarianSpec

# Module logger
logger = logging.getLogger(__name__)

default_ident = "graph-rag"
default_concurrency = 1

def source_refs(sources):
    return [Source(uri=s["uri"], title=s["title"]) for s in sources]

class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id", default_ident)
        concurrency = params.get("concurrency", 1)

        entity_limit = params.get("entity_limit", 50)
        triple_limit = params.get("triple_limit", 30)
        max_path_length = params.get("max_path_length", 2)
        edge_limit = params.get("edge_limit", 25)
        max_reranker_input = params.get("max_reranker_input", 350)

        super(Processor, self).__init__(
            **params | {
                "id": id,
                "concurrency": concurrency,
                "entity_limit": entity_limit,
                "triple_limit": triple_limit,
                "max_path_length": max_path_length,
                "edge_limit": edge_limit,
                "max_reranker_input": max_reranker_input,
            }
        )

        self.default_entity_limit = entity_limit
        self.default_triple_limit = triple_limit
        self.default_max_path_length = max_path_length
        self.default_edge_limit = edge_limit
        self.default_max_reranker_input = max_reranker_input

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = GraphRagQuery,
                handler = self.on_request,
                concurrency = concurrency,
            )
        )

        self.register_specification(
            ConceptExtractionClientSpec(
                request_name = "concept-extraction-request",
                response_name = "concept-extraction-response",
            )
        )

        self.register_specification(
            KnowledgeRetrievalClientSpec(
                request_name = "knowledge-retrieval-request",
                response_name = "knowledge-retrieval-response",
            )
        )

        self.register_specification(
            TriplesClientSpec(
                request_name = "triples-request",
                response_name = "triples-response",
            )
        )

        self.register_specification(
            PromptClientSpec(
                request_name = "prompt-request",
                response_name = "prompt-response",
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = GraphRagResponse,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "explainability",
                schema = Triples,
            )
        )

        self.register_specification(
            LibrarianSpec()
        )

        logger.info("Graph RAG service initialized")

    async def on_request(self, msg, consumer, flow):

        try:

            v = msg.value()

            id = msg.properties()["id"]

            logger.info(f"Handling input {id}...")

            explainability_refs_emitted = []

            async def send_explainability(triples, explain_id):
                await flow("explainability").send(Triples(
                    metadata=Metadata(
                        id=explain_id,
                        collection=v.collection,
                    ),
                    triples=triples,
                ))

                await flow("response").send(
                    GraphRagResponse(
                        message_type="explain",
                        explain_id=explain_id,
                        explain_graph=GRAPH_RETRIEVAL,
                        explain_triples=triples,
                    ),
                    properties={"id": id}
                )

                explainability_refs_emitted.append(explain_id)

            rag = GraphRag(
                concept_extraction_client=flow(
                    "concept-extraction-request",
                ),
                knowledge_retrieval_client=flow(
                    "knowledge-retrieval-request",
                ),
                triples_client=flow("triples-request"),
                prompt_client=flow("prompt-request"),
                verbose=True,
            )

            entity_limit = (
                v.entity_limit or self.default_entity_limit
            )
            triple_limit = (
                v.triple_limit or self.default_triple_limit
            )
            max_path_length = (
                v.max_path_length or self.default_max_path_length
            )
            edge_limit = (
                v.edge_limit or self.default_edge_limit
            )
            max_reranker_input = (
                v.max_reranker_input or self.default_max_reranker_input
            )

            grounding_seeds = v.grounding_seeds or []
            graph_seeds = v.graph_seeds or []
            languages = v.languages or []
            graph = v.graph

            if grounding_seeds and graph_seeds:
                raise ValueError(
                    "grounding_seeds and graph_seeds are mutually "
                    "exclusive"
                )

            async def save_answer(doc_id, answer_text):
                await flow.librarian.save_document(
                    doc_id=doc_id,
                    content=answer_text,
                    title=f"GraphRAG Answer: {v.query[:50]}...",
                    document_type="answer",
                )

            if v.streaming:
                async def send_chunk(chunk, end_of_stream):
                    await flow("response").send(
                        GraphRagResponse(
                            message_type="chunk",
                            response=chunk,
                            end_of_stream=end_of_stream,
                            error=None
                        ),
                        properties={"id": id}
                    )

                response, usage, sources = await rag.query(
                    query=v.query, collection=v.collection,
                    entity_limit=entity_limit,
                    triple_limit=triple_limit,
                    max_path_length=max_path_length,
                    edge_limit=edge_limit,
                    max_reranker_input=max_reranker_input,
                    streaming=True,
                    chunk_callback=send_chunk,
                    explain_callback=send_explainability,
                    save_answer_callback=save_answer,
                    parent_uri=v.parent_uri,
                    user_context=v.user_context,
                    grounding_seeds=grounding_seeds,
                    graph_seeds=graph_seeds,
                    languages=languages,
                    graph=graph,
                )

            else:
                response, usage, sources = await rag.query(
                    query=v.query, collection=v.collection,
                    entity_limit=entity_limit,
                    triple_limit=triple_limit,
                    max_path_length=max_path_length,
                    edge_limit=edge_limit,
                    max_reranker_input=max_reranker_input,
                    explain_callback=send_explainability,
                    save_answer_callback=save_answer,
                    parent_uri=v.parent_uri,
                    user_context=v.user_context,
                    grounding_seeds=grounding_seeds,
                    graph_seeds=graph_seeds,
                    languages=languages,
                    graph=graph,
                )

                await flow("response").send(
                    GraphRagResponse(
                        message_type="chunk",
                        response=response,
                        end_of_stream=True,
                        end_of_session=True,
                        in_token=usage.get("in_token"),
                        out_token=usage.get("out_token"),
                        model=usage.get("model"),
                        sources=source_refs(sources),
                    ),
                    properties={"id": id}
                )
                return

            await flow("response").send(
                GraphRagResponse(
                    message_type="chunk",
                    response="",
                    end_of_session=True,
                    in_token=usage.get("in_token"),
                    out_token=usage.get("out_token"),
                    model=usage.get("model"),
                    sources=source_refs(sources),
                ),
                properties={"id": id}
            )

            logger.info("Request processing complete")

        except Exception as e:

            logger.error(
                f"Graph RAG service exception: {e}", exc_info=True,
            )

            logger.debug("Sending error response...")

            await flow("response").send(
                GraphRagResponse(
                    message_type="chunk",
                    error=Error(
                        type="graph-rag-error",
                        message=str(e),
                    ),
                    end_of_stream=True,
                    end_of_session=True,
                ),
                properties={"id": id}
            )

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

        parser.add_argument(
            '-e', '--entity-limit',
            type=int,
            default=50,
            help='Default entity vector fetch limit (default: 50)'
        )

        parser.add_argument(
            '-t', '--triple-limit',
            type=int,
            default=30,
            help='Default triple query limit, per query (default: 30)'
        )

        parser.add_argument(
            '-a', '--max-path-length',
            type=int,
            default=2,
            help='Default max path length (default: 2)'
        )

        parser.add_argument(
            '--edge-limit',
            type=int,
            default=25,
            help='Max edges selected per hop (default: 25)'
        )

        parser.add_argument(
            '--max-reranker-input',
            type=int,
            default=350,
            help='Max candidate edges sent to reranker (default: 350)'
        )

def run():

    Processor.launch(default_ident, __doc__)
