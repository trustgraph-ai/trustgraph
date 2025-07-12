"""
Tests for Gateway Socket Endpoint
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from aiohttp import WSMsgType

from trustgraph.gateway.endpoint.socket import SocketEndpoint


class TestSocketEndpoint:
    """Test cases for SocketEndpoint class"""

    def test_socket_endpoint_initialization(self):
        """Test SocketEndpoint initialization"""
        mock_auth = MagicMock()
        mock_dispatcher = MagicMock()
        
        endpoint = SocketEndpoint(
            endpoint_path="/api/socket",
            auth=mock_auth,
            dispatcher=mock_dispatcher
        )
        
        assert endpoint.path == "/api/socket"
        assert endpoint.auth == mock_auth
        assert endpoint.dispatcher == mock_dispatcher
        assert endpoint.operation == "socket"

    @pytest.mark.asyncio
    async def test_worker_method(self):
        """Test SocketEndpoint worker method"""
        mock_auth = MagicMock()
        mock_dispatcher = AsyncMock()
        
        endpoint = SocketEndpoint("/api/socket", mock_auth, mock_dispatcher)
        
        mock_ws = MagicMock()
        mock_running = MagicMock()
        
        # Call worker method
        await endpoint.worker(mock_ws, mock_dispatcher, mock_running)
        
        # Verify dispatcher.run was called
        mock_dispatcher.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_listener_method_with_text_message(self):
        """Test SocketEndpoint listener method with text message"""
        mock_auth = MagicMock()
        mock_dispatcher = AsyncMock()
        
        endpoint = SocketEndpoint("/api/socket", mock_auth, mock_dispatcher)
        
        # Mock websocket with text message
        mock_msg = MagicMock()
        mock_msg.type = WSMsgType.TEXT
        
        # Create async iterator for websocket
        async def async_iter():
            yield mock_msg
        
        mock_ws = MagicMock()
        mock_ws.__aiter__ = lambda: async_iter()
        mock_running = MagicMock()
        
        # Call listener method
        await endpoint.listener(mock_ws, mock_dispatcher, mock_running)
        
        # Verify dispatcher.receive was called with the message
        mock_dispatcher.receive.assert_called_once_with(mock_msg)

    @pytest.mark.asyncio
    async def test_listener_method_with_binary_message(self):
        """Test SocketEndpoint listener method with binary message"""
        mock_auth = MagicMock()
        mock_dispatcher = AsyncMock()
        
        endpoint = SocketEndpoint("/api/socket", mock_auth, mock_dispatcher)
        
        # Mock websocket with binary message
        mock_msg = MagicMock()
        mock_msg.type = WSMsgType.BINARY
        
        # Create async iterator for websocket
        async def async_iter():
            yield mock_msg
        
        mock_ws = MagicMock()
        mock_ws.__aiter__ = lambda: async_iter()
        mock_running = MagicMock()
        
        # Call listener method
        await endpoint.listener(mock_ws, mock_dispatcher, mock_running)
        
        # Verify dispatcher.receive was called with the message
        mock_dispatcher.receive.assert_called_once_with(mock_msg)

    @pytest.mark.asyncio
    async def test_listener_method_with_close_message(self):
        """Test SocketEndpoint listener method with close message"""
        mock_auth = MagicMock()
        mock_dispatcher = AsyncMock()
        
        endpoint = SocketEndpoint("/api/socket", mock_auth, mock_dispatcher)
        
        # Mock websocket with close message
        mock_msg = MagicMock()
        mock_msg.type = WSMsgType.CLOSE
        
        # Create async iterator for websocket
        async def async_iter():
            yield mock_msg
        
        mock_ws = MagicMock()
        mock_ws.__aiter__ = lambda: async_iter()
        mock_running = MagicMock()
        
        # Call listener method
        await endpoint.listener(mock_ws, mock_dispatcher, mock_running)
        
        # Verify dispatcher.receive was NOT called for close message
        mock_dispatcher.receive.assert_not_called()