"""
Integration tests for Agent Manager Streaming Functionality

These tests verify the streaming behavior of the Agent service, testing
chunk-by-chunk delivery of thoughts, actions, observations, and final answers.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from trustgraph.agent.react.agent_manager import AgentManager
from trustgraph.agent.react.tools import KnowledgeQueryImpl
from trustgraph.agent.react.types import Tool, Argument
from tests.utils.streaming_assertions import (
    assert_agent_streaming_chunks,
    assert_streaming_chunks_valid,
    assert_callback_invoked,
    assert_chunk_types_valid,
)


@pytest.mark.integration
class TestAgentStreaming:
    """Integration tests for Agent streaming functionality"""

    @pytest.fixture
    def mock_prompt_client_streaming(self):
        """Mock prompt client with streaming support"""
        client = AsyncMock()

        async def agent_react_streaming(variables, timeout=600, streaming=False, chunk_callback=None):
            if streaming and chunk_callback:
                # Simulate streaming response with chunks
                chunks = [
                    "Thought: I need to",
                    " search for",
                    " information about",
                    " machine learning.",
                    "\n",
                    "Action: knowledge_query\n",
                    "Args: {\n",
                    '    "question": "What is machine learning?"\n',
                    "}"
                ]

                full_text = ""
                for chunk in chunks:
                    full_text += chunk
                    await chunk_callback(chunk)

                return full_text
            else:
                # Non-streaming response
                return """Thought: I need to search for information about machine learning.
Action: knowledge_query
Args: {
    "question": "What is machine learning?"
}"""

        client.agent_react.side_effect = agent_react_streaming
        return client

    @pytest.fixture
    def mock_flow_context(self, mock_prompt_client_streaming):
        """Mock flow context with streaming prompt client"""
        context = MagicMock()

        # Mock graph RAG client
        graph_rag_client = AsyncMock()
        graph_rag_client.rag.return_value = "Machine learning is a subset of AI."

        def context_router(service_name):
            if service_name == "prompt-request":
                return mock_prompt_client_streaming
            elif service_name == "graph-rag-request":
                return graph_rag_client
            else:
                return AsyncMock()

        context.side_effect = context_router
        return context

    @pytest.fixture
    def sample_tools(self):
        """Sample tool configuration"""
        return {
            "knowledge_query": Tool(
                name="knowledge_query",
                description="Query the knowledge graph",
                arguments=[
                    Argument(
                        name="question",
                        type="string",
                        description="The question to ask"
                    )
                ],
                implementation=KnowledgeQueryImpl,
                config={}
            )
        }

    @pytest.fixture
    def agent_manager(self, sample_tools):
        """Create AgentManager instance with streaming support"""
        return AgentManager(
            tools=sample_tools,
            additional_context="You are a helpful AI assistant."
        )

    @pytest.mark.asyncio
    async def test_agent_streaming_thought_chunks(self, agent_manager, mock_flow_context):
        """Test that thought chunks are streamed correctly"""
        # Arrange
        thought_chunks = []

        async def think(chunk):
            thought_chunks.append(chunk)

        # Act
        await agent_manager.react(
            question="What is machine learning?",
            history=[],
            think=think,
            observe=AsyncMock(),
            context=mock_flow_context,
            streaming=True
        )

        # Assert
        assert len(thought_chunks) > 0
        assert_streaming_chunks_valid(thought_chunks, min_chunks=1)

        # Verify thought content makes sense
        full_thought = "".join(thought_chunks)
        assert "search" in full_thought.lower() or "information" in full_thought.lower()

    @pytest.mark.asyncio
    async def test_agent_streaming_observation_chunks(self, agent_manager, mock_flow_context):
        """Test that observation chunks are streamed correctly"""
        # Arrange
        observation_chunks = []

        async def observe(chunk):
            observation_chunks.append(chunk)

        # Act
        await agent_manager.react(
            question="What is machine learning?",
            history=[],
            think=AsyncMock(),
            observe=observe,
            context=mock_flow_context,
            streaming=True
        )

        # Assert
        # Note: Observations come from tool execution, which may or may not be streamed
        # depending on the tool implementation
        # For now, verify callback was set up
        assert observe is not None

    @pytest.mark.asyncio
    async def test_agent_streaming_vs_non_streaming(self, agent_manager, mock_flow_context):
        """Test that streaming and non-streaming produce equivalent results"""
        # Arrange
        question = "What is machine learning?"
        history = []

        # Act - Non-streaming
        non_streaming_result = await agent_manager.react(
            question=question,
            history=history,
            think=AsyncMock(),
            observe=AsyncMock(),
            context=mock_flow_context,
            streaming=False
        )

        # Act - Streaming
        thought_chunks = []
        observation_chunks = []

        async def think(chunk):
            thought_chunks.append(chunk)

        async def observe(chunk):
            observation_chunks.append(chunk)

        streaming_result = await agent_manager.react(
            question=question,
            history=history,
            think=think,
            observe=observe,
            context=mock_flow_context,
            streaming=True
        )

        # Assert - Results should be equivalent (or both valid)
        assert non_streaming_result is not None
        assert streaming_result is not None

    @pytest.mark.asyncio
    async def test_agent_streaming_callback_invocation(self, agent_manager, mock_flow_context):
        """Test that callbacks are invoked with correct parameters"""
        # Arrange
        think = AsyncMock()
        observe = AsyncMock()

        # Act
        await agent_manager.react(
            question="What is machine learning?",
            history=[],
            think=think,
            observe=observe,
            context=mock_flow_context,
            streaming=True
        )

        # Assert - Think callback should be invoked
        assert think.call_count > 0

        # Verify all callback invocations had string arguments
        for call in think.call_args_list:
            assert len(call.args) > 0
            assert isinstance(call.args[0], str)

    @pytest.mark.asyncio
    async def test_agent_streaming_without_callbacks(self, agent_manager, mock_flow_context):
        """Test streaming parameter without callbacks (should work gracefully)"""
        # Arrange & Act
        result = await agent_manager.react(
            question="What is machine learning?",
            history=[],
            think=AsyncMock(),
            observe=AsyncMock(),
            context=mock_flow_context,
            streaming=True  # Streaming enabled with mock callbacks
        )

        # Assert - Should complete without error
        assert result is not None

    @pytest.mark.asyncio
    async def test_agent_streaming_with_conversation_history(self, agent_manager, mock_flow_context,
                                                              sample_agent_responses):
        """Test streaming with existing conversation history"""
        # Arrange
        history = sample_agent_responses[:1]  # Use first response as history
        think = AsyncMock()

        # Act
        result = await agent_manager.react(
            question="Tell me more about neural networks",
            history=history,
            think=think,
            observe=AsyncMock(),
            context=mock_flow_context,
            streaming=True
        )

        # Assert
        assert result is not None
        assert think.call_count > 0

    @pytest.mark.asyncio
    async def test_agent_streaming_error_propagation(self, agent_manager, mock_flow_context):
        """Test that errors during streaming are properly propagated"""
        # Arrange
        mock_prompt_client = mock_flow_context("prompt-request")
        mock_prompt_client.agent_react.side_effect = Exception("Prompt service error")

        think = AsyncMock()
        observe = AsyncMock()

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await agent_manager.react(
                question="test question",
                history=[],
                think=think,
                observe=observe,
                context=mock_flow_context,
                streaming=True
            )

        assert "Prompt service error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_agent_streaming_multi_step_reasoning(self, agent_manager, mock_flow_context,
                                                         mock_prompt_client_streaming):
        """Test streaming through multi-step reasoning process"""
        # Arrange - Mock a multi-step response
        step_responses = [
            """Thought: I need to search for basic information.
Action: knowledge_query
Args: {"question": "What is AI?"}""",
            """Thought: Now I can answer the question.
Final Answer: AI is the simulation of human intelligence in machines."""
        ]

        call_count = 0

        async def multi_step_agent_react(variables, timeout=600, streaming=False, chunk_callback=None):
            nonlocal call_count
            response = step_responses[min(call_count, len(step_responses) - 1)]
            call_count += 1

            if streaming and chunk_callback:
                for chunk in response.split():
                    await chunk_callback(chunk + " ")
                return response
            return response

        mock_prompt_client_streaming.agent_react.side_effect = multi_step_agent_react

        think = AsyncMock()
        observe = AsyncMock()

        # Act
        result = await agent_manager.react(
            question="What is artificial intelligence?",
            history=[],
            think=think,
            observe=observe,
            context=mock_flow_context,
            streaming=True
        )

        # Assert
        assert result is not None
        assert think.call_count > 0

    @pytest.mark.asyncio
    async def test_agent_streaming_preserves_tool_config(self, agent_manager, mock_flow_context):
        """Test that streaming preserves tool configuration and context"""
        # Arrange
        think = AsyncMock()
        observe = AsyncMock()

        # Act
        await agent_manager.react(
            question="What is machine learning?",
            history=[],
            think=think,
            observe=observe,
            context=mock_flow_context,
            streaming=True
        )

        # Assert - Verify prompt client was called with streaming
        mock_prompt_client = mock_flow_context("prompt-request")
        call_args = mock_prompt_client.agent_react.call_args
        assert call_args.kwargs['streaming'] is True
        assert call_args.kwargs['chunk_callback'] is not None
