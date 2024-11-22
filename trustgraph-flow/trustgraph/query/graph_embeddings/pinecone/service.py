
"""
Graph embeddings query service.  Input is vector, output is list of
entities.  Pinecone implementation.
"""

from pinecone import Pinecone, ServerlessSpec
from pinecone.grpc import PineconeGRPC, GRPCClientConfig
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

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)

        self.url = params.get("url", None)
        self.api_key = params.get("api_key", None)

        if self.url:

            self.pinecone = PineconeGRPC(
                api_key = self.api_key,
                host = self.url
            )

        else:

            self.pinecone = Pinecone(api_key = self.api_key)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": GraphEmbeddingsRequest,
                "output_schema": GraphEmbeddingsResponse,
                "url": self.url,
            }
        )

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

                index_name = (
                    "t-" + v.user + "-" + str(dim)
                )

                index = self.pinecone.Index(index_name)

                results = index.query(
                    namespace=v.collection,
                    vector=vec,
                    top_k=v.limit,
                    include_values=False,
                    include_metadata=True
                )

                for r in results.matches:
                    ent = r.metadata["entity"]
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
            '-a', '--api-key',
            required=True,
            help=f'Pinecone API key.'
        )

        parser.add_argument(
            '-u', '--url',
            help=f'Pinecone URL.  If unspecified, serverless is used'
        )

def run():

    Processor.start(module, __doc__)

