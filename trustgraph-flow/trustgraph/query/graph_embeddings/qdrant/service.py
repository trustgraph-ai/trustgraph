
"""
Graph embeddings query service.  Input is vector, output is list of
entities
"""

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from qdrant_client.models import Distance, VectorParams
import uuid

from .... schema import GraphEmbeddingsRequest, GraphEmbeddingsResponse
from .... schema import Error, Value
from .... schema import graph_embeddings_request_queue
from .... schema import graph_embeddings_response_queue
from .... base import ConsumerProducer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = graph_embeddings_request_queue
default_output_queue = graph_embeddings_response_queue
default_subscriber = module
default_store_uri = 'http://localhost:6333'

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

        self.client = QdrantClient(url=store_uri)

    def create_value(self, ent):
        if ent.startswith("http://") or ent.startswith("https://"):
            return Value(value=ent, is_uri=True)
        else:
            return Value(value=ent, is_uri=False)
        
    def handle(self, msg):

        try:

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            print(f"Handling input {id}...", flush=True)

            entities = set()

            for vec in v.vectors:

                dim = len(vec)
                collection = (
                    "t_" + v.user + "_" + v.collection + "_" +
                    str(dim)
                )

                search_result = self.client.query_points(
                    collection_name=collection,
                    query=vec,
                    limit=v.limit,
                    with_payload=True,
                ).points

                for r in search_result:
                    ent = r.payload["entity"]
                    entities.add(ent)

            # Convert set to list
            entities = list(entities)

            ents2 = []

            for ent in entities:
                ents2.append(self.create_value(ent))

            entities = ents2

            print("Send response...", flush=True)
            r = GraphEmbeddingsResponse(entities=entities, error=None)
            self.producer.send(r, properties={"id": id})

            print("Done.", flush=True)

        except Exception as e:

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            r = GraphEmbeddingsResponse(
                error=Error(
                    type = "llm-error",
                    message = str(e),
                ),
                entities=None,
            )

            self.producer.send(r, properties={"id": id})

            self.consumer.acknowledge(msg)

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

