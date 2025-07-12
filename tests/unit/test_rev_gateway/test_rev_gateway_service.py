"""
Tests for Reverse Gateway Service
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch, Mock
from aiohttp import WSMsgType, ClientWebSocketResponse
import json

from trustgraph.rev_gateway.service import ReverseGateway, parse_args, run


class TestReverseGateway:
    """Test cases for ReverseGateway class"""

    @patch('trustgraph.rev_gateway.service.ConfigReceiver')
    @patch('trustgraph.rev_gateway.service.MessageDispatcher')
    @patch('pulsar.Client')
    def test_reverse_gateway_initialization_defaults(self, mock_pulsar_client, mock_dispatcher, mock_config_receiver):
        """Test ReverseGateway initialization with default parameters"""
        mock_client_instance = MagicMock()
        mock_pulsar_client.return_value = mock_client_instance
        
        gateway = ReverseGateway()
        
        assert gateway.websocket_uri == "ws://localhost:7650/out"
        assert gateway.host == "localhost"
        assert gateway.port == 7650
        assert gateway.scheme == "ws"
        assert gateway.path == "/out"
        assert gateway.url == "ws://localhost:7650/out"
        assert gateway.max_workers == 10
        assert gateway.running is False
        assert gateway.reconnect_delay == 3.0
        assert gateway.pulsar_host == "pulsar://pulsar:6650"
        assert gateway.pulsar_api_key is None

    @patch('trustgraph.rev_gateway.service.ConfigReceiver')
    @patch('trustgraph.rev_gateway.service.MessageDispatcher')
    @patch('pulsar.Client')
    def test_reverse_gateway_initialization_custom_params(self, mock_pulsar_client, mock_dispatcher, mock_config_receiver):
        """Test ReverseGateway initialization with custom parameters"""
        mock_client_instance = MagicMock()
        mock_pulsar_client.return_value = mock_client_instance
        
        gateway = ReverseGateway(
            websocket_uri="wss://example.com:8080/websocket",
            max_workers=20,
            pulsar_host="pulsar://custom:6650",
            pulsar_api_key="test-key",
            pulsar_listener="test-listener"
        )
        
        assert gateway.websocket_uri == "wss://example.com:8080/websocket"
        assert gateway.host == "example.com"
        assert gateway.port == 8080
        assert gateway.scheme == "wss"
        assert gateway.path == "/websocket"
        assert gateway.url == "wss://example.com:8080/websocket"
        assert gateway.max_workers == 20
        assert gateway.pulsar_host == "pulsar://custom:6650"
        assert gateway.pulsar_api_key == "test-key"
        assert gateway.pulsar_listener == "test-listener"

    @patch('trustgraph.rev_gateway.service.ConfigReceiver')
    @patch('trustgraph.rev_gateway.service.MessageDispatcher')
    @patch('pulsar.Client')
    def test_reverse_gateway_initialization_with_missing_path(self, mock_pulsar_client, mock_dispatcher, mock_config_receiver):
        """Test ReverseGateway initialization with WebSocket URI missing path"""
        mock_client_instance = MagicMock()
        mock_pulsar_client.return_value = mock_client_instance
        
        gateway = ReverseGateway(websocket_uri="ws://example.com")
        
        assert gateway.path == "/ws"
        assert gateway.url == "ws://example.com/ws"

    @patch('trustgraph.rev_gateway.service.ConfigReceiver')
    @patch('trustgraph.rev_gateway.service.MessageDispatcher')
    @patch('pulsar.Client')
    def test_reverse_gateway_initialization_invalid_scheme(self, mock_pulsar_client, mock_dispatcher, mock_config_receiver):
        """Test ReverseGateway initialization with invalid WebSocket scheme"""
        with pytest.raises(ValueError, match="WebSocket URI must use ws:// or wss:// scheme"):
            ReverseGateway(websocket_uri="http://example.com")

    @patch('trustgraph.rev_gateway.service.ConfigReceiver')
    @patch('trustgraph.rev_gateway.service.MessageDispatcher')
    @patch('pulsar.Client')
    def test_reverse_gateway_initialization_missing_hostname(self, mock_pulsar_client, mock_dispatcher, mock_config_receiver):
        """Test ReverseGateway initialization with missing hostname"""
        with pytest.raises(ValueError, match="WebSocket URI must include hostname"):
            ReverseGateway(websocket_uri="ws://")

    @patch('trustgraph.rev_gateway.service.ConfigReceiver')
    @patch('trustgraph.rev_gateway.service.MessageDispatcher')
    @patch('pulsar.Client')
    def test_reverse_gateway_pulsar_client_with_auth(self, mock_pulsar_client, mock_dispatcher, mock_config_receiver):
        """Test ReverseGateway creates Pulsar client with authentication"""
        mock_client_instance = MagicMock()
        mock_pulsar_client.return_value = mock_client_instance
        
        with patch('pulsar.AuthenticationToken') as mock_auth:
            mock_auth_instance = MagicMock()
            mock_auth.return_value = mock_auth_instance
            
            gateway = ReverseGateway(
                pulsar_api_key="test-key",
                pulsar_listener="test-listener"
            )
            
            mock_auth.assert_called_once_with("test-key")
            mock_pulsar_client.assert_called_once_with(
                "pulsar://pulsar:6650",
                listener_name="test-listener",
                authentication=mock_auth_instance
            )

    @patch('trustgraph.rev_gateway.service.ConfigReceiver')
    @patch('trustgraph.rev_gateway.service.MessageDispatcher')
    @patch('pulsar.Client')
    @patch('aiohttp.ClientSession')
    @pytest.mark.asyncio
    async def test_reverse_gateway_connect_success(self, mock_session_class, mock_pulsar_client, mock_dispatcher, mock_config_receiver):
        """Test ReverseGateway successful connection"""
        mock_client_instance = MagicMock()
        mock_pulsar_client.return_value = mock_client_instance
        
        mock_session = AsyncMock()
        mock_ws = AsyncMock()
        mock_session.ws_connect.return_value = mock_ws
        mock_session_class.return_value = mock_session
        
        gateway = ReverseGateway()
        
        result = await gateway.connect()
        
        assert result is True
        assert gateway.session == mock_session
        assert gateway.ws == mock_ws
        mock_session.ws_connect.assert_called_once_with(gateway.url)

    @patch('trustgraph.rev_gateway.service.ConfigReceiver')
    @patch('trustgraph.rev_gateway.service.MessageDispatcher')
    @patch('pulsar.Client')
    @patch('aiohttp.ClientSession')
    @pytest.mark.asyncio
    async def test_reverse_gateway_connect_failure(self, mock_session_class, mock_pulsar_client, mock_dispatcher, mock_config_receiver):
        """Test ReverseGateway connection failure"""
        mock_client_instance = MagicMock()
        mock_pulsar_client.return_value = mock_client_instance
        
        mock_session = AsyncMock()
        mock_session.ws_connect.side_effect = Exception("Connection failed")
        mock_session_class.return_value = mock_session
        
        gateway = ReverseGateway()
        
        result = await gateway.connect()
        
        assert result is False

    @patch('trustgraph.rev_gateway.service.ConfigReceiver')
    @patch('trustgraph.rev_gateway.service.MessageDispatcher')
    @patch('pulsar.Client')
    @pytest.mark.asyncio
    async def test_reverse_gateway_disconnect(self, mock_pulsar_client, mock_dispatcher, mock_config_receiver):
        """Test ReverseGateway disconnect"""
        mock_client_instance = MagicMock()
        mock_pulsar_client.return_value = mock_client_instance
        
        gateway = ReverseGateway()
        
        # Mock websocket and session
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_session = AsyncMock()
        mock_session.closed = False
        
        gateway.ws = mock_ws
        gateway.session = mock_session
        
        await gateway.disconnect()
        
        mock_ws.close.assert_called_once()
        mock_session.close.assert_called_once()
        assert gateway.ws is None
        assert gateway.session is None

    @patch('trustgraph.rev_gateway.service.ConfigReceiver')
    @patch('trustgraph.rev_gateway.service.MessageDispatcher')
    @patch('pulsar.Client')
    @pytest.mark.asyncio
    async def test_reverse_gateway_send_message(self, mock_pulsar_client, mock_dispatcher, mock_config_receiver):
        """Test ReverseGateway send message"""
        mock_client_instance = MagicMock()
        mock_pulsar_client.return_value = mock_client_instance
        
        gateway = ReverseGateway()
        
        # Mock websocket
        mock_ws = AsyncMock()
        mock_ws.closed = False
        gateway.ws = mock_ws
        
        test_message = {"id": "test", "data": "hello"}
        
        await gateway.send_message(test_message)
        
        mock_ws.send_str.assert_called_once_with(json.dumps(test_message))

    @patch('trustgraph.rev_gateway.service.ConfigReceiver')
    @patch('trustgraph.rev_gateway.service.MessageDispatcher')
    @patch('pulsar.Client')
    @pytest.mark.asyncio
    async def test_reverse_gateway_send_message_closed_connection(self, mock_pulsar_client, mock_dispatcher, mock_config_receiver):
        """Test ReverseGateway send message with closed connection"""
        mock_client_instance = MagicMock()
        mock_pulsar_client.return_value = mock_client_instance
        
        gateway = ReverseGateway()
        
        # Mock closed websocket
        mock_ws = AsyncMock()
        mock_ws.closed = True
        gateway.ws = mock_ws
        
        test_message = {"id": "test", "data": "hello"}
        
        await gateway.send_message(test_message)
        
        # Should not call send_str on closed connection
        mock_ws.send_str.assert_not_called()

    @patch('trustgraph.rev_gateway.service.ConfigReceiver')
    @patch('trustgraph.rev_gateway.service.MessageDispatcher')
    @patch('pulsar.Client')
    @pytest.mark.asyncio
    async def test_reverse_gateway_handle_message(self, mock_pulsar_client, mock_dispatcher, mock_config_receiver):
        """Test ReverseGateway handle message"""
        mock_client_instance = MagicMock()
        mock_pulsar_client.return_value = mock_client_instance
        
        mock_dispatcher_instance = AsyncMock()
        mock_dispatcher_instance.handle_message.return_value = {"response": "success"}
        mock_dispatcher.return_value = mock_dispatcher_instance
        
        gateway = ReverseGateway()
        
        # Mock send_message
        gateway.send_message = AsyncMock()
        
        test_message = '{"id": "test", "service": "test-service", "request": {"data": "test"}}'
        
        await gateway.handle_message(test_message)
        
        mock_dispatcher_instance.handle_message.assert_called_once_with({
            "id": "test",
            "service": "test-service", 
            "request": {"data": "test"}
        })
        gateway.send_message.assert_called_once_with({"response": "success"})

    @patch('trustgraph.rev_gateway.service.ConfigReceiver')
    @patch('trustgraph.rev_gateway.service.MessageDispatcher')
    @patch('pulsar.Client')
    @pytest.mark.asyncio
    async def test_reverse_gateway_handle_message_invalid_json(self, mock_pulsar_client, mock_dispatcher, mock_config_receiver):
        """Test ReverseGateway handle message with invalid JSON"""
        mock_client_instance = MagicMock()
        mock_pulsar_client.return_value = mock_client_instance
        
        gateway = ReverseGateway()
        
        # Mock send_message
        gateway.send_message = AsyncMock()
        
        test_message = 'invalid json'
        
        # Should not raise exception
        await gateway.handle_message(test_message)
        
        # Should not call send_message due to error
        gateway.send_message.assert_not_called()

    @patch('trustgraph.rev_gateway.service.ConfigReceiver')
    @patch('trustgraph.rev_gateway.service.MessageDispatcher')
    @patch('pulsar.Client')
    @pytest.mark.asyncio
    async def test_reverse_gateway_listen_text_message(self, mock_pulsar_client, mock_dispatcher, mock_config_receiver):
        """Test ReverseGateway listen with text message"""
        mock_client_instance = MagicMock()
        mock_pulsar_client.return_value = mock_client_instance
        
        gateway = ReverseGateway()
        gateway.running = True
        
        # Mock websocket
        mock_ws = AsyncMock()
        mock_ws.closed = False
        gateway.ws = mock_ws
        
        # Mock handle_message
        gateway.handle_message = AsyncMock()
        
        # Mock message
        mock_msg = MagicMock()
        mock_msg.type = WSMsgType.TEXT
        mock_msg.data = '{"test": "message"}'
        
        # Mock receive to return message once, then raise exception to stop loop
        mock_ws.receive.side_effect = [mock_msg, Exception("Test stop")]
        
        # listen() catches exceptions and breaks, so no exception should be raised
        await gateway.listen()
        
        gateway.handle_message.assert_called_once_with('{"test": "message"}')

    @patch('trustgraph.rev_gateway.service.ConfigReceiver')
    @patch('trustgraph.rev_gateway.service.MessageDispatcher')
    @patch('pulsar.Client')
    @pytest.mark.asyncio
    async def test_reverse_gateway_listen_binary_message(self, mock_pulsar_client, mock_dispatcher, mock_config_receiver):
        """Test ReverseGateway listen with binary message"""
        mock_client_instance = MagicMock()
        mock_pulsar_client.return_value = mock_client_instance
        
        gateway = ReverseGateway()
        gateway.running = True
        
        # Mock websocket
        mock_ws = AsyncMock()
        mock_ws.closed = False
        gateway.ws = mock_ws
        
        # Mock handle_message
        gateway.handle_message = AsyncMock()
        
        # Mock message
        mock_msg = MagicMock()
        mock_msg.type = WSMsgType.BINARY
        mock_msg.data = b'{"test": "binary"}'
        
        # Mock receive to return message once, then raise exception to stop loop
        mock_ws.receive.side_effect = [mock_msg, Exception("Test stop")]
        
        # listen() catches exceptions and breaks, so no exception should be raised
        await gateway.listen()
        
        gateway.handle_message.assert_called_once_with('{"test": "binary"}')

    @patch('trustgraph.rev_gateway.service.ConfigReceiver')
    @patch('trustgraph.rev_gateway.service.MessageDispatcher')
    @patch('pulsar.Client')
    @pytest.mark.asyncio
    async def test_reverse_gateway_listen_close_message(self, mock_pulsar_client, mock_dispatcher, mock_config_receiver):
        """Test ReverseGateway listen with close message"""
        mock_client_instance = MagicMock()
        mock_pulsar_client.return_value = mock_client_instance
        
        gateway = ReverseGateway()
        gateway.running = True
        
        # Mock websocket
        mock_ws = AsyncMock()
        mock_ws.closed = False
        gateway.ws = mock_ws
        
        # Mock handle_message
        gateway.handle_message = AsyncMock()
        
        # Mock message
        mock_msg = MagicMock()
        mock_msg.type = WSMsgType.CLOSE
        
        # Mock receive to return close message
        mock_ws.receive.return_value = mock_msg
        
        await gateway.listen()
        
        # Should not call handle_message for close message
        gateway.handle_message.assert_not_called()

    @patch('trustgraph.rev_gateway.service.ConfigReceiver')
    @patch('trustgraph.rev_gateway.service.MessageDispatcher')
    @patch('pulsar.Client')
    @pytest.mark.asyncio
    async def test_reverse_gateway_shutdown(self, mock_pulsar_client, mock_dispatcher, mock_config_receiver):
        """Test ReverseGateway shutdown"""
        mock_client_instance = MagicMock()
        mock_pulsar_client.return_value = mock_client_instance
        
        mock_dispatcher_instance = AsyncMock()
        mock_dispatcher.return_value = mock_dispatcher_instance
        
        gateway = ReverseGateway()
        gateway.running = True
        
        # Mock disconnect
        gateway.disconnect = AsyncMock()
        
        await gateway.shutdown()
        
        assert gateway.running is False
        mock_dispatcher_instance.shutdown.assert_called_once()
        gateway.disconnect.assert_called_once()
        mock_client_instance.close.assert_called_once()

    @patch('trustgraph.rev_gateway.service.ConfigReceiver')
    @patch('trustgraph.rev_gateway.service.MessageDispatcher')
    @patch('pulsar.Client')
    def test_reverse_gateway_stop(self, mock_pulsar_client, mock_dispatcher, mock_config_receiver):
        """Test ReverseGateway stop"""
        mock_client_instance = MagicMock()
        mock_pulsar_client.return_value = mock_client_instance
        
        gateway = ReverseGateway()
        gateway.running = True
        
        gateway.stop()
        
        assert gateway.running is False


class TestReverseGatewayRun:
    """Test cases for ReverseGateway run method"""

    @patch('trustgraph.rev_gateway.service.ConfigReceiver')
    @patch('trustgraph.rev_gateway.service.MessageDispatcher')
    @patch('pulsar.Client')
    @pytest.mark.asyncio
    async def test_reverse_gateway_run_successful_cycle(self, mock_pulsar_client, mock_dispatcher, mock_config_receiver):
        """Test ReverseGateway run method with successful connect/listen cycle"""
        mock_client_instance = MagicMock()
        mock_pulsar_client.return_value = mock_client_instance
        
        mock_config_receiver_instance = AsyncMock()
        mock_config_receiver.return_value = mock_config_receiver_instance
        
        gateway = ReverseGateway()
        
        # Mock methods
        gateway.connect = AsyncMock(return_value=True)
        gateway.listen = AsyncMock()
        gateway.disconnect = AsyncMock()
        gateway.shutdown = AsyncMock()
        
        # Stop after one iteration
        call_count = 0
        async def mock_connect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return True
            else:
                gateway.running = False
                return False
        
        gateway.connect = mock_connect
        
        await gateway.run()
        
        mock_config_receiver_instance.start.assert_called_once()
        gateway.listen.assert_called_once()
        # disconnect is called twice: once in the main loop, once in shutdown
        assert gateway.disconnect.call_count == 2
        gateway.shutdown.assert_called_once()


class TestReverseGatewayArgs:
    """Test cases for argument parsing and run function"""

    def test_parse_args_defaults(self):
        """Test parse_args with default values"""
        import sys
        
        # Mock sys.argv
        original_argv = sys.argv
        sys.argv = ['reverse-gateway']
        
        try:
            args = parse_args()
            
            assert args.websocket_uri is None
            assert args.max_workers == 10
            assert args.pulsar_host is None
            assert args.pulsar_api_key is None
            assert args.pulsar_listener is None
        finally:
            sys.argv = original_argv

    def test_parse_args_custom_values(self):
        """Test parse_args with custom values"""
        import sys
        
        # Mock sys.argv
        original_argv = sys.argv
        sys.argv = [
            'reverse-gateway',
            '--websocket-uri', 'ws://custom:8080/ws',
            '--max-workers', '20',
            '--pulsar-host', 'pulsar://custom:6650',
            '--pulsar-api-key', 'test-key',
            '--pulsar-listener', 'test-listener'
        ]
        
        try:
            args = parse_args()
            
            assert args.websocket_uri == 'ws://custom:8080/ws'
            assert args.max_workers == 20
            assert args.pulsar_host == 'pulsar://custom:6650'
            assert args.pulsar_api_key == 'test-key'
            assert args.pulsar_listener == 'test-listener'
        finally:
            sys.argv = original_argv

    @patch('trustgraph.rev_gateway.service.ReverseGateway')
    @patch('asyncio.run')
    def test_run_function(self, mock_asyncio_run, mock_gateway_class):
        """Test run function"""
        import sys
        
        # Mock sys.argv
        original_argv = sys.argv
        sys.argv = ['reverse-gateway', '--max-workers', '15']
        
        try:
            mock_gateway_instance = MagicMock()
            mock_gateway_instance.url = "ws://localhost:7650/out"
            mock_gateway_instance.pulsar_host = "pulsar://pulsar:6650"
            mock_gateway_class.return_value = mock_gateway_instance
            
            run()
            
            mock_gateway_class.assert_called_once_with(
                websocket_uri=None,
                max_workers=15,
                pulsar_host=None,
                pulsar_api_key=None,
                pulsar_listener=None
            )
            mock_asyncio_run.assert_called_once_with(mock_gateway_instance.run())
        finally:
            sys.argv = original_argv