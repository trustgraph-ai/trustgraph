"""
Tests for Gateway Stream Endpoint
"""

import pytest
from unittest.mock import MagicMock

from trustgraph.gateway.endpoint.stream_endpoint import StreamEndpoint


class TestStreamEndpoint:
    """Test cases for StreamEndpoint class"""

    def test_stream_endpoint_initialization_with_post(self):
        """Test StreamEndpoint initialization with POST method"""
        mock_auth = MagicMock()
        mock_dispatcher = MagicMock()
        
        endpoint = StreamEndpoint(
            endpoint_path="/api/stream",
            auth=mock_auth,
            dispatcher=mock_dispatcher,
            method="POST"
        )
        
        assert endpoint.path == "/api/stream"
        assert endpoint.auth == mock_auth
        assert endpoint.dispatcher == mock_dispatcher
        assert endpoint.operation == "service"
        assert endpoint.method == "POST"

    def test_stream_endpoint_initialization_with_get(self):
        """Test StreamEndpoint initialization with GET method"""
        mock_auth = MagicMock()
        mock_dispatcher = MagicMock()
        
        endpoint = StreamEndpoint(
            endpoint_path="/api/stream",
            auth=mock_auth,
            dispatcher=mock_dispatcher,
            method="GET"
        )
        
        assert endpoint.method == "GET"

    def test_stream_endpoint_initialization_default_method(self):
        """Test StreamEndpoint initialization with default POST method"""
        mock_auth = MagicMock()
        mock_dispatcher = MagicMock()
        
        endpoint = StreamEndpoint(
            endpoint_path="/api/stream",
            auth=mock_auth,
            dispatcher=mock_dispatcher
        )
        
        assert endpoint.method == "POST"  # Default value

    @pytest.mark.asyncio
    async def test_stream_endpoint_start_method(self):
        """Test StreamEndpoint start method (should be no-op)"""
        mock_auth = MagicMock()
        mock_dispatcher = MagicMock()
        
        endpoint = StreamEndpoint("/api/stream", mock_auth, mock_dispatcher)
        
        # start() should complete without error
        await endpoint.start()

    def test_add_routes_with_post_method(self):
        """Test add_routes method with POST method"""
        mock_auth = MagicMock()
        mock_dispatcher = MagicMock()
        mock_app = MagicMock()
        
        endpoint = StreamEndpoint(
            endpoint_path="/api/stream",
            auth=mock_auth,
            dispatcher=mock_dispatcher,
            method="POST"
        )
        
        endpoint.add_routes(mock_app)
        
        # Verify add_routes was called with POST route
        mock_app.add_routes.assert_called_once()
        call_args = mock_app.add_routes.call_args[0][0]
        assert len(call_args) == 1  # One route added

    def test_add_routes_with_get_method(self):
        """Test add_routes method with GET method"""
        mock_auth = MagicMock()
        mock_dispatcher = MagicMock()
        mock_app = MagicMock()
        
        endpoint = StreamEndpoint(
            endpoint_path="/api/stream",
            auth=mock_auth,
            dispatcher=mock_dispatcher,
            method="GET"
        )
        
        endpoint.add_routes(mock_app)
        
        # Verify add_routes was called with GET route
        mock_app.add_routes.assert_called_once()
        call_args = mock_app.add_routes.call_args[0][0]
        assert len(call_args) == 1  # One route added

    def test_add_routes_with_invalid_method_raises_error(self):
        """Test add_routes method with invalid method raises RuntimeError"""
        mock_auth = MagicMock()
        mock_dispatcher = MagicMock()
        mock_app = MagicMock()
        
        endpoint = StreamEndpoint(
            endpoint_path="/api/stream",
            auth=mock_auth,
            dispatcher=mock_dispatcher,
            method="INVALID"
        )
        
        with pytest.raises(RuntimeError, match="Bad method"):
            endpoint.add_routes(mock_app)