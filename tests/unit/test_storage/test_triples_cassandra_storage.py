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
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        assert processor.graph_host == ['localhost']
        assert processor.username is None
        assert processor.password is None
        assert processor.table is None

    def test_processor_initialization_with_custom_params(self):
        """Test processor initialization with custom parameters"""
        taskgroup_mock = MagicMock()
        
        processor = Processor(
            taskgroup=taskgroup_mock,
            id='custom-storage',
            graph_host='cassandra.example.com',
            graph_username='testuser',
            graph_password='testpass'
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
            graph_username='testuser'
        )
        
        assert processor.username == 'testuser'
        assert processor.password is None

    @pytest.mark.asyncio
    @patch('trustgraph.storage.triples.cassandra.write.TrustGraph')
    async def test_table_switching_with_auth(self, mock_trustgraph):
        """Test table switching logic when authentication is provided"""
        taskgroup_mock = MagicMock()
        mock_tg_instance = MagicMock()
        mock_trustgraph.return_value = mock_tg_instance
        
        processor = Processor(
            taskgroup=taskgroup_mock,
            graph_username='testuser',
            graph_password='testpass'
        )
        
        # Create mock message
        mock_message = MagicMock()
        mock_message.metadata.user = 'user1'
        mock_message.metadata.collection = 'collection1'
        mock_message.triples = []
        
        await processor.store_triples(mock_message)
        
        # Verify TrustGraph was called with auth parameters
        mock_trustgraph.assert_called_once_with(
            hosts=['localhost'],
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
            hosts=['localhost'],
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
        
        # Verify our specific arguments were added
        # Parse empty args to check defaults
        args = parser.parse_args([])
        
        assert hasattr(args, 'graph_host')
        assert args.graph_host == 'localhost'
        assert hasattr(args, 'graph_username')
        assert args.graph_username is None
        assert hasattr(args, 'graph_password')
        assert args.graph_password is None

    def test_add_args_with_custom_values(self):
        """Test add_args with custom command line values"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        with patch('trustgraph.storage.triples.cassandra.write.TriplesStoreService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with custom values
        args = parser.parse_args([
            '--graph-host', 'cassandra.example.com',
            '--graph-username', 'testuser',
            '--graph-password', 'testpass'
        ])
        
        assert args.graph_host == 'cassandra.example.com'
        assert args.graph_username == 'testuser'
        assert args.graph_password == 'testpass'

    def test_add_args_short_form(self):
        """Test add_args with short form arguments"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        with patch('trustgraph.storage.triples.cassandra.write.TriplesStoreService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with short form
        args = parser.parse_args(['-g', 'short.example.com'])
        
        assert args.graph_host == 'short.example.com'

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