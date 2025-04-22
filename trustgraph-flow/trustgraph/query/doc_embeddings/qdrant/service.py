
"""
Document embeddings query service.  Input is vector, output is an array
of chunks
"""

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from qdrant_client.models import Distance, VectorParams

from .... schema import DocumentEmbeddingsResponse
from .... schema import Error, Value
from .... base import DocumentEmbeddingsQueryService

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

    async def query_document_embeddings(self, msg):

        try:

            chunks = []

            for vec in msg.vectors:

                dim = len(vec)
                collection = (
                    "d_" + msg.user + "_" + msg.collection + "_" +
                    str(dim)
                )

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

            print(f"Exception: {e}")
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

