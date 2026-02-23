
"""
Row embeddings processor. Calls the embeddings service to compute embeddings
for indexed field values in extracted row data.

Input is ExtractedObject (structured row data with schema).
Output is RowEmbeddings (row data with embeddings for indexed fields).

This follows the two-stage pattern used by graph-embeddings and document-embeddings:
  Stage 1 (this processor): Compute embeddings
  Stage 2 (row-embeddings-write-*): Store embeddings
"""

import json
import logging
from typing import Dict, List, Set

from ... schema import ExtractedObject, RowEmbeddings, RowIndexEmbedding
from ... schema import RowSchema, Field
from ... base import FlowProcessor, EmbeddingsClientSpec, ConsumerSpec
from ... base import ProducerSpec, CollectionConfigHandler

logger = logging.getLogger(__name__)

default_ident = "row-embeddings"
default_batch_size = 10


class Processor(CollectionConfigHandler, FlowProcessor):

    def __init__(self, **params):

        id = params.get("id", default_ident)
        self.batch_size = params.get("batch_size", default_batch_size)

        # Config key for schemas
        self.config_key = params.get("config_type", "schema")

        super(Processor, self).__init__(
            **params | {
                "id": id,
                "config_type": self.config_key,
            }
        )

        self.register_specification(
            ConsumerSpec(
                name="input",
                schema=ExtractedObject,
                handler=self.on_message,
            )
        )

        self.register_specification(
            EmbeddingsClientSpec(
                request_name="embeddings-request",
                response_name="embeddings-response",
            )
        )

        self.register_specification(
            ProducerSpec(
                name="output",
                schema=RowEmbeddings
            )
        )

        # Register config handlers
        self.register_config_handler(self.on_schema_config)
        self.register_config_handler(self.on_collection_config)

        # Schema storage: name -> RowSchema
        self.schemas: Dict[str, RowSchema] = {}

    async def on_schema_config(self, config, version):
        """Handle schema configuration updates"""
        logger.info(f"Loading schema configuration version {version}")

        # Clear existing schemas
        self.schemas = {}

        # Check if our config type exists
        if self.config_key not in config:
            logger.warning(f"No '{self.config_key}' type in configuration")
            return

        # Get the schemas dictionary for our type
        schemas_config = config[self.config_key]

        # Process each schema in the schemas config
        for schema_name, schema_json in schemas_config.items():
            try:
                # Parse the JSON schema definition
                schema_def = json.loads(schema_json)

                # Create Field objects
                fields = []
                for field_def in schema_def.get("fields", []):
                    field = Field(
                        name=field_def["name"],
                        type=field_def["type"],
                        size=field_def.get("size", 0),
                        primary=field_def.get("primary_key", False),
                        description=field_def.get("description", ""),
                        required=field_def.get("required", False),
                        enum_values=field_def.get("enum", []),
                        indexed=field_def.get("indexed", False)
                    )
                    fields.append(field)

                # Create RowSchema
                row_schema = RowSchema(
                    name=schema_def.get("name", schema_name),
                    description=schema_def.get("description", ""),
                    fields=fields
                )

                self.schemas[schema_name] = row_schema
                logger.info(f"Loaded schema: {schema_name} with {len(fields)} fields")

            except Exception as e:
                logger.error(f"Failed to parse schema {schema_name}: {e}", exc_info=True)

        logger.info(f"Schema configuration loaded: {len(self.schemas)} schemas")

    def get_index_names(self, schema: RowSchema) -> List[str]:
        """Get all index names for a schema."""
        index_names = []
        for field in schema.fields:
            if field.primary or field.indexed:
                index_names.append(field.name)
        return index_names

    def build_index_value(self, value_map: Dict[str, str], index_name: str) -> List[str]:
        """Build the index_value list for a given index."""
        field_names = [f.strip() for f in index_name.split(',')]
        values = []
        for field_name in field_names:
            value = value_map.get(field_name)
            values.append(str(value) if value is not None else "")
        return values

    def build_text_for_embedding(self, index_value: List[str]) -> str:
        """Build text representation for embedding from index values."""
        # Space-join the values for composite indexes
        return " ".join(index_value)

    async def on_message(self, msg, consumer, flow):
        """Process incoming ExtractedObject and compute embeddings"""

        obj = msg.value()
        logger.info(
            f"Computing embeddings for {len(obj.values)} rows, "
            f"schema {obj.schema_name}, doc {obj.metadata.id}"
        )

        # Validate collection exists before processing
        if not self.collection_exists(obj.metadata.user, obj.metadata.collection):
            logger.warning(
                f"Collection {obj.metadata.collection} for user {obj.metadata.user} "
                f"does not exist in config. Dropping message."
            )
            return

        # Get schema definition
        schema = self.schemas.get(obj.schema_name)
        if not schema:
            logger.warning(f"No schema found for {obj.schema_name} - skipping")
            return

        # Get all index names for this schema
        index_names = self.get_index_names(schema)

        if not index_names:
            logger.warning(f"Schema {obj.schema_name} has no indexed fields - skipping")
            return

        # Track unique texts to avoid duplicate embeddings
        # text -> (index_name, index_value)
        texts_to_embed: Dict[str, tuple] = {}

        # Collect all texts that need embeddings
        for value_map in obj.values:
            for index_name in index_names:
                index_value = self.build_index_value(value_map, index_name)

                # Skip empty values
                if not index_value or all(v == "" for v in index_value):
                    continue

                text = self.build_text_for_embedding(index_value)
                if text and text not in texts_to_embed:
                    texts_to_embed[text] = (index_name, index_value)

        if not texts_to_embed:
            logger.info("No texts to embed")
            return

        # Compute embeddings
        embeddings_list = []

        try:
            for text, (index_name, index_value) in texts_to_embed.items():
                vectors = await flow("embeddings-request").embed(text=text)

                embeddings_list.append(
                    RowIndexEmbedding(
                        index_name=index_name,
                        index_value=index_value,
                        text=text,
                        vectors=vectors
                    )
                )

            # Send in batches to avoid oversized messages
            for i in range(0, len(embeddings_list), self.batch_size):
                batch = embeddings_list[i:i + self.batch_size]
                result = RowEmbeddings(
                    metadata=obj.metadata,
                    schema_name=obj.schema_name,
                    embeddings=batch,
                )
                await flow("output").send(result)

            logger.info(
                f"Computed {len(embeddings_list)} embeddings for "
                f"{len(obj.values)} rows ({len(index_names)} indexes)"
            )

        except Exception as e:
            logger.error("Exception during embedding computation", exc_info=True)
            raise e

    async def create_collection(self, user: str, collection: str, metadata: dict):
        """Collection creation notification - no action needed for embedding stage"""
        logger.debug(f"Row embeddings collection notification for {user}/{collection}")

    async def delete_collection(self, user: str, collection: str):
        """Collection deletion notification - no action needed for embedding stage"""
        logger.debug(f"Row embeddings collection delete notification for {user}/{collection}")

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

        parser.add_argument(
            '--batch-size',
            type=int,
            default=default_batch_size,
            help=f'Maximum embeddings per output message (default: {default_batch_size})'
        )

        parser.add_argument(
            '--config-type',
            default='schema',
            help='Configuration type prefix for schemas (default: schema)'
        )


def run():
    Processor.launch(default_ident, __doc__)

