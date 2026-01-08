"""
Unit tests for TrustGraph Python API client library

These tests use mocks and do not require a running server.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import json

from trustgraph.api import (
    Api,
    Triple,
    AgentThought,
    AgentObservation,
    AgentAnswer,
    RAGChunk,
)


class TestApiInstantiation:
    """Test Api class instantiation and configuration"""

    def test_api_instantiation_defaults(self):
        """Test Api with default parameters"""
        api = Api()
        assert api.url == "http://localhost:8088/api/v1/"
        assert api.timeout == 60
        assert api.token is None

    def test_api_instantiation_with_url(self):
        """Test Api with custom URL"""
        api = Api(url="http://test-server:9000/")
        assert api.url == "http://test-server:9000/api/v1/"

    def test_api_instantiation_with_url_trailing_slash(self):
        """Test Api adds trailing slash if missing"""
        api = Api(url="http://test-server:9000")
        assert api.url == "http://test-server:9000/api/v1/"

    def test_api_instantiation_with_token(self):
        """Test Api with authentication token"""
        api = Api(token="test-token-123")
        assert api.token == "test-token-123"

    def test_api_instantiation_with_timeout(self):
        """Test Api with custom timeout"""
        api = Api(timeout=120)
        assert api.timeout == 120


class TestApiLazyInitialization:
    """Test lazy initialization of client components"""

    def test_socket_client_lazy_init(self):
        """Test socket client is created on first access"""
        api = Api(url="http://test/", token="token")

        assert api._socket_client is None
        socket = api.socket()
        assert api._socket_client is not None
        assert socket is api._socket_client

        # Second access returns same instance
        socket2 = api.socket()
        assert socket2 is socket

    def test_bulk_client_lazy_init(self):
        """Test bulk client is created on first access"""
        api = Api(url="http://test/")

        assert api._bulk_client is None
        bulk = api.bulk()
        assert api._bulk_client is not None

    def test_async_flow_lazy_init(self):
        """Test async flow is created on first access"""
        api = Api(url="http://test/")

        assert api._async_flow is None
        async_flow = api.async_flow()
        assert api._async_flow is not None

    def test_metrics_lazy_init(self):
        """Test metrics client is created on first access"""
        api = Api(url="http://test/")

        assert api._metrics is None
        metrics = api.metrics()
        assert api._metrics is not None


class TestApiContextManager:
    """Test context manager functionality"""

    def test_sync_context_manager(self):
        """Test synchronous context manager"""
        with Api(url="http://test/") as api:
            assert api is not None
            assert isinstance(api, Api)
        # Should exit cleanly

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test asynchronous context manager"""
        async with Api(url="http://test/") as api:
            assert api is not None
            assert isinstance(api, Api)
        # Should exit cleanly


class TestFlowClient:
    """Test Flow client functionality"""

    @patch('requests.post')
    def test_flow_list(self, mock_post):
        """Test listing flows"""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"flow-ids": ["flow1", "flow2"]}

        api = Api(url="http://test/")
        flows = api.flow().list()

        assert flows == ["flow1", "flow2"]
        assert mock_post.called

    @patch('requests.post')
    def test_flow_list_with_token(self, mock_post):
        """Test flow listing includes auth token"""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"flow-ids": []}

        api = Api(url="http://test/", token="my-token")
        api.flow().list()

        # Verify Authorization header was set
        call_args = mock_post.call_args
        headers = call_args[1]['headers'] if 'headers' in call_args[1] else {}
        assert 'Authorization' in headers
        assert headers['Authorization'] == 'Bearer my-token'

    @patch('requests.post')
    def test_flow_get(self, mock_post):
        """Test getting flow definition"""
        flow_def = {"name": "test-flow", "description": "Test"}
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"flow": json.dumps(flow_def)}

        api = Api(url="http://test/")
        result = api.flow().get("test-flow")

        assert result == flow_def

    def test_flow_instance_creation(self):
        """Test creating flow instance"""
        api = Api(url="http://test/")
        flow_instance = api.flow().id("my-flow")

        assert flow_instance is not None
        assert flow_instance.id == "my-flow"

    def test_flow_instance_has_methods(self):
        """Test flow instance has expected methods"""
        api = Api(url="http://test/")
        flow_instance = api.flow().id("my-flow")

        expected_methods = [
            'text_completion', 'agent', 'graph_rag', 'document_rag',
            'graph_embeddings_query', 'embeddings', 'prompt',
            'triples_query', 'objects_query'
        ]

        for method in expected_methods:
            assert hasattr(flow_instance, method), f"Missing method: {method}"


class TestSocketClient:
    """Test WebSocket client functionality"""

    def test_socket_client_url_conversion_http(self):
        """Test HTTP URL converted to WebSocket"""
        api = Api(url="http://test-server:8088/")
        socket = api.socket()

        assert socket.url.startswith("ws://")
        assert "test-server" in socket.url

    def test_socket_client_url_conversion_https(self):
        """Test HTTPS URL converted to secure WebSocket"""
        api = Api(url="https://test-server:8088/")
        socket = api.socket()

        assert socket.url.startswith("wss://")

    def test_socket_client_token_passed(self):
        """Test token is passed to socket client"""
        api = Api(url="http://test/", token="socket-token")
        socket = api.socket()

        assert socket.token == "socket-token"

    def test_socket_flow_instance(self):
        """Test creating socket flow instance"""
        api = Api(url="http://test/")
        socket = api.socket()
        flow_instance = socket.flow("test-flow")

        assert flow_instance is not None
        assert flow_instance.flow_id == "test-flow"

    def test_socket_flow_has_methods(self):
        """Test socket flow instance has expected methods"""
        api = Api(url="http://test/")
        flow_instance = api.socket().flow("test-flow")

        expected_methods = [
            'agent', 'text_completion', 'graph_rag', 'document_rag',
            'prompt', 'graph_embeddings_query', 'embeddings',
            'triples_query', 'objects_query', 'mcp_tool'
        ]

        for method in expected_methods:
            assert hasattr(flow_instance, method), f"Missing method: {method}"


class TestBulkClient:
    """Test bulk operations client"""

    def test_bulk_client_url_conversion(self):
        """Test bulk client uses WebSocket URL"""
        api = Api(url="http://test/")
        bulk = api.bulk()

        assert bulk.url.startswith("ws://")

    def test_bulk_client_has_import_methods(self):
        """Test bulk client has import methods"""
        api = Api(url="http://test/")
        bulk = api.bulk()

        import_methods = [
            'import_triples',
            'import_graph_embeddings',
            'import_document_embeddings',
            'import_entity_contexts',
            'import_objects'
        ]

        for method in import_methods:
            assert hasattr(bulk, method), f"Missing method: {method}"

    def test_bulk_client_has_export_methods(self):
        """Test bulk client has export methods"""
        api = Api(url="http://test/")
        bulk = api.bulk()

        export_methods = [
            'export_triples',
            'export_graph_embeddings',
            'export_document_embeddings',
            'export_entity_contexts'
        ]

        for method in export_methods:
            assert hasattr(bulk, method), f"Missing method: {method}"


class TestMetricsClient:
    """Test metrics client"""

    @patch('requests.get')
    def test_metrics_get(self, mock_get):
        """Test getting metrics"""
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "# HELP metric_name\nmetric_name 42"

        api = Api(url="http://test/")
        metrics_text = api.metrics().get()

        assert "metric_name" in metrics_text
        assert mock_get.called

    @patch('requests.get')
    def test_metrics_with_token(self, mock_get):
        """Test metrics request includes token"""
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "metrics"

        api = Api(url="http://test/", token="metrics-token")
        api.metrics().get()

        # Verify token in headers
        call_args = mock_get.call_args
        headers = call_args[1].get('headers', {})
        assert 'Authorization' in headers


class TestStreamingTypes:
    """Test streaming chunk types"""

    def test_agent_thought_creation(self):
        """Test creating AgentThought chunk"""
        chunk = AgentThought(content="thinking...", end_of_message=False)

        assert chunk.content == "thinking..."
        assert chunk.end_of_message is False
        assert chunk.chunk_type == "thought"

    def test_agent_observation_creation(self):
        """Test creating AgentObservation chunk"""
        chunk = AgentObservation(content="observing...", end_of_message=False)

        assert chunk.content == "observing..."
        assert chunk.chunk_type == "observation"

    def test_agent_answer_creation(self):
        """Test creating AgentAnswer chunk"""
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
        """Test creating RAGChunk"""
        chunk = RAGChunk(
            content="response chunk",
            end_of_stream=False,
            error=None
        )

        assert chunk.content == "response chunk"
        assert chunk.end_of_stream is False
        assert chunk.error is None

    def test_rag_chunk_with_error(self):
        """Test RAGChunk with error"""
        error_dict = {"type": "error", "message": "failed"}
        chunk = RAGChunk(
            content="",
            end_of_stream=True,
            error=error_dict
        )

        assert chunk.error == error_dict


class TestTripleType:
    """Test Triple data structure"""

    def test_triple_creation(self):
        """Test creating Triple"""
        triple = Triple(s="subject", p="predicate", o="object")

        assert triple.s == "subject"
        assert triple.p == "predicate"
        assert triple.o == "object"

    def test_triple_with_uris(self):
        """Test Triple with URI values"""
        triple = Triple(
            s="http://example.org/entity1",
            p="http://example.org/relation",
            o="http://example.org/entity2"
        )

        assert triple.s.startswith("http://")
        assert triple.p.startswith("http://")
        assert triple.o.startswith("http://")


class TestAsyncClients:
    """Test async client availability"""

    def test_async_flow_creation(self):
        """Test creating async flow client"""
        api = Api(url="http://test/")
        async_flow = api.async_flow()

        assert async_flow is not None

    def test_async_socket_creation(self):
        """Test creating async socket client"""
        api = Api(url="http://test/")
        async_socket = api.async_socket()

        assert async_socket is not None
        assert async_socket.url.startswith("ws://")

    def test_async_bulk_creation(self):
        """Test creating async bulk client"""
        api = Api(url="http://test/")
        async_bulk = api.async_bulk()

        assert async_bulk is not None

    def test_async_metrics_creation(self):
        """Test creating async metrics client"""
        api = Api(url="http://test/")
        async_metrics = api.async_metrics()

        assert async_metrics is not None


class TestErrorHandling:
    """Test error handling"""

    @patch('requests.post')
    def test_protocol_exception_on_non_200(self, mock_post):
        """Test ProtocolException raised on non-200 status"""
        from trustgraph.api.exceptions import ProtocolException

        mock_post.return_value.status_code = 500

        api = Api(url="http://test/")

        with pytest.raises(ProtocolException):
            api.flow().list()

    @patch('requests.post')
    def test_application_exception_on_error_response(self, mock_post):
        """Test ApplicationException on error in response"""
        from trustgraph.api.exceptions import ApplicationException

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "error": {
                "type": "ValidationError",
                "message": "Invalid input"
            }
        }

        api = Api(url="http://test/")

        with pytest.raises(ApplicationException):
            api.flow().list()


# Run tests with: pytest tests/unit/test_python_api_client.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
