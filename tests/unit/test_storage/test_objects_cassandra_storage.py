"""
Unit tests for Cassandra Object Storage Processor

Tests the business logic of the object storage processor including:
- Schema configuration handling
- Type conversions
- Name sanitization
- Table structure generation
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json

from trustgraph.storage.objects.cassandra.write import Processor
from trustgraph.schema import ExtractedObject, Metadata, RowSchema, Field


class TestObjectsCassandraStorageLogic:
    """Test business logic without FlowProcessor dependencies"""

    def test_sanitize_name(self):
        """Test name sanitization for Cassandra compatibility"""
        processor = MagicMock()
        processor.sanitize_name = Processor.sanitize_name.__get__(processor, Processor)
        
        # Test various name patterns (back to original logic)
        assert processor.sanitize_name("simple_name") == "simple_name"
        assert processor.sanitize_name("Name-With-Dashes") == "name_with_dashes"
        assert processor.sanitize_name("name.with.dots") == "name_with_dots"
        assert processor.sanitize_name("123_starts_with_number") == "o_123_starts_with_number"
        assert processor.sanitize_name("name with spaces") == "name_with_spaces"
        assert processor.sanitize_name("special!@#$%^chars") == "special______chars"

    def test_get_cassandra_type(self):
        """Test field type conversion to Cassandra types"""
        processor = MagicMock()
        processor.get_cassandra_type = Processor.get_cassandra_type.__get__(processor, Processor)
        
        # Basic type mappings
        assert processor.get_cassandra_type("string") == "text"
        assert processor.get_cassandra_type("boolean") == "boolean"
        assert processor.get_cassandra_type("timestamp") == "timestamp"
        assert processor.get_cassandra_type("uuid") == "uuid"
        
        # Integer types with size hints
        assert processor.get_cassandra_type("integer", size=2) == "int"
        assert processor.get_cassandra_type("integer", size=8) == "bigint"
        
        # Float types with size hints
        assert processor.get_cassandra_type("float", size=2) == "float"
        assert processor.get_cassandra_type("float", size=8) == "double"
        
        # Unknown type defaults to text
        assert processor.get_cassandra_type("unknown_type") == "text"

    def test_convert_value(self):
        """Test value conversion for different field types"""
        processor = MagicMock()
        processor.convert_value = Processor.convert_value.__get__(processor, Processor)
        
        # Integer conversions
        assert processor.convert_value("123", "integer") == 123
        assert processor.convert_value(123.5, "integer") == 123
        assert processor.convert_value(None, "integer") is None
        
        # Float conversions
        assert processor.convert_value("123.45", "float") == 123.45
        assert processor.convert_value(123, "float") == 123.0
        
        # Boolean conversions
        assert processor.convert_value("true", "boolean") is True
        assert processor.convert_value("false", "boolean") is False
        assert processor.convert_value("1", "boolean") is True
        assert processor.convert_value("0", "boolean") is False
        assert processor.convert_value("yes", "boolean") is True
        assert processor.convert_value("no", "boolean") is False
        
        # String conversions
        assert processor.convert_value(123, "string") == "123"
        assert processor.convert_value(True, "string") == "True"

    def test_table_creation_cql_generation(self):
        """Test CQL generation for table creation"""
        processor = MagicMock()
        processor.schemas = {}
        processor.known_keyspaces = set()
        processor.known_tables = {}
        processor.session = MagicMock()
        processor.sanitize_name = Processor.sanitize_name.__get__(processor, Processor)
        processor.sanitize_table = Processor.sanitize_table.__get__(processor, Processor)
        processor.get_cassandra_type = Processor.get_cassandra_type.__get__(processor, Processor)
        def mock_ensure_keyspace(keyspace):
            processor.known_keyspaces.add(keyspace)
            processor.known_tables[keyspace] = set()
        processor.ensure_keyspace = mock_ensure_keyspace
        processor.ensure_table = Processor.ensure_table.__get__(processor, Processor)
        
        # Create test schema
        schema = RowSchema(
            name="customer_records",
            description="Test customer schema",
            fields=[
                Field(
                    name="customer_id",
                    type="string",
                    size=50,
                    primary=True,
                    required=True,
                    indexed=False
                ),
                Field(
                    name="email",
                    type="string",
                    size=100,
                    required=True,
                    indexed=True
                ),
                Field(
                    name="age",
                    type="integer",
                    size=4,
                    required=False,
                    indexed=False
                )
            ]
        )
        
        # Call ensure_table
        processor.ensure_table("test_user", "customer_records", schema)
        
        # Verify keyspace was ensured (check that it was added to known_keyspaces)
        assert "test_user" in processor.known_keyspaces
        
        # Check the CQL that was executed (first call should be table creation)
        all_calls = processor.session.execute.call_args_list
        table_creation_cql = all_calls[0][0][0]  # First call
        
        # Verify table structure (keyspace uses sanitize_name, table uses sanitize_table)
        assert "CREATE TABLE IF NOT EXISTS test_user.o_customer_records" in table_creation_cql
        assert "collection text" in table_creation_cql
        assert "customer_id text" in table_creation_cql
        assert "email text" in table_creation_cql
        assert "age int" in table_creation_cql
        assert "PRIMARY KEY ((collection, customer_id))" in table_creation_cql

    def test_table_creation_without_primary_key(self):
        """Test table creation when no primary key is defined"""
        processor = MagicMock()
        processor.schemas = {}
        processor.known_keyspaces = set()
        processor.known_tables = {}
        processor.session = MagicMock()
        processor.sanitize_name = Processor.sanitize_name.__get__(processor, Processor)
        processor.sanitize_table = Processor.sanitize_table.__get__(processor, Processor)
        processor.get_cassandra_type = Processor.get_cassandra_type.__get__(processor, Processor)
        def mock_ensure_keyspace(keyspace):
            processor.known_keyspaces.add(keyspace)
            processor.known_tables[keyspace] = set()
        processor.ensure_keyspace = mock_ensure_keyspace
        processor.ensure_table = Processor.ensure_table.__get__(processor, Processor)
        
        # Create schema without primary key
        schema = RowSchema(
            name="events",
            description="Event log",
            fields=[
                Field(name="event_type", type="string", size=50),
                Field(name="timestamp", type="timestamp", size=0)
            ]
        )
        
        # Call ensure_table
        processor.ensure_table("test_user", "events", schema)
        
        # Check the CQL includes synthetic_id (field names don't get o_ prefix)
        executed_cql = processor.session.execute.call_args[0][0]
        assert "synthetic_id uuid" in executed_cql
        assert "PRIMARY KEY ((collection, synthetic_id))" in executed_cql

    @pytest.mark.asyncio
    async def test_schema_config_parsing(self):
        """Test parsing of schema configurations"""
        processor = MagicMock()
        processor.schemas = {}
        processor.config_key = "schema"
        processor.on_schema_config = Processor.on_schema_config.__get__(processor, Processor)
        
        # Create test configuration
        config = {
            "schema": {
                "customer_records": json.dumps({
                    "name": "customer_records",
                    "description": "Customer data",
                    "fields": [
                        {
                            "name": "id",
                            "type": "string",
                            "primary_key": True,
                            "required": True
                        },
                        {
                            "name": "name",
                            "type": "string",
                            "required": True
                        },
                        {
                            "name": "balance",
                            "type": "float",
                            "size": 8
                        }
                    ]
                })
            }
        }
        
        # Process configuration
        await processor.on_schema_config(config, version=1)
        
        # Verify schema was loaded
        assert "customer_records" in processor.schemas
        schema = processor.schemas["customer_records"]
        assert schema.name == "customer_records"
        assert len(schema.fields) == 3
        
        # Check field properties
        id_field = schema.fields[0]
        assert id_field.name == "id"
        assert id_field.type == "string"
        assert id_field.primary is True
        # Note: Field.required always returns False due to Pulsar schema limitations
        # The actual required value is tracked during schema parsing

    @pytest.mark.asyncio
    async def test_object_processing_logic(self):
        """Test the logic for processing ExtractedObject"""
        processor = MagicMock()
        processor.schemas = {
            "test_schema": RowSchema(
                name="test_schema",
                description="Test",
                fields=[
                    Field(name="id", type="string", size=50, primary=True),
                    Field(name="value", type="integer", size=4)
                ]
            )
        }
        processor.ensure_table = MagicMock()
        processor.sanitize_name = Processor.sanitize_name.__get__(processor, Processor)
        processor.sanitize_table = Processor.sanitize_table.__get__(processor, Processor)
        processor.convert_value = Processor.convert_value.__get__(processor, Processor)
        processor.session = MagicMock()
        processor.on_object = Processor.on_object.__get__(processor, Processor)
        processor.known_keyspaces = {"test_user"}  # Pre-populate to skip validation query
        processor.known_tables = {"test_user": set()}  # Pre-populate
        
        # Create test object
        test_obj = ExtractedObject(
            metadata=Metadata(
                id="test-001",
                user="test_user",
                collection="test_collection",
                metadata=[]
            ),
            schema_name="test_schema",
            values=[{"id": "123", "value": "456"}],
            confidence=0.9,
            source_span="test source"
        )
        
        # Create mock message
        msg = MagicMock()
        msg.value.return_value = test_obj
        
        # Process object
        await processor.on_object(msg, None, None)
        
        # Verify table was ensured
        processor.ensure_table.assert_called_once_with("test_user", "test_schema", processor.schemas["test_schema"])
        
        # Verify insert was executed (keyspace normal, table with o_ prefix)
        processor.session.execute.assert_called_once()
        insert_cql = processor.session.execute.call_args[0][0]
        values = processor.session.execute.call_args[0][1]
        
        assert "INSERT INTO test_user.o_test_schema" in insert_cql
        assert "collection" in insert_cql
        assert values[0] == "test_collection"  # collection value
        assert values[1] == "123"  # id value (from values[0])
        assert values[2] == 456  # converted integer value (from values[0])

    def test_secondary_index_creation(self):
        """Test that secondary indexes are created for indexed fields"""
        processor = MagicMock()
        processor.schemas = {}
        processor.known_keyspaces = {"test_user"}  # Pre-populate to skip validation query
        processor.known_tables = {"test_user": set()}  # Pre-populate
        processor.session = MagicMock()
        processor.sanitize_name = Processor.sanitize_name.__get__(processor, Processor)
        processor.sanitize_table = Processor.sanitize_table.__get__(processor, Processor)
        processor.get_cassandra_type = Processor.get_cassandra_type.__get__(processor, Processor)
        def mock_ensure_keyspace(keyspace):
            processor.known_keyspaces.add(keyspace)
            if keyspace not in processor.known_tables:
                processor.known_tables[keyspace] = set()
        processor.ensure_keyspace = mock_ensure_keyspace
        processor.ensure_table = Processor.ensure_table.__get__(processor, Processor)

        # Create schema with indexed field
        schema = RowSchema(
            name="products",
            description="Product catalog",
            fields=[
                Field(name="product_id", type="string", size=50, primary=True),
                Field(name="category", type="string", size=30, indexed=True),
                Field(name="price", type="float", size=8, indexed=True)
            ]
        )

        # Call ensure_table
        processor.ensure_table("test_user", "products", schema)

        # Should have 3 calls: create table + 2 indexes
        assert processor.session.execute.call_count == 3
        
        # Check index creation calls (table has o_ prefix, fields don't)
        calls = processor.session.execute.call_args_list
        index_calls = [call[0][0] for call in calls if "CREATE INDEX" in call[0][0]]
        assert len(index_calls) == 2
        assert any("o_products_category_idx" in call for call in index_calls)
        assert any("o_products_price_idx" in call for call in index_calls)


class TestObjectsCassandraStorageBatchLogic:
    """Test batch processing logic in Cassandra storage"""

    @pytest.mark.asyncio
    async def test_batch_object_processing_logic(self):
        """Test processing of batch ExtractedObjects"""
        processor = MagicMock()
        processor.schemas = {
            "batch_schema": RowSchema(
                name="batch_schema",
                description="Test batch schema",
                fields=[
                    Field(name="id", type="string", size=50, primary=True),
                    Field(name="name", type="string", size=100),
                    Field(name="value", type="integer", size=4)
                ]
            )
        }
        processor.known_keyspaces = {"test_user"}  # Pre-populate to skip validation query
        processor.ensure_table = MagicMock()
        processor.sanitize_name = Processor.sanitize_name.__get__(processor, Processor)
        processor.sanitize_table = Processor.sanitize_table.__get__(processor, Processor)
        processor.convert_value = Processor.convert_value.__get__(processor, Processor)
        processor.session = MagicMock()
        processor.on_object = Processor.on_object.__get__(processor, Processor)
        
        # Create batch object with multiple values
        batch_obj = ExtractedObject(
            metadata=Metadata(
                id="batch-001",
                user="test_user",
                collection="batch_collection", 
                metadata=[]
            ),
            schema_name="batch_schema",
            values=[
                {"id": "001", "name": "First", "value": "100"},
                {"id": "002", "name": "Second", "value": "200"},
                {"id": "003", "name": "Third", "value": "300"}
            ],
            confidence=0.95,
            source_span="batch source"
        )
        
        # Create mock message
        msg = MagicMock()
        msg.value.return_value = batch_obj
        
        # Process batch object
        await processor.on_object(msg, None, None)
        
        # Verify table was ensured once
        processor.ensure_table.assert_called_once_with("test_user", "batch_schema", processor.schemas["batch_schema"])
        
        # Verify 3 separate insert calls (one per batch item)
        assert processor.session.execute.call_count == 3
        
        # Check each insert call
        calls = processor.session.execute.call_args_list
        for i, call in enumerate(calls):
            insert_cql = call[0][0]
            values = call[0][1]
            
            assert "INSERT INTO test_user.o_batch_schema" in insert_cql
            assert "collection" in insert_cql
            
            # Check values for each batch item
            assert values[0] == "batch_collection"  # collection
            assert values[1] == f"00{i+1}"  # id from batch item i
            assert values[2] == f"First" if i == 0 else f"Second" if i == 1 else f"Third"  # name
            assert values[3] == (i+1) * 100  # converted integer value

    @pytest.mark.asyncio  
    async def test_empty_batch_processing_logic(self):
        """Test processing of empty batch ExtractedObjects"""
        processor = MagicMock()
        processor.schemas = {
            "empty_schema": RowSchema(
                name="empty_schema",
                fields=[Field(name="id", type="string", size=50, primary=True)]
            )
        }
        processor.ensure_table = MagicMock()
        processor.sanitize_name = Processor.sanitize_name.__get__(processor, Processor)
        processor.sanitize_table = Processor.sanitize_table.__get__(processor, Processor)
        processor.convert_value = Processor.convert_value.__get__(processor, Processor)
        processor.session = MagicMock()
        processor.on_object = Processor.on_object.__get__(processor, Processor)
        processor.known_keyspaces = {"test_user"}  # Pre-populate to skip validation query
        processor.known_tables = {"test_user": set()}  # Pre-populate
        
        # Create empty batch object
        empty_batch_obj = ExtractedObject(
            metadata=Metadata(
                id="empty-001",
                user="test_user",
                collection="empty_collection",
                metadata=[]
            ),
            schema_name="empty_schema",
            values=[],  # Empty batch
            confidence=1.0,
            source_span="empty source"
        )
        
        msg = MagicMock()
        msg.value.return_value = empty_batch_obj
        
        # Process empty batch object
        await processor.on_object(msg, None, None)
        
        # Verify table was ensured
        processor.ensure_table.assert_called_once()
        
        # Verify no insert calls for empty batch
        processor.session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_single_item_batch_processing_logic(self):
        """Test processing of single-item batch (backward compatibility)"""
        processor = MagicMock()
        processor.schemas = {
            "single_schema": RowSchema(
                name="single_schema",
                fields=[
                    Field(name="id", type="string", size=50, primary=True),
                    Field(name="data", type="string", size=100)
                ]
            )
        }
        processor.ensure_table = MagicMock()
        processor.sanitize_name = Processor.sanitize_name.__get__(processor, Processor)
        processor.sanitize_table = Processor.sanitize_table.__get__(processor, Processor)
        processor.convert_value = Processor.convert_value.__get__(processor, Processor)
        processor.session = MagicMock()
        processor.on_object = Processor.on_object.__get__(processor, Processor)
        processor.known_keyspaces = {"test_user"}  # Pre-populate to skip validation query
        processor.known_tables = {"test_user": set()}  # Pre-populate
        
        # Create single-item batch object (backward compatibility case)
        single_batch_obj = ExtractedObject(
            metadata=Metadata(
                id="single-001",
                user="test_user",
                collection="single_collection",
                metadata=[]
            ),
            schema_name="single_schema",
            values=[{"id": "single-1", "data": "single data"}],  # Array with one item
            confidence=0.8,
            source_span="single source"
        )
        
        msg = MagicMock()
        msg.value.return_value = single_batch_obj
        
        # Process single-item batch object
        await processor.on_object(msg, None, None)
        
        # Verify table was ensured
        processor.ensure_table.assert_called_once()
        
        # Verify exactly one insert call
        processor.session.execute.assert_called_once()
        
        insert_cql = processor.session.execute.call_args[0][0]
        values = processor.session.execute.call_args[0][1]
        
        assert "INSERT INTO test_user.o_single_schema" in insert_cql
        assert values[0] == "single_collection"  # collection
        assert values[1] == "single-1"  # id value
        assert values[2] == "single data"  # data value

    def test_batch_value_conversion_logic(self):
        """Test value conversion works correctly for batch items"""
        processor = MagicMock()
        processor.convert_value = Processor.convert_value.__get__(processor, Processor)
        
        # Test various conversion scenarios that would occur in batch processing
        test_cases = [
            # Integer conversions for batch items
            ("123", "integer", 123),
            ("456", "integer", 456), 
            ("789", "integer", 789),
            # Float conversions for batch items
            ("12.5", "float", 12.5),
            ("34.7", "float", 34.7),
            # Boolean conversions for batch items  
            ("true", "boolean", True),
            ("false", "boolean", False),
            ("1", "boolean", True),
            ("0", "boolean", False),
            # String conversions for batch items
            (123, "string", "123"),
            (45.6, "string", "45.6"),
        ]
        
        for input_val, field_type, expected_output in test_cases:
            result = processor.convert_value(input_val, field_type)
            assert result == expected_output, f"Failed for {input_val} -> {field_type}: got {result}, expected {expected_output}"