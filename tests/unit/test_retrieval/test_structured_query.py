"""
Unit tests for Structured Query Service
Following TEST_STRATEGY.md approach for service testing
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from trustgraph.schema import (
    StructuredQueryRequest, StructuredQueryResponse,
    QuestionToStructuredQueryRequest, QuestionToStructuredQueryResponse,
    ObjectsQueryRequest, ObjectsQueryResponse,
    Error, GraphQLError
)
from trustgraph.retrieval.structured_query.service import Processor


@pytest.fixture
def mock_pulsar_client():
    """Mock Pulsar client"""
    return AsyncMock()


@pytest.fixture
def processor(mock_pulsar_client):
    """Create processor with mocked dependencies"""
    proc = Processor(
        taskgroup=MagicMock(),
        pulsar_client=mock_pulsar_client
    )
    
    # Mock the client method
    proc.client = MagicMock()
    
    return proc


@pytest.mark.asyncio
class TestStructuredQueryProcessor:
    """Test Structured Query service processor"""

    async def test_successful_end_to_end_query(self, processor):
        """Test successful end-to-end query processing"""
        # Arrange
        request = StructuredQueryRequest(
            question="Show me all customers from New York",
            user="trustgraph", 
            collection="default"
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "test-123"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock NLP query service response
        nlp_response = QuestionToStructuredQueryResponse(
            error=None,
            graphql_query='query { customers(where: {state: {eq: "NY"}}) { id name email } }',
            variables={"state": "NY"},
            detected_schemas=["customers"],
            confidence=0.95
        )
        
        # Mock objects query service response
        objects_response = ObjectsQueryResponse(
            error=None,
            data='{"customers": [{"id": "1", "name": "John", "email": "john@example.com"}]}',
            errors=None,
            extensions={}
        )
        
        # Set up mock clients
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
        await processor.on_message(msg, consumer, flow)
        
        # Assert
        # Verify NLP query service was called correctly
        mock_nlp_client.request.assert_called_once()
        nlp_call_args = mock_nlp_client.request.call_args[0][0]
        assert isinstance(nlp_call_args, QuestionToStructuredQueryRequest)
        assert nlp_call_args.question == "Show me all customers from New York"
        assert nlp_call_args.max_results == 100
        
        # Verify objects query service was called correctly
        mock_objects_client.request.assert_called_once()
        objects_call_args = mock_objects_client.request.call_args[0][0]
        assert isinstance(objects_call_args, ObjectsQueryRequest)
        assert objects_call_args.query == 'query { customers(where: {state: {eq: "NY"}}) { id name email } }'
        assert objects_call_args.variables == {"state": "NY"}
        assert objects_call_args.user == "trustgraph"
        assert objects_call_args.collection == "default"
        
        # Verify response
        flow_response.send.assert_called_once()
        response_call = flow_response.send.call_args
        response = response_call[0][0]
        
        assert isinstance(response, StructuredQueryResponse)
        assert response.error is None
        assert response.data == '{"customers": [{"id": "1", "name": "John", "email": "john@example.com"}]}'
        assert len(response.errors) == 0

    async def test_nlp_query_service_error(self, processor):
        """Test handling of NLP query service errors"""
        # Arrange
        request = StructuredQueryRequest(
            question="Invalid query"
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "test-error"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock NLP query service error response
        nlp_response = QuestionToStructuredQueryResponse(
            error=Error(type="nlp-query-error", message="Failed to parse question"),
            graphql_query="",
            variables={},
            detected_schemas=[],
            confidence=0.0
        )
        
        mock_nlp_client = AsyncMock()
        mock_nlp_client.request.return_value = nlp_response
        
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
        await processor.on_message(msg, consumer, flow)
        
        # Assert
        flow_response.send.assert_called_once()
        response_call = flow_response.send.call_args
        response = response_call[0][0]
        
        assert isinstance(response, StructuredQueryResponse)
        assert response.error is not None
        assert response.error.type == "structured-query-error"
        assert "NLP query service error" in response.error.message

    async def test_empty_graphql_query_error(self, processor):
        """Test handling of empty GraphQL query from NLP service"""
        # Arrange
        request = StructuredQueryRequest(
            question="Ambiguous question"
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "test-empty"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock NLP query service response with empty query
        nlp_response = QuestionToStructuredQueryResponse(
            error=None,
            graphql_query="",  # Empty query
            variables={},
            detected_schemas=[],
            confidence=0.1
        )
        
        mock_nlp_client = AsyncMock()
        mock_nlp_client.request.return_value = nlp_response
        
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
        await processor.on_message(msg, consumer, flow)
        
        # Assert
        flow_response.send.assert_called_once()
        response_call = flow_response.send.call_args
        response = response_call[0][0]
        
        assert response.error is not None
        assert "empty GraphQL query" in response.error.message

    async def test_objects_query_service_error(self, processor):
        """Test handling of objects query service errors"""
        # Arrange
        request = StructuredQueryRequest(
            question="Show me customers"
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "test-objects-error"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock successful NLP response
        nlp_response = QuestionToStructuredQueryResponse(
            error=None,
            graphql_query='query { customers { id name } }',
            variables={},
            detected_schemas=["customers"],
            confidence=0.9
        )
        
        # Mock objects query service error
        objects_response = ObjectsQueryResponse(
            error=Error(type="graphql-execution-error", message="Table 'customers' not found"),
            data=None,
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
        await processor.on_message(msg, consumer, flow)
        
        # Assert
        flow_response.send.assert_called_once()
        response_call = flow_response.send.call_args
        response = response_call[0][0]
        
        assert response.error is not None
        assert "Objects query service error" in response.error.message
        assert "Table 'customers' not found" in response.error.message

    async def test_graphql_errors_handling(self, processor):
        """Test handling of GraphQL validation/execution errors"""
        # Arrange
        request = StructuredQueryRequest(
            question="Show invalid field"
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "test-graphql-errors"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock successful NLP response
        nlp_response = QuestionToStructuredQueryResponse(
            error=None,
            graphql_query='query { customers { invalid_field } }',
            variables={},
            detected_schemas=["customers"],
            confidence=0.8
        )
        
        # Mock objects response with GraphQL errors
        graphql_errors = [
            GraphQLError(
                message="Cannot query field 'invalid_field' on type 'Customer'",
                path=["customers", "0", "invalid_field"],  # All path elements must be strings
                extensions={}
            )
        ]
        
        objects_response = ObjectsQueryResponse(
            error=None,
            data=None,
            errors=graphql_errors,
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
        await processor.on_message(msg, consumer, flow)
        
        # Assert
        flow_response.send.assert_called_once()
        response_call = flow_response.send.call_args
        response = response_call[0][0]
        
        assert response.error is None
        assert len(response.errors) == 1
        assert "Cannot query field 'invalid_field'" in response.errors[0]
        assert "customers" in response.errors[0]

    async def test_complex_query_with_variables(self, processor):
        """Test processing complex queries with variables"""
        # Arrange
        request = StructuredQueryRequest(
            question="Show customers with orders over $100 from last month"
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "test-complex"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock NLP response with complex query and variables
        nlp_response = QuestionToStructuredQueryResponse(
            error=None,
            graphql_query='''
            query GetCustomersWithLargeOrders($minTotal: Float!, $startDate: String!) {
                customers {
                    id
                    name
                    orders(where: {total: {gt: $minTotal}, date: {gte: $startDate}}) {
                        id
                        total
                        date
                    }
                }
            }
            ''',
            variables={
                "minTotal": "100.0",  # Convert to string for Pulsar schema
                "startDate": "2024-01-01"
            },
            detected_schemas=["customers", "orders"],
            confidence=0.88
        )
        
        # Mock objects response
        objects_response = ObjectsQueryResponse(
            error=None,
            data='{"customers": [{"id": "1", "name": "Alice", "orders": [{"id": "100", "total": 150.0}]}]}',
            errors=None
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
        await processor.on_message(msg, consumer, flow)
        
        # Assert
        # Verify variables were passed correctly (converted to strings)
        objects_call_args = mock_objects_client.request.call_args[0][0]
        assert objects_call_args.variables["minTotal"] == "100.0"  # Should be converted to string
        assert objects_call_args.variables["startDate"] == "2024-01-01"
        
        # Verify response
        response_call = flow_response.send.call_args
        response = response_call[0][0]
        assert response.error is None
        assert "Alice" in response.data

    async def test_null_data_handling(self, processor):
        """Test handling of null/empty data responses"""
        # Arrange
        request = StructuredQueryRequest(
            question="Show nonexistent data"
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "test-null"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock responses
        nlp_response = QuestionToStructuredQueryResponse(
            error=None,
            graphql_query='query { customers { id } }',
            variables={},
            detected_schemas=["customers"],
            confidence=0.9
        )
        
        objects_response = ObjectsQueryResponse(
            error=None,
            data=None,  # Null data
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
        await processor.on_message(msg, consumer, flow)
        
        # Assert
        response_call = flow_response.send.call_args
        response = response_call[0][0]
        
        assert response.error is None
        assert response.data == "null"  # Should convert None to "null" string

    async def test_exception_handling(self, processor):
        """Test general exception handling"""
        # Arrange
        request = StructuredQueryRequest(
            question="Test exception"
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "test-exception"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock flow context to raise exception
        mock_client = AsyncMock()
        mock_client.request.side_effect = Exception("Network timeout")
        
        def flow_router(service_name):
            if service_name == "nlp-query-request":
                return mock_client
            elif service_name == "response":
                return flow_response
            else:
                return AsyncMock()
        flow.side_effect = flow_router
        
        # Act
        await processor.on_message(msg, consumer, flow)
        
        # Assert
        flow_response.send.assert_called_once()
        response_call = flow_response.send.call_args
        response = response_call[0][0]
        
        assert response.error is not None
        assert response.error.type == "structured-query-error"
        assert "Network timeout" in response.error.message
        assert response.data == "null"
        assert len(response.errors) == 0

    def test_processor_initialization(self, mock_pulsar_client):
        """Test processor initialization with correct specifications"""
        # Act
        processor = Processor(
            taskgroup=MagicMock(),
            pulsar_client=mock_pulsar_client
        )
        
        # Assert - Test default ID
        assert processor.id == "structured-query"
        
        # Verify specifications were registered (we can't directly access them,
        # but we know they were registered if initialization succeeded)
        assert processor is not None

    def test_add_args(self):
        """Test command-line argument parsing"""
        import argparse
        
        parser = argparse.ArgumentParser()
        Processor.add_args(parser)
        
        # Test that it doesn't crash (no additional args)
        args = parser.parse_args([])
        # No specific assertions since no custom args are added
        assert args is not None


@pytest.mark.unit
class TestStructuredQueryHelperFunctions:
    """Test helper functions and data transformations"""
    
    def test_service_logging_integration(self):
        """Test that logging is properly configured"""
        # Import the logger
        from trustgraph.retrieval.structured_query.service import logger
        
        assert logger.name == "trustgraph.retrieval.structured_query.service"
        
    def test_default_values(self):
        """Test default configuration values"""
        from trustgraph.retrieval.structured_query.service import default_ident
        
        assert default_ident == "structured-query"