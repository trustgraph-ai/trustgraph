"""
Tests for Gateway Config Dispatch
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock, Mock

from trustgraph.gateway.dispatch.config import ConfigRequestor

# Import parent class for local patching
from trustgraph.gateway.dispatch.requestor import ServiceRequestor


class TestConfigRequestor:
    """Test cases for ConfigRequestor class"""

    @patch('trustgraph.gateway.dispatch.config.TranslatorRegistry')
    def test_config_requestor_initialization(self, mock_translator_registry):
        """Test ConfigRequestor initialization"""
        # Mock translators
        mock_request_translator = Mock()
        mock_response_translator = Mock()
        mock_translator_registry.get_request_translator.return_value = mock_request_translator
        mock_translator_registry.get_response_translator.return_value = mock_response_translator
        
        # Mock dependencies
        mock_pulsar_client = Mock()
        
        requestor = ConfigRequestor(
            pulsar_client=mock_pulsar_client,
            consumer="test-consumer",
            subscriber="test-subscriber",
            timeout=60
        )
        
        # Verify translator setup
        mock_translator_registry.get_request_translator.assert_called_once_with("config")
        mock_translator_registry.get_response_translator.assert_called_once_with("config")
        
        assert requestor.request_translator == mock_request_translator
        assert requestor.response_translator == mock_response_translator

    @patch('trustgraph.gateway.dispatch.config.TranslatorRegistry')
    def test_config_requestor_to_request(self, mock_translator_registry):
        """Test ConfigRequestor to_request method"""
        # Mock translators
        mock_request_translator = Mock()
        mock_translator_registry.get_request_translator.return_value = mock_request_translator
        mock_translator_registry.get_response_translator.return_value = Mock()
        
        # Setup translator response
        mock_request_translator.to_pulsar.return_value = "translated_request"
        
        # Patch ServiceRequestor async methods with regular mocks (not AsyncMock)
        with patch.object(ServiceRequestor, 'start', return_value=None), \
             patch.object(ServiceRequestor, 'process', return_value=None):
            requestor = ConfigRequestor(
                pulsar_client=Mock(),
                consumer="test-consumer", 
                subscriber="test-subscriber"
            )
        
        # Call to_request
        result = requestor.to_request({"test": "body"})
        
        # Verify translator was called correctly
        mock_request_translator.to_pulsar.assert_called_once_with({"test": "body"})
        assert result == "translated_request"

    @patch('trustgraph.gateway.dispatch.config.TranslatorRegistry')
    def test_config_requestor_from_response(self, mock_translator_registry):
        """Test ConfigRequestor from_response method"""
        # Mock translators
        mock_response_translator = Mock()
        mock_translator_registry.get_request_translator.return_value = Mock()
        mock_translator_registry.get_response_translator.return_value = mock_response_translator
        
        # Setup translator response
        mock_response_translator.from_response_with_completion.return_value = "translated_response"
        
        requestor = ConfigRequestor(
            pulsar_client=Mock(),
            consumer="test-consumer",
            subscriber="test-subscriber"
        )
        
        # Call from_response
        mock_message = Mock()
        result = requestor.from_response(mock_message)
        
        # Verify translator was called correctly
        mock_response_translator.from_response_with_completion.assert_called_once_with(mock_message)
        assert result == "translated_response"