"""
Tests for Milvus document embeddings storage service
"""

import pytest
from unittest.mock import MagicMock, patch

from trustgraph.storage.doc_embeddings.milvus.write import Processor
from trustgraph.schema import ChunkEmbeddings


class TestMilvusDocEmbeddingsStorageProcessor:
    """Test cases for Milvus document embeddings storage processor"""

    @pytest.fixture
    def mock_message(self):
        """Create a mock message for testing"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        # Create test document embeddings
        chunk1 = ChunkEmbeddings(
            chunk=b"This is the first document chunk",
            vectors=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        )
        chunk2 = ChunkEmbeddings(
            chunk=b"This is the second document chunk",
            vectors=[[0.7, 0.8, 0.9]]
        )
        message.chunks = [chunk1, chunk2]
        
        return message

    @pytest.fixture
    def processor(self):
        """Create a processor instance for testing"""
        with patch('trustgraph.storage.doc_embeddings.milvus.write.DocVectors') as mock_doc_vectors:
            mock_vecstore = MagicMock()
            mock_doc_vectors.return_value = mock_vecstore
            
            processor = Processor(
                taskgroup=MagicMock(),
                id='test-milvus-de-storage',
                store_uri='http://localhost:19530'
            )
            
            return processor

    @patch('trustgraph.storage.doc_embeddings.milvus.write.DocVectors')
    def test_processor_initialization_with_defaults(self, mock_doc_vectors):
        """Test processor initialization with default parameters"""
        taskgroup_mock = MagicMock()
        mock_vecstore = MagicMock()
        mock_doc_vectors.return_value = mock_vecstore
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        mock_doc_vectors.assert_called_once_with('http://localhost:19530')
        assert processor.vecstore == mock_vecstore

    @patch('trustgraph.storage.doc_embeddings.milvus.write.DocVectors')
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
    async def test_store_document_embeddings_single_chunk(self, processor):
        """Test storing document embeddings for a single chunk"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        chunk = ChunkEmbeddings(
            chunk=b"Test document content",
            vectors=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        )
        message.chunks = [chunk]
        
        await processor.store_document_embeddings(message)
        
        # Verify insert was called for each vector with user/collection parameters
        expected_calls = [
            ([0.1, 0.2, 0.3], "Test document content", 'test_user', 'test_collection'),
            ([0.4, 0.5, 0.6], "Test document content", 'test_user', 'test_collection'),
        ]
        
        assert processor.vecstore.insert.call_count == 2
        for i, (expected_vec, expected_doc, expected_user, expected_collection) in enumerate(expected_calls):
            actual_call = processor.vecstore.insert.call_args_list[i]
            assert actual_call[0][0] == expected_vec
            assert actual_call[0][1] == expected_doc
            assert actual_call[0][2] == expected_user
            assert actual_call[0][3] == expected_collection

    @pytest.mark.asyncio
    async def test_store_document_embeddings_multiple_chunks(self, processor, mock_message):
        """Test storing document embeddings for multiple chunks"""
        await processor.store_document_embeddings(mock_message)
        
        # Verify insert was called for each vector of each chunk with user/collection parameters
        expected_calls = [
            # Chunk 1 vectors
            ([0.1, 0.2, 0.3], "This is the first document chunk", 'test_user', 'test_collection'),
            ([0.4, 0.5, 0.6], "This is the first document chunk", 'test_user', 'test_collection'),
            # Chunk 2 vectors
            ([0.7, 0.8, 0.9], "This is the second document chunk", 'test_user', 'test_collection'),
        ]
        
        assert processor.vecstore.insert.call_count == 3
        for i, (expected_vec, expected_doc, expected_user, expected_collection) in enumerate(expected_calls):
            actual_call = processor.vecstore.insert.call_args_list[i]
            assert actual_call[0][0] == expected_vec
            assert actual_call[0][1] == expected_doc
            assert actual_call[0][2] == expected_user
            assert actual_call[0][3] == expected_collection

    @pytest.mark.asyncio
    async def test_store_document_embeddings_empty_chunk(self, processor):
        """Test storing document embeddings with empty chunk (should be skipped)"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        chunk = ChunkEmbeddings(
            chunk=b"",
            vectors=[[0.1, 0.2, 0.3]]
        )
        message.chunks = [chunk]
        
        await processor.store_document_embeddings(message)
        
        # Verify no insert was called for empty chunk
        processor.vecstore.insert.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_document_embeddings_none_chunk(self, processor):
        """Test storing document embeddings with None chunk (should be skipped)"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        chunk = ChunkEmbeddings(
            chunk=None,
            vectors=[[0.1, 0.2, 0.3]]
        )
        message.chunks = [chunk]
        
        await processor.store_document_embeddings(message)
        
        # Verify no insert was called for None chunk
        processor.vecstore.insert.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_document_embeddings_mixed_valid_invalid_chunks(self, processor):
        """Test storing document embeddings with mix of valid and invalid chunks"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        valid_chunk = ChunkEmbeddings(
            chunk=b"Valid document content",
            vectors=[[0.1, 0.2, 0.3]]
        )
        empty_chunk = ChunkEmbeddings(
            chunk=b"",
            vectors=[[0.4, 0.5, 0.6]]
        )
        none_chunk = ChunkEmbeddings(
            chunk=None,
            vectors=[[0.7, 0.8, 0.9]]
        )
        message.chunks = [valid_chunk, empty_chunk, none_chunk]
        
        await processor.store_document_embeddings(message)
        
        # Verify only valid chunk was inserted with user/collection parameters
        processor.vecstore.insert.assert_called_once_with(
            [0.1, 0.2, 0.3], "Valid document content", 'test_user', 'test_collection'
        )

    @pytest.mark.asyncio
    async def test_store_document_embeddings_empty_chunks_list(self, processor):
        """Test storing document embeddings with empty chunks list"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        message.chunks = []
        
        await processor.store_document_embeddings(message)
        
        # Verify no insert was called
        processor.vecstore.insert.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_document_embeddings_chunk_with_no_vectors(self, processor):
        """Test storing document embeddings for chunk with no vectors"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        chunk = ChunkEmbeddings(
            chunk=b"Document with no vectors",
            vectors=[]
        )
        message.chunks = [chunk]
        
        await processor.store_document_embeddings(message)
        
        # Verify no insert was called (no vectors to insert)
        processor.vecstore.insert.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_document_embeddings_different_vector_dimensions(self, processor):
        """Test storing document embeddings with different vector dimensions"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        chunk = ChunkEmbeddings(
            chunk=b"Document with mixed dimensions",
            vectors=[
                [0.1, 0.2],  # 2D vector
                [0.3, 0.4, 0.5, 0.6],  # 4D vector
                [0.7, 0.8, 0.9]  # 3D vector
            ]
        )
        message.chunks = [chunk]
        
        await processor.store_document_embeddings(message)
        
        # Verify all vectors were inserted regardless of dimension with user/collection parameters
        expected_calls = [
            ([0.1, 0.2], "Document with mixed dimensions", 'test_user', 'test_collection'),
            ([0.3, 0.4, 0.5, 0.6], "Document with mixed dimensions", 'test_user', 'test_collection'),
            ([0.7, 0.8, 0.9], "Document with mixed dimensions", 'test_user', 'test_collection'),
        ]
        
        assert processor.vecstore.insert.call_count == 3
        for i, (expected_vec, expected_doc, expected_user, expected_collection) in enumerate(expected_calls):
            actual_call = processor.vecstore.insert.call_args_list[i]
            assert actual_call[0][0] == expected_vec
            assert actual_call[0][1] == expected_doc
            assert actual_call[0][2] == expected_user
            assert actual_call[0][3] == expected_collection

    @pytest.mark.asyncio
    async def test_store_document_embeddings_unicode_content(self, processor):
        """Test storing document embeddings with Unicode content"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        chunk = ChunkEmbeddings(
            chunk="Document with Unicode: éñ中文🚀".encode('utf-8'),
            vectors=[[0.1, 0.2, 0.3]]
        )
        message.chunks = [chunk]
        
        await processor.store_document_embeddings(message)
        
        # Verify Unicode content was properly decoded and inserted with user/collection parameters
        processor.vecstore.insert.assert_called_once_with(
            [0.1, 0.2, 0.3], "Document with Unicode: éñ中文🚀", 'test_user', 'test_collection'
        )

    @pytest.mark.asyncio
    async def test_store_document_embeddings_large_chunks(self, processor):
        """Test storing document embeddings with large document chunks"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        # Create a large document chunk
        large_content = "A" * 10000  # 10KB of content
        chunk = ChunkEmbeddings(
            chunk=large_content.encode('utf-8'),
            vectors=[[0.1, 0.2, 0.3]]
        )
        message.chunks = [chunk]
        
        await processor.store_document_embeddings(message)
        
        # Verify large content was inserted with user/collection parameters
        processor.vecstore.insert.assert_called_once_with(
            [0.1, 0.2, 0.3], large_content, 'test_user', 'test_collection'
        )

    @pytest.mark.asyncio
    async def test_store_document_embeddings_whitespace_only_chunk(self, processor):
        """Test storing document embeddings with whitespace-only chunk"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        chunk = ChunkEmbeddings(
            chunk=b"   \n\t   ",
            vectors=[[0.1, 0.2, 0.3]]
        )
        message.chunks = [chunk]
        
        await processor.store_document_embeddings(message)
        
        # Verify whitespace content was inserted (not filtered out) with user/collection parameters
        processor.vecstore.insert.assert_called_once_with(
            [0.1, 0.2, 0.3], "   \n\t   ", 'test_user', 'test_collection'
        )

    @pytest.mark.asyncio
    async def test_store_document_embeddings_different_user_collection_combinations(self, processor):
        """Test storing document embeddings with different user/collection combinations"""
        test_cases = [
            ('user1', 'collection1'),
            ('user2', 'collection2'), 
            ('admin', 'production'),
            ('test@domain.com', 'test-collection.v1'),
        ]
        
        for user, collection in test_cases:
            processor.vecstore.reset_mock()  # Reset mock for each test case
            
            message = MagicMock()
            message.metadata = MagicMock()
            message.metadata.user = user
            message.metadata.collection = collection
            
            chunk = ChunkEmbeddings(
                chunk=b"Test content",
                vectors=[[0.1, 0.2, 0.3]]
            )
            message.chunks = [chunk]
            
            await processor.store_document_embeddings(message)
            
            # Verify insert was called with the correct user/collection
            processor.vecstore.insert.assert_called_once_with(
                [0.1, 0.2, 0.3], "Test content", user, collection
            )

    @pytest.mark.asyncio
    async def test_store_document_embeddings_user_collection_parameter_isolation(self, processor):
        """Test that different user/collection combinations are properly isolated"""
        # Store embeddings for user1/collection1
        message1 = MagicMock()
        message1.metadata = MagicMock()
        message1.metadata.user = 'user1'
        message1.metadata.collection = 'collection1'
        chunk1 = ChunkEmbeddings(
            chunk=b"User1 content",
            vectors=[[0.1, 0.2, 0.3]]
        )
        message1.chunks = [chunk1]
        
        # Store embeddings for user2/collection2
        message2 = MagicMock()
        message2.metadata = MagicMock() 
        message2.metadata.user = 'user2'
        message2.metadata.collection = 'collection2'
        chunk2 = ChunkEmbeddings(
            chunk=b"User2 content",
            vectors=[[0.4, 0.5, 0.6]]
        )
        message2.chunks = [chunk2]
        
        await processor.store_document_embeddings(message1)
        await processor.store_document_embeddings(message2)
        
        # Verify both calls were made with correct parameters
        expected_calls = [
            ([0.1, 0.2, 0.3], "User1 content", 'user1', 'collection1'),
            ([0.4, 0.5, 0.6], "User2 content", 'user2', 'collection2'),
        ]
        
        assert processor.vecstore.insert.call_count == 2
        for i, (expected_vec, expected_doc, expected_user, expected_collection) in enumerate(expected_calls):
            actual_call = processor.vecstore.insert.call_args_list[i]
            assert actual_call[0][0] == expected_vec
            assert actual_call[0][1] == expected_doc
            assert actual_call[0][2] == expected_user
            assert actual_call[0][3] == expected_collection

    @pytest.mark.asyncio
    async def test_store_document_embeddings_special_character_user_collection(self, processor):
        """Test storing document embeddings with special characters in user/collection names"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'user@domain.com'  # Email-like user
        message.metadata.collection = 'test-collection.v1'  # Collection with special chars
        
        chunk = ChunkEmbeddings(
            chunk=b"Special chars test",
            vectors=[[0.1, 0.2, 0.3]]
        )
        message.chunks = [chunk]
        
        await processor.store_document_embeddings(message)
        
        # Verify the exact user/collection strings are passed (sanitization happens in DocVectors)
        processor.vecstore.insert.assert_called_once_with(
            [0.1, 0.2, 0.3], "Special chars test", 'user@domain.com', 'test-collection.v1'
        )

    def test_add_args_method(self):
        """Test that add_args properly configures argument parser"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        # Mock the parent class add_args method
        with patch('trustgraph.storage.doc_embeddings.milvus.write.DocumentEmbeddingsStoreService.add_args') as mock_parent_add_args:
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
        
        with patch('trustgraph.storage.doc_embeddings.milvus.write.DocumentEmbeddingsStoreService.add_args'):
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
        
        with patch('trustgraph.storage.doc_embeddings.milvus.write.DocumentEmbeddingsStoreService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with short form
        args = parser.parse_args(['-t', 'http://short-milvus:19530'])
        
        assert args.store_uri == 'http://short-milvus:19530'

    @patch('trustgraph.storage.doc_embeddings.milvus.write.Processor.launch')
    def test_run_function(self, mock_launch):
        """Test the run function calls Processor.launch with correct parameters"""
        from trustgraph.storage.doc_embeddings.milvus.write import run, default_ident
        
        run()
        
        mock_launch.assert_called_once_with(
            default_ident,
            "\nAccepts entity/vector pairs and writes them to a Milvus store.\n"
        )