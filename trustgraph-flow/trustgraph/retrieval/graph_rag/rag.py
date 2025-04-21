
"""
Simple RAG service, performs query using graph RAG an LLM.
Input is query, output is response.
"""

from ... schema import GraphRagQuery, GraphRagResponse, Error
from . graph_rag import GraphRag
from ... base import FlowProcessor, ConsumerSpec, ProducerSpec
from ... base import PromptClientSpec, EmbeddingsClientSpec
from ... base import GraphEmbeddingsClientSpec, TriplesClientSpec

default_ident = "graph-rag"

class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id", default_ident)

        entity_limit = params.get("entity_limit", 50)
        triple_limit = params.get("triple_limit", 30)
        max_subgraph_size = params.get("max_subgraph_size", 150)
        max_path_length = params.get("max_path_length", 2)

        super(Processor, self).__init__(
            **params | {
                "id": id,
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

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = GraphRagQuery,
                handler = self.on_request,
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

            self.rag = GraphRag(
                embeddings_client = flow("embeddings-request"),
                graph_embeddings_client = flow("graph-embeddings-request"),
                triples_client = flow("triples-request"),
                prompt_client = flow("prompt-request"),
                verbose=True,
            )

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]
         
            print(f"Handling input {id}...", flush=True)

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

            response = await self.rag.query(
                query = v.query, user = v.user, collection = v.collection,
                entity_limit = entity_limit, triple_limit = triple_limit,
                max_subgraph_size = max_subgraph_size,
                max_path_length = max_path_length,
            )

            await flow("response").send(
                GraphRagResponse(
                    response = response,
                    error = None
                ),
                properties = {"id": id}
            )

            print("Done.", flush=True)

        except Exception as e:

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            await flow("response").send(
                GraphRagResponse(
                    response = None,
                    error = Error(
                        type = "graph-rag-error",
                        message = str(e),
                    ),
                ),
                properties = {"id": id}
            )

            await self.send(r, properties={"id": id})

            self.consumer.acknowledge(msg)

    @staticmethod
    def add_args(parser):

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

