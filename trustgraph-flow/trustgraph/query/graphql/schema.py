"""
Dynamic GraphQL schema generation from RowSchema definitions.

Provides a builder class that creates Strawberry GraphQL schemas
from TrustGraph RowSchema definitions, with pluggable query backends.
"""

import logging
from typing import Dict, Any, Optional, List, Callable, Awaitable

import strawberry
from strawberry import Schema
from strawberry.types import Info

from .types import IntFilter, StringFilter, FloatFilter, SortDirection

logger = logging.getLogger(__name__)

# Type alias for query callback function
QueryCallback = Callable[
    [str, str, str, Any, Dict[str, Any], int, Optional[str], Optional[SortDirection]],
    Awaitable[List[Dict[str, Any]]]
]


class GraphQLSchemaBuilder:
    """
    Builds GraphQL schemas from RowSchema definitions.

    This class extracts the GraphQL schema generation logic so it can be
    reused across different query backends (Cassandra, etc.).

    Usage:
        builder = GraphQLSchemaBuilder()

        # Add schemas
        for name, row_schema in schemas.items():
            builder.add_schema(name, row_schema)

        # Build with a query callback
        schema = builder.build(query_callback)
    """

    def __init__(self):
        self.schemas: Dict[str, Any] = {}  # name -> RowSchema
        self.graphql_types: Dict[str, type] = {}
        self.filter_types: Dict[str, type] = {}

    def add_schema(self, name: str, row_schema) -> None:
        """
        Add a RowSchema to the builder.

        Args:
            name: The schema name (used as the GraphQL query field name)
            row_schema: The RowSchema object defining fields
        """
        self.schemas[name] = row_schema
        self.graphql_types[name] = self._create_graphql_type(name, row_schema)
        self.filter_types[name] = self._create_filter_type(name, row_schema)
        logger.debug(f"Added schema {name} with {len(row_schema.fields)} fields")

    def clear(self) -> None:
        """Clear all schemas from the builder."""
        self.schemas = {}
        self.graphql_types = {}
        self.filter_types = {}

    def build(self, query_callback: QueryCallback) -> Optional[Schema]:
        """
        Build the GraphQL schema with the provided query callback.

        The query callback will be invoked when resolving queries, with:
            - user: str
            - collection: str
            - schema_name: str
            - row_schema: RowSchema
            - filters: Dict[str, Any]
            - limit: int
            - order_by: Optional[str]
            - direction: Optional[SortDirection]

        It should return a list of row dictionaries.

        Args:
            query_callback: Async function to execute queries

        Returns:
            Strawberry Schema, or None if no schemas are loaded
        """
        if not self.schemas:
            logger.warning("No schemas loaded, cannot generate GraphQL schema")
            return None

        # Create the Query class with resolvers
        query_dict = {'__annotations__': {}}

        for schema_name, row_schema in self.schemas.items():
            graphql_type = self.graphql_types[schema_name]
            filter_type = self.filter_types[schema_name]

            # Create resolver function for this schema
            resolver_func = self._make_resolver(
                schema_name, row_schema, graphql_type, filter_type, query_callback
            )

            # Add field to query dictionary
            query_dict[schema_name] = strawberry.field(resolver=resolver_func)
            query_dict['__annotations__'][schema_name] = List[graphql_type]

        # Create the Query class
        Query = type('Query', (), query_dict)
        Query = strawberry.type(Query)

        # Create the schema with auto_camel_case disabled to keep snake_case field names
        schema = strawberry.Schema(
            query=Query,
            config=strawberry.schema.config.StrawberryConfig(auto_camel_case=False)
        )
        logger.info(f"Generated GraphQL schema with {len(self.schemas)} types")
        return schema

    def _get_python_type(self, field_type: str):
        """Convert schema field type to Python type for GraphQL."""
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

    def _create_graphql_type(self, schema_name: str, row_schema) -> type:
        """Create a GraphQL output type from a RowSchema."""
        # Create annotations for the GraphQL type
        annotations = {}
        defaults = {}

        for field in row_schema.fields:
            python_type = self._get_python_type(field.type)

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

    def _create_filter_type(self, schema_name: str, row_schema) -> type:
        """Create a dynamic filter input type for a schema."""
        filter_type_name = f"{schema_name.capitalize()}Filter"

        # Add __annotations__ and defaults for the fields
        annotations = {}
        defaults = {}

        logger.debug(f"Creating filter type {filter_type_name} for schema {schema_name}")

        for field in row_schema.fields:
            logger.debug(
                f"Field {field.name}: type={field.type}, "
                f"indexed={field.indexed}, primary={field.primary}"
            )

            # Allow filtering on any field
            if field.type == "integer":
                annotations[field.name] = Optional[IntFilter]
                defaults[field.name] = None
            elif field.type == "float":
                annotations[field.name] = Optional[FloatFilter]
                defaults[field.name] = None
            elif field.type == "string":
                annotations[field.name] = Optional[StringFilter]
                defaults[field.name] = None

        logger.debug(
            f"Filter type {filter_type_name} will have fields: {list(annotations.keys())}"
        )

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

    def _make_resolver(
        self,
        schema_name: str,
        row_schema,
        graphql_type: type,
        filter_type: type,
        query_callback: QueryCallback
    ):
        """Create a resolver function for a schema."""
        from .filters import parse_where_clause

        async def resolver(
            info: Info,
            where: Optional[filter_type] = None,
            order_by: Optional[str] = None,
            direction: Optional[SortDirection] = None,
            limit: Optional[int] = 100
        ) -> List[graphql_type]:
            # Get context values
            user = info.context["user"]
            collection = info.context["collection"]

            # Parse the where clause
            filters = parse_where_clause(where)

            # Call the query backend
            results = await query_callback(
                user, collection, schema_name, row_schema,
                filters, limit, order_by, direction
            )

            # Convert to GraphQL types
            graphql_results = []
            for row in results:
                graphql_obj = graphql_type(**row)
                graphql_results.append(graphql_obj)

            return graphql_results

        return resolver
