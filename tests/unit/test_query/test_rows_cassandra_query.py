"""
Unit tests for Cassandra Rows GraphQL Query Processor (Unified Table Implementation)

Tests the business logic of the GraphQL query processor including:
- Schema configuration handling
- Query execution using unified rows table
- Name sanitization
- GraphQL query execution
- Message processing logic
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json

from trustgraph.query.rows.cassandra.service import Processor
from trustgraph.schema import RowsQueryRequest, RowsQueryResponse, GraphQLError
from trustgraph.schema import RowSchema, Field


class TestRowsGraphQLQueryLogic:
    """Test business logic for unified table query implementation"""

    def test_sanitize_name_cassandra_compatibility(self):
        """Test name sanitization for Cassandra field names"""
        processor = MagicMock()
        processor.sanitize_name = Processor.sanitize_name.__get__(processor, Processor)

        # Test field name sanitization (uses r_ prefix like storage processor)
        assert processor.sanitize_name("simple_field") == "simple_field"
        assert processor.sanitize_name("Field-With-Dashes") == "field_with_dashes"
        assert processor.sanitize_name("field.with.dots") == "field_with_dots"
        assert processor.sanitize_name("123_field") == "r_123_field"
        assert processor.sanitize_name("field with spaces") == "field_with_spaces"
        assert processor.sanitize_name("special!@#chars") == "special___chars"
        assert processor.sanitize_name("UPPERCASE") == "uppercase"
        assert processor.sanitize_name("CamelCase") == "camelcase"

    def test_get_index_names(self):
        """Test extraction of index names from schema"""
        processor = MagicMock()
        processor.get_index_names = Processor.get_index_names.__get__(processor, Processor)

        schema = RowSchema(
            name="test_schema",
            fields=[
                Field(name="id", type="string", primary=True),
                Field(name="category", type="string", indexed=True),
                Field(name="name", type="string"),  # Not indexed
                Field(name="status", type="string", indexed=True)
            ]
        )

        index_names = processor.get_index_names(schema)

        assert "id" in index_names
        assert "category" in index_names
        assert "status" in index_names
        assert "name" not in index_names
        assert len(index_names) == 3

    def test_find_matching_index_exact_match(self):
        """Test finding matching index for exact match query"""
        processor = MagicMock()
        processor.get_index_names = Processor.get_index_names.__get__(processor, Processor)
        processor.find_matching_index = Processor.find_matching_index.__get__(processor, Processor)

        schema = RowSchema(
            name="test_schema",
            fields=[
                Field(name="id", type="string", primary=True),
                Field(name="category", type="string", indexed=True),
                Field(name="name", type="string")  # Not indexed
            ]
        )

        # Filter on indexed field should return match
        filters = {"category": "electronics"}
        result = processor.find_matching_index(schema, filters)
        assert result is not None
        assert result[0] == "category"
        assert result[1] == ["electronics"]

        # Filter on non-indexed field should return None
        filters = {"name": "test"}
        result = processor.find_matching_index(schema, filters)
        assert result is None

    @pytest.mark.asyncio
    async def test_schema_config_parsing(self):
        """Test parsing of schema configuration"""
        processor = MagicMock()
        processor.schemas = {}
        processor.config_key = "schema"
        processor.schema_builder = MagicMock()
        processor.schema_builder.clear = MagicMock()
        processor.schema_builder.add_schema = MagicMock()
        processor.schema_builder.build = MagicMock(return_value=MagicMock())
        processor.on_schema_config = Processor.on_schema_config.__get__(processor, Processor)

        # Create test config
        schema_config = {
            "schema": {
                "customer": json.dumps({
                    "name": "customer",
                    "description": "Customer table",
                    "fields": [
                        {
                            "name": "id",
                            "type": "string",
                            "primary_key": True,
                            "required": True,
                            "description": "Customer ID"
                        },
                        {
                            "name": "email",
                            "type": "string",
                            "indexed": True,
                            "required": True
                        },
                        {
                            "name": "status",
                            "type": "string",
                            "enum": ["active", "inactive"]
                        }
                    ]
                })
            }
        }

        # Process config
        await processor.on_schema_config(schema_config, version=1)

        # Verify schema was loaded
        assert "customer" in processor.schemas
        schema = processor.schemas["customer"]
        assert schema.name == "customer"
        assert len(schema.fields) == 3

        # Verify fields
        id_field = next(f for f in schema.fields if f.name == "id")
        assert id_field.primary is True

        email_field = next(f for f in schema.fields if f.name == "email")
        assert email_field.indexed is True

        status_field = next(f for f in schema.fields if f.name == "status")
        assert status_field.enum_values == ["active", "inactive"]

        # Verify schema builder was called
        processor.schema_builder.add_schema.assert_called_once()
        processor.schema_builder.build.assert_called_once()

    @pytest.mark.asyncio
    async def test_graphql_context_handling(self):
        """Test GraphQL execution context setup"""
        processor = MagicMock()
        processor.graphql_schema = AsyncMock()
        processor.execute_graphql_query = Processor.execute_graphql_query.__get__(processor, Processor)

        # Mock schema execution
        mock_result = MagicMock()
        mock_result.data = {"customers": [{"id": "1", "name": "Test"}]}
        mock_result.errors = None
        processor.graphql_schema.execute.return_value = mock_result

        result = await processor.execute_graphql_query(
            query='{ customers { id name } }',
            variables={},
            operation_name=None,
            user="test_user",
            collection="test_collection"
        )

        # Verify schema.execute was called with correct context
        processor.graphql_schema.execute.assert_called_once()
        call_args = processor.graphql_schema.execute.call_args

        # Verify context was passed
        context = call_args[1]['context_value']
        assert context["processor"] == processor
        assert context["user"] == "test_user"
        assert context["collection"] == "test_collection"

        # Verify result structure
        assert "data" in result
        assert result["data"] == {"customers": [{"id": "1", "name": "Test"}]}

    @pytest.mark.asyncio
    async def test_error_handling_graphql_errors(self):
        """Test GraphQL error handling and conversion"""
        processor = MagicMock()
        processor.graphql_schema = AsyncMock()
        processor.execute_graphql_query = Processor.execute_graphql_query.__get__(processor, Processor)

        # Create a simple object to simulate GraphQL error
        class MockError:
            def __init__(self, message, path, extensions):
                self.message = message
                self.path = path
                self.extensions = extensions

            def __str__(self):
                return self.message

        mock_error = MockError(
            message="Field 'invalid_field' doesn't exist",
            path=["customers", "0", "invalid_field"],
            extensions={"code": "FIELD_NOT_FOUND"}
        )

        mock_result = MagicMock()
        mock_result.data = None
        mock_result.errors = [mock_error]
        processor.graphql_schema.execute.return_value = mock_result

        result = await processor.execute_graphql_query(
            query='{ customers { invalid_field } }',
            variables={},
            operation_name=None,
            user="test_user",
            collection="test_collection"
        )

        # Verify error handling
        assert "errors" in result
        assert len(result["errors"]) == 1

        error = result["errors"][0]
        assert error["message"] == "Field 'invalid_field' doesn't exist"
        assert error["path"] == ["customers", "0", "invalid_field"]
        assert error["extensions"] == {"code": "FIELD_NOT_FOUND"}

    @pytest.mark.asyncio
    async def test_message_processing_success(self):
        """Test successful message processing flow"""
        processor = MagicMock()
        processor.execute_graphql_query = AsyncMock()
        processor.on_message = Processor.on_message.__get__(processor, Processor)

        # Mock successful query result
        processor.execute_graphql_query.return_value = {
            "data": {"customers": [{"id": "1", "name": "John"}]},
            "errors": [],
            "extensions": {}
        }

        # Create mock message
        mock_msg = MagicMock()
        mock_request = RowsQueryRequest(
            user="test_user",
            collection="test_collection",
            query='{ customers { id name } }',
            variables={},
            operation_name=None
        )
        mock_msg.value.return_value = mock_request
        mock_msg.properties.return_value = {"id": "test-123"}

        # Mock flow
        mock_flow = MagicMock()
        mock_response_flow = AsyncMock()
        mock_flow.return_value = mock_response_flow

        # Process message
        await processor.on_message(mock_msg, None, mock_flow)

        # Verify query was executed
        processor.execute_graphql_query.assert_called_once_with(
            query='{ customers { id name } }',
            variables={},
            operation_name=None,
            user="test_user",
            collection="test_collection"
        )

        # Verify response was sent
        mock_response_flow.send.assert_called_once()
        response_call = mock_response_flow.send.call_args[0][0]

        # Verify response structure
        assert isinstance(response_call, RowsQueryResponse)
        assert response_call.error is None
        assert '"customers"' in response_call.data  # JSON encoded
        assert len(response_call.errors) == 0

    @pytest.mark.asyncio
    async def test_message_processing_error(self):
        """Test error handling during message processing"""
        processor = MagicMock()
        processor.execute_graphql_query = AsyncMock()
        processor.on_message = Processor.on_message.__get__(processor, Processor)

        # Mock query execution error
        processor.execute_graphql_query.side_effect = RuntimeError("No schema available")

        # Create mock message
        mock_msg = MagicMock()
        mock_request = RowsQueryRequest(
            user="test_user",
            collection="test_collection",
            query='{ invalid_query }',
            variables={},
            operation_name=None
        )
        mock_msg.value.return_value = mock_request
        mock_msg.properties.return_value = {"id": "test-456"}

        # Mock flow
        mock_flow = MagicMock()
        mock_response_flow = AsyncMock()
        mock_flow.return_value = mock_response_flow

        # Process message
        await processor.on_message(mock_msg, None, mock_flow)

        # Verify error response was sent
        mock_response_flow.send.assert_called_once()
        response_call = mock_response_flow.send.call_args[0][0]

        # Verify error response structure
        assert isinstance(response_call, RowsQueryResponse)
        assert response_call.error is not None
        assert response_call.error.type == "rows-query-error"
        assert "No schema available" in response_call.error.message
        assert response_call.data is None


class TestUnifiedTableQueries:
    """Test queries against the unified rows table"""

    @pytest.mark.asyncio
    async def test_query_with_index_match(self):
        """Test query execution with matching index"""
        processor = MagicMock()
        processor.session = MagicMock()
        processor.connect_cassandra = MagicMock()
        processor.sanitize_name = Processor.sanitize_name.__get__(processor, Processor)
        processor.get_index_names = Processor.get_index_names.__get__(processor, Processor)
        processor.find_matching_index = Processor.find_matching_index.__get__(processor, Processor)
        processor.query_cassandra = Processor.query_cassandra.__get__(processor, Processor)

        # Mock session execute to return test data
        mock_row = MagicMock()
        mock_row.data = {"id": "123", "name": "Test Product", "category": "electronics"}
        processor.session.execute.return_value = [mock_row]

        schema = RowSchema(
            name="products",
            fields=[
                Field(name="id", type="string", primary=True),
                Field(name="category", type="string", indexed=True),
                Field(name="name", type="string")
            ]
        )

        # Query with filter on indexed field
        results = await processor.query_cassandra(
            user="test_user",
            collection="test_collection",
            schema_name="products",
            row_schema=schema,
            filters={"category": "electronics"},
            limit=10
        )

        # Verify Cassandra was connected and queried
        processor.connect_cassandra.assert_called_once()
        processor.session.execute.assert_called_once()

        # Verify query structure - should query unified rows table
        call_args = processor.session.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert "SELECT data, source FROM test_user.rows" in query
        assert "collection = %s" in query
        assert "schema_name = %s" in query
        assert "index_name = %s" in query
        assert "index_value = %s" in query

        assert params[0] == "test_collection"
        assert params[1] == "products"
        assert params[2] == "category"
        assert params[3] == ["electronics"]

        # Verify results
        assert len(results) == 1
        assert results[0]["id"] == "123"
        assert results[0]["category"] == "electronics"

    @pytest.mark.asyncio
    async def test_query_without_index_match(self):
        """Test query execution without matching index (scan mode)"""
        processor = MagicMock()
        processor.session = MagicMock()
        processor.connect_cassandra = MagicMock()
        processor.sanitize_name = Processor.sanitize_name.__get__(processor, Processor)
        processor.get_index_names = Processor.get_index_names.__get__(processor, Processor)
        processor.find_matching_index = Processor.find_matching_index.__get__(processor, Processor)
        processor._matches_filters = Processor._matches_filters.__get__(processor, Processor)
        processor.query_cassandra = Processor.query_cassandra.__get__(processor, Processor)

        # Mock session execute to return test data
        mock_row1 = MagicMock()
        mock_row1.data = {"id": "1", "name": "Product A", "price": "100"}
        mock_row2 = MagicMock()
        mock_row2.data = {"id": "2", "name": "Product B", "price": "200"}
        processor.session.execute.return_value = [mock_row1, mock_row2]

        schema = RowSchema(
            name="products",
            fields=[
                Field(name="id", type="string", primary=True),
                Field(name="name", type="string"),  # Not indexed
                Field(name="price", type="string")  # Not indexed
            ]
        )

        # Query with filter on non-indexed field
        results = await processor.query_cassandra(
            user="test_user",
            collection="test_collection",
            schema_name="products",
            row_schema=schema,
            filters={"name": "Product A"},
            limit=10
        )

        # Query should use ALLOW FILTERING for scan
        call_args = processor.session.execute.call_args
        query = call_args[0][0]

        assert "ALLOW FILTERING" in query

        # Should post-filter results
        assert len(results) == 1
        assert results[0]["name"] == "Product A"


class TestFilterMatching:
    """Test filter matching logic"""

    def test_matches_filters_exact_match(self):
        """Test exact match filter"""
        processor = MagicMock()
        processor._matches_filters = Processor._matches_filters.__get__(processor, Processor)

        schema = RowSchema(name="test", fields=[Field(name="status", type="string")])

        row = {"status": "active", "name": "test"}
        assert processor._matches_filters(row, {"status": "active"}, schema) is True
        assert processor._matches_filters(row, {"status": "inactive"}, schema) is False

    def test_matches_filters_comparison_operators(self):
        """Test comparison operators in filters"""
        processor = MagicMock()
        processor._matches_filters = Processor._matches_filters.__get__(processor, Processor)

        schema = RowSchema(name="test", fields=[Field(name="price", type="float")])

        row = {"price": "100.0"}

        # Greater than
        assert processor._matches_filters(row, {"price_gt": 50}, schema) is True
        assert processor._matches_filters(row, {"price_gt": 150}, schema) is False

        # Less than
        assert processor._matches_filters(row, {"price_lt": 150}, schema) is True
        assert processor._matches_filters(row, {"price_lt": 50}, schema) is False

        # Greater than or equal
        assert processor._matches_filters(row, {"price_gte": 100}, schema) is True
        assert processor._matches_filters(row, {"price_gte": 101}, schema) is False

        # Less than or equal
        assert processor._matches_filters(row, {"price_lte": 100}, schema) is True
        assert processor._matches_filters(row, {"price_lte": 99}, schema) is False

    def test_matches_filters_contains(self):
        """Test contains filter"""
        processor = MagicMock()
        processor._matches_filters = Processor._matches_filters.__get__(processor, Processor)

        schema = RowSchema(name="test", fields=[Field(name="description", type="string")])

        row = {"description": "A great product for everyone"}

        assert processor._matches_filters(row, {"description_contains": "great"}, schema) is True
        assert processor._matches_filters(row, {"description_contains": "terrible"}, schema) is False

    def test_matches_filters_in_list(self):
        """Test in-list filter"""
        processor = MagicMock()
        processor._matches_filters = Processor._matches_filters.__get__(processor, Processor)

        schema = RowSchema(name="test", fields=[Field(name="status", type="string")])

        row = {"status": "active"}

        assert processor._matches_filters(row, {"status_in": ["active", "pending"]}, schema) is True
        assert processor._matches_filters(row, {"status_in": ["inactive", "deleted"]}, schema) is False


class TestIndexedFieldFiltering:
    """Test that only indexed or primary key fields can be directly filtered"""

    def test_indexed_field_filtering(self):
        """Test that only indexed or primary key fields can be filtered"""
        schema = RowSchema(
            name="test",
            fields=[
                Field(name="id", type="string", primary=True),
                Field(name="indexed_field", type="string", indexed=True),
                Field(name="normal_field", type="string", indexed=False),
                Field(name="another_field", type="string")
            ]
        )

        filters = {
            "id": "test123",  # Primary key - should be included
            "indexed_field": "value",  # Indexed - should be included
            "normal_field": "ignored",  # Not indexed - should be ignored
            "another_field": "also_ignored"  # Not indexed - should be ignored
        }

        # Simulate the filtering logic from the processor
        valid_filters = []
        for field_name, value in filters.items():
            if value is not None:
                schema_field = next((f for f in schema.fields if f.name == field_name), None)
                if schema_field and (schema_field.indexed or schema_field.primary):
                    valid_filters.append((field_name, value))

        # Only id and indexed_field should be included
        assert len(valid_filters) == 2
        field_names = [f[0] for f in valid_filters]
        assert "id" in field_names
        assert "indexed_field" in field_names
        assert "normal_field" not in field_names
        assert "another_field" not in field_names
