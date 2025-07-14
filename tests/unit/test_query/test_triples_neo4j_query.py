"""
Tests for Neo4j triples query service
"""

import pytest
from unittest.mock import MagicMock, patch

from trustgraph.query.triples.neo4j.service import Processor
from trustgraph.schema import Value, TriplesQueryRequest


class TestNeo4jQueryProcessor:
    """Test cases for Neo4j query processor"""

    @pytest.fixture
    def processor(self):
        """Create a processor instance for testing"""
        with patch('trustgraph.query.triples.neo4j.service.GraphDatabase'):
            return Processor(
                taskgroup=MagicMock(),
                id='test-neo4j-query',
                graph_host='bolt://localhost:7687'
            )

    def test_create_value_with_http_uri(self, processor):
        """Test create_value with HTTP URI"""
        result = processor.create_value("http://example.com/resource")
        
        assert isinstance(result, Value)
        assert result.value == "http://example.com/resource"
        assert result.is_uri is True

    def test_create_value_with_https_uri(self, processor):
        """Test create_value with HTTPS URI"""
        result = processor.create_value("https://example.com/resource")
        
        assert isinstance(result, Value)
        assert result.value == "https://example.com/resource"
        assert result.is_uri is True

    def test_create_value_with_literal(self, processor):
        """Test create_value with literal value"""
        result = processor.create_value("just a literal string")
        
        assert isinstance(result, Value)
        assert result.value == "just a literal string"
        assert result.is_uri is False

    def test_create_value_with_empty_string(self, processor):
        """Test create_value with empty string"""
        result = processor.create_value("")
        
        assert isinstance(result, Value)
        assert result.value == ""
        assert result.is_uri is False

    def test_create_value_with_partial_uri(self, processor):
        """Test create_value with string that looks like URI but isn't complete"""
        result = processor.create_value("http")
        
        assert isinstance(result, Value)
        assert result.value == "http"
        assert result.is_uri is False

    def test_create_value_with_ftp_uri(self, processor):
        """Test create_value with FTP URI (should not be detected as URI)"""
        result = processor.create_value("ftp://example.com/file")
        
        assert isinstance(result, Value)
        assert result.value == "ftp://example.com/file"
        assert result.is_uri is False

    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    def test_processor_initialization_with_defaults(self, mock_graph_db):
        """Test processor initialization with default parameters"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        assert processor.db == 'neo4j'
        mock_graph_db.driver.assert_called_once_with(
            'bolt://neo4j:7687',
            auth=('neo4j', 'password')
        )

    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    def test_processor_initialization_with_custom_params(self, mock_graph_db):
        """Test processor initialization with custom parameters"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        processor = Processor(
            taskgroup=taskgroup_mock,
            graph_host='bolt://custom:7687',
            username='queryuser',
            password='querypass',
            database='customdb'
        )
        
        assert processor.db == 'customdb'
        mock_graph_db.driver.assert_called_once_with(
            'bolt://custom:7687',
            auth=('queryuser', 'querypass')
        )

    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    @pytest.mark.asyncio
    async def test_query_triples_spo_query(self, mock_graph_db):
        """Test SPO query (all values specified)"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        # Mock query results - both queries return one record each
        mock_records = [MagicMock()]
        mock_driver.execute_query.return_value = (mock_records, None, None)
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Create query request
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=Value(value="http://example.com/subject", is_uri=True),
            p=Value(value="http://example.com/predicate", is_uri=True),
            o=Value(value="literal object", is_uri=False),
            limit=100
        )
        
        result = await processor.query_triples(query)
        
        # Verify both literal and URI queries were executed
        assert mock_driver.execute_query.call_count == 2
        
        # Verify result contains the queried triple (appears twice - once from each query)
        assert len(result) == 2
        assert result[0].s.value == "http://example.com/subject"
        assert result[0].p.value == "http://example.com/predicate"
        assert result[0].o.value == "literal object"

    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    @pytest.mark.asyncio
    async def test_query_triples_sp_query(self, mock_graph_db):
        """Test SP query (subject and predicate specified)"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        # Mock query results with different objects
        mock_record1 = MagicMock()
        mock_record1.data.return_value = {"dest": "literal result"}
        mock_record2 = MagicMock()
        mock_record2.data.return_value = {"dest": "http://example.com/uri_result"}
        
        mock_driver.execute_query.side_effect = [
            ([mock_record1], None, None),  # Literal query
            ([mock_record2], None, None)   # URI query
        ]
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Create query request
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=Value(value="http://example.com/subject", is_uri=True),
            p=Value(value="http://example.com/predicate", is_uri=True),
            o=None,
            limit=100
        )
        
        result = await processor.query_triples(query)
        
        # Verify both literal and URI queries were executed
        assert mock_driver.execute_query.call_count == 2
        
        # Verify results contain different objects
        assert len(result) == 2
        assert result[0].s.value == "http://example.com/subject"
        assert result[0].p.value == "http://example.com/predicate"
        assert result[0].o.value == "literal result"
        
        assert result[1].s.value == "http://example.com/subject"
        assert result[1].p.value == "http://example.com/predicate"
        assert result[1].o.value == "http://example.com/uri_result"

    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    @pytest.mark.asyncio
    async def test_query_triples_wildcard_query(self, mock_graph_db):
        """Test wildcard query (no constraints)"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        # Mock query results
        mock_record1 = MagicMock()
        mock_record1.data.return_value = {"src": "http://example.com/s1", "rel": "http://example.com/p1", "dest": "literal1"}
        mock_record2 = MagicMock()
        mock_record2.data.return_value = {"src": "http://example.com/s2", "rel": "http://example.com/p2", "dest": "http://example.com/o2"}
        
        mock_driver.execute_query.side_effect = [
            ([mock_record1], None, None),  # Literal query
            ([mock_record2], None, None)   # URI query
        ]
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Create query request
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=None,
            p=None,
            o=None,
            limit=100
        )
        
        result = await processor.query_triples(query)
        
        # Verify both literal and URI queries were executed
        assert mock_driver.execute_query.call_count == 2
        
        # Verify results contain different triples
        assert len(result) == 2
        assert result[0].s.value == "http://example.com/s1"
        assert result[0].p.value == "http://example.com/p1"
        assert result[0].o.value == "literal1"
        
        assert result[1].s.value == "http://example.com/s2"
        assert result[1].p.value == "http://example.com/p2"
        assert result[1].o.value == "http://example.com/o2"

    @patch('trustgraph.query.triples.neo4j.service.GraphDatabase')
    @pytest.mark.asyncio
    async def test_query_triples_exception_handling(self, mock_graph_db):
        """Test exception handling during query processing"""
        taskgroup_mock = MagicMock()
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        # Mock execute_query to raise exception
        mock_driver.execute_query.side_effect = Exception("Database connection failed")
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Create query request
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=Value(value="http://example.com/subject", is_uri=True),
            p=None,
            o=None,
            limit=100
        )
        
        # Should raise the exception
        with pytest.raises(Exception, match="Database connection failed"):
            await processor.query_triples(query)

    def test_add_args_method(self):
        """Test that add_args properly configures argument parser"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        # Mock the parent class add_args method
        with patch('trustgraph.query.triples.neo4j.service.TriplesQueryService.add_args') as mock_parent_add_args:
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
        
        with patch('trustgraph.query.triples.neo4j.service.TriplesQueryService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with custom values
        args = parser.parse_args([
            '--graph-host', 'bolt://custom:7687',
            '--username', 'queryuser',
            '--password', 'querypass',
            '--database', 'querydb'
        ])
        
        assert args.graph_host == 'bolt://custom:7687'
        assert args.username == 'queryuser'
        assert args.password == 'querypass'
        assert args.database == 'querydb'

    def test_add_args_short_form(self):
        """Test add_args with short form arguments"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        with patch('trustgraph.query.triples.neo4j.service.TriplesQueryService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with short form
        args = parser.parse_args(['-g', 'bolt://short:7687'])
        
        assert args.graph_host == 'bolt://short:7687'

    @patch('trustgraph.query.triples.neo4j.service.Processor.launch')
    def test_run_function(self, mock_launch):
        """Test the run function calls Processor.launch with correct parameters"""
        from trustgraph.query.triples.neo4j.service import run, default_ident
        
        run()
        
        mock_launch.assert_called_once_with(
            default_ident,
            "\nTriples query service for neo4j.\nInput is a (s, p, o) triple, some values may be null.  Output is a list of\ntriples.\n"
        )