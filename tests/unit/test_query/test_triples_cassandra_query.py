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
            graph_host='localhost'
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