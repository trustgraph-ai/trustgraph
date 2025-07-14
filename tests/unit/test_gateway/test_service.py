"""
Tests for Gateway Service API
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from aiohttp import web
import pulsar

from trustgraph.gateway.service import Api, run, default_pulsar_host, default_prometheus_url, default_timeout, default_port, default_api_token

# Tests for Gateway Service API


class TestApi:
    """Test cases for Api class"""

    def test_api_initialization_with_defaults(self):
        """Test Api initialization with default values"""
        with patch('pulsar.Client') as mock_client:
            mock_client.return_value = Mock()
            
            api = Api()
            
            assert api.port == default_port
            assert api.timeout == default_timeout
            assert api.pulsar_host == default_pulsar_host
            assert api.pulsar_api_key is None
            assert api.prometheus_url == default_prometheus_url + "/"
            assert api.auth.allow_all is True
            
            # Verify Pulsar client was created without API key
            mock_client.assert_called_once_with(
                default_pulsar_host,
                listener_name=None
            )

    def test_api_initialization_with_custom_config(self):
        """Test Api initialization with custom configuration"""
        config = {
            "port": 9000,
            "timeout": 300,
            "pulsar_host": "pulsar://custom-host:6650",
            "pulsar_api_key": "test-api-key",
            "pulsar_listener": "custom-listener",
            "prometheus_url": "http://custom-prometheus:9090",
            "api_token": "secret-token"
        }
        
        with patch('pulsar.Client') as mock_client, \
             patch('pulsar.AuthenticationToken') as mock_auth:
            mock_client.return_value = Mock()
            mock_auth.return_value = Mock()
            
            api = Api(**config)
            
            assert api.port == 9000
            assert api.timeout == 300
            assert api.pulsar_host == "pulsar://custom-host:6650"
            assert api.pulsar_api_key == "test-api-key"
            assert api.prometheus_url == "http://custom-prometheus:9090/"
            assert api.auth.token == "secret-token"
            assert api.auth.allow_all is False
            
            # Verify Pulsar client was created with API key
            mock_auth.assert_called_once_with("test-api-key")
            mock_client.assert_called_once_with(
                "pulsar://custom-host:6650",
                listener_name="custom-listener",
                authentication=mock_auth.return_value
            )

    def test_api_initialization_with_pulsar_api_key(self):
        """Test Api initialization with Pulsar API key authentication"""
        with patch('pulsar.Client') as mock_client, \
             patch('pulsar.AuthenticationToken') as mock_auth:
            mock_client.return_value = Mock()
            mock_auth.return_value = Mock()
            
            api = Api(pulsar_api_key="test-key")
            
            mock_auth.assert_called_once_with("test-key")
            mock_client.assert_called_once_with(
                default_pulsar_host,
                listener_name=None,
                authentication=mock_auth.return_value
            )

    def test_api_initialization_prometheus_url_normalization(self):
        """Test that prometheus_url gets normalized with trailing slash"""
        with patch('pulsar.Client') as mock_client:
            mock_client.return_value = Mock()
            
            # Test URL without trailing slash
            api = Api(prometheus_url="http://prometheus:9090")
            assert api.prometheus_url == "http://prometheus:9090/"
            
            # Test URL with trailing slash
            api = Api(prometheus_url="http://prometheus:9090/")
            assert api.prometheus_url == "http://prometheus:9090/"

    def test_api_initialization_empty_api_token_means_no_auth(self):
        """Test that empty API token results in allow_all authentication"""
        with patch('pulsar.Client') as mock_client:
            mock_client.return_value = Mock()
            
            api = Api(api_token="")
            assert api.auth.allow_all is True

    def test_api_initialization_none_api_token_means_no_auth(self):
        """Test that None API token results in allow_all authentication"""
        with patch('pulsar.Client') as mock_client:
            mock_client.return_value = Mock()
            
            api = Api(api_token=None)
            assert api.auth.allow_all is True

    @pytest.mark.asyncio
    async def test_app_factory_creates_application(self):
        """Test that app_factory creates aiohttp application"""
        with patch('pulsar.Client') as mock_client:
            mock_client.return_value = Mock()
            
            api = Api()
            
            # Mock the dependencies
            api.config_receiver = Mock()
            api.config_receiver.start = AsyncMock()
            api.endpoint_manager = Mock()
            api.endpoint_manager.add_routes = Mock()
            api.endpoint_manager.start = AsyncMock()
            
            app = await api.app_factory()
            
            assert isinstance(app, web.Application)
            assert app._client_max_size == 256 * 1024 * 1024
            
            # Verify that config receiver was started
            api.config_receiver.start.assert_called_once()
            
            # Verify that endpoint manager was configured
            api.endpoint_manager.add_routes.assert_called_once_with(app)
            api.endpoint_manager.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_app_factory_with_custom_endpoints(self):
        """Test app_factory with custom endpoints"""
        with patch('pulsar.Client') as mock_client:
            mock_client.return_value = Mock()
            
            api = Api()
            
            # Mock custom endpoints
            mock_endpoint1 = Mock()
            mock_endpoint1.add_routes = Mock()
            mock_endpoint1.start = AsyncMock()
            
            mock_endpoint2 = Mock()
            mock_endpoint2.add_routes = Mock()
            mock_endpoint2.start = AsyncMock()
            
            api.endpoints = [mock_endpoint1, mock_endpoint2]
            
            # Mock the dependencies
            api.config_receiver = Mock()
            api.config_receiver.start = AsyncMock()
            api.endpoint_manager = Mock()
            api.endpoint_manager.add_routes = Mock()
            api.endpoint_manager.start = AsyncMock()
            
            app = await api.app_factory()
            
            # Verify custom endpoints were configured
            mock_endpoint1.add_routes.assert_called_once_with(app)
            mock_endpoint1.start.assert_called_once()
            mock_endpoint2.add_routes.assert_called_once_with(app)
            mock_endpoint2.start.assert_called_once()

    def test_run_method_calls_web_run_app(self):
        """Test that run method calls web.run_app"""
        with patch('pulsar.Client') as mock_client, \
             patch('aiohttp.web.run_app') as mock_run_app:
            mock_client.return_value = Mock()
            
            api = Api(port=8080)
            api.run()
            
            # Verify run_app was called once with the correct port
            mock_run_app.assert_called_once()
            args, kwargs = mock_run_app.call_args
            assert len(args) == 1  # Should have one positional arg (the coroutine)
            assert kwargs == {'port': 8080}  # Should have port keyword arg

    def test_api_components_initialization(self):
        """Test that all API components are properly initialized"""
        with patch('pulsar.Client') as mock_client:
            mock_client.return_value = Mock()
            
            api = Api()
            
            # Verify all components are initialized
            assert api.config_receiver is not None
            assert api.dispatcher_manager is not None
            assert api.endpoint_manager is not None
            assert api.endpoints == []
            
            # Verify component relationships
            assert api.dispatcher_manager.pulsar_client == api.pulsar_client
            assert api.dispatcher_manager.config_receiver == api.config_receiver
            assert api.endpoint_manager.dispatcher_manager == api.dispatcher_manager
            # EndpointManager doesn't store auth directly, it passes it to individual endpoints


class TestRunFunction:
    """Test cases for the run() function"""

    @patch('trustgraph.gateway.service.Api')
    @patch('trustgraph.gateway.service.start_http_server')
    @patch('argparse.ArgumentParser.parse_args')
    def test_run_function_with_metrics_enabled(self, mock_parse_args, mock_start_http_server, mock_api):
        """Test run function with metrics enabled"""
        # Mock command line arguments
        mock_args = Mock()
        mock_args.metrics = True
        mock_args.metrics_port = 8000
        mock_parse_args.return_value = mock_args
        
        # Mock the Api instance and its run method
        mock_api_instance = Mock()
        mock_api_instance.run = Mock()
        mock_api.return_value = mock_api_instance
        
        # Mock vars() to return a dict
        with patch('builtins.vars') as mock_vars:
            mock_vars.return_value = {
                'metrics': True,
                'metrics_port': 8000,
                'pulsar_host': default_pulsar_host,
                'timeout': default_timeout
            }
            
            run()
            
            # Verify metrics server was started
            mock_start_http_server.assert_called_once_with(8000)
            
            # Verify Api was created and run was called
            mock_api.assert_called_once()
            mock_api_instance.run.assert_called_once()

    @patch('trustgraph.gateway.service.Api')
    @patch('trustgraph.gateway.service.start_http_server')
    @patch('argparse.ArgumentParser.parse_args')
    def test_run_function_with_metrics_disabled(self, mock_parse_args, mock_start_http_server, mock_api):
        """Test run function with metrics disabled"""
        # Mock command line arguments
        mock_args = Mock()
        mock_args.metrics = False
        mock_parse_args.return_value = mock_args
        
        # Mock the Api instance and its run method
        mock_api_instance = Mock()
        mock_api_instance.run = Mock()
        mock_api.return_value = mock_api_instance
        
        # Mock vars() to return a dict
        with patch('builtins.vars') as mock_vars:
            mock_vars.return_value = {
                'metrics': False,
                'metrics_port': 8000,
                'pulsar_host': default_pulsar_host,
                'timeout': default_timeout
            }
            
            run()
            
            # Verify metrics server was NOT started
            mock_start_http_server.assert_not_called()
            
            # Verify Api was created and run was called
            mock_api.assert_called_once()
            mock_api_instance.run.assert_called_once()

    @patch('trustgraph.gateway.service.Api')
    @patch('argparse.ArgumentParser.parse_args')
    def test_run_function_argument_parsing(self, mock_parse_args, mock_api):
        """Test that run function properly parses command line arguments"""
        # Mock command line arguments
        mock_args = Mock()
        mock_args.metrics = False
        mock_parse_args.return_value = mock_args
        
        # Mock the Api instance and its run method
        mock_api_instance = Mock()
        mock_api_instance.run = Mock()
        mock_api.return_value = mock_api_instance
        
        # Mock vars() to return a dict with all expected arguments
        expected_args = {
            'pulsar_host': 'pulsar://test:6650',
            'pulsar_api_key': 'test-key',
            'pulsar_listener': 'test-listener',
            'prometheus_url': 'http://test-prometheus:9090',
            'port': 9000,
            'timeout': 300,
            'api_token': 'secret',
            'log_level': 'INFO',
            'metrics': False,
            'metrics_port': 8001
        }
        
        with patch('builtins.vars') as mock_vars:
            mock_vars.return_value = expected_args
            
            run()
            
            # Verify Api was created with the parsed arguments
            mock_api.assert_called_once_with(**expected_args)
            mock_api_instance.run.assert_called_once()

    def test_run_function_creates_argument_parser(self):
        """Test that run function creates argument parser with correct arguments"""
        with patch('argparse.ArgumentParser') as mock_parser_class:
            mock_parser = Mock()
            mock_parser_class.return_value = mock_parser
            mock_parser.parse_args.return_value = Mock(metrics=False)
            
            with patch('trustgraph.gateway.service.Api') as mock_api, \
                 patch('builtins.vars') as mock_vars:
                mock_vars.return_value = {'metrics': False}
                mock_api.return_value = Mock()
                
                run()
                
                # Verify ArgumentParser was created
                mock_parser_class.assert_called_once()
                
                # Verify add_argument was called for each expected argument
                expected_arguments = [
                    'pulsar-host', 'pulsar-api-key', 'pulsar-listener',
                    'prometheus-url', 'port', 'timeout', 'api-token',
                    'log-level', 'metrics', 'metrics-port'
                ]
                
                # Check that add_argument was called multiple times (once for each arg)
                assert mock_parser.add_argument.call_count >= len(expected_arguments)