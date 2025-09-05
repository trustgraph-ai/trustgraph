"""
Integration tests for NLP Query Service

These tests verify the end-to-end functionality of the NLP query service,
testing service coordination, prompt service integration, and schema processing.
Following the TEST_STRATEGY.md approach for integration testing.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from trustgraph.schema import (
    QuestionToStructuredQueryRequest, QuestionToStructuredQueryResponse,
    PromptRequest, PromptResponse, Error, RowSchema, Field as SchemaField
)
from trustgraph.retrieval.nlp_query.service import Processor


@pytest.mark.integration
class TestNLPQueryServiceIntegration:
    """Integration tests for NLP query service coordination"""

    @pytest.fixture
    def sample_schemas(self):
        """Sample schemas for testing"""
        return {
            "customers": RowSchema(
                name="customers",
                description="Customer data with contact information",
                fields=[
                    SchemaField(name="id", type="string", primary=True),
                    SchemaField(name="name", type="string"),
                    SchemaField(name="email", type="string"),
                    SchemaField(name="state", type="string"),
                    SchemaField(name="phone", type="string")
                ]
            ),
            "orders": RowSchema(
                name="orders",
                description="Customer order transactions",
                fields=[
                    SchemaField(name="order_id", type="string", primary=True),
                    SchemaField(name="customer_id", type="string"),
                    SchemaField(name="total", type="float"),
                    SchemaField(name="status", type="string"),
                    SchemaField(name="order_date", type="datetime")
                ]
            ),
            "products": RowSchema(
                name="products",
                description="Product catalog information",
                fields=[
                    SchemaField(name="product_id", type="string", primary=True),
                    SchemaField(name="name", type="string"),
                    SchemaField(name="category", type="string"),
                    SchemaField(name="price", type="float"),
                    SchemaField(name="in_stock", type="boolean")
                ]
            )
        }

    @pytest.fixture
    def integration_processor(self, sample_schemas):
        """Create processor with realistic configuration"""
        proc = Processor(
            taskgroup=MagicMock(),
            pulsar_client=AsyncMock(),
            config_type="schema",
            schema_selection_template="schema-selection-v1",
            graphql_generation_template="graphql-generation-v1"
        )
        
        # Set up schemas
        proc.schemas = sample_schemas
        
        # Mock the client method
        proc.client = MagicMock()
        
        return proc

    @pytest.mark.asyncio
    async def test_end_to_end_nlp_query_processing(self, integration_processor):
        """Test complete NLP query processing pipeline"""
        # Arrange - Create realistic query request
        request = QuestionToStructuredQueryRequest(
            question="Show me customers from California who have placed orders over $500",
            max_results=50
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "integration-test-001"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock Phase 1 - Schema Selection Response
        phase1_response = PromptResponse(
            text=json.dumps(["customers", "orders"]),
            error=None
        )
        
        # Mock Phase 2 - GraphQL Generation Response  
        expected_graphql = """
        query GetCaliforniaCustomersWithLargeOrders($min_total: Float!) {
          customers(where: {state: {eq: "California"}}) {
            id
            name
            email
            state
            orders(where: {total: {gt: $min_total}}) {
              order_id
              total
              status
              order_date
            }
          }
        }
        """
        
        phase2_response = PromptResponse(
            text=json.dumps({
                "query": expected_graphql.strip(),
                "variables": {"min_total": "500.0"},
                "confidence": 0.92
            }),
            error=None
        )
        
        # Set up mock to return different responses for each call
        # Mock the flow context to return prompt service responses  
        prompt_service = AsyncMock()
        prompt_service.request = AsyncMock(
            side_effect=[phase1_response, phase2_response]
        )
        flow.side_effect = lambda service_name: prompt_service if service_name == "prompt-request" else flow_response if service_name == "response" else AsyncMock()
        
        # Act - Process the message
        await integration_processor.on_message(msg, consumer, flow)
        
        # Assert - Verify the complete pipeline
        assert prompt_service.request.call_count == 2
        flow_response.send.assert_called_once()
        
        # Verify response structure and content
        response_call = flow_response.send.call_args
        response = response_call[0][0]
        
        assert isinstance(response, QuestionToStructuredQueryResponse)
        assert response.error is None
        assert "customers" in response.graphql_query
        assert "orders" in response.graphql_query
        assert "California" in response.graphql_query
        assert response.detected_schemas == ["customers", "orders"]
        assert response.confidence == 0.92
        assert response.variables["min_total"] == "500.0"

    @pytest.mark.asyncio
    async def test_complex_multi_table_query_integration(self, integration_processor):
        """Test integration with complex multi-table queries"""
        # Arrange
        request = QuestionToStructuredQueryRequest(
            question="Find all electronic products under $100 that are in stock, along with any recent orders",
            max_results=25
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "multi-table-test"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock responses
        phase1_response = PromptResponse(
            text=json.dumps(["products", "orders"]),
            error=None
        )
        
        phase2_response = PromptResponse(
            text=json.dumps({
                "query": "query { products(where: {category: {eq: \"Electronics\"}, price: {lt: 100}, in_stock: {eq: true}}) { product_id name price orders { order_id total } } }",
                "variables": {},
                "confidence": 0.88
            }),
            error=None
        )
        
        # Mock the flow context to return prompt service responses  
        prompt_service = AsyncMock()
        prompt_service.request = AsyncMock(
            side_effect=[phase1_response, phase2_response]
        )
        flow.side_effect = lambda service_name: prompt_service if service_name == "prompt-request" else flow_response if service_name == "response" else AsyncMock()
        
        # Act
        await integration_processor.on_message(msg, consumer, flow)
        
        # Assert
        response_call = flow_response.send.call_args
        response = response_call[0][0]
        
        assert response.detected_schemas == ["products", "orders"]
        assert "Electronics" in response.graphql_query
        assert "price: {lt: 100}" in response.graphql_query
        assert "in_stock: {eq: true}" in response.graphql_query

    @pytest.mark.asyncio
    async def test_schema_configuration_integration(self, integration_processor):
        """Test integration with dynamic schema configuration"""
        # Arrange - New schema configuration
        new_schema_config = {
            "schema": {
                "inventory": json.dumps({
                    "name": "inventory",
                    "description": "Product inventory tracking",
                    "fields": [
                        {"name": "sku", "type": "string", "primary_key": True},
                        {"name": "quantity", "type": "integer"},
                        {"name": "warehouse_location", "type": "string"}
                    ]
                })
            }
        }
        
        # Act - Update configuration
        await integration_processor.on_schema_config(new_schema_config, "v2")
        
        # Arrange - Test query using new schema
        request = QuestionToStructuredQueryRequest(
            question="Show inventory levels for all products in warehouse A",
            max_results=100
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "schema-config-test"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock responses that use the new schema
        phase1_response = PromptResponse(
            text=json.dumps(["inventory"]),
            error=None
        )
        
        phase2_response = PromptResponse(
            text=json.dumps({
                "query": "query { inventory(where: {warehouse_location: {eq: \"A\"}}) { sku quantity warehouse_location } }",
                "variables": {},
                "confidence": 0.85
            }),
            error=None
        )
        
        # Mock the flow context to return prompt service responses  
        prompt_service = AsyncMock()
        prompt_service.request = AsyncMock(
            side_effect=[phase1_response, phase2_response]
        )
        flow.side_effect = lambda service_name: prompt_service if service_name == "prompt-request" else flow_response if service_name == "response" else AsyncMock()
        
        # Act
        await integration_processor.on_message(msg, consumer, flow)
        
        # Assert
        assert "inventory" in integration_processor.schemas
        response_call = flow_response.send.call_args
        response = response_call[0][0]
        assert response.detected_schemas == ["inventory"]
        assert "inventory" in response.graphql_query

    @pytest.mark.asyncio
    async def test_prompt_service_error_recovery_integration(self, integration_processor):
        """Test integration with prompt service error scenarios"""
        # Arrange
        request = QuestionToStructuredQueryRequest(
            question="Show me customer data",
            max_results=10
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "error-recovery-test"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock Phase 1 error
        phase1_error_response = PromptResponse(
            text="",
            error=Error(type="template-not-found", message="Schema selection template not available")
        )
        
        # Mock the flow context to return prompt service error response  
        prompt_service = AsyncMock()
        prompt_service.request = AsyncMock(
            return_value=phase1_error_response
        )
        flow.side_effect = lambda service_name: prompt_service if service_name == "prompt-request" else flow_response if service_name == "response" else AsyncMock()
        
        # Act
        await integration_processor.on_message(msg, consumer, flow)
        
        # Assert - Error is properly handled and propagated
        flow_response.send.assert_called_once()
        response_call = flow_response.send.call_args
        response = response_call[0][0]
        
        assert isinstance(response, QuestionToStructuredQueryResponse)
        assert response.error is not None
        assert response.error.type == "nlp-query-error"
        assert "Prompt service error" in response.error.message

    @pytest.mark.asyncio
    async def test_template_parameter_integration(self, sample_schemas):
        """Test integration with different template configurations"""
        # Test with custom templates
        custom_processor = Processor(
            taskgroup=MagicMock(),
            pulsar_client=AsyncMock(),
            config_type="schema",
            schema_selection_template="custom-schema-selector",
            graphql_generation_template="custom-graphql-generator"
        )
        
        custom_processor.schemas = sample_schemas
        custom_processor.client = MagicMock()
        
        request = QuestionToStructuredQueryRequest(
            question="Test query",
            max_results=5
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "template-test"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock responses
        phase1_response = PromptResponse(text=json.dumps(["customers"]), error=None)
        phase2_response = PromptResponse(
            text=json.dumps({
                "query": "query { customers { id name } }",
                "variables": {},
                "confidence": 0.9
            }),
            error=None
        )
        
        # Mock flow context to return prompt service responses
        mock_prompt_service = AsyncMock()
        mock_prompt_service.request = AsyncMock(
            side_effect=[phase1_response, phase2_response]
        )
        flow.side_effect = lambda service_name: mock_prompt_service if service_name == "prompt-request" else flow_response if service_name == "response" else AsyncMock()
        
        # Act
        await custom_processor.on_message(msg, consumer, flow)
        
        # Assert - Verify custom templates are used
        assert custom_processor.schema_selection_template == "custom-schema-selector"
        assert custom_processor.graphql_generation_template == "custom-graphql-generator"
        
        # Verify the calls were made
        assert mock_prompt_service.request.call_count == 2

    @pytest.mark.asyncio 
    async def test_large_schema_set_integration(self, integration_processor):
        """Test integration with large numbers of schemas"""
        # Arrange - Add many schemas
        large_schema_set = {}
        for i in range(20):
            schema_name = f"table_{i:02d}"
            large_schema_set[schema_name] = RowSchema(
                name=schema_name,
                description=f"Test table {i} with sample data",
                fields=[
                    SchemaField(name="id", type="string", primary=True)
                ] + [SchemaField(name=f"field_{j}", type="string") for j in range(5)]
            )
        
        integration_processor.schemas.update(large_schema_set)
        
        request = QuestionToStructuredQueryRequest(
            question="Show me data from table_05 and table_12",
            max_results=20
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "large-schema-test"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock responses
        phase1_response = PromptResponse(
            text=json.dumps(["table_05", "table_12"]),
            error=None
        )
        
        phase2_response = PromptResponse(
            text=json.dumps({
                "query": "query { table_05 { id field_0 } table_12 { id field_1 } }",
                "variables": {},
                "confidence": 0.87
            }),
            error=None
        )
        
        # Mock the flow context to return prompt service responses  
        prompt_service = AsyncMock()
        prompt_service.request = AsyncMock(
            side_effect=[phase1_response, phase2_response]
        )
        flow.side_effect = lambda service_name: prompt_service if service_name == "prompt-request" else flow_response if service_name == "response" else AsyncMock()
        
        # Act
        await integration_processor.on_message(msg, consumer, flow)
        
        # Assert - Should handle large schema sets efficiently
        response_call = flow_response.send.call_args
        response = response_call[0][0]
        
        assert response.detected_schemas == ["table_05", "table_12"]
        assert "table_05" in response.graphql_query
        assert "table_12" in response.graphql_query

    @pytest.mark.asyncio
    async def test_concurrent_request_handling_integration(self, integration_processor):
        """Test integration with concurrent request processing"""
        # Arrange - Multiple concurrent requests
        requests = []
        messages = []
        flows = []
        
        for i in range(5):
            request = QuestionToStructuredQueryRequest(
                question=f"Query {i}: Show me data",
                max_results=10
            )
            
            msg = MagicMock()
            msg.value.return_value = request
            msg.properties.return_value = {"id": f"concurrent-test-{i}"}
            
            flow = MagicMock()
            flow_response = AsyncMock()
            flow.return_value = flow_response
            
            requests.append(request)
            messages.append(msg)
            flows.append(flow)
        
        # Mock responses for all requests - create individual prompt services for each flow
        prompt_services = []
        for i in range(5):  # 5 concurrent requests
            phase1_response = PromptResponse(
                text=json.dumps(["customers"]),
                error=None
            )
            phase2_response = PromptResponse(
                text=json.dumps({
                    "query": f"query {{ customers {{ id name }} }}",
                    "variables": {},
                    "confidence": 0.9
                }),
                error=None
            )
            
            # Create a prompt service for this request
            prompt_service = AsyncMock()
            prompt_service.request = AsyncMock(
                side_effect=[phase1_response, phase2_response]
            )
            prompt_services.append(prompt_service)
            
            # Set up the flow for this request
            flow_response = flows[i].return_value
            flows[i].side_effect = lambda service_name, ps=prompt_service, fr=flow_response: (
                ps if service_name == "prompt-request" else 
                fr if service_name == "response" else 
                AsyncMock()
            )
        
        # Act - Process all messages concurrently
        import asyncio
        consumer = MagicMock()
        
        tasks = []
        for msg, flow in zip(messages, flows):
            task = integration_processor.on_message(msg, consumer, flow)
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Assert - All requests should be processed
        total_calls = sum(ps.request.call_count for ps in prompt_services)
        assert total_calls == 10  # 2 calls per request (phase1 + phase2)
        for flow in flows:
            flow.return_value.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_performance_timing_integration(self, integration_processor):
        """Test performance characteristics of the integration"""
        # Arrange
        request = QuestionToStructuredQueryRequest(
            question="Performance test query",
            max_results=100
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "performance-test"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock fast responses
        phase1_response = PromptResponse(text=json.dumps(["customers"]), error=None)
        phase2_response = PromptResponse(
            text=json.dumps({
                "query": "query { customers { id } }",
                "variables": {},
                "confidence": 0.9
            }),
            error=None
        )
        
        # Mock the flow context to return prompt service responses  
        prompt_service = AsyncMock()
        prompt_service.request = AsyncMock(
            side_effect=[phase1_response, phase2_response]
        )
        flow.side_effect = lambda service_name: prompt_service if service_name == "prompt-request" else flow_response if service_name == "response" else AsyncMock()
        
        # Act
        import time
        start_time = time.time()
        
        await integration_processor.on_message(msg, consumer, flow)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Assert
        assert execution_time < 1.0  # Should complete quickly with mocked services
        flow_response.send.assert_called_once()
        response_call = flow_response.send.call_args
        response = response_call[0][0]
        assert response.error is None