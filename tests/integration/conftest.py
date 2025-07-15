"""
Shared fixtures and configuration for integration tests

This file provides common fixtures and test configuration for integration tests.
Following the TEST_STRATEGY.md patterns for integration testing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_pulsar_client():
    """Mock Pulsar client for integration tests"""
    client = MagicMock()
    client.create_producer.return_value = AsyncMock()
    client.subscribe.return_value = AsyncMock()
    return client


@pytest.fixture
def mock_flow_context():
    """Mock flow context for testing service coordination"""
    context = MagicMock()
    
    # Mock flow producers/consumers
    context.return_value.send = AsyncMock()
    context.return_value.receive = AsyncMock()
    
    return context


@pytest.fixture
def integration_config():
    """Common configuration for integration tests"""
    return {
        "pulsar_host": "localhost",
        "pulsar_port": 6650,
        "test_timeout": 30.0,
        "max_retries": 3,
        "doc_limit": 10,
        "embedding_dim": 5,
    }


@pytest.fixture
def sample_documents():
    """Sample document collection for testing"""
    return [
        {
            "id": "doc1",
            "content": "Machine learning is a subset of artificial intelligence that focuses on algorithms that learn from data.",
            "collection": "ml_knowledge",
            "user": "test_user"
        },
        {
            "id": "doc2", 
            "content": "Deep learning uses neural networks with multiple layers to model complex patterns in data.",
            "collection": "ml_knowledge",
            "user": "test_user"
        },
        {
            "id": "doc3",
            "content": "Supervised learning algorithms learn from labeled training data to make predictions on new data.",
            "collection": "ml_knowledge", 
            "user": "test_user"
        }
    ]


@pytest.fixture
def sample_embeddings():
    """Sample embedding vectors for testing"""
    return [
        [0.1, 0.2, 0.3, 0.4, 0.5],
        [0.6, 0.7, 0.8, 0.9, 1.0],
        [0.2, 0.3, 0.4, 0.5, 0.6],
        [0.7, 0.8, 0.9, 1.0, 0.1],
        [0.3, 0.4, 0.5, 0.6, 0.7]
    ]


@pytest.fixture
def sample_queries():
    """Sample queries for testing"""
    return [
        "What is machine learning?",
        "How does deep learning work?",
        "Explain supervised learning",
        "What are neural networks?",
        "How do algorithms learn from data?"
    ]


@pytest.fixture
def sample_text_completion_requests():
    """Sample text completion requests for testing"""
    return [
        {
            "system": "You are a helpful assistant.",
            "prompt": "What is artificial intelligence?",
            "expected_keywords": ["artificial intelligence", "AI", "machine learning"]
        },
        {
            "system": "You are a technical expert.",
            "prompt": "Explain neural networks",
            "expected_keywords": ["neural networks", "neurons", "layers"]
        },
        {
            "system": "You are a teacher.",
            "prompt": "What is supervised learning?",
            "expected_keywords": ["supervised learning", "training", "labels"]
        }
    ]


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response structure"""
    return {
        "id": "chatcmpl-test123",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-3.5-turbo",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is a test response from the AI model."
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 100,
            "total_tokens": 150
        }
    }


@pytest.fixture
def text_completion_configs():
    """Various text completion configurations for testing"""
    return [
        {
            "model": "gpt-3.5-turbo",
            "temperature": 0.0,
            "max_output": 1024,
            "description": "Conservative settings"
        },
        {
            "model": "gpt-4",
            "temperature": 0.7,
            "max_output": 2048,
            "description": "Balanced settings"
        },
        {
            "model": "gpt-4-turbo",
            "temperature": 1.0,
            "max_output": 4096,
            "description": "Creative settings"
        }
    ]


@pytest.fixture
def sample_agent_tools():
    """Sample agent tools configuration for testing"""
    return {
        "knowledge_query": {
            "name": "knowledge_query",
            "description": "Query the knowledge graph for information",
            "type": "knowledge-query",
            "arguments": [
                {
                    "name": "question",
                    "type": "string",
                    "description": "The question to ask the knowledge graph"
                }
            ]
        },
        "text_completion": {
            "name": "text_completion", 
            "description": "Generate text completion using LLM",
            "type": "text-completion",
            "arguments": [
                {
                    "name": "question",
                    "type": "string",
                    "description": "The question to ask the LLM"
                }
            ]
        },
        "web_search": {
            "name": "web_search",
            "description": "Search the web for information",
            "type": "mcp-tool",
            "arguments": [
                {
                    "name": "query",
                    "type": "string",
                    "description": "The search query"
                }
            ]
        }
    }


@pytest.fixture
def sample_agent_requests():
    """Sample agent requests for testing"""
    return [
        {
            "question": "What is machine learning?",
            "plan": "",
            "state": "",
            "history": [],
            "expected_tool": "knowledge_query"
        },
        {
            "question": "Can you explain neural networks in simple terms?",
            "plan": "",
            "state": "",
            "history": [],
            "expected_tool": "text_completion"
        },
        {
            "question": "Search for the latest AI research papers",
            "plan": "",
            "state": "",
            "history": [],
            "expected_tool": "web_search"
        }
    ]


@pytest.fixture
def sample_agent_responses():
    """Sample agent responses for testing"""
    return [
        {
            "thought": "I need to search for information about machine learning",
            "action": "knowledge_query",
            "arguments": {"question": "What is machine learning?"}
        },
        {
            "thought": "I can provide a direct answer about neural networks",
            "final-answer": "Neural networks are computing systems inspired by biological neural networks."
        },
        {
            "thought": "I should search the web for recent research",
            "action": "web_search",
            "arguments": {"query": "latest AI research papers 2024"}
        }
    ]


@pytest.fixture
def sample_conversation_history():
    """Sample conversation history for testing"""
    return [
        {
            "thought": "I need to search for basic information first",
            "action": "knowledge_query",
            "arguments": {"question": "What is artificial intelligence?"},
            "observation": "AI is the simulation of human intelligence in machines."
        },
        {
            "thought": "Now I can provide more specific information",
            "action": "text_completion",
            "arguments": {"question": "Explain machine learning within AI"},
            "observation": "Machine learning is a subset of AI that enables computers to learn from data."
        }
    ]


@pytest.fixture
def sample_kg_extraction_data():
    """Sample knowledge graph extraction data for testing"""
    return {
        "text_chunks": [
            "Machine Learning is a subset of Artificial Intelligence that enables computers to learn from data.",
            "Neural Networks are computing systems inspired by biological neural networks.",
            "Deep Learning uses neural networks with multiple layers to model complex patterns."
        ],
        "expected_entities": [
            "Machine Learning",
            "Artificial Intelligence", 
            "Neural Networks",
            "Deep Learning"
        ],
        "expected_relationships": [
            {
                "subject": "Machine Learning",
                "predicate": "is_subset_of",
                "object": "Artificial Intelligence"
            },
            {
                "subject": "Deep Learning",
                "predicate": "uses",
                "object": "Neural Networks"
            }
        ]
    }


@pytest.fixture
def sample_kg_definitions():
    """Sample knowledge graph definitions for testing"""
    return [
        {
            "entity": "Machine Learning",
            "definition": "A subset of artificial intelligence that enables computers to learn from data without explicit programming."
        },
        {
            "entity": "Artificial Intelligence",
            "definition": "The simulation of human intelligence in machines that are programmed to think and act like humans."
        },
        {
            "entity": "Neural Networks",
            "definition": "Computing systems inspired by biological neural networks that process information using interconnected nodes."
        },
        {
            "entity": "Deep Learning",
            "definition": "A subset of machine learning that uses neural networks with multiple layers to model complex patterns in data."
        }
    ]


@pytest.fixture
def sample_kg_relationships():
    """Sample knowledge graph relationships for testing"""
    return [
        {
            "subject": "Machine Learning",
            "predicate": "is_subset_of",
            "object": "Artificial Intelligence",
            "object-entity": True
        },
        {
            "subject": "Deep Learning",
            "predicate": "is_subset_of",
            "object": "Machine Learning",
            "object-entity": True
        },
        {
            "subject": "Neural Networks",
            "predicate": "is_used_in",
            "object": "Deep Learning",
            "object-entity": True
        },
        {
            "subject": "Machine Learning",
            "predicate": "processes",
            "object": "data patterns",
            "object-entity": False
        }
    ]


@pytest.fixture
def sample_kg_triples():
    """Sample knowledge graph triples for testing"""
    return [
        {
            "subject": "http://trustgraph.ai/e/machine-learning",
            "predicate": "http://www.w3.org/2000/01/rdf-schema#label",
            "object": "Machine Learning"
        },
        {
            "subject": "http://trustgraph.ai/e/machine-learning",
            "predicate": "http://trustgraph.ai/definition",
            "object": "A subset of artificial intelligence that enables computers to learn from data."
        },
        {
            "subject": "http://trustgraph.ai/e/machine-learning",
            "predicate": "http://trustgraph.ai/e/is_subset_of",
            "object": "http://trustgraph.ai/e/artificial-intelligence"
        }
    ]


# Test markers for integration tests
pytestmark = pytest.mark.integration


def pytest_sessionfinish(session, exitstatus):
    """
    Called after whole test run finished, right before returning the exit status.
    
    This hook is used to ensure Cassandra driver threads have time to shut down
    properly before pytest exits, preventing "cannot schedule new futures after
    shutdown" errors.
    """
    import time
    import gc
    
    # Force garbage collection to clean up any remaining objects
    gc.collect()
    
    # Give Cassandra driver threads more time to clean up
    time.sleep(2)