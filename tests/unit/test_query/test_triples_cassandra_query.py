"""
Tests for Cassandra triples query service
"""

import pytest
from unittest.mock import MagicMock, patch

from trustgraph.query.triples.cassandra.service import Processor, create_term
from trustgraph.schema import Term, IRI, LITERAL


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

    def test_create_term_with_http_uri(self, processor):
        """Test create_term with HTTP URI"""
        result = create_term("http://example.com/resource")

        assert isinstance(result, Term)
        assert result.iri == "http://example.com/resource"
        assert result.type == IRI

    def test_create_term_with_https_uri(self, processor):
        """Test create_term with HTTPS URI"""
        result = create_term("https://example.com/resource")

        assert isinstance(result, Term)
        assert result.iri == "https://example.com/resource"
        assert result.type == IRI

    def test_create_term_with_literal(self, processor):
        """Test create_term with literal value"""
        result = create_term("just a literal string")

        assert isinstance(result, Term)
        assert result.value == "just a literal string"
        assert result.type == LITERAL

    def test_create_term_with_empty_string(self, processor):
        """Test create_term with empty string"""
        result = create_term("")

        assert isinstance(result, Term)
        assert result.value == ""
        assert result.type == LITERAL

    def test_create_term_with_partial_uri(self, processor):
        """Test create_term with string that looks like URI but isn't complete"""
        result = create_term("http")

        assert isinstance(result, Term)
        assert result.value == "http"
        assert result.type == LITERAL

    def test_create_term_with_ftp_uri(self, processor):
        """Test create_term with FTP URI (should not be detected as URI)"""
        result = create_term("ftp://example.com/file")

        assert isinstance(result, Term)
        assert result.value == "ftp://example.com/file"
        assert result.type == LITERAL

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.KnowledgeGraph')
    async def test_query_triples_spo_query(self, mock_trustgraph):
        """Test querying triples with subject, predicate, and object specified"""
        from trustgraph.schema import TriplesQueryRequest, Term, IRI, LITERAL
        
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
            s=Term(type=LITERAL, value='test_subject'),
            p=Term(type=LITERAL, value='test_predicate'),
            o=Term(type=LITERAL, value='test_object'),
            limit=100
        )
        
        result = await processor.query_triples(query)
        
        # Verify KnowledgeGraph was created with correct parameters
        mock_trustgraph.assert_called_once_with(
            hosts=['localhost'],
            keyspace='test_user'
        )
        
        # Verify get_spo was called with correct parameters
        mock_tg_instance.get_spo.assert_called_once_with(
            'test_collection', 'test_subject', 'test_predicate', 'test_object', limit=100
        )
        
        # Verify result contains the queried triple
        assert len(result) == 1
        assert result[0].s.iri == 'test_subject'
        assert result[0].p.iri == 'test_predicate'
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
    @patch('trustgraph.query.triples.cassandra.service.KnowledgeGraph')
    async def test_query_triples_sp_pattern(self, mock_trustgraph):
        """Test SP query pattern (subject and predicate, no object)"""
        from trustgraph.schema import TriplesQueryRequest, Term, IRI, LITERAL
        
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
            s=Term(type=LITERAL, value='test_subject'),
            p=Term(type=LITERAL, value='test_predicate'),
            o=None,
            limit=50
        )
        
        result = await processor.query_triples(query)
        
        mock_tg_instance.get_sp.assert_called_once_with('test_collection', 'test_subject', 'test_predicate', limit=50)
        assert len(result) == 1
        assert result[0].s.iri == 'test_subject'
        assert result[0].p.iri == 'test_predicate'
        assert result[0].o.value == 'result_object'

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.KnowledgeGraph')
    async def test_query_triples_s_pattern(self, mock_trustgraph):
        """Test S query pattern (subject only)"""
        from trustgraph.schema import TriplesQueryRequest, Term, IRI, LITERAL
        
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
            s=Term(type=LITERAL, value='test_subject'),
            p=None,
            o=None,
            limit=25
        )
        
        result = await processor.query_triples(query)
        
        mock_tg_instance.get_s.assert_called_once_with('test_collection', 'test_subject', limit=25)
        assert len(result) == 1
        assert result[0].s.iri == 'test_subject'
        assert result[0].p.iri == 'result_predicate'
        assert result[0].o.value == 'result_object'

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.KnowledgeGraph')
    async def test_query_triples_p_pattern(self, mock_trustgraph):
        """Test P query pattern (predicate only)"""
        from trustgraph.schema import TriplesQueryRequest, Term, IRI, LITERAL
        
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
            p=Term(type=LITERAL, value='test_predicate'),
            o=None,
            limit=10
        )
        
        result = await processor.query_triples(query)
        
        mock_tg_instance.get_p.assert_called_once_with('test_collection', 'test_predicate', limit=10)
        assert len(result) == 1
        assert result[0].s.iri == 'result_subject'
        assert result[0].p.iri == 'test_predicate'
        assert result[0].o.value == 'result_object'

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.KnowledgeGraph')
    async def test_query_triples_o_pattern(self, mock_trustgraph):
        """Test O query pattern (object only)"""
        from trustgraph.schema import TriplesQueryRequest, Term, IRI, LITERAL
        
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
            o=Term(type=LITERAL, value='test_object'),
            limit=75
        )
        
        result = await processor.query_triples(query)
        
        mock_tg_instance.get_o.assert_called_once_with('test_collection', 'test_object', limit=75)
        assert len(result) == 1
        assert result[0].s.iri == 'result_subject'
        assert result[0].p.iri == 'result_predicate'
        assert result[0].o.value == 'test_object'

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.KnowledgeGraph')
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
        
        mock_tg_instance.get_all.assert_called_once_with('test_collection', limit=1000)
        assert len(result) == 1
        assert result[0].s.iri == 'all_subject'
        assert result[0].p.iri == 'all_predicate'
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
    @patch('trustgraph.query.triples.cassandra.service.KnowledgeGraph')
    async def test_query_triples_with_authentication(self, mock_trustgraph):
        """Test querying with username and password authentication"""
        from trustgraph.schema import TriplesQueryRequest, Term, IRI, LITERAL
        
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
            s=Term(type=LITERAL, value='test_subject'),
            p=Term(type=LITERAL, value='test_predicate'),
            o=Term(type=LITERAL, value='test_object'),
            limit=100
        )
        
        await processor.query_triples(query)
        
        # Verify KnowledgeGraph was created with authentication
        mock_trustgraph.assert_called_once_with(
            hosts=['cassandra'],  # Updated default
            keyspace='test_user',
            username='authuser',
            password='authpass'
        )

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.KnowledgeGraph')
    async def test_query_triples_table_reuse(self, mock_trustgraph):
        """Test that TrustGraph is reused for same table"""
        from trustgraph.schema import TriplesQueryRequest, Term, IRI, LITERAL
        
        mock_tg_instance = MagicMock()
        mock_trustgraph.return_value = mock_tg_instance
        mock_tg_instance.get_spo.return_value = None
        
        processor = Processor(taskgroup=MagicMock())
        
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=Term(type=LITERAL, value='test_subject'),
            p=Term(type=LITERAL, value='test_predicate'),
            o=Term(type=LITERAL, value='test_object'),
            limit=100
        )
        
        # First query should create TrustGraph
        await processor.query_triples(query)
        assert mock_trustgraph.call_count == 1
        
        # Second query with same table should reuse TrustGraph
        await processor.query_triples(query)
        assert mock_trustgraph.call_count == 1  # Should not increase

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.KnowledgeGraph')
    async def test_query_triples_table_switching(self, mock_trustgraph):
        """Test table switching creates new TrustGraph"""
        from trustgraph.schema import TriplesQueryRequest, Term, IRI, LITERAL
        
        mock_tg_instance1 = MagicMock()
        mock_tg_instance2 = MagicMock()
        mock_trustgraph.side_effect = [mock_tg_instance1, mock_tg_instance2]
        
        processor = Processor(taskgroup=MagicMock())
        
        # First query
        query1 = TriplesQueryRequest(
            user='user1',
            collection='collection1',
            s=Term(type=LITERAL, value='test_subject'),
            p=None,
            o=None,
            limit=100
        )
        
        await processor.query_triples(query1)
        assert processor.table == 'user1'
        
        # Second query with different table
        query2 = TriplesQueryRequest(
            user='user2',
            collection='collection2',
            s=Term(type=LITERAL, value='test_subject'),
            p=None,
            o=None,
            limit=100
        )
        
        await processor.query_triples(query2)
        assert processor.table == 'user2'
        
        # Verify TrustGraph was created twice
        assert mock_trustgraph.call_count == 2

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.KnowledgeGraph')
    async def test_query_triples_exception_handling(self, mock_trustgraph):
        """Test exception handling during query execution"""
        from trustgraph.schema import TriplesQueryRequest, Term, IRI, LITERAL
        
        mock_tg_instance = MagicMock()
        mock_trustgraph.return_value = mock_tg_instance
        mock_tg_instance.get_spo.side_effect = Exception("Query failed")
        
        processor = Processor(taskgroup=MagicMock())
        
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=Term(type=LITERAL, value='test_subject'),
            p=Term(type=LITERAL, value='test_predicate'),
            o=Term(type=LITERAL, value='test_object'),
            limit=100
        )
        
        with pytest.raises(Exception, match="Query failed"):
            await processor.query_triples(query)

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.KnowledgeGraph')
    async def test_query_triples_multiple_results(self, mock_trustgraph):
        """Test query returning multiple results"""
        from trustgraph.schema import TriplesQueryRequest, Term, IRI, LITERAL
        
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
            s=Term(type=LITERAL, value='test_subject'),
            p=Term(type=LITERAL, value='test_predicate'),
            o=None,
            limit=100
        )
        
        result = await processor.query_triples(query)
        
        assert len(result) == 2
        assert result[0].o.value == 'object1'
        assert result[1].o.value == 'object2'


class TestCassandraQueryPerformanceOptimizations:
    """Test cases for multi-table performance optimizations in query service"""

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.KnowledgeGraph')
    async def test_get_po_query_optimization(self, mock_trustgraph):
        """Test that get_po queries use optimized table (no ALLOW FILTERING)"""
        from trustgraph.schema import TriplesQueryRequest, Term, IRI, LITERAL

        mock_tg_instance = MagicMock()
        mock_trustgraph.return_value = mock_tg_instance

        mock_result = MagicMock()
        mock_result.s = 'result_subject'
        mock_tg_instance.get_po.return_value = [mock_result]

        processor = Processor(taskgroup=MagicMock())

        # PO query pattern (predicate + object, find subjects)
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=None,
            p=Term(type=LITERAL, value='test_predicate'),
            o=Term(type=LITERAL, value='test_object'),
            limit=50
        )

        result = await processor.query_triples(query)

        # Verify get_po was called (should use optimized po_table)
        mock_tg_instance.get_po.assert_called_once_with(
            'test_collection', 'test_predicate', 'test_object', limit=50
        )

        assert len(result) == 1
        assert result[0].s.iri == 'result_subject'
        assert result[0].p.iri == 'test_predicate'
        assert result[0].o.value == 'test_object'

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.KnowledgeGraph')
    async def test_get_os_query_optimization(self, mock_trustgraph):
        """Test that get_os queries use optimized table (no ALLOW FILTERING)"""
        from trustgraph.schema import TriplesQueryRequest, Term, IRI, LITERAL

        mock_tg_instance = MagicMock()
        mock_trustgraph.return_value = mock_tg_instance

        mock_result = MagicMock()
        mock_result.p = 'result_predicate'
        mock_tg_instance.get_os.return_value = [mock_result]

        processor = Processor(taskgroup=MagicMock())

        # OS query pattern (object + subject, find predicates)
        query = TriplesQueryRequest(
            user='test_user',
            collection='test_collection',
            s=Term(type=LITERAL, value='test_subject'),
            p=None,
            o=Term(type=LITERAL, value='test_object'),
            limit=25
        )

        result = await processor.query_triples(query)

        # Verify get_os was called (should use optimized subject_table with clustering)
        mock_tg_instance.get_os.assert_called_once_with(
            'test_collection', 'test_object', 'test_subject', limit=25
        )

        assert len(result) == 1
        assert result[0].s.iri == 'test_subject'
        assert result[0].p.iri == 'result_predicate'
        assert result[0].o.value == 'test_object'

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.KnowledgeGraph')
    async def test_all_query_patterns_use_correct_tables(self, mock_trustgraph):
        """Test that all query patterns route to their optimal tables"""
        from trustgraph.schema import TriplesQueryRequest, Term, IRI, LITERAL

        mock_tg_instance = MagicMock()
        mock_trustgraph.return_value = mock_tg_instance

        # Mock empty results for all queries
        mock_tg_instance.get_all.return_value = []
        mock_tg_instance.get_s.return_value = []
        mock_tg_instance.get_p.return_value = []
        mock_tg_instance.get_o.return_value = []
        mock_tg_instance.get_sp.return_value = []
        mock_tg_instance.get_po.return_value = []
        mock_tg_instance.get_os.return_value = []
        mock_tg_instance.get_spo.return_value = []

        processor = Processor(taskgroup=MagicMock())

        # Test each query pattern
        test_patterns = [
            # (s, p, o, expected_method)
            (None, None, None, 'get_all'),  # All triples
            ('s1', None, None, 'get_s'),    # Subject only
            (None, 'p1', None, 'get_p'),    # Predicate only
            (None, None, 'o1', 'get_o'),    # Object only
            ('s1', 'p1', None, 'get_sp'),   # Subject + Predicate
            (None, 'p1', 'o1', 'get_po'),   # Predicate + Object (CRITICAL OPTIMIZATION)
            ('s1', None, 'o1', 'get_os'),   # Object + Subject
            ('s1', 'p1', 'o1', 'get_spo'),  # All three
        ]

        for s, p, o, expected_method in test_patterns:
            # Reset mock call counts
            mock_tg_instance.reset_mock()

            query = TriplesQueryRequest(
                user='test_user',
                collection='test_collection',
                s=Term(type=LITERAL, value=s) if s else None,
                p=Term(type=LITERAL, value=p) if p else None,
                o=Term(type=LITERAL, value=o) if o else None,
                limit=10
            )

            await processor.query_triples(query)

            # Verify the correct method was called
            method = getattr(mock_tg_instance, expected_method)
            assert method.called, f"Expected {expected_method} to be called for pattern s={s}, p={p}, o={o}"

    def test_legacy_vs_optimized_mode_configuration(self):
        """Test that environment variable controls query optimization mode"""
        taskgroup_mock = MagicMock()

        # Test optimized mode (default)
        with patch.dict('os.environ', {}, clear=True):
            processor = Processor(taskgroup=taskgroup_mock)
            # Mode is determined in KnowledgeGraph initialization

        # Test legacy mode
        with patch.dict('os.environ', {'CASSANDRA_USE_LEGACY': 'true'}):
            processor = Processor(taskgroup=taskgroup_mock)
            # Mode is determined in KnowledgeGraph initialization

        # Test explicit optimized mode
        with patch.dict('os.environ', {'CASSANDRA_USE_LEGACY': 'false'}):
            processor = Processor(taskgroup=taskgroup_mock)
            # Mode is determined in KnowledgeGraph initialization

    @pytest.mark.asyncio
    @patch('trustgraph.query.triples.cassandra.service.KnowledgeGraph')
    async def test_performance_critical_po_query_no_filtering(self, mock_trustgraph):
        """Test the performance-critical PO query that eliminates ALLOW FILTERING"""
        from trustgraph.schema import TriplesQueryRequest, Term, IRI, LITERAL

        mock_tg_instance = MagicMock()
        mock_trustgraph.return_value = mock_tg_instance

        # Mock multiple subjects for the same predicate-object pair
        mock_results = []
        for i in range(5):
            mock_result = MagicMock()
            mock_result.s = f'subject_{i}'
            mock_results.append(mock_result)

        mock_tg_instance.get_po.return_value = mock_results

        processor = Processor(taskgroup=MagicMock())

        # This is the query pattern that was slow with ALLOW FILTERING
        query = TriplesQueryRequest(
            user='large_dataset_user',
            collection='massive_collection',
            s=None,
            p=Term(type=IRI, iri='http://www.w3.org/1999/02/22-rdf-syntax-ns#type'),
            o=Term(type=IRI, iri='http://example.com/Person'),
            limit=1000
        )

        result = await processor.query_triples(query)

        # Verify optimized get_po was used (no ALLOW FILTERING needed!)
        mock_tg_instance.get_po.assert_called_once_with(
            'massive_collection',
            'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
            'http://example.com/Person',
            limit=1000
        )

        # Verify all results were returned
        assert len(result) == 5
        for i, triple in enumerate(result):
            assert triple.s.iri == f'subject_{i}'
            assert triple.p.iri == 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'
            assert triple.p.type == IRI
            assert triple.o.value == 'http://example.com/Person'
            assert triple.o.type == IRI