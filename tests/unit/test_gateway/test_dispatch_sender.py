"""
Tests for Gateway Service Sender
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from trustgraph.gateway.dispatch.sender import ServiceSender


class TestServiceSender:
    """Test cases for ServiceSender class"""

    @patch('trustgraph.gateway.dispatch.sender.Publisher')
    def test_service_sender_initialization(self, mock_publisher):
        """Test ServiceSender initialization"""
        mock_backend = MagicMock()
        mock_schema = MagicMock()
        
        sender = ServiceSender(
            backend=mock_backend,
            queue="test-queue",
            schema=mock_schema
        )
        
        # Verify Publisher was created correctly
        mock_publisher.assert_called_once_with(
            mock_backend, "test-queue", schema=mock_schema
        )

    @patch('trustgraph.gateway.dispatch.sender.Publisher')
    @pytest.mark.asyncio
    async def test_service_sender_start(self, mock_publisher):
        """Test ServiceSender start method"""
        mock_pub_instance = AsyncMock()
        mock_publisher.return_value = mock_pub_instance
        
        sender = ServiceSender(
            backend=MagicMock(),
            queue="test-queue",
            schema=MagicMock()
        )
        
        # Call start
        await sender.start()
        
        # Verify publisher start was called
        mock_pub_instance.start.assert_called_once()

    @patch('trustgraph.gateway.dispatch.sender.Publisher')
    @pytest.mark.asyncio
    async def test_service_sender_stop(self, mock_publisher):
        """Test ServiceSender stop method"""
        mock_pub_instance = AsyncMock()
        mock_publisher.return_value = mock_pub_instance
        
        sender = ServiceSender(
            backend=MagicMock(),
            queue="test-queue",
            schema=MagicMock()
        )
        
        # Call stop
        await sender.stop()
        
        # Verify publisher stop was called
        mock_pub_instance.stop.assert_called_once()

    @patch('trustgraph.gateway.dispatch.sender.Publisher')
    def test_service_sender_to_request_not_implemented(self, mock_publisher):
        """Test ServiceSender to_request method raises RuntimeError"""
        sender = ServiceSender(
            backend=MagicMock(),
            queue="test-queue",
            schema=MagicMock()
        )
        
        with pytest.raises(RuntimeError, match="Not defined"):
            sender.to_request({"test": "request"})

    @patch('trustgraph.gateway.dispatch.sender.Publisher')
    @pytest.mark.asyncio
    async def test_service_sender_process(self, mock_publisher):
        """Test ServiceSender process method"""
        mock_pub_instance = AsyncMock()
        mock_publisher.return_value = mock_pub_instance
        
        # Create a concrete sender that implements to_request
        class ConcreteSender(ServiceSender):
            def to_request(self, request):
                return {"processed": request}
        
        sender = ConcreteSender(
            backend=MagicMock(),
            queue="test-queue",
            schema=MagicMock()
        )
        
        test_request = {"test": "data"}
        
        # Call process
        await sender.process(test_request)
        
        # Verify publisher send was called with processed request
        mock_pub_instance.send.assert_called_once_with(None, {"processed": test_request})

    @patch('trustgraph.gateway.dispatch.sender.Publisher')
    def test_service_sender_attributes(self, mock_publisher):
        """Test ServiceSender has correct attributes"""
        mock_pub_instance = MagicMock()
        mock_publisher.return_value = mock_pub_instance
        
        sender = ServiceSender(
            backend=MagicMock(),
            queue="test-queue",
            schema=MagicMock()
        )
        
        # Verify attributes are set correctly
        assert sender.pub == mock_pub_instance