"""
Integration tests for Cassandra Object Storage

These tests verify the end-to-end functionality of storing ExtractedObjects
in Cassandra, including table creation, data insertion, and error handling.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json
import uuid

from trustgraph.storage.objects.cassandra.write import Processor
from trustgraph.schema import ExtractedObject, Metadata, RowSchema, Field


@pytest.mark.integration
class TestObjectsCassandraIntegration:
    """Integration tests for Cassandra object storage"""

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
                # Extract keyspace name from query
                import re
                match = re.search(r'CREATE KEYSPACE IF NOT EXISTS (\w+)', query_str)
                if match:
                    created_keyspaces.add(match.group(1))

            # For keyspace existence checks
            if "system_schema.keyspaces" in query_str:
                # Check if this keyspace was created
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
        processor.graph_host = "localhost"
        processor.graph_username = None
        processor.graph_password = None
        processor.config_key = "schema"
        processor.schemas = {}
        processor.known_keyspaces = set()
        processor.known_tables = {}
        processor.cluster = None
        processor.session = None
        
        # Bind actual methods
        processor.connect_cassandra = Processor.connect_cassandra.__get__(processor, Processor)
        processor.ensure_keyspace = Processor.ensure_keyspace.__get__(processor, Processor)
        processor.ensure_table = Processor.ensure_table.__get__(processor, Processor)
        processor.sanitize_name = Processor.sanitize_name.__get__(processor, Processor)
        processor.sanitize_table = Processor.sanitize_table.__get__(processor, Processor)
        processor.get_cassandra_type = Processor.get_cassandra_type.__get__(processor, Processor)
        processor.convert_value = Processor.convert_value.__get__(processor, Processor)
        processor.on_schema_config = Processor.on_schema_config.__get__(processor, Processor)
        processor.on_object = Processor.on_object.__get__(processor, Processor)
        
        return processor, mock_cassandra_cluster, mock_cassandra_session

    @pytest.mark.asyncio
    async def test_end_to_end_object_storage(self, processor_with_mocks):
        """Test complete flow from schema config to object storage"""
        processor, mock_cluster, mock_session = processor_with_mocks
        
        # Mock Cluster creation
        with patch('trustgraph.storage.objects.cassandra.write.Cluster', return_value=mock_cluster):
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

            # Step 1.5: Create the collection first (simulate tg-set-collection)
            await processor.create_collection("test_user", "import_2024")

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
            
            # Verify table creation
            table_calls = [call for call in mock_session.execute.call_args_list 
                         if "CREATE TABLE" in str(call)]
            assert len(table_calls) == 1
            assert "o_customer_records" in str(table_calls[0])  # Table gets o_ prefix
            assert "collection text" in str(table_calls[0])
            assert "PRIMARY KEY ((collection, customer_id))" in str(table_calls[0])
            
            # Verify index creation
            index_calls = [call for call in mock_session.execute.call_args_list 
                         if "CREATE INDEX" in str(call)]
            assert len(index_calls) == 1
            assert "email" in str(index_calls[0])
            
            # Verify data insertion
            insert_calls = [call for call in mock_session.execute.call_args_list 
                          if "INSERT INTO" in str(call)]
            assert len(insert_calls) == 1
            insert_call = insert_calls[0]
            assert "test_user.o_customer_records" in str(insert_call)  # Table gets o_ prefix
            
            # Check inserted values
            values = insert_call[0][1]
            assert "import_2024" in values  # collection
            assert "CUST001" in values      # customer_id
            assert "John Doe" in values     # name
            assert "john@example.com" in values  # email
            assert 30 in values             # age (converted to int)

    @pytest.mark.asyncio
    async def test_multi_schema_handling(self, processor_with_mocks):
        """Test handling multiple schemas and objects"""
        processor, mock_cluster, mock_session = processor_with_mocks
        
        with patch('trustgraph.storage.objects.cassandra.write.Cluster', return_value=mock_cluster):
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

            # Create collections first
            await processor.create_collection("shop", "catalog")
            await processor.create_collection("shop", "sales")

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
            
            # Verify separate tables were created
            table_calls = [call for call in mock_session.execute.call_args_list 
                         if "CREATE TABLE" in str(call)]
            assert len(table_calls) == 2
            assert any("o_products" in str(call) for call in table_calls)  # Tables get o_ prefix
            assert any("o_orders" in str(call) for call in table_calls)    # Tables get o_ prefix

    @pytest.mark.asyncio
    async def test_missing_required_fields(self, processor_with_mocks):
        """Test handling of objects with missing required fields"""
        processor, mock_cluster, mock_session = processor_with_mocks
        
        with patch('trustgraph.storage.objects.cassandra.write.Cluster', return_value=mock_cluster):
            # Configure schema with required field
            processor.schemas["test_schema"] = RowSchema(
                name="test_schema",
                description="Test",
                fields=[
                    Field(name="id", type="string", size=50, primary=True, required=True),
                    Field(name="required_field", type="string", size=100, required=True)
                ]
            )
            
            # Create object missing required field
            test_obj = ExtractedObject(
                metadata=Metadata(id="t1", user="test", collection="test", metadata=[]),
                schema_name="test_schema",
                values=[{"id": "123"}],  # missing required_field
                confidence=0.8,
                source_span="Test"
            )
            
            msg = MagicMock()
            msg.value.return_value = test_obj
            
            # Should still process (Cassandra doesn't enforce NOT NULL)
            await processor.on_object(msg, None, None)
            
            # Verify insert was attempted
            insert_calls = [call for call in mock_session.execute.call_args_list 
                          if "INSERT INTO" in str(call)]
            assert len(insert_calls) == 1

    @pytest.mark.asyncio
    async def test_schema_without_primary_key(self, processor_with_mocks):
        """Test handling schemas without defined primary keys"""
        processor, mock_cluster, mock_session = processor_with_mocks
        
        with patch('trustgraph.storage.objects.cassandra.write.Cluster', return_value=mock_cluster):
            # Configure schema without primary key
            processor.schemas["events"] = RowSchema(
                name="events",
                description="Event log",
                fields=[
                    Field(name="event_type", type="string", size=50),
                    Field(name="timestamp", type="timestamp", size=0)
                ]
            )
            
            # Process object
            test_obj = ExtractedObject(
                metadata=Metadata(id="e1", user="logger", collection="app_events", metadata=[]),
                schema_name="events",
                values=[{"event_type": "login", "timestamp": "2024-01-01T10:00:00Z"}],
                confidence=1.0,
                source_span="Event"
            )
            
            msg = MagicMock()
            msg.value.return_value = test_obj
            
            await processor.on_object(msg, None, None)
            
            # Verify synthetic_id was added
            table_calls = [call for call in mock_session.execute.call_args_list 
                         if "CREATE TABLE" in str(call)]
            assert len(table_calls) == 1
            assert "synthetic_id uuid" in str(table_calls[0])
            
            # Verify insert includes UUID
            insert_calls = [call for call in mock_session.execute.call_args_list 
                          if "INSERT INTO" in str(call)]
            assert len(insert_calls) == 1
            values = insert_calls[0][0][1]
            # Check that a UUID was generated (will be in values list)
            uuid_found = any(isinstance(v, uuid.UUID) for v in values)
            assert uuid_found

    @pytest.mark.asyncio
    async def test_authentication_handling(self, processor_with_mocks):
        """Test Cassandra authentication"""
        processor, mock_cluster, mock_session = processor_with_mocks
        processor.cassandra_username = "cassandra_user"
        processor.cassandra_password = "cassandra_pass"
        
        with patch('trustgraph.storage.objects.cassandra.write.Cluster') as mock_cluster_class:
            with patch('trustgraph.storage.objects.cassandra.write.PlainTextAuthProvider') as mock_auth:
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
    async def test_error_handling_during_insert(self, processor_with_mocks):
        """Test error handling when insertion fails"""
        processor, mock_cluster, mock_session = processor_with_mocks
        
        with patch('trustgraph.storage.objects.cassandra.write.Cluster', return_value=mock_cluster):
            processor.schemas["test"] = RowSchema(
                name="test",
                fields=[Field(name="id", type="string", size=50, primary=True)]
            )
            
            # Make insert fail
            mock_result = MagicMock()
            mock_result.one.return_value = MagicMock()  # Keyspace exists
            mock_session.execute.side_effect = [
                mock_result,  # keyspace existence check succeeds
                None,  # table creation succeeds
                Exception("Connection timeout")  # insert fails
            ]
            
            test_obj = ExtractedObject(
                metadata=Metadata(id="t1", user="test", collection="test", metadata=[]),
                schema_name="test",
                values=[{"id": "123"}],
                confidence=0.9,
                source_span="Test"
            )
            
            msg = MagicMock()
            msg.value.return_value = test_obj
            
            # Should raise the exception
            with pytest.raises(Exception, match="Connection timeout"):
                await processor.on_object(msg, None, None)

    @pytest.mark.asyncio
    async def test_collection_partitioning(self, processor_with_mocks):
        """Test that objects are properly partitioned by collection"""
        processor, mock_cluster, mock_session = processor_with_mocks
        
        with patch('trustgraph.storage.objects.cassandra.write.Cluster', return_value=mock_cluster):
            processor.schemas["data"] = RowSchema(
                name="data",
                fields=[Field(name="id", type="string", size=50, primary=True)]
            )
            
            # Process objects from different collections
            collections = ["import_jan", "import_feb", "import_mar"]
            
            for coll in collections:
                obj = ExtractedObject(
                    metadata=Metadata(id=f"{coll}-1", user="analytics", collection=coll, metadata=[]),
                    schema_name="data",
                    values=[{"id": f"ID-{coll}"}],
                    confidence=0.9,
                    source_span="Data"
                )
                
                msg = MagicMock()
                msg.value.return_value = obj
                await processor.on_object(msg, None, None)
            
            # Verify all inserts include collection in values
            insert_calls = [call for call in mock_session.execute.call_args_list 
                          if "INSERT INTO" in str(call)]
            assert len(insert_calls) == 3
            
            # Check each insert has the correct collection
            for i, call in enumerate(insert_calls):
                values = call[0][1]
                assert collections[i] in values

    @pytest.mark.asyncio
    async def test_batch_object_processing(self, processor_with_mocks):
        """Test processing objects with batched values"""
        processor, mock_cluster, mock_session = processor_with_mocks
        
        with patch('trustgraph.storage.objects.cassandra.write.Cluster', return_value=mock_cluster):
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
            
            # Verify table creation
            table_calls = [call for call in mock_session.execute.call_args_list 
                         if "CREATE TABLE" in str(call)]
            assert len(table_calls) == 1
            assert "o_batch_customers" in str(table_calls[0])
            
            # Verify multiple inserts for batch values
            insert_calls = [call for call in mock_session.execute.call_args_list 
                          if "INSERT INTO" in str(call)]
            # Should have 3 separate inserts for the 3 objects in the batch
            assert len(insert_calls) == 3
            
            # Check each insert has correct data
            for i, call in enumerate(insert_calls):
                values = call[0][1]
                assert "batch_import" in values  # collection
                assert f"CUST00{i+1}" in values  # customer_id
                if i == 0:
                    assert "John Doe" in values
                    assert "john@example.com" in values
                elif i == 1:
                    assert "Jane Smith" in values
                    assert "jane@example.com" in values
                elif i == 2:
                    assert "Bob Johnson" in values
                    assert "bob@example.com" in values

    @pytest.mark.asyncio
    async def test_empty_batch_processing(self, processor_with_mocks):
        """Test processing objects with empty values array"""
        processor, mock_cluster, mock_session = processor_with_mocks
        
        with patch('trustgraph.storage.objects.cassandra.write.Cluster', return_value=mock_cluster):
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
            
            # Should still create table
            table_calls = [call for call in mock_session.execute.call_args_list 
                         if "CREATE TABLE" in str(call)]
            assert len(table_calls) == 1
            
            # Should not create any insert statements for empty batch
            insert_calls = [call for call in mock_session.execute.call_args_list 
                          if "INSERT INTO" in str(call)]
            assert len(insert_calls) == 0

    @pytest.mark.asyncio
    async def test_mixed_single_and_batch_objects(self, processor_with_mocks):
        """Test processing mix of single and batch objects"""
        processor, mock_cluster, mock_session = processor_with_mocks
        
        with patch('trustgraph.storage.objects.cassandra.write.Cluster', return_value=mock_cluster):
            processor.schemas["mixed_test"] = RowSchema(
                name="mixed_test",
                fields=[
                    Field(name="id", type="string", size=50, primary=True),
                    Field(name="data", type="string", size=100)
                ]
            )
            
            # Single object (backward compatibility)
            single_obj = ExtractedObject(
                metadata=Metadata(id="single", user="test", collection="mixed", metadata=[]),
                schema_name="mixed_test",
                values=[{"id": "single-1", "data": "single data"}],  # Array with single item
                confidence=0.9,
                source_span="Single object"
            )
            
            # Batch object
            batch_obj = ExtractedObject(
                metadata=Metadata(id="batch", user="test", collection="mixed", metadata=[]),
                schema_name="mixed_test",
                values=[
                    {"id": "batch-1", "data": "batch data 1"},
                    {"id": "batch-2", "data": "batch data 2"}
                ],
                confidence=0.85,
                source_span="Batch objects"
            )
            
            # Process both
            for obj in [single_obj, batch_obj]:
                msg = MagicMock()
                msg.value.return_value = obj
                await processor.on_object(msg, None, None)
            
            # Should have 3 total inserts (1 + 2)
            insert_calls = [call for call in mock_session.execute.call_args_list 
                          if "INSERT INTO" in str(call)]
            assert len(insert_calls) == 3