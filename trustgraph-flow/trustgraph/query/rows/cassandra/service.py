"""
Row query service using GraphQL. Input is a GraphQL query with variables.
Output is GraphQL response data with any errors.

Queries against the unified 'rows' table with schema:
    - collection: text
    - schema_name: text
    - index_name: text
    - index_value: frozen<list<text>>
    - data: map<text, text>
    - source: text
"""

import json
import logging
import re
from typing import Dict, Any, Optional, List, Set

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider

from .... schema import RowsQueryRequest, RowsQueryResponse, GraphQLError
from .... schema import Error, RowSchema, Field as SchemaField
from .... base import FlowProcessor, ConsumerSpec, ProducerSpec
from .... base.cassandra_config import add_cassandra_args, resolve_cassandra_config

from ... graphql import GraphQLSchemaBuilder, SortDirection

# Module logger
logger = logging.getLogger(__name__)

default_ident = "rows-query"


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
                name="request",
                schema=RowsQueryRequest,
                handler=self.on_message
            )
        )

        self.register_specification(
            ProducerSpec(
                name="response",
                schema=RowsQueryResponse,
            )
        )

        # Register config handler for schema updates
        self.register_config_handler(self.on_schema_config)

        # Schema storage: name -> RowSchema
        self.schemas: Dict[str, RowSchema] = {}

        # GraphQL schema builder and generated schema
        self.schema_builder = GraphQLSchemaBuilder()
        self.graphql_schema = None

        # Cassandra session
        self.cluster = None
        self.session = None

        # Known keyspaces
        self.known_keyspaces: Set[str] = set()

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
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        if safe_name and not safe_name[0].isalpha():
            safe_name = 'r_' + safe_name
        return safe_name.lower()

    async def on_schema_config(self, config, version):
        """Handle schema configuration updates"""
        logger.info(f"Loading schema configuration version {version}")

        # Clear existing schemas
        self.schemas = {}
        self.schema_builder.clear()

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
                self.schema_builder.add_schema(schema_name, row_schema)
                logger.info(f"Loaded schema: {schema_name} with {len(fields)} fields")

            except Exception as e:
                logger.error(f"Failed to parse schema {schema_name}: {e}", exc_info=True)

        logger.info(f"Schema configuration loaded: {len(self.schemas)} schemas")

        # Regenerate GraphQL schema
        self.graphql_schema = self.schema_builder.build(self.query_cassandra)

    def get_index_names(self, schema: RowSchema) -> List[str]:
        """Get all index names for a schema."""
        index_names = []
        for field in schema.fields:
            if field.primary or field.indexed:
                index_names.append(field.name)
        return index_names

    def find_matching_index(
        self,
        schema: RowSchema,
        filters: Dict[str, Any]
    ) -> Optional[tuple]:
        """
        Find an index that can satisfy the query filters.
        Returns (index_name, index_value) if found, None otherwise.

        For exact match queries, we need a filter on an indexed field.
        """
        index_names = self.get_index_names(schema)

        # Look for an exact match filter on an indexed field
        for index_name in index_names:
            if index_name in filters:
                value = filters[index_name]
                # Single field index -> single element list
                index_value = [str(value)]
                return (index_name, index_value)

        return None

    async def query_cassandra(
        self,
        user: str,
        collection: str,
        schema_name: str,
        row_schema: RowSchema,
        filters: Dict[str, Any],
        limit: int,
        order_by: Optional[str] = None,
        direction: Optional[SortDirection] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a query against the unified Cassandra rows table.

        For exact match queries on indexed fields, we can query directly.
        For other queries, we need to scan and post-filter.
        """
        # Connect if needed
        self.connect_cassandra()

        safe_keyspace = self.sanitize_name(user)

        # Try to find an index that matches the filters
        index_match = self.find_matching_index(row_schema, filters)

        results = []

        if index_match:
            # Direct query using index
            index_name, index_value = index_match

            query = f"""
            SELECT data, source FROM {safe_keyspace}.rows
            WHERE collection = %s
              AND schema_name = %s
              AND index_name = %s
              AND index_value = %s
            """
            params = [collection, schema_name, index_name, index_value]

            if limit:
                query += f" LIMIT {limit}"

            try:
                rows = self.session.execute(query, params)
                for row in rows:
                    # Convert data map to dict with proper field names
                    row_dict = dict(row.data) if row.data else {}
                    results.append(row_dict)
            except Exception as e:
                logger.error(f"Failed to query rows: {e}", exc_info=True)
                raise

        else:
            # No direct index match - scan all rows for this schema
            # This is less efficient but necessary for non-indexed queries
            logger.warning(
                f"No index match for filters {filters} - scanning all indexes"
            )

            # Get all index names for this schema
            index_names = self.get_index_names(row_schema)

            if not index_names:
                logger.warning(f"Schema {schema_name} has no indexes")
                return []

            # Query using the first index (arbitrary choice for scan)
            primary_index = index_names[0]

            # We need to scan all values for this index
            # This requires ALLOW FILTERING or a different approach
            query = f"""
            SELECT data, source FROM {safe_keyspace}.rows
            WHERE collection = %s
              AND schema_name = %s
              AND index_name = %s
            ALLOW FILTERING
            """
            params = [collection, schema_name, primary_index]

            try:
                rows = self.session.execute(query, params)

                for row in rows:
                    row_dict = dict(row.data) if row.data else {}

                    # Apply post-filters
                    if self._matches_filters(row_dict, filters, row_schema):
                        results.append(row_dict)

                        if limit and len(results) >= limit:
                            break

            except Exception as e:
                logger.error(f"Failed to scan rows: {e}", exc_info=True)
                raise

        # Post-query sorting if requested
        if order_by and results:
            reverse_order = direction and direction.value == "desc"
            try:
                results.sort(
                    key=lambda x: x.get(order_by, ""),
                    reverse=reverse_order
                )
            except Exception as e:
                logger.warning(f"Failed to sort results by {order_by}: {e}")

        return results

    def _matches_filters(
        self,
        row_dict: Dict[str, Any],
        filters: Dict[str, Any],
        row_schema: RowSchema
    ) -> bool:
        """Check if a row matches the given filters."""
        for filter_key, filter_value in filters.items():
            if filter_value is None:
                continue

            # Parse filter key for operator
            if '_' in filter_key:
                parts = filter_key.rsplit('_', 1)
                if parts[1] in ['gt', 'gte', 'lt', 'lte', 'contains', 'in']:
                    field_name = parts[0]
                    operator = parts[1]
                else:
                    field_name = filter_key
                    operator = 'eq'
            else:
                field_name = filter_key
                operator = 'eq'

            row_value = row_dict.get(field_name)
            if row_value is None:
                return False

            # Convert types for comparison
            try:
                if operator == 'eq':
                    if str(row_value) != str(filter_value):
                        return False
                elif operator == 'gt':
                    if float(row_value) <= float(filter_value):
                        return False
                elif operator == 'gte':
                    if float(row_value) < float(filter_value):
                        return False
                elif operator == 'lt':
                    if float(row_value) >= float(filter_value):
                        return False
                elif operator == 'lte':
                    if float(row_value) > float(filter_value):
                        return False
                elif operator == 'contains':
                    if str(filter_value) not in str(row_value):
                        return False
                elif operator == 'in':
                    if str(row_value) not in [str(v) for v in filter_value]:
                        return False
            except (ValueError, TypeError):
                return False

        return True

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

            response = RowsQueryResponse(
                error=None,
                data=json.dumps(result.get("data")) if result.get("data") else "null",
                errors=graphql_errors,
                extensions=result.get("extensions", {})
            )

            logger.debug("Sending objects query response...")
            await flow("response").send(response, properties={"id": id})

            logger.debug("Objects query request completed")

        except Exception as e:

            logger.error(f"Exception in rows query service: {e}", exc_info=True)

            logger.info("Sending error response...")

            response = RowsQueryResponse(
                error=Error(
                    type="rows-query-error",
                    message=str(e),
                ),
                data=None,
                errors=[],
                extensions={}
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
    """Entry point for rows-query-cassandra command"""
    Processor.launch(default_ident, __doc__)
