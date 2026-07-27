"""
Tests for Gateway Service Sender
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from trustgraph.gateway.dispatch.sender import ServiceSender


class TestServiceSender:
    """Test cases for ServiceSender class"""

    def test_service_sender_initialization(self):
        """Test ServiceSender initialization"""
        mock_backend = MagicMock()
        mock_schema = MagicMock()

        sender = ServiceSender(
            backend=mock_backend,
            queue="test-queue",
            schema=mock_schema
        )

        assert sender.backend is mock_backend
        assert sender.queue == "test-queue"
        assert sender.schema is mock_schema
        assert sender.producer is None

    @pytest.mark.asyncio
    async def test_service_sender_start(self):
        """Test ServiceSender start method"""
        mock_producer = AsyncMock()
        mock_backend = MagicMock()
        mock_schema = MagicMock()
        mock_backend.create_producer = AsyncMock(return_value=mock_producer)

        sender = ServiceSender(
            backend=mock_backend,
            queue="test-queue",
            schema=mock_schema
        )

        # Call start
        await sender.start()

        # Verify backend.create_producer was called correctly
        mock_backend.create_producer.assert_called_once_with(
            topic="test-queue",
            schema=mock_schema,
        )
        assert sender.producer is mock_producer

    @pytest.mark.asyncio
    async def test_service_sender_stop(self):
        """Test ServiceSender stop method"""
        mock_producer = AsyncMock()
        mock_backend = MagicMock()
        mock_backend.create_producer = AsyncMock(return_value=mock_producer)

        sender = ServiceSender(
            backend=mock_backend,
            queue="test-queue",
            schema=MagicMock()
        )

        await sender.start()
        await sender.stop()

        # Verify producer close was called
        mock_producer.close.assert_called_once()
        assert sender.producer is None

    def test_service_sender_to_request_not_implemented(self):
        """Test ServiceSender to_request method raises RuntimeError"""
        sender = ServiceSender(
            backend=MagicMock(),
            queue="test-queue",
            schema=MagicMock()
        )

        with pytest.raises(RuntimeError, match="Not defined"):
            sender.to_request({"test": "request"})

    @pytest.mark.asyncio
    async def test_service_sender_process(self):
        """Test ServiceSender process method"""
        mock_producer = AsyncMock()
        mock_backend = MagicMock()
        mock_backend.create_producer = AsyncMock(return_value=mock_producer)

        # Create a concrete sender that implements to_request
        class ConcreteSender(ServiceSender):
            def to_request(self, request):
                return {"processed": request}

        sender = ConcreteSender(
            backend=mock_backend,
            queue="test-queue",
            schema=MagicMock()
        )

        await sender.start()

        test_request = {"test": "data"}

        # Call process
        await sender.process(test_request)

        # Verify producer send was called with processed request (single arg)
        mock_producer.send.assert_called_once_with({"processed": test_request})

    def test_service_sender_attributes(self):
        """Test ServiceSender has correct attributes"""
        mock_backend = MagicMock()

        sender = ServiceSender(
            backend=mock_backend,
            queue="test-queue",
            schema=MagicMock()
        )

        # Verify attributes are set correctly
        assert sender.producer is None
