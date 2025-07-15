"""
Tests for Memgraph triples storage service
"""

import pytest
from unittest.mock import MagicMock, patch

from trustgraph.storage.triples.memgraph.write import Processor
from trustgraph.schema import Value, Triple


class TestMemgraphStorageProcessor:
    """Test cases for Memgraph storage processor"""

    @pytest.fixture
    def mock_message(self):
        """Create a mock message for testing"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        # Create a test triple
        triple = Triple(
            s=Value(value='http://example.com/subject', is_uri=True),
            p=Value(value='http://example.com/predicate', is_uri=True),
            o=Value(value='literal object', is_uri=False)
        )
        message.triples = [triple]
        
        return message

    @pytest.fixture
    def processor(self):
        """Create a processor instance for testing"""
        with patch('trustgraph.storage.triples.memgraph.write.GraphDatabase') as mock_graph_db:
            mock_driver = MagicMock()
            mock_session = MagicMock()
            mock_graph_db.driver.return_value = mock_driver
            mock_driver.session.return_value.__enter__.return_value = mock_session
            
            return Processor(
                taskgroup=MagicMock(),
                id='test-memgraph-storage',
                graph_host='bolt://localhost:7687',
                username='test_user',
                password='test_pass',
                database='test_db'
            )

    @patch('trustgraph.storage.triples.memgraph.write.GraphDatabase')
    def test_processor_initialization_with_defaults(self, mock_graph_db):
        """Test processor initialization with default parameters"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        assert processor.db == 'memgraph'
        mock_graph_db.driver.assert_called_once_with(
            'bolt://memgraph:7687',
            auth=('memgraph', 'password')
        )

    @patch('trustgraph.storage.triples.memgraph.write.GraphDatabase')
    def test_processor_initialization_with_custom_params(self, mock_graph_db):
        """Test processor initialization with custom parameters"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        processor = Processor(
            taskgroup=taskgroup_mock,
            graph_host='bolt://custom:7687',
            username='custom_user',
            password='custom_pass',
            database='custom_db'
        )
        
        assert processor.db == 'custom_db'
        mock_graph_db.driver.assert_called_once_with(
            'bolt://custom:7687',
            auth=('custom_user', 'custom_pass')
        )

    @patch('trustgraph.storage.triples.memgraph.write.GraphDatabase')
    def test_create_indexes_success(self, mock_graph_db):
        """Test successful index creation"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Verify index creation calls
        expected_calls = [
            "CREATE INDEX ON :Node",
            "CREATE INDEX ON :Node(uri)",
            "CREATE INDEX ON :Literal",
            "CREATE INDEX ON :Literal(value)"
        ]
        
        assert mock_session.run.call_count == len(expected_calls)
        for i, expected_call in enumerate(expected_calls):
            actual_call = mock_session.run.call_args_list[i][0][0]
            assert actual_call == expected_call

    @patch('trustgraph.storage.triples.memgraph.write.GraphDatabase')
    def test_create_indexes_with_exceptions(self, mock_graph_db):
        """Test index creation with exceptions (should be ignored)"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        # Make all index creation calls raise exceptions
        mock_session.run.side_effect = Exception("Index already exists")
        
        # Should not raise an exception
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Verify all index creation calls were attempted
        assert mock_session.run.call_count == 4

    def test_create_node(self, processor):
        """Test node creation"""
        test_uri = 'http://example.com/node'
        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        
        processor.io.execute_query.return_value = mock_result
        
        processor.create_node(test_uri)
        
        processor.io.execute_query.assert_called_once_with(
            "MERGE (n:Node {uri: $uri})",
            uri=test_uri,
            database_=processor.db
        )

    def test_create_literal(self, processor):
        """Test literal creation"""
        test_value = 'test literal value'
        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        
        processor.io.execute_query.return_value = mock_result
        
        processor.create_literal(test_value)
        
        processor.io.execute_query.assert_called_once_with(
            "MERGE (n:Literal {value: $value})",
            value=test_value,
            database_=processor.db
        )

    def test_relate_node(self, processor):
        """Test node-to-node relationship creation"""
        src_uri = 'http://example.com/src'
        pred_uri = 'http://example.com/pred'
        dest_uri = 'http://example.com/dest'
        
        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 0
        mock_summary.result_available_after = 5
        mock_result.summary = mock_summary
        
        processor.io.execute_query.return_value = mock_result
        
        processor.relate_node(src_uri, pred_uri, dest_uri)
        
        processor.io.execute_query.assert_called_once_with(
            "MATCH (src:Node {uri: $src}) "
            "MATCH (dest:Node {uri: $dest}) "
            "MERGE (src)-[:Rel {uri: $uri}]->(dest)",
            src=src_uri, dest=dest_uri, uri=pred_uri,
            database_=processor.db
        )

    def test_relate_literal(self, processor):
        """Test node-to-literal relationship creation"""
        src_uri = 'http://example.com/src'
        pred_uri = 'http://example.com/pred'
        literal_value = 'literal destination'
        
        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 0
        mock_summary.result_available_after = 5
        mock_result.summary = mock_summary
        
        processor.io.execute_query.return_value = mock_result
        
        processor.relate_literal(src_uri, pred_uri, literal_value)
        
        processor.io.execute_query.assert_called_once_with(
            "MATCH (src:Node {uri: $src}) "
            "MATCH (dest:Literal {value: $dest}) "
            "MERGE (src)-[:Rel {uri: $uri}]->(dest)",
            src=src_uri, dest=literal_value, uri=pred_uri,
            database_=processor.db
        )

    def test_create_triple_with_uri_object(self, processor):
        """Test triple creation with URI object"""
        mock_tx = MagicMock()
        
        triple = Triple(
            s=Value(value='http://example.com/subject', is_uri=True),
            p=Value(value='http://example.com/predicate', is_uri=True),
            o=Value(value='http://example.com/object', is_uri=True)
        )
        
        processor.create_triple(mock_tx, triple)
        
        # Verify transaction calls
        expected_calls = [
            # Create subject node
            ("MERGE (n:Node {uri: $uri})", {'uri': 'http://example.com/subject'}),
            # Create object node  
            ("MERGE (n:Node {uri: $uri})", {'uri': 'http://example.com/object'}),
            # Create relationship
            ("MATCH (src:Node {uri: $src}) "
             "MATCH (dest:Node {uri: $dest}) "
             "MERGE (src)-[:Rel {uri: $uri}]->(dest)",
             {'src': 'http://example.com/subject', 'dest': 'http://example.com/object', 'uri': 'http://example.com/predicate'})
        ]
        
        assert mock_tx.run.call_count == 3
        for i, (expected_query, expected_params) in enumerate(expected_calls):
            actual_call = mock_tx.run.call_args_list[i]
            assert actual_call[0][0] == expected_query
            assert actual_call[1] == expected_params

    def test_create_triple_with_literal_object(self, processor):
        """Test triple creation with literal object"""
        mock_tx = MagicMock()
        
        triple = Triple(
            s=Value(value='http://example.com/subject', is_uri=True),
            p=Value(value='http://example.com/predicate', is_uri=True),
            o=Value(value='literal object', is_uri=False)
        )
        
        processor.create_triple(mock_tx, triple)
        
        # Verify transaction calls
        expected_calls = [
            # Create subject node
            ("MERGE (n:Node {uri: $uri})", {'uri': 'http://example.com/subject'}),
            # Create literal object
            ("MERGE (n:Literal {value: $value})", {'value': 'literal object'}),
            # Create relationship
            ("MATCH (src:Node {uri: $src}) "
             "MATCH (dest:Literal {value: $dest}) "
             "MERGE (src)-[:Rel {uri: $uri}]->(dest)",
             {'src': 'http://example.com/subject', 'dest': 'literal object', 'uri': 'http://example.com/predicate'})
        ]
        
        assert mock_tx.run.call_count == 3
        for i, (expected_query, expected_params) in enumerate(expected_calls):
            actual_call = mock_tx.run.call_args_list[i]
            assert actual_call[0][0] == expected_query
            assert actual_call[1] == expected_params

    @pytest.mark.asyncio
    async def test_store_triples_single_triple(self, processor, mock_message):
        """Test storing a single triple"""
        mock_session = MagicMock()
        processor.io.session.return_value.__enter__.return_value = mock_session
        
        # Reset the mock to clear the initialization call
        processor.io.session.reset_mock()
        
        await processor.store_triples(mock_message)
        
        # Verify session was created with correct database
        processor.io.session.assert_called_once_with(database=processor.db)
        
        # Verify execute_write was called once per triple
        mock_session.execute_write.assert_called_once()
        
        # Verify the triple was passed to create_triple
        call_args = mock_session.execute_write.call_args
        assert call_args[0][0] == processor.create_triple
        assert call_args[0][1] == mock_message.triples[0]

    @pytest.mark.asyncio
    async def test_store_triples_multiple_triples(self, processor):
        """Test storing multiple triples"""
        mock_session = MagicMock()
        processor.io.session.return_value.__enter__.return_value = mock_session
        
        # Reset the mock to clear the initialization call
        processor.io.session.reset_mock()
        
        # Create message with multiple triples
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        triple1 = Triple(
            s=Value(value='http://example.com/subject1', is_uri=True),
            p=Value(value='http://example.com/predicate1', is_uri=True),
            o=Value(value='literal object1', is_uri=False)
        )
        triple2 = Triple(
            s=Value(value='http://example.com/subject2', is_uri=True),
            p=Value(value='http://example.com/predicate2', is_uri=True),
            o=Value(value='http://example.com/object2', is_uri=True)
        )
        message.triples = [triple1, triple2]
        
        await processor.store_triples(message)
        
        # Verify session was called twice (once per triple)
        assert processor.io.session.call_count == 2
        
        # Verify execute_write was called once per triple
        assert mock_session.execute_write.call_count == 2
        
        # Verify each triple was processed
        call_args_list = mock_session.execute_write.call_args_list
        assert call_args_list[0][0][1] == triple1
        assert call_args_list[1][0][1] == triple2

    @pytest.mark.asyncio
    async def test_store_triples_empty_list(self, processor):
        """Test storing empty triples list"""
        mock_session = MagicMock()
        processor.io.session.return_value.__enter__.return_value = mock_session
        
        # Reset the mock to clear the initialization call
        processor.io.session.reset_mock()
        
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        message.triples = []
        
        await processor.store_triples(message)
        
        # Verify no session calls were made (no triples to process)
        processor.io.session.assert_not_called()
        
        # Verify no execute_write calls were made
        mock_session.execute_write.assert_not_called()

    def test_add_args_method(self):
        """Test that add_args properly configures argument parser"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        # Mock the parent class add_args method
        with patch('trustgraph.storage.triples.memgraph.write.TriplesStoreService.add_args') as mock_parent_add_args:
            Processor.add_args(parser)
            
            # Verify parent add_args was called
            mock_parent_add_args.assert_called_once()
        
        # Verify our specific arguments were added
        # Parse empty args to check defaults
        args = parser.parse_args([])
        
        assert hasattr(args, 'graph_host')
        assert args.graph_host == 'bolt://memgraph:7687'
        assert hasattr(args, 'username')
        assert args.username == 'memgraph'
        assert hasattr(args, 'password')
        assert args.password == 'password'
        assert hasattr(args, 'database')
        assert args.database == 'memgraph'

    def test_add_args_with_custom_values(self):
        """Test add_args with custom command line values"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        with patch('trustgraph.storage.triples.memgraph.write.TriplesStoreService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with custom values
        args = parser.parse_args([
            '--graph-host', 'bolt://custom:7687',
            '--username', 'custom_user',
            '--password', 'custom_pass',
            '--database', 'custom_db'
        ])
        
        assert args.graph_host == 'bolt://custom:7687'
        assert args.username == 'custom_user'
        assert args.password == 'custom_pass'
        assert args.database == 'custom_db'

    def test_add_args_short_form(self):
        """Test add_args with short form arguments"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        with patch('trustgraph.storage.triples.memgraph.write.TriplesStoreService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with short form
        args = parser.parse_args(['-g', 'bolt://short:7687'])
        
        assert args.graph_host == 'bolt://short:7687'

    @patch('trustgraph.storage.triples.memgraph.write.Processor.launch')
    def test_run_function(self, mock_launch):
        """Test the run function calls Processor.launch with correct parameters"""
        from trustgraph.storage.triples.memgraph.write import run, default_ident
        
        run()
        
        mock_launch.assert_called_once_with(
            default_ident,
            "\nGraph writer.  Input is graph edge.  Writes edges to Memgraph.\n"
        )