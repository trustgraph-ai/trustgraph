"""
Tests for Cassandra triples storage service
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from trustgraph.storage.triples.cassandra.write import Processor
from trustgraph.schema import Value, Triple


class TestCassandraStorageProcessor:
    """Test cases for Cassandra storage processor"""

    def test_processor_initialization_with_defaults(self):
        """Test processor initialization with default parameters"""
        taskgroup_mock = MagicMock()
        
        # Patch environment to ensure clean defaults
        with patch.dict('os.environ', {}, clear=True):
            processor = Processor(taskgroup=taskgroup_mock)
        
        assert processor.graph_host == ['cassandra']  # Updated default
        assert processor.username is None
        assert processor.password is None
        assert processor.table is None

    def test_processor_initialization_with_custom_params(self):
        """Test processor initialization with custom parameters (new cassandra_* names)"""
        taskgroup_mock = MagicMock()
        
        processor = Processor(
            taskgroup=taskgroup_mock,
            id='custom-storage',
            cassandra_host='cassandra.example.com',
            cassandra_username='testuser',
            cassandra_password='testpass'
        )
        
        assert processor.graph_host == ['cassandra.example.com']
        assert processor.username == 'testuser'
        assert processor.password == 'testpass'
        assert processor.table is None

    def test_processor_initialization_with_partial_auth(self):
        """Test processor initialization with only username (no password)"""
        taskgroup_mock = MagicMock()
        
        processor = Processor(
            taskgroup=taskgroup_mock,
            cassandra_username='testuser'
        )
        
        assert processor.username == 'testuser'
        assert processor.password is None
    
    def test_processor_initialization_backward_compatibility(self):
        """Test processor initialization with old graph_* parameters (backward compatibility)"""
        taskgroup_mock = MagicMock()
        
        processor = Processor(
            taskgroup=taskgroup_mock,
            graph_host='old-host',
            graph_username='old-user',
            graph_password='old-pass'
        )
        
        assert processor.graph_host == ['old-host']
        assert processor.username == 'old-user'
        assert processor.password == 'old-pass'
    
    def test_processor_parameter_precedence(self):
        """Test that new cassandra_* parameters take precedence over old graph_* parameters"""
        taskgroup_mock = MagicMock()
        
        processor = Processor(
            taskgroup=taskgroup_mock,
            cassandra_host='new-host',
            graph_host='old-host',  # Should be ignored
            cassandra_username='new-user',
            graph_username='old-user'  # Should be ignored
        )
        
        assert processor.graph_host == ['new-host']  # New parameter wins
        assert processor.username == 'new-user'     # New parameter wins

    @pytest.mark.asyncio
    @patch('trustgraph.storage.triples.cassandra.write.TrustGraph')
    async def test_table_switching_with_auth(self, mock_trustgraph):
        """Test table switching logic when authentication is provided"""
        taskgroup_mock = MagicMock()
        mock_tg_instance = MagicMock()
        mock_trustgraph.return_value = mock_tg_instance
        
        processor = Processor(
            taskgroup=taskgroup_mock,
            cassandra_username='testuser',
            cassandra_password='testpass'
        )
        
        # Create mock message
        mock_message = MagicMock()
        mock_message.metadata.user = 'user1'
        mock_message.metadata.collection = 'collection1'
        mock_message.triples = []
        
        await processor.store_triples(mock_message)
        
        # Verify TrustGraph was called with auth parameters
        mock_trustgraph.assert_called_once_with(
            hosts=['cassandra'],  # Updated default
            keyspace='user1',
            table='collection1',
            username='testuser',
            password='testpass'
        )
        assert processor.table == ('user1', 'collection1')

    @pytest.mark.asyncio
    @patch('trustgraph.storage.triples.cassandra.write.TrustGraph')
    async def test_table_switching_without_auth(self, mock_trustgraph):
        """Test table switching logic when no authentication is provided"""
        taskgroup_mock = MagicMock()
        mock_tg_instance = MagicMock()
        mock_trustgraph.return_value = mock_tg_instance
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Create mock message
        mock_message = MagicMock()
        mock_message.metadata.user = 'user2'
        mock_message.metadata.collection = 'collection2'
        mock_message.triples = []
        
        await processor.store_triples(mock_message)
        
        # Verify TrustGraph was called without auth parameters
        mock_trustgraph.assert_called_once_with(
            hosts=['cassandra'],  # Updated default
            keyspace='user2',
            table='collection2'
        )
        assert processor.table == ('user2', 'collection2')

    @pytest.mark.asyncio
    @patch('trustgraph.storage.triples.cassandra.write.TrustGraph')
    async def test_table_reuse_when_same(self, mock_trustgraph):
        """Test that TrustGraph is not recreated when table hasn't changed"""
        taskgroup_mock = MagicMock()
        mock_tg_instance = MagicMock()
        mock_trustgraph.return_value = mock_tg_instance
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Create mock message
        mock_message = MagicMock()
        mock_message.metadata.user = 'user1'
        mock_message.metadata.collection = 'collection1'
        mock_message.triples = []
        
        # First call should create TrustGraph
        await processor.store_triples(mock_message)
        assert mock_trustgraph.call_count == 1
        
        # Second call with same table should reuse TrustGraph
        await processor.store_triples(mock_message)
        assert mock_trustgraph.call_count == 1  # Should not increase

    @pytest.mark.asyncio
    @patch('trustgraph.storage.triples.cassandra.write.TrustGraph')
    async def test_triple_insertion(self, mock_trustgraph):
        """Test that triples are properly inserted into Cassandra"""
        taskgroup_mock = MagicMock()
        mock_tg_instance = MagicMock()
        mock_trustgraph.return_value = mock_tg_instance
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Create mock triples
        triple1 = MagicMock()
        triple1.s.value = 'subject1'
        triple1.p.value = 'predicate1'
        triple1.o.value = 'object1'
        
        triple2 = MagicMock()
        triple2.s.value = 'subject2'
        triple2.p.value = 'predicate2'
        triple2.o.value = 'object2'
        
        # Create mock message
        mock_message = MagicMock()
        mock_message.metadata.user = 'user1'
        mock_message.metadata.collection = 'collection1'
        mock_message.triples = [triple1, triple2]
        
        await processor.store_triples(mock_message)
        
        # Verify both triples were inserted
        assert mock_tg_instance.insert.call_count == 2
        mock_tg_instance.insert.assert_any_call('subject1', 'predicate1', 'object1')
        mock_tg_instance.insert.assert_any_call('subject2', 'predicate2', 'object2')

    @pytest.mark.asyncio
    @patch('trustgraph.storage.triples.cassandra.write.TrustGraph')
    async def test_triple_insertion_with_empty_list(self, mock_trustgraph):
        """Test behavior when message has no triples"""
        taskgroup_mock = MagicMock()
        mock_tg_instance = MagicMock()
        mock_trustgraph.return_value = mock_tg_instance
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Create mock message with empty triples
        mock_message = MagicMock()
        mock_message.metadata.user = 'user1'
        mock_message.metadata.collection = 'collection1'
        mock_message.triples = []
        
        await processor.store_triples(mock_message)
        
        # Verify no triples were inserted
        mock_tg_instance.insert.assert_not_called()

    @pytest.mark.asyncio
    @patch('trustgraph.storage.triples.cassandra.write.TrustGraph')
    @patch('trustgraph.storage.triples.cassandra.write.time.sleep')
    async def test_exception_handling_with_retry(self, mock_sleep, mock_trustgraph):
        """Test exception handling during TrustGraph creation"""
        taskgroup_mock = MagicMock()
        mock_trustgraph.side_effect = Exception("Connection failed")
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Create mock message
        mock_message = MagicMock()
        mock_message.metadata.user = 'user1'
        mock_message.metadata.collection = 'collection1'
        mock_message.triples = []
        
        with pytest.raises(Exception, match="Connection failed"):
            await processor.store_triples(mock_message)
        
        # Verify sleep was called before re-raising
        mock_sleep.assert_called_once_with(1)

    def test_add_args_method(self):
        """Test that add_args properly configures argument parser"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        # Mock the parent class add_args method
        with patch('trustgraph.storage.triples.cassandra.write.TriplesStoreService.add_args') as mock_parent_add_args:
            Processor.add_args(parser)
            
            # Verify parent add_args was called
            mock_parent_add_args.assert_called_once_with(parser)
        
        # Verify our specific arguments were added (now using cassandra_* names)
        # Parse empty args to check defaults
        args = parser.parse_args([])
        
        assert hasattr(args, 'cassandra_host')
        assert args.cassandra_host == 'cassandra'  # Updated default
        assert hasattr(args, 'cassandra_username')
        assert args.cassandra_username is None
        assert hasattr(args, 'cassandra_password')
        assert args.cassandra_password is None

    def test_add_args_with_custom_values(self):
        """Test add_args with custom command line values"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        with patch('trustgraph.storage.triples.cassandra.write.TriplesStoreService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with custom values (new cassandra_* arguments)
        args = parser.parse_args([
            '--cassandra-host', 'cassandra.example.com',
            '--cassandra-username', 'testuser',
            '--cassandra-password', 'testpass'
        ])
        
        assert args.cassandra_host == 'cassandra.example.com'
        assert args.cassandra_username == 'testuser'
        assert args.cassandra_password == 'testpass'

    def test_add_args_with_env_vars(self):
        """Test add_args shows environment variables in help text"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        import os
        
        parser = ArgumentParser()
        
        # Set environment variables
        env_vars = {
            'CASSANDRA_HOST': 'env-host1,env-host2',
            'CASSANDRA_USERNAME': 'env-user',
            'CASSANDRA_PASSWORD': 'env-pass'
        }
        
        with patch('trustgraph.storage.triples.cassandra.write.TriplesStoreService.add_args'):
            with patch.dict(os.environ, env_vars, clear=True):
                Processor.add_args(parser)
                
                # Check that help text includes environment variable info
                help_text = parser.format_help()
                # Argparse may break lines, so check for components
                assert 'env-' in help_text and 'host1' in help_text
                assert 'env-host2' in help_text
                assert 'env-user' in help_text
                assert '<set>' in help_text  # Password should be hidden
                assert 'env-pass' not in help_text  # Password value not shown

    @patch('trustgraph.storage.triples.cassandra.write.Processor.launch')
    def test_run_function(self, mock_launch):
        """Test the run function calls Processor.launch with correct parameters"""
        from trustgraph.storage.triples.cassandra.write import run, default_ident
        
        run()
        
        mock_launch.assert_called_once_with(default_ident, '\nGraph writer.  Input is graph edge.  Writes edges to Cassandra graph.\n')

    @pytest.mark.asyncio
    @patch('trustgraph.storage.triples.cassandra.write.TrustGraph')
    async def test_store_triples_table_switching_between_different_tables(self, mock_trustgraph):
        """Test table switching when different tables are used in sequence"""
        taskgroup_mock = MagicMock()
        mock_tg_instance1 = MagicMock()
        mock_tg_instance2 = MagicMock()
        mock_trustgraph.side_effect = [mock_tg_instance1, mock_tg_instance2]
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # First message with table1
        mock_message1 = MagicMock()
        mock_message1.metadata.user = 'user1'
        mock_message1.metadata.collection = 'collection1'
        mock_message1.triples = []
        
        await processor.store_triples(mock_message1)
        assert processor.table == ('user1', 'collection1')
        assert processor.tg == mock_tg_instance1
        
        # Second message with different table
        mock_message2 = MagicMock()
        mock_message2.metadata.user = 'user2'
        mock_message2.metadata.collection = 'collection2'
        mock_message2.triples = []
        
        await processor.store_triples(mock_message2)
        assert processor.table == ('user2', 'collection2')
        assert processor.tg == mock_tg_instance2
        
        # Verify TrustGraph was created twice for different tables
        assert mock_trustgraph.call_count == 2

    @pytest.mark.asyncio
    @patch('trustgraph.storage.triples.cassandra.write.TrustGraph')
    async def test_store_triples_with_special_characters_in_values(self, mock_trustgraph):
        """Test storing triples with special characters and unicode"""
        taskgroup_mock = MagicMock()
        mock_tg_instance = MagicMock()
        mock_trustgraph.return_value = mock_tg_instance
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Create triple with special characters
        triple = MagicMock()
        triple.s.value = 'subject with spaces & symbols'
        triple.p.value = 'predicate:with/colons'
        triple.o.value = 'object with "quotes" and unicode: ñáéíóú'
        
        mock_message = MagicMock()
        mock_message.metadata.user = 'test_user'
        mock_message.metadata.collection = 'test_collection'
        mock_message.triples = [triple]
        
        await processor.store_triples(mock_message)
        
        # Verify the triple was inserted with special characters preserved
        mock_tg_instance.insert.assert_called_once_with(
            'subject with spaces & symbols',
            'predicate:with/colons',
            'object with "quotes" and unicode: ñáéíóú'
        )

    @pytest.mark.asyncio
    @patch('trustgraph.storage.triples.cassandra.write.TrustGraph')
    async def test_store_triples_preserves_old_table_on_exception(self, mock_trustgraph):
        """Test that table remains unchanged when TrustGraph creation fails"""
        taskgroup_mock = MagicMock()
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Set an initial table
        processor.table = ('old_user', 'old_collection')
        
        # Mock TrustGraph to raise exception
        mock_trustgraph.side_effect = Exception("Connection failed")
        
        mock_message = MagicMock()
        mock_message.metadata.user = 'new_user'
        mock_message.metadata.collection = 'new_collection'
        mock_message.triples = []
        
        with pytest.raises(Exception, match="Connection failed"):
            await processor.store_triples(mock_message)
        
        # Table should remain unchanged since self.table = table happens after try/except
        assert processor.table == ('old_user', 'old_collection')
        # TrustGraph should be set to None though
        assert processor.tg is None