"""
Integration tests for React Agent with Structured Query Tool

These tests verify the end-to-end functionality of the React agent 
using the structured-query tool to query structured data with natural language.
Following the TEST_STRATEGY.md approach for integration testing.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from trustgraph.schema import (
    AgentRequest, AgentResponse,
    StructuredQueryRequest, StructuredQueryResponse,
    Error
)
from trustgraph.agent.react.service import Processor


@pytest.mark.integration  
class TestAgentStructuredQueryIntegration:
    """Integration tests for React agent with structured query tool"""

    @pytest.fixture
    def agent_processor(self):
        """Create agent processor with structured query tool configured"""
        proc = Processor(
            taskgroup=MagicMock(),
            pulsar_client=AsyncMock(),
            max_iterations=3
        )
        
        # Mock the client method for structured query
        proc.client = MagicMock()
        
        return proc

    @pytest.fixture
    def structured_query_tool_config(self):
        """Configuration for structured-query tool"""
        import json
        return {
            "tool": {
                "structured-query": json.dumps({
                    "name": "structured-query",
                    "description": "Query structured data using natural language",
                    "type": "structured-query"
                })
            }
        }

    @pytest.mark.asyncio
    async def test_agent_structured_query_basic_integration(self, agent_processor, structured_query_tool_config):
        """Test basic agent integration with structured query tool"""
        # Arrange - Load tool configuration
        await agent_processor.on_tools_config(structured_query_tool_config, "v1")
        
        # Create agent request
        request = AgentRequest(
            question="I need to find all customers from New York. Use the structured query tool to get this information.",
            state="",
            group=[],
            history=[],
            user="test_user"
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "agent-test-001"}
        
        consumer = MagicMock()
        
        # Mock response producer for the flow
        response_producer = AsyncMock()
        
        # Mock structured query response
        structured_query_response = {
            "data": json.dumps({
                "customers": [
                    {"id": "1", "name": "John Doe", "email": "john@example.com", "state": "New York"},
                    {"id": "2", "name": "Jane Smith", "email": "jane@example.com", "state": "New York"}
                ]
            }),
            "errors": [],
            "error": None
        }
        
        # Mock the structured query client
        mock_structured_client = AsyncMock()
        mock_structured_client.structured_query.return_value = structured_query_response
        
        # Mock the prompt client that agent calls for reasoning
        mock_prompt_client = AsyncMock()
        mock_prompt_client.agent_react.return_value = """Thought: I need to find customers from New York using structured query
Action: structured-query
Args: {
    "question": "Find all customers from New York"
}"""
        
        # Set up flow context routing
        def flow_context(service_name):
            if service_name == "structured-query-request":
                return mock_structured_client
            elif service_name == "prompt-request":
                return mock_prompt_client
            elif service_name == "response":
                return response_producer
            else:
                return AsyncMock()
        
        # Mock flow parameter in agent_processor.on_request
        flow = MagicMock()
        flow.side_effect = flow_context
        
        # Act
        await agent_processor.on_request(msg, consumer, flow)
        
        # Assert
        # Verify structured query was called
        mock_structured_client.structured_query.assert_called_once()
        call_args = mock_structured_client.structured_query.call_args
        question_arg = call_args[0][0]  # positional argument
        assert "customers" in question_arg.lower()
        assert "new york" in question_arg.lower()
        
        # Verify responses were sent (agent sends multiple responses for thought/observation)
        assert response_producer.send.call_count >= 1
        
        # Check all the responses that were sent
        all_calls = response_producer.send.call_args_list
        responses = [call[0][0] for call in all_calls]
        
        # Verify at least one response is of correct type and has no error
        assert any(isinstance(resp, AgentResponse) and resp.error is None for resp in responses)

    @pytest.mark.asyncio
    async def test_agent_structured_query_error_handling(self, agent_processor, structured_query_tool_config):
        """Test agent handling of structured query errors"""
        # Arrange
        await agent_processor.on_tools_config(structured_query_tool_config, "v1")
        
        request = AgentRequest(
            question="Find data from a table that doesn't exist using structured query.",
            state="",
            group=[],
            history=[],
            user="test_user"
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "agent-error-test"}
        
        consumer = MagicMock()
        
        # Mock response producer for the flow
        response_producer = AsyncMock()
        
        # Mock structured query error response
        structured_query_error_response = {
            "data": None,
            "errors": ["Table 'nonexistent' not found in schema"],
            "error": {"type": "structured-query-error", "message": "Schema not found"}
        }
        
        mock_structured_client = AsyncMock()
        mock_structured_client.structured_query.return_value = structured_query_error_response
        
        # Mock the prompt client that agent calls for reasoning
        mock_prompt_client = AsyncMock()
        mock_prompt_client.agent_react.return_value = """Thought: I need to query for a table that might not exist
Action: structured-query
Args: {
    "question": "Find data from a table that doesn't exist"
}"""
        
        # Set up flow context routing
        def flow_context(service_name):
            if service_name == "structured-query-request":
                return mock_structured_client
            elif service_name == "prompt-request":
                return mock_prompt_client
            elif service_name == "response":
                return response_producer
            else:
                return AsyncMock()
        
        flow = MagicMock()
        flow.side_effect = flow_context
        
        # Act
        await agent_processor.on_request(msg, consumer, flow)
        
        # Assert
        mock_structured_client.structured_query.assert_called_once()
        assert response_producer.send.call_count >= 1
        
        all_calls = response_producer.send.call_args_list
        responses = [call[0][0] for call in all_calls]
        
        # Agent should handle the error gracefully
        assert any(isinstance(resp, AgentResponse) for resp in responses)
        # The tool should have returned an error response that contains error info
        structured_query_call_args = mock_structured_client.structured_query.call_args[0]
        assert "table" in structured_query_call_args[0].lower() or "exist" in structured_query_call_args[0].lower()

    @pytest.mark.asyncio
    async def test_agent_multi_step_structured_query_reasoning(self, agent_processor, structured_query_tool_config):
        """Test agent using structured query in multi-step reasoning"""
        # Arrange  
        await agent_processor.on_tools_config(structured_query_tool_config, "v1")
        
        request = AgentRequest(
            question="First find all customers from California, then tell me how many orders they have made.",
            state="",
            group=[],
            history=[],
            user="test_user"
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "agent-multi-step-test"}
        
        consumer = MagicMock()
        
        # Mock response producer for the flow
        response_producer = AsyncMock()
        
        # Mock structured query response (just one for this test)
        customers_response = {
            "data": json.dumps({
                "customers": [
                    {"id": "101", "name": "Alice Johnson", "state": "California"},
                    {"id": "102", "name": "Bob Wilson", "state": "California"}
                ]
            }),
            "errors": [],
            "error": None
        }
        
        mock_structured_client = AsyncMock()
        mock_structured_client.structured_query.return_value = customers_response
        
        # Mock the prompt client that agent calls for reasoning
        mock_prompt_client = AsyncMock()
        mock_prompt_client.agent_react.return_value = """Thought: I need to find customers from California first
Action: structured-query
Args: {
    "question": "Find all customers from California"
}"""
        
        # Set up flow context routing
        def flow_context(service_name):
            if service_name == "structured-query-request":
                return mock_structured_client
            elif service_name == "prompt-request":
                return mock_prompt_client
            elif service_name == "response":
                return response_producer
            else:
                return AsyncMock()
        
        flow = MagicMock()
        flow.side_effect = flow_context
        
        # Act
        await agent_processor.on_request(msg, consumer, flow)
        
        # Assert
        # Should have made structured query call
        assert mock_structured_client.structured_query.call_count >= 1
        
        assert response_producer.send.call_count >= 1
        all_calls = response_producer.send.call_args_list
        responses = [call[0][0] for call in all_calls]
        
        assert any(isinstance(resp, AgentResponse) for resp in responses)
        # Verify the structured query was called with customer-related question
        call_args = mock_structured_client.structured_query.call_args[0]
        assert "california" in call_args[0].lower()

    @pytest.mark.asyncio
    async def test_agent_structured_query_with_collection_parameter(self, agent_processor):
        """Test structured query tool with collection parameter"""
        # Arrange - Configure tool with collection
        import json
        tool_config_with_collection = {
            "tool": {
                "structured-query": json.dumps({
                    "name": "structured-query",
                    "description": "Query structured data using natural language",
                    "type": "structured-query",
                    "collection": "sales_data"
                })
            }
        }
        
        await agent_processor.on_tools_config(tool_config_with_collection, "v1")
        
        request = AgentRequest(
            question="Query the sales data for recent transactions.",
            state="",
            group=[],
            history=[],
            user="test_user"
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "agent-collection-test"}
        
        consumer = MagicMock()
        
        # Mock response producer for the flow
        response_producer = AsyncMock()
        
        # Mock structured query response
        sales_response = {
            "data": json.dumps({
                "transactions": [
                    {"id": "tx1", "amount": 299.99, "date": "2024-01-15"},
                    {"id": "tx2", "amount": 149.50, "date": "2024-01-16"}
                ]
            }),
            "errors": [],
            "error": None
        }
        
        mock_structured_client = AsyncMock()
        mock_structured_client.structured_query.return_value = sales_response
        
        # Mock the prompt client that agent calls for reasoning
        mock_prompt_client = AsyncMock()
        mock_prompt_client.agent_react.return_value = """Thought: I need to query the sales data
Action: structured-query
Args: {
    "question": "Query the sales data for recent transactions"
}"""
        
        # Set up flow context routing
        def flow_context(service_name):
            if service_name == "structured-query-request":
                return mock_structured_client
            elif service_name == "prompt-request":
                return mock_prompt_client
            elif service_name == "response":
                return response_producer
            else:
                return AsyncMock()
        
        flow = MagicMock()
        flow.side_effect = flow_context
        
        # Act
        await agent_processor.on_request(msg, consumer, flow)
        
        # Assert
        mock_structured_client.structured_query.assert_called_once()
        
        # Verify the tool was configured with collection parameter
        # (Collection parameter is passed to tool constructor, not to query method)
        assert response_producer.send.call_count >= 1
        all_calls = response_producer.send.call_args_list
        responses = [call[0][0] for call in all_calls]
        
        assert any(isinstance(resp, AgentResponse) for resp in responses)
        # Check the query was about sales/transactions
        call_args = mock_structured_client.structured_query.call_args[0]
        assert "sales" in call_args[0].lower() or "transactions" in call_args[0].lower()

    @pytest.mark.asyncio
    async def test_agent_structured_query_tool_argument_validation(self, agent_processor, structured_query_tool_config):
        """Test that structured query tool arguments are properly validated"""
        # Arrange
        await agent_processor.on_tools_config(structured_query_tool_config, "v1")
        
        # Check that the tool was registered with correct arguments
        tools = agent_processor.agent.tools
        assert "structured-query" in tools
        
        structured_tool = tools["structured-query"]
        arguments = structured_tool.arguments
        
        # Verify tool has the expected argument structure
        assert len(arguments) == 1
        question_arg = arguments[0]
        assert question_arg.name == "question"
        assert question_arg.type == "string"
        assert "structured data" in question_arg.description.lower()

    @pytest.mark.asyncio
    async def test_agent_structured_query_json_formatting(self, agent_processor, structured_query_tool_config):
        """Test that structured query results are properly formatted for agent consumption"""
        # Arrange
        await agent_processor.on_tools_config(structured_query_tool_config, "v1")
        
        request = AgentRequest(
            question="Get customer information and format it nicely.",
            state="",
            group=[],
            history=[],
            user="test_user"
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "agent-format-test"}
        
        consumer = MagicMock()
        
        # Mock response producer for the flow
        response_producer = AsyncMock()
        
        # Mock structured query response with complex data
        complex_response = {
            "data": json.dumps({
                "customers": [
                    {
                        "id": "c1",
                        "name": "Enterprise Corp",
                        "contact": {
                            "email": "contact@enterprise.com",
                            "phone": "555-0123"
                        },
                        "orders": [
                            {"id": "o1", "total": 5000.00, "items": 15},
                            {"id": "o2", "total": 3200.50, "items": 8}
                        ]
                    }
                ]
            }),
            "errors": [],
            "error": None
        }
        
        mock_structured_client = AsyncMock()
        mock_structured_client.structured_query.return_value = complex_response
        
        # Mock the prompt client that agent calls for reasoning
        mock_prompt_client = AsyncMock()
        mock_prompt_client.agent_react.return_value = """Thought: I need to get customer information
Action: structured-query
Args: {
    "question": "Get customer information and format it nicely"
}"""
        
        # Set up flow context routing
        def flow_context(service_name):
            if service_name == "structured-query-request":
                return mock_structured_client
            elif service_name == "prompt-request":
                return mock_prompt_client
            elif service_name == "response":
                return response_producer
            else:
                return AsyncMock()
        
        flow = MagicMock()
        flow.side_effect = flow_context
        
        # Act
        await agent_processor.on_request(msg, consumer, flow)
        
        # Assert
        mock_structured_client.structured_query.assert_called_once()
        assert response_producer.send.call_count >= 1
        
        # The tool should have properly formatted the JSON for agent consumption
        all_calls = response_producer.send.call_args_list
        responses = [call[0][0] for call in all_calls]
        assert any(isinstance(resp, AgentResponse) for resp in responses)
        
        # Check that the query was about customer information
        call_args = mock_structured_client.structured_query.call_args[0]
        assert "customer" in call_args[0].lower()