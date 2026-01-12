"""
Unit tests for Agent service non-streaming mode.
Tests that end_of_message and end_of_dialog flags are correctly set.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from trustgraph.agent.react.service import Processor
from trustgraph.schema import AgentRequest, AgentResponse
from trustgraph.agent.react.types import Final


class TestAgentServiceNonStreaming:
    """Test Agent service non-streaming behavior"""

    @patch('trustgraph.agent.react.service.AgentManager')
    @pytest.mark.asyncio
    async def test_non_streaming_intermediate_messages_have_correct_flags(self, mock_agent_manager_class):
        """
        Test that intermediate messages (thought/observation) in non-streaming mode
        have end_of_message=True and end_of_dialog=False.
        """
        # Setup processor
        processor = Processor(
            taskgroup=MagicMock(),
            id="test-agent",
            max_iterations=10
        )

        # Track all responses sent
        sent_responses = []

        # Setup mock agent manager
        mock_agent_instance = AsyncMock()
        mock_agent_manager_class.return_value = mock_agent_instance

        # Mock react to call think and observe callbacks
        async def mock_react(question, history, think, observe, answer, context, streaming):
            await think("I need to solve this.", is_final=True)
            await observe("The answer is 4.", is_final=True)
            return Final("4")

        mock_agent_instance.react = mock_react

        # Setup message with non-streaming request
        msg = MagicMock()
        msg.value.return_value = AgentRequest(
            question="What is 2 + 2?",
            user="trustgraph",
            streaming=False  # Non-streaming mode
        )
        msg.properties.return_value = {"id": "test-id"}

        # Setup flow mock
        consumer = MagicMock()
        flow = MagicMock()

        mock_producer = AsyncMock()

        async def capture_response(response, properties):
            sent_responses.append(response)

        mock_producer.send = AsyncMock(side_effect=capture_response)

        def flow_router(service_name):
            if service_name == "response":
                return mock_producer
            return AsyncMock()

        flow.side_effect = flow_router

        # Execute
        await processor.on_request(msg, consumer, flow)

        # Verify: should have 3 responses (thought, observation, answer)
        assert len(sent_responses) == 3, f"Expected 3 responses, got {len(sent_responses)}"

        # Check thought message
        thought_response = sent_responses[0]
        assert isinstance(thought_response, AgentResponse)
        assert thought_response.thought == "I need to solve this."
        assert thought_response.answer is None
        assert thought_response.end_of_message is True, "Thought message must have end_of_message=True"
        assert thought_response.end_of_dialog is False, "Thought message must have end_of_dialog=False"

        # Check observation message
        observation_response = sent_responses[1]
        assert isinstance(observation_response, AgentResponse)
        assert observation_response.observation == "The answer is 4."
        assert observation_response.answer is None
        assert observation_response.end_of_message is True, "Observation message must have end_of_message=True"
        assert observation_response.end_of_dialog is False, "Observation message must have end_of_dialog=False"

    @patch('trustgraph.agent.react.service.AgentManager')
    @pytest.mark.asyncio
    async def test_non_streaming_final_answer_has_correct_flags(self, mock_agent_manager_class):
        """
        Test that final answer in non-streaming mode has
        end_of_message=True and end_of_dialog=True.
        """
        # Setup processor
        processor = Processor(
            taskgroup=MagicMock(),
            id="test-agent",
            max_iterations=10
        )

        # Track all responses sent
        sent_responses = []

        # Setup mock agent manager
        mock_agent_instance = AsyncMock()
        mock_agent_manager_class.return_value = mock_agent_instance

        # Mock react to return Final directly
        async def mock_react(question, history, think, observe, answer, context, streaming):
            return Final("4")

        mock_agent_instance.react = mock_react

        # Setup message with non-streaming request
        msg = MagicMock()
        msg.value.return_value = AgentRequest(
            question="What is 2 + 2?",
            user="trustgraph",
            streaming=False  # Non-streaming mode
        )
        msg.properties.return_value = {"id": "test-id"}

        # Setup flow mock
        consumer = MagicMock()
        flow = MagicMock()

        mock_producer = AsyncMock()

        async def capture_response(response, properties):
            sent_responses.append(response)

        mock_producer.send = AsyncMock(side_effect=capture_response)

        def flow_router(service_name):
            if service_name == "response":
                return mock_producer
            return AsyncMock()

        flow.side_effect = flow_router

        # Execute
        await processor.on_request(msg, consumer, flow)

        # Verify: should have 1 response (final answer)
        assert len(sent_responses) == 1, f"Expected 1 response, got {len(sent_responses)}"

        # Check final answer message
        answer_response = sent_responses[0]
        assert isinstance(answer_response, AgentResponse)
        assert answer_response.answer == "4"
        assert answer_response.thought is None
        assert answer_response.observation is None
        assert answer_response.end_of_message is True, "Final answer must have end_of_message=True"
        assert answer_response.end_of_dialog is True, "Final answer must have end_of_dialog=True"

    @pytest.mark.asyncio
    async def test_error_response_has_correct_flags(self):
        """
        Test that error responses have end_of_message=True and end_of_dialog=True.
        """
        # Setup processor that will error
        processor = Processor(
            taskgroup=MagicMock(),
            id="test-agent",
            max_iterations=10
        )

        # Track all responses sent
        sent_responses = []

        # Setup message
        msg = MagicMock()
        msg.value.side_effect = Exception("Test error")
        msg.properties.return_value = {"id": "test-id"}

        # Setup flow mock
        consumer = MagicMock()
        flow = MagicMock()
        flow.producer = {"response": AsyncMock()}

        async def capture_response(response, properties):
            sent_responses.append(response)

        flow.producer["response"].send = AsyncMock(side_effect=capture_response)

        # Execute
        await processor.on_request(msg, consumer, flow)

        # Verify: should have 1 error response
        assert len(sent_responses) == 1, f"Expected 1 error response, got {len(sent_responses)}"

        # Check error response
        error_response = sent_responses[0]
        assert isinstance(error_response, AgentResponse)
        assert error_response.error is not None
        assert "Test error" in error_response.error.message
        assert error_response.end_of_message is True, "Error response must have end_of_message=True"
        assert error_response.end_of_dialog is True, "Error response must have end_of_dialog=True"
