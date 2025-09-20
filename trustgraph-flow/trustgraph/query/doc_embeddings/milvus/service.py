
"""
Document embeddings query service.  Input is vector, output is an array
of chunks
"""

import logging

from .... direct.milvus_doc_embeddings import DocVectors
from .... schema import DocumentEmbeddingsResponse
from .... schema import Error, Value
from .... base import DocumentEmbeddingsQueryService

# Module logger
logger = logging.getLogger(__name__)

default_ident = "de-query"
default_store_uri = 'http://localhost:19530'

class Processor(DocumentEmbeddingsQueryService):

    def __init__(self, **params):

        store_uri = params.get("store_uri", default_store_uri)

        super(Processor, self).__init__(
            **params | {
                "store_uri": store_uri,
            }
        )

        self.vecstore = DocVectors(store_uri)

    async def query_document_embeddings(self, msg):

        try:

            # Handle zero limit case
            if msg.limit <= 0:
                return []

            chunks = []

            for vec in msg.vectors:

                resp = self.vecstore.search(
                    vec, 
                    msg.user, 
                    msg.collection, 
                    limit=msg.limit
                )

                for r in resp:
                    chunk = r["entity"]["doc"]
                    chunks.append(chunk)

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
            help=f'Milvus store URI (default: {default_store_uri})'
        )

def run():

    Processor.launch(default_ident, __doc__)

