"""Unit tests for SocketEndpoint graceful shutdown functionality."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import web, WSMsgType
from trustgraph.gateway.endpoint.socket import SocketEndpoint
from trustgraph.gateway.running import Running


@pytest.fixture
def mock_auth():
    """Mock authentication service."""
    auth = MagicMock()
    auth.permitted.return_value = True
    return auth


@pytest.fixture
def mock_dispatcher_factory():
    """Mock dispatcher factory function."""
    async def dispatcher_factory(ws, running, match_info):
        dispatcher = AsyncMock()
        dispatcher.run = AsyncMock()
        dispatcher.receive = AsyncMock()
        dispatcher.destroy = AsyncMock()
        return dispatcher
    
    return dispatcher_factory


@pytest.fixture
def socket_endpoint(mock_auth, mock_dispatcher_factory):
    """Create SocketEndpoint for testing."""
    return SocketEndpoint(
        endpoint_path="/test-socket",
        auth=mock_auth,
        dispatcher=mock_dispatcher_factory
    )


@pytest.fixture
def mock_websocket():
    """Mock websocket response."""
    ws = AsyncMock(spec=web.WebSocketResponse)
    ws.prepare = AsyncMock()
    ws.close = AsyncMock()
    ws.closed = False
    return ws


@pytest.fixture
def mock_request():
    """Mock HTTP request."""
    request = MagicMock()
    request.query = {"token": "test-token"}
    request.match_info = {}
    return request


@pytest.mark.asyncio
async def test_listener_graceful_shutdown_on_close():
    """Test listener handles websocket close gracefully."""
    socket_endpoint = SocketEndpoint("/test", MagicMock(), AsyncMock())
    
    # Mock websocket that closes after one message
    ws = AsyncMock()
    
    # Create async iterator that yields one message then closes
    async def mock_iterator(self):
        # Yield normal message
        msg = MagicMock()
        msg.type = WSMsgType.TEXT
        yield msg
        
        # Yield close message 
        close_msg = MagicMock()
        close_msg.type = WSMsgType.CLOSE
        yield close_msg
    
    # Set the async iterator method
    ws.__aiter__ = mock_iterator
    
    dispatcher = AsyncMock()
    running = Running()
    
    with patch('asyncio.sleep') as mock_sleep:
        await socket_endpoint.listener(ws, dispatcher, running)
    
    # Should have processed one message
    dispatcher.receive.assert_called_once()
    
    # Should have initiated graceful shutdown
    assert running.get() is False
    
    # Should have slept for grace period
    mock_sleep.assert_called_once_with(1.0)


@pytest.mark.asyncio
async def test_handle_normal_flow():
    """Test normal websocket handling flow."""
    mock_auth = MagicMock()
    mock_auth.permitted.return_value = True
    
    dispatcher_created = False
    async def mock_dispatcher_factory(ws, running, match_info):
        nonlocal dispatcher_created
        dispatcher_created = True
        dispatcher = AsyncMock()
        dispatcher.destroy = AsyncMock()
        return dispatcher
    
    socket_endpoint = SocketEndpoint("/test", mock_auth, mock_dispatcher_factory)
    
    request = MagicMock()
    request.query = {"token": "valid-token"}
    request.match_info = {}
    
    with patch('aiohttp.web.WebSocketResponse') as mock_ws_class:
        mock_ws = AsyncMock()
        mock_ws.prepare = AsyncMock()
        mock_ws.close = AsyncMock()
        mock_ws.closed = False
        mock_ws_class.return_value = mock_ws
        
        with patch('asyncio.TaskGroup') as mock_task_group:
            # Mock task group context manager
            mock_tg = AsyncMock()
            mock_tg.__aenter__ = AsyncMock(return_value=mock_tg)
            mock_tg.__aexit__ = AsyncMock(return_value=None)
            mock_tg.create_task = MagicMock(return_value=AsyncMock())
            mock_task_group.return_value = mock_tg
            
            result = await socket_endpoint.handle(request)
    
    # Should have created dispatcher
    assert dispatcher_created is True
    
    # Should return websocket
    assert result == mock_ws


@pytest.mark.asyncio
async def test_handle_exception_group_cleanup():
    """Test exception group triggers dispatcher cleanup."""
    mock_auth = MagicMock()
    mock_auth.permitted.return_value = True
    
    mock_dispatcher = AsyncMock()
    mock_dispatcher.destroy = AsyncMock()
    
    async def mock_dispatcher_factory(ws, running, match_info):
        return mock_dispatcher
    
    socket_endpoint = SocketEndpoint("/test", mock_auth, mock_dispatcher_factory)
    
    request = MagicMock()
    request.query = {"token": "valid-token"}
    request.match_info = {}
    
    # Mock TaskGroup to raise ExceptionGroup
    class TestException(Exception):
        pass
    
    exception_group = ExceptionGroup("Test exceptions", [TestException("test")])
    
    with patch('aiohttp.web.WebSocketResponse') as mock_ws_class:
        mock_ws = AsyncMock()
        mock_ws.prepare = AsyncMock()
        mock_ws.close = AsyncMock() 
        mock_ws.closed = False
        mock_ws_class.return_value = mock_ws
        
        with patch('asyncio.TaskGroup') as mock_task_group:
            mock_tg = AsyncMock()
            mock_tg.__aenter__ = AsyncMock(return_value=mock_tg)
            mock_tg.__aexit__ = AsyncMock(side_effect=exception_group)
            mock_tg.create_task = MagicMock(side_effect=TestException("test"))
            mock_task_group.return_value = mock_tg
            
            with patch('trustgraph.gateway.endpoint.socket.asyncio.wait_for') as mock_wait_for:
                mock_wait_for.return_value = None
                
                result = await socket_endpoint.handle(request)
    
    # Should have attempted graceful cleanup
    mock_wait_for.assert_called_once()
    
    # Should have called destroy in finally block
    assert mock_dispatcher.destroy.call_count >= 1
    
    # Should have closed websocket
    mock_ws.close.assert_called()


@pytest.mark.asyncio
async def test_handle_dispatcher_cleanup_timeout():
    """Test dispatcher cleanup with timeout."""
    mock_auth = MagicMock()
    mock_auth.permitted.return_value = True
    
    # Mock dispatcher that takes long to destroy
    mock_dispatcher = AsyncMock()
    mock_dispatcher.destroy = AsyncMock()
    
    async def mock_dispatcher_factory(ws, running, match_info):
        return mock_dispatcher
    
    socket_endpoint = SocketEndpoint("/test", mock_auth, mock_dispatcher_factory)
    
    request = MagicMock()
    request.query = {"token": "valid-token"}
    request.match_info = {}
    
    # Mock TaskGroup to raise exception
    exception_group = ExceptionGroup("Test", [Exception("test")])
    
    with patch('aiohttp.web.WebSocketResponse') as mock_ws_class:
        mock_ws = AsyncMock()
        mock_ws.prepare = AsyncMock()
        mock_ws.close = AsyncMock()
        mock_ws.closed = False
        mock_ws_class.return_value = mock_ws
        
        with patch('asyncio.TaskGroup') as mock_task_group:
            mock_tg = AsyncMock()
            mock_tg.__aenter__ = AsyncMock(return_value=mock_tg)
            mock_tg.__aexit__ = AsyncMock(side_effect=exception_group)
            mock_tg.create_task = MagicMock(side_effect=Exception("test"))
            mock_task_group.return_value = mock_tg
            
            # Mock asyncio.wait_for to raise TimeoutError
            with patch('trustgraph.gateway.endpoint.socket.asyncio.wait_for') as mock_wait_for:
                mock_wait_for.side_effect = asyncio.TimeoutError("Cleanup timeout")
                
                result = await socket_endpoint.handle(request)
    
    # Should have attempted cleanup with timeout
    mock_wait_for.assert_called_once()
    # Check that timeout was passed correctly
    assert mock_wait_for.call_args[1]['timeout'] == 5.0
    
    # Should still call destroy in finally block
    assert mock_dispatcher.destroy.call_count >= 1


@pytest.mark.asyncio
async def test_handle_unauthorized_request():
    """Test handling of unauthorized requests."""
    mock_auth = MagicMock()
    mock_auth.permitted.return_value = False  # Unauthorized
    
    socket_endpoint = SocketEndpoint("/test", mock_auth, AsyncMock())
    
    request = MagicMock()
    request.query = {"token": "invalid-token"}
    
    result = await socket_endpoint.handle(request)
    
    # Should return HTTP 401
    assert isinstance(result, web.HTTPUnauthorized)
    
    # Should have checked permission
    mock_auth.permitted.assert_called_once_with("invalid-token", "socket")


@pytest.mark.asyncio
async def test_handle_missing_token():
    """Test handling of requests with missing token."""
    mock_auth = MagicMock()
    mock_auth.permitted.return_value = False
    
    socket_endpoint = SocketEndpoint("/test", mock_auth, AsyncMock())
    
    request = MagicMock()
    request.query = {}  # No token
    
    result = await socket_endpoint.handle(request)
    
    # Should return HTTP 401
    assert isinstance(result, web.HTTPUnauthorized)
    
    # Should have checked permission with empty token
    mock_auth.permitted.assert_called_once_with("", "socket")


@pytest.mark.asyncio
async def test_handle_websocket_already_closed():
    """Test handling when websocket is already closed."""
    mock_auth = MagicMock()
    mock_auth.permitted.return_value = True
    
    mock_dispatcher = AsyncMock()
    mock_dispatcher.destroy = AsyncMock()
    
    async def mock_dispatcher_factory(ws, running, match_info):
        return mock_dispatcher
    
    socket_endpoint = SocketEndpoint("/test", mock_auth, mock_dispatcher_factory)
    
    request = MagicMock()
    request.query = {"token": "valid-token"}
    request.match_info = {}
    
    with patch('aiohttp.web.WebSocketResponse') as mock_ws_class:
        mock_ws = AsyncMock()
        mock_ws.prepare = AsyncMock()
        mock_ws.close = AsyncMock()
        mock_ws.closed = True  # Already closed
        mock_ws_class.return_value = mock_ws
        
        with patch('asyncio.TaskGroup') as mock_task_group:
            mock_tg = AsyncMock()
            mock_tg.__aenter__ = AsyncMock(return_value=mock_tg)
            mock_tg.__aexit__ = AsyncMock(return_value=None)
            mock_tg.create_task = MagicMock(return_value=AsyncMock())
            mock_task_group.return_value = mock_tg
            
            result = await socket_endpoint.handle(request)
    
    # Should still have called destroy
    mock_dispatcher.destroy.assert_called()
    
    # Should not attempt to close already closed websocket
    mock_ws.close.assert_not_called()  # Not called in finally since ws.closed = True