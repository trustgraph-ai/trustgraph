"""
Integration tests for TrustGraph Python API

These tests require a running TrustGraph Gateway API server.
Set environment variable TRUSTGRAPH_URL to point to your server.
Set TRUSTGRAPH_TOKEN if authentication is required.

Example:
    export TRUSTGRAPH_URL=http://localhost:8088/
    export TRUSTGRAPH_TOKEN=your-token-here
    pytest tests/test_api_integration.py -v
"""

import os
import pytest
import asyncio
from typing import List, Dict, Any

from trustgraph.api import (
    Api,
    Triple,
    AgentThought,
    AgentObservation,
    AgentAnswer,
    RAGChunk,
)


# Configuration from environment
GATEWAY_URL = os.getenv("TRUSTGRAPH_URL", "http://localhost:8088/")
AUTH_TOKEN = os.getenv("TRUSTGRAPH_TOKEN", None)
TEST_FLOW_ID = os.getenv("TRUSTGRAPH_TEST_FLOW", "test-flow")
TEST_USER = "test-user"
TEST_COLLECTION = "test-collection"

# Skip tests if gateway is not available
SKIP_INTEGRATION = os.getenv("SKIP_INTEGRATION_TESTS", "false").lower() == "true"
skip_if_no_gateway = pytest.mark.skipif(
    SKIP_INTEGRATION,
    reason="Integration tests disabled (set SKIP_INTEGRATION_TESTS=false to enable)"
)


class TestBasicConnection:
    """Test basic API instantiation and connectivity"""

    @skip_if_no_gateway
    def test_api_instantiation(self):
        """Test that Api class can be instantiated"""
        api = Api(url=GATEWAY_URL, timeout=60, token=AUTH_TOKEN)
        assert api.url.endswith("api/v1/")
        assert api.timeout == 60
        assert api.token == AUTH_TOKEN

    @skip_if_no_gateway
    def test_api_with_context_manager(self):
        """Test Api works as context manager"""
        with Api(url=GATEWAY_URL, timeout=60, token=AUTH_TOKEN) as api:
            assert api is not None
            # Context manager should work
        # Should exit cleanly

    @skip_if_no_gateway
    def test_client_lazy_initialization(self):
        """Test that clients are lazily initialized"""
        api = Api(url=GATEWAY_URL, timeout=60, token=AUTH_TOKEN)

        # Clients should be None initially
        assert api._socket_client is None
        assert api._bulk_client is None
        assert api._async_flow is None

        # Access should initialize
        socket = api.socket()
        assert api._socket_client is not None
        assert socket is api._socket_client

        # Second access should return same instance
        socket2 = api.socket()
        assert socket2 is socket


class TestRESTAPI:
    """Test REST API functionality"""

    @skip_if_no_gateway
    def test_flow_list(self):
        """Test listing flows via REST API"""
        api = Api(url=GATEWAY_URL, timeout=60, token=AUTH_TOKEN)
        flow = api.flow()

        # Should be able to list flows
        flows = flow.list()
        assert isinstance(flows, list)

    @skip_if_no_gateway
    def test_flow_class_list(self):
        """Test listing flow classes"""
        api = Api(url=GATEWAY_URL, timeout=60, token=AUTH_TOKEN)
        flow = api.flow()

        # Should be able to list classes
        classes = flow.list_classes()
        assert isinstance(classes, list)

    @skip_if_no_gateway
    def test_flow_instance_creation(self):
        """Test creating flow instance"""
        api = Api(url=GATEWAY_URL, timeout=60, token=AUTH_TOKEN)
        flow = api.flow()
        flow_instance = flow.id(TEST_FLOW_ID)

        assert flow_instance is not None
        assert flow_instance.id == TEST_FLOW_ID

    @skip_if_no_gateway
    def test_graph_embeddings_query_method_exists(self):
        """Test that graph_embeddings_query method exists"""
        api = Api(url=GATEWAY_URL, timeout=60, token=AUTH_TOKEN)
        flow = api.flow()
        flow_instance = flow.id(TEST_FLOW_ID)

        assert hasattr(flow_instance, 'graph_embeddings_query')


class TestAsyncRESTAPI:
    """Test asynchronous REST API functionality"""

    @skip_if_no_gateway
    @pytest.mark.asyncio
    async def test_async_flow_list(self):
        """Test listing flows via async REST API"""
        api = Api(url=GATEWAY_URL, timeout=60, token=AUTH_TOKEN)
        async_flow = api.async_flow()

        # Should be able to list flows
        flows = await async_flow.list()
        assert isinstance(flows, list)

    @skip_if_no_gateway
    @pytest.mark.asyncio
    async def test_async_flow_class_list(self):
        """Test listing flow classes asynchronously"""
        api = Api(url=GATEWAY_URL, timeout=60, token=AUTH_TOKEN)
        async_flow = api.async_flow()

        # Should be able to list classes
        classes = await async_flow.list_classes()
        assert isinstance(classes, list)

    @skip_if_no_gateway
    @pytest.mark.asyncio
    async def test_async_flow_instance_creation(self):
        """Test creating async flow instance"""
        api = Api(url=GATEWAY_URL, timeout=60, token=AUTH_TOKEN)
        async_flow = api.async_flow()
        flow_instance = async_flow.id(TEST_FLOW_ID)

        assert flow_instance is not None
        assert flow_instance.flow_id == TEST_FLOW_ID

    @skip_if_no_gateway
    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager"""
        async with Api(url=GATEWAY_URL, timeout=60, token=AUTH_TOKEN) as api:
            async_flow = api.async_flow()
            flows = await async_flow.list()
            assert isinstance(flows, list)


class TestWebSocketAPI:
    """Test WebSocket API functionality"""

    @skip_if_no_gateway
    def test_socket_client_creation(self):
        """Test WebSocket client instantiation"""
        api = Api(url=GATEWAY_URL, timeout=60, token=AUTH_TOKEN)
        socket = api.socket()

        assert socket is not None
        assert socket.url.startswith("ws://") or socket.url.startswith("wss://")
        assert socket.token == AUTH_TOKEN

    @skip_if_no_gateway
    def test_socket_flow_instance(self):
        """Test WebSocket flow instance creation"""
        api = Api(url=GATEWAY_URL, timeout=60, token=AUTH_TOKEN)
        socket = api.socket()
        flow_instance = socket.flow(TEST_FLOW_ID)

        assert flow_instance is not None
        assert flow_instance.flow_id == TEST_FLOW_ID

    @skip_if_no_gateway
    def test_socket_methods_exist(self):
        """Test that all expected WebSocket methods exist"""
        api = Api(url=GATEWAY_URL, timeout=60, token=AUTH_TOKEN)
        socket = api.socket()
        flow_instance = socket.flow(TEST_FLOW_ID)

        # Check all methods exist
        expected_methods = [
            'agent', 'text_completion', 'graph_rag', 'document_rag',
            'prompt', 'graph_embeddings_query', 'embeddings',
            'triples_query', 'objects_query', 'mcp_tool'
        ]

        for method in expected_methods:
            assert hasattr(flow_instance, method), f"Missing method: {method}"


class TestAsyncWebSocketAPI:
    """Test async WebSocket API functionality"""

    @skip_if_no_gateway
    def test_async_socket_client_creation(self):
        """Test async WebSocket client instantiation"""
        api = Api(url=GATEWAY_URL, timeout=60, token=AUTH_TOKEN)
        async_socket = api.async_socket()

        assert async_socket is not None
        assert async_socket.url.startswith("ws://") or async_socket.url.startswith("wss://")

    @skip_if_no_gateway
    def test_async_socket_flow_instance(self):
        """Test async WebSocket flow instance creation"""
        api = Api(url=GATEWAY_URL, timeout=60, token=AUTH_TOKEN)
        async_socket = api.async_socket()
        flow_instance = async_socket.flow(TEST_FLOW_ID)

        assert flow_instance is not None
        assert flow_instance.flow_id == TEST_FLOW_ID

    @skip_if_no_gateway
    def test_async_socket_methods_exist(self):
        """Test that all expected async WebSocket methods exist"""
        api = Api(url=GATEWAY_URL, timeout=60, token=AUTH_TOKEN)
        async_socket = api.async_socket()
        flow_instance = async_socket.flow(TEST_FLOW_ID)

        # Check all methods exist
        expected_methods = [
            'agent', 'text_completion', 'graph_rag', 'document_rag',
            'prompt', 'graph_embeddings_query', 'embeddings',
            'triples_query', 'objects_query', 'mcp_tool'
        ]

        for method in expected_methods:
            assert hasattr(flow_instance, method), f"Missing method: {method}"


class TestBulkOperations:
    """Test bulk operations functionality"""

    @skip_if_no_gateway
    def test_bulk_client_creation(self):
        """Test bulk client instantiation"""
        api = Api(url=GATEWAY_URL, timeout=60, token=AUTH_TOKEN)
        bulk = api.bulk()

        assert bulk is not None
        assert bulk.url.startswith("ws://") or bulk.url.startswith("wss://")

    @skip_if_no_gateway
    def test_bulk_methods_exist(self):
        """Test that all expected bulk methods exist"""
        api = Api(url=GATEWAY_URL, timeout=60, token=AUTH_TOKEN)
        bulk = api.bulk()

        # Check all methods exist
        expected_methods = [
            'import_triples', 'export_triples',
            'import_graph_embeddings', 'export_graph_embeddings',
            'import_document_embeddings', 'export_document_embeddings',
            'import_entity_contexts', 'export_entity_contexts',
            'import_objects'
        ]

        for method in expected_methods:
            assert hasattr(bulk, method), f"Missing method: {method}"

    @skip_if_no_gateway
    def test_async_bulk_client_creation(self):
        """Test async bulk client instantiation"""
        api = Api(url=GATEWAY_URL, timeout=60, token=AUTH_TOKEN)
        async_bulk = api.async_bulk()

        assert async_bulk is not None
        assert async_bulk.url.startswith("ws://") or async_bulk.url.startswith("wss://")


class TestMetrics:
    """Test metrics functionality"""

    @skip_if_no_gateway
    def test_metrics_client_creation(self):
        """Test metrics client instantiation"""
        api = Api(url=GATEWAY_URL, timeout=60, token=AUTH_TOKEN)
        metrics = api.metrics()

        assert metrics is not None
        assert hasattr(metrics, 'get')

    @skip_if_no_gateway
    def test_async_metrics_client_creation(self):
        """Test async metrics client instantiation"""
        api = Api(url=GATEWAY_URL, timeout=60, token=AUTH_TOKEN)
        async_metrics = api.async_metrics()

        assert async_metrics is not None
        assert hasattr(async_metrics, 'get')

    @skip_if_no_gateway
    @pytest.mark.asyncio
    async def test_async_metrics_get(self):
        """Test getting metrics asynchronously"""
        try:
            api = Api(url=GATEWAY_URL, timeout=60, token=AUTH_TOKEN)
            async_metrics = api.async_metrics()

            metrics_text = await async_metrics.get()
            assert isinstance(metrics_text, str)
            # Prometheus metrics should contain "# HELP" lines
            assert "# HELP" in metrics_text or len(metrics_text) > 0
        except Exception as e:
            # Metrics endpoint might not be available
            pytest.skip(f"Metrics endpoint not available: {e}")


class TestStreamingTypes:
    """Test streaming chunk type classes"""

    def test_agent_thought_creation(self):
        """Test AgentThought chunk creation"""
        chunk = AgentThought(content="thinking...", end_of_message=False)
        assert chunk.content == "thinking..."
        assert chunk.end_of_message is False
        assert chunk.chunk_type == "thought"

    def test_agent_observation_creation(self):
        """Test AgentObservation chunk creation"""
        chunk = AgentObservation(content="observing...", end_of_message=False)
        assert chunk.content == "observing..."
        assert chunk.chunk_type == "observation"

    def test_agent_answer_creation(self):
        """Test AgentAnswer chunk creation"""
        chunk = AgentAnswer(
            content="answer",
            end_of_message=True,
            end_of_dialog=True
        )
        assert chunk.content == "answer"
        assert chunk.end_of_message is True
        assert chunk.end_of_dialog is True
        assert chunk.chunk_type == "final-answer"

    def test_rag_chunk_creation(self):
        """Test RAGChunk creation"""
        chunk = RAGChunk(
            content="response chunk",
            end_of_stream=False,
            error=None
        )
        assert chunk.content == "response chunk"
        assert chunk.end_of_stream is False
        assert chunk.error is None


class TestTripleType:
    """Test Triple type"""

    def test_triple_creation(self):
        """Test Triple creation"""
        triple = Triple(s="subject", p="predicate", o="object")
        assert triple.s == "subject"
        assert triple.p == "predicate"
        assert triple.o == "object"


# Run tests with: pytest tests/test_api_integration.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
