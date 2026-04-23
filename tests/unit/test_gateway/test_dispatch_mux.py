"""
Tests for Gateway Dispatch Mux
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from trustgraph.gateway.dispatch.mux import Mux, MAX_QUEUE_SIZE


class TestMux:
    """Test cases for Mux class"""

    def test_mux_requires_auth(self):
        """Constructing a Mux without an ``auth`` argument must
        fail.  The Mux implements the first-frame auth protocol and
        there is no no-auth mode — a no-auth Mux would silently
        accept every frame without authenticating it."""
        with pytest.raises(ValueError, match="auth"):
            Mux(
                dispatcher_manager=MagicMock(),
                ws=MagicMock(),
                running=MagicMock(),
                auth=None,
            )

    def test_mux_initialization(self):
        """Test Mux initialization"""
        mock_dispatcher_manager = MagicMock()
        mock_ws = MagicMock()
        mock_running = MagicMock()
        
        mux = Mux(
            dispatcher_manager=mock_dispatcher_manager,
            ws=mock_ws,
            running=mock_running,
            auth=MagicMock(),
        )
        
        assert mux.dispatcher_manager == mock_dispatcher_manager
        assert mux.ws == mock_ws
        assert mux.running == mock_running
        assert isinstance(mux.q, asyncio.Queue)
        assert mux.q.maxsize == MAX_QUEUE_SIZE

    @pytest.mark.asyncio
    async def test_mux_destroy_with_websocket(self):
        """Test Mux destroy method with websocket"""
        mock_dispatcher_manager = MagicMock()
        mock_ws = AsyncMock()
        mock_running = MagicMock()
        
        mux = Mux(
            dispatcher_manager=mock_dispatcher_manager,
            ws=mock_ws,
            running=mock_running,
            auth=MagicMock(),
        )
        
        # Call destroy
        await mux.destroy()
        
        # Verify running.stop was called
        mock_running.stop.assert_called_once()
        
        # Verify websocket close was called
        mock_ws.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_mux_destroy_without_websocket(self):
        """Test Mux destroy method without websocket"""
        mock_dispatcher_manager = MagicMock()
        mock_running = MagicMock()
        
        mux = Mux(
            dispatcher_manager=mock_dispatcher_manager,
            ws=None,
            running=mock_running,
            auth=MagicMock(),
        )
        
        # Call destroy
        await mux.destroy()
        
        # Verify running.stop was called
        mock_running.stop.assert_called_once()
        # No websocket to close

    @pytest.mark.asyncio
    async def test_mux_receive_valid_message(self):
        """Test Mux receive method with valid message"""
        mock_dispatcher_manager = MagicMock()
        mock_ws = AsyncMock()
        mock_running = MagicMock()
        
        mux = Mux(
            dispatcher_manager=mock_dispatcher_manager,
            ws=mock_ws,
            running=mock_running,
            auth=MagicMock(),
        )
        
        # Mock message with valid JSON
        mock_msg = MagicMock()
        mock_msg.json.return_value = {
            "request": {"type": "test"},
            "id": "test-id-123",
            "service": "test-service"
        }
        
        # Call receive
        await mux.receive(mock_msg)
        
        # Verify json was called
        mock_msg.json.assert_called_once()

    @pytest.mark.asyncio
    async def test_mux_receive_message_without_request(self):
        """Test Mux receive method with message missing request field"""
        mock_dispatcher_manager = MagicMock()
        mock_ws = AsyncMock()
        mock_running = MagicMock()
        
        mux = Mux(
            dispatcher_manager=mock_dispatcher_manager,
            ws=mock_ws,
            running=mock_running,
            auth=MagicMock(),
        )
        
        # Mock message without request field
        mock_msg = MagicMock()
        mock_msg.json.return_value = {
            "id": "test-id-123"
        }
        
        # receive method should handle the RuntimeError internally
        # Based on the code, it seems to catch exceptions
        await mux.receive(mock_msg)
        
        mock_ws.send_json.assert_called_once_with({
            "error": {"message": "Bad message", "type": "error"},
            "complete": True,
            "id": "test-id-123",
        })

    @pytest.mark.asyncio
    async def test_mux_receive_message_without_id(self):
        """Test Mux receive method with message missing id field"""
        mock_dispatcher_manager = MagicMock()
        mock_ws = AsyncMock()
        mock_running = MagicMock()

        mux = Mux(
            dispatcher_manager=mock_dispatcher_manager,
            ws=mock_ws,
            running=mock_running,
            auth=MagicMock(),
        )

        # Mock message without id field
        mock_msg = MagicMock()
        mock_msg.json.return_value = {
            "request": {"type": "test"}
        }

        # receive method should handle the RuntimeError internally
        await mux.receive(mock_msg)

        mock_ws.send_json.assert_called_once_with({
            "error": {"message": "Bad message", "type": "error"},
            "complete": True,
        })

    @pytest.mark.asyncio
    async def test_mux_receive_invalid_json(self):
        """Test Mux receive method with invalid JSON"""
        mock_dispatcher_manager = MagicMock()
        mock_ws = AsyncMock()
        mock_running = MagicMock()

        mux = Mux(
            dispatcher_manager=mock_dispatcher_manager,
            ws=mock_ws,
            running=mock_running,
            auth=MagicMock(),
        )

        # Mock message with invalid JSON
        mock_msg = MagicMock()
        mock_msg.json.side_effect = ValueError("Invalid JSON")

        # receive method should handle the ValueError internally
        await mux.receive(mock_msg)

        mock_msg.json.assert_called_once()
        mock_ws.send_json.assert_called_once_with({
            "error": {"message": "Invalid JSON", "type": "error"},
            "complete": True,
        })