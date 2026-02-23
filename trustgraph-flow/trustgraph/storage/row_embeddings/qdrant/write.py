"""
Row embeddings writer for Qdrant (Stage 2).

Consumes RowEmbeddings messages (which already contain computed vectors)
and writes them to Qdrant. One Qdrant collection per (user, collection, schema_name) pair.

This follows the two-stage pattern used by graph-embeddings and document-embeddings:
  Stage 1 (row-embeddings): Compute embeddings
  Stage 2 (this processor): Store embeddings

Collection naming: rows_{user}_{collection}_{schema_name}_{dimension}

Payload structure:
    - index_name: The indexed field(s) this embedding represents
    - index_value: The original list of values (for Cassandra lookup)
    - text: The text that was embedded (for debugging/display)
"""

import logging
import re
import uuid
from typing import Set, Tuple

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams

from .... schema import RowEmbeddings
from .... base import FlowProcessor, ConsumerSpec
from .... base import CollectionConfigHandler

# Module logger
logger = logging.getLogger(__name__)

default_ident = "row-embeddings-write"
default_store_uri = 'http://localhost:6333'


class Processor(CollectionConfigHandler, FlowProcessor):

    def __init__(self, **params):

        id = params.get("id", default_ident)

        store_uri = params.get("store_uri", default_store_uri)
        api_key = params.get("api_key", None)

        super(Processor, self).__init__(
            **params | {
                "id": id,
                "store_uri": store_uri,
                "api_key": api_key,
            }
        )

        self.register_specification(
            ConsumerSpec(
                name="input",
                schema=RowEmbeddings,
                handler=self.on_embeddings
            )
        )

        # Register config handler for collection management
        self.register_config_handler(self.on_collection_config)

        # Cache of created Qdrant collections
        self.created_collections: Set[str] = set()

        # Qdrant client
        self.qdrant = QdrantClient(url=store_uri, api_key=api_key)

    def sanitize_name(self, name: str) -> str:
        """Sanitize names for Qdrant collection naming"""
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        if safe_name and not safe_name[0].isalpha():
            safe_name = 'r_' + safe_name
        return safe_name.lower()

    def get_collection_name(
        self, user: str, collection: str, schema_name: str, dimension: int
    ) -> str:
        """Generate Qdrant collection name"""
        safe_user = self.sanitize_name(user)
        safe_collection = self.sanitize_name(collection)
        safe_schema = self.sanitize_name(schema_name)
        return f"rows_{safe_user}_{safe_collection}_{safe_schema}_{dimension}"

    def ensure_collection(self, collection_name: str, dimension: int):
        """Create Qdrant collection if it doesn't exist"""
        if collection_name in self.created_collections:
            return

        if not self.qdrant.collection_exists(collection_name):
            logger.info(
                f"Creating Qdrant collection {collection_name} "
                f"with dimension {dimension}"
            )
            self.qdrant.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=Distance.COSINE
                )
            )

        self.created_collections.add(collection_name)

    async def on_embeddings(self, msg, consumer, flow):
        """Process incoming RowEmbeddings and write to Qdrant"""

        embeddings = msg.value()
        logger.info(
            f"Writing {len(embeddings.embeddings)} embeddings for schema "
            f"{embeddings.schema_name} from {embeddings.metadata.id}"
        )

        # Validate collection exists in config before processing
        if not self.collection_exists(
            embeddings.metadata.user, embeddings.metadata.collection
        ):
            logger.warning(
                f"Collection {embeddings.metadata.collection} for user "
                f"{embeddings.metadata.user} does not exist in config. "
                f"Dropping message."
            )
            return

        user = embeddings.metadata.user
        collection = embeddings.metadata.collection
        schema_name = embeddings.schema_name

        embeddings_written = 0
        qdrant_collection = None

        for row_emb in embeddings.embeddings:
            if not row_emb.vectors:
                logger.warning(
                    f"No vectors for index {row_emb.index_name} - skipping"
                )
                continue

            # Use first vector (there may be multiple from different models)
            for vector in row_emb.vectors:
                dimension = len(vector)

                # Create/get collection name (lazily on first vector)
                if qdrant_collection is None:
                    qdrant_collection = self.get_collection_name(
                        user, collection, schema_name, dimension
                    )
                    self.ensure_collection(qdrant_collection, dimension)

                # Write to Qdrant
                self.qdrant.upsert(
                    collection_name=qdrant_collection,
                    points=[
                        PointStruct(
                            id=str(uuid.uuid4()),
                            vector=vector,
                            payload={
                                "index_name": row_emb.index_name,
                                "index_value": row_emb.index_value,
                                "text": row_emb.text
                            }
                        )
                    ]
                )
                embeddings_written += 1

        logger.info(f"Wrote {embeddings_written} embeddings to Qdrant")

    async def create_collection(self, user: str, collection: str, metadata: dict):
        """Collection creation via config push - collections created lazily on first write"""
        logger.info(
            f"Row embeddings collection create request for {user}/{collection} - "
            f"will be created lazily on first write"
        )

    async def delete_collection(self, user: str, collection: str):
        """Delete all Qdrant collections for a given user/collection"""
        try:
            prefix = f"rows_{self.sanitize_name(user)}_{self.sanitize_name(collection)}_"

            # Get all collections and filter for matches
            all_collections = self.qdrant.get_collections().collections
            matching_collections = [
                coll.name for coll in all_collections
                if coll.name.startswith(prefix)
            ]

            if not matching_collections:
                logger.info(f"No Qdrant collections found matching prefix {prefix}")
            else:
                for collection_name in matching_collections:
                    self.qdrant.delete_collection(collection_name)
                    self.created_collections.discard(collection_name)
                    logger.info(f"Deleted Qdrant collection: {collection_name}")
                logger.info(
                    f"Deleted {len(matching_collections)} collection(s) "
                    f"for {user}/{collection}"
                )

        except Exception as e:
            logger.error(
                f"Failed to delete collection {user}/{collection}: {e}",
                exc_info=True
            )
            raise

    async def delete_collection_schema(
        self, user: str, collection: str, schema_name: str
    ):
        """Delete Qdrant collection for a specific user/collection/schema"""
        try:
            prefix = (
                f"rows_{self.sanitize_name(user)}_"
                f"{self.sanitize_name(collection)}_{self.sanitize_name(schema_name)}_"
            )

            # Get all collections and filter for matches
            all_collections = self.qdrant.get_collections().collections
            matching_collections = [
                coll.name for coll in all_collections
                if coll.name.startswith(prefix)
            ]

            if not matching_collections:
                logger.info(f"No Qdrant collections found matching prefix {prefix}")
            else:
                for collection_name in matching_collections:
                    self.qdrant.delete_collection(collection_name)
                    self.created_collections.discard(collection_name)
                    logger.info(f"Deleted Qdrant collection: {collection_name}")

        except Exception as e:
            logger.error(
                f"Failed to delete collection {user}/{collection}/{schema_name}: {e}",
                exc_info=True
            )
            raise

    @staticmethod
    def add_args(parser):
        """Add command-line arguments"""

        FlowProcessor.add_args(parser)

        parser.add_argument(
            '-t', '--store-uri',
            default=default_store_uri,
            help=f'Qdrant URI (default: {default_store_uri})'
        )

        parser.add_argument(
            '-k', '--api-key',
            default=None,
            help='Qdrant API key (default: None)'
        )


def run():
    """Entry point for row-embeddings-write-qdrant command"""
    Processor.launch(default_ident, __doc__)

