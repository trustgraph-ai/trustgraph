
"""
Accepts entity/vector pairs and writes them to a Pinecone store.
"""

from pinecone import Pinecone, ServerlessSpec
from pinecone.grpc import PineconeGRPC, GRPCClientConfig

import time
import uuid
import os

from .... base import GraphEmbeddingsStoreService

default_ident = "ge-write"
default_api_key = os.getenv("PINECONE_API_KEY", "not-specified")
default_cloud = "aws"
default_region = "us-east-1"

class Processor(GraphEmbeddingsStoreService):

    def __init__(self, **params):

        self.url = params.get("url", None)
        self.cloud = params.get("cloud", default_cloud)
        self.region = params.get("region", default_region)
        self.api_key = params.get("api_key", default_api_key)

        if self.api_key is None or self.api_key == "not-specified":
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
                "url": self.url,
                "cloud": self.cloud,
                "region": self.region,
                "api_key": self.api_key,
            }
        )

        self.last_index_name = None

    def create_index(self, index_name, dim):

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

    async def store_graph_embeddings(self, message):

        for entity in message.entities:

            if entity.entity.value == "" or entity.entity.value is None:
                continue

            for vec in entity.vectors:

                dim = len(vec)

                index_name = (
                    "t-" + message.metadata.user + "-" + message.metadata.collection + "-" + str(dim)
                )

                if index_name != self.last_index_name:

                    if not self.pinecone.has_index(index_name):

                        try:

                            self.create_index(index_name, dim)

                        except Exception as e:
                            print("Pinecone index creation failed")
                            raise e

                        print(f"Index {index_name} created", flush=True)

                    self.last_index_name = index_name

                index = self.pinecone.Index(index_name)

                # Generate unique ID for each vector
                vector_id = str(uuid.uuid4())

                records = [
                    {
                        "id": vector_id,
                        "values": vec,
                        "metadata": { "entity": entity.entity.value },
                    }
                ]

                index.upsert(
                    vectors = records,
                )

    @staticmethod
    def add_args(parser):

        GraphEmbeddingsStoreService.add_args(parser)

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

    Processor.launch(default_ident, __doc__)

