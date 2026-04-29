"""
Tests for Gateway Endpoint Manager
"""

import pytest
from unittest.mock import MagicMock

from trustgraph.gateway.endpoint.manager import EndpointManager


class TestEndpointManager:
    """Test cases for EndpointManager class"""

    def test_endpoint_manager_initialization(self):
        """EndpointManager wires up the full endpoint set and
        records dispatcher_manager / timeout on the instance."""
        mock_dispatcher_manager = MagicMock()
        mock_auth = MagicMock()

        # The dispatcher_manager exposes a small set of factory
        # methods — MagicMock auto-creates them, returning fresh
        # MagicMocks on each call.
        manager = EndpointManager(
            dispatcher_manager=mock_dispatcher_manager,
            auth=mock_auth,
            prometheus_url="http://prometheus:9090",
            timeout=300,
        )

        assert manager.dispatcher_manager == mock_dispatcher_manager
        assert manager.timeout == 300
        assert len(manager.endpoints) > 0

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
        
        # Each dispatcher factory is invoked once per endpoint that
        # needs a dedicated wire.  dispatch_auth_iam is shared by
        # two endpoints — AuthEndpoints (login / bootstrap /
        # change-password) and IamEndpoint (registry-driven
        # /api/v1/iam) — so it's expected to be called twice.
        # Both forwarders pin the dispatcher to kind=iam and reuse
        # the same factory; they're distinct from
        # dispatch_global_service (the generic /api/v1/{kind} route).
        mock_dispatcher_manager.dispatch_global_service.assert_called_once()
        assert mock_dispatcher_manager.dispatch_auth_iam.call_count == 2
        mock_dispatcher_manager.dispatch_socket.assert_called_once()
        mock_dispatcher_manager.dispatch_flow_service.assert_called_once()
        mock_dispatcher_manager.dispatch_flow_import.assert_called_once()
        mock_dispatcher_manager.dispatch_flow_export.assert_called_once()
        mock_dispatcher_manager.dispatch_core_import.assert_called_once()
        mock_dispatcher_manager.dispatch_core_export.assert_called_once()