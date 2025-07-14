"""
Contract test fixtures and configuration

This file provides common fixtures for contract testing, focusing on
message schema validation, API interface contracts, and service compatibility.
"""

import pytest
import json
from typing import Dict, Any, Type
from pulsar.schema import Record
from unittest.mock import MagicMock

from trustgraph.schema import (
    TextCompletionRequest, TextCompletionResponse,
    DocumentRagQuery, DocumentRagResponse,
    AgentRequest, AgentResponse, AgentStep,
    Chunk, Triple, Triples, Value, Error,
    EntityContext, EntityContexts,
    GraphEmbeddings, EntityEmbeddings,
    Metadata
)


@pytest.fixture
def schema_registry():
    """Registry of all Pulsar schemas used in TrustGraph"""
    return {
        # Text Completion
        "TextCompletionRequest": TextCompletionRequest,
        "TextCompletionResponse": TextCompletionResponse,
        
        # Document RAG
        "DocumentRagQuery": DocumentRagQuery,
        "DocumentRagResponse": DocumentRagResponse,
        
        # Agent
        "AgentRequest": AgentRequest,
        "AgentResponse": AgentResponse,
        "AgentStep": AgentStep,
        
        # Graph
        "Chunk": Chunk,
        "Triple": Triple,
        "Triples": Triples,
        "Value": Value,
        "Error": Error,
        "EntityContext": EntityContext,
        "EntityContexts": EntityContexts,
        "GraphEmbeddings": GraphEmbeddings,
        "EntityEmbeddings": EntityEmbeddings,
        
        # Common
        "Metadata": Metadata,
    }


@pytest.fixture
def sample_message_data():
    """Sample message data for contract testing"""
    return {
        "TextCompletionRequest": {
            "system": "You are a helpful assistant.",
            "prompt": "What is machine learning?"
        },
        "TextCompletionResponse": {
            "error": None,
            "response": "Machine learning is a subset of artificial intelligence.",
            "in_token": 50,
            "out_token": 100,
            "model": "gpt-3.5-turbo"
        },
        "DocumentRagQuery": {
            "query": "What is artificial intelligence?",
            "user": "test_user",
            "collection": "test_collection",
            "doc_limit": 10
        },
        "DocumentRagResponse": {
            "error": None,
            "response": "Artificial intelligence is the simulation of human intelligence in machines."
        },
        "AgentRequest": {
            "question": "What is machine learning?",
            "plan": "",
            "state": "",
            "history": []
        },
        "AgentResponse": {
            "answer": "Machine learning is a subset of AI.",
            "error": None,
            "thought": "I need to provide information about machine learning.",
            "observation": None
        },
        "Metadata": {
            "id": "test-doc-123",
            "user": "test_user",
            "collection": "test_collection",
            "metadata": []
        },
        "Value": {
            "value": "http://example.com/entity",
            "is_uri": True,
            "type": ""
        },
        "Triple": {
            "s": Value(
                value="http://example.com/subject",
                is_uri=True,
                type=""
            ),
            "p": Value(
                value="http://example.com/predicate", 
                is_uri=True,
                type=""
            ),
            "o": Value(
                value="Object value",
                is_uri=False,
                type=""
            )
        }
    }


@pytest.fixture
def invalid_message_data():
    """Invalid message data for contract validation testing"""
    return {
        "TextCompletionRequest": [
            {"system": None, "prompt": "test"},  # Invalid system (None)
            {"system": "test", "prompt": None},  # Invalid prompt (None)
            {"system": 123, "prompt": "test"},   # Invalid system (not string)
            {},  # Missing required fields
        ],
        "DocumentRagQuery": [
            {"query": None, "user": "test", "collection": "test", "doc_limit": 10},  # Invalid query
            {"query": "test", "user": None, "collection": "test", "doc_limit": 10},  # Invalid user
            {"query": "test", "user": "test", "collection": "test", "doc_limit": -1},  # Invalid doc_limit
            {"query": "test"},  # Missing required fields
        ],
        "Value": [
            {"value": None, "is_uri": True, "type": ""},  # Invalid value (None)
            {"value": "test", "is_uri": "not_boolean", "type": ""},  # Invalid is_uri
            {"value": 123, "is_uri": True, "type": ""},  # Invalid value (not string)
        ]
    }


@pytest.fixture
def message_properties():
    """Standard message properties for contract testing"""
    return {
        "id": "test-message-123",
        "routing_key": "test.routing.key",
        "timestamp": "2024-01-01T00:00:00Z",
        "source_service": "test-service",
        "correlation_id": "correlation-123"
    }


@pytest.fixture
def schema_evolution_data():
    """Data for testing schema evolution and backward compatibility"""
    return {
        "TextCompletionRequest_v1": {
            "system": "You are helpful.",
            "prompt": "Test prompt"
        },
        "TextCompletionRequest_v2": {
            "system": "You are helpful.",
            "prompt": "Test prompt",
            "temperature": 0.7,  # New field
            "max_tokens": 100    # New field
        },
        "TextCompletionResponse_v1": {
            "error": None,
            "response": "Test response",
            "model": "gpt-3.5-turbo"
        },
        "TextCompletionResponse_v2": {
            "error": None,
            "response": "Test response",
            "in_token": 50,      # New field
            "out_token": 100,    # New field
            "model": "gpt-3.5-turbo"
        }
    }


def validate_schema_contract(schema_class: Type[Record], data: Dict[str, Any]) -> bool:
    """Helper function to validate schema contracts"""
    try:
        # Create instance from data
        instance = schema_class(**data)
        
        # Verify all fields are accessible
        for field_name in data.keys():
            assert hasattr(instance, field_name)
            assert getattr(instance, field_name) == data[field_name]
        
        return True
    except Exception:
        return False


def serialize_deserialize_test(schema_class: Type[Record], data: Dict[str, Any]) -> bool:
    """Helper function to test serialization/deserialization"""
    try:
        # Create instance
        instance = schema_class(**data)
        
        # This would test actual Pulsar serialization if we had the client
        # For now, we test the schema construction and field access
        for field_name, field_value in data.items():
            assert getattr(instance, field_name) == field_value
        
        return True
    except Exception:
        return False


# Test markers for contract tests
pytestmark = pytest.mark.contract