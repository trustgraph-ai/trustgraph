"""
Tests for Gateway Service Requestor
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from trustgraph.gateway.dispatch.requestor import ServiceRequestor


class TestServiceRequestor:
    """Test cases for ServiceRequestor class"""

    def test_service_requestor_initialization(self):
        """Test ServiceRequestor initialization"""
        mock_backend = MagicMock()
        mock_request_schema = MagicMock()
        mock_response_schema = MagicMock()

        requestor = ServiceRequestor(
            backend=mock_backend,
            request_queue="test-request-queue",
            request_schema=mock_request_schema,
            response_queue="test-response-queue",
            response_schema=mock_response_schema,
            subscription="test-subscription",
            consumer_name="test-consumer",
            timeout=300
        )

        assert requestor.backend is mock_backend
        assert requestor.request_queue == "test-request-queue"
        assert requestor.request_schema is mock_request_schema
        assert requestor.response_queue == "test-response-queue"
        assert requestor.response_schema is mock_response_schema
        assert requestor.timeout == 300
        assert requestor.running is True
        assert requestor.client is None

    def test_service_requestor_with_defaults(self):
        """Test ServiceRequestor initialization with default parameters"""
        mock_backend = MagicMock()
        mock_request_schema = MagicMock()
        mock_response_schema = MagicMock()

        requestor = ServiceRequestor(
            backend=mock_backend,
            request_queue="test-queue",
            request_schema=mock_request_schema,
            response_queue="response-queue",
            response_schema=mock_response_schema
        )

        # Verify default values
        assert requestor.timeout == 600  # Default timeout
        assert requestor.running is True
        assert requestor.client is None

    @patch('trustgraph.gateway.dispatch.requestor.RequestResponseClient')
    @pytest.mark.asyncio
    async def test_service_requestor_start(self, mock_rrc_class):
        """Test ServiceRequestor start method"""
        mock_backend = MagicMock()
        mock_request_schema = MagicMock()
        mock_response_schema = MagicMock()
        mock_client_instance = AsyncMock()
        mock_rrc_class.create = AsyncMock(return_value=mock_client_instance)

        requestor = ServiceRequestor(
            backend=mock_backend,
            request_queue="test-queue",
            request_schema=mock_request_schema,
            response_queue="response-queue",
            response_schema=mock_response_schema
        )

        # Call start
        await requestor.start()

        # Verify RequestResponseClient.create was called correctly
        mock_rrc_class.create.assert_called_once_with(
            backend=mock_backend,
            request_topic="test-queue",
            response_topic="response-queue",
            request_schema=mock_request_schema,
            response_schema=mock_response_schema,
            processor_id="api-gateway",
            target_service=None,
        )
        assert requestor.client is mock_client_instance
        assert requestor.running is True

    @patch('trustgraph.gateway.dispatch.requestor.RequestResponseClient')
    @pytest.mark.asyncio
    async def test_service_requestor_stop(self, mock_rrc_class):
        """Test ServiceRequestor stop method"""
        mock_client_instance = AsyncMock()
        mock_rrc_class.create = AsyncMock(return_value=mock_client_instance)

        requestor = ServiceRequestor(
            backend=MagicMock(),
            request_queue="test-queue",
            request_schema=MagicMock(),
            response_queue="response-queue",
            response_schema=MagicMock()
        )

        await requestor.start()
        await requestor.stop()

        assert requestor.running is False
        mock_client_instance.close.assert_called_once()
        assert requestor.client is None

    def test_service_requestor_attributes(self):
        """Test ServiceRequestor has correct attributes"""
        mock_backend = MagicMock()

        requestor = ServiceRequestor(
            backend=mock_backend,
            request_queue="test-queue",
            request_schema=MagicMock(),
            response_queue="response-queue",
            response_schema=MagicMock()
        )

        # Verify attributes are set correctly
        assert requestor.client is None
        assert requestor.running is True
