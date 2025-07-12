"""
Tests for Reverse Gateway Dispatcher
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from trustgraph.rev_gateway.dispatcher import WebSocketResponder


class TestWebSocketResponder:
    """Test cases for WebSocketResponder class"""

    def test_websocket_responder_initialization(self):
        """Test WebSocketResponder initialization"""
        responder = WebSocketResponder()
        
        assert responder.response is None
        assert responder.completed is False

    @pytest.mark.asyncio
    async def test_websocket_responder_send_method(self):
        """Test WebSocketResponder send method"""
        responder = WebSocketResponder()
        
        test_response = {"data": "test response"}
        
        # Call send method
        await responder.send(test_response)
        
        # Verify response was stored
        assert responder.response == test_response

    @pytest.mark.asyncio
    async def test_websocket_responder_call_method(self):
        """Test WebSocketResponder __call__ method"""
        responder = WebSocketResponder()
        
        test_response = {"result": "success"}
        test_completed = True
        
        # Call the responder
        await responder(test_response, test_completed)
        
        # Verify response and completed status were set
        assert responder.response == test_response
        assert responder.completed == test_completed

    @pytest.mark.asyncio
    async def test_websocket_responder_call_method_with_false_completion(self):
        """Test WebSocketResponder __call__ method with incomplete response"""
        responder = WebSocketResponder()
        
        test_response = {"partial": "data"}
        test_completed = False
        
        # Call the responder
        await responder(test_response, test_completed)
        
        # Verify response was set and completed is True (since send() always sets completed=True)
        assert responder.response == test_response
        assert responder.completed is True