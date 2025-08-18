"""
Tests for FalkorDB triples storage service
"""

import pytest
from unittest.mock import MagicMock, patch

from trustgraph.storage.triples.falkordb.write import Processor
from trustgraph.schema import Value, Triple


class TestFalkorDBStorageProcessor:
    """Test cases for FalkorDB storage processor"""

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
        with patch('trustgraph.storage.triples.falkordb.write.FalkorDB') as mock_falkordb:
            mock_client = MagicMock()
            mock_graph = MagicMock()
            mock_falkordb.from_url.return_value = mock_client
            mock_client.select_graph.return_value = mock_graph
            
            return Processor(
                taskgroup=MagicMock(),
                id='test-falkordb-storage',
                graph_url='falkor://localhost:6379',
                database='test_db'
            )

    @patch('trustgraph.storage.triples.falkordb.write.FalkorDB')
    def test_processor_initialization_with_defaults(self, mock_falkordb):
        """Test processor initialization with default parameters"""
        taskgroup_mock = MagicMock()
        mock_client = MagicMock()
        mock_graph = MagicMock()
        mock_falkordb.from_url.return_value = mock_client
        mock_client.select_graph.return_value = mock_graph
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        assert processor.db == 'falkordb'
        mock_falkordb.from_url.assert_called_once_with('falkor://falkordb:6379')
        mock_client.select_graph.assert_called_once_with('falkordb')

    @patch('trustgraph.storage.triples.falkordb.write.FalkorDB')
    def test_processor_initialization_with_custom_params(self, mock_falkordb):
        """Test processor initialization with custom parameters"""
        taskgroup_mock = MagicMock()
        mock_client = MagicMock()
        mock_graph = MagicMock()
        mock_falkordb.from_url.return_value = mock_client
        mock_client.select_graph.return_value = mock_graph
        
        processor = Processor(
            taskgroup=taskgroup_mock,
            graph_url='falkor://custom:6379',
            database='custom_db'
        )
        
        assert processor.db == 'custom_db'
        mock_falkordb.from_url.assert_called_once_with('falkor://custom:6379')
        mock_client.select_graph.assert_called_once_with('custom_db')

    def test_create_node(self, processor):
        """Test node creation"""
        test_uri = 'http://example.com/node'
        mock_result = MagicMock()
        mock_result.nodes_created = 1
        mock_result.run_time_ms = 10
        
        processor.io.query.return_value = mock_result
        
        processor.create_node(test_uri)
        
        processor.io.query.assert_called_once_with(
            "MERGE (n:Node {uri: $uri})",
            params={
                "uri": test_uri,
            },
        )

    def test_create_literal(self, processor):
        """Test literal creation"""
        test_value = 'test literal value'
        mock_result = MagicMock()
        mock_result.nodes_created = 1
        mock_result.run_time_ms = 10
        
        processor.io.query.return_value = mock_result
        
        processor.create_literal(test_value)
        
        processor.io.query.assert_called_once_with(
            "MERGE (n:Literal {value: $value})",
            params={
                "value": test_value,
            },
        )

    def test_relate_node(self, processor):
        """Test node-to-node relationship creation"""
        src_uri = 'http://example.com/src'
        pred_uri = 'http://example.com/pred'
        dest_uri = 'http://example.com/dest'
        
        mock_result = MagicMock()
        mock_result.nodes_created = 0
        mock_result.run_time_ms = 5
        
        processor.io.query.return_value = mock_result
        
        processor.relate_node(src_uri, pred_uri, dest_uri)
        
        processor.io.query.assert_called_once_with(
            "MATCH (src:Node {uri: $src}) "
            "MATCH (dest:Node {uri: $dest}) "
            "MERGE (src)-[:Rel {uri: $uri}]->(dest)",
            params={
                "src": src_uri,
                "dest": dest_uri,
                "uri": pred_uri,
            },
        )

    def test_relate_literal(self, processor):
        """Test node-to-literal relationship creation"""
        src_uri = 'http://example.com/src'
        pred_uri = 'http://example.com/pred'
        literal_value = 'literal destination'
        
        mock_result = MagicMock()
        mock_result.nodes_created = 0
        mock_result.run_time_ms = 5
        
        processor.io.query.return_value = mock_result
        
        processor.relate_literal(src_uri, pred_uri, literal_value)
        
        processor.io.query.assert_called_once_with(
            "MATCH (src:Node {uri: $src}) "
            "MATCH (dest:Literal {value: $dest}) "
            "MERGE (src)-[:Rel {uri: $uri}]->(dest)",
            params={
                "src": src_uri,
                "dest": literal_value,
                "uri": pred_uri,
            },
        )

    @pytest.mark.asyncio
    async def test_store_triples_with_uri_object(self, processor):
        """Test storing triple with URI object"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        triple = Triple(
            s=Value(value='http://example.com/subject', is_uri=True),
            p=Value(value='http://example.com/predicate', is_uri=True),
            o=Value(value='http://example.com/object', is_uri=True)
        )
        message.triples = [triple]
        
        mock_result = MagicMock()
        mock_result.nodes_created = 1
        mock_result.run_time_ms = 10
        processor.io.query.return_value = mock_result
        
        await processor.store_triples(message)
        
        # Verify queries were called in the correct order
        expected_calls = [
            # Create subject node
            (("MERGE (n:Node {uri: $uri})",), {"params": {"uri": "http://example.com/subject"}}),
            # Create object node
            (("MERGE (n:Node {uri: $uri})",), {"params": {"uri": "http://example.com/object"}}),
            # Create relationship
            (("MATCH (src:Node {uri: $src}) "
              "MATCH (dest:Node {uri: $dest}) "
              "MERGE (src)-[:Rel {uri: $uri}]->(dest)",), 
             {"params": {"src": "http://example.com/subject", "dest": "http://example.com/object", "uri": "http://example.com/predicate"}}),
        ]
        
        assert processor.io.query.call_count == 3
        for i, (expected_args, expected_kwargs) in enumerate(expected_calls):
            actual_call = processor.io.query.call_args_list[i]
            assert actual_call[0] == expected_args
            assert actual_call[1] == expected_kwargs

    @pytest.mark.asyncio
    async def test_store_triples_with_literal_object(self, processor, mock_message):
        """Test storing triple with literal object"""
        mock_result = MagicMock()
        mock_result.nodes_created = 1
        mock_result.run_time_ms = 10
        processor.io.query.return_value = mock_result
        
        await processor.store_triples(mock_message)
        
        # Verify queries were called in the correct order
        expected_calls = [
            # Create subject node
            (("MERGE (n:Node {uri: $uri})",), {"params": {"uri": "http://example.com/subject"}}),
            # Create literal object
            (("MERGE (n:Literal {value: $value})",), {"params": {"value": "literal object"}}),
            # Create relationship
            (("MATCH (src:Node {uri: $src}) "
              "MATCH (dest:Literal {value: $dest}) "
              "MERGE (src)-[:Rel {uri: $uri}]->(dest)",), 
             {"params": {"src": "http://example.com/subject", "dest": "literal object", "uri": "http://example.com/predicate"}}),
        ]
        
        assert processor.io.query.call_count == 3
        for i, (expected_args, expected_kwargs) in enumerate(expected_calls):
            actual_call = processor.io.query.call_args_list[i]
            assert actual_call[0] == expected_args
            assert actual_call[1] == expected_kwargs

    @pytest.mark.asyncio
    async def test_store_triples_multiple_triples(self, processor):
        """Test storing multiple triples"""
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
        
        mock_result = MagicMock()
        mock_result.nodes_created = 1
        mock_result.run_time_ms = 10
        processor.io.query.return_value = mock_result
        
        await processor.store_triples(message)
        
        # Verify total number of queries (3 per triple)
        assert processor.io.query.call_count == 6
        
        # Verify first triple operations
        first_triple_calls = processor.io.query.call_args_list[0:3]
        assert first_triple_calls[0][1]["params"]["uri"] == "http://example.com/subject1"
        assert first_triple_calls[1][1]["params"]["value"] == "literal object1"
        assert first_triple_calls[2][1]["params"]["src"] == "http://example.com/subject1"
        
        # Verify second triple operations
        second_triple_calls = processor.io.query.call_args_list[3:6]
        assert second_triple_calls[0][1]["params"]["uri"] == "http://example.com/subject2"
        assert second_triple_calls[1][1]["params"]["uri"] == "http://example.com/object2"
        assert second_triple_calls[2][1]["params"]["src"] == "http://example.com/subject2"

    @pytest.mark.asyncio
    async def test_store_triples_empty_list(self, processor):
        """Test storing empty triples list"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        message.triples = []
        
        await processor.store_triples(message)
        
        # Verify no queries were made
        processor.io.query.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_triples_mixed_objects(self, processor):
        """Test storing triples with mixed URI and literal objects"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        triple1 = Triple(
            s=Value(value='http://example.com/subject1', is_uri=True),
            p=Value(value='http://example.com/predicate1', is_uri=True),
            o=Value(value='literal object', is_uri=False)
        )
        triple2 = Triple(
            s=Value(value='http://example.com/subject2', is_uri=True),
            p=Value(value='http://example.com/predicate2', is_uri=True),
            o=Value(value='http://example.com/object2', is_uri=True)
        )
        message.triples = [triple1, triple2]
        
        mock_result = MagicMock()
        mock_result.nodes_created = 1
        mock_result.run_time_ms = 10
        processor.io.query.return_value = mock_result
        
        await processor.store_triples(message)
        
        # Verify total number of queries (3 per triple)
        assert processor.io.query.call_count == 6
        
        # Verify first triple creates literal
        assert "Literal" in processor.io.query.call_args_list[1][0][0]
        assert processor.io.query.call_args_list[1][1]["params"]["value"] == "literal object"
        
        # Verify second triple creates node
        assert "Node" in processor.io.query.call_args_list[4][0][0]
        assert processor.io.query.call_args_list[4][1]["params"]["uri"] == "http://example.com/object2"

    def test_add_args_method(self):
        """Test that add_args properly configures argument parser"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        # Mock the parent class add_args method
        with patch('trustgraph.storage.triples.falkordb.write.TriplesStoreService.add_args') as mock_parent_add_args:
            Processor.add_args(parser)
            
            # Verify parent add_args was called
            mock_parent_add_args.assert_called_once()
        
        # Verify our specific arguments were added
        # Parse empty args to check defaults
        args = parser.parse_args([])
        
        assert hasattr(args, 'graph_url')
        assert args.graph_url == 'falkor://falkordb:6379'
        assert hasattr(args, 'database')
        assert args.database == 'falkordb'

    def test_add_args_with_custom_values(self):
        """Test add_args with custom command line values"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        with patch('trustgraph.storage.triples.falkordb.write.TriplesStoreService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with custom values
        args = parser.parse_args([
            '--graph-url', 'falkor://custom:6379',
            '--database', 'custom_db'
        ])
        
        assert args.graph_url == 'falkor://custom:6379'
        assert args.database == 'custom_db'

    def test_add_args_short_form(self):
        """Test add_args with short form arguments"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        with patch('trustgraph.storage.triples.falkordb.write.TriplesStoreService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with short form
        args = parser.parse_args(['-g', 'falkor://short:6379'])
        
        assert args.graph_url == 'falkor://short:6379'

    @patch('trustgraph.storage.triples.falkordb.write.Processor.launch')
    def test_run_function(self, mock_launch):
        """Test the run function calls Processor.launch with correct parameters"""
        from trustgraph.storage.triples.falkordb.write import run, default_ident
        
        run()
        
        mock_launch.assert_called_once_with(
            default_ident,
            "\nGraph writer.  Input is graph edge.  Writes edges to FalkorDB graph.\n"
        )

    def test_create_node_with_special_characters(self, processor):
        """Test node creation with special characters in URI"""
        test_uri = 'http://example.com/node with spaces & symbols'
        mock_result = MagicMock()
        mock_result.nodes_created = 1
        mock_result.run_time_ms = 10
        
        processor.io.query.return_value = mock_result
        
        processor.create_node(test_uri)
        
        processor.io.query.assert_called_once_with(
            "MERGE (n:Node {uri: $uri})",
            params={
                "uri": test_uri,
            },
        )

    def test_create_literal_with_special_characters(self, processor):
        """Test literal creation with special characters"""
        test_value = 'literal with "quotes" and \n newlines'
        mock_result = MagicMock()
        mock_result.nodes_created = 1
        mock_result.run_time_ms = 10
        
        processor.io.query.return_value = mock_result
        
        processor.create_literal(test_value)
        
        processor.io.query.assert_called_once_with(
            "MERGE (n:Literal {value: $value})",
            params={
                "value": test_value,
            },
        )