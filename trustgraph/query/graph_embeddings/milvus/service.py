
"""
Graph embeddings query service.  Input is vector, output is list of
e
"""

from .... direct.milvus import TripleVectors
from .... schema import GraphEmbeddingsRequest, GraphEmbeddingsResponse, Value
from .... schema import graph_embeddings_request_queue
from .... schema import graph_embeddings_response_queue
from .... base import ConsumerProducer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = graph_embeddings_request_queue
default_output_queue = graph_embeddings_response_queue
default_subscriber = module
default_store_uri = 'http://localhost:19530'

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        store_uri = params.get("store_uri", default_store_uri)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": GraphEmbeddingsRequest,
                "output_schema": GraphEmbeddingsResponse,
                "store_uri": store_uri,
            }
        )

        self.vecstore = TripleVectors(store_uri)

    def handle(self, msg):

        v = msg.value()

        # Sender-produced ID
        id = msg.properties()["id"]

        print(f"Handling input {id}...", flush=True)

        entities = set()

        for vec in v.vectors:

            resp = self.vecstore.search(vec, limit=v.limit)

            for r in resp:
                ent = r["entity"]["entity"]
                entities.add(ent)

        # Convert set to list
        entities = list(entities)

        ents2 = []

        for ent in entities:
            if ent.startswith("http://") or ent.startswith("https://"):
                ents2.append(Value(value=ent, is_uri=True))
            else:
                ents2.append(Value(value=ent, is_uri=False))

        entities = ents2

        print("Send response...", flush=True)
        r = GraphEmbeddingsResponse(entities=entities)
        self.producer.send(r, properties={"id": id})

        print("Done.", flush=True)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '-t', '--store-uri',
            default=default_store_uri,
            help=f'Milvus store URI (default: {default_store_uri})'
        )

def run():

    Processor.start(module, __doc__)

