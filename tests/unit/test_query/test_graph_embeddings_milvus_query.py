"""
Tests for Milvus graph embeddings query service
"""

import pytest
from unittest.mock import MagicMock, patch

from trustgraph.query.graph_embeddings.milvus.service import Processor
from trustgraph.schema import Term, GraphEmbeddingsRequest, IRI, LITERAL


class TestMilvusGraphEmbeddingsQueryProcessor:
    """Test cases for Milvus graph embeddings query processor"""

    @pytest.fixture
    def processor(self):
        """Create a processor instance for testing"""
        with patch('trustgraph.query.graph_embeddings.milvus.service.EntityVectors') as mock_entity_vectors:
            mock_vecstore = MagicMock()
            mock_entity_vectors.return_value = mock_vecstore
            
            processor = Processor(
                taskgroup=MagicMock(),
                id='test-milvus-ge-query',
                store_uri='http://localhost:19530'
            )
            
            return processor

    @pytest.fixture
    def mock_query_request(self):
        """Create a mock query request for testing"""
        query = GraphEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            limit=10
        )
        return query

    @patch('trustgraph.query.graph_embeddings.milvus.service.EntityVectors')
    def test_processor_initialization_with_defaults(self, mock_entity_vectors):
        """Test processor initialization with default parameters"""
        taskgroup_mock = MagicMock()
        mock_vecstore = MagicMock()
        mock_entity_vectors.return_value = mock_vecstore
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        mock_entity_vectors.assert_called_once_with('http://localhost:19530')
        assert processor.vecstore == mock_vecstore

    @patch('trustgraph.query.graph_embeddings.milvus.service.EntityVectors')
    def test_processor_initialization_with_custom_params(self, mock_entity_vectors):
        """Test processor initialization with custom parameters"""
        taskgroup_mock = MagicMock()
        mock_vecstore = MagicMock()
        mock_entity_vectors.return_value = mock_vecstore
        
        processor = Processor(
            taskgroup=taskgroup_mock,
            store_uri='http://custom-milvus:19530'
        )
        
        mock_entity_vectors.assert_called_once_with('http://custom-milvus:19530')
        assert processor.vecstore == mock_vecstore

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

    @pytest.mark.asyncio
    async def test_query_graph_embeddings_single_vector(self, processor):
        """Test querying graph embeddings with a single vector"""
        query = GraphEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[[0.1, 0.2, 0.3]],
            limit=5
        )
        
        # Mock search results
        mock_results = [
            {"entity": {"entity": "http://example.com/entity1"}},
            {"entity": {"entity": "http://example.com/entity2"}},
            {"entity": {"entity": "literal entity"}},
        ]
        processor.vecstore.search.return_value = mock_results
        
        result = await processor.query_graph_embeddings(query)
        
        # Verify search was called with correct parameters including user/collection
        processor.vecstore.search.assert_called_once_with(
            [0.1, 0.2, 0.3], 'test_user', 'test_collection', limit=10
        )
        
        # Verify results are converted to Term objects
        assert len(result) == 3
        assert isinstance(result[0], Term)
        assert result[0].iri == "http://example.com/entity1"
        assert result[0].type == IRI
        assert isinstance(result[1], Term)
        assert result[1].iri == "http://example.com/entity2"
        assert result[1].type == IRI
        assert isinstance(result[2], Term)
        assert result[2].value == "literal entity"
        assert result[2].type == LITERAL

    @pytest.mark.asyncio
    async def test_query_graph_embeddings_multiple_vectors(self, processor):
        """Test querying graph embeddings with multiple vectors"""
        query = GraphEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            limit=3
        )
        
        # Mock search results - different results for each vector
        mock_results_1 = [
            {"entity": {"entity": "http://example.com/entity1"}},
            {"entity": {"entity": "http://example.com/entity2"}},
        ]
        mock_results_2 = [
            {"entity": {"entity": "http://example.com/entity2"}},  # Duplicate
            {"entity": {"entity": "http://example.com/entity3"}},
        ]
        processor.vecstore.search.side_effect = [mock_results_1, mock_results_2]
        
        result = await processor.query_graph_embeddings(query)
        
        # Verify search was called twice with correct parameters including user/collection
        expected_calls = [
            (([0.1, 0.2, 0.3], 'test_user', 'test_collection'), {"limit": 6}),
            (([0.4, 0.5, 0.6], 'test_user', 'test_collection'), {"limit": 6}),
        ]
        assert processor.vecstore.search.call_count == 2
        for i, (expected_args, expected_kwargs) in enumerate(expected_calls):
            actual_call = processor.vecstore.search.call_args_list[i]
            assert actual_call[0] == expected_args
            assert actual_call[1] == expected_kwargs
        
        # Verify results are deduplicated and limited
        assert len(result) == 3
        entity_values = [r.iri if r.type == IRI else r.value for r in result]
        assert "http://example.com/entity1" in entity_values
        assert "http://example.com/entity2" in entity_values
        assert "http://example.com/entity3" in entity_values

    @pytest.mark.asyncio
    async def test_query_graph_embeddings_with_limit(self, processor):
        """Test querying graph embeddings respects limit parameter"""
        query = GraphEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[[0.1, 0.2, 0.3]],
            limit=2
        )
        
        # Mock search results - more results than limit
        mock_results = [
            {"entity": {"entity": "http://example.com/entity1"}},
            {"entity": {"entity": "http://example.com/entity2"}},
            {"entity": {"entity": "http://example.com/entity3"}},
            {"entity": {"entity": "http://example.com/entity4"}},
        ]
        processor.vecstore.search.return_value = mock_results
        
        result = await processor.query_graph_embeddings(query)
        
        # Verify search was called with 2*limit for better deduplication
        processor.vecstore.search.assert_called_once_with(
            [0.1, 0.2, 0.3], 'test_user', 'test_collection', limit=4
        )
        
        # Verify results are limited to the requested limit
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_query_graph_embeddings_deduplication(self, processor):
        """Test that duplicate entities are properly deduplicated"""
        query = GraphEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            limit=5
        )
        
        # Mock search results with duplicates
        mock_results_1 = [
            {"entity": {"entity": "http://example.com/entity1"}},
            {"entity": {"entity": "http://example.com/entity2"}},
        ]
        mock_results_2 = [
            {"entity": {"entity": "http://example.com/entity2"}},  # Duplicate
            {"entity": {"entity": "http://example.com/entity1"}},  # Duplicate
            {"entity": {"entity": "http://example.com/entity3"}},  # New
        ]
        processor.vecstore.search.side_effect = [mock_results_1, mock_results_2]
        
        result = await processor.query_graph_embeddings(query)
        
        # Verify duplicates are removed
        assert len(result) == 3
        entity_values = [r.iri if r.type == IRI else r.value for r in result]
        assert len(set(entity_values)) == 3  # All unique
        assert "http://example.com/entity1" in entity_values
        assert "http://example.com/entity2" in entity_values
        assert "http://example.com/entity3" in entity_values

    @pytest.mark.asyncio
    async def test_query_graph_embeddings_early_termination_on_limit(self, processor):
        """Test that querying stops early when limit is reached"""
        query = GraphEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            limit=2
        )
        
        # Mock search results - first vector returns enough results
        mock_results_1 = [
            {"entity": {"entity": "http://example.com/entity1"}},
            {"entity": {"entity": "http://example.com/entity2"}},
            {"entity": {"entity": "http://example.com/entity3"}},
        ]
        processor.vecstore.search.return_value = mock_results_1
        
        result = await processor.query_graph_embeddings(query)
        
        # Verify only first vector was searched (limit reached)
        processor.vecstore.search.assert_called_once_with(
            [0.1, 0.2, 0.3], 'test_user', 'test_collection', limit=4
        )
        
        # Verify results are limited
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_query_graph_embeddings_empty_vectors(self, processor):
        """Test querying graph embeddings with empty vectors list"""
        query = GraphEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[],
            limit=5
        )
        
        result = await processor.query_graph_embeddings(query)
        
        # Verify no search was called
        processor.vecstore.search.assert_not_called()
        
        # Verify empty results
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_query_graph_embeddings_empty_search_results(self, processor):
        """Test querying graph embeddings with empty search results"""
        query = GraphEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[[0.1, 0.2, 0.3]],
            limit=5
        )
        
        # Mock empty search results
        processor.vecstore.search.return_value = []
        
        result = await processor.query_graph_embeddings(query)
        
        # Verify search was called
        processor.vecstore.search.assert_called_once_with(
            [0.1, 0.2, 0.3], 'test_user', 'test_collection', limit=10
        )
        
        # Verify empty results
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_query_graph_embeddings_mixed_uri_literal_results(self, processor):
        """Test querying graph embeddings with mixed URI and literal results"""
        query = GraphEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[[0.1, 0.2, 0.3]],
            limit=5
        )
        
        # Mock search results with mixed types
        mock_results = [
            {"entity": {"entity": "http://example.com/uri_entity"}},
            {"entity": {"entity": "literal entity text"}},
            {"entity": {"entity": "https://example.com/another_uri"}},
            {"entity": {"entity": "another literal"}},
        ]
        processor.vecstore.search.return_value = mock_results
        
        result = await processor.query_graph_embeddings(query)
        
        # Verify all results are properly typed
        assert len(result) == 4
        
        # Check URI entities
        uri_results = [r for r in result if r.type == IRI]
        assert len(uri_results) == 2
        uri_values = [r.iri for r in uri_results]
        assert "http://example.com/uri_entity" in uri_values
        assert "https://example.com/another_uri" in uri_values
        
        # Check literal entities
        literal_results = [r for r in result if not r.type == IRI]
        assert len(literal_results) == 2
        literal_values = [r.value for r in literal_results]
        assert "literal entity text" in literal_values
        assert "another literal" in literal_values

    @pytest.mark.asyncio
    async def test_query_graph_embeddings_exception_handling(self, processor):
        """Test exception handling during query processing"""
        query = GraphEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[[0.1, 0.2, 0.3]],
            limit=5
        )
        
        # Mock search to raise exception
        processor.vecstore.search.side_effect = Exception("Milvus connection failed")
        
        # Should raise the exception
        with pytest.raises(Exception, match="Milvus connection failed"):
            await processor.query_graph_embeddings(query)

    def test_add_args_method(self):
        """Test that add_args properly configures argument parser"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        # Mock the parent class add_args method
        with patch('trustgraph.query.graph_embeddings.milvus.service.GraphEmbeddingsQueryService.add_args') as mock_parent_add_args:
            Processor.add_args(parser)
            
            # Verify parent add_args was called
            mock_parent_add_args.assert_called_once()
        
        # Verify our specific arguments were added
        # Parse empty args to check defaults
        args = parser.parse_args([])
        
        assert hasattr(args, 'store_uri')
        assert args.store_uri == 'http://localhost:19530'

    def test_add_args_with_custom_values(self):
        """Test add_args with custom command line values"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        with patch('trustgraph.query.graph_embeddings.milvus.service.GraphEmbeddingsQueryService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with custom values
        args = parser.parse_args([
            '--store-uri', 'http://custom-milvus:19530'
        ])
        
        assert args.store_uri == 'http://custom-milvus:19530'

    def test_add_args_short_form(self):
        """Test add_args with short form arguments"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        with patch('trustgraph.query.graph_embeddings.milvus.service.GraphEmbeddingsQueryService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with short form
        args = parser.parse_args(['-t', 'http://short-milvus:19530'])
        
        assert args.store_uri == 'http://short-milvus:19530'

    @patch('trustgraph.query.graph_embeddings.milvus.service.Processor.launch')
    def test_run_function(self, mock_launch):
        """Test the run function calls Processor.launch with correct parameters"""
        from trustgraph.query.graph_embeddings.milvus.service import run, default_ident
        
        run()
        
        mock_launch.assert_called_once_with(
            default_ident,
            "\nGraph embeddings query service.  Input is vector, output is list of\nentities\n"
        )

    @pytest.mark.asyncio
    async def test_query_graph_embeddings_zero_limit(self, processor):
        """Test querying graph embeddings with zero limit"""
        query = GraphEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[[0.1, 0.2, 0.3]],
            limit=0
        )
        
        result = await processor.query_graph_embeddings(query)
        
        # Verify no search was called (optimization for zero limit)
        processor.vecstore.search.assert_not_called()
        
        # Verify empty results due to zero limit
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_query_graph_embeddings_different_vector_dimensions(self, processor):
        """Test querying graph embeddings with different vector dimensions"""
        query = GraphEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[
                [0.1, 0.2],  # 2D vector
                [0.3, 0.4, 0.5, 0.6],  # 4D vector
                [0.7, 0.8, 0.9]  # 3D vector
            ],
            limit=5
        )
        
        # Mock search results for each vector
        mock_results_1 = [{"entity": {"entity": "entity_2d"}}]
        mock_results_2 = [{"entity": {"entity": "entity_4d"}}]
        mock_results_3 = [{"entity": {"entity": "entity_3d"}}]
        processor.vecstore.search.side_effect = [mock_results_1, mock_results_2, mock_results_3]
        
        result = await processor.query_graph_embeddings(query)
        
        # Verify all vectors were searched
        assert processor.vecstore.search.call_count == 3
        
        # Verify results from all dimensions
        assert len(result) == 3
        entity_values = [r.iri if r.type == IRI else r.value for r in result]
        assert "entity_2d" in entity_values
        assert "entity_4d" in entity_values
        assert "entity_3d" in entity_values