"""
Object writer for Cassandra. Input is ExtractedObject. 
Writes structured objects to Cassandra tables based on schema definitions.
"""

import json
import logging
from typing import Dict, Set, Optional, Any
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.cqlengine import connection
from cassandra import ConsistencyLevel

from .... schema import ExtractedObject
from .... schema import RowSchema, Field
from .... schema import StorageManagementRequest, StorageManagementResponse
from .... schema import object_storage_management_topic, storage_management_response_topic
from .... base import FlowProcessor, ConsumerSpec, ProducerSpec
from .... base.cassandra_config import add_cassandra_args, resolve_cassandra_config

# Module logger
logger = logging.getLogger(__name__)

default_ident = "objects-write"

class Processor(FlowProcessor):

    def __init__(self, **params):
        
        id = params.get("id", default_ident)
        
        # Get Cassandra parameters
        cassandra_host = params.get("cassandra_host")
        cassandra_username = params.get("cassandra_username")
        cassandra_password = params.get("cassandra_password")
        
        # Resolve configuration with environment variable fallback
        hosts, username, password = resolve_cassandra_config(
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
                name = "input",
                schema = ExtractedObject,
                handler = self.on_object
            )
        )

        # Set up storage management consumer and producer directly
        # (FlowProcessor doesn't support topic-based specs outside of flows)
        from .... base import Consumer, Producer, ConsumerMetrics, ProducerMetrics

        storage_request_metrics = ConsumerMetrics(
            processor=self.id, flow=None, name="storage-request"
        )
        storage_response_metrics = ProducerMetrics(
            processor=self.id, flow=None, name="storage-response"
        )

        # Create storage management consumer
        self.storage_request_consumer = Consumer(
            taskgroup=self.taskgroup,
            client=self.pulsar_client,
            flow=None,
            topic=object_storage_management_topic,
            subscriber=f"{id}-storage",
            schema=StorageManagementRequest,
            handler=self.on_storage_management,
            metrics=storage_request_metrics,
        )

        # Create storage management response producer
        self.storage_response_producer = Producer(
            client=self.pulsar_client,
            topic=storage_management_response_topic,
            schema=StorageManagementResponse,
            metrics=storage_response_metrics,
        )

        # Register config handler for schema updates
        self.register_config_handler(self.on_schema_config)
        
        # Cache of known keyspaces/tables
        self.known_keyspaces: Set[str] = set()
        self.known_tables: Dict[str, Set[str]] = {}  # keyspace -> set of tables
        
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
            self.known_tables[keyspace] = set()
            logger.info(f"Ensured keyspace exists: {safe_keyspace}")
        except Exception as e:
            logger.error(f"Failed to create keyspace {safe_keyspace}: {e}", exc_info=True)
            raise

    def get_cassandra_type(self, field_type: str, size: int = 0) -> str:
        """Convert schema field type to Cassandra type"""
        # Handle None size
        if size is None:
            size = 0
            
        type_mapping = {
            "string": "text",
            "integer": "bigint" if size > 4 else "int",
            "float": "double" if size > 4 else "float",
            "boolean": "boolean",
            "timestamp": "timestamp",
            "date": "date",
            "time": "time",
            "uuid": "uuid"
        }
        
        return type_mapping.get(field_type, "text")

    def sanitize_name(self, name: str) -> str:
        """Sanitize names for Cassandra compatibility"""
        # Replace non-alphanumeric characters with underscore
        import re
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # Ensure it starts with a letter
        if safe_name and not safe_name[0].isalpha():
            safe_name = 'o_' + safe_name
        return safe_name.lower()

    def sanitize_table(self, name: str) -> str:
        """Sanitize names for Cassandra compatibility"""
        # Replace non-alphanumeric characters with underscore
        import re
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # Ensure it starts with a letter
        safe_name = 'o_' + safe_name
        return safe_name.lower()

    def ensure_table(self, keyspace: str, table_name: str, schema: RowSchema):
        """Ensure table exists with proper structure"""
        table_key = f"{keyspace}.{table_name}"
        if table_key in self.known_tables.get(keyspace, set()):
            return
            
        # Ensure keyspace exists first
        self.ensure_keyspace(keyspace)
        
        safe_keyspace = self.sanitize_name(keyspace)
        safe_table = self.sanitize_table(table_name)
        
        # Build column definitions
        columns = ["collection text"]  # Collection is always part of table
        primary_key_fields = []
        clustering_fields = []
        
        for field in schema.fields:
            safe_field_name = self.sanitize_name(field.name)
            cassandra_type = self.get_cassandra_type(field.type, field.size)
            columns.append(f"{safe_field_name} {cassandra_type}")
            
            if field.primary:
                primary_key_fields.append(safe_field_name)
        
        # Build primary key - collection is always first in partition key
        if primary_key_fields:
            primary_key = f"PRIMARY KEY ((collection, {', '.join(primary_key_fields)}))"
        else:
            # If no primary key defined, use collection and a synthetic id
            columns.append("synthetic_id uuid")
            primary_key = "PRIMARY KEY ((collection, synthetic_id))"
        
        # Create table
        create_table_cql = f"""
        CREATE TABLE IF NOT EXISTS {safe_keyspace}.{safe_table} (
            {', '.join(columns)},
            {primary_key}
        )
        """
        
        try:
            self.session.execute(create_table_cql)
            self.known_tables[keyspace].add(table_key)
            logger.info(f"Ensured table exists: {safe_keyspace}.{safe_table}")
            
            # Create secondary indexes for indexed fields
            for field in schema.fields:
                if field.indexed and not field.primary:
                    safe_field_name = self.sanitize_name(field.name)
                    index_name = f"{safe_table}_{safe_field_name}_idx"
                    create_index_cql = f"""
                    CREATE INDEX IF NOT EXISTS {index_name}
                    ON {safe_keyspace}.{safe_table} ({safe_field_name})
                    """
                    try:
                        self.session.execute(create_index_cql)
                        logger.info(f"Created index: {index_name}")
                    except Exception as e:
                        logger.warning(f"Failed to create index {index_name}: {e}")
                        
        except Exception as e:
            logger.error(f"Failed to create table {safe_keyspace}.{safe_table}: {e}", exc_info=True)
            raise

    def convert_value(self, value: Any, field_type: str) -> Any:
        """Convert value to appropriate type for Cassandra"""
        if value is None:
            return None
            
        try:
            if field_type == "integer":
                return int(value)
            elif field_type == "float":
                return float(value)
            elif field_type == "boolean":
                if isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes')
                return bool(value)
            elif field_type == "timestamp":
                # Handle timestamp conversion if needed
                return value
            else:
                return str(value)
        except Exception as e:
            logger.warning(f"Failed to convert value {value} to type {field_type}: {e}")
            return str(value)

    async def on_object(self, msg, consumer, flow):
        """Process incoming ExtractedObject and store in Cassandra"""
        
        obj = msg.value()
        logger.info(f"Storing {len(obj.values)} objects for schema {obj.schema_name} from {obj.metadata.id}")
        
        # Get schema definition
        schema = self.schemas.get(obj.schema_name)
        if not schema:
            logger.warning(f"No schema found for {obj.schema_name} - skipping")
            return
        
        # Ensure table exists
        keyspace = obj.metadata.user
        table_name = obj.schema_name
        self.ensure_table(keyspace, table_name, schema)
        
        # Prepare data for insertion
        safe_keyspace = self.sanitize_name(keyspace)
        safe_table = self.sanitize_table(table_name)
        
        # Process each object in the batch
        for obj_index, value_map in enumerate(obj.values):
            # Build column names and values for this object
            columns = ["collection"]
            values = [obj.metadata.collection]
            placeholders = ["%s"]
            
            # Check if we need a synthetic ID
            has_primary_key = any(field.primary for field in schema.fields)
            if not has_primary_key:
                import uuid
                columns.append("synthetic_id")
                values.append(uuid.uuid4())
                placeholders.append("%s")
            
            # Process fields for this object
            skip_object = False
            for field in schema.fields:
                safe_field_name = self.sanitize_name(field.name)
                raw_value = value_map.get(field.name)
                
                # Handle required fields
                if field.required and raw_value is None:
                    logger.warning(f"Required field {field.name} is missing in object {obj_index}")
                    # Continue anyway - Cassandra doesn't enforce NOT NULL
                
                # Check if primary key field is NULL
                if field.primary and raw_value is None:
                    logger.error(f"Primary key field {field.name} cannot be NULL - skipping object {obj_index}")
                    skip_object = True
                    break
                
                # Convert value to appropriate type
                converted_value = self.convert_value(raw_value, field.type)
                
                columns.append(safe_field_name)
                values.append(converted_value)
                placeholders.append("%s")
            
            # Skip this object if primary key validation failed
            if skip_object:
                continue
            
            # Build and execute insert query for this object
            insert_cql = f"""
            INSERT INTO {safe_keyspace}.{safe_table} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            """
            
            # Debug: Show data being inserted
            logger.debug(f"Storing {obj.schema_name} object {obj_index}: {dict(zip(columns, values))}")
            
            if len(columns) != len(values) or len(columns) != len(placeholders):
                raise ValueError(f"Mismatch in counts - columns: {len(columns)}, values: {len(values)}, placeholders: {len(placeholders)}")
            
            try:
                # Convert to tuple - Cassandra driver requires tuple for parameters
                self.session.execute(insert_cql, tuple(values))
            except Exception as e:
                logger.error(f"Failed to insert object {obj_index}: {e}", exc_info=True)
                raise

    async def on_storage_management(self, msg, consumer, flow):
        """Handle storage management requests for collection operations"""
        logger.info(f"Received storage management request: {msg.operation} for {msg.user}/{msg.collection}")

        try:
            if msg.operation == "delete-collection":
                await self.delete_collection(msg.user, msg.collection)

                # Send success response
                response = StorageManagementResponse(
                    error=None  # No error means success
                )
                await self.storage_response_producer.send(response)
                logger.info(f"Successfully deleted collection {msg.user}/{msg.collection}")
            else:
                logger.warning(f"Unknown storage management operation: {msg.operation}")
                # Send error response
                from .... schema import Error
                response = StorageManagementResponse(
                    error=Error(
                        type="unknown_operation",
                        message=f"Unknown operation: {msg.operation}"
                    )
                )
                await self.storage_response_producer.send(response)

        except Exception as e:
            logger.error(f"Error handling storage management request: {e}", exc_info=True)
            # Send error response
            from .... schema import Error
            response = StorageManagementResponse(
                error=Error(
                    type="processing_error",
                    message=str(e)
                )
            )
            await self.send("storage-response", response)

    async def delete_collection(self, user: str, collection: str):
        """Delete all data for a specific collection"""
        # Connect if not already connected
        self.connect_cassandra()

        # Sanitize names for safety
        safe_keyspace = self.sanitize_name(user)

        # Check if keyspace exists
        if safe_keyspace not in self.known_keyspaces:
            # Query to verify keyspace exists
            check_keyspace_cql = """
            SELECT keyspace_name FROM system_schema.keyspaces
            WHERE keyspace_name = %s
            """
            result = self.session.execute(check_keyspace_cql, (safe_keyspace,))
            if not result.one():
                logger.info(f"Keyspace {safe_keyspace} does not exist, nothing to delete")
                return
            self.known_keyspaces.add(safe_keyspace)

        # Get all tables in the keyspace that might contain collection data
        get_tables_cql = """
        SELECT table_name FROM system_schema.tables
        WHERE keyspace_name = %s
        """

        tables = self.session.execute(get_tables_cql, (safe_keyspace,))
        tables_deleted = 0

        for row in tables:
            table_name = row.table_name

            # Check if the table has a collection column
            check_column_cql = """
            SELECT column_name FROM system_schema.columns
            WHERE keyspace_name = %s AND table_name = %s AND column_name = 'collection'
            """

            result = self.session.execute(check_column_cql, (safe_keyspace, table_name))
            if result.one():
                # Table has collection column, delete data for this collection
                try:
                    delete_cql = f"""
                    DELETE FROM {safe_keyspace}.{table_name}
                    WHERE collection = %s
                    """
                    self.session.execute(delete_cql, (collection,))
                    tables_deleted += 1
                    logger.info(f"Deleted collection {collection} from table {safe_keyspace}.{table_name}")
                except Exception as e:
                    logger.error(f"Failed to delete from table {safe_keyspace}.{table_name}: {e}")
                    raise

        logger.info(f"Deleted collection {collection} from {tables_deleted} tables in keyspace {safe_keyspace}")

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
    """Entry point for objects-write-cassandra command"""
    Processor.launch(default_ident, __doc__)
