
"""
Graph embeddings query service.  Input is vector, output is list of
entities
"""

from .... direct.milvus_graph_embeddings import EntityVectors
from .... schema import GraphEmbeddingsRequest, GraphEmbeddingsResponse
from .... schema import Error, Value
from .... schema import graph_embeddings_request_queue
from .... schema import graph_embeddings_response_queue
from .... base import ConsumerProducer

module = "ge-query"

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

        self.vecstore = EntityVectors(store_uri)

    def create_value(self, ent):
        if ent.startswith("http://") or ent.startswith("https://"):
            return Value(value=ent, is_uri=True)
        else:
            return Value(value=ent, is_uri=False)
        
    async def handle(self, msg):

        try:

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
                ents2.append(self.create_value(ent))

            entities = ents2

            print("Send response...", flush=True)
            r = GraphEmbeddingsResponse(entities=entities, error=None)
            await self.send(r, properties={"id": id})

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

            await self.send(r, properties={"id": id})

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

    Processor.launch(module, __doc__)

