"""
Integration tests for Object Extraction Service

These tests verify the end-to-end functionality of the object extraction service,
testing configuration management, text-to-object transformation, and service coordination.
Following the TEST_STRATEGY.md approach for integration testing.
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from trustgraph.extract.kg.objects.processor import Processor
from trustgraph.schema import (
    Chunk, ExtractedObject, Metadata, RowSchema, Field,
    PromptRequest, PromptResponse
)


@pytest.mark.integration
class TestObjectExtractionServiceIntegration:
    """Integration tests for Object Extraction Service"""

    @pytest.fixture
    def integration_config(self):
        """Integration test configuration with multiple schemas"""
        customer_schema = {
            "name": "customer_records",
            "description": "Customer information schema",
            "fields": [
                {
                    "name": "customer_id",
                    "type": "string", 
                    "primary_key": True,
                    "required": True,
                    "indexed": True,
                    "description": "Unique customer identifier"
                },
                {
                    "name": "name",
                    "type": "string",
                    "required": True,
                    "description": "Customer full name"
                },
                {
                    "name": "email",
                    "type": "string",
                    "required": True,
                    "indexed": True,
                    "description": "Customer email address"
                },
                {
                    "name": "phone",
                    "type": "string", 
                    "required": False,
                    "description": "Customer phone number"
                }
            ]
        }
        
        product_schema = {
            "name": "product_catalog",
            "description": "Product catalog schema",
            "fields": [
                {
                    "name": "product_id",
                    "type": "string",
                    "primary_key": True,
                    "required": True,
                    "indexed": True,
                    "description": "Unique product identifier"
                },
                {
                    "name": "name",
                    "type": "string",
                    "required": True,
                    "description": "Product name"
                },
                {
                    "name": "price",
                    "type": "double",
                    "required": True,
                    "description": "Product price"
                },
                {
                    "name": "category",
                    "type": "string",
                    "required": False,
                    "enum": ["electronics", "clothing", "books", "home"],
                    "description": "Product category"
                }
            ]
        }
        
        return {
            "schema": {
                "customer_records": json.dumps(customer_schema),
                "product_catalog": json.dumps(product_schema)
            }
        }

    @pytest.fixture
    def mock_integrated_flow(self):
        """Mock integrated flow context with realistic prompt responses"""
        context = MagicMock()
        
        # Mock prompt client with realistic responses
        prompt_client = AsyncMock()
        
        def mock_extract_rows(schema, text):
            """Mock extract_rows with schema-aware responses"""
            if schema.name == "customer_records":
                if "john" in text.lower():
                    return [
                        {
                            "customer_id": "CUST001",
                            "name": "John Smith", 
                            "email": "john.smith@email.com",
                            "phone": "555-0123"
                        }
                    ]
                elif "jane" in text.lower():
                    return [
                        {
                            "customer_id": "CUST002",
                            "name": "Jane Doe",
                            "email": "jane.doe@email.com",
                            "phone": ""
                        }
                    ]
                else:
                    return []
            
            elif schema.name == "product_catalog":
                if "laptop" in text.lower():
                    return [
                        {
                            "product_id": "PROD001",
                            "name": "Gaming Laptop",
                            "price": "1299.99",
                            "category": "electronics"
                        }
                    ]
                elif "book" in text.lower():
                    return [
                        {
                            "product_id": "PROD002", 
                            "name": "Python Programming Guide",
                            "price": "49.99",
                            "category": "books"
                        }
                    ]
                else:
                    return []
            
            return []
        
        prompt_client.extract_rows.side_effect = mock_extract_rows
        
        # Mock output producer
        output_producer = AsyncMock()
        
        def context_router(service_name):
            if service_name == "prompt-request":
                return prompt_client
            elif service_name == "output":
                return output_producer
            else:
                return AsyncMock()
        
        context.side_effect = context_router
        return context

    @pytest.mark.asyncio
    async def test_multi_schema_configuration_integration(self, integration_config):
        """Test integration with multiple schema configurations"""
        # Arrange - Create mock processor with actual methods
        processor = MagicMock()
        processor.schemas = {}
        processor.config_key = "schema"
        processor.on_schema_config = Processor.on_schema_config.__get__(processor, Processor)
        
        # Act
        await processor.on_schema_config(integration_config, version=1)
        
        # Assert
        assert len(processor.schemas) == 2
        assert "customer_records" in processor.schemas
        assert "product_catalog" in processor.schemas
        
        # Verify customer schema
        customer_schema = processor.schemas["customer_records"]
        assert customer_schema.name == "customer_records"
        assert len(customer_schema.fields) == 4
        
        # Verify product schema
        product_schema = processor.schemas["product_catalog"]
        assert product_schema.name == "product_catalog"
        assert len(product_schema.fields) == 4
        
        # Check enum field in product schema
        category_field = next((f for f in product_schema.fields if f.name == "category"), None)
        assert category_field is not None
        assert len(category_field.enum_values) == 4
        assert "electronics" in category_field.enum_values

    @pytest.mark.asyncio
    async def test_full_service_integration_customer_extraction(self, integration_config, mock_integrated_flow):
        """Test full service integration for customer data extraction"""
        # Arrange - Create mock processor with actual methods
        processor = MagicMock()
        processor.schemas = {}
        processor.config_key = "schema"
        processor.flow = mock_integrated_flow
        processor.on_schema_config = Processor.on_schema_config.__get__(processor, Processor)
        processor.on_chunk = Processor.on_chunk.__get__(processor, Processor)
        processor.extract_objects_for_schema = Processor.extract_objects_for_schema.__get__(processor, Processor)
        
        # Load configuration
        await processor.on_schema_config(integration_config, version=1)
        
        # Create realistic customer data chunk
        metadata = Metadata(
            id="customer-doc-001",
            user="integration_test",
            collection="test_documents",
            metadata=[]
        )
        
        chunk_text = """
        Customer Registration Form
        
        Name: John Smith
        Email: john.smith@email.com
        Phone: 555-0123
        Customer ID: CUST001
        
        Registration completed successfully.
        """
        
        chunk = Chunk(metadata=metadata, chunk=chunk_text.encode('utf-8'))
        
        # Mock message
        mock_msg = MagicMock()
        mock_msg.value.return_value = chunk
        
        # Act
        await processor.on_chunk(mock_msg, None, mock_integrated_flow)
        
        # Assert
        output_producer = mock_integrated_flow("output")
        
        # Should have calls for both schemas (even if one returns empty)
        assert output_producer.send.call_count >= 1
        
        # Find customer extraction
        customer_calls = []
        for call in output_producer.send.call_args_list:
            extracted_obj = call[0][0]
            if extracted_obj.schema_name == "customer_records":
                customer_calls.append(extracted_obj)
        
        assert len(customer_calls) == 1
        customer_obj = customer_calls[0]
        
        assert customer_obj.values["customer_id"] == "CUST001"
        assert customer_obj.values["name"] == "John Smith"
        assert customer_obj.values["email"] == "john.smith@email.com"
        assert customer_obj.confidence > 0.5

    @pytest.mark.asyncio
    async def test_full_service_integration_product_extraction(self, integration_config, mock_integrated_flow):
        """Test full service integration for product data extraction"""
        # Arrange - Create mock processor with actual methods
        processor = MagicMock()
        processor.schemas = {}
        processor.config_key = "schema"
        processor.flow = mock_integrated_flow
        processor.on_schema_config = Processor.on_schema_config.__get__(processor, Processor)
        processor.on_chunk = Processor.on_chunk.__get__(processor, Processor)
        processor.extract_objects_for_schema = Processor.extract_objects_for_schema.__get__(processor, Processor)
        
        # Load configuration
        await processor.on_schema_config(integration_config, version=1)
        
        # Create realistic product data chunk
        metadata = Metadata(
            id="product-doc-001",
            user="integration_test",
            collection="test_documents",
            metadata=[]
        )
        
        chunk_text = """
        Product Specification Sheet
        
        Product Name: Gaming Laptop
        Product ID: PROD001
        Price: $1,299.99
        Category: Electronics
        
        High-performance gaming laptop with latest specifications.
        """
        
        chunk = Chunk(metadata=metadata, chunk=chunk_text.encode('utf-8'))
        
        # Mock message
        mock_msg = MagicMock()
        mock_msg.value.return_value = chunk
        
        # Act
        await processor.on_chunk(mock_msg, None, mock_integrated_flow)
        
        # Assert
        output_producer = mock_integrated_flow("output")
        
        # Find product extraction
        product_calls = []
        for call in output_producer.send.call_args_list:
            extracted_obj = call[0][0]
            if extracted_obj.schema_name == "product_catalog":
                product_calls.append(extracted_obj)
        
        assert len(product_calls) == 1
        product_obj = product_calls[0]
        
        assert product_obj.values["product_id"] == "PROD001"
        assert product_obj.values["name"] == "Gaming Laptop"
        assert product_obj.values["price"] == "1299.99"
        assert product_obj.values["category"] == "electronics"

    @pytest.mark.asyncio
    async def test_concurrent_extraction_integration(self, integration_config, mock_integrated_flow):
        """Test concurrent processing of multiple chunks"""
        # Arrange - Create mock processor with actual methods
        processor = MagicMock()
        processor.schemas = {}
        processor.config_key = "schema"
        processor.flow = mock_integrated_flow
        processor.on_schema_config = Processor.on_schema_config.__get__(processor, Processor)
        processor.on_chunk = Processor.on_chunk.__get__(processor, Processor)
        processor.extract_objects_for_schema = Processor.extract_objects_for_schema.__get__(processor, Processor)
        
        # Load configuration
        await processor.on_schema_config(integration_config, version=1)
        
        # Create multiple test chunks
        chunks_data = [
            ("customer-chunk-1", "Customer: John Smith, email: john.smith@email.com, ID: CUST001"),
            ("customer-chunk-2", "Customer: Jane Doe, email: jane.doe@email.com, ID: CUST002"),
            ("product-chunk-1", "Product: Gaming Laptop, ID: PROD001, Price: $1299.99, Category: electronics"),
            ("product-chunk-2", "Product: Python Programming Guide, ID: PROD002, Price: $49.99, Category: books")
        ]
        
        chunks = []
        for chunk_id, text in chunks_data:
            metadata = Metadata(
                id=chunk_id,
                user="concurrent_test",
                collection="test_collection",
                metadata=[]
            )
            chunk = Chunk(metadata=metadata, chunk=text.encode('utf-8'))
            chunks.append(chunk)
        
        # Act - Process chunks concurrently
        tasks = []
        for chunk in chunks:
            mock_msg = MagicMock()
            mock_msg.value.return_value = chunk
            task = processor.on_chunk(mock_msg, None, mock_integrated_flow)
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Assert
        output_producer = mock_integrated_flow("output")
        
        # Should have processed all chunks (some may produce objects, some may not)
        assert output_producer.send.call_count >= 2  # At least customer and product extractions
        
        # Verify we got both types of objects
        extracted_objects = []
        for call in output_producer.send.call_args_list:
            extracted_objects.append(call[0][0])
        
        customer_objects = [obj for obj in extracted_objects if obj.schema_name == "customer_records"]
        product_objects = [obj for obj in extracted_objects if obj.schema_name == "product_catalog"]
        
        assert len(customer_objects) >= 1
        assert len(product_objects) >= 1

    @pytest.mark.asyncio
    async def test_configuration_reload_integration(self, integration_config, mock_integrated_flow):
        """Test configuration reload during service operation"""
        # Arrange - Create mock processor with actual methods
        processor = MagicMock()
        processor.schemas = {}
        processor.config_key = "schema"
        processor.flow = mock_integrated_flow
        processor.on_schema_config = Processor.on_schema_config.__get__(processor, Processor)
        
        # Load initial configuration (only customer schema)
        initial_config = {
            "schema": {
                "customer_records": integration_config["schema"]["customer_records"]
            }
        }
        await processor.on_schema_config(initial_config, version=1)
        
        assert len(processor.schemas) == 1
        assert "customer_records" in processor.schemas
        assert "product_catalog" not in processor.schemas
        
        # Act - Reload with full configuration
        await processor.on_schema_config(integration_config, version=2)
        
        # Assert
        assert len(processor.schemas) == 2
        assert "customer_records" in processor.schemas
        assert "product_catalog" in processor.schemas

    @pytest.mark.asyncio
    async def test_error_resilience_integration(self, integration_config):
        """Test service resilience to various error conditions"""
        # Arrange - Create mock processor with actual methods
        processor = MagicMock()
        processor.schemas = {}
        processor.config_key = "schema"
        processor.on_schema_config = Processor.on_schema_config.__get__(processor, Processor)
        processor.on_chunk = Processor.on_chunk.__get__(processor, Processor)
        processor.extract_objects_for_schema = Processor.extract_objects_for_schema.__get__(processor, Processor)
        
        # Mock flow with failing prompt service
        failing_flow = MagicMock()
        failing_prompt = AsyncMock()
        failing_prompt.extract_rows.side_effect = Exception("Prompt service unavailable")
        
        def failing_context_router(service_name):
            if service_name == "prompt-request":
                return failing_prompt
            elif service_name == "output":
                return AsyncMock()
            else:
                return AsyncMock()
        
        failing_flow.side_effect = failing_context_router
        processor.flow = failing_flow
        
        # Load configuration
        await processor.on_schema_config(integration_config, version=1)
        
        # Create test chunk
        metadata = Metadata(id="error-test", user="test", collection="test", metadata=[])
        chunk = Chunk(metadata=metadata, chunk=b"Some text that will fail to process")
        
        mock_msg = MagicMock()
        mock_msg.value.return_value = chunk
        
        # Act & Assert - Should not raise exception
        try:
            await processor.on_chunk(mock_msg, None, failing_flow)
            # Should complete without throwing exception
        except Exception as e:
            pytest.fail(f"Service should handle errors gracefully, but raised: {e}")

    @pytest.mark.asyncio
    async def test_metadata_propagation_integration(self, integration_config, mock_integrated_flow):
        """Test proper metadata propagation through extraction pipeline"""
        # Arrange - Create mock processor with actual methods
        processor = MagicMock()
        processor.schemas = {}
        processor.config_key = "schema"
        processor.flow = mock_integrated_flow
        processor.on_schema_config = Processor.on_schema_config.__get__(processor, Processor)
        processor.on_chunk = Processor.on_chunk.__get__(processor, Processor)
        processor.extract_objects_for_schema = Processor.extract_objects_for_schema.__get__(processor, Processor)
        
        # Load configuration
        await processor.on_schema_config(integration_config, version=1)
        
        # Create chunk with rich metadata
        original_metadata = Metadata(
            id="metadata-test-chunk",
            user="test_user",
            collection="test_collection",
            metadata=[]  # Could include source document metadata
        )
        
        chunk = Chunk(
            metadata=original_metadata,
            chunk=b"Customer: John Smith, ID: CUST001, email: john.smith@email.com"
        )
        
        mock_msg = MagicMock()
        mock_msg.value.return_value = chunk
        
        # Act
        await processor.on_chunk(mock_msg, None, mock_integrated_flow)
        
        # Assert
        output_producer = mock_integrated_flow("output")
        
        # Find extracted object
        extracted_obj = None
        for call in output_producer.send.call_args_list:
            obj = call[0][0]
            if obj.schema_name == "customer_records":
                extracted_obj = obj
                break
        
        assert extracted_obj is not None
        
        # Verify metadata propagation
        assert extracted_obj.metadata.user == "test_user"
        assert extracted_obj.metadata.collection == "test_collection"
        assert "metadata-test-chunk" in extracted_obj.metadata.id  # Should include source reference