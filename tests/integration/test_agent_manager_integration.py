"""
Integration tests for Agent Manager (ReAct Pattern) Service

These tests verify the end-to-end functionality of the Agent Manager service,
testing the ReAct pattern (Think-Act-Observe), tool coordination, multi-step reasoning,
and conversation state management.
Following the TEST_STRATEGY.md approach for integration testing.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from trustgraph.agent.react.agent_manager import AgentManager
from trustgraph.agent.react.tools import KnowledgeQueryImpl, TextCompletionImpl, McpToolImpl
from trustgraph.agent.react.types import Action, Final, Tool, Argument
from trustgraph.schema import AgentRequest, AgentResponse, AgentStep, Error


@pytest.mark.integration
class TestAgentManagerIntegration:
    """Integration tests for Agent Manager ReAct pattern coordination"""

    @pytest.fixture
    def mock_flow_context(self):
        """Mock flow context for service coordination"""
        context = MagicMock()
        
        # Mock prompt client
        prompt_client = AsyncMock()
        prompt_client.agent_react.return_value = """Thought: I need to search for information about machine learning
Action: knowledge_query
Args: {
    "question": "What is machine learning?"
}"""
        
        # Mock graph RAG client
        graph_rag_client = AsyncMock()
        graph_rag_client.rag.return_value = "Machine learning is a subset of AI that enables computers to learn from data."
        
        # Mock text completion client
        text_completion_client = AsyncMock()
        text_completion_client.question.return_value = "Machine learning involves algorithms that improve through experience."
        
        # Mock MCP tool client
        mcp_tool_client = AsyncMock()
        mcp_tool_client.invoke.return_value = "Tool execution successful"
        
        # Configure context to return appropriate clients
        def context_router(service_name):
            if service_name == "prompt-request":
                return prompt_client
            elif service_name == "graph-rag-request":
                return graph_rag_client
            elif service_name == "prompt-request":
                return text_completion_client
            elif service_name == "mcp-tool-request":
                return mcp_tool_client
            else:
                return AsyncMock()
        
        context.side_effect = context_router
        return context

    @pytest.fixture
    def sample_tools(self):
        """Sample tool configuration for testing"""
        return {
            "knowledge_query": Tool(
                name="knowledge_query",
                description="Query the knowledge graph for information",
                arguments=[
                    Argument(
                        name="question",
                        type="string", 
                        description="The question to ask the knowledge graph"
                    )
                ],
                implementation=KnowledgeQueryImpl,
                config={}
            ),
            "text_completion": Tool(
                name="text_completion",
                description="Generate text completion using LLM",
                arguments=[
                    Argument(
                        name="question",
                        type="string",
                        description="The question to ask the LLM"
                    )
                ],
                implementation=TextCompletionImpl,
                config={}
            ),
            "web_search": Tool(
                name="web_search",
                description="Search the web for information",
                arguments=[
                    Argument(
                        name="query",
                        type="string",
                        description="The search query"
                    )
                ],
                implementation=lambda context: AsyncMock(invoke=AsyncMock(return_value="Web search results")),
                config={}
            )
        }

    @pytest.fixture
    def agent_manager(self, sample_tools):
        """Create agent manager with sample tools"""
        return AgentManager(
            tools=sample_tools,
            additional_context="You are a helpful AI assistant with access to knowledge and tools."
        )

    @pytest.mark.asyncio
    async def test_agent_manager_reasoning_cycle(self, agent_manager, mock_flow_context):
        """Test basic reasoning cycle with tool selection"""
        # Arrange
        question = "What is machine learning?"
        history = []

        # Act
        action = await agent_manager.reason(question, history, mock_flow_context)

        # Assert
        assert isinstance(action, Action)
        assert action.thought == "I need to search for information about machine learning"
        assert action.name == "knowledge_query"
        assert action.arguments == {"question": "What is machine learning?"}
        assert action.observation == ""

        # Verify prompt client was called correctly
        prompt_client = mock_flow_context("prompt-request")
        prompt_client.agent_react.assert_called_once()
        
        # Verify the prompt variables passed to agent_react
        call_args = prompt_client.agent_react.call_args
        variables = call_args[0][0]
        assert variables["question"] == question
        assert len(variables["tools"]) == 3  # knowledge_query, text_completion, web_search
        assert variables["context"] == "You are a helpful AI assistant with access to knowledge and tools."

    @pytest.mark.asyncio
    async def test_agent_manager_final_answer(self, agent_manager, mock_flow_context):
        """Test agent manager returning final answer"""
        # Arrange
        mock_flow_context("prompt-request").agent_react.return_value = """Thought: I have enough information to answer the question
Final Answer: Machine learning is a field of AI that enables computers to learn from data."""
        
        question = "What is machine learning?"
        history = []

        # Act
        action = await agent_manager.reason(question, history, mock_flow_context)

        # Assert
        assert isinstance(action, Final)
        assert action.thought == "I have enough information to answer the question"
        assert action.final == "Machine learning is a field of AI that enables computers to learn from data."

    @pytest.mark.asyncio
    async def test_agent_manager_react_with_tool_execution(self, agent_manager, mock_flow_context):
        """Test full ReAct cycle with tool execution"""
        # Arrange
        question = "What is machine learning?"
        history = []
        
        think_callback = AsyncMock()
        observe_callback = AsyncMock()

        # Act
        action = await agent_manager.react(question, history, think_callback, observe_callback, mock_flow_context)

        # Assert
        assert isinstance(action, Action)
        assert action.thought == "I need to search for information about machine learning"
        assert action.name == "knowledge_query"
        assert action.arguments == {"question": "What is machine learning?"}
        assert action.observation == "Machine learning is a subset of AI that enables computers to learn from data."

        # Verify callbacks were called
        think_callback.assert_called_once_with("I need to search for information about machine learning")
        observe_callback.assert_called_once_with("Machine learning is a subset of AI that enables computers to learn from data.")

        # Verify tool was executed
        graph_rag_client = mock_flow_context("graph-rag-request")
        graph_rag_client.rag.assert_called_once_with("What is machine learning?", collection="default")

    @pytest.mark.asyncio
    async def test_agent_manager_react_with_final_answer(self, agent_manager, mock_flow_context):
        """Test ReAct cycle ending with final answer"""
        # Arrange
        mock_flow_context("prompt-request").agent_react.return_value = """Thought: I can provide a direct answer
Final Answer: Machine learning is a branch of artificial intelligence."""
        
        question = "What is machine learning?"
        history = []
        
        think_callback = AsyncMock()
        observe_callback = AsyncMock()

        # Act
        action = await agent_manager.react(question, history, think_callback, observe_callback, mock_flow_context)

        # Assert
        assert isinstance(action, Final)
        assert action.thought == "I can provide a direct answer"
        assert action.final == "Machine learning is a branch of artificial intelligence."

        # Verify only think callback was called (no observation for final answer)
        think_callback.assert_called_once_with("I can provide a direct answer")
        observe_callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_agent_manager_with_conversation_history(self, agent_manager, mock_flow_context):
        """Test agent manager with conversation history"""
        # Arrange
        question = "Can you tell me more about neural networks?"
        history = [
            Action(
                thought="I need to search for information about machine learning",
                name="knowledge_query",
                arguments={"question": "What is machine learning?"},
                observation="Machine learning is a subset of AI that enables computers to learn from data."
            )
        ]

        # Act
        action = await agent_manager.reason(question, history, mock_flow_context)

        # Assert
        assert isinstance(action, Action)
        
        # Verify history was included in prompt variables
        prompt_client = mock_flow_context("prompt-request")
        call_args = prompt_client.agent_react.call_args
        variables = call_args[0][0]
        assert len(variables["history"]) == 1
        assert variables["history"][0]["thought"] == "I need to search for information about machine learning"
        assert variables["history"][0]["action"] == "knowledge_query"
        assert variables["history"][0]["observation"] == "Machine learning is a subset of AI that enables computers to learn from data."

    @pytest.mark.asyncio
    async def test_agent_manager_tool_selection(self, agent_manager, mock_flow_context):
        """Test agent manager selecting different tools"""
        # Test different tool selections
        tool_scenarios = [
            ("knowledge_query", "graph-rag-request"),
            ("text_completion", "prompt-request"),
        ]

        for tool_name, expected_service in tool_scenarios:
            # Arrange
            mock_flow_context("prompt-request").agent_react.return_value = f"""Thought: I need to use {tool_name}
Action: {tool_name}
Args: {{
    "question": "test question"
}}"""
            
            think_callback = AsyncMock()
            observe_callback = AsyncMock()

            # Act
            action = await agent_manager.react("test question", [], think_callback, observe_callback, mock_flow_context)

            # Assert
            assert isinstance(action, Action)
            assert action.name == tool_name
            
            # Verify correct service was called
            if tool_name == "knowledge_query":
                mock_flow_context("graph-rag-request").rag.assert_called_with("test question", collection="default")
            elif tool_name == "text_completion":
                mock_flow_context("prompt-request").question.assert_called()

            # Reset mocks for next iteration
            for service in ["prompt-request", "graph-rag-request", "prompt-request"]:
                mock_flow_context(service).reset_mock()

    @pytest.mark.asyncio
    async def test_agent_manager_unknown_tool_error(self, agent_manager, mock_flow_context):
        """Test agent manager error handling for unknown tool"""
        # Arrange
        mock_flow_context("prompt-request").agent_react.return_value = """Thought: I need to use an unknown tool
Action: unknown_tool
Args: {
    "param": "value"
}"""
        
        think_callback = AsyncMock()
        observe_callback = AsyncMock()

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            await agent_manager.react("test question", [], think_callback, observe_callback, mock_flow_context)
        
        assert "No action for unknown_tool!" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_agent_manager_tool_execution_error(self, agent_manager, mock_flow_context):
        """Test agent manager handling tool execution errors"""
        # Arrange
        mock_flow_context("graph-rag-request").rag.side_effect = Exception("Tool execution failed")
        
        think_callback = AsyncMock()
        observe_callback = AsyncMock()

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await agent_manager.react("test question", [], think_callback, observe_callback, mock_flow_context)
        
        assert "Tool execution failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_agent_manager_multiple_tools_coordination(self, agent_manager, mock_flow_context):
        """Test agent manager coordination with multiple available tools"""
        # Arrange
        question = "Find information about AI and summarize it"
        
        # Mock multi-step reasoning
        mock_flow_context("prompt-request").agent_react.return_value = """Thought: I need to search for AI information first
Action: knowledge_query
Args: {
    "question": "What is artificial intelligence?"
}"""

        # Act
        action = await agent_manager.reason(question, [], mock_flow_context)

        # Assert
        assert isinstance(action, Action)
        assert action.name == "knowledge_query"
        
        # Verify tool information was passed to prompt
        prompt_client = mock_flow_context("prompt-request")
        call_args = prompt_client.agent_react.call_args
        variables = call_args[0][0]
        
        # Should have all 3 tools available
        tool_names = [tool["name"] for tool in variables["tools"]]
        assert "knowledge_query" in tool_names
        assert "text_completion" in tool_names
        assert "web_search" in tool_names

    @pytest.mark.asyncio
    async def test_agent_manager_tool_argument_validation(self, agent_manager, mock_flow_context):
        """Test agent manager with various tool argument patterns"""
        # Arrange
        test_cases = [
            {
                "action": "knowledge_query",
                "arguments": {"question": "What is deep learning?"},
                "expected_service": "graph-rag-request"
            },
            {
                "action": "text_completion", 
                "arguments": {"question": "Explain neural networks"},
                "expected_service": "prompt-request"
            },
            {
                "action": "web_search",
                "arguments": {"query": "latest AI research"},
                "expected_service": None  # Custom mock
            }
        ]

        for test_case in test_cases:
            # Arrange
            # Format arguments as JSON
            import json
            args_json = json.dumps(test_case['arguments'], indent=4)
            mock_flow_context("prompt-request").agent_react.return_value = f"""Thought: Using {test_case['action']}
Action: {test_case['action']}
Args: {args_json}"""
            
            think_callback = AsyncMock()
            observe_callback = AsyncMock()

            # Act
            action = await agent_manager.react("test", [], think_callback, observe_callback, mock_flow_context)

            # Assert
            assert isinstance(action, Action)
            assert action.name == test_case['action']
            assert action.arguments == test_case['arguments']
            
            # Reset mocks
            for service in ["prompt-request", "graph-rag-request", "prompt-request"]:
                mock_flow_context(service).reset_mock()

    @pytest.mark.asyncio
    async def test_agent_manager_context_integration(self, agent_manager, mock_flow_context):
        """Test agent manager integration with additional context"""
        # Arrange
        agent_with_context = AgentManager(
            tools={"knowledge_query": agent_manager.tools["knowledge_query"]},
            additional_context="You are an expert in machine learning research."
        )
        
        question = "What are the latest developments in AI?"

        # Act
        action = await agent_with_context.reason(question, [], mock_flow_context)

        # Assert
        prompt_client = mock_flow_context("prompt-request")
        call_args = prompt_client.agent_react.call_args
        variables = call_args[0][0]
        
        assert variables["context"] == "You are an expert in machine learning research."
        assert variables["question"] == question

    @pytest.mark.asyncio
    async def test_agent_manager_empty_tools(self, mock_flow_context):
        """Test agent manager with no tools available"""
        # Arrange
        agent_no_tools = AgentManager(tools={}, additional_context="")
        
        question = "What is machine learning?"

        # Act
        action = await agent_no_tools.reason(question, [], mock_flow_context)

        # Assert
        prompt_client = mock_flow_context("prompt-request")
        call_args = prompt_client.agent_react.call_args
        variables = call_args[0][0]
        
        assert len(variables["tools"]) == 0
        assert variables["tool_names"] == ""

    @pytest.mark.asyncio
    async def test_agent_manager_tool_response_processing(self, agent_manager, mock_flow_context):
        """Test agent manager processing different tool response types"""
        # Arrange
        response_scenarios = [
            "Simple text response",
            "Multi-line response\nwith several lines\nof information",
            "Response with special characters: @#$%^&*()_+-=[]{}|;':\",./<>?",
            "   Response with whitespace   ",
            ""  # Empty response
        ]

        for expected_response in response_scenarios:
            # Set up mock response
            mock_flow_context("graph-rag-request").rag.return_value = expected_response
            
            think_callback = AsyncMock()
            observe_callback = AsyncMock()

            # Act
            action = await agent_manager.react("test question", [], think_callback, observe_callback, mock_flow_context)

            # Assert
            assert isinstance(action, Action)
            assert action.observation == expected_response.strip()
            observe_callback.assert_called_with(expected_response.strip())
            
            # Reset mocks
            mock_flow_context("graph-rag-request").reset_mock()

    @pytest.mark.asyncio
    async def test_agent_manager_malformed_response_handling(self, agent_manager, mock_flow_context):
        """Test agent manager handling of malformed text responses"""
        # Test cases with expected error messages
        test_cases = [
            # Missing action/final answer
            {
                "response": "Thought: I need to do something",
                "error_contains": "Response has thought but no action or final answer"
            },
            # Invalid JSON in Args
            {
                "response": """Thought: I need to search
Action: knowledge_query
Args: {invalid json}""",
                "error_contains": "Invalid JSON in Args"
            },
            # Empty response
            {
                "response": "",
                "error_contains": "Could not parse response"
            },
            # Only whitespace
            {
                "response": "   \n\t  ",
                "error_contains": "Could not parse response"
            },
            # Missing Args for action (should create empty args dict)
            {
                "response": """Thought: I need to search
Action: knowledge_query""",
                "error_contains": None  # This should actually succeed with empty args
            },
            # Incomplete JSON
            {
                "response": """Thought: I need to search
Action: knowledge_query
Args: {
    "question": "test"
""",
                "error_contains": "Invalid JSON in Args"
            },
        ]
        
        for test_case in test_cases:
            mock_flow_context("prompt-request").agent_react.return_value = test_case["response"]
            
            if test_case["error_contains"]:
                # Should raise an error
                with pytest.raises(RuntimeError) as exc_info:
                    await agent_manager.reason("test question", [], mock_flow_context)
                
                assert "Failed to parse agent response" in str(exc_info.value)
                assert test_case["error_contains"] in str(exc_info.value)
            else:
                # Should succeed
                action = await agent_manager.reason("test question", [], mock_flow_context)
                assert isinstance(action, Action)
                assert action.name == "knowledge_query"
                assert action.arguments == {}

    @pytest.mark.asyncio
    async def test_agent_manager_text_parsing_edge_cases(self, agent_manager, mock_flow_context):
        """Test edge cases in text parsing"""
        # Test response with markdown code blocks
        mock_flow_context("prompt-request").agent_react.return_value = """```
Thought: I need to search for information
Action: knowledge_query
Args: {
    "question": "What is AI?"
}
```"""
        
        action = await agent_manager.reason("test", [], mock_flow_context)
        assert isinstance(action, Action)
        assert action.thought == "I need to search for information"
        assert action.name == "knowledge_query"
        
        # Test response with extra whitespace
        mock_flow_context("prompt-request").agent_react.return_value = """

Thought:    I need to think about this    
Action:   knowledge_query   
Args:    {
    "question": "test"
}

"""
        
        action = await agent_manager.reason("test", [], mock_flow_context)
        assert isinstance(action, Action)
        assert action.thought == "I need to think about this"
        assert action.name == "knowledge_query"

    @pytest.mark.asyncio
    async def test_agent_manager_multiline_content(self, agent_manager, mock_flow_context):
        """Test handling of multi-line thoughts and final answers"""
        # Multi-line thought
        mock_flow_context("prompt-request").agent_react.return_value = """Thought: I need to consider multiple factors:
1. The user's question is complex
2. I should search for comprehensive information
3. This requires using the knowledge query tool
Action: knowledge_query
Args: {
    "question": "complex query"
}"""
        
        action = await agent_manager.reason("test", [], mock_flow_context)
        assert isinstance(action, Action)
        assert "multiple factors" in action.thought
        assert "knowledge query tool" in action.thought
        
        # Multi-line final answer
        mock_flow_context("prompt-request").agent_react.return_value = """Thought: I have gathered enough information
Final Answer: Here is a comprehensive answer:
1. First point about the topic
2. Second point with details
3. Final conclusion

This covers all aspects of the question."""
        
        action = await agent_manager.reason("test", [], mock_flow_context)
        assert isinstance(action, Final)
        assert "First point" in action.final
        assert "Final conclusion" in action.final
        assert "all aspects" in action.final

    @pytest.mark.asyncio
    async def test_agent_manager_json_args_special_characters(self, agent_manager, mock_flow_context):
        """Test JSON arguments with special characters and edge cases"""
        # Test with special characters in JSON (properly escaped)
        mock_flow_context("prompt-request").agent_react.return_value = """Thought: Processing special characters
Action: knowledge_query
Args: {
    "question": "What about \\"quotes\\" and 'apostrophes'?",
    "context": "Line 1\\nLine 2\\tTabbed",
    "special": "Symbols: @#$%^&*()_+-=[]{}|;':,.<>?"
}"""
        
        action = await agent_manager.reason("test", [], mock_flow_context)
        assert isinstance(action, Action)
        assert action.arguments["question"] == 'What about "quotes" and \'apostrophes\'?'
        assert action.arguments["context"] == "Line 1\nLine 2\tTabbed"
        assert "@#$%^&*" in action.arguments["special"]
        
        # Test with nested JSON
        mock_flow_context("prompt-request").agent_react.return_value = """Thought: Complex arguments
Action: web_search
Args: {
    "query": "test",
    "options": {
        "limit": 10,
        "filters": ["recent", "relevant"],
        "metadata": {
            "source": "user",
            "timestamp": "2024-01-01"
        }
    }
}"""
        
        action = await agent_manager.reason("test", [], mock_flow_context)
        assert isinstance(action, Action)
        assert action.arguments["options"]["limit"] == 10
        assert "recent" in action.arguments["options"]["filters"]
        assert action.arguments["options"]["metadata"]["source"] == "user"

    @pytest.mark.asyncio
    async def test_agent_manager_final_answer_json_format(self, agent_manager, mock_flow_context):
        """Test final answers that contain JSON-like content"""
        # Final answer with JSON content
        mock_flow_context("prompt-request").agent_react.return_value = """Thought: I can provide the data in JSON format
Final Answer: {
    "result": "success",
    "data": {
        "name": "Machine Learning",
        "type": "AI Technology",
        "applications": ["NLP", "Computer Vision", "Robotics"]
    },
    "confidence": 0.95
}"""
        
        action = await agent_manager.reason("test", [], mock_flow_context)
        assert isinstance(action, Final)
        # The final answer should preserve the JSON structure as a string
        assert '"result": "success"' in action.final
        assert '"applications":' in action.final

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_agent_manager_performance_with_large_history(self, agent_manager, mock_flow_context):
        """Test agent manager performance with large conversation history"""
        # Arrange
        large_history = [
            Action(
                thought=f"Step {i} thinking",
                name="knowledge_query",
                arguments={"question": f"Question {i}"},
                observation=f"Observation {i}"
            )
            for i in range(50)  # Large history
        ]
        
        question = "Final question"

        # Act
        import time
        start_time = time.time()
        
        action = await agent_manager.reason(question, large_history, mock_flow_context)
        
        end_time = time.time()
        execution_time = end_time - start_time

        # Assert
        assert isinstance(action, Action)
        assert execution_time < 5.0  # Should complete within reasonable time
        
        # Verify history was processed correctly
        prompt_client = mock_flow_context("prompt-request")
        call_args = prompt_client.agent_react.call_args
        variables = call_args[0][0]
        assert len(variables["history"]) == 50

    @pytest.mark.asyncio
    async def test_agent_manager_json_serialization(self, agent_manager, mock_flow_context):
        """Test agent manager handling of JSON serialization in prompts"""
        # Arrange
        complex_history = [
            Action(
                thought="Complex thinking with special characters: \"quotes\", 'apostrophes', and symbols",
                name="knowledge_query",
                arguments={"question": "What about JSON serialization?", "complex": {"nested": "value"}},
                observation="Response with JSON: {\"key\": \"value\"}"
            )
        ]
        
        question = "Handle JSON properly"

        # Act
        action = await agent_manager.reason(question, complex_history, mock_flow_context)

        # Assert
        assert isinstance(action, Action)
        
        # Verify JSON was properly serialized in prompt
        prompt_client = mock_flow_context("prompt-request")
        call_args = prompt_client.agent_react.call_args
        variables = call_args[0][0]
        
        # Should not raise JSON serialization errors
        json_str = json.dumps(variables, indent=4)
        assert len(json_str) > 0

    @pytest.mark.asyncio
    async def test_knowledge_query_with_default_collection(self, mock_flow_context):
        """Test KnowledgeQueryImpl uses default collection when not specified"""
        # Arrange
        tool = KnowledgeQueryImpl(mock_flow_context)
        
        # Act
        result = await tool.invoke(question="What is AI?")
        
        # Assert
        graph_rag_client = mock_flow_context("graph-rag-request")
        graph_rag_client.rag.assert_called_once_with("What is AI?", collection="default")

    @pytest.mark.asyncio
    async def test_knowledge_query_with_custom_collection(self, mock_flow_context):
        """Test KnowledgeQueryImpl uses custom collection when specified"""
        # Arrange
        tool = KnowledgeQueryImpl(mock_flow_context, collection="custom_collection")
        
        # Act
        result = await tool.invoke(question="What is machine learning?")
        
        # Assert
        graph_rag_client = mock_flow_context("graph-rag-request")
        graph_rag_client.rag.assert_called_once_with("What is machine learning?", collection="custom_collection")

    @pytest.mark.asyncio
    async def test_knowledge_query_with_none_collection(self, mock_flow_context):
        """Test KnowledgeQueryImpl handles None collection properly"""
        # Arrange
        tool = KnowledgeQueryImpl(mock_flow_context, collection=None)
        
        # Act
        result = await tool.invoke(question="Explain neural networks")
        
        # Assert
        graph_rag_client = mock_flow_context("graph-rag-request")
        graph_rag_client.rag.assert_called_once_with("Explain neural networks", collection="default")

    @pytest.mark.asyncio
    async def test_agent_manager_knowledge_query_collection_integration(self, mock_flow_context):
        """Test agent manager integration with KnowledgeQueryImpl collection parameter"""
        # Arrange
        custom_tools = {
            "knowledge_query_custom": Tool(
                name="knowledge_query_custom",
                description="Query custom knowledge collection",
                arguments=[
                    Argument(
                        name="question",
                        type="string",
                        description="The question to ask"
                    )
                ],
                implementation=KnowledgeQueryImpl,
                config={"collection": "research_papers"}
            ),
            "knowledge_query_default": Tool(
                name="knowledge_query_default",
                description="Query default knowledge collection",
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
        
        agent = AgentManager(tools=custom_tools, additional_context="")
        
        # Mock response for custom collection query
        mock_flow_context("prompt-request").agent_react.return_value = """Thought: I need to search in the research papers
Action: knowledge_query_custom
Args: {
    "question": "Latest AI research?"
}"""
        
        think_callback = AsyncMock()
        observe_callback = AsyncMock()
        
        # Act
        action = await agent.react("Find latest research", [], think_callback, observe_callback, mock_flow_context)
        
        # Assert
        assert isinstance(action, Action)
        assert action.name == "knowledge_query_custom"
        
        # Verify the custom collection was used
        graph_rag_client = mock_flow_context("graph-rag-request")
        graph_rag_client.rag.assert_called_once_with("Latest AI research?", collection="research_papers")

    @pytest.mark.asyncio
    async def test_knowledge_query_multiple_collections(self, mock_flow_context):
        """Test multiple KnowledgeQueryImpl instances with different collections"""
        # Arrange
        tools = {
            "general_kb": KnowledgeQueryImpl(mock_flow_context, collection="general"),
            "technical_kb": KnowledgeQueryImpl(mock_flow_context, collection="technical"),
            "research_kb": KnowledgeQueryImpl(mock_flow_context, collection="research")
        }
        
        # Act & Assert for each tool
        test_cases = [
            ("general_kb", "What is Python?", "general"),
            ("technical_kb", "Explain TCP/IP", "technical"),
            ("research_kb", "Latest ML papers", "research")
        ]
        
        for tool_name, question, expected_collection in test_cases:
            # Reset mock
            mock_flow_context("graph-rag-request").reset_mock()
            
            # Invoke tool
            await tools[tool_name].invoke(question=question)
            
            # Verify correct collection was used
            graph_rag_client = mock_flow_context("graph-rag-request")
            graph_rag_client.rag.assert_called_once_with(question, collection=expected_collection)