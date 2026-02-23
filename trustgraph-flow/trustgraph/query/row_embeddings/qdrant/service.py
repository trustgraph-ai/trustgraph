"""
Row embeddings query service for Qdrant.

Input is query vectors plus user/collection/schema context.
Output is matching row index information (index_name, index_value) for
use in subsequent Cassandra lookups.
"""

import logging
import re
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from .... schema import (
    RowEmbeddingsRequest, RowEmbeddingsResponse,
    RowIndexMatch, Error
)
from .... base import FlowProcessor, ConsumerSpec, ProducerSpec

# Module logger
logger = logging.getLogger(__name__)

default_ident = "row-embeddings-query"
default_store_uri = 'http://localhost:6333'


class Processor(FlowProcessor):

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
                name="request",
                schema=RowEmbeddingsRequest,
                handler=self.on_message
            )
        )

        self.register_specification(
            ProducerSpec(
                name="response",
                schema=RowEmbeddingsResponse
            )
        )

        self.qdrant = QdrantClient(url=store_uri, api_key=api_key)

    def sanitize_name(self, name: str) -> str:
        """Sanitize names for Qdrant collection naming"""
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        if safe_name and not safe_name[0].isalpha():
            safe_name = 'r_' + safe_name
        return safe_name.lower()

    def find_collection(self, user: str, collection: str, schema_name: str) -> Optional[str]:
        """Find the Qdrant collection for a given user/collection/schema"""
        prefix = (
            f"rows_{self.sanitize_name(user)}_"
            f"{self.sanitize_name(collection)}_{self.sanitize_name(schema_name)}_"
        )

        try:
            all_collections = self.qdrant.get_collections().collections
            matching = [
                coll.name for coll in all_collections
                if coll.name.startswith(prefix)
            ]

            if matching:
                # Return first match (there should typically be only one per dimension)
                return matching[0]

        except Exception as e:
            logger.error(f"Failed to list Qdrant collections: {e}", exc_info=True)

        return None

    async def query_row_embeddings(self, request: RowEmbeddingsRequest):
        """Execute row embeddings query"""

        matches = []

        # Find the collection for this user/collection/schema
        qdrant_collection = self.find_collection(
            request.user, request.collection, request.schema_name
        )

        if not qdrant_collection:
            logger.info(
                f"No Qdrant collection found for "
                f"{request.user}/{request.collection}/{request.schema_name}"
            )
            return matches

        for vec in request.vectors:
            try:
                # Build optional filter for index_name
                query_filter = None
                if request.index_name:
                    query_filter = Filter(
                        must=[
                            FieldCondition(
                                key="index_name",
                                match=MatchValue(value=request.index_name)
                            )
                        ]
                    )

                # Query Qdrant
                search_result = self.qdrant.query_points(
                    collection_name=qdrant_collection,
                    query=vec,
                    limit=request.limit,
                    with_payload=True,
                    query_filter=query_filter,
                ).points

                # Convert to RowIndexMatch objects
                for point in search_result:
                    payload = point.payload or {}
                    match = RowIndexMatch(
                        index_name=payload.get("index_name", ""),
                        index_value=payload.get("index_value", []),
                        text=payload.get("text", ""),
                        score=point.score if hasattr(point, 'score') else 0.0
                    )
                    matches.append(match)

            except Exception as e:
                logger.error(f"Failed to query Qdrant: {e}", exc_info=True)
                raise

        return matches

    async def on_message(self, msg, consumer, flow):
        """Handle incoming query request"""

        try:
            request = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            logger.debug(
                f"Handling row embeddings query for "
                f"{request.user}/{request.collection}/{request.schema_name}..."
            )

            # Execute query
            matches = await self.query_row_embeddings(request)

            response = RowEmbeddingsResponse(
                error=None,
                matches=matches
            )

            logger.debug(f"Returning {len(matches)} matches")
            await flow("response").send(response, properties={"id": id})

        except Exception as e:
            logger.error(f"Exception in row embeddings query: {e}", exc_info=True)

            response = RowEmbeddingsResponse(
                error=Error(
                    type="row-embeddings-query-error",
                    message=str(e)
                ),
                matches=[]
            )

            await flow("response").send(response, properties={"id": id})

    @staticmethod
    def add_args(parser):
        """Add command-line arguments"""

        FlowProcessor.add_args(parser)

        parser.add_argument(
            '-t', '--store-uri',
            default=default_store_uri,
            help=f'Qdrant store URI (default: {default_store_uri})'
        )

        parser.add_argument(
            '-k', '--api-key',
            default=None,
            help='API key for Qdrant (default: None)'
        )


def run():
    """Entry point for row-embeddings-query-qdrant command"""
    Processor.launch(default_ident, __doc__)
