
"""
Simple RAG service, performs query using graph RAG an LLM.
Input is query, output is response.
"""

import logging

from ... schema import GraphRagQuery, GraphRagResponse, Error
from ... schema import Triples, Metadata
from ... provenance import GRAPH_RETRIEVAL
from . graph_rag import GraphRag
from ... base import FlowProcessor, ConsumerSpec, ProducerSpec
from ... base import PromptClientSpec, EmbeddingsClientSpec
from ... base import GraphEmbeddingsClientSpec, TriplesClientSpec
from ... base import RerankerClientSpec
from ... base import LibrarianSpec

# Module logger
logger = logging.getLogger(__name__)

default_ident = "graph-rag"
default_concurrency = 1

class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id", default_ident)
        concurrency = params.get("concurrency", 1)

        entity_limit = params.get("entity_limit", 50)
        triple_limit = params.get("triple_limit", 30)
        max_subgraph_size = params.get("max_subgraph_size", 150)
        max_path_length = params.get("max_path_length", 2)
        edge_limit = params.get("edge_limit", 25)

        super(Processor, self).__init__(
            **params | {
                "id": id,
                "concurrency": concurrency,
                "entity_limit": entity_limit,
                "triple_limit": triple_limit,
                "max_subgraph_size": max_subgraph_size,
                "max_path_length": max_path_length,
                "edge_limit": edge_limit,
            }
        )

        self.default_entity_limit = entity_limit
        self.default_triple_limit = triple_limit
        self.default_max_subgraph_size = max_subgraph_size
        self.default_max_path_length = max_path_length
        self.default_edge_limit = edge_limit

        # Workspace isolation is enforced by the flow layer (flow.workspace).
        # Per-request caching (see GraphRag) keeps within-request state
        # scoped; no cross-request sharing here.

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = GraphRagQuery,
                handler = self.on_request,
                concurrency = concurrency,
            )
        )

        self.register_specification(
            EmbeddingsClientSpec(
                request_name = "embeddings-request",
                response_name = "embeddings-response",
            )
        )

        self.register_specification(
            GraphEmbeddingsClientSpec(
                request_name = "graph-embeddings-request",
                response_name = "graph-embeddings-response",
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
            RerankerClientSpec(
                request_name = "reranker-request",
                response_name = "reranker-response",
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

            # Sender-produced ID
            id = msg.properties()["id"]

            logger.info(f"Handling input {id}...")

            # Track explainability refs for end_of_session signaling
            explainability_refs_emitted = []

            # Real-time explainability callback - emits triples and IDs as they're generated
            # Triples are stored in the request's collection with a named graph (urn:graph:retrieval)
            async def send_explainability(triples, explain_id):
                # Send triples to explainability queue - stores in same collection with named graph
                await flow("explainability").send(Triples(
                    metadata=Metadata(
                        id=explain_id,
                        collection=v.collection,
                    ),
                    triples=triples,
                ))

                # Send explain data to response queue
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

            # Create new GraphRag instance per request — its label cache
            # is request-scoped, and flow clients must not be shared
            # across requests.
            rag = GraphRag(
                embeddings_client=flow("embeddings-request"),
                graph_embeddings_client=flow("graph-embeddings-request"),
                triples_client=flow("triples-request"),
                prompt_client=flow("prompt-request"),
                reranker_client=flow("reranker-request"),
                verbose=True,
            )

            if v.entity_limit:
                entity_limit = v.entity_limit
            else:
                entity_limit = self.default_entity_limit

            if v.triple_limit:
                triple_limit = v.triple_limit
            else:
                triple_limit = self.default_triple_limit

            if v.max_subgraph_size:
                max_subgraph_size = v.max_subgraph_size
            else:
                max_subgraph_size = self.default_max_subgraph_size

            if v.max_path_length:
                max_path_length = v.max_path_length
            else:
                max_path_length = self.default_max_path_length

            if v.edge_limit:
                edge_limit = v.edge_limit
            else:
                edge_limit = self.default_edge_limit

            async def save_answer(doc_id, answer_text):
                await flow.librarian.save_document(
                    doc_id=doc_id,
                    content=answer_text,
                    title=f"GraphRAG Answer: {v.query[:50]}...",
                    document_type="answer",
                )

            # Check if streaming is requested
            if v.streaming:
                # Define async callback for streaming chunks
                # Receives chunk text and end_of_stream flag from prompt client
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

                # Query with streaming and real-time explain
                response, usage = await rag.query(
                    query = v.query, collection = v.collection,
                    entity_limit = entity_limit, triple_limit = triple_limit,
                    max_subgraph_size = max_subgraph_size,
                    max_path_length = max_path_length,

                    edge_limit = edge_limit,
                    streaming = True,
                    chunk_callback = send_chunk,
                    explain_callback = send_explainability,
                    save_answer_callback = save_answer,
                    parent_uri = v.parent_uri,
                )

            else:
                # Non-streaming path with real-time explain
                response, usage = await rag.query(
                    query = v.query, collection = v.collection,
                    entity_limit = entity_limit, triple_limit = triple_limit,
                    max_subgraph_size = max_subgraph_size,
                    max_path_length = max_path_length,

                    edge_limit = edge_limit,
                    explain_callback = send_explainability,
                    save_answer_callback = save_answer,
                    parent_uri = v.parent_uri,
                )

                # Send single response with answer and token usage
                await flow("response").send(
                    GraphRagResponse(
                        message_type="chunk",
                        response=response,
                        end_of_stream=True,
                        end_of_session=True,
                        in_token=usage.get("in_token"),
                        out_token=usage.get("out_token"),
                        model=usage.get("model"),
                    ),
                    properties={"id": id}
                )
                return

            # Streaming: send final message to close session with token usage
            await flow("response").send(
                GraphRagResponse(
                    message_type="chunk",
                    response="",
                    end_of_session=True,
                    in_token=usage.get("in_token"),
                    out_token=usage.get("out_token"),
                    model=usage.get("model"),
                ),
                properties={"id": id}
            )

            logger.info("Request processing complete")

        except Exception as e:

            logger.error(f"Graph RAG service exception: {e}", exc_info=True)

            logger.debug("Sending error response...")

            # Send error response and close session
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

        parser.add_argument(
            '-c', '--concurrency',
            type=int,
            default=default_concurrency,
            help=f'Concurrent processing threads (default: {default_concurrency})'
        )

        FlowProcessor.add_args(parser)

        parser.add_argument(
            '-e', '--entity-limit',
            type=int,
            default=50,
            help=f'Default entity vector fetch limit (default: 50)'
        )

        parser.add_argument(
            '-t', '--triple-limit',
            type=int,
            default=30,
            help=f'Default triple query limit, per query (default: 30)'
        )

        parser.add_argument(
            '-u', '--max-subgraph-size',
            type=int,
            default=150,
            help=f'Default max subgraph size (default: 150)'
        )

        parser.add_argument(
            '-a', '--max-path-length',
            type=int,
            default=2,
            help=f'Default max path length (default: 2)'
        )

        parser.add_argument(
            '--edge-limit',
            type=int,
            default=25,
            help=f'Max edges selected per hop by cross-encoder (default: 25)'
        )

        # Note: Explainability triples are now stored in the request's collection
        # with the named graph urn:graph:retrieval (no separate collection needed)

def run():

    Processor.launch(default_ident, __doc__)

