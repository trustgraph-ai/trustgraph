"""
Tests for Reverse Gateway Service
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch, Mock
from aiohttp import WSMsgType, ClientWebSocketResponse
import json

from trustgraph.rev_gateway.service import ReverseGateway, run


MOCK_PATCHES = [
    'trustgraph.rev_gateway.service.IamAuth',
    'trustgraph.rev_gateway.service.ConfigReceiver',
    'trustgraph.rev_gateway.service.MessageDispatcher',
    'trustgraph.rev_gateway.service.get_pubsub',
]


def make_gateway(**overrides):
    config = {"websocket_uri": "ws://localhost:7650/out"}
    config.update(overrides)
    return ReverseGateway(**config)


class TestReverseGateway:
    """Test cases for ReverseGateway class"""

    @patch(*MOCK_PATCHES[0:1])
    @patch(*MOCK_PATCHES[1:2])
    @patch(*MOCK_PATCHES[2:3])
    @patch(*MOCK_PATCHES[3:4])
    def test_reverse_gateway_initialization_defaults(
        self, mock_get_pubsub, mock_dispatcher,
        mock_config_receiver, mock_iam_auth,
    ):
        mock_get_pubsub.return_value = MagicMock()

        gateway = make_gateway()

        assert gateway.websocket_uri == "ws://localhost:7650/out"
        assert gateway.host == "localhost"
        assert gateway.port == 7650
        assert gateway.scheme == "ws"
        assert gateway.path == "/out"
        assert gateway.url == "ws://localhost:7650/out"
        assert gateway.max_workers == 10
        assert gateway.running is False
        assert gateway.reconnect_delay == 3.0

    @patch(*MOCK_PATCHES[0:1])
    @patch(*MOCK_PATCHES[1:2])
    @patch(*MOCK_PATCHES[2:3])
    @patch(*MOCK_PATCHES[3:4])
    def test_reverse_gateway_initialization_custom_params(
        self, mock_get_pubsub, mock_dispatcher,
        mock_config_receiver, mock_iam_auth,
    ):
        mock_get_pubsub.return_value = MagicMock()

        gateway = make_gateway(
            websocket_uri="wss://example.com:8080/websocket",
            max_workers=20,
        )

        assert gateway.websocket_uri == "wss://example.com:8080/websocket"
        assert gateway.host == "example.com"
        assert gateway.port == 8080
        assert gateway.scheme == "wss"
        assert gateway.path == "/websocket"
        assert gateway.url == "wss://example.com:8080/websocket"
        assert gateway.max_workers == 20

    @patch(*MOCK_PATCHES[0:1])
    @patch(*MOCK_PATCHES[1:2])
    @patch(*MOCK_PATCHES[2:3])
    @patch(*MOCK_PATCHES[3:4])
    def test_reverse_gateway_initialization_with_missing_path(
        self, mock_get_pubsub, mock_dispatcher,
        mock_config_receiver, mock_iam_auth,
    ):
        mock_get_pubsub.return_value = MagicMock()

        gateway = make_gateway(websocket_uri="ws://example.com")

        assert gateway.path == "/ws"
        assert gateway.url == "ws://example.com/ws"

    @patch(*MOCK_PATCHES[0:1])
    @patch(*MOCK_PATCHES[1:2])
    @patch(*MOCK_PATCHES[2:3])
    @patch(*MOCK_PATCHES[3:4])
    def test_reverse_gateway_initialization_invalid_scheme(
        self, mock_get_pubsub, mock_dispatcher,
        mock_config_receiver, mock_iam_auth,
    ):
        with pytest.raises(ValueError, match="WebSocket URI must use ws:// or wss:// scheme"):
            make_gateway(websocket_uri="http://example.com")

    @patch(*MOCK_PATCHES[0:1])
    @patch(*MOCK_PATCHES[1:2])
    @patch(*MOCK_PATCHES[2:3])
    @patch(*MOCK_PATCHES[3:4])
    def test_reverse_gateway_initialization_missing_hostname(
        self, mock_get_pubsub, mock_dispatcher,
        mock_config_receiver, mock_iam_auth,
    ):
        with pytest.raises(ValueError, match="WebSocket URI must include hostname"):
            make_gateway(websocket_uri="ws://")

    @patch(*MOCK_PATCHES[0:1])
    @patch(*MOCK_PATCHES[1:2])
    @patch(*MOCK_PATCHES[2:3])
    @patch(*MOCK_PATCHES[3:4])
    def test_reverse_gateway_iam_auth_created(
        self, mock_get_pubsub, mock_dispatcher,
        mock_config_receiver, mock_iam_auth,
    ):
        mock_backend = MagicMock()
        mock_get_pubsub.return_value = mock_backend

        gateway = make_gateway(id="test-rev-gw")

        mock_iam_auth.assert_called_once_with(
            backend=mock_backend,
            id="test-rev-gw",
        )

    @patch(*MOCK_PATCHES[0:1])
    @patch(*MOCK_PATCHES[1:2])
    @patch(*MOCK_PATCHES[2:3])
    @patch(*MOCK_PATCHES[3:4])
    def test_reverse_gateway_config_receiver_gets_auth(
        self, mock_get_pubsub, mock_dispatcher,
        mock_config_receiver, mock_iam_auth,
    ):
        mock_backend = MagicMock()
        mock_get_pubsub.return_value = mock_backend
        mock_auth_instance = MagicMock()
        mock_iam_auth.return_value = mock_auth_instance

        gateway = make_gateway()

        mock_config_receiver.assert_called_once_with(
            mock_backend, auth=mock_auth_instance,
        )

    @patch(*MOCK_PATCHES[0:1])
    @patch(*MOCK_PATCHES[1:2])
    @patch(*MOCK_PATCHES[2:3])
    @patch(*MOCK_PATCHES[3:4])
    @patch('trustgraph.rev_gateway.service.ClientSession')
    @pytest.mark.asyncio
    async def test_reverse_gateway_connect_success(
        self, mock_session_class, mock_get_pubsub,
        mock_dispatcher, mock_config_receiver, mock_iam_auth,
    ):
        mock_get_pubsub.return_value = MagicMock()

        mock_session = AsyncMock()
        mock_ws = AsyncMock()
        mock_session.ws_connect.return_value = mock_ws
        mock_session_class.return_value = mock_session

        gateway = make_gateway()

        result = await gateway.connect()

        assert result is True
        assert gateway.session == mock_session
        assert gateway.ws == mock_ws
        mock_session.ws_connect.assert_called_once_with(gateway.url)

    @patch(*MOCK_PATCHES[0:1])
    @patch(*MOCK_PATCHES[1:2])
    @patch(*MOCK_PATCHES[2:3])
    @patch(*MOCK_PATCHES[3:4])
    @patch('trustgraph.rev_gateway.service.ClientSession')
    @pytest.mark.asyncio
    async def test_reverse_gateway_connect_failure(
        self, mock_session_class, mock_get_pubsub,
        mock_dispatcher, mock_config_receiver, mock_iam_auth,
    ):
        mock_get_pubsub.return_value = MagicMock()

        mock_session = AsyncMock()
        mock_session.ws_connect.side_effect = Exception("Connection failed")
        mock_session_class.return_value = mock_session

        gateway = make_gateway()

        result = await gateway.connect()

        assert result is False

    @patch(*MOCK_PATCHES[0:1])
    @patch(*MOCK_PATCHES[1:2])
    @patch(*MOCK_PATCHES[2:3])
    @patch(*MOCK_PATCHES[3:4])
    @pytest.mark.asyncio
    async def test_reverse_gateway_disconnect(
        self, mock_get_pubsub, mock_dispatcher,
        mock_config_receiver, mock_iam_auth,
    ):
        mock_get_pubsub.return_value = MagicMock()

        gateway = make_gateway()

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

    @patch(*MOCK_PATCHES[0:1])
    @patch(*MOCK_PATCHES[1:2])
    @patch(*MOCK_PATCHES[2:3])
    @patch(*MOCK_PATCHES[3:4])
    @pytest.mark.asyncio
    async def test_reverse_gateway_send_message(
        self, mock_get_pubsub, mock_dispatcher,
        mock_config_receiver, mock_iam_auth,
    ):
        mock_get_pubsub.return_value = MagicMock()

        gateway = make_gateway()

        mock_ws = AsyncMock()
        mock_ws.closed = False
        gateway.ws = mock_ws

        test_message = {"id": "test", "data": "hello"}

        await gateway.send_message(test_message)

        mock_ws.send_str.assert_called_once_with(json.dumps(test_message))

    @patch(*MOCK_PATCHES[0:1])
    @patch(*MOCK_PATCHES[1:2])
    @patch(*MOCK_PATCHES[2:3])
    @patch(*MOCK_PATCHES[3:4])
    @pytest.mark.asyncio
    async def test_reverse_gateway_send_message_closed_connection(
        self, mock_get_pubsub, mock_dispatcher,
        mock_config_receiver, mock_iam_auth,
    ):
        mock_get_pubsub.return_value = MagicMock()

        gateway = make_gateway()

        mock_ws = AsyncMock()
        mock_ws.closed = True
        gateway.ws = mock_ws

        test_message = {"id": "test", "data": "hello"}

        await gateway.send_message(test_message)

        mock_ws.send_str.assert_not_called()

    @patch(*MOCK_PATCHES[0:1])
    @patch(*MOCK_PATCHES[1:2])
    @patch(*MOCK_PATCHES[2:3])
    @patch(*MOCK_PATCHES[3:4])
    @pytest.mark.asyncio
    async def test_reverse_gateway_handle_message(
        self, mock_get_pubsub, mock_dispatcher,
        mock_config_receiver, mock_iam_auth,
    ):
        mock_get_pubsub.return_value = MagicMock()

        mock_dispatcher_instance = AsyncMock()
        mock_dispatcher.return_value = mock_dispatcher_instance

        gateway = make_gateway()

        gateway.send_message = AsyncMock()

        test_message = '{"id": "test", "service": "test-service", "request": {"data": "test"}}'

        await gateway.handle_message(test_message)

        mock_dispatcher_instance.handle_message.assert_called_once_with(
            {
                "id": "test",
                "service": "test-service",
                "request": {"data": "test"},
            },
            gateway.send_message,
        )

    @patch(*MOCK_PATCHES[0:1])
    @patch(*MOCK_PATCHES[1:2])
    @patch(*MOCK_PATCHES[2:3])
    @patch(*MOCK_PATCHES[3:4])
    @pytest.mark.asyncio
    async def test_reverse_gateway_handle_message_invalid_json(
        self, mock_get_pubsub, mock_dispatcher,
        mock_config_receiver, mock_iam_auth,
    ):
        mock_get_pubsub.return_value = MagicMock()

        gateway = make_gateway()

        gateway.send_message = AsyncMock()

        await gateway.handle_message('invalid json')

        gateway.send_message.assert_not_called()

    @patch(*MOCK_PATCHES[0:1])
    @patch(*MOCK_PATCHES[1:2])
    @patch(*MOCK_PATCHES[2:3])
    @patch(*MOCK_PATCHES[3:4])
    @pytest.mark.asyncio
    async def test_reverse_gateway_listen_text_message(
        self, mock_get_pubsub, mock_dispatcher,
        mock_config_receiver, mock_iam_auth,
    ):
        mock_get_pubsub.return_value = MagicMock()

        gateway = make_gateway()
        gateway.running = True

        mock_ws = AsyncMock()
        mock_ws.closed = False
        gateway.ws = mock_ws

        gateway.handle_message = AsyncMock()

        mock_msg = MagicMock()
        mock_msg.type = WSMsgType.TEXT
        mock_msg.data = '{"test": "message"}'

        mock_ws.receive.side_effect = [mock_msg, Exception("Test stop")]

        await gateway.listen()

        gateway.handle_message.assert_called_once_with('{"test": "message"}')

    @patch(*MOCK_PATCHES[0:1])
    @patch(*MOCK_PATCHES[1:2])
    @patch(*MOCK_PATCHES[2:3])
    @patch(*MOCK_PATCHES[3:4])
    @pytest.mark.asyncio
    async def test_reverse_gateway_listen_binary_message(
        self, mock_get_pubsub, mock_dispatcher,
        mock_config_receiver, mock_iam_auth,
    ):
        mock_get_pubsub.return_value = MagicMock()

        gateway = make_gateway()
        gateway.running = True

        mock_ws = AsyncMock()
        mock_ws.closed = False
        gateway.ws = mock_ws

        gateway.handle_message = AsyncMock()

        mock_msg = MagicMock()
        mock_msg.type = WSMsgType.BINARY
        mock_msg.data = b'{"test": "binary"}'

        mock_ws.receive.side_effect = [mock_msg, Exception("Test stop")]

        await gateway.listen()

        gateway.handle_message.assert_called_once_with('{"test": "binary"}')

    @patch(*MOCK_PATCHES[0:1])
    @patch(*MOCK_PATCHES[1:2])
    @patch(*MOCK_PATCHES[2:3])
    @patch(*MOCK_PATCHES[3:4])
    @pytest.mark.asyncio
    async def test_reverse_gateway_listen_close_message(
        self, mock_get_pubsub, mock_dispatcher,
        mock_config_receiver, mock_iam_auth,
    ):
        mock_get_pubsub.return_value = MagicMock()

        gateway = make_gateway()
        gateway.running = True

        mock_ws = AsyncMock()
        mock_ws.closed = False
        gateway.ws = mock_ws

        gateway.handle_message = AsyncMock()

        mock_msg = MagicMock()
        mock_msg.type = WSMsgType.CLOSE

        mock_ws.receive.return_value = mock_msg

        await gateway.listen()

        gateway.handle_message.assert_not_called()

    @patch(*MOCK_PATCHES[0:1])
    @patch(*MOCK_PATCHES[1:2])
    @patch(*MOCK_PATCHES[2:3])
    @patch(*MOCK_PATCHES[3:4])
    @pytest.mark.asyncio
    async def test_reverse_gateway_shutdown(
        self, mock_get_pubsub, mock_dispatcher,
        mock_config_receiver, mock_iam_auth,
    ):
        mock_backend = MagicMock()
        mock_get_pubsub.return_value = mock_backend

        mock_dispatcher_instance = AsyncMock()
        mock_dispatcher.return_value = mock_dispatcher_instance

        gateway = make_gateway()
        gateway.running = True

        gateway.disconnect = AsyncMock()

        await gateway.shutdown()

        assert gateway.running is False
        mock_dispatcher_instance.shutdown.assert_called_once()
        gateway.disconnect.assert_called_once()
        mock_backend.close.assert_called_once()

    @patch(*MOCK_PATCHES[0:1])
    @patch(*MOCK_PATCHES[1:2])
    @patch(*MOCK_PATCHES[2:3])
    @patch(*MOCK_PATCHES[3:4])
    def test_reverse_gateway_stop(
        self, mock_get_pubsub, mock_dispatcher,
        mock_config_receiver, mock_iam_auth,
    ):
        mock_get_pubsub.return_value = MagicMock()

        gateway = make_gateway()
        gateway.running = True

        gateway.stop()

        assert gateway.running is False


class TestReverseGatewayRun:
    """Test cases for ReverseGateway run method"""

    @patch(*MOCK_PATCHES[0:1])
    @patch(*MOCK_PATCHES[1:2])
    @patch(*MOCK_PATCHES[2:3])
    @patch(*MOCK_PATCHES[3:4])
    @pytest.mark.asyncio
    async def test_reverse_gateway_run_successful_cycle(
        self, mock_get_pubsub, mock_dispatcher,
        mock_config_receiver, mock_iam_auth,
    ):
        mock_get_pubsub.return_value = MagicMock()

        mock_auth_instance = AsyncMock()
        mock_iam_auth.return_value = mock_auth_instance

        mock_config_receiver_instance = AsyncMock()
        mock_config_receiver.return_value = mock_config_receiver_instance

        gateway = make_gateway()

        gateway.listen = AsyncMock()
        gateway.disconnect = AsyncMock()
        gateway.shutdown = AsyncMock()

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

        mock_auth_instance.start.assert_called_once()
        mock_config_receiver_instance.start.assert_called_once()
        gateway.listen.assert_called_once()
        assert gateway.disconnect.call_count == 2
        gateway.shutdown.assert_called_once()
