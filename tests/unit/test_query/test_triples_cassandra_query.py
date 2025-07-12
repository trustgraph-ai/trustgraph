"""
Tests for Cassandra triples query service
"""

import pytest
from unittest.mock import MagicMock

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