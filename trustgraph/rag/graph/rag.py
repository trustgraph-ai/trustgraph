
"""
Simple RAG service, performs query using graph RAG an LLM.
Input is query, output is response.
"""

from ... schema import GraphRagQuery, GraphRagResponse
from ... log_level import LogLevel
from ... graph_rag import GraphRag
from ... base import ConsumerProducer

default_input_queue = 'graph-rag-query'
default_output_queue = 'graph-rag-response'
default_subscriber = 'graph-rag'
default_graph_hosts = [ 'localhost' ]
default_vector_store = 'http://localhost:19530'

class Processor(ConsumerProducer):

    def __init__(
            self,
            pulsar_host=None,
            input_queue=default_input_queue,
            output_queue=default_output_queue,
            subscriber=default_subscriber,
            log_level=LogLevel.INFO,
            graph_hosts=default_graph_hosts,
            vector_store=default_vector_store,
            entity_limit=50,
            triple_limit=30,
            max_sg_size=3000,
    ):

        super(Processor, self).__init__(
            pulsar_host=pulsar_host,
            log_level=log_level,
            input_queue=input_queue,
            output_queue=output_queue,
            subscriber=subscriber,
            input_schema=GraphRagQuery,
            output_schema=GraphRagResponse,
        )

        self.rag = GraphRag(
            pulsar_host=pulsar_host,
            graph_hosts=graph_hosts,
            vector_store=vector_store,
            verbose=True,
            entity_limit=entity_limit,
            triple_limit=triple_limit,
            max_sg_size=max_sg_size,
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

    Processor.start('graph-rag', __doc__)

    
