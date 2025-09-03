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
from .... base import FlowProcessor, ConsumerSpec
from .... base.cassandra_config import add_cassandra_args, resolve_cassandra_config

# Module logger
logger = logging.getLogger(__name__)

default_ident = "objects-write"

class Processor(FlowProcessor):

    def __init__(self, **params):
        
        id = params.get("id", default_ident)
        
        # Use new parameter names, fall back to old for compatibility
        cassandra_host = params.get("cassandra_host", params.get("graph_host"))
        cassandra_username = params.get("cassandra_username", params.get("graph_username"))
        cassandra_password = params.get("cassandra_password", params.get("graph_password"))
        
        # Resolve configuration with environment variable fallback
        hosts, username, password = resolve_cassandra_config(
            host=cassandra_host,
            username=cassandra_username,
            password=cassandra_password
        )
        
        # Store resolved configuration
        self.graph_host = hosts  # Store as list
        self.graph_username = username
        self.graph_password = password
        
        # Config key for schemas
        self.config_key = params.get("config_type", "schema")
        
        super(Processor, self).__init__(
            **params | {
                "id": id,
                "config-type": self.config_key,
            }
        )
        
        self.register_specification(
            ConsumerSpec(
                name = "input",
                schema = ExtractedObject,
                handler = self.on_object
            )
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
            if self.graph_username and self.graph_password:
                auth_provider = PlainTextAuthProvider(
                    username=self.graph_username,
                    password=self.graph_password
                )
                self.cluster = Cluster(
                    contact_points=self.graph_host,
                    auth_provider=auth_provider
                )
            else:
                self.cluster = Cluster(contact_points=self.graph_host)
            
            self.session = self.cluster.connect()
            logger.info(f"Connected to Cassandra cluster at {self.graph_host}")
            
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
        logger.info(f"Storing object for schema {obj.schema_name} from {obj.metadata.id}")
        
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
        
        # Build column names and values
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
        
        # Process fields
        for field in schema.fields:
            safe_field_name = self.sanitize_name(field.name)
            raw_value = obj.values.get(field.name)
            
            # Handle required fields
            if field.required and raw_value is None:
                logger.warning(f"Required field {field.name} is missing in object")
                # Continue anyway - Cassandra doesn't enforce NOT NULL
            
            # Check if primary key field is NULL
            if field.primary and raw_value is None:
                logger.error(f"Primary key field {field.name} cannot be NULL - skipping object")
                return
            
            # Convert value to appropriate type
            converted_value = self.convert_value(raw_value, field.type)
            
            columns.append(safe_field_name)
            values.append(converted_value)
            placeholders.append("%s")
        
        # Build and execute insert query
        insert_cql = f"""
        INSERT INTO {safe_keyspace}.{safe_table} ({', '.join(columns)})
        VALUES ({', '.join(placeholders)})
        """
        
        # Debug: Show data being inserted
        logger.debug(f"Storing {obj.schema_name}: {dict(zip(columns, values))}")
        
        if len(columns) != len(values) or len(columns) != len(placeholders):
            raise ValueError(f"Mismatch in counts - columns: {len(columns)}, values: {len(values)}, placeholders: {len(placeholders)}")
        
        try:
            # Convert to tuple - Cassandra driver requires tuple for parameters
            self.session.execute(insert_cql, tuple(values))
        except Exception as e:
            logger.error(f"Failed to insert object: {e}", exc_info=True)
            raise

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
