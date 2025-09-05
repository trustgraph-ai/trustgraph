"""
Integration tests for Structured Query Service

These tests verify the end-to-end functionality of the structured query service,
testing orchestration between nlp-query and objects-query services.
Following the TEST_STRATEGY.md approach for integration testing.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from trustgraph.schema import (
    StructuredQueryRequest, StructuredQueryResponse,
    QuestionToStructuredQueryRequest, QuestionToStructuredQueryResponse,
    ObjectsQueryRequest, ObjectsQueryResponse,
    Error, GraphQLError
)
from trustgraph.retrieval.structured_query.service import Processor


@pytest.mark.integration
class TestStructuredQueryServiceIntegration:
    """Integration tests for structured query service orchestration"""

    @pytest.fixture
    def integration_processor(self):
        """Create processor with realistic configuration"""
        proc = Processor(
            taskgroup=MagicMock(),
            pulsar_client=AsyncMock()
        )
        
        # Mock the client method
        proc.client = MagicMock()
        
        return proc

    @pytest.mark.asyncio
    async def test_end_to_end_structured_query_processing(self, integration_processor):
        """Test complete structured query processing pipeline"""
        # Arrange - Create realistic query request
        request = StructuredQueryRequest(
            question="Show me all customers from California who have made purchases over $500"
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "integration-test-001"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock NLP Query Service Response
        nlp_response = QuestionToStructuredQueryResponse(
            error=None,
            graphql_query='''
            query GetCaliforniaCustomersWithLargePurchases($minAmount: String!, $state: String!) {
                customers(where: {state: {eq: $state}}) {
                    id
                    name
                    email
                    orders(where: {total: {gt: $minAmount}}) {
                        id
                        total
                        date
                    }
                }
            }
            ''',
            variables={
                "minAmount": "500.0",
                "state": "California"
            },
            detected_schemas=["customers", "orders"],
            confidence=0.91
        )
        
        # Mock Objects Query Service Response
        objects_response = ObjectsQueryResponse(
            error=None,
            data='{"customers": [{"id": "123", "name": "Alice Johnson", "email": "alice@example.com", "orders": [{"id": "456", "total": 750.0, "date": "2024-01-15"}]}]}',
            errors=None,
            extensions={"execution_time": "150ms", "query_complexity": "8"}
        )
        
        # Set up mock clients to return different responses
        mock_nlp_client = AsyncMock()
        mock_nlp_client.request.return_value = nlp_response
        
        mock_objects_client = AsyncMock()
        mock_objects_client.request.return_value = objects_response
        
        # Mock flow context to route to appropriate services
        def flow_router(service_name):
            if service_name == "nlp-query-request":
                return mock_nlp_client
            elif service_name == "objects-query-request": 
                return mock_objects_client
            elif service_name == "response":
                return flow_response
            else:
                return AsyncMock()
        flow.side_effect = flow_router
        
        # Act - Process the message
        await integration_processor.on_message(msg, consumer, flow)
        
        # Assert - Verify the complete orchestration
        # Verify NLP service call
        mock_nlp_client.request.assert_called_once()
        nlp_call_args = mock_nlp_client.request.call_args[0][0]
        assert isinstance(nlp_call_args, QuestionToStructuredQueryRequest)
        assert nlp_call_args.question == "Show me all customers from California who have made purchases over $500"
        assert nlp_call_args.max_results == 100  # Default max_results
        
        # Verify Objects service call
        mock_objects_client.request.assert_called_once()
        objects_call_args = mock_objects_client.request.call_args[0][0]
        assert isinstance(objects_call_args, ObjectsQueryRequest)
        assert "customers" in objects_call_args.query
        assert "orders" in objects_call_args.query
        assert objects_call_args.variables["minAmount"] == "500.0"  # Converted to string
        assert objects_call_args.variables["state"] == "California"
        assert objects_call_args.user == "trustgraph"
        assert objects_call_args.collection == "default"
        
        # Verify response
        flow_response.send.assert_called_once()
        response_call = flow_response.send.call_args
        response = response_call[0][0]
        
        assert isinstance(response, StructuredQueryResponse)
        assert response.error is None
        assert "Alice Johnson" in response.data
        assert "750.0" in response.data
        assert len(response.errors) == 0

    @pytest.mark.asyncio
    async def test_nlp_service_integration_failure(self, integration_processor):
        """Test integration when NLP service fails"""
        # Arrange
        request = StructuredQueryRequest(
            question="This is an unparseable query ][{}"
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "nlp-failure-test"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock NLP service failure
        nlp_error_response = QuestionToStructuredQueryResponse(
            error=Error(type="nlp-parsing-error", message="Unable to parse natural language query"),
            graphql_query="",
            variables={},
            detected_schemas=[],
            confidence=0.0
        )
        
        mock_nlp_client = AsyncMock()
        mock_nlp_client.request.return_value = nlp_error_response
        
        # Mock flow context to route to nlp service
        def flow_router(service_name):
            if service_name == "nlp-query-request":
                return mock_nlp_client
            elif service_name == "response":
                return flow_response
            else:
                return AsyncMock()
        flow.side_effect = flow_router
        
        # Act
        await integration_processor.on_message(msg, consumer, flow)
        
        # Assert - Error should be propagated properly
        flow_response.send.assert_called_once()
        response_call = flow_response.send.call_args
        response = response_call[0][0]
        
        assert isinstance(response, StructuredQueryResponse)
        assert response.error is not None
        assert response.error.type == "structured-query-error"
        assert "NLP query service error" in response.error.message
        assert "Unable to parse natural language query" in response.error.message

    @pytest.mark.asyncio
    async def test_objects_service_integration_failure(self, integration_processor):
        """Test integration when Objects service fails"""
        # Arrange
        request = StructuredQueryRequest(
            question="Show me data from a table that doesn't exist"
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "objects-failure-test"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock successful NLP response
        nlp_response = QuestionToStructuredQueryResponse(
            error=None,
            graphql_query='query { nonexistent_table { id name } }',
            variables={},
            detected_schemas=["nonexistent_table"],
            confidence=0.7
        )
        
        # Mock Objects service failure
        objects_error_response = ObjectsQueryResponse(
            error=Error(type="graphql-schema-error", message="Table 'nonexistent_table' does not exist in schema"),
            data=None,
            errors=None,
            extensions={}
        )
        
        mock_nlp_client = AsyncMock()
        mock_nlp_client.request.return_value = nlp_response
        
        mock_objects_client = AsyncMock()
        mock_objects_client.request.return_value = objects_error_response
        
        # Mock flow context to route to appropriate services
        def flow_router(service_name):
            if service_name == "nlp-query-request":
                return mock_nlp_client
            elif service_name == "objects-query-request": 
                return mock_objects_client
            elif service_name == "response":
                return flow_response
            else:
                return AsyncMock()
        flow.side_effect = flow_router
        
        # Act
        await integration_processor.on_message(msg, consumer, flow)
        
        # Assert - Error should be propagated
        flow_response.send.assert_called_once()
        response_call = flow_response.send.call_args
        response = response_call[0][0]
        
        assert response.error is not None
        assert response.error.type == "structured-query-error"
        assert "Objects query service error" in response.error.message
        assert "nonexistent_table" in response.error.message

    @pytest.mark.asyncio
    async def test_graphql_validation_errors_integration(self, integration_processor):
        """Test integration with GraphQL validation errors"""
        # Arrange
        request = StructuredQueryRequest(
            question="Show me customer invalid_field values"
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "validation-error-test"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock NLP response with invalid field
        nlp_response = QuestionToStructuredQueryResponse(
            error=None,
            graphql_query='query { customers { id invalid_field } }',
            variables={},
            detected_schemas=["customers"],
            confidence=0.8
        )
        
        # Mock Objects response with GraphQL validation errors
        validation_errors = [
            GraphQLError(
                message="Cannot query field 'invalid_field' on type 'Customer'",
                path=["customers", "0", "invalid_field"],
                extensions={"code": "VALIDATION_ERROR"}
            ),
            GraphQLError(
                message="Field 'invalid_field' is not defined in the schema",
                path=["customers", "invalid_field"],
                extensions={"code": "FIELD_NOT_FOUND"}
            )
        ]
        
        objects_response = ObjectsQueryResponse(
            error=None,
            data=None,  # No data when validation fails
            errors=validation_errors,
            extensions={"validation_errors": "2"}
        )
        
        mock_nlp_client = AsyncMock()
        mock_nlp_client.request.return_value = nlp_response
        
        mock_objects_client = AsyncMock()
        mock_objects_client.request.return_value = objects_response
        
        # Mock flow context to route to appropriate services
        def flow_router(service_name):
            if service_name == "nlp-query-request":
                return mock_nlp_client
            elif service_name == "objects-query-request": 
                return mock_objects_client
            elif service_name == "response":
                return flow_response
            else:
                return AsyncMock()
        flow.side_effect = flow_router
        
        # Act
        await integration_processor.on_message(msg, consumer, flow)
        
        # Assert - GraphQL errors should be included in response
        flow_response.send.assert_called_once()
        response_call = flow_response.send.call_args
        response = response_call[0][0]
        
        assert response.error is None  # No system error
        assert len(response.errors) == 2  # Two GraphQL errors
        assert "Cannot query field 'invalid_field'" in response.errors[0]
        assert "Field 'invalid_field' is not defined" in response.errors[1]
        assert "customers" in response.errors[0]

    @pytest.mark.asyncio
    async def test_complex_multi_service_integration(self, integration_processor):
        """Test complex integration scenario with multiple entities and relationships"""
        # Arrange
        request = StructuredQueryRequest(
            question="Find all products under $100 that are in stock, along with their recent orders from customers in New York"
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "complex-integration-test"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock complex NLP response
        nlp_response = QuestionToStructuredQueryResponse(
            error=None,
            graphql_query='''
            query GetProductsWithCustomerOrders($maxPrice: String!, $inStock: String!, $state: String!) {
                products(where: {price: {lt: $maxPrice}, in_stock: {eq: $inStock}}) {
                    id
                    name
                    price
                    orders {
                        id
                        total
                        customer {
                            id
                            name
                            state
                        }
                    }
                }
            }
            ''',
            variables={
                "maxPrice": "100.0",
                "inStock": "true",
                "state": "New York"
            },
            detected_schemas=["products", "orders", "customers"],
            confidence=0.85
        )
        
        # Mock complex Objects response
        complex_data = {
            "products": [
                {
                    "id": "prod_123",
                    "name": "Widget A",
                    "price": 89.99,
                    "orders": [
                        {
                            "id": "order_456",
                            "total": 179.98,
                            "customer": {
                                "id": "cust_789",
                                "name": "Bob Smith",
                                "state": "New York"
                            }
                        }
                    ]
                },
                {
                    "id": "prod_124",
                    "name": "Widget B", 
                    "price": 65.50,
                    "orders": [
                        {
                            "id": "order_457",
                            "total": 131.00,
                            "customer": {
                                "id": "cust_790",
                                "name": "Carol Jones",
                                "state": "New York"
                            }
                        }
                    ]
                }
            ]
        }
        
        objects_response = ObjectsQueryResponse(
            error=None,
            data=json.dumps(complex_data),
            errors=None,
            extensions={
                "execution_time": "250ms",
                "query_complexity": "15",
                "data_sources": "products,orders,customers"  # Convert array to comma-separated string
            }
        )
        
        mock_nlp_client = AsyncMock()
        mock_nlp_client.request.return_value = nlp_response
        
        mock_objects_client = AsyncMock()
        mock_objects_client.request.return_value = objects_response
        
        # Mock flow context to route to appropriate services
        def flow_router(service_name):
            if service_name == "nlp-query-request":
                return mock_nlp_client
            elif service_name == "objects-query-request": 
                return mock_objects_client
            elif service_name == "response":
                return flow_response
            else:
                return AsyncMock()
        flow.side_effect = flow_router
        
        # Act
        await integration_processor.on_message(msg, consumer, flow)
        
        # Assert - Verify complex data integration
        # Check NLP service call
        nlp_call_args = mock_nlp_client.request.call_args[0][0]
        assert len(nlp_call_args.question) > 50  # Complex question
        
        # Check Objects service call with variable conversion
        objects_call_args = mock_objects_client.request.call_args[0][0]
        assert objects_call_args.variables["maxPrice"] == "100.0"
        assert objects_call_args.variables["inStock"] == "true"
        assert objects_call_args.variables["state"] == "New York"
        
        # Check response contains complex data
        response_call = flow_response.send.call_args
        response = response_call[0][0]
        
        assert response.error is None
        assert "Widget A" in response.data
        assert "Widget B" in response.data
        assert "Bob Smith" in response.data
        assert "Carol Jones" in response.data
        assert "New York" in response.data

    @pytest.mark.asyncio
    async def test_empty_result_integration(self, integration_processor):
        """Test integration when query returns empty results"""
        # Arrange
        request = StructuredQueryRequest(
            question="Show me customers from Mars"
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "empty-result-test"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock NLP response
        nlp_response = QuestionToStructuredQueryResponse(
            error=None,
            graphql_query='query { customers(where: {planet: {eq: "Mars"}}) { id name planet } }',
            variables={},
            detected_schemas=["customers"],
            confidence=0.9
        )
        
        # Mock empty Objects response
        objects_response = ObjectsQueryResponse(
            error=None,
            data='{"customers": []}',  # Empty result set
            errors=None,
            extensions={"result_count": "0"}
        )
        
        mock_nlp_client = AsyncMock()
        mock_nlp_client.request.return_value = nlp_response
        
        mock_objects_client = AsyncMock()
        mock_objects_client.request.return_value = objects_response
        
        # Mock flow context to route to appropriate services
        def flow_router(service_name):
            if service_name == "nlp-query-request":
                return mock_nlp_client
            elif service_name == "objects-query-request": 
                return mock_objects_client
            elif service_name == "response":
                return flow_response
            else:
                return AsyncMock()
        flow.side_effect = flow_router
        
        # Act
        await integration_processor.on_message(msg, consumer, flow)
        
        # Assert - Empty results should be handled gracefully
        response_call = flow_response.send.call_args
        response = response_call[0][0]
        
        assert response.error is None
        assert response.data == '{"customers": []}'
        assert len(response.errors) == 0

    @pytest.mark.asyncio
    async def test_concurrent_requests_integration(self, integration_processor):
        """Test integration with concurrent request processing"""
        # Arrange - Multiple concurrent requests
        requests = []
        messages = []
        flows = []
        
        for i in range(3):
            request = StructuredQueryRequest(
                question=f"Query {i}: Show me data"
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
        
        # Mock responses for all requests (6 total: 3 NLP + 3 Objects)
        mock_responses = []
        for i in range(6):
            if i % 2 == 0:  # NLP responses
                mock_responses.append(QuestionToStructuredQueryResponse(
                    error=None,
                    graphql_query=f'query {{ test_{i//2} {{ id }} }}',
                    variables={},
                    detected_schemas=[f"test_{i//2}"],
                    confidence=0.9
                ))
            else:  # Objects responses  
                mock_responses.append(ObjectsQueryResponse(
                    error=None,
                    data=f'{{"test_{i//2}": [{{"id": "{i//2}"}}]}}',
                    errors=None,
                    extensions={}
                ))
        
        call_count = 0
        def mock_client_side_effect(name):
            nonlocal call_count
            client = AsyncMock()
            client.request.return_value = mock_responses[call_count]
            call_count += 1
            return client
        
        integration_processor.client.side_effect = mock_client_side_effect
        
        # Act - Process all messages concurrently
        import asyncio
        consumer = MagicMock()
        
        tasks = []
        for msg, flow in zip(messages, flows):
            task = integration_processor.on_message(msg, consumer, flow)
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Assert - All requests should be processed
        assert call_count == 6  # 2 calls per request (NLP + Objects)
        for flow in flows:
            flow.return_value.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_timeout_integration(self, integration_processor):
        """Test integration with service timeout scenarios"""
        # Arrange
        request = StructuredQueryRequest(
            question="This query will timeout"
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "timeout-test"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock NLP service timeout
        mock_nlp_client = AsyncMock()
        mock_nlp_client.request.side_effect = Exception("Service timeout: Request took longer than 30s")
        
        # Mock flow context to route to nlp service
        def flow_router(service_name):
            if service_name == "nlp-query-request":
                return mock_nlp_client
            elif service_name == "response":
                return flow_response
            else:
                return AsyncMock()
        flow.side_effect = flow_router
        
        # Act
        await integration_processor.on_message(msg, consumer, flow)
        
        # Assert - Timeout should be handled gracefully
        flow_response.send.assert_called_once()
        response_call = flow_response.send.call_args
        response = response_call[0][0]
        
        assert response.error is not None
        assert response.error.type == "structured-query-error"
        assert "timeout" in response.error.message.lower()

    @pytest.mark.asyncio
    async def test_variable_type_conversion_integration(self, integration_processor):
        """Test integration with complex variable type conversions"""
        # Arrange
        request = StructuredQueryRequest(
            question="Show me orders with totals between 50.5 and 200.75 from the last 30 days"
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "variable-conversion-test"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock NLP response with various data types that need string conversion
        nlp_response = QuestionToStructuredQueryResponse(
            error=None,
            graphql_query='query($minTotal: Float!, $maxTotal: Float!, $daysPast: Int!) { orders(filter: {total: {between: [$minTotal, $maxTotal]}, date: {gte: $daysPast}}) { id total date } }',
            variables={
                "minTotal": "50.5",   # Already string
                "maxTotal": "200.75", # Already string
                "daysPast": "30"      # Already string
            },
            detected_schemas=["orders"],
            confidence=0.88
        )
        
        # Mock Objects response
        objects_response = ObjectsQueryResponse(
            error=None,
            data='{"orders": [{"id": "123", "total": 125.50, "date": "2024-01-15"}]}',
            errors=None,
            extensions={}
        )
        
        mock_nlp_client = AsyncMock()
        mock_nlp_client.request.return_value = nlp_response
        
        mock_objects_client = AsyncMock()
        mock_objects_client.request.return_value = objects_response
        
        # Mock flow context to route to appropriate services
        def flow_router(service_name):
            if service_name == "nlp-query-request":
                return mock_nlp_client
            elif service_name == "objects-query-request": 
                return mock_objects_client
            elif service_name == "response":
                return flow_response
            else:
                return AsyncMock()
        flow.side_effect = flow_router
        
        # Act
        await integration_processor.on_message(msg, consumer, flow)
        
        # Assert - Variables should be properly converted to strings
        objects_call_args = mock_objects_client.request.call_args[0][0]
        
        # All variables should be strings for Pulsar schema compatibility
        assert isinstance(objects_call_args.variables["minTotal"], str)
        assert isinstance(objects_call_args.variables["maxTotal"], str)
        assert isinstance(objects_call_args.variables["daysPast"], str)
        
        # Values should be preserved
        assert objects_call_args.variables["minTotal"] == "50.5"
        assert objects_call_args.variables["maxTotal"] == "200.75"
        assert objects_call_args.variables["daysPast"] == "30"
        
        # Response should contain expected data
        response_call = flow_response.send.call_args
        response = response_call[0][0]
        assert response.error is None
        assert "125.50" in response.data