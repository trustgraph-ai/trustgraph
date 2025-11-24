
"""
Document embeddings query service.  Input is vector, output is an array
of chunks.  Pinecone implementation.
"""

import logging
import uuid
import os

from pinecone import Pinecone, ServerlessSpec
from pinecone.grpc import PineconeGRPC, GRPCClientConfig

from .... base import DocumentEmbeddingsQueryService

# Module logger
logger = logging.getLogger(__name__)

default_ident = "de-query"
default_api_key = os.getenv("PINECONE_API_KEY", "not-specified")

class Processor(DocumentEmbeddingsQueryService):

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

    async def query_document_embeddings(self, msg):

        try:

            # Handle zero limit case
            if msg.limit <= 0:
                return []

            chunks = []

            for vec in msg.vectors:

                dim = len(vec)

                # Use dimension suffix in index name
                index_name = f"d-{msg.user}-{msg.collection}-{dim}"

                # Check if index exists - skip if not
                if not self.pinecone.has_index(index_name):
                    logger.info(f"Index {index_name} does not exist, skipping this vector")
                    continue

                index = self.pinecone.Index(index_name)

                results = index.query(
                    vector=vec,
                    top_k=msg.limit,
                    include_values=False,
                    include_metadata=True
                )

                for r in results.matches:
                    doc = r.metadata["doc"]
                    chunks.append(doc)

            return chunks

        except Exception as e:

            logger.error(f"Exception querying document embeddings: {e}", exc_info=True)
            raise e

    @staticmethod
    def add_args(parser):

        DocumentEmbeddingsQueryService.add_args(parser)

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

