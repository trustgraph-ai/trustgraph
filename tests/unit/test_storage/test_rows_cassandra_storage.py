"""
Unit tests for Cassandra Row Storage Processor (Unified Table Implementation)

Tests the business logic of the row storage processor including:
- Schema configuration handling
- Name sanitization
- Unified table structure
- Index management
- Row storage with multi-index support
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json

from trustgraph.storage.rows.cassandra.write import Processor
from trustgraph.schema import ExtractedObject, Metadata, RowSchema, Field


class TestRowsCassandraStorageLogic:
    """Test business logic for unified table implementation"""

    def test_sanitize_name(self):
        """Test name sanitization for Cassandra compatibility"""
        processor = MagicMock()
        processor.sanitize_name = Processor.sanitize_name.__get__(processor, Processor)

        # Test various name patterns
        assert processor.sanitize_name("simple_name") == "simple_name"
        assert processor.sanitize_name("Name-With-Dashes") == "name_with_dashes"
        assert processor.sanitize_name("name.with.dots") == "name_with_dots"
        assert processor.sanitize_name("123_starts_with_number") == "r_123_starts_with_number"
        assert processor.sanitize_name("name with spaces") == "name_with_spaces"
        assert processor.sanitize_name("special!@#$%^chars") == "special______chars"
        assert processor.sanitize_name("UPPERCASE") == "uppercase"
        assert processor.sanitize_name("CamelCase") == "camelcase"
        assert processor.sanitize_name("_underscore_start") == "r__underscore_start"

    def test_get_index_names(self):
        """Test extraction of index names from schema"""
        processor = MagicMock()
        processor.get_index_names = Processor.get_index_names.__get__(processor, Processor)

        # Schema with primary and indexed fields
        schema = RowSchema(
            name="test_schema",
            description="Test",
            fields=[
                Field(name="id", type="string", primary=True),
                Field(name="category", type="string", indexed=True),
                Field(name="name", type="string"),  # Not indexed
                Field(name="status", type="string", indexed=True)
            ]
        )

        index_names = processor.get_index_names(schema)

        # Should include primary key and indexed fields
        assert "id" in index_names
        assert "category" in index_names
        assert "status" in index_names
        assert "name" not in index_names  # Not indexed
        assert len(index_names) == 3

    def test_get_index_names_no_indexes(self):
        """Test schema with no indexed fields"""
        processor = MagicMock()
        processor.get_index_names = Processor.get_index_names.__get__(processor, Processor)

        schema = RowSchema(
            name="no_index_schema",
            fields=[
                Field(name="data1", type="string"),
                Field(name="data2", type="string")
            ]
        )

        index_names = processor.get_index_names(schema)
        assert len(index_names) == 0

    def test_build_index_value(self):
        """Test building index values from row data"""
        processor = MagicMock()
        processor.build_index_value = Processor.build_index_value.__get__(processor, Processor)

        value_map = {"id": "123", "category": "electronics", "name": "Widget"}

        # Single field index
        result = processor.build_index_value(value_map, "id")
        assert result == ["123"]

        result = processor.build_index_value(value_map, "category")
        assert result == ["electronics"]

        # Missing field returns empty string
        result = processor.build_index_value(value_map, "missing")
        assert result == [""]

    def test_build_index_value_composite(self):
        """Test building composite index values"""
        processor = MagicMock()
        processor.build_index_value = Processor.build_index_value.__get__(processor, Processor)

        value_map = {"region": "us-west", "category": "electronics", "id": "123"}

        # Composite index (comma-separated field names)
        result = processor.build_index_value(value_map, "region,category")
        assert result == ["us-west", "electronics"]

    @pytest.mark.asyncio
    async def test_schema_config_parsing(self):
        """Test parsing of schema configurations"""
        processor = MagicMock()
        processor.schemas = {}
        processor.config_key = "schema"
        processor.registered_partitions = set()
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
                            "name": "category",
                            "type": "string",
                            "indexed": True
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

    @pytest.mark.asyncio
    async def test_object_processing_stores_data_map(self):
        """Test that row processing stores data as map<text, text>"""
        processor = MagicMock()
        processor.schemas = {
            "test_schema": RowSchema(
                name="test_schema",
                description="Test",
                fields=[
                    Field(name="id", type="string", size=50, primary=True),
                    Field(name="value", type="string", size=100)
                ]
            )
        }
        processor.tables_initialized = {"test_user"}
        processor.registered_partitions = set()
        processor.session = MagicMock()
        processor.sanitize_name = Processor.sanitize_name.__get__(processor, Processor)
        processor.get_index_names = Processor.get_index_names.__get__(processor, Processor)
        processor.build_index_value = Processor.build_index_value.__get__(processor, Processor)
        processor.ensure_tables = MagicMock()
        processor.register_partitions = MagicMock()
        processor.collection_exists = MagicMock(return_value=True)
        processor.on_object = Processor.on_object.__get__(processor, Processor)

        # Create test object
        test_obj = ExtractedObject(
            metadata=Metadata(
                id="test-001",
                user="test_user",
                collection="test_collection",
                metadata=[]
            ),
            schema_name="test_schema",
            values=[{"id": "123", "value": "test_data"}],
            confidence=0.9,
            source_span="test source"
        )

        # Create mock message
        msg = MagicMock()
        msg.value.return_value = test_obj

        # Process object
        await processor.on_object(msg, None, None)

        # Verify insert was executed
        processor.session.execute.assert_called()
        insert_call = processor.session.execute.call_args
        insert_cql = insert_call[0][0]
        values = insert_call[0][1]

        # Verify using unified rows table
        assert "INSERT INTO test_user.rows" in insert_cql

        # Values should be: (collection, schema_name, index_name, index_value, data, source)
        assert values[0] == "test_collection"  # collection
        assert values[1] == "test_schema"      # schema_name
        assert values[2] == "id"               # index_name (primary key field)
        assert values[3] == ["123"]            # index_value as list
        assert values[4] == {"id": "123", "value": "test_data"}  # data map
        assert values[5] == ""                 # source

    @pytest.mark.asyncio
    async def test_object_processing_multiple_indexes(self):
        """Test that row is written once per indexed field"""
        processor = MagicMock()
        processor.schemas = {
            "multi_index_schema": RowSchema(
                name="multi_index_schema",
                fields=[
                    Field(name="id", type="string", primary=True),
                    Field(name="category", type="string", indexed=True),
                    Field(name="status", type="string", indexed=True)
                ]
            )
        }
        processor.tables_initialized = {"test_user"}
        processor.registered_partitions = set()
        processor.session = MagicMock()
        processor.sanitize_name = Processor.sanitize_name.__get__(processor, Processor)
        processor.get_index_names = Processor.get_index_names.__get__(processor, Processor)
        processor.build_index_value = Processor.build_index_value.__get__(processor, Processor)
        processor.ensure_tables = MagicMock()
        processor.register_partitions = MagicMock()
        processor.collection_exists = MagicMock(return_value=True)
        processor.on_object = Processor.on_object.__get__(processor, Processor)

        test_obj = ExtractedObject(
            metadata=Metadata(
                id="test-001",
                user="test_user",
                collection="test_collection",
                metadata=[]
            ),
            schema_name="multi_index_schema",
            values=[{"id": "123", "category": "electronics", "status": "active"}],
            confidence=0.9,
            source_span=""
        )

        msg = MagicMock()
        msg.value.return_value = test_obj

        await processor.on_object(msg, None, None)

        # Should have 3 inserts (one per indexed field: id, category, status)
        assert processor.session.execute.call_count == 3

        # Check that different index_names were used
        index_names_used = set()
        for call in processor.session.execute.call_args_list:
            values = call[0][1]
            index_names_used.add(values[2])  # index_name is 3rd value

        assert index_names_used == {"id", "category", "status"}


class TestRowsCassandraStorageBatchLogic:
    """Test batch processing logic for unified table implementation"""

    @pytest.mark.asyncio
    async def test_batch_object_processing(self):
        """Test processing of batch ExtractedObjects"""
        processor = MagicMock()
        processor.schemas = {
            "batch_schema": RowSchema(
                name="batch_schema",
                fields=[
                    Field(name="id", type="string", primary=True),
                    Field(name="name", type="string")
                ]
            )
        }
        processor.tables_initialized = {"test_user"}
        processor.registered_partitions = set()
        processor.session = MagicMock()
        processor.sanitize_name = Processor.sanitize_name.__get__(processor, Processor)
        processor.get_index_names = Processor.get_index_names.__get__(processor, Processor)
        processor.build_index_value = Processor.build_index_value.__get__(processor, Processor)
        processor.ensure_tables = MagicMock()
        processor.register_partitions = MagicMock()
        processor.collection_exists = MagicMock(return_value=True)
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
                {"id": "001", "name": "First"},
                {"id": "002", "name": "Second"},
                {"id": "003", "name": "Third"}
            ],
            confidence=0.95,
            source_span=""
        )

        msg = MagicMock()
        msg.value.return_value = batch_obj

        await processor.on_object(msg, None, None)

        # Should have 3 inserts (one per row, one index per row since only primary key)
        assert processor.session.execute.call_count == 3

        # Check each insert has different id
        ids_inserted = set()
        for call in processor.session.execute.call_args_list:
            values = call[0][1]
            ids_inserted.add(tuple(values[3]))  # index_value is 4th value

        assert ids_inserted == {("001",), ("002",), ("003",)}

    @pytest.mark.asyncio
    async def test_empty_batch_processing(self):
        """Test processing of empty batch ExtractedObjects"""
        processor = MagicMock()
        processor.schemas = {
            "empty_schema": RowSchema(
                name="empty_schema",
                fields=[Field(name="id", type="string", primary=True)]
            )
        }
        processor.tables_initialized = {"test_user"}
        processor.registered_partitions = set()
        processor.session = MagicMock()
        processor.sanitize_name = Processor.sanitize_name.__get__(processor, Processor)
        processor.get_index_names = Processor.get_index_names.__get__(processor, Processor)
        processor.build_index_value = Processor.build_index_value.__get__(processor, Processor)
        processor.ensure_tables = MagicMock()
        processor.register_partitions = MagicMock()
        processor.collection_exists = MagicMock(return_value=True)
        processor.on_object = Processor.on_object.__get__(processor, Processor)

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
            source_span=""
        )

        msg = MagicMock()
        msg.value.return_value = empty_batch_obj

        await processor.on_object(msg, None, None)

        # Verify no insert calls for empty batch
        processor.session.execute.assert_not_called()


class TestUnifiedTableStructure:
    """Test the unified rows table structure"""

    def test_ensure_tables_creates_unified_structure(self):
        """Test that ensure_tables creates the unified rows table"""
        processor = MagicMock()
        processor.known_keyspaces = {"test_user"}
        processor.tables_initialized = set()
        processor.session = MagicMock()
        processor.sanitize_name = Processor.sanitize_name.__get__(processor, Processor)
        processor.ensure_keyspace = MagicMock()
        processor.ensure_tables = Processor.ensure_tables.__get__(processor, Processor)

        processor.ensure_tables("test_user")

        # Should have 2 calls: create rows table + create row_partitions table
        assert processor.session.execute.call_count == 2

        # Check rows table creation
        rows_cql = processor.session.execute.call_args_list[0][0][0]
        assert "CREATE TABLE IF NOT EXISTS test_user.rows" in rows_cql
        assert "collection text" in rows_cql
        assert "schema_name text" in rows_cql
        assert "index_name text" in rows_cql
        assert "index_value frozen<list<text>>" in rows_cql
        assert "data map<text, text>" in rows_cql
        assert "source text" in rows_cql
        assert "PRIMARY KEY ((collection, schema_name, index_name), index_value)" in rows_cql

        # Check row_partitions table creation
        partitions_cql = processor.session.execute.call_args_list[1][0][0]
        assert "CREATE TABLE IF NOT EXISTS test_user.row_partitions" in partitions_cql
        assert "PRIMARY KEY ((collection), schema_name, index_name)" in partitions_cql

        # Verify keyspace added to initialized set
        assert "test_user" in processor.tables_initialized

    def test_ensure_tables_idempotent(self):
        """Test that ensure_tables is idempotent"""
        processor = MagicMock()
        processor.tables_initialized = {"test_user"}  # Already initialized
        processor.session = MagicMock()
        processor.ensure_tables = Processor.ensure_tables.__get__(processor, Processor)

        processor.ensure_tables("test_user")

        # Should not execute any CQL since already initialized
        processor.session.execute.assert_not_called()


class TestPartitionRegistration:
    """Test partition registration for tracking what's stored"""

    def test_register_partitions(self):
        """Test registering partitions for a collection/schema pair"""
        processor = MagicMock()
        processor.registered_partitions = set()
        processor.session = MagicMock()
        processor.schemas = {
            "test_schema": RowSchema(
                name="test_schema",
                fields=[
                    Field(name="id", type="string", primary=True),
                    Field(name="category", type="string", indexed=True)
                ]
            )
        }
        processor.sanitize_name = Processor.sanitize_name.__get__(processor, Processor)
        processor.get_index_names = Processor.get_index_names.__get__(processor, Processor)
        processor.register_partitions = Processor.register_partitions.__get__(processor, Processor)

        processor.register_partitions("test_user", "test_collection", "test_schema")

        # Should have 2 inserts (one per index: id, category)
        assert processor.session.execute.call_count == 2

        # Verify cache was updated
        assert ("test_collection", "test_schema") in processor.registered_partitions

    def test_register_partitions_idempotent(self):
        """Test that partition registration is idempotent"""
        processor = MagicMock()
        processor.registered_partitions = {("test_collection", "test_schema")}  # Already registered
        processor.session = MagicMock()
        processor.register_partitions = Processor.register_partitions.__get__(processor, Processor)

        processor.register_partitions("test_user", "test_collection", "test_schema")

        # Should not execute any CQL since already registered
        processor.session.execute.assert_not_called()
