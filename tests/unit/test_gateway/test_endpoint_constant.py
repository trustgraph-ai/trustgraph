"""
Tests for Gateway Constant Endpoint
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from aiohttp import web

from trustgraph.gateway.endpoint.constant_endpoint import ConstantEndpoint


class TestConstantEndpoint:
    """Test cases for ConstantEndpoint class"""

    def test_constant_endpoint_initialization(self):
        """Test ConstantEndpoint initialization"""
        mock_auth = MagicMock()
        mock_dispatcher = MagicMock()
        
        endpoint = ConstantEndpoint(
            endpoint_path="/api/test",
            auth=mock_auth,
            dispatcher=mock_dispatcher
        )
        
        assert endpoint.path == "/api/test"
        assert endpoint.auth == mock_auth
        assert endpoint.dispatcher == mock_dispatcher
        assert endpoint.operation == "service"

    @pytest.mark.asyncio
    async def test_constant_endpoint_start_method(self):
        """Test ConstantEndpoint start method (should be no-op)"""
        mock_auth = MagicMock()
        mock_dispatcher = MagicMock()
        
        endpoint = ConstantEndpoint("/api/test", mock_auth, mock_dispatcher)
        
        # start() should complete without error
        await endpoint.start()

    def test_add_routes_registers_post_handler(self):
        """Test add_routes method registers POST route"""
        mock_auth = MagicMock()
        mock_dispatcher = MagicMock()
        mock_app = MagicMock()
        
        endpoint = ConstantEndpoint("/api/test", mock_auth, mock_dispatcher)
        endpoint.add_routes(mock_app)
        
        # Verify add_routes was called with POST route
        mock_app.add_routes.assert_called_once()
        # The call should include web.post with the path and handler
        call_args = mock_app.add_routes.call_args[0][0]
        assert len(call_args) == 1  # One route added