
"""
Simple RAG service, performs query using graph RAG an LLM.
Input is query, output is response.
"""

import logging
from ... schema import GraphRagQuery, GraphRagResponse, Error
from . graph_rag import GraphRag
from ... base import FlowProcessor, ConsumerSpec, ProducerSpec
from ... base import PromptClientSpec, EmbeddingsClientSpec
from ... base import GraphEmbeddingsClientSpec, TriplesClientSpec

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

        super(Processor, self).__init__(
            **params | {
                "id": id,
                "concurrency": concurrency,
                "entity_limit": entity_limit,
                "triple_limit": triple_limit,
                "max_subgraph_size": max_subgraph_size,
                "max_path_length": max_path_length,
            }
        )

        self.default_entity_limit = entity_limit
        self.default_triple_limit = triple_limit
        self.default_max_subgraph_size = max_subgraph_size
        self.default_max_path_length = max_path_length

        # CRITICAL SECURITY: NEVER share data between users or collections
        # Each user/collection combination MUST have isolated data access
        # Caching must NEVER allow information leakage across these boundaries

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
            ProducerSpec(
                name = "response",
                schema = GraphRagResponse,
            )
        )

    async def on_request(self, msg, consumer, flow):

        try:

            # CRITICAL SECURITY: Create new GraphRag instance per request
            # This ensures proper isolation between users and collections
            # Flow clients are request-scoped and must not be shared
            rag = GraphRag(
                embeddings_client=flow("embeddings-request"),
                graph_embeddings_client=flow("graph-embeddings-request"),
                triples_client=flow("triples-request"),
                prompt_client=flow("prompt-request"),
                verbose=True,
            )

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]
         
            logger.info(f"Handling input {id}...")

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

            # Check if streaming is requested
            if v.streaming:
                # Define async callback for streaming chunks
                # Receives chunk text and end_of_stream flag from prompt client
                async def send_chunk(chunk, end_of_stream):
                    await flow("response").send(
                        GraphRagResponse(
                            response=chunk,
                            end_of_stream=end_of_stream,
                            error=None
                        ),
                        properties={"id": id}
                    )

                # Query with streaming enabled
                # All chunks (including final one with end_of_stream=True) are sent via callback
                await rag.query(
                    query = v.query, user = v.user, collection = v.collection,
                    entity_limit = entity_limit, triple_limit = triple_limit,
                    max_subgraph_size = max_subgraph_size,
                    max_path_length = max_path_length,
                    streaming = True,
                    chunk_callback = send_chunk,
                )
            else:
                # Non-streaming path (existing behavior)
                response = await rag.query(
                    query = v.query, user = v.user, collection = v.collection,
                    entity_limit = entity_limit, triple_limit = triple_limit,
                    max_subgraph_size = max_subgraph_size,
                    max_path_length = max_path_length,
                )

                await flow("response").send(
                    GraphRagResponse(
                        response = response,
                        end_of_stream = True,
                        error = None
                    ),
                    properties = {"id": id}
                )

            logger.info("Request processing complete")

        except Exception as e:

            logger.error(f"Graph RAG service exception: {e}", exc_info=True)

            logger.debug("Sending error response...")

            # Send error response with end_of_stream flag if streaming was requested
            error_response = GraphRagResponse(
                response = None,
                error = Error(
                    type = "graph-rag-error",
                    message = str(e),
                ),
            )

            # If streaming was requested, indicate stream end
            if v.streaming:
                error_response.end_of_stream = True

            await flow("response").send(
                error_response,
                properties = {"id": id}
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

def run():

    Processor.launch(default_ident, __doc__)

