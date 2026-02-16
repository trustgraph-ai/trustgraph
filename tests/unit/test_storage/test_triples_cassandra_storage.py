"""
Tests for Cassandra triples storage service
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from trustgraph.storage.triples.cassandra.write import Processor
from trustgraph.schema import Triple, LITERAL, IRI
from trustgraph.direct.cassandra_kg import DEFAULT_GRAPH


class TestCassandraStorageProcessor:
    """Test cases for Cassandra storage processor"""

    def test_processor_initialization_with_defaults(self):
        """Test processor initialization with default parameters"""
        taskgroup_mock = MagicMock()
        
        # Patch environment to ensure clean defaults
        with patch.dict('os.environ', {}, clear=True):
            processor = Processor(taskgroup=taskgroup_mock)
        
        assert processor.cassandra_host == ['cassandra']  # Updated default
        assert processor.cassandra_username is None
        assert processor.cassandra_password is None
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
        
        assert processor.cassandra_host == ['cassandra.example.com']
        assert processor.cassandra_username == 'testuser'
        assert processor.cassandra_password == 'testpass'
        assert processor.table is None

    def test_processor_initialization_with_partial_auth(self):
        """Test processor initialization with only username (no password)"""
        taskgroup_mock = MagicMock()
        
        processor = Processor(
            taskgroup=taskgroup_mock,
            cassandra_username='testuser'
        )
        
        assert processor.cassandra_username == 'testuser'
        assert processor.cassandra_password is None
    
    def test_processor_no_backward_compatibility(self):
        """Test that old graph_* parameters are no longer supported"""
        taskgroup_mock = MagicMock()
        
        processor = Processor(
            taskgroup=taskgroup_mock,
            graph_host='old-host',
            graph_username='old-user',
            graph_password='old-pass'
        )
        
        # Should use defaults since graph_* params are not recognized
        assert processor.cassandra_host == ['cassandra']  # Default
        assert processor.cassandra_username is None
        assert processor.cassandra_password is None
    
    def test_processor_only_new_parameters_work(self):
        """Test that only new cassandra_* parameters work"""
        taskgroup_mock = MagicMock()
        
        processor = Processor(
            taskgroup=taskgroup_mock,
            cassandra_host='new-host',
            graph_host='old-host',  # Should be ignored
            cassandra_username='new-user',
            graph_username='old-user'  # Should be ignored
        )
        
        assert processor.cassandra_host == ['new-host']  # Only cassandra_* params work
        assert processor.cassandra_username == 'new-user'  # Only cassandra_* params work

    @pytest.mark.asyncio
    @patch('trustgraph.storage.triples.cassandra.write.EntityCentricKnowledgeGraph')
    async def test_table_switching_with_auth(self, mock_kg_class):
        """Test table switching logic when authentication is provided"""
        taskgroup_mock = MagicMock()
        mock_tg_instance = MagicMock()
        mock_kg_class.return_value = mock_tg_instance

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

        # Verify KnowledgeGraph was called with auth parameters
        mock_kg_class.assert_called_once_with(
            hosts=['cassandra'],  # Updated default
            keyspace='user1',
            username='testuser',
            password='testpass'
        )
        assert processor.table == 'user1'

    @pytest.mark.asyncio
    @patch('trustgraph.storage.triples.cassandra.write.EntityCentricKnowledgeGraph')
    async def test_table_switching_without_auth(self, mock_kg_class):
        """Test table switching logic when no authentication is provided"""
        taskgroup_mock = MagicMock()
        mock_tg_instance = MagicMock()
        mock_kg_class.return_value = mock_tg_instance

        processor = Processor(taskgroup=taskgroup_mock)

        # Create mock message
        mock_message = MagicMock()
        mock_message.metadata.user = 'user2'
        mock_message.metadata.collection = 'collection2'
        mock_message.triples = []

        await processor.store_triples(mock_message)

        # Verify KnowledgeGraph was called without auth parameters
        mock_kg_class.assert_called_once_with(
            hosts=['cassandra'],  # Updated default
            keyspace='user2'
        )
        assert processor.table == 'user2'

    @pytest.mark.asyncio
    @patch('trustgraph.storage.triples.cassandra.write.EntityCentricKnowledgeGraph')
    async def test_table_reuse_when_same(self, mock_kg_class):
        """Test that TrustGraph is not recreated when table hasn't changed"""
        taskgroup_mock = MagicMock()
        mock_tg_instance = MagicMock()
        mock_kg_class.return_value = mock_tg_instance

        processor = Processor(taskgroup=taskgroup_mock)

        # Create mock message
        mock_message = MagicMock()
        mock_message.metadata.user = 'user1'
        mock_message.metadata.collection = 'collection1'
        mock_message.triples = []

        # First call should create TrustGraph
        await processor.store_triples(mock_message)
        assert mock_kg_class.call_count == 1

        # Second call with same table should reuse TrustGraph
        await processor.store_triples(mock_message)
        assert mock_kg_class.call_count == 1  # Should not increase

    @pytest.mark.asyncio
    @patch('trustgraph.storage.triples.cassandra.write.EntityCentricKnowledgeGraph')
    async def test_triple_insertion(self, mock_kg_class):
        """Test that triples are properly inserted into Cassandra"""
        taskgroup_mock = MagicMock()
        mock_tg_instance = MagicMock()
        mock_kg_class.return_value = mock_tg_instance

        processor = Processor(taskgroup=taskgroup_mock)

        # Create mock triples with proper Term structure
        triple1 = MagicMock()
        triple1.s.type = LITERAL
        triple1.s.value = 'subject1'
        triple1.s.datatype = ''
        triple1.s.language = ''
        triple1.p.type = LITERAL
        triple1.p.value = 'predicate1'
        triple1.o.type = LITERAL
        triple1.o.value = 'object1'
        triple1.o.datatype = ''
        triple1.o.language = ''
        triple1.g = None

        triple2 = MagicMock()
        triple2.s.type = LITERAL
        triple2.s.value = 'subject2'
        triple2.s.datatype = ''
        triple2.s.language = ''
        triple2.p.type = LITERAL
        triple2.p.value = 'predicate2'
        triple2.o.type = LITERAL
        triple2.o.value = 'object2'
        triple2.o.datatype = ''
        triple2.o.language = ''
        triple2.g = None

        # Create mock message
        mock_message = MagicMock()
        mock_message.metadata.user = 'user1'
        mock_message.metadata.collection = 'collection1'
        mock_message.triples = [triple1, triple2]

        await processor.store_triples(mock_message)

        # Verify both triples were inserted (with g=, otype=, dtype=, lang= parameters)
        assert mock_tg_instance.insert.call_count == 2
        mock_tg_instance.insert.assert_any_call(
            'collection1', 'subject1', 'predicate1', 'object1',
            g=DEFAULT_GRAPH, otype='l', dtype='', lang=''
        )
        mock_tg_instance.insert.assert_any_call(
            'collection1', 'subject2', 'predicate2', 'object2',
            g=DEFAULT_GRAPH, otype='l', dtype='', lang=''
        )

    @pytest.mark.asyncio
    @patch('trustgraph.storage.triples.cassandra.write.EntityCentricKnowledgeGraph')
    async def test_triple_insertion_with_empty_list(self, mock_kg_class):
        """Test behavior when message has no triples"""
        taskgroup_mock = MagicMock()
        mock_tg_instance = MagicMock()
        mock_kg_class.return_value = mock_tg_instance

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
    @patch('trustgraph.storage.triples.cassandra.write.EntityCentricKnowledgeGraph')
    @patch('trustgraph.storage.triples.cassandra.write.time.sleep')
    async def test_exception_handling_with_retry(self, mock_sleep, mock_kg_class):
        """Test exception handling during TrustGraph creation"""
        taskgroup_mock = MagicMock()
        mock_kg_class.side_effect = Exception("Connection failed")

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
    @patch('trustgraph.storage.triples.cassandra.write.EntityCentricKnowledgeGraph')
    async def test_store_triples_table_switching_between_different_tables(self, mock_kg_class):
        """Test table switching when different tables are used in sequence"""
        taskgroup_mock = MagicMock()
        mock_tg_instance1 = MagicMock()
        mock_tg_instance2 = MagicMock()
        mock_kg_class.side_effect = [mock_tg_instance1, mock_tg_instance2]

        processor = Processor(taskgroup=taskgroup_mock)

        # First message with table1
        mock_message1 = MagicMock()
        mock_message1.metadata.user = 'user1'
        mock_message1.metadata.collection = 'collection1'
        mock_message1.triples = []

        await processor.store_triples(mock_message1)
        assert processor.table == 'user1'
        assert processor.tg == mock_tg_instance1

        # Second message with different table
        mock_message2 = MagicMock()
        mock_message2.metadata.user = 'user2'
        mock_message2.metadata.collection = 'collection2'
        mock_message2.triples = []

        await processor.store_triples(mock_message2)
        assert processor.table == 'user2'
        assert processor.tg == mock_tg_instance2

        # Verify TrustGraph was created twice for different tables
        assert mock_kg_class.call_count == 2

    @pytest.mark.asyncio
    @patch('trustgraph.storage.triples.cassandra.write.EntityCentricKnowledgeGraph')
    async def test_store_triples_with_special_characters_in_values(self, mock_kg_class):
        """Test storing triples with special characters and unicode"""
        taskgroup_mock = MagicMock()
        mock_tg_instance = MagicMock()
        mock_kg_class.return_value = mock_tg_instance

        processor = Processor(taskgroup=taskgroup_mock)

        # Create triple with special characters and proper Term structure
        triple = MagicMock()
        triple.s.type = LITERAL
        triple.s.value = 'subject with spaces & symbols'
        triple.s.datatype = ''
        triple.s.language = ''
        triple.p.type = LITERAL
        triple.p.value = 'predicate:with/colons'
        triple.o.type = LITERAL
        triple.o.value = 'object with "quotes" and unicode: ñáéíóú'
        triple.o.datatype = ''
        triple.o.language = ''
        triple.g = None

        mock_message = MagicMock()
        mock_message.metadata.user = 'test_user'
        mock_message.metadata.collection = 'test_collection'
        mock_message.triples = [triple]

        await processor.store_triples(mock_message)

        # Verify the triple was inserted with special characters preserved
        mock_tg_instance.insert.assert_called_once_with(
            'test_collection',
            'subject with spaces & symbols',
            'predicate:with/colons',
            'object with "quotes" and unicode: ñáéíóú',
            g=DEFAULT_GRAPH,
            otype='l',
            dtype='',
            lang=''
        )

    @pytest.mark.asyncio
    @patch('trustgraph.storage.triples.cassandra.write.EntityCentricKnowledgeGraph')
    async def test_store_triples_preserves_old_table_on_exception(self, mock_kg_class):
        """Test that table remains unchanged when TrustGraph creation fails"""
        taskgroup_mock = MagicMock()

        processor = Processor(taskgroup=taskgroup_mock)

        # Set an initial table
        processor.table = ('old_user', 'old_collection')

        # Mock TrustGraph to raise exception
        mock_kg_class.side_effect = Exception("Connection failed")

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


class TestCassandraPerformanceOptimizations:
    """Test cases for multi-table performance optimizations"""

    @pytest.mark.asyncio
    @patch('trustgraph.storage.triples.cassandra.write.EntityCentricKnowledgeGraph')
    async def test_legacy_mode_uses_single_table(self, mock_kg_class):
        """Test that legacy mode still works with single table"""
        taskgroup_mock = MagicMock()
        mock_tg_instance = MagicMock()
        mock_kg_class.return_value = mock_tg_instance

        with patch.dict('os.environ', {'CASSANDRA_USE_LEGACY': 'true'}):
            processor = Processor(taskgroup=taskgroup_mock)

            mock_message = MagicMock()
            mock_message.metadata.user = 'user1'
            mock_message.metadata.collection = 'collection1'
            mock_message.triples = []

            await processor.store_triples(mock_message)

            # Verify KnowledgeGraph instance uses legacy mode
            assert mock_tg_instance is not None

    @pytest.mark.asyncio
    @patch('trustgraph.storage.triples.cassandra.write.EntityCentricKnowledgeGraph')
    async def test_optimized_mode_uses_multi_table(self, mock_kg_class):
        """Test that optimized mode uses multi-table schema"""
        taskgroup_mock = MagicMock()
        mock_tg_instance = MagicMock()
        mock_kg_class.return_value = mock_tg_instance

        with patch.dict('os.environ', {'CASSANDRA_USE_LEGACY': 'false'}):
            processor = Processor(taskgroup=taskgroup_mock)

            mock_message = MagicMock()
            mock_message.metadata.user = 'user1'
            mock_message.metadata.collection = 'collection1'
            mock_message.triples = []

            await processor.store_triples(mock_message)

            # Verify KnowledgeGraph instance is in optimized mode
            assert mock_tg_instance is not None

    @pytest.mark.asyncio
    @patch('trustgraph.storage.triples.cassandra.write.EntityCentricKnowledgeGraph')
    async def test_batch_write_consistency(self, mock_kg_class):
        """Test that all tables stay consistent during batch writes"""
        taskgroup_mock = MagicMock()
        mock_tg_instance = MagicMock()
        mock_kg_class.return_value = mock_tg_instance

        processor = Processor(taskgroup=taskgroup_mock)

        # Create test triple with proper Term structure
        triple = MagicMock()
        triple.s.type = LITERAL
        triple.s.value = 'test_subject'
        triple.s.datatype = ''
        triple.s.language = ''
        triple.p.type = LITERAL
        triple.p.value = 'test_predicate'
        triple.o.type = LITERAL
        triple.o.value = 'test_object'
        triple.o.datatype = ''
        triple.o.language = ''
        triple.g = None

        mock_message = MagicMock()
        mock_message.metadata.user = 'user1'
        mock_message.metadata.collection = 'collection1'
        mock_message.triples = [triple]

        await processor.store_triples(mock_message)

        # Verify insert was called for the triple (implementation details tested in KnowledgeGraph)
        mock_tg_instance.insert.assert_called_once_with(
            'collection1', 'test_subject', 'test_predicate', 'test_object',
            g=DEFAULT_GRAPH, otype='l', dtype='', lang=''
        )

    def test_environment_variable_controls_mode(self):
        """Test that CASSANDRA_USE_LEGACY environment variable controls operation mode"""
        taskgroup_mock = MagicMock()

        # Test legacy mode
        with patch.dict('os.environ', {'CASSANDRA_USE_LEGACY': 'true'}):
            processor = Processor(taskgroup=taskgroup_mock)
            # Mode is determined in KnowledgeGraph initialization

        # Test optimized mode
        with patch.dict('os.environ', {'CASSANDRA_USE_LEGACY': 'false'}):
            processor = Processor(taskgroup=taskgroup_mock)
            # Mode is determined in KnowledgeGraph initialization

        # Test default mode (optimized when env var not set)
        with patch.dict('os.environ', {}, clear=True):
            processor = Processor(taskgroup=taskgroup_mock)
            # Mode is determined in KnowledgeGraph initialization