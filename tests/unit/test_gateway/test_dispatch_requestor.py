"""
Tests for Gateway Service Requestor
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from trustgraph.gateway.dispatch.requestor import ServiceRequestor


class TestServiceRequestor:
    """Test cases for ServiceRequestor class"""

    @patch('trustgraph.gateway.dispatch.requestor.Publisher')
    @patch('trustgraph.gateway.dispatch.requestor.Subscriber')
    def test_service_requestor_initialization(self, mock_subscriber, mock_publisher):
        """Test ServiceRequestor initialization"""
        mock_pulsar_client = MagicMock()
        mock_request_schema = MagicMock()
        mock_response_schema = MagicMock()
        
        requestor = ServiceRequestor(
            pulsar_client=mock_pulsar_client,
            request_queue="test-request-queue",
            request_schema=mock_request_schema,
            response_queue="test-response-queue",
            response_schema=mock_response_schema,
            subscription="test-subscription",
            consumer_name="test-consumer",
            timeout=300
        )
        
        # Verify Publisher was created correctly
        mock_publisher.assert_called_once_with(
            mock_pulsar_client, "test-request-queue", schema=mock_request_schema
        )
        
        # Verify Subscriber was created correctly
        mock_subscriber.assert_called_once_with(
            mock_pulsar_client, "test-response-queue",
            "test-subscription", "test-consumer", mock_response_schema
        )
        
        assert requestor.timeout == 300
        assert requestor.running is True

    @patch('trustgraph.gateway.dispatch.requestor.Publisher')
    @patch('trustgraph.gateway.dispatch.requestor.Subscriber')
    def test_service_requestor_with_defaults(self, mock_subscriber, mock_publisher):
        """Test ServiceRequestor initialization with default parameters"""
        mock_pulsar_client = MagicMock()
        mock_request_schema = MagicMock()
        mock_response_schema = MagicMock()
        
        requestor = ServiceRequestor(
            pulsar_client=mock_pulsar_client,
            request_queue="test-queue",
            request_schema=mock_request_schema,
            response_queue="response-queue",
            response_schema=mock_response_schema
        )
        
        # Verify default values
        mock_subscriber.assert_called_once_with(
            mock_pulsar_client, "response-queue",
            "api-gateway", "api-gateway", mock_response_schema
        )
        assert requestor.timeout == 600  # Default timeout

    @patch('trustgraph.gateway.dispatch.requestor.Publisher')
    @patch('trustgraph.gateway.dispatch.requestor.Subscriber')
    @pytest.mark.asyncio
    async def test_service_requestor_start(self, mock_subscriber, mock_publisher):
        """Test ServiceRequestor start method"""
        mock_pulsar_client = MagicMock()
        mock_sub_instance = AsyncMock()
        mock_pub_instance = AsyncMock()
        mock_subscriber.return_value = mock_sub_instance
        mock_publisher.return_value = mock_pub_instance
        
        requestor = ServiceRequestor(
            pulsar_client=mock_pulsar_client,
            request_queue="test-queue",
            request_schema=MagicMock(),
            response_queue="response-queue",
            response_schema=MagicMock()
        )
        
        # Call start
        await requestor.start()
        
        # Verify both subscriber and publisher start were called
        mock_sub_instance.start.assert_called_once()
        mock_pub_instance.start.assert_called_once()
        assert requestor.running is True

    @patch('trustgraph.gateway.dispatch.requestor.Publisher')
    @patch('trustgraph.gateway.dispatch.requestor.Subscriber')
    def test_service_requestor_attributes(self, mock_subscriber, mock_publisher):
        """Test ServiceRequestor has correct attributes"""
        mock_pulsar_client = MagicMock()
        mock_pub_instance = AsyncMock()
        mock_sub_instance = AsyncMock()
        mock_publisher.return_value = mock_pub_instance
        mock_subscriber.return_value = mock_sub_instance
        
        requestor = ServiceRequestor(
            pulsar_client=mock_pulsar_client,
            request_queue="test-queue",
            request_schema=MagicMock(),
            response_queue="response-queue",
            response_schema=MagicMock()
        )
        
        # Verify attributes are set correctly
        assert requestor.pub == mock_pub_instance
        assert requestor.sub == mock_sub_instance
        assert requestor.running is True