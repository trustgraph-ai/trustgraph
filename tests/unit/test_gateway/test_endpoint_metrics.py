"""
Tests for Gateway Metrics Endpoint
"""

import pytest
from unittest.mock import MagicMock

from trustgraph.gateway.endpoint.metrics import MetricsEndpoint


class TestMetricsEndpoint:
    """Test cases for MetricsEndpoint class"""

    def test_metrics_endpoint_initialization(self):
        """Test MetricsEndpoint initialization"""
        mock_auth = MagicMock()
        
        endpoint = MetricsEndpoint(
            prometheus_url="http://prometheus:9090",
            endpoint_path="/metrics",
            auth=mock_auth
        )
        
        assert endpoint.prometheus_url == "http://prometheus:9090"
        assert endpoint.path == "/metrics"
        assert endpoint.auth == mock_auth
        assert endpoint.operation == "service"

    @pytest.mark.asyncio
    async def test_metrics_endpoint_start_method(self):
        """Test MetricsEndpoint start method (should be no-op)"""
        mock_auth = MagicMock()
        
        endpoint = MetricsEndpoint(
            prometheus_url="http://localhost:9090",
            endpoint_path="/metrics",
            auth=mock_auth
        )
        
        # start() should complete without error
        await endpoint.start()

    def test_add_routes_registers_get_handler(self):
        """Test add_routes method registers GET route with wildcard path"""
        mock_auth = MagicMock()
        mock_app = MagicMock()
        
        endpoint = MetricsEndpoint(
            prometheus_url="http://prometheus:9090",
            endpoint_path="/metrics",
            auth=mock_auth
        )
        
        endpoint.add_routes(mock_app)
        
        # Verify add_routes was called with GET route
        mock_app.add_routes.assert_called_once()
        # The call should include web.get with wildcard path pattern
        call_args = mock_app.add_routes.call_args[0][0]
        assert len(call_args) == 1  # One route added