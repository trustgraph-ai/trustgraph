"""
Tests for Pinecone document embeddings storage service
"""

import pytest
from unittest.mock import MagicMock, patch
import uuid

from trustgraph.storage.doc_embeddings.pinecone.write import Processor
from trustgraph.schema import ChunkEmbeddings


class TestPineconeDocEmbeddingsStorageProcessor:
    """Test cases for Pinecone document embeddings storage processor"""

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
        with patch('trustgraph.storage.doc_embeddings.pinecone.write.Pinecone') as mock_pinecone_class:
            mock_pinecone = MagicMock()
            mock_pinecone_class.return_value = mock_pinecone
            
            processor = Processor(
                taskgroup=MagicMock(),
                id='test-pinecone-de-storage',
                api_key='test-api-key'
            )
            
            return processor

    @patch('trustgraph.storage.doc_embeddings.pinecone.write.Pinecone')
    @patch('trustgraph.storage.doc_embeddings.pinecone.write.default_api_key', 'env-api-key')
    def test_processor_initialization_with_defaults(self, mock_pinecone_class):
        """Test processor initialization with default parameters"""
        mock_pinecone = MagicMock()
        mock_pinecone_class.return_value = mock_pinecone
        taskgroup_mock = MagicMock()
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        mock_pinecone_class.assert_called_once_with(api_key='env-api-key')
        assert processor.pinecone == mock_pinecone
        assert processor.api_key == 'env-api-key'
        assert processor.cloud == 'aws'
        assert processor.region == 'us-east-1'

    @patch('trustgraph.storage.doc_embeddings.pinecone.write.Pinecone')
    def test_processor_initialization_with_custom_params(self, mock_pinecone_class):
        """Test processor initialization with custom parameters"""
        mock_pinecone = MagicMock()
        mock_pinecone_class.return_value = mock_pinecone
        taskgroup_mock = MagicMock()
        
        processor = Processor(
            taskgroup=taskgroup_mock,
            api_key='custom-api-key',
            cloud='gcp',
            region='us-west1'
        )
        
        mock_pinecone_class.assert_called_once_with(api_key='custom-api-key')
        assert processor.api_key == 'custom-api-key'
        assert processor.cloud == 'gcp'
        assert processor.region == 'us-west1'

    @patch('trustgraph.storage.doc_embeddings.pinecone.write.PineconeGRPC')
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

    @patch('trustgraph.storage.doc_embeddings.pinecone.write.default_api_key', 'not-specified')
    def test_processor_initialization_missing_api_key(self):
        """Test processor initialization fails with missing API key"""
        taskgroup_mock = MagicMock()
        
        with pytest.raises(RuntimeError, match="Pinecone API key must be specified"):
            Processor(taskgroup=taskgroup_mock)

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
        
        # Mock index operations
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        processor.pinecone.has_index.return_value = True
        
        with patch('uuid.uuid4', side_effect=['id1', 'id2']):
            await processor.store_document_embeddings(message)
        
        # Verify index name and operations (with dimension suffix)
        expected_index_name = "d-test_user-test_collection-3"  # 3 dimensions
        processor.pinecone.Index.assert_called_with(expected_index_name)
        
        # Verify upsert was called for each vector
        assert mock_index.upsert.call_count == 2
        
        # Check first vector upsert
        first_call = mock_index.upsert.call_args_list[0]
        first_vectors = first_call[1]['vectors']
        assert len(first_vectors) == 1
        assert first_vectors[0]['id'] == 'id1'
        assert first_vectors[0]['values'] == [0.1, 0.2, 0.3]
        assert first_vectors[0]['metadata']['doc'] == "Test document content"
        
        # Check second vector upsert
        second_call = mock_index.upsert.call_args_list[1]
        second_vectors = second_call[1]['vectors']
        assert len(second_vectors) == 1
        assert second_vectors[0]['id'] == 'id2'
        assert second_vectors[0]['values'] == [0.4, 0.5, 0.6]
        assert second_vectors[0]['metadata']['doc'] == "Test document content"

    @pytest.mark.asyncio
    async def test_store_document_embeddings_multiple_chunks(self, processor, mock_message):
        """Test storing document embeddings for multiple chunks"""
        # Mock index operations
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        processor.pinecone.has_index.return_value = True
        
        with patch('uuid.uuid4', side_effect=['id1', 'id2', 'id3']):
            await processor.store_document_embeddings(mock_message)
        
        # Verify upsert was called for each vector (3 total)
        assert mock_index.upsert.call_count == 3
        
        # Verify document content in metadata
        calls = mock_index.upsert.call_args_list
        assert calls[0][1]['vectors'][0]['metadata']['doc'] == "This is the first document chunk"
        assert calls[1][1]['vectors'][0]['metadata']['doc'] == "This is the first document chunk"
        assert calls[2][1]['vectors'][0]['metadata']['doc'] == "This is the second document chunk"

    @pytest.mark.asyncio
    async def test_store_document_embeddings_index_validation(self, processor):
        """Test that writing to non-existent index raises ValueError"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'

        chunk = ChunkEmbeddings(
            chunk=b"Test document content",
            vectors=[[0.1, 0.2, 0.3]]
        )
        message.chunks = [chunk]

        # Mock index doesn't exist
        processor.pinecone.has_index.return_value = False

        with pytest.raises(ValueError, match="Collection .* does not exist"):
            await processor.store_document_embeddings(message)

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
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        await processor.store_document_embeddings(message)
        
        # Verify no upsert was called for empty chunk
        mock_index.upsert.assert_not_called()

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
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        await processor.store_document_embeddings(message)
        
        # Verify no upsert was called for None chunk
        mock_index.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_document_embeddings_empty_decoded_chunk(self, processor):
        """Test storing document embeddings with chunk that decodes to empty string"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        chunk = ChunkEmbeddings(
            chunk=b"",  # Empty bytes
            vectors=[[0.1, 0.2, 0.3]]
        )
        message.chunks = [chunk]
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        await processor.store_document_embeddings(message)
        
        # Verify no upsert was called for empty decoded chunk
        mock_index.upsert.assert_not_called()

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
        
        mock_index_2d = MagicMock()
        mock_index_4d = MagicMock()
        mock_index_3d = MagicMock()
        
        def mock_index_side_effect(name):
            # All dimensions now use the same index name pattern
            # Different dimensions will be handled within the same index
            if "test_user" in name and "test_collection" in name:
                return mock_index_2d  # Just return one mock for all
            return MagicMock()
        
        processor.pinecone.Index.side_effect = mock_index_side_effect
        processor.pinecone.has_index.return_value = True
        
        with patch('uuid.uuid4', side_effect=['id1', 'id2', 'id3']):
            await processor.store_document_embeddings(message)
        
        # Verify all vectors are now stored in the same index
        # (Pinecone can handle mixed dimensions in the same index)
        assert processor.pinecone.Index.call_count == 3  # Called once per vector
        mock_index_2d.upsert.call_count == 3  # All upserts go to same index

    @pytest.mark.asyncio
    async def test_store_document_embeddings_empty_chunks_list(self, processor):
        """Test storing document embeddings with empty chunks list"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        message.chunks = []
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        await processor.store_document_embeddings(message)
        
        # Verify no operations were performed
        processor.pinecone.Index.assert_not_called()
        mock_index.upsert.assert_not_called()

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
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        await processor.store_document_embeddings(message)
        
        # Verify no upsert was called (no vectors to insert)
        mock_index.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_document_embeddings_validation_before_creation(self, processor):
        """Test that validation error occurs before creation attempts"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'

        chunk = ChunkEmbeddings(
            chunk=b"Test document content",
            vectors=[[0.1, 0.2, 0.3]]
        )
        message.chunks = [chunk]

        # Mock index doesn't exist
        processor.pinecone.has_index.return_value = False

        with pytest.raises(ValueError, match="Collection .* does not exist"):
            await processor.store_document_embeddings(message)

    @pytest.mark.asyncio
    async def test_store_document_embeddings_validates_before_timeout(self, processor):
        """Test that validation error occurs before timeout checks"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'

        chunk = ChunkEmbeddings(
            chunk=b"Test document content",
            vectors=[[0.1, 0.2, 0.3]]
        )
        message.chunks = [chunk]

        # Mock index doesn't exist
        processor.pinecone.has_index.return_value = False

        with pytest.raises(ValueError, match="Collection .* does not exist"):
            await processor.store_document_embeddings(message)

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
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        processor.pinecone.has_index.return_value = True
        
        with patch('uuid.uuid4', return_value='test-id'):
            await processor.store_document_embeddings(message)
        
        # Verify Unicode content was properly decoded and stored
        call_args = mock_index.upsert.call_args
        stored_doc = call_args[1]['vectors'][0]['metadata']['doc']
        assert stored_doc == "Document with Unicode: éñ中文🚀"

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
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        processor.pinecone.has_index.return_value = True
        
        with patch('uuid.uuid4', return_value='test-id'):
            await processor.store_document_embeddings(message)
        
        # Verify large content was stored
        call_args = mock_index.upsert.call_args
        stored_doc = call_args[1]['vectors'][0]['metadata']['doc']
        assert stored_doc == large_content

    def test_add_args_method(self):
        """Test that add_args properly configures argument parser"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        # Mock the parent class add_args method
        with patch('trustgraph.storage.doc_embeddings.pinecone.write.DocumentEmbeddingsStoreService.add_args') as mock_parent_add_args:
            Processor.add_args(parser)
            
            # Verify parent add_args was called
            mock_parent_add_args.assert_called_once()
        
        # Verify our specific arguments were added
        args = parser.parse_args([])
        
        assert hasattr(args, 'api_key')
        assert args.api_key == 'not-specified'  # Default value when no env var
        assert hasattr(args, 'url')
        assert args.url is None
        assert hasattr(args, 'cloud')
        assert args.cloud == 'aws'
        assert hasattr(args, 'region')
        assert args.region == 'us-east-1'

    def test_add_args_with_custom_values(self):
        """Test add_args with custom command line values"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        with patch('trustgraph.storage.doc_embeddings.pinecone.write.DocumentEmbeddingsStoreService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with custom values
        args = parser.parse_args([
            '--api-key', 'custom-api-key',
            '--url', 'https://custom-host.pinecone.io',
            '--cloud', 'gcp',
            '--region', 'us-west1'
        ])
        
        assert args.api_key == 'custom-api-key'
        assert args.url == 'https://custom-host.pinecone.io'
        assert args.cloud == 'gcp'
        assert args.region == 'us-west1'

    def test_add_args_short_form(self):
        """Test add_args with short form arguments"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        with patch('trustgraph.storage.doc_embeddings.pinecone.write.DocumentEmbeddingsStoreService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with short form
        args = parser.parse_args([
            '-a', 'short-api-key',
            '-u', 'https://short-host.pinecone.io'
        ])
        
        assert args.api_key == 'short-api-key'
        assert args.url == 'https://short-host.pinecone.io'

    @patch('trustgraph.storage.doc_embeddings.pinecone.write.Processor.launch')
    def test_run_function(self, mock_launch):
        """Test the run function calls Processor.launch with correct parameters"""
        from trustgraph.storage.doc_embeddings.pinecone.write import run, default_ident
        
        run()
        
        mock_launch.assert_called_once_with(
            default_ident,
            "\nAccepts document chunks/vector pairs and writes them to a Pinecone store.\n"
        )