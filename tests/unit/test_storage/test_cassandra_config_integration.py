"""
Integration tests for Cassandra configuration in processors.

Tests that processors correctly use the configuration helper
and handle environment variables, CLI args, and backward compatibility.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock

from trustgraph.storage.triples.cassandra.write import Processor as TriplesWriter
from trustgraph.storage.objects.cassandra.write import Processor as ObjectsWriter
from trustgraph.query.triples.cassandra.service import Processor as TriplesQuery
from trustgraph.storage.knowledge.store import Processor as KgStore


class TestTriplesWriterConfiguration:
    """Test Cassandra configuration in triples writer processor."""
    
    @patch('trustgraph.direct.cassandra.TrustGraph')
    def test_environment_variable_configuration(self, mock_trust_graph):
        """Test processor picks up configuration from environment variables."""
        env_vars = {
            'CASSANDRA_HOST': 'env-host1,env-host2',
            'CASSANDRA_USERNAME': 'env-user',
            'CASSANDRA_PASSWORD': 'env-pass'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            processor = TriplesWriter()
            
            assert processor.graph_host == ['env-host1', 'env-host2']
            assert processor.username == 'env-user'
            assert processor.password == 'env-pass'
    
    @patch('trustgraph.direct.cassandra.TrustGraph')
    def test_parameter_override_environment(self, mock_trust_graph):
        """Test explicit parameters override environment variables."""
        env_vars = {
            'CASSANDRA_HOST': 'env-host',
            'CASSANDRA_USERNAME': 'env-user',
            'CASSANDRA_PASSWORD': 'env-pass'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            processor = TriplesWriter(
                cassandra_host='param-host1,param-host2',
                cassandra_username='param-user',
                cassandra_password='param-pass'
            )
            
            assert processor.graph_host == ['param-host1', 'param-host2']
            assert processor.username == 'param-user'
            assert processor.password == 'param-pass'
    
    @patch('trustgraph.direct.cassandra.TrustGraph')
    def test_backward_compatibility_graph_params(self, mock_trust_graph):
        """Test backward compatibility with old graph_* parameter names."""
        processor = TriplesWriter(
            graph_host='compat-host',
            graph_username='compat-user',
            graph_password='compat-pass'
        )
        
        assert processor.graph_host == ['compat-host']
        assert processor.username == 'compat-user'
        assert processor.password == 'compat-pass'
    
    @patch('trustgraph.direct.cassandra.TrustGraph')
    def test_default_configuration(self, mock_trust_graph):
        """Test default configuration when no params or env vars provided."""
        with patch.dict(os.environ, {}, clear=True):
            processor = TriplesWriter()
            
            assert processor.graph_host == ['cassandra']
            assert processor.username is None
            assert processor.password is None


class TestObjectsWriterConfiguration:
    """Test Cassandra configuration in objects writer processor."""
    
    @patch('trustgraph.storage.objects.cassandra.write.Cluster')
    def test_environment_variable_configuration(self, mock_cluster):
        """Test processor picks up configuration from environment variables."""
        env_vars = {
            'CASSANDRA_HOST': 'obj-env-host1,obj-env-host2',
            'CASSANDRA_USERNAME': 'obj-env-user',
            'CASSANDRA_PASSWORD': 'obj-env-pass'
        }
        
        mock_cluster_instance = MagicMock()
        mock_cluster.return_value = mock_cluster_instance
        
        with patch.dict(os.environ, env_vars, clear=True):
            processor = ObjectsWriter()
            
            assert processor.graph_host == ['obj-env-host1', 'obj-env-host2']
            assert processor.graph_username == 'obj-env-user'
            assert processor.graph_password == 'obj-env-pass'
    
    @patch('trustgraph.storage.objects.cassandra.write.Cluster')
    def test_cassandra_connection_with_hosts_list(self, mock_cluster):
        """Test that Cassandra connection uses hosts list correctly."""
        env_vars = {
            'CASSANDRA_HOST': 'conn-host1,conn-host2,conn-host3',
            'CASSANDRA_USERNAME': 'conn-user',
            'CASSANDRA_PASSWORD': 'conn-pass'
        }
        
        mock_cluster_instance = MagicMock()
        mock_session = MagicMock()
        mock_cluster_instance.connect.return_value = mock_session
        mock_cluster.return_value = mock_cluster_instance
        
        with patch.dict(os.environ, env_vars, clear=True):
            processor = ObjectsWriter()
            processor.connect_cassandra()
            
            # Verify cluster was called with hosts list
            mock_cluster.assert_called_once()
            call_args = mock_cluster.call_args
            
            # Check that contact_points was passed the hosts list
            assert 'contact_points' in call_args.kwargs
            assert call_args.kwargs['contact_points'] == ['conn-host1', 'conn-host2', 'conn-host3']
    
    @patch('trustgraph.storage.objects.cassandra.write.Cluster')
    @patch('trustgraph.storage.objects.cassandra.write.PlainTextAuthProvider')
    def test_authentication_configuration(self, mock_auth_provider, mock_cluster):
        """Test authentication is configured when credentials are provided."""
        env_vars = {
            'CASSANDRA_HOST': 'auth-host',
            'CASSANDRA_USERNAME': 'auth-user',
            'CASSANDRA_PASSWORD': 'auth-pass'
        }
        
        mock_auth_instance = MagicMock()
        mock_auth_provider.return_value = mock_auth_instance
        mock_cluster_instance = MagicMock()
        mock_cluster.return_value = mock_cluster_instance
        
        with patch.dict(os.environ, env_vars, clear=True):
            processor = ObjectsWriter()
            processor.connect_cassandra()
            
            # Verify auth provider was created with correct credentials
            mock_auth_provider.assert_called_once_with(
                username='auth-user',
                password='auth-pass'
            )
            
            # Verify cluster was configured with auth provider
            call_args = mock_cluster.call_args
            assert 'auth_provider' in call_args.kwargs
            assert call_args.kwargs['auth_provider'] == mock_auth_instance


class TestTriplesQueryConfiguration:
    """Test Cassandra configuration in triples query processor."""
    
    @patch('trustgraph.direct.cassandra.TrustGraph')
    def test_environment_variable_configuration(self, mock_trust_graph):
        """Test processor picks up configuration from environment variables."""
        env_vars = {
            'CASSANDRA_HOST': 'query-env-host1,query-env-host2',
            'CASSANDRA_USERNAME': 'query-env-user',
            'CASSANDRA_PASSWORD': 'query-env-pass'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            processor = TriplesQuery()
            
            assert processor.graph_host == ['query-env-host1', 'query-env-host2']
            assert processor.username == 'query-env-user'
            assert processor.password == 'query-env-pass'
    
    @patch('trustgraph.direct.cassandra.TrustGraph')
    def test_mixed_old_new_parameters(self, mock_trust_graph):
        """Test mixing old and new parameter names (new should win)."""
        processor = TriplesQuery(
            cassandra_host='new-host',
            graph_host='old-host',
            cassandra_username='new-user',
            graph_username='old-user'
        )
        
        # New parameters should take precedence
        assert processor.graph_host == ['new-host']
        assert processor.username == 'new-user'


class TestKgStoreConfiguration:
    """Test Cassandra configuration in knowledge store processor."""
    
    @patch('trustgraph.tables.knowledge.KnowledgeTableStore')
    def test_environment_variable_configuration(self, mock_table_store):
        """Test kg-store picks up configuration from environment variables."""
        env_vars = {
            'CASSANDRA_HOST': 'kg-env-host1,kg-env-host2,kg-env-host3',
            'CASSANDRA_USERNAME': 'kg-env-user',
            'CASSANDRA_PASSWORD': 'kg-env-pass'
        }
        
        mock_store_instance = MagicMock()
        mock_table_store.return_value = mock_store_instance
        
        with patch.dict(os.environ, env_vars, clear=True):
            processor = KgStore()
            
            # Verify KnowledgeTableStore was called with resolved config
            mock_table_store.assert_called_once_with(
                cassandra_host=['kg-env-host1', 'kg-env-host2', 'kg-env-host3'],
                cassandra_user='kg-env-user',
                cassandra_password='kg-env-pass',
                keyspace='knowledge'
            )
    
    @patch('trustgraph.tables.knowledge.KnowledgeTableStore')
    def test_explicit_parameters(self, mock_table_store):
        """Test kg-store with explicit parameters."""
        mock_store_instance = MagicMock()
        mock_table_store.return_value = mock_store_instance
        
        processor = KgStore(
            cassandra_host='explicit-host',
            cassandra_username='explicit-user',
            cassandra_password='explicit-pass'
        )
        
        # Verify KnowledgeTableStore was called with explicit config
        mock_table_store.assert_called_once_with(
            cassandra_host=['explicit-host'],
            cassandra_user='explicit-user',
            cassandra_password='explicit-pass',
            keyspace='knowledge'
        )
    
    @patch('trustgraph.tables.knowledge.KnowledgeTableStore')
    def test_backward_compatibility_cassandra_user(self, mock_table_store):
        """Test backward compatibility with cassandra_user parameter."""
        mock_store_instance = MagicMock()
        mock_table_store.return_value = mock_store_instance
        
        processor = KgStore(
            cassandra_host='compat-host',
            cassandra_user='compat-user',  # Old parameter name
            cassandra_password='compat-pass'
        )
        
        # Should still work with old parameter name
        mock_table_store.assert_called_once_with(
            cassandra_host=['compat-host'],
            cassandra_user='compat-user',
            cassandra_password='compat-pass',
            keyspace='knowledge'
        )
    
    @patch('trustgraph.tables.knowledge.KnowledgeTableStore')
    def test_default_configuration(self, mock_table_store):
        """Test kg-store default configuration."""
        mock_store_instance = MagicMock()
        mock_table_store.return_value = mock_store_instance
        
        with patch.dict(os.environ, {}, clear=True):
            processor = KgStore()
            
            # Should use defaults
            mock_table_store.assert_called_once_with(
                cassandra_host=['cassandra'],
                cassandra_user=None,
                cassandra_password=None,
                keyspace='knowledge'
            )


class TestCommandLineArgumentHandling:
    """Test command-line argument parsing in processors."""
    
    def test_triples_writer_add_args(self):
        """Test that triples writer adds standard Cassandra arguments."""
        import argparse
        from trustgraph.storage.triples.cassandra.write import Processor as TriplesWriter
        
        parser = argparse.ArgumentParser()
        TriplesWriter.add_args(parser)
        
        # Parse empty args to check that arguments exist
        args = parser.parse_args([])
        
        assert hasattr(args, 'cassandra_host')
        assert hasattr(args, 'cassandra_username')
        assert hasattr(args, 'cassandra_password')
    
    def test_objects_writer_add_args(self):
        """Test that objects writer adds standard Cassandra arguments."""
        import argparse
        from trustgraph.storage.objects.cassandra.write import Processor as ObjectsWriter
        
        parser = argparse.ArgumentParser()
        ObjectsWriter.add_args(parser)
        
        # Parse empty args to check that arguments exist
        args = parser.parse_args([])
        
        assert hasattr(args, 'cassandra_host')
        assert hasattr(args, 'cassandra_username')
        assert hasattr(args, 'cassandra_password')
        assert hasattr(args, 'config_type')  # Objects writer specific arg
    
    def test_triples_query_add_args(self):
        """Test that triples query adds standard Cassandra arguments."""
        import argparse
        from trustgraph.query.triples.cassandra.service import Processor as TriplesQuery
        
        parser = argparse.ArgumentParser()
        TriplesQuery.add_args(parser)
        
        # Parse empty args to check that arguments exist
        args = parser.parse_args([])
        
        assert hasattr(args, 'cassandra_host')
        assert hasattr(args, 'cassandra_username')
        assert hasattr(args, 'cassandra_password')
    
    def test_kg_store_add_args(self):
        """Test that kg-store now adds Cassandra arguments (previously missing)."""
        import argparse
        from trustgraph.storage.knowledge.store import Processor as KgStore
        
        parser = argparse.ArgumentParser()
        KgStore.add_args(parser)
        
        # Parse empty args to check that arguments exist
        args = parser.parse_args([])
        
        assert hasattr(args, 'cassandra_host')
        assert hasattr(args, 'cassandra_username')
        assert hasattr(args, 'cassandra_password')
    
    def test_help_text_with_environment_variables(self):
        """Test that help text shows environment variable values."""
        import argparse
        from trustgraph.storage.triples.cassandra.write import Processor as TriplesWriter
        
        env_vars = {
            'CASSANDRA_HOST': 'help-host1,help-host2',
            'CASSANDRA_USERNAME': 'help-user',
            'CASSANDRA_PASSWORD': 'help-pass'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            parser = argparse.ArgumentParser()
            TriplesWriter.add_args(parser)
            
            help_text = parser.format_help()
            
            # Should show environment variable values (except password)
            assert 'help-host1,help-host2' in help_text
            assert 'help-user' in help_text
            assert '<set>' in help_text  # Password should be hidden
            assert 'help-pass' not in help_text  # Password value not shown
            assert '[from CASSANDRA_HOST]' in help_text
            assert '[from CASSANDRA_USERNAME]' in help_text
            assert '[from CASSANDRA_PASSWORD]' in help_text


class TestConfigurationPriorityIntegration:
    """Test complete configuration priority chain in processors."""
    
    @patch('trustgraph.direct.cassandra.TrustGraph')
    def test_complete_priority_chain(self, mock_trust_graph):
        """Test CLI params > env vars > defaults priority in actual processor."""
        env_vars = {
            'CASSANDRA_HOST': 'env-host',
            'CASSANDRA_USERNAME': 'env-user',
            'CASSANDRA_PASSWORD': 'env-pass'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # Explicit parameters should override environment
            processor = TriplesWriter(
                cassandra_host='cli-host1,cli-host2',
                cassandra_username='cli-user'
                # Password not provided - should fall back to env
            )
            
            assert processor.graph_host == ['cli-host1', 'cli-host2']  # From CLI
            assert processor.username == 'cli-user'                   # From CLI
            assert processor.password == 'env-pass'                   # From env
    
    @patch('trustgraph.tables.knowledge.KnowledgeTableStore')
    def test_kg_store_priority_chain(self, mock_table_store):
        """Test configuration priority chain in kg-store processor."""
        mock_store_instance = MagicMock()
        mock_table_store.return_value = mock_store_instance
        
        env_vars = {
            'CASSANDRA_HOST': 'env-host1,env-host2',
            'CASSANDRA_USERNAME': 'env-user',
            'CASSANDRA_PASSWORD': 'env-pass'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            processor = KgStore(
                cassandra_host='param-host'
                # username and password not provided - should use env
            )
            
            # Verify correct priority resolution
            mock_table_store.assert_called_once_with(
                cassandra_host=['param-host'],  # From parameter
                cassandra_user='env-user',      # From environment
                cassandra_password='env-pass',  # From environment
                keyspace='knowledge'
            )