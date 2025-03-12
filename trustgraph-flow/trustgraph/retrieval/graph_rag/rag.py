
"""
Simple RAG service, performs query using graph RAG an LLM.
Input is query, output is response.
"""

from ... schema import GraphRagQuery, GraphRagResponse, Error
from ... schema import graph_rag_request_queue, graph_rag_response_queue
from ... schema import prompt_request_queue
from ... schema import prompt_response_queue
from ... schema import embeddings_request_queue
from ... schema import embeddings_response_queue
from ... schema import graph_embeddings_request_queue
from ... schema import graph_embeddings_response_queue
from ... schema import triples_request_queue
from ... schema import triples_response_queue
from ... log_level import LogLevel
from ... graph_rag import GraphRag
from ... base import ConsumerProducer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = graph_rag_request_queue
default_output_queue = graph_rag_response_queue
default_subscriber = module

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)

        pr_request_queue = params.get(
            "prompt_request_queue", prompt_request_queue
        )
        pr_response_queue = params.get(
            "prompt_response_queue", prompt_response_queue
        )
        emb_request_queue = params.get(
            "embeddings_request_queue", embeddings_request_queue
        )
        emb_response_queue = params.get(
            "embeddings_response_queue", embeddings_response_queue
        )
        ge_request_queue = params.get(
            "graph_embeddings_request_queue", graph_embeddings_request_queue
        )
        ge_response_queue = params.get(
            "graph_embeddings_response_queue", graph_embeddings_response_queue
        )
        tpl_request_queue = params.get(
            "triples_request_queue", triples_request_queue
        )
        tpl_response_queue = params.get(
            "triples_response_queue", triples_response_queue
        )

        entity_limit = params.get("entity_limit", 50)
        triple_limit = params.get("triple_limit", 30)
        max_subgraph_size = params.get("max_subgraph_size", 1000)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": GraphRagQuery,
                "output_schema": GraphRagResponse,
                "entity_limit": entity_limit,
                "triple_limit": triple_limit,
                "max_subgraph_size": max_subgraph_size,
                "prompt_request_queue": pr_request_queue,
                "prompt_response_queue": pr_response_queue,
                "embeddings_request_queue": emb_request_queue,
                "embeddings_response_queue": emb_response_queue,
                "graph_embeddings_request_queue": ge_request_queue,
                "graph_embeddings_response_queue": ge_response_queue,
                "triples_request_queue": triples_request_queue,
                "triples_response_queue": triples_response_queue,
            }
        )

        self.rag = GraphRag(
            pulsar_host=self.pulsar_host,
            pulsar_api_key=self.pulsar_api_key,
            pr_request_queue=pr_request_queue,
            pr_response_queue=pr_response_queue,
            emb_request_queue=emb_request_queue,
            emb_response_queue=emb_response_queue,
            ge_request_queue=ge_request_queue,
            ge_response_queue=ge_response_queue,
            tpl_request_queue=triples_request_queue,
            tpl_response_queue=triples_response_queue,
            verbose=True,
            module=module,
        )

        self.default_entity_limit = entity_limit
        self.default_triple_limit = triple_limit
        self.default_max_subgraph_size = max_subgraph_size

    async def handle(self, msg):

        try:

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]
         
            print(f"Handling input {id}...", flush=True)

            if v.entity_limit:
                entity_limit = v.entity_limit
            else:
                entity_limit = self.entity_limit

            if v.triple_limit:
                triple_limit = v.triple_limit
            else:
                triple_limit = self.triple_limit

            if v.max_subgraph_size:
                max_subgraph_size = v.max_subgraph_size
            else:
                max_subgraph_size = self.max_subgraph_size

            response = self.rag.query(
                query=v.query, user=v.user, collection=v.collection,
                entity_limit=entity_limit, triple_limit=triple_limit,
                max_subgraph_size=max_subgraph_size
            )

            print("Send response...", flush=True)
            r = GraphRagResponse(response=response, error=None)
            await self.send(r, properties={"id": id})

            print("Done.", flush=True)

        except Exception as e:

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            r = GraphRagResponse(
                error=Error(
                    type = "llm-error",
                    message = str(e),
                ),
                response=None,
            )

            await self.send(r, properties={"id": id})

            self.consumer.acknowledge(msg)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

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
            default=1000,
            help=f'Default max subgraph size (default: 1000)'
        )

        parser.add_argument(
            '--prompt-request-queue',
            default=prompt_request_queue,
            help=f'Prompt request queue (default: {prompt_request_queue})',
        )

        parser.add_argument(
            '--prompt-response-queue',
            default=prompt_response_queue,
            help=f'Prompt response queue (default: {prompt_response_queue})',
        )

        parser.add_argument(
            '--embeddings-request-queue',
            default=embeddings_request_queue,
            help=f'Embeddings request queue (default: {embeddings_request_queue})',
        )

        parser.add_argument(
            '--embeddings-response-queue',
            default=embeddings_response_queue,
            help=f'Embeddings response queue (default: {embeddings_response_queue})',
        )

        parser.add_argument(
            '--graph-embeddings-request-queue',
            default=graph_embeddings_request_queue,
            help=f'Graph embeddings request queue (default: {graph_embeddings_request_queue})',
        )

        parser.add_argument(
            '--graph-embeddings-response-queue',
            default=graph_embeddings_response_queue,
            help=f'Graph embeddings response queue (default: {graph_embeddings_response_queue})',
        )

        parser.add_argument(
            '--triples-request-queue',
            default=triples_request_queue,
            help=f'Triples request queue (default: {triples_request_queue})',
        )

        parser.add_argument(
            '--triples-response-queue',
            default=triples_response_queue,
            help=f'Triples response queue (default: {triples_response_queue})',
        )

def run():

    Processor.launch(module, __doc__)

