
"""
Document embeddings query service.  Input is vector, output is an array
of chunks.  Pinecone implementation.
"""

from pinecone import Pinecone, ServerlessSpec
from pinecone.grpc import PineconeGRPC, GRPCClientConfig

import uuid
import os

from .... schema import DocumentEmbeddingsRequest, DocumentEmbeddingsResponse
from .... schema import Error, Value
from .... schema import document_embeddings_request_queue
from .... schema import document_embeddings_response_queue
from .... base import ConsumerProducer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = document_embeddings_request_queue
default_output_queue = document_embeddings_response_queue
default_subscriber = module
default_api_key = os.getenv("PINECONE_API_KEY", "not-specified")

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)

        self.url = params.get("url", None)
        self.api_key = params.get("api_key", default_api_key)

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
                "input_schema": DocumentEmbeddingsRequest,
                "output_schema": DocumentEmbeddingsResponse,
                "url": self.url,
            }
        )

    def handle(self, msg):

        try:

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            print(f"Handling input {id}...", flush=True)

            chunks = []

            for vec in v.vectors:

                dim = len(vec)

                index_name = (
                    "d-" + v.user + "-" + str(dim)
                )

                index = self.pinecone.Index(index_name)

                results = index.query(
                    namespace=v.collection,
                    vector=vec,
                    top_k=v.limit,
                    include_values=False,
                    include_metadata=True
                )

                search_result = self.client.query_points(
                    collection_name=collection,
                    query=vec,
                    limit=v.limit,
                    with_payload=True,
                ).points

                for r in results.matches:
                    doc = r.metadata["doc"]
                    chunks.add(doc)

            print("Send response...", flush=True)
            r = DocumentEmbeddingsResponse(documents=chunks, error=None)
            self.producer.send(r, properties={"id": id})

            print("Done.", flush=True)

        except Exception as e:

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            r = DocumentEmbeddingsResponse(
                error=Error(
                    type = "llm-error",
                    message = str(e),
                ),
                documents=None,
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
            default=default_api_key,
            help='Pinecone API key. (default from PINECONE_API_KEY)'
        )

        parser.add_argument(
            '-u', '--url',
            help='Pinecone URL.  If unspecified, serverless is used'
        )

def run():

    Processor.start(module, __doc__)

