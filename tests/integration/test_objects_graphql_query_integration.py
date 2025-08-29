"""
Integration tests for Objects GraphQL Query Service

These tests verify end-to-end functionality including:
- Real Cassandra database operations
- Full GraphQL query execution
- Schema generation and configuration handling
- Message processing with actual Pulsar schemas
"""

import pytest
import json
import asyncio
from unittest.mock import MagicMock, AsyncMock
from testcontainers.cassandra import CassandraContainer

from trustgraph.query.objects.cassandra.service import Processor
from trustgraph.schema import ObjectsQueryRequest, ObjectsQueryResponse, GraphQLError
from trustgraph.schema import RowSchema, Field, ExtractedObject, Metadata


@pytest.mark.integration
class TestObjectsGraphQLQueryIntegration:
    """Integration tests with real Cassandra database"""

    @pytest.fixture(scope="class")
    def cassandra_container(self):
        """Start Cassandra container for testing"""
        with CassandraContainer("cassandra:3.11") as cassandra:
            # Wait for Cassandra to be ready
            cassandra.get_connection_url()
            yield cassandra

    @pytest.fixture
    def processor(self, cassandra_container):
        """Create processor with real Cassandra connection"""
        # Extract host and port from container
        host = cassandra_container.get_container_host_ip()
        port = cassandra_container.get_exposed_port(9042)
        
        # Create processor
        processor = Processor(
            id="test-graphql-query",
            graph_host=host,
            # Note: testcontainer typically doesn't require auth
            graph_username=None,
            graph_password=None,
            config_type="schema"
        )
        
        # Override connection parameters for test container
        processor.graph_host = host
        processor.cluster = None
        processor.session = None
        
        return processor

    @pytest.fixture
    def sample_schema_config(self):
        """Sample schema configuration for testing"""
        return {
            "schema": {
                "customer": json.dumps({
                    "name": "customer",
                    "description": "Customer records",
                    "fields": [
                        {
                            "name": "customer_id",
                            "type": "string",
                            "primary_key": True,
                            "required": True,
                            "description": "Customer identifier"
                        },
                        {
                            "name": "name",
                            "type": "string", 
                            "required": True,
                            "indexed": True,
                            "description": "Customer name"
                        },
                        {
                            "name": "email",
                            "type": "string",
                            "required": True,
                            "indexed": True,
                            "description": "Customer email"
                        },
                        {
                            "name": "status",
                            "type": "string",
                            "required": False,
                            "indexed": True,
                            "enum": ["active", "inactive", "pending"],
                            "description": "Customer status"
                        },
                        {
                            "name": "created_date",
                            "type": "timestamp",
                            "required": False,
                            "description": "Registration date"
                        }
                    ]
                }),
                "order": json.dumps({
                    "name": "order",
                    "description": "Order records",
                    "fields": [
                        {
                            "name": "order_id",
                            "type": "string",
                            "primary_key": True,
                            "required": True
                        },
                        {
                            "name": "customer_id",
                            "type": "string",
                            "required": True,
                            "indexed": True,
                            "description": "Related customer"
                        },
                        {
                            "name": "total",
                            "type": "float",
                            "required": True,
                            "description": "Order total amount"
                        },
                        {
                            "name": "status",
                            "type": "string",
                            "indexed": True,
                            "enum": ["pending", "processing", "shipped", "delivered"],
                            "description": "Order status"
                        }
                    ]
                })
            }
        }

    @pytest.mark.asyncio
    async def test_schema_configuration_and_generation(self, processor, sample_schema_config):
        """Test schema configuration loading and GraphQL schema generation"""
        # Load schema configuration
        await processor.on_schema_config(sample_schema_config, version=1)
        
        # Verify schemas were loaded
        assert len(processor.schemas) == 2
        assert "customer" in processor.schemas
        assert "order" in processor.schemas
        
        # Verify customer schema
        customer_schema = processor.schemas["customer"]
        assert customer_schema.name == "customer"
        assert len(customer_schema.fields) == 5
        
        # Find primary key field
        pk_field = next((f for f in customer_schema.fields if f.primary), None)
        assert pk_field is not None
        assert pk_field.name == "customer_id"
        
        # Verify GraphQL schema was generated
        assert processor.graphql_schema is not None
        assert len(processor.graphql_types) == 2
        assert "customer" in processor.graphql_types
        assert "order" in processor.graphql_types

    @pytest.mark.asyncio
    async def test_cassandra_connection_and_table_creation(self, processor, sample_schema_config):
        """Test Cassandra connection and dynamic table creation"""
        # Load schema configuration
        await processor.on_schema_config(sample_schema_config, version=1)
        
        # Connect to Cassandra
        processor.connect_cassandra()
        assert processor.session is not None
        
        # Create test keyspace and table
        keyspace = "test_user"
        collection = "test_collection"
        schema_name = "customer"
        schema = processor.schemas[schema_name]
        
        # Ensure table creation
        processor.ensure_table(keyspace, schema_name, schema)
        
        # Verify keyspace and table tracking
        assert keyspace in processor.known_keyspaces
        assert keyspace in processor.known_tables
        
        # Verify table was created by querying Cassandra system tables
        safe_keyspace = processor.sanitize_name(keyspace)
        safe_table = processor.sanitize_table(schema_name)
        
        # Check if table exists
        table_query = """
        SELECT table_name FROM system_schema.tables 
        WHERE keyspace_name = %s AND table_name = %s
        """
        result = processor.session.execute(table_query, (safe_keyspace, safe_table))
        rows = list(result)
        assert len(rows) == 1
        assert rows[0].table_name == safe_table

    @pytest.mark.asyncio
    async def test_data_insertion_and_graphql_query(self, processor, sample_schema_config):
        """Test inserting data and querying via GraphQL"""
        # Load schema and connect
        await processor.on_schema_config(sample_schema_config, version=1)
        processor.connect_cassandra()
        
        # Setup test data
        keyspace = "test_user"
        collection = "integration_test"
        schema_name = "customer"
        schema = processor.schemas[schema_name]
        
        # Ensure table exists
        processor.ensure_table(keyspace, schema_name, schema)
        
        # Insert test data directly (simulating what storage processor would do)
        safe_keyspace = processor.sanitize_name(keyspace)
        safe_table = processor.sanitize_table(schema_name)
        
        insert_query = f"""
        INSERT INTO {safe_keyspace}.{safe_table} 
        (collection, customer_id, name, email, status, created_date)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        test_customers = [
            (collection, "CUST001", "John Doe", "john@example.com", "active", "2024-01-15"),
            (collection, "CUST002", "Jane Smith", "jane@example.com", "active", "2024-01-16"),
            (collection, "CUST003", "Bob Wilson", "bob@example.com", "inactive", "2024-01-17")
        ]
        
        for customer_data in test_customers:
            processor.session.execute(insert_query, customer_data)
        
        # Test GraphQL query execution
        graphql_query = '''
        {
            customer_objects(collection: "integration_test") {
                customer_id
                name
                email
                status
            }
        }
        '''
        
        result = await processor.execute_graphql_query(
            query=graphql_query,
            variables={},
            operation_name=None,
            user=keyspace,
            collection=collection
        )
        
        # Verify query results
        assert "data" in result
        assert "customer_objects" in result["data"]
        
        customers = result["data"]["customer_objects"]
        assert len(customers) == 3
        
        # Verify customer data
        customer_ids = [c["customer_id"] for c in customers]
        assert "CUST001" in customer_ids
        assert "CUST002" in customer_ids
        assert "CUST003" in customer_ids
        
        # Find specific customer and verify fields
        john = next(c for c in customers if c["customer_id"] == "CUST001")
        assert john["name"] == "John Doe"
        assert john["email"] == "john@example.com"
        assert john["status"] == "active"

    @pytest.mark.asyncio
    async def test_graphql_query_with_filters(self, processor, sample_schema_config):
        """Test GraphQL queries with filtering on indexed fields"""
        # Setup (reuse previous setup)
        await processor.on_schema_config(sample_schema_config, version=1)
        processor.connect_cassandra()
        
        keyspace = "test_user"
        collection = "filter_test"
        schema_name = "customer"
        schema = processor.schemas[schema_name]
        
        processor.ensure_table(keyspace, schema_name, schema)
        
        # Insert test data
        safe_keyspace = processor.sanitize_name(keyspace)
        safe_table = processor.sanitize_table(schema_name)
        
        insert_query = f"""
        INSERT INTO {safe_keyspace}.{safe_table} 
        (collection, customer_id, name, email, status)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        test_data = [
            (collection, "A001", "Active User 1", "active1@test.com", "active"),
            (collection, "A002", "Active User 2", "active2@test.com", "active"), 
            (collection, "I001", "Inactive User", "inactive@test.com", "inactive")
        ]
        
        for data in test_data:
            processor.session.execute(insert_query, data)
        
        # Query with status filter (indexed field)
        filtered_query = '''
        {
            customer_objects(collection: "filter_test", status: "active") {
                customer_id
                name
                status
            }
        }
        '''
        
        result = await processor.execute_graphql_query(
            query=filtered_query,
            variables={},
            operation_name=None,
            user=keyspace,
            collection=collection
        )
        
        # Verify filtered results
        assert "data" in result
        customers = result["data"]["customer_objects"]
        assert len(customers) == 2  # Only active customers
        
        for customer in customers:
            assert customer["status"] == "active"
            assert customer["customer_id"] in ["A001", "A002"]

    @pytest.mark.asyncio
    async def test_graphql_error_handling(self, processor, sample_schema_config):
        """Test GraphQL error handling for invalid queries"""
        # Setup
        await processor.on_schema_config(sample_schema_config, version=1)
        
        # Test invalid field query
        invalid_query = '''
        {
            customer_objects {
                customer_id
                nonexistent_field
            }
        }
        '''
        
        result = await processor.execute_graphql_query(
            query=invalid_query,
            variables={},
            operation_name=None,
            user="test_user",
            collection="test_collection"
        )
        
        # Verify error response
        assert "errors" in result
        assert len(result["errors"]) > 0
        
        error = result["errors"][0]
        assert "message" in error
        # GraphQL error should mention the invalid field
        assert "nonexistent_field" in error["message"] or "Cannot query field" in error["message"]

    @pytest.mark.asyncio
    async def test_message_processing_integration(self, processor, sample_schema_config):
        """Test full message processing workflow"""
        # Setup
        await processor.on_schema_config(sample_schema_config, version=1)
        processor.connect_cassandra()
        
        # Create mock message
        request = ObjectsQueryRequest(
            user="msg_test_user",
            collection="msg_test_collection",
            query='{ customer_objects { customer_id name } }',
            variables={},
            operation_name=""
        )
        
        mock_msg = MagicMock()
        mock_msg.value.return_value = request
        mock_msg.properties.return_value = {"id": "integration-test-123"}
        
        # Mock flow for response
        mock_response_producer = AsyncMock()
        mock_flow = MagicMock()
        mock_flow.return_value = mock_response_producer
        
        # Process message
        await processor.on_message(mock_msg, None, mock_flow)
        
        # Verify response was sent
        mock_response_producer.send.assert_called_once()
        
        # Verify response structure
        sent_response = mock_response_producer.send.call_args[0][0]
        assert isinstance(sent_response, ObjectsQueryResponse)
        
        # Should have no system error (even if no data)
        assert sent_response.error is None
        
        # Data should be JSON string (even if empty result)
        assert sent_response.data is not None
        assert isinstance(sent_response.data, str)
        
        # Should be able to parse as JSON
        parsed_data = json.loads(sent_response.data)
        assert isinstance(parsed_data, dict)

    @pytest.mark.asyncio
    async def test_concurrent_queries(self, processor, sample_schema_config):
        """Test handling multiple concurrent GraphQL queries"""
        # Setup
        await processor.on_schema_config(sample_schema_config, version=1)
        processor.connect_cassandra()
        
        # Create multiple query tasks
        queries = [
            '{ customer_objects { customer_id } }',
            '{ order_objects { order_id } }',
            '{ customer_objects { name email } }',
            '{ order_objects { total status } }'
        ]
        
        # Execute queries concurrently
        tasks = []
        for i, query in enumerate(queries):
            task = processor.execute_graphql_query(
                query=query,
                variables={},
                operation_name=None,
                user=f"concurrent_user_{i}",
                collection=f"concurrent_collection_{i}"
            )
            tasks.append(task)
        
        # Wait for all queries to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all queries completed without exceptions
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Query {i} failed: {result}"
            assert "data" in result or "errors" in result

    @pytest.mark.asyncio 
    async def test_schema_update_handling(self, processor):
        """Test handling of schema configuration updates"""
        # Load initial schema
        initial_config = {
            "schema": {
                "simple": json.dumps({
                    "name": "simple",
                    "fields": [{"name": "id", "type": "string", "primary_key": True}]
                })
            }
        }
        
        await processor.on_schema_config(initial_config, version=1)
        assert len(processor.schemas) == 1
        assert "simple" in processor.schemas
        
        # Update with additional schema
        updated_config = {
            "schema": {
                "simple": json.dumps({
                    "name": "simple", 
                    "fields": [
                        {"name": "id", "type": "string", "primary_key": True},
                        {"name": "name", "type": "string"}  # New field
                    ]
                }),
                "complex": json.dumps({
                    "name": "complex",
                    "fields": [
                        {"name": "id", "type": "string", "primary_key": True},
                        {"name": "data", "type": "string"}
                    ]
                })
            }
        }
        
        await processor.on_schema_config(updated_config, version=2)
        
        # Verify updated schemas
        assert len(processor.schemas) == 2
        assert "simple" in processor.schemas
        assert "complex" in processor.schemas
        
        # Verify simple schema was updated
        simple_schema = processor.schemas["simple"]
        assert len(simple_schema.fields) == 2
        
        # Verify GraphQL schema was regenerated
        assert len(processor.graphql_types) == 2

    @pytest.mark.asyncio
    async def test_large_result_set_handling(self, processor, sample_schema_config):
        """Test handling of large query result sets"""
        # Setup
        await processor.on_schema_config(sample_schema_config, version=1)
        processor.connect_cassandra()
        
        keyspace = "large_test_user"
        collection = "large_collection"
        schema_name = "customer"
        schema = processor.schemas[schema_name]
        
        processor.ensure_table(keyspace, schema_name, schema)
        
        # Insert larger dataset
        safe_keyspace = processor.sanitize_name(keyspace)
        safe_table = processor.sanitize_table(schema_name)
        
        insert_query = f"""
        INSERT INTO {safe_keyspace}.{safe_table} 
        (collection, customer_id, name, email, status)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        # Insert 50 records
        for i in range(50):
            processor.session.execute(insert_query, (
                collection, 
                f"CUST{i:03d}",
                f"Customer {i}",
                f"customer{i}@test.com",
                "active" if i % 2 == 0 else "inactive"
            ))
        
        # Query with limit
        limited_query = '''
        {
            customer_objects(collection: "large_collection", limit: 10) {
                customer_id
                name
            }
        }
        '''
        
        result = await processor.execute_graphql_query(
            query=limited_query,
            variables={},
            operation_name=None,
            user=keyspace,
            collection=collection
        )
        
        # Verify limited results
        assert "data" in result
        customers = result["data"]["customer_objects"]
        assert len(customers) <= 10  # Should be limited


@pytest.mark.integration
class TestObjectsGraphQLQueryPerformance:
    """Performance-focused integration tests"""
    
    @pytest.mark.asyncio
    async def test_query_execution_timing(self, cassandra_container):
        """Test query execution performance and timeout handling"""
        import time
        
        # Create processor with shorter timeout for testing
        host = cassandra_container.get_container_host_ip()
        
        processor = Processor(
            id="perf-test-graphql-query",
            graph_host=host,
            config_type="schema"
        )
        
        # Load minimal schema
        schema_config = {
            "schema": {
                "perf_test": json.dumps({
                    "name": "perf_test",
                    "fields": [{"name": "id", "type": "string", "primary_key": True}]
                })
            }
        }
        
        await processor.on_schema_config(schema_config, version=1)
        
        # Measure query execution time
        start_time = time.time()
        
        result = await processor.execute_graphql_query(
            query='{ perf_test_objects { id } }',
            variables={},
            operation_name=None,
            user="perf_user",
            collection="perf_collection"
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Verify reasonable execution time (should be under 1 second for empty result)
        assert execution_time < 1.0
        
        # Verify result structure
        assert "data" in result or "errors" in result