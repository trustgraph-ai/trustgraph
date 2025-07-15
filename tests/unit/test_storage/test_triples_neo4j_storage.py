"""
Tests for Neo4j triples storage service
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from trustgraph.storage.triples.neo4j.write import Processor


class TestNeo4jStorageProcessor:
    """Test cases for Neo4j storage processor"""

    @patch('trustgraph.storage.triples.neo4j.write.GraphDatabase')
    def test_processor_initialization_with_defaults(self, mock_graph_db):
        """Test processor initialization with default parameters"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        assert processor.db == 'neo4j'
        mock_graph_db.driver.assert_called_once_with(
            'bolt://neo4j:7687',
            auth=('neo4j', 'password')
        )

    @patch('trustgraph.storage.triples.neo4j.write.GraphDatabase')
    def test_processor_initialization_with_custom_params(self, mock_graph_db):
        """Test processor initialization with custom parameters"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        processor = Processor(
            taskgroup=taskgroup_mock,
            graph_host='bolt://custom:7687',
            username='testuser',
            password='testpass',
            database='testdb'
        )
        
        assert processor.db == 'testdb'
        mock_graph_db.driver.assert_called_once_with(
            'bolt://custom:7687',
            auth=('testuser', 'testpass')
        )

    @patch('trustgraph.storage.triples.neo4j.write.GraphDatabase')
    def test_create_indexes_success(self, mock_graph_db):
        """Test successful index creation"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Verify index creation queries were executed
        expected_calls = [
            "CREATE INDEX Node_uri FOR (n:Node) ON (n.uri)",
            "CREATE INDEX Literal_value FOR (n:Literal) ON (n.value)",
            "CREATE INDEX Rel_uri FOR ()-[r:Rel]-() ON (r.uri)"
        ]
        
        assert mock_session.run.call_count == 3
        for expected_query in expected_calls:
            mock_session.run.assert_any_call(expected_query)

    @patch('trustgraph.storage.triples.neo4j.write.GraphDatabase')
    def test_create_indexes_with_exceptions(self, mock_graph_db):
        """Test index creation with exceptions (should be ignored)"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        # Make session.run raise exceptions
        mock_session.run.side_effect = Exception("Index already exists")
        
        # Should not raise exception - they should be caught and ignored
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Should have tried to create all 3 indexes despite exceptions
        assert mock_session.run.call_count == 3

    @patch('trustgraph.storage.triples.neo4j.write.GraphDatabase')
    def test_create_node(self, mock_graph_db):
        """Test node creation"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        # Mock execute_query response
        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        mock_driver.execute_query.return_value = mock_result
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Test create_node
        processor.create_node("http://example.com/node")
        
        mock_driver.execute_query.assert_called_with(
            "MERGE (n:Node {uri: $uri})",
            uri="http://example.com/node",
            database_="neo4j"
        )

    @patch('trustgraph.storage.triples.neo4j.write.GraphDatabase')
    def test_create_literal(self, mock_graph_db):
        """Test literal creation"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        # Mock execute_query response
        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        mock_driver.execute_query.return_value = mock_result
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Test create_literal
        processor.create_literal("literal value")
        
        mock_driver.execute_query.assert_called_with(
            "MERGE (n:Literal {value: $value})",
            value="literal value",
            database_="neo4j"
        )

    @patch('trustgraph.storage.triples.neo4j.write.GraphDatabase')
    def test_relate_node(self, mock_graph_db):
        """Test node-to-node relationship creation"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        # Mock execute_query response
        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 0
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        mock_driver.execute_query.return_value = mock_result
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Test relate_node
        processor.relate_node(
            "http://example.com/subject",
            "http://example.com/predicate",
            "http://example.com/object"
        )
        
        mock_driver.execute_query.assert_called_with(
            "MATCH (src:Node {uri: $src}) "
            "MATCH (dest:Node {uri: $dest}) "
            "MERGE (src)-[:Rel {uri: $uri}]->(dest)",
            src="http://example.com/subject",
            dest="http://example.com/object",
            uri="http://example.com/predicate",
            database_="neo4j"
        )

    @patch('trustgraph.storage.triples.neo4j.write.GraphDatabase')
    def test_relate_literal(self, mock_graph_db):
        """Test node-to-literal relationship creation"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        # Mock execute_query response
        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 0
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        mock_driver.execute_query.return_value = mock_result
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Test relate_literal
        processor.relate_literal(
            "http://example.com/subject",
            "http://example.com/predicate",
            "literal value"
        )
        
        mock_driver.execute_query.assert_called_with(
            "MATCH (src:Node {uri: $src}) "
            "MATCH (dest:Literal {value: $dest}) "
            "MERGE (src)-[:Rel {uri: $uri}]->(dest)",
            src="http://example.com/subject",
            dest="literal value",
            uri="http://example.com/predicate",
            database_="neo4j"
        )

    @patch('trustgraph.storage.triples.neo4j.write.GraphDatabase')
    @pytest.mark.asyncio
    async def test_handle_triples_with_uri_object(self, mock_graph_db):
        """Test handling triples message with URI object"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        # Mock execute_query response
        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        mock_driver.execute_query.return_value = mock_result
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Create mock triple with URI object
        triple = MagicMock()
        triple.s.value = "http://example.com/subject"
        triple.p.value = "http://example.com/predicate"
        triple.o.value = "http://example.com/object"
        triple.o.is_uri = True
        
        # Create mock message
        mock_message = MagicMock()
        mock_message.triples = [triple]
        
        await processor.store_triples(mock_message)
        
        # Verify create_node was called for subject and object
        # Verify relate_node was called
        expected_calls = [
            # Subject node creation
            (
                "MERGE (n:Node {uri: $uri})",
                {"uri": "http://example.com/subject", "database_": "neo4j"}
            ),
            # Object node creation
            (
                "MERGE (n:Node {uri: $uri})",
                {"uri": "http://example.com/object", "database_": "neo4j"}
            ),
            # Relationship creation
            (
                "MATCH (src:Node {uri: $src}) "
                "MATCH (dest:Node {uri: $dest}) "
                "MERGE (src)-[:Rel {uri: $uri}]->(dest)",
                {
                    "src": "http://example.com/subject",
                    "dest": "http://example.com/object",
                    "uri": "http://example.com/predicate",
                    "database_": "neo4j"
                }
            )
        ]
        
        assert mock_driver.execute_query.call_count == 3
        for expected_query, expected_params in expected_calls:
            mock_driver.execute_query.assert_any_call(expected_query, **expected_params)

    @patch('trustgraph.storage.triples.neo4j.write.GraphDatabase')
    @pytest.mark.asyncio
    async def test_store_triples_with_literal_object(self, mock_graph_db):
        """Test handling triples message with literal object"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        # Mock execute_query response
        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        mock_driver.execute_query.return_value = mock_result
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Create mock triple with literal object
        triple = MagicMock()
        triple.s.value = "http://example.com/subject"
        triple.p.value = "http://example.com/predicate"
        triple.o.value = "literal value"
        triple.o.is_uri = False
        
        # Create mock message
        mock_message = MagicMock()
        mock_message.triples = [triple]
        
        await processor.store_triples(mock_message)
        
        # Verify create_node was called for subject
        # Verify create_literal was called for object
        # Verify relate_literal was called
        expected_calls = [
            # Subject node creation
            (
                "MERGE (n:Node {uri: $uri})",
                {"uri": "http://example.com/subject", "database_": "neo4j"}
            ),
            # Literal creation
            (
                "MERGE (n:Literal {value: $value})",
                {"value": "literal value", "database_": "neo4j"}
            ),
            # Relationship creation
            (
                "MATCH (src:Node {uri: $src}) "
                "MATCH (dest:Literal {value: $dest}) "
                "MERGE (src)-[:Rel {uri: $uri}]->(dest)",
                {
                    "src": "http://example.com/subject",
                    "dest": "literal value",
                    "uri": "http://example.com/predicate",
                    "database_": "neo4j"
                }
            )
        ]
        
        assert mock_driver.execute_query.call_count == 3
        for expected_query, expected_params in expected_calls:
            mock_driver.execute_query.assert_any_call(expected_query, **expected_params)

    @patch('trustgraph.storage.triples.neo4j.write.GraphDatabase')
    @pytest.mark.asyncio
    async def test_store_multiple_triples(self, mock_graph_db):
        """Test handling message with multiple triples"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        # Mock execute_query response
        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        mock_driver.execute_query.return_value = mock_result
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Create mock triples
        triple1 = MagicMock()
        triple1.s.value = "http://example.com/subject1"
        triple1.p.value = "http://example.com/predicate1"
        triple1.o.value = "http://example.com/object1"
        triple1.o.is_uri = True
        
        triple2 = MagicMock()
        triple2.s.value = "http://example.com/subject2"
        triple2.p.value = "http://example.com/predicate2"
        triple2.o.value = "literal value"
        triple2.o.is_uri = False
        
        # Create mock message
        mock_message = MagicMock()
        mock_message.triples = [triple1, triple2]
        
        await processor.store_triples(mock_message)
        
        # Should have processed both triples
        # Triple1: 2 nodes + 1 relationship = 3 calls
        # Triple2: 1 node + 1 literal + 1 relationship = 3 calls
        # Total: 6 calls
        assert mock_driver.execute_query.call_count == 6

    @patch('trustgraph.storage.triples.neo4j.write.GraphDatabase')
    @pytest.mark.asyncio
    async def test_store_empty_triples(self, mock_graph_db):
        """Test handling message with no triples"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Create mock message with empty triples
        mock_message = MagicMock()
        mock_message.triples = []
        
        await processor.store_triples(mock_message)
        
        # Should not have made any execute_query calls beyond index creation
        # Only index creation calls should have been made during initialization
        mock_driver.execute_query.assert_not_called()

    def test_add_args_method(self):
        """Test that add_args properly configures argument parser"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        # Mock the parent class add_args method
        with patch('trustgraph.storage.triples.neo4j.write.TriplesStoreService.add_args') as mock_parent_add_args:
            Processor.add_args(parser)
            
            # Verify parent add_args was called
            mock_parent_add_args.assert_called_once()
        
        # Verify our specific arguments were added
        # Parse empty args to check defaults
        args = parser.parse_args([])
        
        assert hasattr(args, 'graph_host')
        assert args.graph_host == 'bolt://neo4j:7687'
        assert hasattr(args, 'username')
        assert args.username == 'neo4j'
        assert hasattr(args, 'password')
        assert args.password == 'password'
        assert hasattr(args, 'database')
        assert args.database == 'neo4j'

    def test_add_args_with_custom_values(self):
        """Test add_args with custom command line values"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        with patch('trustgraph.storage.triples.neo4j.write.TriplesStoreService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with custom values
        args = parser.parse_args([
            '--graph_host', 'bolt://custom:7687',
            '--username', 'testuser',
            '--password', 'testpass',
            '--database', 'testdb'
        ])
        
        assert args.graph_host == 'bolt://custom:7687'
        assert args.username == 'testuser'
        assert args.password == 'testpass'
        assert args.database == 'testdb'

    def test_add_args_short_form(self):
        """Test add_args with short form arguments"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        with patch('trustgraph.storage.triples.neo4j.write.TriplesStoreService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with short form
        args = parser.parse_args(['-g', 'bolt://short:7687'])
        
        assert args.graph_host == 'bolt://short:7687'

    @patch('trustgraph.storage.triples.neo4j.write.Processor.launch')
    def test_run_function(self, mock_launch):
        """Test the run function calls Processor.launch with correct parameters"""
        from trustgraph.storage.triples.neo4j.write import run, default_ident
        
        run()
        
        mock_launch.assert_called_once_with(
            default_ident,
            "\nGraph writer.  Input is graph edge.  Writes edges to Neo4j graph.\n"
        )

    @patch('trustgraph.storage.triples.neo4j.write.GraphDatabase')
    @pytest.mark.asyncio
    async def test_store_triples_with_special_characters(self, mock_graph_db):
        """Test handling triples with special characters and unicode"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        # Mock execute_query response
        mock_result = MagicMock()
        mock_summary = MagicMock()
        mock_summary.counters.nodes_created = 1
        mock_summary.result_available_after = 10
        mock_result.summary = mock_summary
        mock_driver.execute_query.return_value = mock_result
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Create triple with special characters
        triple = MagicMock()
        triple.s.value = "http://example.com/subject with spaces"
        triple.p.value = "http://example.com/predicate:with/symbols"
        triple.o.value = 'literal with "quotes" and unicode: ñáéíóú'
        triple.o.is_uri = False
        
        mock_message = MagicMock()
        mock_message.triples = [triple]
        
        await processor.store_triples(mock_message)
        
        # Verify the triple was processed with special characters preserved
        mock_driver.execute_query.assert_any_call(
            "MERGE (n:Node {uri: $uri})",
            uri="http://example.com/subject with spaces",
            database_="neo4j"
        )
        
        mock_driver.execute_query.assert_any_call(
            "MERGE (n:Literal {value: $value})",
            value='literal with "quotes" and unicode: ñáéíóú',
            database_="neo4j"
        )
        
        mock_driver.execute_query.assert_any_call(
            "MATCH (src:Node {uri: $src}) "
            "MATCH (dest:Literal {value: $dest}) "
            "MERGE (src)-[:Rel {uri: $uri}]->(dest)",
            src="http://example.com/subject with spaces",
            dest='literal with "quotes" and unicode: ñáéíóú',
            uri="http://example.com/predicate:with/symbols",
            database_="neo4j"
        )
