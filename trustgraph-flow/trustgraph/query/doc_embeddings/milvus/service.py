
"""
Document embeddings query service.  Input is vector, output is an array
of chunk_ids
"""

import logging

from .... direct.milvus_doc_embeddings import DocVectors
from .... schema import DocumentEmbeddingsResponse, ChunkMatch
from .... schema import Error
from .... base import DocumentEmbeddingsQueryService

# Module logger
logger = logging.getLogger(__name__)

default_ident = "doc-embeddings-query"
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

            vec = msg.vector
            if not vec:
                return []

            # Handle zero limit case
            if msg.limit <= 0:
                return []

            resp = self.vecstore.search(
                vec,
                msg.user,
                msg.collection,
                limit=msg.limit
            )

            chunks = []
            for r in resp:
                chunk_id = r["entity"]["chunk_id"]
                # Milvus returns distance, convert to similarity score
                distance = r.get("distance", 0.0)
                score = 1.0 - distance if distance else 0.0
                chunks.append(ChunkMatch(
                    chunk_id=chunk_id,
                    score=score,
                ))

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

