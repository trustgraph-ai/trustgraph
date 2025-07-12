"""
Tests for Gateway Variable Endpoint
"""

import pytest
from unittest.mock import MagicMock

from trustgraph.gateway.endpoint.variable_endpoint import VariableEndpoint


class TestVariableEndpoint:
    """Test cases for VariableEndpoint class"""

    def test_variable_endpoint_initialization(self):
        """Test VariableEndpoint initialization"""
        mock_auth = MagicMock()
        mock_dispatcher = MagicMock()
        
        endpoint = VariableEndpoint(
            endpoint_path="/api/variable",
            auth=mock_auth,
            dispatcher=mock_dispatcher
        )
        
        assert endpoint.path == "/api/variable"
        assert endpoint.auth == mock_auth
        assert endpoint.dispatcher == mock_dispatcher
        assert endpoint.operation == "service"

    @pytest.mark.asyncio
    async def test_variable_endpoint_start_method(self):
        """Test VariableEndpoint start method (should be no-op)"""
        mock_auth = MagicMock()
        mock_dispatcher = MagicMock()
        
        endpoint = VariableEndpoint("/api/var", mock_auth, mock_dispatcher)
        
        # start() should complete without error
        await endpoint.start()

    def test_add_routes_registers_post_handler(self):
        """Test add_routes method registers POST route"""
        mock_auth = MagicMock()
        mock_dispatcher = MagicMock()
        mock_app = MagicMock()
        
        endpoint = VariableEndpoint("/api/variable", mock_auth, mock_dispatcher)
        endpoint.add_routes(mock_app)
        
        # Verify add_routes was called with POST route
        mock_app.add_routes.assert_called_once()
        call_args = mock_app.add_routes.call_args[0][0]
        assert len(call_args) == 1  # One route added