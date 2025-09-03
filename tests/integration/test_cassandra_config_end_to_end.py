"""
End-to-end integration tests for Cassandra configuration.

Tests complete configuration flow from environment variables
through processors to Cassandra connections.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from argparse import ArgumentParser

# Import processors that use Cassandra configuration
from trustgraph.storage.triples.cassandra.write import Processor as TriplesWriter
from trustgraph.storage.objects.cassandra.write import Processor as ObjectsWriter
from trustgraph.query.triples.cassandra.service import Processor as TriplesQuery
from trustgraph.storage.knowledge.store import Processor as KgStore


class TestEndToEndConfigurationFlow:
    """Test complete configuration flow from environment to processors."""
    
    @pytest.mark.asyncio
    @patch('trustgraph.direct.cassandra.Cluster')
    async def test_triples_writer_env_to_connection(self, mock_cluster):
        """Test complete flow from environment variables to TrustGraph connection."""
        env_vars = {
            'CASSANDRA_HOST': 'integration-host1,integration-host2,integration-host3',
            'CASSANDRA_USERNAME': 'integration-user',
            'CASSANDRA_PASSWORD': 'integration-pass'
        }
        
        mock_cluster_instance = MagicMock()
        mock_session = MagicMock()
        mock_cluster_instance.connect.return_value = mock_session
        mock_cluster.return_value = mock_cluster_instance
        
        with patch.dict(os.environ, env_vars, clear=True):
            processor = TriplesWriter(taskgroup=MagicMock())
            
            # Create a mock message to trigger TrustGraph creation
            mock_message = MagicMock()
            mock_message.metadata.user = 'test_user'
            mock_message.metadata.collection = 'test_collection'
            mock_message.triples = []
            
            # This should create TrustGraph with environment config
            await processor.store_triples(mock_message)
            
            # Verify Cluster was created with correct hosts
            mock_cluster.assert_called_once()
            call_args = mock_cluster.call_args
            assert call_args.args[0] == ['integration-host1', 'integration-host2', 'integration-host3']
            assert 'auth_provider' in call_args.kwargs  # Should have auth since credentials provided
    
    @patch('trustgraph.storage.objects.cassandra.write.Cluster')
    @patch('trustgraph.storage.objects.cassandra.write.PlainTextAuthProvider')
    def test_objects_writer_env_to_cluster_connection(self, mock_auth_provider, mock_cluster):
        """Test complete flow from environment variables to Cassandra Cluster connection."""
        env_vars = {
            'CASSANDRA_HOST': 'obj-host1,obj-host2',
            'CASSANDRA_USERNAME': 'obj-user',
            'CASSANDRA_PASSWORD': 'obj-pass'
        }
        
        mock_auth_instance = MagicMock()
        mock_auth_provider.return_value = mock_auth_instance
        mock_cluster_instance = MagicMock()
        mock_session = MagicMock()
        mock_cluster_instance.connect.return_value = mock_session
        mock_cluster.return_value = mock_cluster_instance
        
        with patch.dict(os.environ, env_vars, clear=True):
            processor = ObjectsWriter(taskgroup=MagicMock())
            
            # Trigger Cassandra connection
            processor.connect_cassandra()
            
            # Verify auth provider was created with env vars
            mock_auth_provider.assert_called_once_with(
                username='obj-user',
                password='obj-pass'
            )
            
            # Verify cluster was created with hosts from env and auth
            mock_cluster.assert_called_once()
            call_args = mock_cluster.call_args
            assert call_args.kwargs['contact_points'] == ['obj-host1', 'obj-host2']
            assert call_args.kwargs['auth_provider'] == mock_auth_instance
    
    @pytest.mark.asyncio
    @patch('trustgraph.storage.knowledge.store.KnowledgeTableStore')
    async def test_kg_store_env_to_table_store(self, mock_table_store):
        """Test complete flow from environment variables to KnowledgeTableStore."""
        env_vars = {
            'CASSANDRA_HOST': 'kg-host1,kg-host2,kg-host3,kg-host4',
            'CASSANDRA_USERNAME': 'kg-user',
            'CASSANDRA_PASSWORD': 'kg-pass'
        }
        
        mock_store_instance = MagicMock()
        mock_table_store.return_value = mock_store_instance
        
        with patch.dict(os.environ, env_vars, clear=True):
            processor = KgStore(taskgroup=MagicMock())
            
            # Verify KnowledgeTableStore was created with env config
            mock_table_store.assert_called_once_with(
                cassandra_host=['kg-host1', 'kg-host2', 'kg-host3', 'kg-host4'],
                cassandra_user='kg-user',
                cassandra_password='kg-pass',
                keyspace='knowledge'
            )


class TestConfigurationPriorityEndToEnd:
    """Test configuration priority chains end-to-end."""
    
    @pytest.mark.asyncio
    @patch('trustgraph.direct.cassandra.Cluster')
    async def test_cli_override_env_end_to_end(self, mock_cluster):
        """Test that CLI parameters override environment variables end-to-end."""
        env_vars = {
            'CASSANDRA_HOST': 'env-host',
            'CASSANDRA_USERNAME': 'env-user',
            'CASSANDRA_PASSWORD': 'env-pass'
        }
        
        mock_cluster_instance = MagicMock()
        mock_session = MagicMock()
        mock_cluster_instance.connect.return_value = mock_session
        mock_cluster.return_value = mock_cluster_instance
        
        with patch.dict(os.environ, env_vars, clear=True):
            # CLI parameters should override environment
            processor = TriplesWriter(
                taskgroup=MagicMock(),
                cassandra_host='cli-host1,cli-host2',
                cassandra_username='cli-user',
                cassandra_password='cli-pass'
            )
            
            # Trigger TrustGraph creation
            mock_message = MagicMock()
            mock_message.metadata.user = 'test_user'
            mock_message.metadata.collection = 'test_collection'
            mock_message.triples = []
            
            await processor.store_triples(mock_message)
            
            # Should use CLI parameters, not environment
            mock_cluster.assert_called_once()
            call_args = mock_cluster.call_args
            assert call_args.args[0] == ['cli-host1', 'cli-host2']  # From CLI
            assert 'auth_provider' in call_args.kwargs  # Should have auth since credentials provided
    
    @pytest.mark.asyncio
    @patch('trustgraph.storage.knowledge.store.KnowledgeTableStore')
    async def test_partial_cli_with_env_fallback_end_to_end(self, mock_table_store):
        """Test partial CLI parameters with environment fallback end-to-end."""
        env_vars = {
            'CASSANDRA_HOST': 'fallback-host1,fallback-host2',
            'CASSANDRA_USERNAME': 'fallback-user',
            'CASSANDRA_PASSWORD': 'fallback-pass'
        }
        
        mock_store_instance = MagicMock()
        mock_table_store.return_value = mock_store_instance
        
        with patch.dict(os.environ, env_vars, clear=True):
            # Only provide host via parameter, rest should fall back to env
            processor = KgStore(
                taskgroup=MagicMock(),
                cassandra_host='partial-host'
                # username and password not provided - should use env
            )
            
            # Verify mixed configuration
            mock_table_store.assert_called_once_with(
                cassandra_host=['partial-host'],     # From parameter
                cassandra_user='fallback-user',      # From environment
                cassandra_password='fallback-pass',  # From environment
                keyspace='knowledge'
            )
    
    @pytest.mark.asyncio
    @patch('trustgraph.direct.cassandra.Cluster')
    async def test_no_config_defaults_end_to_end(self, mock_cluster):
        """Test that defaults are used when no configuration provided end-to-end."""
        mock_cluster_instance = MagicMock()
        mock_session = MagicMock()
        mock_cluster_instance.connect.return_value = mock_session
        mock_cluster.return_value = mock_cluster_instance
        
        with patch.dict(os.environ, {}, clear=True):
            processor = TriplesQuery(taskgroup=MagicMock())
            
            # Mock query to trigger TrustGraph creation
            mock_query = MagicMock()
            mock_query.user = 'default_user'
            mock_query.collection = 'default_collection'
            mock_query.s = None
            mock_query.p = None
            mock_query.o = None
            mock_query.limit = 100
            
            # Mock the get_all method to return empty list
            mock_tg_instance = MagicMock()
            mock_tg_instance.get_all.return_value = []
            processor.tg = mock_tg_instance
            
            await processor.query_triples(mock_query)
            
            # Should use defaults
            mock_cluster.assert_called_once()
            call_args = mock_cluster.call_args
            assert call_args.args[0] == ['cassandra']  # Default host
            assert 'auth_provider' not in call_args.kwargs  # No auth with default config


class TestNoBackwardCompatibilityEndToEnd:
    """Test that backward compatibility with old parameter names is removed."""
    
    @pytest.mark.asyncio
    @patch('trustgraph.direct.cassandra.Cluster')
    async def test_old_graph_params_no_longer_work_end_to_end(self, mock_cluster):
        """Test that old graph_* parameters no longer work end-to-end."""
        mock_cluster_instance = MagicMock()
        mock_session = MagicMock()
        mock_cluster_instance.connect.return_value = mock_session
        mock_cluster.return_value = mock_cluster_instance
        
        # Use old parameter names (should be ignored)
        processor = TriplesWriter(
            taskgroup=MagicMock(),
            graph_host='legacy-host',
            graph_username='legacy-user',
            graph_password='legacy-pass'
        )
        
        # Trigger TrustGraph creation
        mock_message = MagicMock()
        mock_message.metadata.user = 'legacy_user'
        mock_message.metadata.collection = 'legacy_collection'
        mock_message.triples = []
        
        await processor.store_triples(mock_message)
        
        # Should use defaults since old parameters are not recognized
        mock_cluster.assert_called_once()
        call_args = mock_cluster.call_args
        assert call_args.args[0] == ['cassandra']  # Default, not legacy-host
        assert 'auth_provider' not in call_args.kwargs  # No auth since no valid credentials
    
    @patch('trustgraph.storage.knowledge.store.KnowledgeTableStore')
    def test_old_cassandra_user_param_still_works_end_to_end(self, mock_table_store):
        """Test that old cassandra_user parameter still works end-to-end."""
        mock_store_instance = MagicMock()
        mock_table_store.return_value = mock_store_instance
        
        # Use old cassandra_user parameter
        processor = KgStore(
            taskgroup=MagicMock(),
            cassandra_host='legacy-kg-host',
            cassandra_user='legacy-kg-user',  # Old parameter name
            cassandra_password='legacy-kg-pass'
        )
        
        # Should work with old parameter name
        mock_table_store.assert_called_once_with(
            cassandra_host=['legacy-kg-host'],
            cassandra_user='legacy-kg-user',
            cassandra_password='legacy-kg-pass',
            keyspace='knowledge'
        )
    
    @pytest.mark.asyncio
    @patch('trustgraph.direct.cassandra.Cluster')
    async def test_new_params_override_old_params_end_to_end(self, mock_cluster):
        """Test that new parameters override old ones when both are present end-to-end."""
        mock_cluster_instance = MagicMock()
        mock_session = MagicMock()
        mock_cluster_instance.connect.return_value = mock_session
        mock_cluster.return_value = mock_cluster_instance
        
        # Provide both old and new parameters
        processor = TriplesWriter(
            taskgroup=MagicMock(),
            cassandra_host='new-host',
            graph_host='old-host',          # Should be ignored
            cassandra_username='new-user',
            graph_username='old-user',      # Should be ignored
            cassandra_password='new-pass',
            graph_password='old-pass'       # Should be ignored
        )
        
        # Trigger TrustGraph creation
        mock_message = MagicMock()
        mock_message.metadata.user = 'precedence_user'
        mock_message.metadata.collection = 'precedence_collection'
        mock_message.triples = []
        
        await processor.store_triples(mock_message)
        
        # Should use new parameters, not old ones
        mock_cluster.assert_called_once()
        call_args = mock_cluster.call_args
        assert call_args.args[0] == ['new-host']    # New parameter wins
        assert 'auth_provider' in call_args.kwargs  # Should have auth since credentials provided


class TestMultipleHostsHandling:
    """Test multiple Cassandra hosts handling end-to-end."""
    
    @patch('trustgraph.storage.objects.cassandra.write.Cluster')
    def test_multiple_hosts_passed_to_cluster(self, mock_cluster):
        """Test that multiple hosts are correctly passed to Cassandra cluster."""
        env_vars = {
            'CASSANDRA_HOST': 'host1,host2,host3,host4,host5'
        }
        
        mock_cluster_instance = MagicMock()
        mock_session = MagicMock()
        mock_cluster_instance.connect.return_value = mock_session
        mock_cluster.return_value = mock_cluster_instance
        
        with patch.dict(os.environ, env_vars, clear=True):
            processor = ObjectsWriter(taskgroup=MagicMock())
            processor.connect_cassandra()
            
            # Verify all hosts were passed to Cluster
            mock_cluster.assert_called_once()
            call_args = mock_cluster.call_args
            assert call_args.kwargs['contact_points'] == ['host1', 'host2', 'host3', 'host4', 'host5']
    
    @pytest.mark.asyncio
    @patch('trustgraph.direct.cassandra.Cluster')
    async def test_single_host_converted_to_list(self, mock_cluster):
        """Test that single host is converted to list for TrustGraph."""
        mock_cluster_instance = MagicMock()
        mock_session = MagicMock()
        mock_cluster_instance.connect.return_value = mock_session
        mock_cluster.return_value = mock_cluster_instance
        
        processor = TriplesWriter(taskgroup=MagicMock(), cassandra_host='single-host')
        
        # Trigger TrustGraph creation
        mock_message = MagicMock()
        mock_message.metadata.user = 'single_user'
        mock_message.metadata.collection = 'single_collection'
        mock_message.triples = []
        
        await processor.store_triples(mock_message)
        
        # Single host should be converted to list
        mock_cluster.assert_called_once()
        call_args = mock_cluster.call_args
        assert call_args.args[0] == ['single-host']  # Converted to list
        assert 'auth_provider' not in call_args.kwargs  # No auth since no credentials provided
    
    def test_whitespace_handling_in_host_list(self):
        """Test that whitespace in host lists is handled correctly."""
        from trustgraph.base.cassandra_config import resolve_cassandra_config
        
        # Test various whitespace scenarios
        hosts1, _, _ = resolve_cassandra_config(host='host1, host2 ,  host3')
        assert hosts1 == ['host1', 'host2', 'host3']
        
        hosts2, _, _ = resolve_cassandra_config(host='host1,host2,host3,')
        assert hosts2 == ['host1', 'host2', 'host3']
        
        hosts3, _, _ = resolve_cassandra_config(host='  host1  ,  host2  ')
        assert hosts3 == ['host1', 'host2']


class TestAuthenticationFlow:
    """Test authentication configuration flow end-to-end."""
    
    @patch('trustgraph.storage.objects.cassandra.write.Cluster')
    @patch('trustgraph.storage.objects.cassandra.write.PlainTextAuthProvider')
    def test_authentication_enabled_when_both_credentials_provided(self, mock_auth_provider, mock_cluster):
        """Test that authentication is enabled when both username and password are provided."""
        env_vars = {
            'CASSANDRA_HOST': 'auth-host',
            'CASSANDRA_USERNAME': 'auth-user',
            'CASSANDRA_PASSWORD': 'auth-secret'
        }
        
        mock_auth_instance = MagicMock()
        mock_auth_provider.return_value = mock_auth_instance
        mock_cluster_instance = MagicMock()
        mock_cluster.return_value = mock_cluster_instance
        
        with patch.dict(os.environ, env_vars, clear=True):
            processor = ObjectsWriter(taskgroup=MagicMock())
            processor.connect_cassandra()
            
            # Auth provider should be created
            mock_auth_provider.assert_called_once_with(
                username='auth-user',
                password='auth-secret'
            )
            
            # Cluster should be created with auth provider
            call_args = mock_cluster.call_args
            assert 'auth_provider' in call_args.kwargs
            assert call_args.kwargs['auth_provider'] == mock_auth_instance
    
    @patch('trustgraph.storage.objects.cassandra.write.Cluster')
    @patch('trustgraph.storage.objects.cassandra.write.PlainTextAuthProvider')
    def test_no_authentication_when_credentials_missing(self, mock_auth_provider, mock_cluster):
        """Test that authentication is not used when credentials are missing."""
        env_vars = {
            'CASSANDRA_HOST': 'no-auth-host'
            # No username/password
        }
        
        mock_cluster_instance = MagicMock()
        mock_cluster.return_value = mock_cluster_instance
        
        with patch.dict(os.environ, env_vars, clear=True):
            processor = ObjectsWriter(taskgroup=MagicMock())
            processor.connect_cassandra()
            
            # Auth provider should not be created
            mock_auth_provider.assert_not_called()
            
            # Cluster should be created without auth provider
            call_args = mock_cluster.call_args
            assert 'auth_provider' not in call_args.kwargs
    
    @patch('trustgraph.storage.objects.cassandra.write.Cluster')
    @patch('trustgraph.storage.objects.cassandra.write.PlainTextAuthProvider')
    def test_no_authentication_when_only_username_provided(self, mock_auth_provider, mock_cluster):
        """Test that authentication is not used when only username is provided."""
        processor = ObjectsWriter(
            taskgroup=MagicMock(),
            cassandra_host='partial-auth-host',
            cassandra_username='partial-user'
            # No password
        )
        
        mock_cluster_instance = MagicMock()
        mock_cluster.return_value = mock_cluster_instance
        
        processor.connect_cassandra()
        
        # Auth provider should not be created (needs both username AND password)
        mock_auth_provider.assert_not_called()
        
        # Cluster should be created without auth provider
        call_args = mock_cluster.call_args
        assert 'auth_provider' not in call_args.kwargs