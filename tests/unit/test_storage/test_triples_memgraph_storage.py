"""
Tests for Memgraph triples storage service
"""

import pytest
from unittest.mock import MagicMock, patch

from trustgraph.storage.triples.memgraph.write import Processor
from trustgraph.schema import Term, Triple, IRI, LITERAL


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
            s=Term(type=IRI, iri='http://example.com/subject'),
            p=Term(type=IRI, iri='http://example.com/predicate'),
            o=Term(type=LITERAL, value='literal object')
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
        
        # Verify index creation calls (now includes user/collection indexes)
        expected_calls = [
            "CREATE INDEX ON :Node",
            "CREATE INDEX ON :Node(uri)",
            "CREATE INDEX ON :Literal",
            "CREATE INDEX ON :Literal(value)",
            "CREATE INDEX ON :Node(user)",
            "CREATE INDEX ON :Node(collection)",
            "CREATE INDEX ON :Literal(user)",
            "CREATE INDEX ON :Literal(collection)"
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
        
        # Verify all index creation calls were attempted (8 total)
        assert mock_session.run.call_count == 8

    def test_create_node(self, processor):
        """Test node creation"""
        test_uri = 'http://example.com/node'
        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        
        processor.io.execute_query.return_value = mock_result
        
        processor.create_node(test_uri, "test_user", "test_collection")
        
        processor.io.execute_query.assert_called_once_with(
            "MERGE (n:Node {uri: $uri, user: $user, collection: $collection})",
            uri=test_uri,
            user="test_user",
            collection="test_collection",
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
        
        processor.create_literal(test_value, "test_user", "test_collection")
        
        processor.io.execute_query.assert_called_once_with(
            "MERGE (n:Literal {value: $value, user: $user, collection: $collection})",
            value=test_value,
            user="test_user",
            collection="test_collection",
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
        
        processor.relate_node(src_uri, pred_uri, dest_uri, "test_user", "test_collection")
        
        processor.io.execute_query.assert_called_once_with(
            "MATCH (src:Node {uri: $src, user: $user, collection: $collection}) "
            "MATCH (dest:Node {uri: $dest, user: $user, collection: $collection}) "
            "MERGE (src)-[:Rel {uri: $uri, user: $user, collection: $collection}]->(dest)",
            src=src_uri, dest=dest_uri, uri=pred_uri,
            user="test_user", collection="test_collection",
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
        
        processor.relate_literal(src_uri, pred_uri, literal_value, "test_user", "test_collection")
        
        processor.io.execute_query.assert_called_once_with(
            "MATCH (src:Node {uri: $src, user: $user, collection: $collection}) "
            "MATCH (dest:Literal {value: $dest, user: $user, collection: $collection}) "
            "MERGE (src)-[:Rel {uri: $uri, user: $user, collection: $collection}]->(dest)",
            src=src_uri, dest=literal_value, uri=pred_uri,
            user="test_user", collection="test_collection",
            database_=processor.db
        )

    def test_create_triple_with_uri_object(self, processor):
        """Test triple creation with URI object"""
        mock_tx = MagicMock()
        
        triple = Triple(
            s=Term(type=IRI, iri='http://example.com/subject'),
            p=Term(type=IRI, iri='http://example.com/predicate'),
            o=Term(type=IRI, iri='http://example.com/object')
        )
        
        processor.create_triple(mock_tx, triple, "test_user", "test_collection")
        
        # Verify transaction calls
        expected_calls = [
            # Create subject node
            ("MERGE (n:Node {uri: $uri, user: $user, collection: $collection})", 
             {'uri': 'http://example.com/subject', 'user': 'test_user', 'collection': 'test_collection'}),
            # Create object node  
            ("MERGE (n:Node {uri: $uri, user: $user, collection: $collection})", 
             {'uri': 'http://example.com/object', 'user': 'test_user', 'collection': 'test_collection'}),
            # Create relationship
            ("MATCH (src:Node {uri: $src, user: $user, collection: $collection}) "
             "MATCH (dest:Node {uri: $dest, user: $user, collection: $collection}) "
             "MERGE (src)-[:Rel {uri: $uri, user: $user, collection: $collection}]->(dest)",
             {'src': 'http://example.com/subject', 'dest': 'http://example.com/object', 'uri': 'http://example.com/predicate',
              'user': 'test_user', 'collection': 'test_collection'})
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
            s=Term(type=IRI, iri='http://example.com/subject'),
            p=Term(type=IRI, iri='http://example.com/predicate'),
            o=Term(type=LITERAL, value='literal object')
        )
        
        processor.create_triple(mock_tx, triple, "test_user", "test_collection")
        
        # Verify transaction calls
        expected_calls = [
            # Create subject node
            ("MERGE (n:Node {uri: $uri, user: $user, collection: $collection})", 
             {'uri': 'http://example.com/subject', 'user': 'test_user', 'collection': 'test_collection'}),
            # Create literal object
            ("MERGE (n:Literal {value: $value, user: $user, collection: $collection})", 
             {'value': 'literal object', 'user': 'test_user', 'collection': 'test_collection'}),
            # Create relationship
            ("MATCH (src:Node {uri: $src, user: $user, collection: $collection}) "
             "MATCH (dest:Literal {value: $dest, user: $user, collection: $collection}) "
             "MERGE (src)-[:Rel {uri: $uri, user: $user, collection: $collection}]->(dest)",
             {'src': 'http://example.com/subject', 'dest': 'literal object', 'uri': 'http://example.com/predicate',
              'user': 'test_user', 'collection': 'test_collection'})
        ]
        
        assert mock_tx.run.call_count == 3
        for i, (expected_query, expected_params) in enumerate(expected_calls):
            actual_call = mock_tx.run.call_args_list[i]
            assert actual_call[0][0] == expected_query
            assert actual_call[1] == expected_params

    @pytest.mark.asyncio
    async def test_store_triples_single_triple(self, processor, mock_message):
        """Test storing a single triple"""
        # Mock the execute_query method used by the direct methods
        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        processor.io.execute_query.return_value = mock_result
        
        # Reset the mock to clear initialization calls
        processor.io.execute_query.reset_mock()
        
        # Mock collection_exists to bypass validation in unit tests

        
        with patch.object(processor, 'collection_exists', return_value=True):

        
            await processor.store_triples(mock_message)
        
        # Verify execute_query was called for create_node, create_literal, and relate_literal
        # (since mock_message has a literal object)
        assert processor.io.execute_query.call_count == 3
        
        # Verify user/collection parameters were included
        for call in processor.io.execute_query.call_args_list:
            call_kwargs = call.kwargs if hasattr(call, 'kwargs') else call[1]
            assert 'user' in call_kwargs
            assert 'collection' in call_kwargs

    @pytest.mark.asyncio
    async def test_store_triples_multiple_triples(self, processor):
        """Test storing multiple triples"""
        # Mock the execute_query method used by the direct methods
        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        processor.io.execute_query.return_value = mock_result
        
        # Reset the mock to clear initialization calls
        processor.io.execute_query.reset_mock()
        
        # Create message with multiple triples
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        triple1 = Triple(
            s=Term(type=IRI, iri='http://example.com/subject1'),
            p=Term(type=IRI, iri='http://example.com/predicate1'),
            o=Term(type=LITERAL, value='literal object1')
        )
        triple2 = Triple(
            s=Term(type=IRI, iri='http://example.com/subject2'),
            p=Term(type=IRI, iri='http://example.com/predicate2'),
            o=Term(type=IRI, iri='http://example.com/object2')
        )
        message.triples = [triple1, triple2]
        
        # Mock collection_exists to bypass validation in unit tests

        
        with patch.object(processor, 'collection_exists', return_value=True):

        
            await processor.store_triples(message)
        
        # Verify execute_query was called:
        # Triple1: create_node(s) + create_literal(o) + relate_literal = 3 calls
        # Triple2: create_node(s) + create_node(o) + relate_node = 3 calls
        # Total: 6 calls
        assert processor.io.execute_query.call_count == 6
        
        # Verify user/collection parameters were included in all calls
        for call in processor.io.execute_query.call_args_list:
            call_kwargs = call.kwargs if hasattr(call, 'kwargs') else call[1]
            assert call_kwargs['user'] == 'test_user'
            assert call_kwargs['collection'] == 'test_collection'

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
        
        # Mock collection_exists to bypass validation in unit tests

        
        with patch.object(processor, 'collection_exists', return_value=True):

        
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