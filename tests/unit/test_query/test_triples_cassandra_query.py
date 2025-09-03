"""
Tests for Cassandra triples query service
"""

import pytest
from unittest.mock import MagicMock, patch

from trustgraph.query.triples.cassandra.service import Processor
from trustgraph.schema import Value


class TestCassandraQueryProcessor:
    """Test cases for Cassandra query processor"""

    @pytest.fixture
    def processor(self):
        """Create a processor instance for testing"""
        return Processor(
            taskgroup=MagicMock(),
            id='test-cassandra-query',
            graph_host='localhost'
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

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.TrustGraph')
    async def test_query_triples_spo_query(self, mock_trustgraph):
        """Test querying triples with subject, predicate, and object specified"""
        from trustgraph.schema import TriplesQueryRequest, Value
        
        # Setup mock TrustGraph
        mock_tg_instance = MagicMock()
        mock_trustgraph.return_value = mock_tg_instance
        mock_tg_instance.get_spo.return_value = None  # SPO query returns None if found
        
        processor = Processor(
            taskgroup=MagicMock(),
            id='test-cassandra-query',
            cassandra_host='localhost'
        )
        
        # Create query request with all SPO values
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=Value(value='test_subject', is_uri=False),
            p=Value(value='test_predicate', is_uri=False),
            o=Value(value='test_object', is_uri=False),
            limit=100
        )
        
        result = await processor.query_triples(query)
        
        # Verify TrustGraph was created with correct parameters
        mock_trustgraph.assert_called_once_with(
            hosts=['localhost'],
            keyspace='test_user',
            table='test_collection'
        )
        
        # Verify get_spo was called with correct parameters
        mock_tg_instance.get_spo.assert_called_once_with(
            'test_subject', 'test_predicate', 'test_object', limit=100
        )
        
        # Verify result contains the queried triple
        assert len(result) == 1
        assert result[0].s.value == 'test_subject'
        assert result[0].p.value == 'test_predicate'
        assert result[0].o.value == 'test_object'

    def test_processor_initialization_with_defaults(self):
        """Test processor initialization with default parameters"""
        taskgroup_mock = MagicMock()
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        assert processor.cassandra_host == ['cassandra']  # Updated default
        assert processor.cassandra_username is None
        assert processor.cassandra_password is None
        assert processor.table is None

    def test_processor_initialization_with_custom_params(self):
        """Test processor initialization with custom parameters"""
        taskgroup_mock = MagicMock()
        
        processor = Processor(
            taskgroup=taskgroup_mock,
            cassandra_host='cassandra.example.com',
            cassandra_username='queryuser',
            cassandra_password='querypass'
        )
        
        assert processor.cassandra_host == ['cassandra.example.com']
        assert processor.cassandra_username == 'queryuser'
        assert processor.cassandra_password == 'querypass'
        assert processor.table is None

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.TrustGraph')
    async def test_query_triples_sp_pattern(self, mock_trustgraph):
        """Test SP query pattern (subject and predicate, no object)"""
        from trustgraph.schema import TriplesQueryRequest, Value
        
        # Setup mock TrustGraph and response
        mock_tg_instance = MagicMock()
        mock_trustgraph.return_value = mock_tg_instance
        
        mock_result = MagicMock()
        mock_result.o = 'result_object'
        mock_tg_instance.get_sp.return_value = [mock_result]
        
        processor = Processor(taskgroup=MagicMock())
        
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=Value(value='test_subject', is_uri=False),
            p=Value(value='test_predicate', is_uri=False),
            o=None,
            limit=50
        )
        
        result = await processor.query_triples(query)
        
        mock_tg_instance.get_sp.assert_called_once_with('test_subject', 'test_predicate', limit=50)
        assert len(result) == 1
        assert result[0].s.value == 'test_subject'
        assert result[0].p.value == 'test_predicate'
        assert result[0].o.value == 'result_object'

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.TrustGraph')
    async def test_query_triples_s_pattern(self, mock_trustgraph):
        """Test S query pattern (subject only)"""
        from trustgraph.schema import TriplesQueryRequest, Value
        
        mock_tg_instance = MagicMock()
        mock_trustgraph.return_value = mock_tg_instance
        
        mock_result = MagicMock()
        mock_result.p = 'result_predicate'
        mock_result.o = 'result_object'
        mock_tg_instance.get_s.return_value = [mock_result]
        
        processor = Processor(taskgroup=MagicMock())
        
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=Value(value='test_subject', is_uri=False),
            p=None,
            o=None,
            limit=25
        )
        
        result = await processor.query_triples(query)
        
        mock_tg_instance.get_s.assert_called_once_with('test_subject', limit=25)
        assert len(result) == 1
        assert result[0].s.value == 'test_subject'
        assert result[0].p.value == 'result_predicate'
        assert result[0].o.value == 'result_object'

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.TrustGraph')
    async def test_query_triples_p_pattern(self, mock_trustgraph):
        """Test P query pattern (predicate only)"""
        from trustgraph.schema import TriplesQueryRequest, Value
        
        mock_tg_instance = MagicMock()
        mock_trustgraph.return_value = mock_tg_instance
        
        mock_result = MagicMock()
        mock_result.s = 'result_subject'
        mock_result.o = 'result_object'
        mock_tg_instance.get_p.return_value = [mock_result]
        
        processor = Processor(taskgroup=MagicMock())
        
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=None,
            p=Value(value='test_predicate', is_uri=False),
            o=None,
            limit=10
        )
        
        result = await processor.query_triples(query)
        
        mock_tg_instance.get_p.assert_called_once_with('test_predicate', limit=10)
        assert len(result) == 1
        assert result[0].s.value == 'result_subject'
        assert result[0].p.value == 'test_predicate'
        assert result[0].o.value == 'result_object'

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.TrustGraph')
    async def test_query_triples_o_pattern(self, mock_trustgraph):
        """Test O query pattern (object only)"""
        from trustgraph.schema import TriplesQueryRequest, Value
        
        mock_tg_instance = MagicMock()
        mock_trustgraph.return_value = mock_tg_instance
        
        mock_result = MagicMock()
        mock_result.s = 'result_subject'
        mock_result.p = 'result_predicate'
        mock_tg_instance.get_o.return_value = [mock_result]
        
        processor = Processor(taskgroup=MagicMock())
        
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=None,
            p=None,
            o=Value(value='test_object', is_uri=False),
            limit=75
        )
        
        result = await processor.query_triples(query)
        
        mock_tg_instance.get_o.assert_called_once_with('test_object', limit=75)
        assert len(result) == 1
        assert result[0].s.value == 'result_subject'
        assert result[0].p.value == 'result_predicate'
        assert result[0].o.value == 'test_object'

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.TrustGraph')
    async def test_query_triples_get_all_pattern(self, mock_trustgraph):
        """Test query pattern with no constraints (get all)"""
        from trustgraph.schema import TriplesQueryRequest
        
        mock_tg_instance = MagicMock()
        mock_trustgraph.return_value = mock_tg_instance
        
        mock_result = MagicMock()
        mock_result.s = 'all_subject'
        mock_result.p = 'all_predicate'
        mock_result.o = 'all_object'
        mock_tg_instance.get_all.return_value = [mock_result]
        
        processor = Processor(taskgroup=MagicMock())
        
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=None,
            p=None,
            o=None,
            limit=1000
        )
        
        result = await processor.query_triples(query)
        
        mock_tg_instance.get_all.assert_called_once_with(limit=1000)
        assert len(result) == 1
        assert result[0].s.value == 'all_subject'
        assert result[0].p.value == 'all_predicate'
        assert result[0].o.value == 'all_object'

    def test_add_args_method(self):
        """Test that add_args properly configures argument parser"""
        from argparse import ArgumentParser
        
        parser = ArgumentParser()
        
        # Mock the parent class add_args method
        with patch('trustgraph.query.triples.cassandra.service.TriplesQueryService.add_args') as mock_parent_add_args:
            Processor.add_args(parser)
            
            # Verify parent add_args was called
            mock_parent_add_args.assert_called_once_with(parser)
        
        # Verify our specific arguments were added
        args = parser.parse_args([])
        
        assert hasattr(args, 'cassandra_host')
        assert args.cassandra_host == 'cassandra'  # Updated to new parameter name and default
        assert hasattr(args, 'cassandra_username')
        assert args.cassandra_username is None
        assert hasattr(args, 'cassandra_password')
        assert args.cassandra_password is None

    def test_add_args_with_custom_values(self):
        """Test add_args with custom command line values"""
        from argparse import ArgumentParser
        
        parser = ArgumentParser()
        
        with patch('trustgraph.query.triples.cassandra.service.TriplesQueryService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with custom values (new cassandra_* arguments)
        args = parser.parse_args([
            '--cassandra-host', 'query.cassandra.com',
            '--cassandra-username', 'queryuser',
            '--cassandra-password', 'querypass'
        ])
        
        assert args.cassandra_host == 'query.cassandra.com'
        assert args.cassandra_username == 'queryuser'
        assert args.cassandra_password == 'querypass'

    def test_add_args_short_form(self):
        """Test add_args with short form arguments"""
        from argparse import ArgumentParser
        
        parser = ArgumentParser()
        
        with patch('trustgraph.query.triples.cassandra.service.TriplesQueryService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with cassandra arguments (no short form)
        args = parser.parse_args(['--cassandra-host', 'short.query.com'])
        
        assert args.cassandra_host == 'short.query.com'

    @patch('trustgraph.query.triples.cassandra.service.Processor.launch')
    def test_run_function(self, mock_launch):
        """Test the run function calls Processor.launch with correct parameters"""
        from trustgraph.query.triples.cassandra.service import run, default_ident
        
        run()
        
        mock_launch.assert_called_once_with(default_ident, '\nTriples query service.  Input is a (s, p, o) triple, some values may be\nnull.  Output is a list of triples.\n')

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.TrustGraph')
    async def test_query_triples_with_authentication(self, mock_trustgraph):
        """Test querying with username and password authentication"""
        from trustgraph.schema import TriplesQueryRequest, Value
        
        mock_tg_instance = MagicMock()
        mock_trustgraph.return_value = mock_tg_instance
        mock_tg_instance.get_spo.return_value = None
        
        processor = Processor(
            taskgroup=MagicMock(),
            cassandra_username='authuser',
            cassandra_password='authpass'
        )
        
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=Value(value='test_subject', is_uri=False),
            p=Value(value='test_predicate', is_uri=False),
            o=Value(value='test_object', is_uri=False),
            limit=100
        )
        
        await processor.query_triples(query)
        
        # Verify TrustGraph was created with authentication
        mock_trustgraph.assert_called_once_with(
            hosts=['cassandra'],  # Updated default
            keyspace='test_user',
            table='test_collection',
            username='authuser',
            password='authpass'
        )

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.TrustGraph')
    async def test_query_triples_table_reuse(self, mock_trustgraph):
        """Test that TrustGraph is reused for same table"""
        from trustgraph.schema import TriplesQueryRequest, Value
        
        mock_tg_instance = MagicMock()
        mock_trustgraph.return_value = mock_tg_instance
        mock_tg_instance.get_spo.return_value = None
        
        processor = Processor(taskgroup=MagicMock())
        
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=Value(value='test_subject', is_uri=False),
            p=Value(value='test_predicate', is_uri=False),
            o=Value(value='test_object', is_uri=False),
            limit=100
        )
        
        # First query should create TrustGraph
        await processor.query_triples(query)
        assert mock_trustgraph.call_count == 1
        
        # Second query with same table should reuse TrustGraph
        await processor.query_triples(query)
        assert mock_trustgraph.call_count == 1  # Should not increase

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.TrustGraph')
    async def test_query_triples_table_switching(self, mock_trustgraph):
        """Test table switching creates new TrustGraph"""
        from trustgraph.schema import TriplesQueryRequest, Value
        
        mock_tg_instance1 = MagicMock()
        mock_tg_instance2 = MagicMock()
        mock_trustgraph.side_effect = [mock_tg_instance1, mock_tg_instance2]
        
        processor = Processor(taskgroup=MagicMock())
        
        # First query
        query1 = TriplesQueryRequest(
            user='user1',
            collection='collection1',
            s=Value(value='test_subject', is_uri=False),
            p=None,
            o=None,
            limit=100
        )
        
        await processor.query_triples(query1)
        assert processor.table == ('user1', 'collection1')
        
        # Second query with different table
        query2 = TriplesQueryRequest(
            user='user2',
            collection='collection2',
            s=Value(value='test_subject', is_uri=False),
            p=None,
            o=None,
            limit=100
        )
        
        await processor.query_triples(query2)
        assert processor.table == ('user2', 'collection2')
        
        # Verify TrustGraph was created twice
        assert mock_trustgraph.call_count == 2

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.TrustGraph')
    async def test_query_triples_exception_handling(self, mock_trustgraph):
        """Test exception handling during query execution"""
        from trustgraph.schema import TriplesQueryRequest, Value
        
        mock_tg_instance = MagicMock()
        mock_trustgraph.return_value = mock_tg_instance
        mock_tg_instance.get_spo.side_effect = Exception("Query failed")
        
        processor = Processor(taskgroup=MagicMock())
        
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=Value(value='test_subject', is_uri=False),
            p=Value(value='test_predicate', is_uri=False),
            o=Value(value='test_object', is_uri=False),
            limit=100
        )
        
        with pytest.raises(Exception, match="Query failed"):
            await processor.query_triples(query)

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.TrustGraph')
    async def test_query_triples_multiple_results(self, mock_trustgraph):
        """Test query returning multiple results"""
        from trustgraph.schema import TriplesQueryRequest, Value
        
        mock_tg_instance = MagicMock()
        mock_trustgraph.return_value = mock_tg_instance
        
        # Mock multiple results
        mock_result1 = MagicMock()
        mock_result1.o = 'object1'
        mock_result2 = MagicMock()
        mock_result2.o = 'object2'
        mock_tg_instance.get_sp.return_value = [mock_result1, mock_result2]
        
        processor = Processor(taskgroup=MagicMock())
        
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=Value(value='test_subject', is_uri=False),
            p=Value(value='test_predicate', is_uri=False),
            o=None,
            limit=100
        )
        
        result = await processor.query_triples(query)
        
        assert len(result) == 2
        assert result[0].o.value == 'object1'
        assert result[1].o.value == 'object2'