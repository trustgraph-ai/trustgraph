"""
Shared fixtures for agent unit tests
"""

import pytest
from unittest.mock import Mock, AsyncMock


# Mock agent schema classes for testing
class AgentRequest:
    def __init__(self, question, conversation_id=None):
        self.question = question
        self.conversation_id = conversation_id


class AgentResponse:
    def __init__(self, answer, conversation_id=None, steps=None):
        self.answer = answer
        self.conversation_id = conversation_id
        self.steps = steps or []


class AgentStep:
    def __init__(self, step_type, content, tool_name=None, tool_result=None):
        self.step_type = step_type  # "think", "act", "observe"
        self.content = content
        self.tool_name = tool_name
        self.tool_result = tool_result


@pytest.fixture
def sample_agent_request():
    """Sample agent request for testing"""
    return AgentRequest(
        question="What is the capital of France?",
        conversation_id="conv-123"
    )


@pytest.fixture
def sample_agent_response():
    """Sample agent response for testing"""
    steps = [
        AgentStep("think", "I need to find information about France's capital"),
        AgentStep("act", "search", tool_name="knowledge_search", tool_result="Paris is the capital of France"),
        AgentStep("observe", "I found that Paris is the capital of France"),
        AgentStep("think", "I can now provide a complete answer")
    ]
    
    return AgentResponse(
        answer="The capital of France is Paris.",
        conversation_id="conv-123",
        steps=steps
    )


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for agent reasoning"""
    mock = AsyncMock()
    mock.generate.return_value = "I need to search for information about the capital of France."
    return mock


@pytest.fixture
def mock_knowledge_search_tool():
    """Mock knowledge search tool"""
    def search_tool(query):
        if "capital" in query.lower() and "france" in query.lower():
            return "Paris is the capital and largest city of France."
        return "No relevant information found."
    
    return search_tool


@pytest.fixture
def mock_graph_rag_tool():
    """Mock graph RAG tool"""
    def graph_rag_tool(query):
        return {
            "entities": ["France", "Paris"],
            "relationships": [("Paris", "capital_of", "France")],
            "context": "Paris is the capital city of France, located in northern France."
        }
    
    return graph_rag_tool


@pytest.fixture
def mock_calculator_tool():
    """Mock calculator tool"""
    def calculator_tool(expression):
        # Simple mock calculator
        try:
            # Very basic expression evaluation for testing
            if "+" in expression:
                parts = expression.split("+")
                return str(sum(int(p.strip()) for p in parts))
            elif "*" in expression:
                parts = expression.split("*")
                result = 1
                for p in parts:
                    result *= int(p.strip())
                return str(result)
            return str(eval(expression))  # Simplified for testing
        except:
            return "Error: Invalid expression"
    
    return calculator_tool


@pytest.fixture
def available_tools(mock_knowledge_search_tool, mock_graph_rag_tool, mock_calculator_tool):
    """Available tools for agent testing"""
    return {
        "knowledge_search": {
            "function": mock_knowledge_search_tool,
            "description": "Search knowledge base for information",
            "parameters": ["query"]
        },
        "graph_rag": {
            "function": mock_graph_rag_tool,
            "description": "Query knowledge graph with RAG",
            "parameters": ["query"]
        },
        "calculator": {
            "function": mock_calculator_tool,
            "description": "Perform mathematical calculations",
            "parameters": ["expression"]
        }
    }


@pytest.fixture
def sample_conversation_history():
    """Sample conversation history for multi-turn testing"""
    return [
        {
            "role": "user",
            "content": "What is 2 + 2?",
            "timestamp": "2024-01-01T10:00:00Z"
        },
        {
            "role": "assistant", 
            "content": "2 + 2 = 4",
            "steps": [
                {"step_type": "think", "content": "This is a simple arithmetic question"},
                {"step_type": "act", "content": "calculator", "tool_name": "calculator", "tool_result": "4"},
                {"step_type": "observe", "content": "The calculator returned 4"},
                {"step_type": "think", "content": "I can provide the answer"}
            ],
            "timestamp": "2024-01-01T10:00:05Z"
        },
        {
            "role": "user",
            "content": "What about 3 + 3?",
            "timestamp": "2024-01-01T10:01:00Z"
        }
    ]


@pytest.fixture
def react_prompts():
    """ReAct prompting templates for testing"""
    return {
        "system_prompt": """You are a helpful AI assistant that uses the ReAct (Reasoning and Acting) pattern.

For each question, follow this cycle:
1. Think: Analyze the question and plan your approach
2. Act: Use available tools to gather information 
3. Observe: Review the tool results
4. Repeat if needed, then provide final answer

Available tools: {tools}

Format your response as:
Think: [your reasoning]
Act: [tool_name: parameters]
Observe: [analysis of results]
Answer: [final response]""",

        "think_prompt": "Think step by step about this question: {question}\nPrevious context: {context}",
        
        "act_prompt": "Based on your thinking, what tool should you use? Available tools: {tools}",
        
        "observe_prompt": "You used {tool_name} and got result: {tool_result}\nHow does this help answer the question?",
        
        "synthesize_prompt": "Based on all your steps, provide a complete answer to: {question}"
    }


@pytest.fixture
def mock_agent_processor():
    """Mock agent processor for testing"""
    class MockAgentProcessor:
        def __init__(self, llm_client=None, tools=None):
            self.llm_client = llm_client
            self.tools = tools or {}
            self.conversation_history = {}
        
        async def process_request(self, request):
            # Mock processing logic
            return AgentResponse(
                answer="Mock response",
                conversation_id=request.conversation_id,
                steps=[]
            )
    
    return MockAgentProcessor