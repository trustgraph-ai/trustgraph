
"""
Accepts entity/vector pairs and writes them to a Qdrant store.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from qdrant_client.models import Distance, VectorParams

import time
import uuid
import os

from .... schema import ChunkEmbeddings
from .... schema import chunk_embeddings_ingest_queue
from .... log_level import LogLevel
from .... base import Consumer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = chunk_embeddings_ingest_queue
default_subscriber = module
default_api_key = os.getenv("PINECONE_API_KEY", "not-specified")
default_cloud = "aws"
default_region = "us-east-1"

class Processor(Consumer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        subscriber = params.get("subscriber", default_subscriber)

        self.url = params.get("url", None)
        self.cloud = params.get("cloud", default_cloud)
        self.region = params.get("region", default_region)
        self.api_key = params.get("api_key", default_api_key)

        if self.api_key is None:
            raise RuntimeError("Pinecone API key must be specified")

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
                "subscriber": subscriber,
                "input_schema": ChunkEmbeddings,
                "url": self.url,
            }
        )

        self.last_index_name = None

    def handle(self, msg):

        v = msg.value()

        chunk = v.chunk.decode("utf-8")

        if chunk == "": return

        for vec in v.vectors:

            dim = len(vec)
            collection = (
                "d-" + v.metadata.user + "-" + str(dim)
            )

            if index_name != self.last_index_name:

                if not self.pinecone.has_index(index_name):

                    try:

                        self.pinecone.create_index(
                            name = index_name,
                            dimension = dim,
                            metric = "cosine",
                            spec = ServerlessSpec(
                                cloud = self.cloud,
                                region = self.region,
                            )
                        )

                        for i in range(0, 1000):

                            if self.pinecone.describe_index(
                                    index_name
                            ).status["ready"]:
                                break

                            time.sleep(1)

                        if not self.pinecone.describe_index(
                                index_name
                        ).status["ready"]:
                            raise RuntimeError(
                                "Gave up waiting for index creation"
                            )

                    except Exception as e:
                        print("Pinecone index creation failed")
                        raise e

                    print(f"Index {index_name} created", flush=True)

                self.last_index_name = index_name

            index = self.pinecone.Index(index_name)

            records = [
                {
                    "id": id,
                    "values": vec,
                    "metadata": { "doc": chunk },
                }
            ]

            index.upsert(
                vectors = records,
                namespace = v.metadata.collection,
            )

    @staticmethod
    def add_args(parser):

        Consumer.add_args(
            parser, default_input_queue, default_subscriber,
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

        parser.add_argument(
            '--cloud',
            default=default_cloud,
            help=f'Pinecone cloud, (default: {default_cloud}'
        )

        parser.add_argument(
            '--region',
            default=default_region,
            help=f'Pinecone region, (default: {default_region}'
        )

def run():

    Processor.start(module, __doc__)

