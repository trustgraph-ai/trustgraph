"""
Objects query service using GraphQL. Input is a GraphQL query with variables.
Output is GraphQL response data with any errors.
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List, Set
from enum import Enum
from dataclasses import dataclass, field
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider

import strawberry
from strawberry import Schema
from strawberry.types import Info
from strawberry.scalars import JSON
from strawberry.tools import create_type

from .... schema import ObjectsQueryRequest, ObjectsQueryResponse, GraphQLError
from .... schema import Error, RowSchema, Field as SchemaField
from .... base import FlowProcessor, ConsumerSpec, ProducerSpec
from .... base.cassandra_config import add_cassandra_args, resolve_cassandra_config

# Module logger
logger = logging.getLogger(__name__)

default_ident = "objects-query"

# GraphQL filter input types
@strawberry.input
class IntFilter:
    eq: Optional[int] = None
    gt: Optional[int] = None
    gte: Optional[int] = None
    lt: Optional[int] = None
    lte: Optional[int] = None
    in_: Optional[List[int]] = strawberry.field(name="in", default=None)
    not_: Optional[int] = strawberry.field(name="not", default=None)
    not_in: Optional[List[int]] = None

@strawberry.input
class StringFilter:
    eq: Optional[str] = None
    contains: Optional[str] = None
    startsWith: Optional[str] = None
    endsWith: Optional[str] = None
    in_: Optional[List[str]] = strawberry.field(name="in", default=None)
    not_: Optional[str] = strawberry.field(name="not", default=None)
    not_in: Optional[List[str]] = None

@strawberry.input  
class FloatFilter:
    eq: Optional[float] = None
    gt: Optional[float] = None
    gte: Optional[float] = None
    lt: Optional[float] = None
    lte: Optional[float] = None
    in_: Optional[List[float]] = strawberry.field(name="in", default=None)
    not_: Optional[float] = strawberry.field(name="not", default=None)
    not_in: Optional[List[float]] = None


class Processor(FlowProcessor):
    
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

    def parse_filter_key(self, filter_key: str) -> tuple[str, str]:
        """Parse GraphQL filter key into field name and operator"""
        if not filter_key:
            return ("", "eq")
            
        # Support common GraphQL filter patterns:
        # field_name -> (field_name, "eq")
        # field_name_gt -> (field_name, "gt") 
        # field_name_gte -> (field_name, "gte")
        # field_name_lt -> (field_name, "lt")
        # field_name_lte -> (field_name, "lte")
        # field_name_in -> (field_name, "in")
        
        operators = ["_gte", "_lte", "_gt", "_lt", "_in", "_eq"]
        
        for op_suffix in operators:
            if filter_key.endswith(op_suffix):
                field_name = filter_key[:-len(op_suffix)]
                operator = op_suffix[1:]  # Remove the leading underscore
                return (field_name, operator)
        
        # Default to equality if no operator suffix found
        return (filter_key, "eq")

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

    def create_filter_type_for_schema(self, schema_name: str, row_schema: RowSchema):
        """Create a dynamic filter input type for a schema"""
        # Create the filter type dynamically
        filter_type_name = f"{schema_name.capitalize()}Filter"
        
        # Add __annotations__ and defaults for the fields
        annotations = {}
        defaults = {}
        
        logger.info(f"Creating filter type {filter_type_name} for schema {schema_name}")
        
        for field in row_schema.fields:
            logger.info(f"Field {field.name}: type={field.type}, indexed={field.indexed}, primary={field.primary}")
            
            # Allow filtering on any field for now, not just indexed/primary
            # if field.indexed or field.primary:
            if field.type == "integer":
                annotations[field.name] = Optional[IntFilter]
                defaults[field.name] = None
                logger.info(f"Added IntFilter for {field.name}")
            elif field.type == "float": 
                annotations[field.name] = Optional[FloatFilter]
                defaults[field.name] = None
                logger.info(f"Added FloatFilter for {field.name}")
            elif field.type == "string":
                annotations[field.name] = Optional[StringFilter]
                defaults[field.name] = None
                logger.info(f"Added StringFilter for {field.name}")
        
        logger.info(f"Filter type {filter_type_name} will have fields: {list(annotations.keys())}")
        
        # Create the class dynamically
        FilterType = type(
            filter_type_name,
            (),
            {
                "__annotations__": annotations,
                **defaults
            }
        )
        
        # Apply strawberry input decorator
        FilterType = strawberry.input(FilterType)
        
        return FilterType

    def create_sort_direction_enum(self):
        """Create sort direction enum"""
        @strawberry.enum
        class SortDirection(Enum):
            ASC = "asc"
            DESC = "desc"
        
        return SortDirection

    def parse_idiomatic_where_clause(self, where_obj) -> Dict[str, Any]:
        """Parse the idiomatic nested filter structure"""
        if not where_obj:
            return {}
        
        conditions = {}
        
        logger.info(f"Parsing where clause: {where_obj}")
        
        for field_name, filter_obj in where_obj.__dict__.items():
            if filter_obj is None:
                continue
                
            logger.info(f"Processing field {field_name} with filter_obj: {filter_obj}")
                
            if hasattr(filter_obj, '__dict__'):
                # This is a filter object (StringFilter, IntFilter, etc.)
                for operator, value in filter_obj.__dict__.items():
                    if value is not None:
                        logger.info(f"Found operator {operator} with value {value}")
                        # Map GraphQL operators to our internal format
                        if operator == "eq":
                            conditions[field_name] = value
                        elif operator in ["gt", "gte", "lt", "lte"]:
                            conditions[f"{field_name}_{operator}"] = value
                        elif operator == "in_":
                            conditions[f"{field_name}_in"] = value
                        elif operator == "contains":
                            conditions[f"{field_name}_contains"] = value
        
        logger.info(f"Final parsed conditions: {conditions}")
        return conditions

    def generate_graphql_schema(self):
        """Generate GraphQL schema from loaded schemas using dynamic filter types"""
        if not self.schemas:
            logger.warning("No schemas loaded, cannot generate GraphQL schema")
            self.graphql_schema = None
            return
        
        # Create GraphQL types and filter types for each schema
        filter_types = {}
        sort_direction_enum = self.create_sort_direction_enum()
        
        for schema_name, row_schema in self.schemas.items():
            graphql_type = self.create_graphql_type(schema_name, row_schema)
            filter_type = self.create_filter_type_for_schema(schema_name, row_schema)
            
            self.graphql_types[schema_name] = graphql_type
            filter_types[schema_name] = filter_type
        
        # Create the Query class with resolvers
        query_dict = {'__annotations__': {}}
        
        for schema_name, row_schema in self.schemas.items():
            graphql_type = self.graphql_types[schema_name]
            filter_type = filter_types[schema_name]
            
            # Create resolver function for this schema
            def make_resolver(s_name, r_schema, g_type, f_type, sort_enum):
                async def resolver(
                    info: Info,
                    where: Optional[f_type] = None,
                    order_by: Optional[str] = None,
                    direction: Optional[sort_enum] = None,
                    limit: Optional[int] = 100
                ) -> List[g_type]:
                    # Get the processor instance from context
                    processor = info.context["processor"]
                    user = info.context["user"]
                    collection = info.context["collection"]
                    
                    # Parse the idiomatic where clause
                    filters = processor.parse_idiomatic_where_clause(where)
                    
                    # Query Cassandra
                    results = await processor.query_cassandra(
                        user, collection, s_name, r_schema, 
                        filters, limit, order_by, direction
                    )
                    
                    # Convert to GraphQL types
                    graphql_results = []
                    for row in results:
                        graphql_obj = g_type(**row)
                        graphql_results.append(graphql_obj)
                    
                    return graphql_results
                
                return resolver
            
            # Add resolver to query
            resolver_name = schema_name
            resolver_func = make_resolver(schema_name, row_schema, graphql_type, filter_type, sort_direction_enum)
            
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
        limit: int,
        order_by: Optional[str] = None,
        direction: Optional[Any] = None
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
        for filter_key, value in filters.items():
            if value is not None:
                # Parse field name and operator from filter key
                logger.debug(f"Parsing filter key: '{filter_key}' (type: {type(filter_key)})")
                result = self.parse_filter_key(filter_key)
                logger.debug(f"parse_filter_key returned: {result} (type: {type(result)}, len: {len(result) if hasattr(result, '__len__') else 'N/A'})")
                
                if not result or len(result) != 2:
                    logger.error(f"parse_filter_key returned invalid result: {result}")
                    continue  # Skip this filter
                    
                field_name, operator = result
                
                # Find the field in schema
                schema_field = None
                for f in row_schema.fields:
                    if f.name == field_name:
                        schema_field = f
                        break
                
                if schema_field:
                    safe_field = self.sanitize_name(field_name)
                    
                    # Build WHERE clause based on operator
                    if operator == "eq":
                        where_clauses.append(f"{safe_field} = %s")
                        params.append(value)
                    elif operator == "gt":
                        where_clauses.append(f"{safe_field} > %s")
                        params.append(value)
                    elif operator == "gte":
                        where_clauses.append(f"{safe_field} >= %s")
                        params.append(value)
                    elif operator == "lt":
                        where_clauses.append(f"{safe_field} < %s")
                        params.append(value)
                    elif operator == "lte":
                        where_clauses.append(f"{safe_field} <= %s")
                        params.append(value)
                    elif operator == "in":
                        if isinstance(value, list):
                            placeholders = ",".join(["%s"] * len(value))
                            where_clauses.append(f"{safe_field} IN ({placeholders})")
                            params.extend(value)
                    else:
                        # Default to equality for unknown operators
                        where_clauses.append(f"{safe_field} = %s")
                        params.append(value)
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        # Add ORDER BY if requested (will try Cassandra first, then fall back to post-query sort)
        cassandra_order_by_added = False
        if order_by and direction:
            # Validate that order_by field exists in schema
            order_field_exists = any(f.name == order_by for f in row_schema.fields)
            if order_field_exists:
                safe_order_field = self.sanitize_name(order_by)
                direction_str = "ASC" if direction.value == "asc" else "DESC"
                # Add ORDER BY - if Cassandra rejects it, we'll catch the error during execution
                query += f" ORDER BY {safe_order_field} {direction_str}"
        
        # Add limit first (must come before ALLOW FILTERING)
        if limit:
            query += f" LIMIT {limit}"
        
        # Add ALLOW FILTERING for now (should optimize with proper indexes later)
        query += " ALLOW FILTERING"
        
        # Execute query
        try:
            result = self.session.execute(query, params)
            cassandra_order_by_added = True  # If we get here, Cassandra handled ORDER BY
        except Exception as e:
            # If ORDER BY fails, try without it
            if order_by and direction and "ORDER BY" in query:
                logger.info(f"Cassandra rejected ORDER BY, falling back to post-query sorting: {e}")
                # Remove ORDER BY clause and retry
                query_parts = query.split(" ORDER BY ")
                if len(query_parts) == 2:
                    query_without_order = query_parts[0] + " LIMIT " + str(limit) + " ALLOW FILTERING" if limit else " ALLOW FILTERING"
                    result = self.session.execute(query_without_order, params)
                    cassandra_order_by_added = False
                else:
                    raise
            else:
                raise
        
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
        
        # Post-query sorting if Cassandra didn't handle ORDER BY
        if order_by and direction and not cassandra_order_by_added:
            reverse_order = (direction.value == "desc")
            try:
                results.sort(key=lambda x: x.get(order_by, 0), reverse=reverse_order)
            except Exception as e:
                logger.warning(f"Failed to sort results by {order_by}: {e}")
        
        return results

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
        add_cassandra_args(parser)
        
        parser.add_argument(
            '--config-type',
            default='schema',
            help='Configuration type prefix for schemas (default: schema)'
        )

def run():
    """Entry point for objects-query-graphql-cassandra command"""
    Processor.launch(default_ident, __doc__)

