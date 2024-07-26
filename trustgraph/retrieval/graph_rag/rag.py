
"""
Simple RAG service, performs query using graph RAG an LLM.
Input is query, output is response.
"""

from ... schema import GraphRagQuery, GraphRagResponse
from ... schema import graph_rag_request_queue, graph_rag_response_queue
from ... log_level import LogLevel
from ... graph_rag import GraphRag
from ... base import ConsumerProducer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = graph_rag_request_queue
default_output_queue = graph_rag_response_queue
default_subscriber = module
default_graph_hosts = 'localhost'
default_vector_store = 'http://localhost:19530'

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        graph_hosts = params.get("graph_hosts", default_graph_hosts)
        vector_store = params.get("vector_store", default_vector_store)
        entity_limit = params.get("entity_limit", 50)
        triple_limit = params.get("triple_limit", 30)
        max_subgraph_size = params.get("max_subgraph_size", 3000)

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
            }
        )

        self.rag = GraphRag(
            pulsar_host=self.pulsar_host,
            graph_hosts=graph_hosts.split(","),
            vector_store=vector_store,
            verbose=True,
            entity_limit=entity_limit,
            triple_limit=triple_limit,
            max_subgraph_size=max_subgraph_size,
            module=module,
        )

    def handle(self, msg):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        print(f"Handling input {id}...", flush=True)

        response = self.rag.query(v.query)

        print("Send response...", flush=True)
        r = GraphRagResponse(response = response)
        self.producer.send(r, properties={"id": id})

        print("Done.", flush=True)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '-g', '--graph-hosts',
            default='cassandra',
            help=f'Graph hosts, comma separated (default: cassandra)'
        )

        parser.add_argument(
            '-v', '--vector-store',
            default='http://milvus:19530',
            help=f'Vector host (default: http://milvus:19530)'
        )

        parser.add_argument(
            '-e', '--entity-limit',
            type=int,
            default=50,
            help=f'Entity vector fetch limit (default: 50)'
        )

        parser.add_argument(
            '-t', '--triple-limit',
            type=int,
            default=30,
            help=f'Triple query limit, per query (default: 30)'
        )

        parser.add_argument(
            '-u', '--max-subgraph-size',
            type=int,
            default=3000,
            help=f'Max subgraph size (default: 3000)'
        )

def run():

    Processor.start(module, __doc__)

