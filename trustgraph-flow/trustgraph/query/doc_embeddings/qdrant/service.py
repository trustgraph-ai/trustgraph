
"""
Document embeddings query service.  Input is vector, output is an array
of chunks
"""

import logging

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from qdrant_client.models import Distance, VectorParams

from .... schema import DocumentEmbeddingsResponse
from .... schema import Error, Value
from .... base import DocumentEmbeddingsQueryService

# Module logger
logger = logging.getLogger(__name__)

default_ident = "de-query"

default_store_uri = 'http://localhost:6333'

class Processor(DocumentEmbeddingsQueryService):

    def __init__(self, **params):

        store_uri = params.get("store_uri", default_store_uri)

        #optional api key
        api_key = params.get("api_key", None)

        super(Processor, self).__init__(
            **params | {
                "store_uri": store_uri,
                "api_key": api_key,
            }
        )

        self.qdrant = QdrantClient(url=store_uri, api_key=api_key)

    def collection_exists(self, collection):
        """Check if collection exists (no implicit creation)"""
        return self.qdrant.collection_exists(collection)

    async def query_document_embeddings(self, msg):

        try:

            chunks = []

            for vec in msg.vectors:

                # Use dimension suffix in collection name
                dim = len(vec)
                collection = f"d_{msg.user}_{msg.collection}_{dim}"

                # Check if collection exists - return empty if not
                if not self.collection_exists(collection):
                    logger.info(f"Collection {collection} does not exist, returning empty results")
                    continue

                search_result = self.qdrant.query_points(
                    collection_name=collection,
                    query=vec,
                    limit=msg.limit,
                    with_payload=True,
                ).points

                for r in search_result:
                    ent = r.payload["doc"]
                    chunks.append(ent)

            return chunks

        except Exception as e:

            logger.error(f"Exception querying document embeddings: {e}", exc_info=True)
            raise e

    @staticmethod
    def add_args(parser):

        DocumentEmbeddingsQueryService.add_args(parser)

        parser.add_argument(
            '-t', '--store-uri',
            default=default_store_uri,
            help=f'Qdrant store URI (default: {default_store_uri})'
        )
        
        parser.add_argument(
            '-k', '--api-key',
            default=None,
            help=f'API key for qdrant (default: None)'
        )

def run():

    Processor.launch(default_ident, __doc__)

