"""
Tests for Pinecone document embeddings query service
"""

import pytest
from unittest.mock import MagicMock, patch

# Skip all tests in this module due to missing Pinecone dependency
pytest.skip("Pinecone library missing protoc_gen_openapiv2 dependency", allow_module_level=True)

from trustgraph.query.doc_embeddings.pinecone.service import Processor


class TestPineconeDocEmbeddingsQueryProcessor:
    """Test cases for Pinecone document embeddings query processor"""

    @pytest.fixture
    def mock_query_message(self):
        """Create a mock query message for testing"""
        message = MagicMock()
        message.vectors = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6]
        ]
        message.limit = 5
        message.user = 'test_user'
        message.collection = 'test_collection'
        return message

    @pytest.fixture
    def processor(self):
        """Create a processor instance for testing"""
        with patch('trustgraph.query.doc_embeddings.pinecone.service.Pinecone') as mock_pinecone_class:
            mock_pinecone = MagicMock()
            mock_pinecone_class.return_value = mock_pinecone
            
            processor = Processor(
                taskgroup=MagicMock(),
                id='test-pinecone-de-query',
                api_key='test-api-key'
            )
            
            return processor

    @patch('trustgraph.query.doc_embeddings.pinecone.service.Pinecone')
    @patch('trustgraph.query.doc_embeddings.pinecone.service.default_api_key', 'env-api-key')
    def test_processor_initialization_with_defaults(self, mock_pinecone_class):
        """Test processor initialization with default parameters"""
        mock_pinecone = MagicMock()
        mock_pinecone_class.return_value = mock_pinecone
        taskgroup_mock = MagicMock()
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        mock_pinecone_class.assert_called_once_with(api_key='env-api-key')
        assert processor.pinecone == mock_pinecone
        assert processor.api_key == 'env-api-key'

    @patch('trustgraph.query.doc_embeddings.pinecone.service.Pinecone')
    def test_processor_initialization_with_custom_params(self, mock_pinecone_class):
        """Test processor initialization with custom parameters"""
        mock_pinecone = MagicMock()
        mock_pinecone_class.return_value = mock_pinecone
        taskgroup_mock = MagicMock()
        
        processor = Processor(
            taskgroup=taskgroup_mock,
            api_key='custom-api-key'
        )
        
        mock_pinecone_class.assert_called_once_with(api_key='custom-api-key')
        assert processor.api_key == 'custom-api-key'

    @patch('trustgraph.query.doc_embeddings.pinecone.service.PineconeGRPC')
    def test_processor_initialization_with_url(self, mock_pinecone_grpc_class):
        """Test processor initialization with custom URL (GRPC mode)"""
        mock_pinecone = MagicMock()
        mock_pinecone_grpc_class.return_value = mock_pinecone
        taskgroup_mock = MagicMock()
        
        processor = Processor(
            taskgroup=taskgroup_mock,
            api_key='test-api-key',
            url='https://custom-host.pinecone.io'
        )
        
        mock_pinecone_grpc_class.assert_called_once_with(
            api_key='test-api-key',
            host='https://custom-host.pinecone.io'
        )
        assert processor.pinecone == mock_pinecone
        assert processor.url == 'https://custom-host.pinecone.io'

    @patch('trustgraph.query.doc_embeddings.pinecone.service.default_api_key', 'not-specified')
    def test_processor_initialization_missing_api_key(self):
        """Test processor initialization fails with missing API key"""
        taskgroup_mock = MagicMock()
        
        with pytest.raises(RuntimeError, match="Pinecone API key must be specified"):
            Processor(taskgroup=taskgroup_mock)

    @pytest.mark.asyncio
    async def test_query_document_embeddings_single_vector(self, processor):
        """Test querying document embeddings with a single vector"""
        message = MagicMock()
        message.vectors = [[0.1, 0.2, 0.3]]
        message.limit = 3
        message.user = 'test_user'
        message.collection = 'test_collection'
        
        # Mock index and query results
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        mock_results = MagicMock()
        mock_results.matches = [
            MagicMock(metadata={'doc': 'First document chunk'}),
            MagicMock(metadata={'doc': 'Second document chunk'}),
            MagicMock(metadata={'doc': 'Third document chunk'})
        ]
        mock_index.query.return_value = mock_results
        
        chunks = await processor.query_document_embeddings(message)
        
        # Verify index was accessed correctly (with dimension suffix)
        expected_index_name = "d-test_user-test_collection-3"  # 3 dimensions
        processor.pinecone.Index.assert_called_once_with(expected_index_name)
        
        # Verify query parameters
        mock_index.query.assert_called_once_with(
            vector=[0.1, 0.2, 0.3],
            top_k=3,
            include_values=False,
            include_metadata=True
        )
        
        # Verify results
        assert len(chunks) == 3
        assert chunks[0] == 'First document chunk'
        assert chunks[1] == 'Second document chunk'
        assert chunks[2] == 'Third document chunk'

    @pytest.mark.asyncio
    async def test_query_document_embeddings_multiple_vectors(self, processor, mock_query_message):
        """Test querying document embeddings with multiple vectors"""
        # Mock index and query results
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        # First query results
        mock_results1 = MagicMock()
        mock_results1.matches = [
            MagicMock(metadata={'doc': 'Document chunk 1'}),
            MagicMock(metadata={'doc': 'Document chunk 2'})
        ]
        
        # Second query results
        mock_results2 = MagicMock()
        mock_results2.matches = [
            MagicMock(metadata={'doc': 'Document chunk 3'}),
            MagicMock(metadata={'doc': 'Document chunk 4'})
        ]
        
        mock_index.query.side_effect = [mock_results1, mock_results2]
        
        chunks = await processor.query_document_embeddings(mock_query_message)
        
        # Verify both queries were made
        assert mock_index.query.call_count == 2
        
        # Verify results from both queries
        assert len(chunks) == 4
        assert 'Document chunk 1' in chunks
        assert 'Document chunk 2' in chunks
        assert 'Document chunk 3' in chunks
        assert 'Document chunk 4' in chunks

    @pytest.mark.asyncio
    async def test_query_document_embeddings_limit_handling(self, processor):
        """Test that query respects the limit parameter"""
        message = MagicMock()
        message.vectors = [[0.1, 0.2, 0.3]]
        message.limit = 2
        message.user = 'test_user'
        message.collection = 'test_collection'
        
        # Mock index with many results
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        mock_results = MagicMock()
        mock_results.matches = [
            MagicMock(metadata={'doc': f'Document chunk {i}'}) for i in range(10)
        ]
        mock_index.query.return_value = mock_results
        
        chunks = await processor.query_document_embeddings(message)
        
        # Verify limit is passed to query
        mock_index.query.assert_called_once()
        call_args = mock_index.query.call_args
        assert call_args[1]['top_k'] == 2
        
        # Results should contain all returned chunks (limit is applied by Pinecone)
        assert len(chunks) == 10

    @pytest.mark.asyncio
    async def test_query_document_embeddings_zero_limit(self, processor):
        """Test querying with zero limit returns empty results"""
        message = MagicMock()
        message.vectors = [[0.1, 0.2, 0.3]]
        message.limit = 0
        message.user = 'test_user'
        message.collection = 'test_collection'
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        chunks = await processor.query_document_embeddings(message)
        
        # Verify no query was made and empty result returned
        mock_index.query.assert_not_called()
        assert chunks == []

    @pytest.mark.asyncio
    async def test_query_document_embeddings_negative_limit(self, processor):
        """Test querying with negative limit returns empty results"""
        message = MagicMock()
        message.vectors = [[0.1, 0.2, 0.3]]
        message.limit = -1
        message.user = 'test_user'
        message.collection = 'test_collection'
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        chunks = await processor.query_document_embeddings(message)
        
        # Verify no query was made and empty result returned
        mock_index.query.assert_not_called()
        assert chunks == []

    @pytest.mark.asyncio
    async def test_query_document_embeddings_different_vector_dimensions(self, processor):
        """Test querying with vectors of different dimensions using same index"""
        message = MagicMock()
        message.vectors = [
            [0.1, 0.2],  # 2D vector
            [0.3, 0.4, 0.5, 0.6]  # 4D vector
        ]
        message.limit = 5
        message.user = 'test_user'
        message.collection = 'test_collection'

        # Mock single index that handles all dimensions
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index

        # Mock results for different vector queries
        mock_results_2d = MagicMock()
        mock_results_2d.matches = [MagicMock(metadata={'doc': 'Document from 2D query'})]

        mock_results_4d = MagicMock()
        mock_results_4d.matches = [MagicMock(metadata={'doc': 'Document from 4D query'})]

        mock_index.query.side_effect = [mock_results_2d, mock_results_4d]

        chunks = await processor.query_document_embeddings(message)

        # Verify different indexes used for different dimensions
        assert processor.pinecone.Index.call_count == 2
        index_calls = processor.pinecone.Index.call_args_list
        index_names = [call[0][0] for call in index_calls]
        assert "d-test_user-test_collection-2" in index_names  # 2D vector
        assert "d-test_user-test_collection-4" in index_names  # 4D vector

        # Verify both queries were made
        assert mock_index.query.call_count == 2

        # Verify results from both dimensions
        assert 'Document from 2D query' in chunks
        assert 'Document from 4D query' in chunks

    @pytest.mark.asyncio
    async def test_query_document_embeddings_empty_vectors_list(self, processor):
        """Test querying with empty vectors list"""
        message = MagicMock()
        message.vectors = []
        message.limit = 5
        message.user = 'test_user'
        message.collection = 'test_collection'
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        chunks = await processor.query_document_embeddings(message)
        
        # Verify no queries were made and empty result returned
        processor.pinecone.Index.assert_not_called()
        mock_index.query.assert_not_called()
        assert chunks == []

    @pytest.mark.asyncio
    async def test_query_document_embeddings_no_results(self, processor):
        """Test querying when index returns no results"""
        message = MagicMock()
        message.vectors = [[0.1, 0.2, 0.3]]
        message.limit = 5
        message.user = 'test_user'
        message.collection = 'test_collection'
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        mock_results = MagicMock()
        mock_results.matches = []
        mock_index.query.return_value = mock_results
        
        chunks = await processor.query_document_embeddings(message)
        
        # Verify empty results
        assert chunks == []

    @pytest.mark.asyncio
    async def test_query_document_embeddings_unicode_content(self, processor):
        """Test querying document embeddings with Unicode content results"""
        message = MagicMock()
        message.vectors = [[0.1, 0.2, 0.3]]
        message.limit = 2
        message.user = 'test_user'
        message.collection = 'test_collection'
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        mock_results = MagicMock()
        mock_results.matches = [
            MagicMock(metadata={'doc': 'Document with Unicode: éñ中文🚀'}),
            MagicMock(metadata={'doc': 'Regular ASCII document'})
        ]
        mock_index.query.return_value = mock_results
        
        chunks = await processor.query_document_embeddings(message)
        
        # Verify Unicode content is properly handled
        assert len(chunks) == 2
        assert 'Document with Unicode: éñ中文🚀' in chunks
        assert 'Regular ASCII document' in chunks

    @pytest.mark.asyncio
    async def test_query_document_embeddings_large_content(self, processor):
        """Test querying document embeddings with large content results"""
        message = MagicMock()
        message.vectors = [[0.1, 0.2, 0.3]]
        message.limit = 1
        message.user = 'test_user'
        message.collection = 'test_collection'
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        # Create a large document content
        large_content = "A" * 10000  # 10KB of content
        mock_results = MagicMock()
        mock_results.matches = [
            MagicMock(metadata={'doc': large_content})
        ]
        mock_index.query.return_value = mock_results
        
        chunks = await processor.query_document_embeddings(message)
        
        # Verify large content is properly handled
        assert len(chunks) == 1
        assert chunks[0] == large_content

    @pytest.mark.asyncio
    async def test_query_document_embeddings_mixed_content_types(self, processor):
        """Test querying document embeddings with mixed content types"""
        message = MagicMock()
        message.vectors = [[0.1, 0.2, 0.3]]
        message.limit = 5
        message.user = 'test_user'
        message.collection = 'test_collection'
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        mock_results = MagicMock()
        mock_results.matches = [
            MagicMock(metadata={'doc': 'Short text'}),
            MagicMock(metadata={'doc': 'A' * 1000}),  # Long text
            MagicMock(metadata={'doc': 'Text with numbers: 123 and symbols: @#$'}),
            MagicMock(metadata={'doc': '   Whitespace text   '}),
            MagicMock(metadata={'doc': ''})  # Empty string
        ]
        mock_index.query.return_value = mock_results
        
        chunks = await processor.query_document_embeddings(message)
        
        # Verify all content types are properly handled
        assert len(chunks) == 5
        assert 'Short text' in chunks
        assert 'A' * 1000 in chunks
        assert 'Text with numbers: 123 and symbols: @#$' in chunks
        assert '   Whitespace text   ' in chunks
        assert '' in chunks

    @pytest.mark.asyncio
    async def test_query_document_embeddings_exception_handling(self, processor):
        """Test that exceptions are properly raised"""
        message = MagicMock()
        message.vectors = [[0.1, 0.2, 0.3]]
        message.limit = 5
        message.user = 'test_user'
        message.collection = 'test_collection'
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        mock_index.query.side_effect = Exception("Query failed")
        
        with pytest.raises(Exception, match="Query failed"):
            await processor.query_document_embeddings(message)

    @pytest.mark.asyncio
    async def test_query_document_embeddings_index_access_failure(self, processor):
        """Test handling of index access failure"""
        message = MagicMock()
        message.vectors = [[0.1, 0.2, 0.3]]
        message.limit = 5
        message.user = 'test_user'
        message.collection = 'test_collection'
        
        processor.pinecone.Index.side_effect = Exception("Index access failed")
        
        with pytest.raises(Exception, match="Index access failed"):
            await processor.query_document_embeddings(message)

    @pytest.mark.asyncio
    async def test_query_document_embeddings_vector_accumulation(self, processor):
        """Test that results from multiple vectors are properly accumulated"""
        message = MagicMock()
        message.vectors = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9]
        ]
        message.limit = 2
        message.user = 'test_user'
        message.collection = 'test_collection'
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        # Each query returns different results
        mock_results1 = MagicMock()
        mock_results1.matches = [
            MagicMock(metadata={'doc': 'Doc from vector 1.1'}),
            MagicMock(metadata={'doc': 'Doc from vector 1.2'})
        ]
        
        mock_results2 = MagicMock()
        mock_results2.matches = [
            MagicMock(metadata={'doc': 'Doc from vector 2.1'})
        ]
        
        mock_results3 = MagicMock()
        mock_results3.matches = [
            MagicMock(metadata={'doc': 'Doc from vector 3.1'}),
            MagicMock(metadata={'doc': 'Doc from vector 3.2'}),
            MagicMock(metadata={'doc': 'Doc from vector 3.3'})
        ]
        
        mock_index.query.side_effect = [mock_results1, mock_results2, mock_results3]
        
        chunks = await processor.query_document_embeddings(message)
        
        # Verify all queries were made
        assert mock_index.query.call_count == 3
        
        # Verify all results are accumulated
        assert len(chunks) == 6
        assert 'Doc from vector 1.1' in chunks
        assert 'Doc from vector 1.2' in chunks
        assert 'Doc from vector 2.1' in chunks
        assert 'Doc from vector 3.1' in chunks
        assert 'Doc from vector 3.2' in chunks
        assert 'Doc from vector 3.3' in chunks

    def test_add_args_method(self):
        """Test that add_args properly configures argument parser"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        # Mock the parent class add_args method
        with patch('trustgraph.query.doc_embeddings.pinecone.service.DocumentEmbeddingsQueryService.add_args') as mock_parent_add_args:
            Processor.add_args(parser)
            
            # Verify parent add_args was called
            mock_parent_add_args.assert_called_once()
        
        # Verify our specific arguments were added
        args = parser.parse_args([])
        
        assert hasattr(args, 'api_key')
        assert args.api_key == 'not-specified'  # Default value when no env var
        assert hasattr(args, 'url')
        assert args.url is None

    def test_add_args_with_custom_values(self):
        """Test add_args with custom command line values"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        with patch('trustgraph.query.doc_embeddings.pinecone.service.DocumentEmbeddingsQueryService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with custom values
        args = parser.parse_args([
            '--api-key', 'custom-api-key',
            '--url', 'https://custom-host.pinecone.io'
        ])
        
        assert args.api_key == 'custom-api-key'
        assert args.url == 'https://custom-host.pinecone.io'

    def test_add_args_short_form(self):
        """Test add_args with short form arguments"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        with patch('trustgraph.query.doc_embeddings.pinecone.service.DocumentEmbeddingsQueryService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with short form
        args = parser.parse_args([
            '-a', 'short-api-key',
            '-u', 'https://short-host.pinecone.io'
        ])
        
        assert args.api_key == 'short-api-key'
        assert args.url == 'https://short-host.pinecone.io'

    @patch('trustgraph.query.doc_embeddings.pinecone.service.Processor.launch')
    def test_run_function(self, mock_launch):
        """Test the run function calls Processor.launch with correct parameters"""
        from trustgraph.query.doc_embeddings.pinecone.service import run, default_ident
        
        run()
        
        mock_launch.assert_called_once_with(
            default_ident,
            "\nDocument embeddings query service.  Input is vector, output is an array\nof chunks.  Pinecone implementation.\n"
        )