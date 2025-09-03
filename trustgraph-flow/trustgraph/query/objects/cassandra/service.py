"""
Objects query service using GraphQL. Input is a GraphQL query with variables.
Output is GraphQL response data with any errors.
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider

import strawberry
from strawberry import Schema
from strawberry.types import Info
from strawberry.scalars import JSON

from .... schema import ObjectsQueryRequest, ObjectsQueryResponse, GraphQLError
from .... schema import Error, RowSchema, Field as SchemaField
from .... base import FlowProcessor, ConsumerSpec, ProducerSpec

# Module logger
logger = logging.getLogger(__name__)

default_ident = "objects-query"
default_graph_host = 'localhost'


class Processor(FlowProcessor):
    
    def __init__(self, **params):
        
        id = params.get("id", default_ident)
        
        # Cassandra connection parameters
        self.graph_host = params.get("graph_host", default_graph_host)
        self.graph_username = params.get("graph_username", None)
        self.graph_password = params.get("graph_password", None)
        
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
                name = "request",
                schema = ObjectsQueryRequest,
                handler = self.on_message
            )
        )
        
        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = ObjectsQueryResponse,
            )
        )
        
        # Register config handler for schema updates
        self.register_config_handler(self.on_schema_config)
        
        # Schema storage: name -> RowSchema
        self.schemas: Dict[str, RowSchema] = {}
        
        # GraphQL schema
        self.graphql_schema: Optional[Schema] = None
        
        # GraphQL types cache
        self.graphql_types: Dict[str, type] = {}
        
        # Cassandra session
        self.cluster = None
        self.session = None
        
        # Known keyspaces and tables
        self.known_keyspaces: Set[str] = set()
        self.known_tables: Dict[str, Set[str]] = {}

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
                    contact_points=[self.graph_host],
                    auth_provider=auth_provider
                )
            else:
                self.cluster = Cluster(contact_points=[self.graph_host])
            
            self.session = self.cluster.connect()
            logger.info(f"Connected to Cassandra cluster at {self.graph_host}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Cassandra: {e}", exc_info=True)
            raise

    def sanitize_name(self, name: str) -> str:
        """Sanitize names for Cassandra compatibility"""
        import re
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        if safe_name and not safe_name[0].isalpha():
            safe_name = 'o_' + safe_name
        return safe_name.lower()

    def sanitize_table(self, name: str) -> str:
        """Sanitize table names for Cassandra compatibility"""
        import re
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        safe_name = 'o_' + safe_name
        return safe_name.lower()

    async def on_schema_config(self, config, version):
        """Handle schema configuration updates"""
        logger.info(f"Loading schema configuration version {version}")
        
        # Clear existing schemas
        self.schemas = {}
        self.graphql_types = {}
        
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
                    field = SchemaField(
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
        
        # Regenerate GraphQL schema
        self.generate_graphql_schema()

    def get_python_type(self, field_type: str):
        """Convert schema field type to Python type for GraphQL"""
        type_mapping = {
            "string": str,
            "integer": int,
            "float": float,
            "boolean": bool,
            "timestamp": str,  # Use string for timestamps in GraphQL
            "date": str,
            "time": str,
            "uuid": str
        }
        return type_mapping.get(field_type, str)

    def create_graphql_type(self, schema_name: str, row_schema: RowSchema) -> type:
        """Create a GraphQL type from a RowSchema"""
        
        # Create annotations for the GraphQL type
        annotations = {}
        defaults = {}
        
        for field in row_schema.fields:
            python_type = self.get_python_type(field.type)
            
            # Make field optional if not required
            if not field.required and not field.primary:
                annotations[field.name] = Optional[python_type]
                defaults[field.name] = None
            else:
                annotations[field.name] = python_type
        
        # Create the class dynamically
        type_name = f"{schema_name.capitalize()}Type"
        graphql_class = type(
            type_name,
            (),
            {
                "__annotations__": annotations,
                **defaults
            }
        )
        
        # Apply strawberry decorator
        return strawberry.type(graphql_class)

    def generate_graphql_schema(self):
        """Generate GraphQL schema from loaded schemas"""
        if not self.schemas:
            logger.warning("No schemas loaded, cannot generate GraphQL schema")
            self.graphql_schema = None
            return
        
        # Create GraphQL types for each schema
        for schema_name, row_schema in self.schemas.items():
            graphql_type = self.create_graphql_type(schema_name, row_schema)
            self.graphql_types[schema_name] = graphql_type
        
        # Store resolvers separately to avoid closure issues
        self.resolvers = {}
        
        # Create the Query class with resolvers
        query_dict = {'__annotations__': {}}
        
        for schema_name, row_schema in self.schemas.items():
            graphql_type = self.graphql_types[schema_name]
            
            # Create resolver function for this schema
            def make_resolver(s_name, r_schema, g_type):
                async def resolver(
                    info: Info,
                    collection: str,
                    limit: Optional[int] = 100
                ) -> List[g_type]:
                    # Get the processor instance from context
                    processor = info.context["processor"]
                    user = info.context["user"]
                    
                    # Query Cassandra
                    results = await processor.query_cassandra(
                        user, collection, s_name, r_schema, 
                        {}, limit
                    )
                    
                    # Convert to GraphQL types
                    graphql_results = []
                    for row in results:
                        graphql_obj = g_type(**row)
                        graphql_results.append(graphql_obj)
                    
                    return graphql_results
                
                return resolver
            
            # Add resolver to query
            resolver_name = f"{schema_name}_objects"
            resolver_func = make_resolver(schema_name, row_schema, graphql_type)
            self.resolvers[resolver_name] = resolver_func
            
            # Add field to query dictionary
            query_dict[resolver_name] = strawberry.field(resolver=resolver_func)
            query_dict['__annotations__'][resolver_name] = List[graphql_type]
        
        # Create the Query class
        Query = type('Query', (), query_dict)
        Query = strawberry.type(Query)
        
        # Create the schema with auto_camel_case disabled to keep snake_case field names
        self.graphql_schema = strawberry.Schema(
            query=Query,
            config=strawberry.schema.config.StrawberryConfig(auto_camel_case=False)
        )
        logger.info(f"Generated GraphQL schema with {len(self.schemas)} types")

    async def query_cassandra(
        self, 
        user: str, 
        collection: str, 
        schema_name: str,
        row_schema: RowSchema,
        filters: Dict[str, Any],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Execute a query against Cassandra"""
        
        # Connect if needed
        self.connect_cassandra()
        
        # Build the query
        keyspace = self.sanitize_name(user)
        table = self.sanitize_table(schema_name)
        
        # Start with basic SELECT
        query = f"SELECT * FROM {keyspace}.{table}"
        
        # Add WHERE clauses
        where_clauses = [f"collection = %s"]
        params = [collection]
        
        # Add filters for indexed or primary key fields
        for field_name, value in filters.items():
            if value is not None:
                # Find the field in schema
                schema_field = None
                for f in row_schema.fields:
                    if f.name == field_name:
                        schema_field = f
                        break
                
                if schema_field and (schema_field.indexed or schema_field.primary):
                    safe_field = self.sanitize_name(field_name)
                    where_clauses.append(f"{safe_field} = %s")
                    params.append(value)
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        # Add limit first (must come before ALLOW FILTERING)
        if limit:
            query += f" LIMIT {limit}"
        
        # Add ALLOW FILTERING for now (should optimize with proper indexes later)
        query += " ALLOW FILTERING"
        
        # Execute query
        try:
            result = self.session.execute(query, params)
            
            # Convert rows to dicts
            results = []
            for row in result:
                row_dict = {}
                for field in row_schema.fields:
                    safe_field = self.sanitize_name(field.name)
                    if hasattr(row, safe_field):
                        value = getattr(row, safe_field)
                        # Use original field name in result
                        row_dict[field.name] = value
                results.append(row_dict)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to query Cassandra: {e}", exc_info=True)
            raise

    async def execute_graphql_query(
        self, 
        query: str, 
        variables: Dict[str, Any],
        operation_name: Optional[str],
        user: str,
        collection: str
    ) -> Dict[str, Any]:
        """Execute a GraphQL query"""
        
        if not self.graphql_schema:
            raise RuntimeError("No GraphQL schema available - no schemas loaded")
        
        # Create context for the query
        context = {
            "processor": self,
            "user": user,
            "collection": collection
        }
        
        # Execute the query
        result = await self.graphql_schema.execute(
            query,
            variable_values=variables,
            operation_name=operation_name,
            context_value=context
        )
        
        # Build response
        response = {}
        
        if result.data:
            response["data"] = result.data
        else:
            response["data"] = None
        
        if result.errors:
            response["errors"] = [
                {
                    "message": str(error),
                    "path": getattr(error, "path", []),
                    "extensions": getattr(error, "extensions", {})
                }
                for error in result.errors
            ]
        else:
            response["errors"] = []
        
        # Add extensions if any
        if hasattr(result, "extensions") and result.extensions:
            response["extensions"] = result.extensions
        
        return response

    async def on_message(self, msg, consumer, flow):
        """Handle incoming query request"""
        
        try:
            request = msg.value()
            
            # Sender-produced ID
            id = msg.properties()["id"]
            
            logger.debug(f"Handling objects query request {id}...")
            
            # Execute GraphQL query
            result = await self.execute_graphql_query(
                query=request.query,
                variables=dict(request.variables) if request.variables else {},
                operation_name=request.operation_name,
                user=request.user,
                collection=request.collection
            )
            
            # Create response
            graphql_errors = []
            if "errors" in result and result["errors"]:
                for err in result["errors"]:
                    graphql_error = GraphQLError(
                        message=err.get("message", ""),
                        path=err.get("path", []),
                        extensions=err.get("extensions", {})
                    )
                    graphql_errors.append(graphql_error)
            
            response = ObjectsQueryResponse(
                error=None,
                data=json.dumps(result.get("data")) if result.get("data") else "null",
                errors=graphql_errors,
                extensions=result.get("extensions", {})
            )
            
            logger.debug("Sending objects query response...")
            await flow("response").send(response, properties={"id": id})
            
            logger.debug("Objects query request completed")
            
        except Exception as e:
            
            logger.error(f"Exception in objects query service: {e}", exc_info=True)
            
            logger.info("Sending error response...")
            
            response = ObjectsQueryResponse(
                error = Error(
                    type = "objects-query-error",
                    message = str(e),
                ),
                data = None,
                errors = [],
                extensions = {}
            )
            
            await flow("response").send(response, properties={"id": id})

    def close(self):
        """Clean up Cassandra connections"""
        if self.cluster:
            self.cluster.shutdown()
            logger.info("Closed Cassandra connection")

    @staticmethod
    def add_args(parser):
        """Add command-line arguments"""
        
        FlowProcessor.add_args(parser)
        
        parser.add_argument(
            '-g', '--graph-host',
            default=default_graph_host,
            help=f'Cassandra host (default: {default_graph_host})'
        )
        
        parser.add_argument(
            '--graph-username',
            default=None,
            help='Cassandra username'
        )
        
        parser.add_argument(
            '--graph-password',
            default=None,
            help='Cassandra password'
        )
        
        parser.add_argument(
            '--config-type',
            default='schema',
            help='Configuration type prefix for schemas (default: schema)'
        )

def run():
    """Entry point for objects-query-graphql-cassandra command"""
    Processor.launch(default_ident, __doc__)

