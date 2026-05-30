
"""
Accepts entity/vector pairs and writes them to a Qdrant store.
"""

import asyncio
import uuid
import logging

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from qdrant_client.models import Distance, VectorParams

from .... base import GraphEmbeddingsStoreService, CollectionConfigHandler
from .... base import AsyncProcessor, Consumer, Producer
from .... base import ConsumerMetrics, ProducerMetrics
from .... schema import IRI, LITERAL

# Module logger
logger = logging.getLogger(__name__)


def get_term_value(term):
    """Extract the string value from a Term"""
    if term is None:
        return None
    if term.type == IRI:
        return term.iri
    elif term.type == LITERAL:
        return term.value
    else:
        # For blank nodes or other types, use id or value
        return term.id or term.value


default_ident = "graph-embeddings-write"

default_store_uri = 'http://localhost:6333'

class Processor(CollectionConfigHandler, GraphEmbeddingsStoreService):

    def __init__(self, **params):

        store_uri = params.get("store_uri", default_store_uri)
        api_key = params.get("api_key", None)

        super(Processor, self).__init__(
            **params | {
                "store_uri": store_uri,
                "api_key": api_key,
            }
        )

        self.qdrant = QdrantClient(url=store_uri, api_key=api_key)
        self._cache_lock = asyncio.Lock()
        self._known_collections: set[str] = set()

        # Register for config push notifications
        self.register_config_handler(self.on_collection_config, types=["collection"])

    async def ensure_collection(self, collection_name, dim):
        async with self._cache_lock:
            if collection_name in self._known_collections:
                return
            exists = await asyncio.to_thread(
                self.qdrant.collection_exists, collection_name
            )
            if not exists:
                logger.info(
                    f"Lazily creating Qdrant collection {collection_name} "
                    f"with dimension {dim}"
                )
                await asyncio.to_thread(
                    self.qdrant.create_collection,
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=dim, distance=Distance.COSINE
                    ),
                )
            self._known_collections.add(collection_name)

    async def store_graph_embeddings(self, workspace, message):

        if not self.collection_exists(workspace, message.metadata.collection):
            logger.warning(
                f"Collection {message.metadata.collection} for workspace {workspace} "
                f"does not exist in config (likely deleted while data was in-flight). "
                f"Dropping message."
            )
            return

        for entity in message.entities:
            entity_value = get_term_value(entity.entity)

            if entity_value == "" or entity_value is None:
                continue

            vec = entity.vector
            if not vec:
                continue

            dim = len(vec)
            collection = (
                f"t_{workspace}_{message.metadata.collection}_{dim}"
            )

            await self.ensure_collection(collection, dim)

            payload = {
                "entity": entity_value,
            }
            if entity.chunk_id:
                payload["chunk_id"] = entity.chunk_id

            await asyncio.to_thread(
                self.qdrant.upsert,
                collection_name=collection,
                points=[
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vec,
                        payload=payload,
                    )
                ],
            )

    @staticmethod
    def add_args(parser):

        GraphEmbeddingsStoreService.add_args(parser)

        parser.add_argument(
            '-t', '--store-uri',
            default=default_store_uri,
            help=f'Qdrant store URI (default: {default_store_uri})'
        )
        
        parser.add_argument(
            '-k', '--api-key',
            default=None,
            help=f'Qdrant API key'
        )

    async def create_collection(self, workspace: str, collection: str, metadata: dict):
        """
        Create collection via config push - collections are created lazily on first write
        with the correct dimension determined from the actual embeddings.
        """
        try:
            logger.info(f"Collection create request for {workspace}/{collection} - will be created lazily on first write")

        except Exception as e:
            logger.error(f"Failed to create collection {workspace}/{collection}: {e}", exc_info=True)
            raise

    async def delete_collection(self, workspace: str, collection: str):
        """Delete the collection for graph embeddings via config push"""
        try:
            prefix = f"t_{workspace}_{collection}_"

            all_collections = await asyncio.to_thread(
                lambda: self.qdrant.get_collections().collections
            )
            matching_collections = [
                coll.name for coll in all_collections
                if coll.name.startswith(prefix)
            ]

            if not matching_collections:
                logger.info(f"No collections found matching prefix {prefix}")
            else:
                for collection_name in matching_collections:
                    await asyncio.to_thread(
                        self.qdrant.delete_collection, collection_name
                    )
                    async with self._cache_lock:
                        self._known_collections.discard(collection_name)
                    logger.info(f"Deleted Qdrant collection: {collection_name}")
                logger.info(f"Deleted {len(matching_collections)} collection(s) for {workspace}/{collection}")

        except Exception as e:
            logger.error(f"Failed to delete collection {workspace}/{collection}: {e}", exc_info=True)
            raise

def run():

    Processor.launch(default_ident, __doc__)

