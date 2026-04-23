"""
Tests for Gateway Socket Endpoint.

In production the only SocketEndpoint registered with HTTP-layer
auth is ``/api/v1/socket`` using ``capability=AUTHENTICATED`` with
``in_band_auth=True`` (first-frame auth over the websocket frames,
not at the handshake).  The tests below use AUTHENTICATED as the
representative capability; construction / worker / listener
behaviour is independent of which capability is configured.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from aiohttp import WSMsgType

from trustgraph.gateway.endpoint.socket import SocketEndpoint
from trustgraph.gateway.capabilities import AUTHENTICATED


class TestSocketEndpoint:
    """Test cases for SocketEndpoint class"""

    def test_socket_endpoint_initialization(self):
        """Construction records the configured capability on the
        instance.  No permissive default is applied."""
        mock_auth = MagicMock()
        mock_dispatcher = MagicMock()

        endpoint = SocketEndpoint(
            endpoint_path="/api/socket",
            auth=mock_auth,
            dispatcher=mock_dispatcher,
            capability=AUTHENTICATED,
        )

        assert endpoint.path == "/api/socket"
        assert endpoint.auth == mock_auth
        assert endpoint.dispatcher == mock_dispatcher
        assert endpoint.capability == AUTHENTICATED

    @pytest.mark.asyncio
    async def test_worker_method(self):
        """Test SocketEndpoint worker method"""
        mock_auth = MagicMock()
        mock_dispatcher = AsyncMock()

        endpoint = SocketEndpoint(
            "/api/socket", mock_auth, mock_dispatcher,
            capability=AUTHENTICATED,
        )

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

        endpoint = SocketEndpoint(
            "/api/socket", mock_auth, mock_dispatcher,
            capability=AUTHENTICATED,
        )
        
        # Mock websocket with text message
        mock_msg = MagicMock()
        mock_msg.type = WSMsgType.TEXT
        
        # Create async iterator for websocket
        async def async_iter():
            yield mock_msg
        
        mock_ws = AsyncMock()
        mock_ws.__aiter__ = lambda self: async_iter()
        mock_ws.closed = False  # Set closed attribute
        mock_running = MagicMock()
        
        # Call listener method
        await endpoint.listener(mock_ws, mock_dispatcher, mock_running)
        
        # Verify dispatcher.receive was called with the message
        mock_dispatcher.receive.assert_called_once_with(mock_msg)
        # Verify cleanup methods were called
        mock_running.stop.assert_called_once()
        mock_ws.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_listener_method_with_binary_message(self):
        """Test SocketEndpoint listener method with binary message"""
        mock_auth = MagicMock()
        mock_dispatcher = AsyncMock()

        endpoint = SocketEndpoint(
            "/api/socket", mock_auth, mock_dispatcher,
            capability=AUTHENTICATED,
        )
        
        # Mock websocket with binary message
        mock_msg = MagicMock()
        mock_msg.type = WSMsgType.BINARY
        
        # Create async iterator for websocket
        async def async_iter():
            yield mock_msg
        
        mock_ws = AsyncMock()
        mock_ws.__aiter__ = lambda self: async_iter()
        mock_ws.closed = False  # Set closed attribute
        mock_running = MagicMock()
        
        # Call listener method
        await endpoint.listener(mock_ws, mock_dispatcher, mock_running)
        
        # Verify dispatcher.receive was called with the message
        mock_dispatcher.receive.assert_called_once_with(mock_msg)
        # Verify cleanup methods were called
        mock_running.stop.assert_called_once()
        mock_ws.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_listener_method_with_close_message(self):
        """Test SocketEndpoint listener method with close message"""
        mock_auth = MagicMock()
        mock_dispatcher = AsyncMock()

        endpoint = SocketEndpoint(
            "/api/socket", mock_auth, mock_dispatcher,
            capability=AUTHENTICATED,
        )
        
        # Mock websocket with close message
        mock_msg = MagicMock()
        mock_msg.type = WSMsgType.CLOSE
        
        # Create async iterator for websocket
        async def async_iter():
            yield mock_msg
        
        mock_ws = AsyncMock()
        mock_ws.__aiter__ = lambda self: async_iter()
        mock_ws.closed = False  # Set closed attribute
        mock_running = MagicMock()
        
        # Call listener method
        await endpoint.listener(mock_ws, mock_dispatcher, mock_running)
        
        # Verify dispatcher.receive was NOT called for close message
        mock_dispatcher.receive.assert_not_called()
        # Verify cleanup methods were called after break
        mock_running.stop.assert_called_once()
        mock_ws.close.assert_called_once()