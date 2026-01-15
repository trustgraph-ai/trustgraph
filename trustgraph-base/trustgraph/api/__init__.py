"""
TrustGraph API Client Library

This package provides Python client interfaces for interacting with TrustGraph services.
TrustGraph is a knowledge graph and RAG (Retrieval-Augmented Generation) platform that
combines graph databases, vector embeddings, and LLM capabilities.

The library offers both synchronous and asynchronous APIs for:
- Flow management and execution
- Knowledge graph operations (triples, entities, embeddings)
- RAG queries (graph-based and document-based)
- Agent interactions with streaming support
- WebSocket-based real-time communication
- Bulk import/export operations
- Configuration and collection management

Quick Start:
    ```python
    from trustgraph.api import Api

    # Create API client
    api = Api(url="http://localhost:8088/")

    # Get a flow instance
    flow = api.flow().id("default")

    # Execute a graph RAG query
    response = flow.graph_rag(
        query="What are the main topics?",
        user="trustgraph",
        collection="default"
    )
    ```

For streaming and async operations:
    ```python
    # WebSocket streaming
    socket = api.socket()
    flow = socket.flow("default")

    for chunk in flow.agent(question="Hello", user="trustgraph"):
        print(chunk.content)

    # Async operations
    async with Api(url="http://localhost:8088/") as api:
        async_flow = api.async_flow()
        result = await async_flow.id("default").text_completion(
            system="You are helpful",
            prompt="Hello"
        )
    ```
"""

# Core API
from .api import Api

# Flow clients
from .flow import Flow, FlowInstance
from .async_flow import AsyncFlow, AsyncFlowInstance

# WebSocket clients
from .socket_client import SocketClient, SocketFlowInstance
from .async_socket_client import AsyncSocketClient, AsyncSocketFlowInstance

# Bulk operation clients
from .bulk_client import BulkClient
from .async_bulk_client import AsyncBulkClient

# Metrics clients
from .metrics import Metrics
from .async_metrics import AsyncMetrics

# Types
from .types import (
    Triple,
    ConfigKey,
    ConfigValue,
    DocumentMetadata,
    ProcessingMetadata,
    CollectionMetadata,
    StreamingChunk,
    AgentThought,
    AgentObservation,
    AgentAnswer,
    RAGChunk,
)

# Exceptions
from .exceptions import (
    ProtocolException,
    TrustGraphException,
    AgentError,
    ConfigError,
    DocumentRagError,
    FlowError,
    GatewayError,
    GraphRagError,
    LLMError,
    LoadError,
    LookupError,
    NLPQueryError,
    ObjectsQueryError,
    RequestError,
    StructuredQueryError,
    UnexpectedError,
    # Legacy alias
    ApplicationException,
)

__all__ = [
    # Core API
    "Api",

    # Flow clients
    "Flow",
    "FlowInstance",
    "AsyncFlow",
    "AsyncFlowInstance",

    # WebSocket clients
    "SocketClient",
    "SocketFlowInstance",
    "AsyncSocketClient",
    "AsyncSocketFlowInstance",

    # Bulk operation clients
    "BulkClient",
    "AsyncBulkClient",

    # Metrics clients
    "Metrics",
    "AsyncMetrics",

    # Types
    "Triple",
    "ConfigKey",
    "ConfigValue",
    "DocumentMetadata",
    "ProcessingMetadata",
    "CollectionMetadata",
    "StreamingChunk",
    "AgentThought",
    "AgentObservation",
    "AgentAnswer",
    "RAGChunk",

    # Exceptions
    "ProtocolException",
    "TrustGraphException",
    "AgentError",
    "ConfigError",
    "DocumentRagError",
    "FlowError",
    "GatewayError",
    "GraphRagError",
    "LLMError",
    "LoadError",
    "LookupError",
    "NLPQueryError",
    "ObjectsQueryError",
    "RequestError",
    "StructuredQueryError",
    "UnexpectedError",
    "ApplicationException",  # Legacy alias
]

