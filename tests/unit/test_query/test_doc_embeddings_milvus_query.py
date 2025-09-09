"""
Tests for Milvus document embeddings query service
"""

import pytest
from unittest.mock import MagicMock, patch

from trustgraph.query.doc_embeddings.milvus.service import Processor
from trustgraph.schema import DocumentEmbeddingsRequest


class TestMilvusDocEmbeddingsQueryProcessor:
    """Test cases for Milvus document embeddings query processor"""

    @pytest.fixture
    def processor(self):
        """Create a processor instance for testing"""
        with patch('trustgraph.query.doc_embeddings.milvus.service.DocVectors') as mock_doc_vectors:
            mock_vecstore = MagicMock()
            mock_doc_vectors.return_value = mock_vecstore
            
            processor = Processor(
                taskgroup=MagicMock(),
                id='test-milvus-de-query',
                store_uri='http://localhost:19530'
            )
            
            return processor

    @pytest.fixture
    def mock_query_request(self):
        """Create a mock query request for testing"""
        query = DocumentEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            limit=10
        )
        return query

    @patch('trustgraph.query.doc_embeddings.milvus.service.DocVectors')
    def test_processor_initialization_with_defaults(self, mock_doc_vectors):
        """Test processor initialization with default parameters"""
        taskgroup_mock = MagicMock()
        mock_vecstore = MagicMock()
        mock_doc_vectors.return_value = mock_vecstore
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        mock_doc_vectors.assert_called_once_with('http://localhost:19530')
        assert processor.vecstore == mock_vecstore

    @patch('trustgraph.query.doc_embeddings.milvus.service.DocVectors')
    def test_processor_initialization_with_custom_params(self, mock_doc_vectors):
        """Test processor initialization with custom parameters"""
        taskgroup_mock = MagicMock()
        mock_vecstore = MagicMock()
        mock_doc_vectors.return_value = mock_vecstore
        
        processor = Processor(
            taskgroup=taskgroup_mock,
            store_uri='http://custom-milvus:19530'
        )
        
        mock_doc_vectors.assert_called_once_with('http://custom-milvus:19530')
        assert processor.vecstore == mock_vecstore

    @pytest.mark.asyncio
    async def test_query_document_embeddings_single_vector(self, processor):
        """Test querying document embeddings with a single vector"""
        query = DocumentEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[[0.1, 0.2, 0.3]],
            limit=5
        )
        
        # Mock search results
        mock_results = [
            {"entity": {"doc": "First document chunk"}},
            {"entity": {"doc": "Second document chunk"}},
            {"entity": {"doc": "Third document chunk"}},
        ]
        processor.vecstore.search.return_value = mock_results
        
        result = await processor.query_document_embeddings(query)
        
        # Verify search was called with correct parameters including user/collection
        processor.vecstore.search.assert_called_once_with(
            [0.1, 0.2, 0.3], 'test_user', 'test_collection', limit=5
        )
        
        # Verify results are document chunks
        assert len(result) == 3
        assert result[0] == "First document chunk"
        assert result[1] == "Second document chunk"
        assert result[2] == "Third document chunk"

    @pytest.mark.asyncio
    async def test_query_document_embeddings_multiple_vectors(self, processor):
        """Test querying document embeddings with multiple vectors"""
        query = DocumentEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            limit=3
        )
        
        # Mock search results - different results for each vector
        mock_results_1 = [
            {"entity": {"doc": "Document from first vector"}},
            {"entity": {"doc": "Another doc from first vector"}},
        ]
        mock_results_2 = [
            {"entity": {"doc": "Document from second vector"}},
        ]
        processor.vecstore.search.side_effect = [mock_results_1, mock_results_2]
        
        result = await processor.query_document_embeddings(query)
        
        # Verify search was called twice with correct parameters
        expected_calls = [
            (([0.1, 0.2, 0.3],), {"limit": 3}),
            (([0.4, 0.5, 0.6],), {"limit": 3}),
        ]
        assert processor.vecstore.search.call_count == 2
        for i, (expected_args, expected_kwargs) in enumerate(expected_calls):
            actual_call = processor.vecstore.search.call_args_list[i]
            assert actual_call[0] == expected_args
            assert actual_call[1] == expected_kwargs
        
        # Verify results from all vectors are combined
        assert len(result) == 3
        assert "Document from first vector" in result
        assert "Another doc from first vector" in result
        assert "Document from second vector" in result

    @pytest.mark.asyncio
    async def test_query_document_embeddings_with_limit(self, processor):
        """Test querying document embeddings respects limit parameter"""
        query = DocumentEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[[0.1, 0.2, 0.3]],
            limit=2
        )
        
        # Mock search results - more results than limit
        mock_results = [
            {"entity": {"doc": "Document 1"}},
            {"entity": {"doc": "Document 2"}},
            {"entity": {"doc": "Document 3"}},
            {"entity": {"doc": "Document 4"}},
        ]
        processor.vecstore.search.return_value = mock_results
        
        result = await processor.query_document_embeddings(query)
        
        # Verify search was called with the specified limit
        processor.vecstore.search.assert_called_once_with([0.1, 0.2, 0.3], limit=2)
        
        # Verify all results are returned (Milvus handles limit internally)
        assert len(result) == 4

    @pytest.mark.asyncio
    async def test_query_document_embeddings_empty_vectors(self, processor):
        """Test querying document embeddings with empty vectors list"""
        query = DocumentEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[],
            limit=5
        )
        
        result = await processor.query_document_embeddings(query)
        
        # Verify no search was called
        processor.vecstore.search.assert_not_called()
        
        # Verify empty results
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_query_document_embeddings_empty_search_results(self, processor):
        """Test querying document embeddings with empty search results"""
        query = DocumentEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[[0.1, 0.2, 0.3]],
            limit=5
        )
        
        # Mock empty search results
        processor.vecstore.search.return_value = []
        
        result = await processor.query_document_embeddings(query)
        
        # Verify search was called
        processor.vecstore.search.assert_called_once_with([0.1, 0.2, 0.3], limit=5)
        
        # Verify empty results
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_query_document_embeddings_unicode_documents(self, processor):
        """Test querying document embeddings with Unicode document content"""
        query = DocumentEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[[0.1, 0.2, 0.3]],
            limit=5
        )
        
        # Mock search results with Unicode content
        mock_results = [
            {"entity": {"doc": "Document with Unicode: éñ中文🚀"}},
            {"entity": {"doc": "Regular ASCII document"}},
            {"entity": {"doc": "Document with émojis: 😀🎉"}},
        ]
        processor.vecstore.search.return_value = mock_results
        
        result = await processor.query_document_embeddings(query)
        
        # Verify Unicode content is preserved
        assert len(result) == 3
        assert "Document with Unicode: éñ中文🚀" in result
        assert "Regular ASCII document" in result
        assert "Document with émojis: 😀🎉" in result

    @pytest.mark.asyncio
    async def test_query_document_embeddings_large_documents(self, processor):
        """Test querying document embeddings with large document content"""
        query = DocumentEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[[0.1, 0.2, 0.3]],
            limit=5
        )
        
        # Mock search results with large content
        large_doc = "A" * 10000  # 10KB of content
        mock_results = [
            {"entity": {"doc": large_doc}},
            {"entity": {"doc": "Small document"}},
        ]
        processor.vecstore.search.return_value = mock_results
        
        result = await processor.query_document_embeddings(query)
        
        # Verify large content is preserved
        assert len(result) == 2
        assert large_doc in result
        assert "Small document" in result

    @pytest.mark.asyncio
    async def test_query_document_embeddings_special_characters(self, processor):
        """Test querying document embeddings with special characters in documents"""
        query = DocumentEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[[0.1, 0.2, 0.3]],
            limit=5
        )
        
        # Mock search results with special characters
        mock_results = [
            {"entity": {"doc": "Document with \"quotes\" and 'apostrophes'"}},
            {"entity": {"doc": "Document with\nnewlines\tand\ttabs"}},
            {"entity": {"doc": "Document with special chars: @#$%^&*()"}},
        ]
        processor.vecstore.search.return_value = mock_results
        
        result = await processor.query_document_embeddings(query)
        
        # Verify special characters are preserved
        assert len(result) == 3
        assert "Document with \"quotes\" and 'apostrophes'" in result
        assert "Document with\nnewlines\tand\ttabs" in result
        assert "Document with special chars: @#$%^&*()" in result

    @pytest.mark.asyncio
    async def test_query_document_embeddings_zero_limit(self, processor):
        """Test querying document embeddings with zero limit"""
        query = DocumentEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[[0.1, 0.2, 0.3]],
            limit=0
        )
        
        result = await processor.query_document_embeddings(query)
        
        # Verify no search was called (optimization for zero limit)
        processor.vecstore.search.assert_not_called()
        
        # Verify empty results due to zero limit
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_query_document_embeddings_negative_limit(self, processor):
        """Test querying document embeddings with negative limit"""
        query = DocumentEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[[0.1, 0.2, 0.3]],
            limit=-1
        )
        
        result = await processor.query_document_embeddings(query)
        
        # Verify no search was called (optimization for negative limit)
        processor.vecstore.search.assert_not_called()
        
        # Verify empty results due to negative limit
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_query_document_embeddings_exception_handling(self, processor):
        """Test exception handling during query processing"""
        query = DocumentEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[[0.1, 0.2, 0.3]],
            limit=5
        )
        
        # Mock search to raise exception
        processor.vecstore.search.side_effect = Exception("Milvus connection failed")
        
        # Should raise the exception
        with pytest.raises(Exception, match="Milvus connection failed"):
            await processor.query_document_embeddings(query)

    @pytest.mark.asyncio
    async def test_query_document_embeddings_different_vector_dimensions(self, processor):
        """Test querying document embeddings with different vector dimensions"""
        query = DocumentEmbeddingsRequest(
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
        mock_results_1 = [{"entity": {"doc": "Document from 2D vector"}}]
        mock_results_2 = [{"entity": {"doc": "Document from 4D vector"}}]
        mock_results_3 = [{"entity": {"doc": "Document from 3D vector"}}]
        processor.vecstore.search.side_effect = [mock_results_1, mock_results_2, mock_results_3]
        
        result = await processor.query_document_embeddings(query)
        
        # Verify all vectors were searched
        assert processor.vecstore.search.call_count == 3
        
        # Verify results from all dimensions
        assert len(result) == 3
        assert "Document from 2D vector" in result
        assert "Document from 4D vector" in result
        assert "Document from 3D vector" in result

    @pytest.mark.asyncio
    async def test_query_document_embeddings_duplicate_documents(self, processor):
        """Test querying document embeddings with duplicate documents in results"""
        query = DocumentEmbeddingsRequest(
            user='test_user',
            collection='test_collection',
            vectors=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            limit=5
        )
        
        # Mock search results with duplicates across vectors
        mock_results_1 = [
            {"entity": {"doc": "Document A"}},
            {"entity": {"doc": "Document B"}},
        ]
        mock_results_2 = [
            {"entity": {"doc": "Document B"}},  # Duplicate
            {"entity": {"doc": "Document C"}},
        ]
        processor.vecstore.search.side_effect = [mock_results_1, mock_results_2]
        
        result = await processor.query_document_embeddings(query)
        
        # Note: Unlike graph embeddings, doc embeddings don't deduplicate
        # This preserves ranking and allows multiple occurrences
        assert len(result) == 4
        assert result.count("Document B") == 2  # Should appear twice
        assert "Document A" in result
        assert "Document C" in result

    def test_add_args_method(self):
        """Test that add_args properly configures argument parser"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        # Mock the parent class add_args method
        with patch('trustgraph.query.doc_embeddings.milvus.service.DocumentEmbeddingsQueryService.add_args') as mock_parent_add_args:
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
        
        with patch('trustgraph.query.doc_embeddings.milvus.service.DocumentEmbeddingsQueryService.add_args'):
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
        
        with patch('trustgraph.query.doc_embeddings.milvus.service.DocumentEmbeddingsQueryService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with short form
        args = parser.parse_args(['-t', 'http://short-milvus:19530'])
        
        assert args.store_uri == 'http://short-milvus:19530'

    @patch('trustgraph.query.doc_embeddings.milvus.service.Processor.launch')
    def test_run_function(self, mock_launch):
        """Test the run function calls Processor.launch with correct parameters"""
        from trustgraph.query.doc_embeddings.milvus.service import run, default_ident
        
        run()
        
        mock_launch.assert_called_once_with(
            default_ident,
            "\nDocument embeddings query service.  Input is vector, output is an array\nof chunks\n"
        )