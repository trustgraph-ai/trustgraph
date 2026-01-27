"""
Tests for FalkorDB triples query service
"""

import pytest
from unittest.mock import MagicMock, patch

from trustgraph.query.triples.falkordb.service import Processor
from trustgraph.schema import Term, TriplesQueryRequest, IRI, LITERAL


class TestFalkorDBQueryProcessor:
    """Test cases for FalkorDB query processor"""

    @pytest.fixture
    def processor(self):
        """Create a processor instance for testing"""
        with patch('trustgraph.query.triples.falkordb.service.FalkorDB'):
            return Processor(
                taskgroup=MagicMock(),
                id='test-falkordb-query',
                graph_url='falkor://localhost:6379'
            )

    def test_create_value_with_http_uri(self, processor):
        """Test create_value with HTTP URI"""
        result = processor.create_value("http://example.com/resource")

        assert isinstance(result, Term)
        assert result.iri == "http://example.com/resource"
        assert result.type == IRI

    def test_create_value_with_https_uri(self, processor):
        """Test create_value with HTTPS URI"""
        result = processor.create_value("https://example.com/resource")

        assert isinstance(result, Term)
        assert result.iri == "https://example.com/resource"
        assert result.type == IRI

    def test_create_value_with_literal(self, processor):
        """Test create_value with literal value"""
        result = processor.create_value("just a literal string")

        assert isinstance(result, Term)
        assert result.value == "just a literal string"
        assert result.type == LITERAL

    def test_create_value_with_empty_string(self, processor):
        """Test create_value with empty string"""
        result = processor.create_value("")

        assert isinstance(result, Term)
        assert result.value == ""
        assert result.type == LITERAL

    def test_create_value_with_partial_uri(self, processor):
        """Test create_value with string that looks like URI but isn't complete"""
        result = processor.create_value("http")

        assert isinstance(result, Term)
        assert result.value == "http"
        assert result.type == LITERAL

    def test_create_value_with_ftp_uri(self, processor):
        """Test create_value with FTP URI (should not be detected as URI)"""
        result = processor.create_value("ftp://example.com/file")

        assert isinstance(result, Term)
        assert result.value == "ftp://example.com/file"
        assert result.type == LITERAL

    @patch('trustgraph.query.triples.falkordb.service.FalkorDB')
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

    @patch('trustgraph.query.triples.falkordb.service.FalkorDB')
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
            database='customdb'
        )
        
        assert processor.db == 'customdb'
        mock_falkordb.from_url.assert_called_once_with('falkor://custom:6379')
        mock_client.select_graph.assert_called_once_with('customdb')

    @patch('trustgraph.query.triples.falkordb.service.FalkorDB')
    @pytest.mark.asyncio
    async def test_query_triples_spo_query(self, mock_falkordb):
        """Test SPO query (all values specified)"""
        taskgroup_mock = MagicMock()
        mock_client = MagicMock()
        mock_graph = MagicMock()
        mock_falkordb.from_url.return_value = mock_client
        mock_client.select_graph.return_value = mock_graph
        
        # Mock query results - both queries return one record each
        mock_result = MagicMock()
        mock_result.result_set = [["record1"]]
        mock_graph.query.return_value = mock_result
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Create query request
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=Term(type=IRI, iri="http://example.com/subject"),
            p=Term(type=IRI, iri="http://example.com/predicate"),
            o=Term(type=LITERAL, value="literal object"),
            limit=100
        )
        
        result = await processor.query_triples(query)
        
        # Verify both literal and URI queries were executed
        assert mock_graph.query.call_count == 2
        
        # Verify result contains the queried triple (appears twice - once from each query)
        assert len(result) == 2
        assert result[0].s.value == "http://example.com/subject"
        assert result[0].p.value == "http://example.com/predicate"
        assert result[0].o.value == "literal object"

    @patch('trustgraph.query.triples.falkordb.service.FalkorDB')
    @pytest.mark.asyncio
    async def test_query_triples_sp_query(self, mock_falkordb):
        """Test SP query (subject and predicate specified)"""
        taskgroup_mock = MagicMock()
        mock_client = MagicMock()
        mock_graph = MagicMock()
        mock_falkordb.from_url.return_value = mock_client
        mock_client.select_graph.return_value = mock_graph
        
        # Mock query results with different objects
        mock_result1 = MagicMock()
        mock_result1.result_set = [["literal result"]]
        mock_result2 = MagicMock()
        mock_result2.result_set = [["http://example.com/uri_result"]]
        
        mock_graph.query.side_effect = [mock_result1, mock_result2]
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Create query request
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=Term(type=IRI, iri="http://example.com/subject"),
            p=Term(type=IRI, iri="http://example.com/predicate"),
            o=None,
            limit=100
        )
        
        result = await processor.query_triples(query)
        
        # Verify both literal and URI queries were executed
        assert mock_graph.query.call_count == 2
        
        # Verify results contain different objects
        assert len(result) == 2
        assert result[0].s.value == "http://example.com/subject"
        assert result[0].p.value == "http://example.com/predicate"
        assert result[0].o.value == "literal result"
        
        assert result[1].s.value == "http://example.com/subject"
        assert result[1].p.value == "http://example.com/predicate"
        assert result[1].o.value == "http://example.com/uri_result"

    @patch('trustgraph.query.triples.falkordb.service.FalkorDB')
    @pytest.mark.asyncio
    async def test_query_triples_so_query(self, mock_falkordb):
        """Test SO query (subject and object specified)"""
        taskgroup_mock = MagicMock()
        mock_client = MagicMock()
        mock_graph = MagicMock()
        mock_falkordb.from_url.return_value = mock_client
        mock_client.select_graph.return_value = mock_graph
        
        # Mock query results with different predicates
        mock_result1 = MagicMock()
        mock_result1.result_set = [["http://example.com/pred1"]]
        mock_result2 = MagicMock()
        mock_result2.result_set = [["http://example.com/pred2"]]
        
        mock_graph.query.side_effect = [mock_result1, mock_result2]
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Create query request
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=Term(type=IRI, iri="http://example.com/subject"),
            p=None,
            o=Term(type=LITERAL, value="literal object"),
            limit=100
        )
        
        result = await processor.query_triples(query)
        
        # Verify both literal and URI queries were executed
        assert mock_graph.query.call_count == 2
        
        # Verify results contain different predicates
        assert len(result) == 2
        assert result[0].s.value == "http://example.com/subject"
        assert result[0].p.value == "http://example.com/pred1"
        assert result[0].o.value == "literal object"
        
        assert result[1].s.value == "http://example.com/subject"
        assert result[1].p.value == "http://example.com/pred2"
        assert result[1].o.value == "literal object"

    @patch('trustgraph.query.triples.falkordb.service.FalkorDB')
    @pytest.mark.asyncio
    async def test_query_triples_s_query(self, mock_falkordb):
        """Test S query (subject only)"""
        taskgroup_mock = MagicMock()
        mock_client = MagicMock()
        mock_graph = MagicMock()
        mock_falkordb.from_url.return_value = mock_client
        mock_client.select_graph.return_value = mock_graph
        
        # Mock query results with different predicate-object pairs
        mock_result1 = MagicMock()
        mock_result1.result_set = [["http://example.com/pred1", "literal1"]]
        mock_result2 = MagicMock()
        mock_result2.result_set = [["http://example.com/pred2", "http://example.com/uri2"]]
        
        mock_graph.query.side_effect = [mock_result1, mock_result2]
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Create query request
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=Term(type=IRI, iri="http://example.com/subject"),
            p=None,
            o=None,
            limit=100
        )
        
        result = await processor.query_triples(query)
        
        # Verify both literal and URI queries were executed
        assert mock_graph.query.call_count == 2
        
        # Verify results contain different predicate-object pairs
        assert len(result) == 2
        assert result[0].s.value == "http://example.com/subject"
        assert result[0].p.value == "http://example.com/pred1"
        assert result[0].o.value == "literal1"
        
        assert result[1].s.value == "http://example.com/subject"
        assert result[1].p.value == "http://example.com/pred2"
        assert result[1].o.value == "http://example.com/uri2"

    @patch('trustgraph.query.triples.falkordb.service.FalkorDB')
    @pytest.mark.asyncio
    async def test_query_triples_po_query(self, mock_falkordb):
        """Test PO query (predicate and object specified)"""
        taskgroup_mock = MagicMock()
        mock_client = MagicMock()
        mock_graph = MagicMock()
        mock_falkordb.from_url.return_value = mock_client
        mock_client.select_graph.return_value = mock_graph
        
        # Mock query results with different subjects
        mock_result1 = MagicMock()
        mock_result1.result_set = [["http://example.com/subj1"]]
        mock_result2 = MagicMock()
        mock_result2.result_set = [["http://example.com/subj2"]]
        
        mock_graph.query.side_effect = [mock_result1, mock_result2]
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Create query request
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=None,
            p=Term(type=IRI, iri="http://example.com/predicate"),
            o=Term(type=LITERAL, value="literal object"),
            limit=100
        )
        
        result = await processor.query_triples(query)
        
        # Verify both literal and URI queries were executed
        assert mock_graph.query.call_count == 2
        
        # Verify results contain different subjects
        assert len(result) == 2
        assert result[0].s.value == "http://example.com/subj1"
        assert result[0].p.value == "http://example.com/predicate"
        assert result[0].o.value == "literal object"
        
        assert result[1].s.value == "http://example.com/subj2"
        assert result[1].p.value == "http://example.com/predicate"
        assert result[1].o.value == "literal object"

    @patch('trustgraph.query.triples.falkordb.service.FalkorDB')
    @pytest.mark.asyncio
    async def test_query_triples_p_query(self, mock_falkordb):
        """Test P query (predicate only)"""
        taskgroup_mock = MagicMock()
        mock_client = MagicMock()
        mock_graph = MagicMock()
        mock_falkordb.from_url.return_value = mock_client
        mock_client.select_graph.return_value = mock_graph
        
        # Mock query results with different subject-object pairs
        mock_result1 = MagicMock()
        mock_result1.result_set = [["http://example.com/subj1", "literal1"]]
        mock_result2 = MagicMock()
        mock_result2.result_set = [["http://example.com/subj2", "http://example.com/uri2"]]
        
        mock_graph.query.side_effect = [mock_result1, mock_result2]
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Create query request
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=None,
            p=Term(type=IRI, iri="http://example.com/predicate"),
            o=None,
            limit=100
        )
        
        result = await processor.query_triples(query)
        
        # Verify both literal and URI queries were executed
        assert mock_graph.query.call_count == 2
        
        # Verify results contain different subject-object pairs
        assert len(result) == 2
        assert result[0].s.value == "http://example.com/subj1"
        assert result[0].p.value == "http://example.com/predicate"
        assert result[0].o.value == "literal1"
        
        assert result[1].s.value == "http://example.com/subj2"
        assert result[1].p.value == "http://example.com/predicate"
        assert result[1].o.value == "http://example.com/uri2"

    @patch('trustgraph.query.triples.falkordb.service.FalkorDB')
    @pytest.mark.asyncio
    async def test_query_triples_o_query(self, mock_falkordb):
        """Test O query (object only)"""
        taskgroup_mock = MagicMock()
        mock_client = MagicMock()
        mock_graph = MagicMock()
        mock_falkordb.from_url.return_value = mock_client
        mock_client.select_graph.return_value = mock_graph
        
        # Mock query results with different subject-predicate pairs
        mock_result1 = MagicMock()
        mock_result1.result_set = [["http://example.com/subj1", "http://example.com/pred1"]]
        mock_result2 = MagicMock()
        mock_result2.result_set = [["http://example.com/subj2", "http://example.com/pred2"]]
        
        mock_graph.query.side_effect = [mock_result1, mock_result2]
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Create query request
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=None,
            p=None,
            o=Term(type=LITERAL, value="literal object"),
            limit=100
        )
        
        result = await processor.query_triples(query)
        
        # Verify both literal and URI queries were executed
        assert mock_graph.query.call_count == 2
        
        # Verify results contain different subject-predicate pairs
        assert len(result) == 2
        assert result[0].s.value == "http://example.com/subj1"
        assert result[0].p.value == "http://example.com/pred1"
        assert result[0].o.value == "literal object"
        
        assert result[1].s.value == "http://example.com/subj2"
        assert result[1].p.value == "http://example.com/pred2"
        assert result[1].o.value == "literal object"

    @patch('trustgraph.query.triples.falkordb.service.FalkorDB')
    @pytest.mark.asyncio
    async def test_query_triples_wildcard_query(self, mock_falkordb):
        """Test wildcard query (no constraints)"""
        taskgroup_mock = MagicMock()
        mock_client = MagicMock()
        mock_graph = MagicMock()
        mock_falkordb.from_url.return_value = mock_client
        mock_client.select_graph.return_value = mock_graph
        
        # Mock query results
        mock_result1 = MagicMock()
        mock_result1.result_set = [["http://example.com/s1", "http://example.com/p1", "literal1"]]
        mock_result2 = MagicMock()
        mock_result2.result_set = [["http://example.com/s2", "http://example.com/p2", "http://example.com/o2"]]
        
        mock_graph.query.side_effect = [mock_result1, mock_result2]
        
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
        assert mock_graph.query.call_count == 2
        
        # Verify results contain different triples
        assert len(result) == 2
        assert result[0].s.value == "http://example.com/s1"
        assert result[0].p.value == "http://example.com/p1"
        assert result[0].o.value == "literal1"
        
        assert result[1].s.value == "http://example.com/s2"
        assert result[1].p.value == "http://example.com/p2"
        assert result[1].o.value == "http://example.com/o2"

    @patch('trustgraph.query.triples.falkordb.service.FalkorDB')
    @pytest.mark.asyncio
    async def test_query_triples_exception_handling(self, mock_falkordb):
        """Test exception handling during query processing"""
        taskgroup_mock = MagicMock()
        mock_client = MagicMock()
        mock_graph = MagicMock()
        mock_falkordb.from_url.return_value = mock_client
        mock_client.select_graph.return_value = mock_graph
        
        # Mock query to raise exception
        mock_graph.query.side_effect = Exception("Database connection failed")
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        # Create query request
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=Term(type=IRI, iri="http://example.com/subject"),
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
        with patch('trustgraph.query.triples.falkordb.service.TriplesQueryService.add_args') as mock_parent_add_args:
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
        
        with patch('trustgraph.query.triples.falkordb.service.TriplesQueryService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with custom values
        args = parser.parse_args([
            '--graph-url', 'falkor://custom:6379',
            '--database', 'querydb'
        ])
        
        assert args.graph_url == 'falkor://custom:6379'
        assert args.database == 'querydb'

    def test_add_args_short_form(self):
        """Test add_args with short form arguments"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        with patch('trustgraph.query.triples.falkordb.service.TriplesQueryService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with short form
        args = parser.parse_args(['-g', 'falkor://short:6379'])
        
        assert args.graph_url == 'falkor://short:6379'

    @patch('trustgraph.query.triples.falkordb.service.Processor.launch')
    def test_run_function(self, mock_launch):
        """Test the run function calls Processor.launch with correct parameters"""
        from trustgraph.query.triples.falkordb.service import run, default_ident
        
        run()
        
        mock_launch.assert_called_once_with(
            default_ident,
            "\nTriples query service for FalkorDB.\nInput is a (s, p, o) triple, some values may be null.  Output is a list of\ntriples.\n"
        )