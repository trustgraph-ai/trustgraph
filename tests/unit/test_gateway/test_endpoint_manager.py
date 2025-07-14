"""
Tests for Gateway Endpoint Manager
"""

import pytest
from unittest.mock import MagicMock

from trustgraph.gateway.endpoint.manager import EndpointManager


class TestEndpointManager:
    """Test cases for EndpointManager class"""

    def test_endpoint_manager_initialization(self):
        """Test EndpointManager initialization creates all endpoints"""
        mock_dispatcher_manager = MagicMock()
        mock_auth = MagicMock()
        
        # Mock dispatcher methods
        mock_dispatcher_manager.dispatch_global_service.return_value = MagicMock()
        mock_dispatcher_manager.dispatch_socket.return_value = MagicMock()
        mock_dispatcher_manager.dispatch_flow_service.return_value = MagicMock()
        mock_dispatcher_manager.dispatch_flow_import.return_value = MagicMock()
        mock_dispatcher_manager.dispatch_flow_export.return_value = MagicMock()
        mock_dispatcher_manager.dispatch_core_import.return_value = MagicMock()
        mock_dispatcher_manager.dispatch_core_export.return_value = MagicMock()
        
        manager = EndpointManager(
            dispatcher_manager=mock_dispatcher_manager,
            auth=mock_auth,
            prometheus_url="http://prometheus:9090",
            timeout=300
        )
        
        assert manager.dispatcher_manager == mock_dispatcher_manager
        assert manager.timeout == 300
        assert manager.services == {}
        assert len(manager.endpoints) > 0  # Should have multiple endpoints

    def test_endpoint_manager_with_default_timeout(self):
        """Test EndpointManager with default timeout value"""
        mock_dispatcher_manager = MagicMock()
        mock_auth = MagicMock()
        
        # Mock dispatcher methods
        mock_dispatcher_manager.dispatch_global_service.return_value = MagicMock()
        mock_dispatcher_manager.dispatch_socket.return_value = MagicMock()
        mock_dispatcher_manager.dispatch_flow_service.return_value = MagicMock()
        mock_dispatcher_manager.dispatch_flow_import.return_value = MagicMock()
        mock_dispatcher_manager.dispatch_flow_export.return_value = MagicMock()
        mock_dispatcher_manager.dispatch_core_import.return_value = MagicMock()
        mock_dispatcher_manager.dispatch_core_export.return_value = MagicMock()
        
        manager = EndpointManager(
            dispatcher_manager=mock_dispatcher_manager,
            auth=mock_auth,
            prometheus_url="http://prometheus:9090"
        )
        
        assert manager.timeout == 600  # Default value

    def test_endpoint_manager_dispatcher_calls(self):
        """Test EndpointManager calls all required dispatcher methods"""
        mock_dispatcher_manager = MagicMock()
        mock_auth = MagicMock()
        
        # Mock dispatcher methods that are actually called
        mock_dispatcher_manager.dispatch_global_service.return_value = MagicMock()
        mock_dispatcher_manager.dispatch_socket.return_value = MagicMock()
        mock_dispatcher_manager.dispatch_flow_service.return_value = MagicMock()
        mock_dispatcher_manager.dispatch_flow_import.return_value = MagicMock()
        mock_dispatcher_manager.dispatch_flow_export.return_value = MagicMock()
        mock_dispatcher_manager.dispatch_core_import.return_value = MagicMock()
        mock_dispatcher_manager.dispatch_core_export.return_value = MagicMock()
        
        EndpointManager(
            dispatcher_manager=mock_dispatcher_manager,
            auth=mock_auth,
            prometheus_url="http://test:9090"
        )
        
        # Verify all dispatcher methods were called during initialization
        mock_dispatcher_manager.dispatch_global_service.assert_called_once()
        mock_dispatcher_manager.dispatch_socket.assert_called()  # Called twice
        mock_dispatcher_manager.dispatch_flow_service.assert_called_once()
        mock_dispatcher_manager.dispatch_flow_import.assert_called_once()
        mock_dispatcher_manager.dispatch_flow_export.assert_called_once()
        mock_dispatcher_manager.dispatch_core_import.assert_called_once()
        mock_dispatcher_manager.dispatch_core_export.assert_called_once()