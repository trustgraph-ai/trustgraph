"""
Row writer for Cassandra. Input is ExtractedObject.
Writes structured rows to a unified Cassandra table with multi-index support.

Uses a single 'rows' table with the schema:
    - collection: text
    - schema_name: text
    - index_name: text
    - index_value: frozen<list<text>>
    - data: map<text, text>
    - source: text

Each row is written multiple times - once per indexed field defined in the schema.
"""

import json
import logging
import re
from typing import Dict, Set, Optional, Any, List, Tuple

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider

from .... schema import ExtractedObject
from .... schema import RowSchema, Field
from .... base import FlowProcessor, ConsumerSpec
from .... base import CollectionConfigHandler
from .... base.cassandra_config import add_cassandra_args, resolve_cassandra_config

# Module logger
logger = logging.getLogger(__name__)

default_ident = "rows-write"


class Processor(CollectionConfigHandler, FlowProcessor):

    def __init__(self, **params):

        id = params.get("id", default_ident)

        # Get Cassandra parameters
        cassandra_host = params.get("cassandra_host")
        cassandra_username = params.get("cassandra_username")
        cassandra_password = params.get("cassandra_password")

        # Resolve configuration with environment variable fallback
        hosts, username, password, keyspace = resolve_cassandra_config(
            host=cassandra_host,
            username=cassandra_username,
            password=cassandra_password
        )

        # Store resolved configuration with proper names
        self.cassandra_host = hosts  # Store as list
        self.cassandra_username = username
        self.cassandra_password = password

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
                handler=self.on_object
            )
        )

        # Register config handlers
        self.register_config_handler(self.on_schema_config)
        self.register_config_handler(self.on_collection_config)

        # Cache of known keyspaces and whether tables exist
        self.known_keyspaces: Set[str] = set()
        self.tables_initialized: Set[str] = set()  # keyspaces with rows/row_partitions tables

        # Cache of registered (collection, schema_name) pairs
        self.registered_partitions: Set[Tuple[str, str]] = set()

        # Schema storage: name -> RowSchema
        self.schemas: Dict[str, RowSchema] = {}

        # Cassandra session
        self.cluster = None
        self.session = None

    def connect_cassandra(self):
        """Connect to Cassandra cluster"""
        if self.session:
            return

        try:
            if self.cassandra_username and self.cassandra_password:
                auth_provider = PlainTextAuthProvider(
                    username=self.cassandra_username,
                    password=self.cassandra_password
                )
                self.cluster = Cluster(
                    contact_points=self.cassandra_host,
                    auth_provider=auth_provider
                )
            else:
                self.cluster = Cluster(contact_points=self.cassandra_host)

            self.session = self.cluster.connect()
            logger.info(f"Connected to Cassandra cluster at {self.cassandra_host}")

        except Exception as e:
            logger.error(f"Failed to connect to Cassandra: {e}", exc_info=True)
            raise

    async def on_schema_config(self, config, version):
        """Handle schema configuration updates"""
        logger.info(f"Loading schema configuration version {version}")

        # Track which schemas changed so we can clear partition cache
        old_schema_names = set(self.schemas.keys())

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

        # Clear partition cache for schemas that changed
        # This ensures next write will re-register partitions
        new_schema_names = set(self.schemas.keys())
        changed_schemas = old_schema_names.symmetric_difference(new_schema_names)
        if changed_schemas:
            self.registered_partitions = {
                (col, sch) for col, sch in self.registered_partitions
                if sch not in changed_schemas
            }
            logger.info(f"Cleared partition cache for changed schemas: {changed_schemas}")

    def sanitize_name(self, name: str) -> str:
        """Sanitize names for Cassandra compatibility"""
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # Ensure it starts with a letter
        if safe_name and not safe_name[0].isalpha():
            safe_name = 'r_' + safe_name
        return safe_name.lower()

    def ensure_keyspace(self, keyspace: str):
        """Ensure keyspace exists in Cassandra"""
        if keyspace in self.known_keyspaces:
            return

        # Connect if needed
        self.connect_cassandra()

        # Sanitize keyspace name
        safe_keyspace = self.sanitize_name(keyspace)

        # Create keyspace if not exists
        create_keyspace_cql = f"""
        CREATE KEYSPACE IF NOT EXISTS {safe_keyspace}
        WITH REPLICATION = {{
            'class': 'SimpleStrategy',
            'replication_factor': 1
        }}
        """

        try:
            self.session.execute(create_keyspace_cql)
            self.known_keyspaces.add(keyspace)
            logger.info(f"Ensured keyspace exists: {safe_keyspace}")
        except Exception as e:
            logger.error(f"Failed to create keyspace {safe_keyspace}: {e}", exc_info=True)
            raise

    def ensure_tables(self, keyspace: str):
        """Ensure unified rows and row_partitions tables exist"""
        if keyspace in self.tables_initialized:
            return

        # Ensure keyspace exists first
        self.ensure_keyspace(keyspace)

        safe_keyspace = self.sanitize_name(keyspace)

        # Create unified rows table
        create_rows_cql = f"""
        CREATE TABLE IF NOT EXISTS {safe_keyspace}.rows (
            collection text,
            schema_name text,
            index_name text,
            index_value frozen<list<text>>,
            data map<text, text>,
            source text,
            PRIMARY KEY ((collection, schema_name, index_name), index_value)
        )
        """

        # Create row_partitions tracking table
        create_partitions_cql = f"""
        CREATE TABLE IF NOT EXISTS {safe_keyspace}.row_partitions (
            collection text,
            schema_name text,
            index_name text,
            PRIMARY KEY ((collection), schema_name, index_name)
        )
        """

        try:
            self.session.execute(create_rows_cql)
            logger.info(f"Ensured rows table exists: {safe_keyspace}.rows")

            self.session.execute(create_partitions_cql)
            logger.info(f"Ensured row_partitions table exists: {safe_keyspace}.row_partitions")

            self.tables_initialized.add(keyspace)

        except Exception as e:
            logger.error(f"Failed to create tables in {safe_keyspace}: {e}", exc_info=True)
            raise

    def get_index_names(self, schema: RowSchema) -> List[str]:
        """
        Get all index names for a schema.
        Returns list of index_name strings (single field names or comma-joined composites).
        """
        index_names = []

        for field in schema.fields:
            # Primary key fields are treated as indexes
            if field.primary:
                index_names.append(field.name)
            # Indexed fields
            elif field.indexed:
                index_names.append(field.name)

        # TODO: Support composite indexes in the future
        # For now, each indexed field is a single-field index

        return index_names

    def register_partitions(self, keyspace: str, collection: str, schema_name: str):
        """
        Register partition entries for a (collection, schema_name) pair.
        Called once on first row for each pair.
        """
        cache_key = (collection, schema_name)
        if cache_key in self.registered_partitions:
            return

        schema = self.schemas.get(schema_name)
        if not schema:
            logger.warning(f"Cannot register partitions - schema {schema_name} not found")
            return

        safe_keyspace = self.sanitize_name(keyspace)
        index_names = self.get_index_names(schema)

        # Insert partition entries for each index
        insert_cql = f"""
        INSERT INTO {safe_keyspace}.row_partitions (collection, schema_name, index_name)
        VALUES (%s, %s, %s)
        """

        for index_name in index_names:
            try:
                self.session.execute(insert_cql, (collection, schema_name, index_name))
            except Exception as e:
                logger.warning(f"Failed to register partition {collection}/{schema_name}/{index_name}: {e}")

        self.registered_partitions.add(cache_key)
        logger.info(f"Registered partitions for {collection}/{schema_name}: {index_names}")

    def build_index_value(self, value_map: Dict[str, str], index_name: str) -> List[str]:
        """
        Build the index_value list for a given index.
        For single-field indexes, returns a single-element list.
        For composite indexes (comma-separated), returns multiple elements.
        """
        field_names = [f.strip() for f in index_name.split(',')]
        values = []

        for field_name in field_names:
            value = value_map.get(field_name)
            # Convert to string for storage
            values.append(str(value) if value is not None else "")

        return values

    async def on_object(self, msg, consumer, flow):
        """Process incoming ExtractedObject and store in Cassandra"""

        obj = msg.value()
        logger.info(
            f"Storing {len(obj.values)} rows for schema {obj.schema_name} "
            f"from {obj.metadata.id}"
        )

        # Validate collection exists before accepting writes
        if not self.collection_exists(obj.metadata.user, obj.metadata.collection):
            error_msg = (
                f"Collection {obj.metadata.collection} does not exist. "
                f"Create it first via collection management API."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Get schema definition
        schema = self.schemas.get(obj.schema_name)
        if not schema:
            logger.warning(f"No schema found for {obj.schema_name} - skipping")
            return

        keyspace = obj.metadata.user
        collection = obj.metadata.collection
        schema_name = obj.schema_name
        source = getattr(obj.metadata, 'source', '') or ''

        # Ensure tables exist
        self.ensure_tables(keyspace)

        # Register partitions if first time seeing this (collection, schema_name)
        self.register_partitions(keyspace, collection, schema_name)

        safe_keyspace = self.sanitize_name(keyspace)

        # Get all index names for this schema
        index_names = self.get_index_names(schema)

        if not index_names:
            logger.warning(f"Schema {schema_name} has no indexed fields - rows won't be queryable")
            return

        # Prepare insert statement
        insert_cql = f"""
        INSERT INTO {safe_keyspace}.rows
            (collection, schema_name, index_name, index_value, data, source)
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        # Process each row in the batch
        rows_written = 0
        for row_index, value_map in enumerate(obj.values):
            # Convert all values to strings for the data map
            data_map = {}
            for field in schema.fields:
                raw_value = value_map.get(field.name)
                if raw_value is not None:
                    data_map[field.name] = str(raw_value)

            # Write one copy per index
            for index_name in index_names:
                index_value = self.build_index_value(value_map, index_name)

                # Skip if index value is empty/null
                if not index_value or all(v == "" for v in index_value):
                    logger.debug(
                        f"Skipping index {index_name} for row {row_index} - "
                        f"empty index value"
                    )
                    continue

                try:
                    self.session.execute(
                        insert_cql,
                        (collection, schema_name, index_name, index_value, data_map, source)
                    )
                    rows_written += 1
                except Exception as e:
                    logger.error(
                        f"Failed to insert row {row_index} for index {index_name}: {e}",
                        exc_info=True
                    )
                    raise

        logger.info(
            f"Wrote {rows_written} index entries for {len(obj.values)} rows "
            f"({len(index_names)} indexes per row)"
        )

    async def create_collection(self, user: str, collection: str, metadata: dict):
        """Create/verify collection exists in Cassandra row store"""
        # Connect if not already connected
        self.connect_cassandra()

        # Ensure tables exist
        self.ensure_tables(user)

        logger.info(f"Collection {collection} ready for user {user}")

    async def delete_collection(self, user: str, collection: str):
        """Delete all data for a specific collection using partition tracking"""
        # Connect if not already connected
        self.connect_cassandra()

        safe_keyspace = self.sanitize_name(user)

        # Check if keyspace exists
        if user not in self.known_keyspaces:
            check_keyspace_cql = """
            SELECT keyspace_name FROM system_schema.keyspaces
            WHERE keyspace_name = %s
            """
            result = self.session.execute(check_keyspace_cql, (safe_keyspace,))
            if not result.one():
                logger.info(f"Keyspace {safe_keyspace} does not exist, nothing to delete")
                return
            self.known_keyspaces.add(user)

        # Discover all partitions for this collection
        select_partitions_cql = f"""
        SELECT schema_name, index_name FROM {safe_keyspace}.row_partitions
        WHERE collection = %s
        """

        try:
            partitions = self.session.execute(select_partitions_cql, (collection,))
            partition_list = list(partitions)
        except Exception as e:
            logger.error(f"Failed to query partitions for collection {collection}: {e}")
            raise

        # Delete each partition from rows table
        delete_rows_cql = f"""
        DELETE FROM {safe_keyspace}.rows
        WHERE collection = %s AND schema_name = %s AND index_name = %s
        """

        partitions_deleted = 0
        for partition in partition_list:
            try:
                self.session.execute(
                    delete_rows_cql,
                    (collection, partition.schema_name, partition.index_name)
                )
                partitions_deleted += 1
            except Exception as e:
                logger.error(
                    f"Failed to delete partition {collection}/{partition.schema_name}/"
                    f"{partition.index_name}: {e}"
                )
                raise

        # Clean up row_partitions entries
        delete_partitions_cql = f"""
        DELETE FROM {safe_keyspace}.row_partitions
        WHERE collection = %s
        """

        try:
            self.session.execute(delete_partitions_cql, (collection,))
        except Exception as e:
            logger.error(f"Failed to clean up row_partitions for {collection}: {e}")
            raise

        # Clear from local cache
        self.registered_partitions = {
            (col, sch) for col, sch in self.registered_partitions
            if col != collection
        }

        logger.info(
            f"Deleted collection {collection}: {partitions_deleted} partitions "
            f"from keyspace {safe_keyspace}"
        )

    async def delete_collection_schema(self, user: str, collection: str, schema_name: str):
        """Delete all data for a specific collection + schema combination"""
        # Connect if not already connected
        self.connect_cassandra()

        safe_keyspace = self.sanitize_name(user)

        # Discover partitions for this collection + schema
        select_partitions_cql = f"""
        SELECT index_name FROM {safe_keyspace}.row_partitions
        WHERE collection = %s AND schema_name = %s
        """

        try:
            partitions = self.session.execute(select_partitions_cql, (collection, schema_name))
            partition_list = list(partitions)
        except Exception as e:
            logger.error(
                f"Failed to query partitions for {collection}/{schema_name}: {e}"
            )
            raise

        # Delete each partition from rows table
        delete_rows_cql = f"""
        DELETE FROM {safe_keyspace}.rows
        WHERE collection = %s AND schema_name = %s AND index_name = %s
        """

        partitions_deleted = 0
        for partition in partition_list:
            try:
                self.session.execute(
                    delete_rows_cql,
                    (collection, schema_name, partition.index_name)
                )
                partitions_deleted += 1
            except Exception as e:
                logger.error(
                    f"Failed to delete partition {collection}/{schema_name}/"
                    f"{partition.index_name}: {e}"
                )
                raise

        # Clean up row_partitions entries for this schema
        delete_partitions_cql = f"""
        DELETE FROM {safe_keyspace}.row_partitions
        WHERE collection = %s AND schema_name = %s
        """

        try:
            self.session.execute(delete_partitions_cql, (collection, schema_name))
        except Exception as e:
            logger.error(
                f"Failed to clean up row_partitions for {collection}/{schema_name}: {e}"
            )
            raise

        # Clear from local cache
        self.registered_partitions.discard((collection, schema_name))

        logger.info(
            f"Deleted {collection}/{schema_name}: {partitions_deleted} partitions "
            f"from keyspace {safe_keyspace}"
        )

    def close(self):
        """Clean up Cassandra connections"""
        if self.cluster:
            self.cluster.shutdown()
            logger.info("Closed Cassandra connection")

    @staticmethod
    def add_args(parser):
        """Add command-line arguments"""

        FlowProcessor.add_args(parser)
        add_cassandra_args(parser)

        parser.add_argument(
            '--config-type',
            default='schema',
            help='Configuration type prefix for schemas (default: schema)'
        )


def run():
    """Entry point for rows-write-cassandra command"""
    Processor.launch(default_ident, __doc__)
