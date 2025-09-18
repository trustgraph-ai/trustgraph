
"""
Graph embeddings query service.  Input is vector, output is list of
entities.  Pinecone implementation.
"""

import logging
import uuid
import os

from pinecone import Pinecone, ServerlessSpec
from pinecone.grpc import PineconeGRPC, GRPCClientConfig

from .... schema import GraphEmbeddingsResponse
from .... schema import Error, Value
from .... base import GraphEmbeddingsQueryService

# Module logger
logger = logging.getLogger(__name__)

default_ident = "ge-query"
default_api_key = os.getenv("PINECONE_API_KEY", "not-specified")

class Processor(GraphEmbeddingsQueryService):

    def __init__(self, **params):

        self.url = params.get("url", None)
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
                "api_key": self.api_key,
            }
        )

        self.last_index_name = None

    def ensure_index_exists(self, index_name, dim):
        """Ensure index exists, create if it doesn't"""
        if index_name != self.last_index_name:
            if not self.pinecone.has_index(index_name):
                try:
                    self.pinecone.create_index(
                        name=index_name,
                        dimension=dim,
                        metric="cosine",
                        spec=ServerlessSpec(
                            cloud="aws",
                            region="us-east-1",
                        )
                    )
                    logger.info(f"Created index: {index_name}")
                    
                    # Wait for index to be ready
                    import time
                    for i in range(0, 1000):
                        if self.pinecone.describe_index(index_name).status["ready"]:
                            break
                        time.sleep(1)
                        
                    if not self.pinecone.describe_index(index_name).status["ready"]:
                        raise RuntimeError("Gave up waiting for index creation")
                        
                except Exception as e:
                    logger.error(f"Pinecone index creation failed: {e}")
                    raise e
            self.last_index_name = index_name

    def create_value(self, ent):
        if ent.startswith("http://") or ent.startswith("https://"):
            return Value(value=ent, is_uri=True)
        else:
            return Value(value=ent, is_uri=False)
        
    async def query_graph_embeddings(self, msg):

        try:

            # Handle zero limit case
            if msg.limit <= 0:
                return []

            entity_set = set()
            entities = []

            for vec in msg.vectors:

                dim = len(vec)

                index_name = (
                    "t-" + msg.user + "-" + msg.collection
                )

                self.ensure_index_exists(index_name, dim)

                index = self.pinecone.Index(index_name)

                # Heuristic hack, get (2*limit), so that we have more chance
                # of getting (limit) entities
                results = index.query(
                    vector=vec,
                    top_k=msg.limit * 2,
                    include_values=False,
                    include_metadata=True
                )

                for r in results.matches:

                    ent = r.metadata["entity"]

                    # De-dupe entities
                    if ent not in entity_set:
                        entity_set.add(ent)
                        entities.append(ent)

                    # Keep adding entities until limit
                    if len(entity_set) >= msg.limit: break

                # Keep adding entities until limit
                if len(entity_set) >= msg.limit: break

            ents2 = []

            for ent in entities:
                ents2.append(self.create_value(ent))

            entities = ents2

            return entities

        except Exception as e:

            logger.error(f"Exception querying graph embeddings: {e}", exc_info=True)
            raise e

    @staticmethod
    def add_args(parser):

        GraphEmbeddingsQueryService.add_args(parser)

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

    Processor.launch(default_ident, __doc__)

