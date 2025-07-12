"""
Tests for Reverse Gateway Dispatcher
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from trustgraph.rev_gateway.dispatcher import WebSocketResponder, MessageDispatcher


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


class TestMessageDispatcher:
    """Test cases for MessageDispatcher class"""

    def test_message_dispatcher_initialization_with_defaults(self):
        """Test MessageDispatcher initialization with default parameters"""
        dispatcher = MessageDispatcher()
        
        assert dispatcher.max_workers == 10
        assert dispatcher.semaphore._value == 10
        assert dispatcher.active_tasks == set()
        assert dispatcher.pulsar_client is None
        assert dispatcher.dispatcher_manager is None
        assert len(dispatcher.service_mapping) > 0

    def test_message_dispatcher_initialization_with_custom_workers(self):
        """Test MessageDispatcher initialization with custom max_workers"""
        dispatcher = MessageDispatcher(max_workers=5)
        
        assert dispatcher.max_workers == 5
        assert dispatcher.semaphore._value == 5

    @patch('trustgraph.rev_gateway.dispatcher.DispatcherManager')
    def test_message_dispatcher_initialization_with_pulsar_client(self, mock_dispatcher_manager):
        """Test MessageDispatcher initialization with pulsar_client and config_receiver"""
        mock_pulsar_client = MagicMock()
        mock_config_receiver = MagicMock()
        mock_dispatcher_instance = MagicMock()
        mock_dispatcher_manager.return_value = mock_dispatcher_instance
        
        dispatcher = MessageDispatcher(
            max_workers=8,
            config_receiver=mock_config_receiver,
            pulsar_client=mock_pulsar_client
        )
        
        assert dispatcher.max_workers == 8
        assert dispatcher.pulsar_client == mock_pulsar_client
        assert dispatcher.dispatcher_manager == mock_dispatcher_instance
        mock_dispatcher_manager.assert_called_once_with(
            mock_pulsar_client, mock_config_receiver, prefix="rev-gateway"
        )

    def test_message_dispatcher_service_mapping(self):
        """Test MessageDispatcher service mapping contains expected services"""
        dispatcher = MessageDispatcher()
        
        expected_services = [
            "text-completion", "graph-rag", "agent", "embeddings",
            "graph-embeddings", "triples", "document-load", "text-load",
            "flow", "knowledge", "config", "librarian", "document-rag"
        ]
        
        for service in expected_services:
            assert service in dispatcher.service_mapping
        
        # Test specific mappings
        assert dispatcher.service_mapping["text-completion"] == "text-completion"
        assert dispatcher.service_mapping["document-load"] == "document"
        assert dispatcher.service_mapping["text-load"] == "text-document"

    @pytest.mark.asyncio
    async def test_message_dispatcher_handle_message_without_dispatcher_manager(self):
        """Test MessageDispatcher handle_message without dispatcher manager"""
        dispatcher = MessageDispatcher()
        
        test_message = {
            "id": "test-123",
            "service": "test-service",
            "request": {"data": "test"}
        }
        
        result = await dispatcher.handle_message(test_message)
        
        assert result["id"] == "test-123"
        assert "error" in result["response"]
        assert "DispatcherManager not available" in result["response"]["error"]

    @pytest.mark.asyncio
    async def test_message_dispatcher_handle_message_with_exception(self):
        """Test MessageDispatcher handle_message with exception during processing"""
        mock_dispatcher_manager = MagicMock()
        mock_dispatcher_manager.invoke_global_service.side_effect = Exception("Test error")
        
        dispatcher = MessageDispatcher()
        dispatcher.dispatcher_manager = mock_dispatcher_manager
        
        test_message = {
            "id": "test-456",
            "service": "text-completion",
            "request": {"prompt": "test"}
        }
        
        with patch('trustgraph.rev_gateway.dispatcher.global_dispatchers', {"text-completion": True}):
            result = await dispatcher.handle_message(test_message)
        
        assert result["id"] == "test-456"
        assert "error" in result["response"]
        assert "Test error" in result["response"]["error"]

    @pytest.mark.asyncio
    async def test_message_dispatcher_handle_message_global_service(self):
        """Test MessageDispatcher handle_message with global service"""
        mock_dispatcher_manager = MagicMock()
        mock_responder = MagicMock()
        mock_responder.completed = True
        mock_responder.response = {"result": "success"}
        
        dispatcher = MessageDispatcher()
        dispatcher.dispatcher_manager = mock_dispatcher_manager
        
        test_message = {
            "id": "test-789",
            "service": "text-completion",
            "request": {"prompt": "hello"}
        }
        
        with patch('trustgraph.rev_gateway.dispatcher.global_dispatchers', {"text-completion": True}):
            with patch('trustgraph.rev_gateway.dispatcher.WebSocketResponder', return_value=mock_responder):
                result = await dispatcher.handle_message(test_message)
        
        assert result["id"] == "test-789"
        assert result["response"] == {"result": "success"}
        mock_dispatcher_manager.invoke_global_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_message_dispatcher_handle_message_flow_service(self):
        """Test MessageDispatcher handle_message with flow service"""
        mock_dispatcher_manager = MagicMock()
        mock_responder = MagicMock()
        mock_responder.completed = True
        mock_responder.response = {"data": "flow_result"}
        
        dispatcher = MessageDispatcher()
        dispatcher.dispatcher_manager = mock_dispatcher_manager
        
        test_message = {
            "id": "test-flow-123",
            "service": "document-rag",
            "request": {"query": "test"},
            "flow": "custom-flow"
        }
        
        with patch('trustgraph.rev_gateway.dispatcher.global_dispatchers', {}):
            with patch('trustgraph.rev_gateway.dispatcher.WebSocketResponder', return_value=mock_responder):
                result = await dispatcher.handle_message(test_message)
        
        assert result["id"] == "test-flow-123"
        assert result["response"] == {"data": "flow_result"}
        mock_dispatcher_manager.invoke_flow_service.assert_called_once_with(
            {"query": "test"}, mock_responder, "custom-flow", "document-rag"
        )

    @pytest.mark.asyncio
    async def test_message_dispatcher_handle_message_incomplete_response(self):
        """Test MessageDispatcher handle_message with incomplete response"""
        mock_dispatcher_manager = MagicMock()
        mock_responder = MagicMock()
        mock_responder.completed = False
        mock_responder.response = None
        
        dispatcher = MessageDispatcher()
        dispatcher.dispatcher_manager = mock_dispatcher_manager
        
        test_message = {
            "id": "test-incomplete",
            "service": "agent",
            "request": {"input": "test"}
        }
        
        with patch('trustgraph.rev_gateway.dispatcher.global_dispatchers', {}):
            with patch('trustgraph.rev_gateway.dispatcher.WebSocketResponder', return_value=mock_responder):
                result = await dispatcher.handle_message(test_message)
        
        assert result["id"] == "test-incomplete"
        assert result["response"] == {"error": "No response received"}

    @pytest.mark.asyncio
    async def test_message_dispatcher_shutdown(self):
        """Test MessageDispatcher shutdown method"""
        dispatcher = MessageDispatcher()
        
        # Add mock tasks
        mock_task1 = AsyncMock()
        mock_task2 = AsyncMock()
        dispatcher.active_tasks = {mock_task1, mock_task2}
        
        # Call shutdown
        await dispatcher.shutdown()
        
        # Verify tasks were handled (they should be empty after shutdown)
        assert len(dispatcher.active_tasks) == 2  # Tasks remain in set but are completed

    @pytest.mark.asyncio
    async def test_message_dispatcher_shutdown_with_no_tasks(self):
        """Test MessageDispatcher shutdown with no active tasks"""
        dispatcher = MessageDispatcher()
        
        # Call shutdown with no active tasks
        await dispatcher.shutdown()
        
        # Should complete without error
        assert dispatcher.active_tasks == set()