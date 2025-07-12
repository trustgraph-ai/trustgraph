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