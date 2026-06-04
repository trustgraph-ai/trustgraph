
"""
Document embeddings query service.  Input is vector, output is an array
of chunk_ids
"""

import asyncio
import logging

from qdrant_client import QdrantClient

from .... schema import DocumentEmbeddingsResponse, ChunkMatch
from .... schema import Error
from .... base import DocumentEmbeddingsQueryService
from .... base.qdrant_config import add_qdrant_args, resolve_qdrant_config

# Module logger
logger = logging.getLogger(__name__)

default_ident = "doc-embeddings-query"

class Processor(DocumentEmbeddingsQueryService):

    def __init__(self, **params):

        store_uri = params.get("store_uri")
        api_key = params.get("api_key")

        url, api_key, _, _ = resolve_qdrant_config(
            url=store_uri, api_key=api_key,
        )

        super(Processor, self).__init__(
            **params | {
                "store_uri": url,
                "api_key": api_key,
            }
        )

        self.qdrant = QdrantClient(url=url, api_key=api_key)

    async def query_document_embeddings(self, workspace, msg):

        try:

            vec = msg.vector
            if not vec:
                return []

            dim = len(vec)
            collection = f"d_{workspace}_{msg.collection}_{dim}"

            exists = await asyncio.to_thread(
                self.qdrant.collection_exists, collection
            )
            if not exists:
                logger.info(f"Collection {collection} does not exist, returning empty results")
                return []

            result = await asyncio.to_thread(
                self.qdrant.query_points,
                collection_name=collection,
                query=vec,
                limit=msg.limit,
                with_payload=True,
            )
            search_result = result.points

            chunks = []
            for r in search_result:
                chunk_id = r.payload["chunk_id"]
                score = r.score if hasattr(r, 'score') else 0.0
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
        add_qdrant_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

