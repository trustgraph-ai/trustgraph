"""
Integration tests for Cassandra Row Storage (Unified Table Implementation)

These tests verify the end-to-end functionality of storing ExtractedObjects
in the unified Cassandra rows table, including table creation, data insertion,
and error handling.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json

from trustgraph.storage.rows.cassandra.write import Processor
from trustgraph.schema import ExtractedObject, Metadata, RowSchema, Field


@pytest.mark.integration
class TestRowsCassandraIntegration:
    """Integration tests for Cassandra row storage with unified table"""

    @pytest.fixture
    def mock_cassandra_session(self):
        """Mock Cassandra session for integration tests"""
        session = MagicMock()

        # Track if keyspaces have been created
        created_keyspaces = set()

        # Mock the execute method to return a valid result for keyspace checks
        def execute_mock(query, *args, **kwargs):
            result = MagicMock()
            query_str = str(query)

            # Track keyspace creation
            if "CREATE KEYSPACE" in query_str:
                import re
                match = re.search(r'CREATE KEYSPACE IF NOT EXISTS (\w+)', query_str)
                if match:
                    created_keyspaces.add(match.group(1))

            # For keyspace existence checks
            if "system_schema.keyspaces" in query_str:
                if args and args[0] in created_keyspaces:
                    result.one.return_value = MagicMock()  # Exists
                else:
                    result.one.return_value = None  # Doesn't exist
            else:
                result.one.return_value = None

            return result

        session.execute = MagicMock(side_effect=execute_mock)
        return session

    @pytest.fixture
    def mock_cassandra_cluster(self, mock_cassandra_session):
        """Mock Cassandra cluster"""
        cluster = MagicMock()
        cluster.connect.return_value = mock_cassandra_session
        cluster.shutdown = MagicMock()
        return cluster

    @pytest.fixture
    def processor_with_mocks(self, mock_cassandra_cluster, mock_cassandra_session):
        """Create processor with mocked Cassandra dependencies"""
        processor = MagicMock()
        processor.cassandra_host = ["localhost"]
        processor.cassandra_username = None
        processor.cassandra_password = None
        processor.config_key = "schema"
        processor.schemas = {}
        processor.known_keyspaces = set()
        processor.tables_initialized = set()
        processor.registered_partitions = set()
        processor.cluster = None
        processor.session = None

        # Bind actual methods from the new unified table implementation
        processor.connect_cassandra = Processor.connect_cassandra.__get__(processor, Processor)
        processor.ensure_keyspace = Processor.ensure_keyspace.__get__(processor, Processor)
        processor.ensure_tables = Processor.ensure_tables.__get__(processor, Processor)
        processor.sanitize_name = Processor.sanitize_name.__get__(processor, Processor)
        processor.get_index_names = Processor.get_index_names.__get__(processor, Processor)
        processor.build_index_value = Processor.build_index_value.__get__(processor, Processor)
        processor.register_partitions = Processor.register_partitions.__get__(processor, Processor)
        processor.on_schema_config = Processor.on_schema_config.__get__(processor, Processor)
        processor.on_object = Processor.on_object.__get__(processor, Processor)
        processor.collection_exists = MagicMock(return_value=True)

        return processor, mock_cassandra_cluster, mock_cassandra_session

    @pytest.mark.asyncio
    async def test_end_to_end_object_storage(self, processor_with_mocks):
        """Test complete flow from schema config to object storage"""
        processor, mock_cluster, mock_session = processor_with_mocks

        with patch('trustgraph.storage.rows.cassandra.write.Cluster', return_value=mock_cluster):
            # Step 1: Configure schema
            config = {
                "schema": {
                    "customer_records": json.dumps({
                        "name": "customer_records",
                        "description": "Customer information",
                        "fields": [
                            {"name": "customer_id", "type": "string", "primary_key": True},
                            {"name": "name", "type": "string", "required": True},
                            {"name": "email", "type": "string", "indexed": True},
                            {"name": "age", "type": "integer"}
                        ]
                    })
                }
            }

            await processor.on_schema_config(config, version=1)
            assert "customer_records" in processor.schemas

            # Step 2: Process an ExtractedObject
            test_obj = ExtractedObject(
                metadata=Metadata(
                    id="doc-001",
                    user="test_user",
                    collection="import_2024",
                    metadata=[]
                ),
                schema_name="customer_records",
                values=[{
                    "customer_id": "CUST001",
                    "name": "John Doe",
                    "email": "john@example.com",
                    "age": "30"
                }],
                confidence=0.95,
                source_span="Customer: John Doe..."
            )

            msg = MagicMock()
            msg.value.return_value = test_obj

            await processor.on_object(msg, None, None)

            # Verify Cassandra interactions
            assert mock_cluster.connect.called

            # Verify keyspace creation
            keyspace_calls = [call for call in mock_session.execute.call_args_list
                            if "CREATE KEYSPACE" in str(call)]
            assert len(keyspace_calls) == 1
            assert "test_user" in str(keyspace_calls[0])

            # Verify unified table creation (rows table, not per-schema table)
            table_calls = [call for call in mock_session.execute.call_args_list
                         if "CREATE TABLE" in str(call)]
            assert len(table_calls) == 2  # rows table + row_partitions table
            assert any("rows" in str(call) for call in table_calls)
            assert any("row_partitions" in str(call) for call in table_calls)

            # Verify the rows table has correct structure
            rows_table_call = [call for call in table_calls if ".rows" in str(call)][0]
            assert "collection text" in str(rows_table_call)
            assert "schema_name text" in str(rows_table_call)
            assert "index_name text" in str(rows_table_call)
            assert "data map<text, text>" in str(rows_table_call)

            # Verify data insertion into unified table
            rows_insert_calls = [call for call in mock_session.execute.call_args_list
                          if "INSERT INTO" in str(call) and ".rows" in str(call)
                          and "row_partitions" not in str(call)]
            # Should have 2 data inserts: one for customer_id (primary), one for email (indexed)
            assert len(rows_insert_calls) == 2

    @pytest.mark.asyncio
    async def test_multi_schema_handling(self, processor_with_mocks):
        """Test handling multiple schemas stored in unified table"""
        processor, mock_cluster, mock_session = processor_with_mocks

        with patch('trustgraph.storage.rows.cassandra.write.Cluster', return_value=mock_cluster):
            # Configure multiple schemas
            config = {
                "schema": {
                    "products": json.dumps({
                        "name": "products",
                        "fields": [
                            {"name": "product_id", "type": "string", "primary_key": True},
                            {"name": "name", "type": "string"},
                            {"name": "price", "type": "float"}
                        ]
                    }),
                    "orders": json.dumps({
                        "name": "orders",
                        "fields": [
                            {"name": "order_id", "type": "string", "primary_key": True},
                            {"name": "customer_id", "type": "string"},
                            {"name": "total", "type": "float"}
                        ]
                    })
                }
            }

            await processor.on_schema_config(config, version=1)
            assert len(processor.schemas) == 2

            # Process objects for different schemas
            product_obj = ExtractedObject(
                metadata=Metadata(id="p1", user="shop", collection="catalog", metadata=[]),
                schema_name="products",
                values=[{"product_id": "P001", "name": "Widget", "price": "19.99"}],
                confidence=0.9,
                source_span="Product..."
            )

            order_obj = ExtractedObject(
                metadata=Metadata(id="o1", user="shop", collection="sales", metadata=[]),
                schema_name="orders",
                values=[{"order_id": "O001", "customer_id": "C001", "total": "59.97"}],
                confidence=0.85,
                source_span="Order..."
            )

            # Process both objects
            for obj in [product_obj, order_obj]:
                msg = MagicMock()
                msg.value.return_value = obj
                await processor.on_object(msg, None, None)

            # All data goes into the same unified rows table
            table_calls = [call for call in mock_session.execute.call_args_list
                         if "CREATE TABLE" in str(call)]
            # Should only create 2 tables: rows + row_partitions (not per-schema tables)
            assert len(table_calls) == 2

            # Verify data inserts go to unified rows table
            rows_insert_calls = [call for call in mock_session.execute.call_args_list
                          if "INSERT INTO" in str(call) and ".rows" in str(call)
                          and "row_partitions" not in str(call)]
            assert len(rows_insert_calls) > 0
            for call in rows_insert_calls:
                assert ".rows" in str(call)

    @pytest.mark.asyncio
    async def test_multi_index_storage(self, processor_with_mocks):
        """Test that rows are stored with multiple indexes"""
        processor, mock_cluster, mock_session = processor_with_mocks

        with patch('trustgraph.storage.rows.cassandra.write.Cluster', return_value=mock_cluster):
            # Schema with multiple indexed fields
            processor.schemas["indexed_data"] = RowSchema(
                name="indexed_data",
                fields=[
                    Field(name="id", type="string", size=50, primary=True),
                    Field(name="category", type="string", size=50, indexed=True),
                    Field(name="status", type="string", size=50, indexed=True),
                    Field(name="description", type="string", size=200)  # Not indexed
                ]
            )

            test_obj = ExtractedObject(
                metadata=Metadata(id="t1", user="test", collection="test", metadata=[]),
                schema_name="indexed_data",
                values=[{
                    "id": "123",
                    "category": "electronics",
                    "status": "active",
                    "description": "A product"
                }],
                confidence=0.9,
                source_span="Test"
            )

            msg = MagicMock()
            msg.value.return_value = test_obj

            await processor.on_object(msg, None, None)

            # Should have 3 data inserts (one per indexed field: id, category, status)
            rows_insert_calls = [call for call in mock_session.execute.call_args_list
                          if "INSERT INTO" in str(call) and ".rows" in str(call)
                          and "row_partitions" not in str(call)]
            assert len(rows_insert_calls) == 3

            # Verify different index names were used
            index_names = set()
            for call in rows_insert_calls:
                values = call[0][1]
                index_names.add(values[2])  # index_name is 3rd parameter

            assert index_names == {"id", "category", "status"}

    @pytest.mark.asyncio
    async def test_authentication_handling(self, processor_with_mocks):
        """Test Cassandra authentication"""
        processor, mock_cluster, mock_session = processor_with_mocks
        processor.cassandra_username = "cassandra_user"
        processor.cassandra_password = "cassandra_pass"

        with patch('trustgraph.storage.rows.cassandra.write.Cluster') as mock_cluster_class:
            with patch('trustgraph.storage.rows.cassandra.write.PlainTextAuthProvider') as mock_auth:
                mock_cluster_class.return_value = mock_cluster

                # Trigger connection
                processor.connect_cassandra()

                # Verify authentication was configured
                mock_auth.assert_called_once_with(
                    username="cassandra_user",
                    password="cassandra_pass"
                )
                mock_cluster_class.assert_called_once()
                call_kwargs = mock_cluster_class.call_args[1]
                assert 'auth_provider' in call_kwargs

    @pytest.mark.asyncio
    async def test_batch_object_processing(self, processor_with_mocks):
        """Test processing objects with batched values"""
        processor, mock_cluster, mock_session = processor_with_mocks

        with patch('trustgraph.storage.rows.cassandra.write.Cluster', return_value=mock_cluster):
            # Configure schema
            config = {
                "schema": {
                    "batch_customers": json.dumps({
                        "name": "batch_customers",
                        "description": "Customer batch data",
                        "fields": [
                            {"name": "customer_id", "type": "string", "primary_key": True},
                            {"name": "name", "type": "string", "required": True},
                            {"name": "email", "type": "string", "indexed": True}
                        ]
                    })
                }
            }

            await processor.on_schema_config(config, version=1)

            # Process batch object with multiple values
            batch_obj = ExtractedObject(
                metadata=Metadata(
                    id="batch-001",
                    user="test_user",
                    collection="batch_import",
                    metadata=[]
                ),
                schema_name="batch_customers",
                values=[
                    {
                        "customer_id": "CUST001",
                        "name": "John Doe",
                        "email": "john@example.com"
                    },
                    {
                        "customer_id": "CUST002",
                        "name": "Jane Smith",
                        "email": "jane@example.com"
                    },
                    {
                        "customer_id": "CUST003",
                        "name": "Bob Johnson",
                        "email": "bob@example.com"
                    }
                ],
                confidence=0.92,
                source_span="Multiple customers extracted from document"
            )

            msg = MagicMock()
            msg.value.return_value = batch_obj

            await processor.on_object(msg, None, None)

            # Verify unified table creation
            table_calls = [call for call in mock_session.execute.call_args_list
                         if "CREATE TABLE" in str(call)]
            assert len(table_calls) == 2  # rows + row_partitions

            # Each row in batch gets 2 data inserts (customer_id primary + email indexed)
            # 3 rows * 2 indexes = 6 data inserts
            rows_insert_calls = [call for call in mock_session.execute.call_args_list
                          if "INSERT INTO" in str(call) and ".rows" in str(call)
                          and "row_partitions" not in str(call)]
            assert len(rows_insert_calls) == 6

    @pytest.mark.asyncio
    async def test_empty_batch_processing(self, processor_with_mocks):
        """Test processing objects with empty values array"""
        processor, mock_cluster, mock_session = processor_with_mocks

        with patch('trustgraph.storage.rows.cassandra.write.Cluster', return_value=mock_cluster):
            processor.schemas["empty_test"] = RowSchema(
                name="empty_test",
                fields=[Field(name="id", type="string", size=50, primary=True)]
            )

            # Process empty batch object
            empty_obj = ExtractedObject(
                metadata=Metadata(id="empty-1", user="test", collection="empty", metadata=[]),
                schema_name="empty_test",
                values=[],  # Empty batch
                confidence=1.0,
                source_span="No objects found"
            )

            msg = MagicMock()
            msg.value.return_value = empty_obj

            await processor.on_object(msg, None, None)

            # Should not create any data insert statements for empty batch
            # (partition registration may still happen)
            rows_insert_calls = [call for call in mock_session.execute.call_args_list
                          if "INSERT INTO" in str(call) and ".rows" in str(call)
                          and "row_partitions" not in str(call)]
            assert len(rows_insert_calls) == 0

    @pytest.mark.asyncio
    async def test_data_stored_as_map(self, processor_with_mocks):
        """Test that data is stored as map<text, text>"""
        processor, mock_cluster, mock_session = processor_with_mocks

        with patch('trustgraph.storage.rows.cassandra.write.Cluster', return_value=mock_cluster):
            processor.schemas["map_test"] = RowSchema(
                name="map_test",
                fields=[
                    Field(name="id", type="string", size=50, primary=True),
                    Field(name="name", type="string", size=100),
                    Field(name="count", type="integer", size=0)
                ]
            )

            test_obj = ExtractedObject(
                metadata=Metadata(id="t1", user="test", collection="test", metadata=[]),
                schema_name="map_test",
                values=[{"id": "123", "name": "Test Item", "count": "42"}],
                confidence=0.9,
                source_span="Test"
            )

            msg = MagicMock()
            msg.value.return_value = test_obj

            await processor.on_object(msg, None, None)

            # Verify insert uses map for data
            rows_insert_calls = [call for call in mock_session.execute.call_args_list
                          if "INSERT INTO" in str(call) and ".rows" in str(call)
                          and "row_partitions" not in str(call)]
            assert len(rows_insert_calls) >= 1

            # Check that data is passed as a dict (will be map in Cassandra)
            insert_call = rows_insert_calls[0]
            values = insert_call[0][1]
            # Values are: (collection, schema_name, index_name, index_value, data, source)
            # values[4] should be the data map
            data_map = values[4]
            assert isinstance(data_map, dict)
            assert data_map["id"] == "123"
            assert data_map["name"] == "Test Item"
            assert data_map["count"] == "42"

    @pytest.mark.asyncio
    async def test_partition_registration(self, processor_with_mocks):
        """Test that partitions are registered for efficient querying"""
        processor, mock_cluster, mock_session = processor_with_mocks

        with patch('trustgraph.storage.rows.cassandra.write.Cluster', return_value=mock_cluster):
            processor.schemas["partition_test"] = RowSchema(
                name="partition_test",
                fields=[
                    Field(name="id", type="string", size=50, primary=True),
                    Field(name="category", type="string", size=50, indexed=True)
                ]
            )

            test_obj = ExtractedObject(
                metadata=Metadata(id="t1", user="test", collection="my_collection", metadata=[]),
                schema_name="partition_test",
                values=[{"id": "123", "category": "test"}],
                confidence=0.9,
                source_span="Test"
            )

            msg = MagicMock()
            msg.value.return_value = test_obj

            await processor.on_object(msg, None, None)

            # Verify partition registration
            partition_inserts = [call for call in mock_session.execute.call_args_list
                                if "INSERT INTO" in str(call) and "row_partitions" in str(call)]
            # Should register partitions for each index (id, category)
            assert len(partition_inserts) == 2

            # Verify cache was updated
            assert ("my_collection", "partition_test") in processor.registered_partitions
