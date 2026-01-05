"""
Unit tests for trustgraph.storage.doc_embeddings.qdrant.write
Testing document embeddings storage functionality
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.storage.doc_embeddings.qdrant.write import Processor


class TestQdrantDocEmbeddingsStorage(IsolatedAsyncioTestCase):
    """Test Qdrant document embeddings storage functionality"""

    @patch('trustgraph.storage.doc_embeddings.qdrant.write.QdrantClient')
    async def test_processor_initialization_basic(self, mock_qdrant_client):
        """Test basic Qdrant processor initialization"""
        # Arrange
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        config = {
            'store_uri': 'http://localhost:6333',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock(),
            'id': 'test-doc-qdrant-processor'
        }

        # Act
        processor = Processor(**config)

        # Assert
        # Verify QdrantClient was created with correct parameters
        mock_qdrant_client.assert_called_once_with(url='http://localhost:6333', api_key='test-api-key')
        
        # Verify processor attributes
        assert hasattr(processor, 'qdrant')
        assert processor.qdrant == mock_qdrant_instance

    @patch('trustgraph.storage.doc_embeddings.qdrant.write.QdrantClient')
    async def test_processor_initialization_with_defaults(self, mock_qdrant_client):
        """Test processor initialization with default values"""
        # Arrange
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-doc-qdrant-processor'
            # No store_uri or api_key provided - should use defaults
        }

        # Act
        processor = Processor(**config)

        # Assert
        # Verify QdrantClient was created with default URI and None API key
        mock_qdrant_client.assert_called_once_with(url='http://localhost:6333', api_key=None)

    @patch('trustgraph.storage.doc_embeddings.qdrant.write.QdrantClient')
    @patch('trustgraph.storage.doc_embeddings.qdrant.write.uuid')
    async def test_store_document_embeddings_basic(self, mock_uuid, mock_qdrant_client):
        """Test storing document embeddings with basic message"""
        # Arrange
        mock_qdrant_instance = MagicMock()
        mock_qdrant_instance.collection_exists.return_value = True  # Collection already exists
        mock_qdrant_client.return_value = mock_qdrant_instance
        mock_uuid.uuid4.return_value = MagicMock()
        mock_uuid.uuid4.return_value.__str__ = MagicMock(return_value='test-uuid-123')
        
        config = {
            'store_uri': 'http://localhost:6333',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock(),
            'id': 'test-doc-qdrant-processor'
        }

        processor = Processor(**config)

        # Add collection to known_collections (simulates config push)
        processor.known_collections[('test_user', 'test_collection')] = {}

        # Create mock message with chunks and vectors
        mock_message = MagicMock()
        mock_message.metadata.user = 'test_user'
        mock_message.metadata.collection = 'test_collection'
        
        mock_chunk = MagicMock()
        mock_chunk.chunk.decode.return_value = 'test document chunk'
        mock_chunk.vectors = [[0.1, 0.2, 0.3]]  # Single vector with 3 dimensions
        
        mock_message.chunks = [mock_chunk]
        
        # Act
        await processor.store_document_embeddings(mock_message)

        # Assert
        # Verify collection existence was checked (with dimension suffix)
        expected_collection = 'd_test_user_test_collection_3'  # 3 dimensions in vector [0.1, 0.2, 0.3]
        mock_qdrant_instance.collection_exists.assert_called_once_with(expected_collection)
        
        # Verify upsert was called
        mock_qdrant_instance.upsert.assert_called_once()
        
        # Verify upsert parameters
        upsert_call_args = mock_qdrant_instance.upsert.call_args
        assert upsert_call_args[1]['collection_name'] == 'd_test_user_test_collection_3'
        assert len(upsert_call_args[1]['points']) == 1
        
        point = upsert_call_args[1]['points'][0]
        assert point.vector == [0.1, 0.2, 0.3]
        assert point.payload['doc'] == 'test document chunk'

    @patch('trustgraph.storage.doc_embeddings.qdrant.write.QdrantClient')
    @patch('trustgraph.storage.doc_embeddings.qdrant.write.uuid')
    async def test_store_document_embeddings_multiple_chunks(self, mock_uuid, mock_qdrant_client):
        """Test storing document embeddings with multiple chunks"""
        # Arrange
        mock_qdrant_instance = MagicMock()
        mock_qdrant_instance.collection_exists.return_value = True
        mock_qdrant_client.return_value = mock_qdrant_instance
        mock_uuid.uuid4.return_value = MagicMock()
        mock_uuid.uuid4.return_value.__str__ = MagicMock(return_value='test-uuid')
        
        config = {
            'store_uri': 'http://localhost:6333',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock(),
            'id': 'test-doc-qdrant-processor'
        }

        processor = Processor(**config)

        # Add collection to known_collections (simulates config push)
        processor.known_collections[('multi_user', 'multi_collection')] = {}

        # Create mock message with multiple chunks
        mock_message = MagicMock()
        mock_message.metadata.user = 'multi_user'
        mock_message.metadata.collection = 'multi_collection'
        
        mock_chunk1 = MagicMock()
        mock_chunk1.chunk.decode.return_value = 'first document chunk'
        mock_chunk1.vectors = [[0.1, 0.2]]
        
        mock_chunk2 = MagicMock()
        mock_chunk2.chunk.decode.return_value = 'second document chunk'
        mock_chunk2.vectors = [[0.3, 0.4]]
        
        mock_message.chunks = [mock_chunk1, mock_chunk2]
        
        # Act
        await processor.store_document_embeddings(mock_message)

        # Assert
        # Should be called twice (once per chunk)
        assert mock_qdrant_instance.upsert.call_count == 2
        
        # Verify both chunks were processed
        upsert_calls = mock_qdrant_instance.upsert.call_args_list
        
        # First chunk
        first_call = upsert_calls[0]
        first_point = first_call[1]['points'][0]
        assert first_point.vector == [0.1, 0.2]
        assert first_point.payload['doc'] == 'first document chunk'
        
        # Second chunk
        second_call = upsert_calls[1]
        second_point = second_call[1]['points'][0]
        assert second_point.vector == [0.3, 0.4]
        assert second_point.payload['doc'] == 'second document chunk'

    @patch('trustgraph.storage.doc_embeddings.qdrant.write.QdrantClient')
    @patch('trustgraph.storage.doc_embeddings.qdrant.write.uuid')
    async def test_store_document_embeddings_multiple_vectors_per_chunk(self, mock_uuid, mock_qdrant_client):
        """Test storing document embeddings with multiple vectors per chunk"""
        # Arrange
        mock_qdrant_instance = MagicMock()
        mock_qdrant_instance.collection_exists.return_value = True
        mock_qdrant_client.return_value = mock_qdrant_instance
        mock_uuid.uuid4.return_value = MagicMock()
        mock_uuid.uuid4.return_value.__str__ = MagicMock(return_value='test-uuid')
        
        config = {
            'store_uri': 'http://localhost:6333',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock(),
            'id': 'test-doc-qdrant-processor'
        }

        processor = Processor(**config)

        # Add collection to known_collections (simulates config push)
        processor.known_collections[('vector_user', 'vector_collection')] = {}

        # Create mock message with chunk having multiple vectors
        mock_message = MagicMock()
        mock_message.metadata.user = 'vector_user'
        mock_message.metadata.collection = 'vector_collection'
        
        mock_chunk = MagicMock()
        mock_chunk.chunk.decode.return_value = 'multi-vector document chunk'
        mock_chunk.vectors = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9]
        ]
        
        mock_message.chunks = [mock_chunk]
        
        # Act
        await processor.store_document_embeddings(mock_message)

        # Assert
        # Should be called 3 times (once per vector)
        assert mock_qdrant_instance.upsert.call_count == 3
        
        # Verify all vectors were processed
        upsert_calls = mock_qdrant_instance.upsert.call_args_list
        
        expected_vectors = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6], 
            [0.7, 0.8, 0.9]
        ]
        
        for i, call in enumerate(upsert_calls):
            point = call[1]['points'][0]
            assert point.vector == expected_vectors[i]
            assert point.payload['doc'] == 'multi-vector document chunk'

    @patch('trustgraph.storage.doc_embeddings.qdrant.write.QdrantClient')
    async def test_store_document_embeddings_empty_chunk(self, mock_qdrant_client):
        """Test storing document embeddings skips empty chunks"""
        # Arrange
        mock_qdrant_instance = MagicMock()
        mock_qdrant_instance.collection_exists.return_value = True  # Collection exists
        mock_qdrant_client.return_value = mock_qdrant_instance

        config = {
            'store_uri': 'http://localhost:6333',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock(),
            'id': 'test-doc-qdrant-processor'
        }

        processor = Processor(**config)

        # Create mock message with empty chunk
        mock_message = MagicMock()
        mock_message.metadata.user = 'empty_user'
        mock_message.metadata.collection = 'empty_collection'

        mock_chunk_empty = MagicMock()
        mock_chunk_empty.chunk.decode.return_value = ""  # Empty string
        mock_chunk_empty.vectors = [[0.1, 0.2]]

        mock_message.chunks = [mock_chunk_empty]

        # Act
        await processor.store_document_embeddings(mock_message)

        # Assert
        # Should not call upsert for empty chunks
        mock_qdrant_instance.upsert.assert_not_called()
        # collection_exists should NOT be called since we return early for empty chunks
        mock_qdrant_instance.collection_exists.assert_not_called()

    @patch('trustgraph.storage.doc_embeddings.qdrant.write.QdrantClient')
    @patch('trustgraph.storage.doc_embeddings.qdrant.write.uuid')
    async def test_collection_creation_when_not_exists(self, mock_uuid, mock_qdrant_client):
        """Test that writing to non-existent collection creates it lazily"""
        # Arrange
        mock_qdrant_instance = MagicMock()
        mock_qdrant_instance.collection_exists.return_value = False  # Collection doesn't exist
        mock_qdrant_client.return_value = mock_qdrant_instance
        mock_uuid.uuid4.return_value = MagicMock()
        mock_uuid.uuid4.return_value.__str__ = MagicMock(return_value='test-uuid')

        config = {
            'store_uri': 'http://localhost:6333',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock(),
            'id': 'test-doc-qdrant-processor'
        }

        processor = Processor(**config)

        # Add collection to known_collections (simulates config push)
        processor.known_collections[('new_user', 'new_collection')] = {}

        # Create mock message
        mock_message = MagicMock()
        mock_message.metadata.user = 'new_user'
        mock_message.metadata.collection = 'new_collection'

        mock_chunk = MagicMock()
        mock_chunk.chunk.decode.return_value = 'test chunk'
        mock_chunk.vectors = [[0.1, 0.2, 0.3, 0.4, 0.5]]  # 5 dimensions

        mock_message.chunks = [mock_chunk]

        # Act
        await processor.store_document_embeddings(mock_message)

        # Assert - collection should be lazily created
        expected_collection = 'd_new_user_new_collection_5'  # 5 dimensions
        mock_qdrant_instance.collection_exists.assert_called_once_with(expected_collection)
        mock_qdrant_instance.create_collection.assert_called_once()

        # Verify create_collection was called with correct parameters
        create_call = mock_qdrant_instance.create_collection.call_args
        assert create_call[1]['collection_name'] == expected_collection
        assert create_call[1]['vectors_config'].size == 5

        # Verify upsert was still called
        mock_qdrant_instance.upsert.assert_called_once()

    @patch('trustgraph.storage.doc_embeddings.qdrant.write.QdrantClient')
    @patch('trustgraph.storage.doc_embeddings.qdrant.write.uuid')
    async def test_collection_creation_exception(self, mock_uuid, mock_qdrant_client):
        """Test that collection creation errors are propagated"""
        # Arrange
        mock_qdrant_instance = MagicMock()
        mock_qdrant_instance.collection_exists.return_value = False  # Collection doesn't exist
        # Simulate creation failure
        mock_qdrant_instance.create_collection.side_effect = Exception("Connection error")
        mock_qdrant_client.return_value = mock_qdrant_instance
        mock_uuid.uuid4.return_value = MagicMock()
        mock_uuid.uuid4.return_value.__str__ = MagicMock(return_value='test-uuid')

        config = {
            'store_uri': 'http://localhost:6333',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock(),
            'id': 'test-doc-qdrant-processor'
        }

        processor = Processor(**config)

        # Add collection to known_collections (simulates config push)
        processor.known_collections[('error_user', 'error_collection')] = {}

        # Create mock message
        mock_message = MagicMock()
        mock_message.metadata.user = 'error_user'
        mock_message.metadata.collection = 'error_collection'

        mock_chunk = MagicMock()
        mock_chunk.chunk.decode.return_value = 'test chunk'
        mock_chunk.vectors = [[0.1, 0.2]]

        mock_message.chunks = [mock_chunk]

        # Act & Assert - should propagate the creation error
        with pytest.raises(Exception, match="Connection error"):
            await processor.store_document_embeddings(mock_message)

    @patch('trustgraph.storage.doc_embeddings.qdrant.write.QdrantClient')
    @patch('trustgraph.storage.doc_embeddings.qdrant.write.uuid')
    async def test_collection_validation_on_write(self, mock_uuid, mock_qdrant_client):
        """Test collection validation checks collection exists before writing"""
        # Arrange
        mock_qdrant_instance = MagicMock()
        mock_qdrant_instance.collection_exists.return_value = True
        mock_qdrant_client.return_value = mock_qdrant_instance
        mock_uuid.uuid4.return_value = MagicMock()
        mock_uuid.uuid4.return_value.__str__ = MagicMock(return_value='test-uuid')

        config = {
            'store_uri': 'http://localhost:6333',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock(),
            'id': 'test-doc-qdrant-processor'
        }

        processor = Processor(**config)

        # Add collection to known_collections (simulates config push)
        processor.known_collections[('cache_user', 'cache_collection')] = {}

        # Create first mock message
        mock_message1 = MagicMock()
        mock_message1.metadata.user = 'cache_user'
        mock_message1.metadata.collection = 'cache_collection'

        mock_chunk1 = MagicMock()
        mock_chunk1.chunk.decode.return_value = 'first chunk'
        mock_chunk1.vectors = [[0.1, 0.2, 0.3]]

        mock_message1.chunks = [mock_chunk1]

        # First call
        await processor.store_document_embeddings(mock_message1)

        # Reset mock to track second call
        mock_qdrant_instance.reset_mock()
        mock_qdrant_instance.collection_exists.return_value = True

        # Create second mock message with same dimensions
        mock_message2 = MagicMock()
        mock_message2.metadata.user = 'cache_user'
        mock_message2.metadata.collection = 'cache_collection'

        mock_chunk2 = MagicMock()
        mock_chunk2.chunk.decode.return_value = 'second chunk'
        mock_chunk2.vectors = [[0.4, 0.5, 0.6]]  # Same dimension (3)

        mock_message2.chunks = [mock_chunk2]

        # Act - Second call with same collection
        await processor.store_document_embeddings(mock_message2)

        # Assert
        expected_collection = 'd_cache_user_cache_collection_3'  # 3 dimensions

        # Verify collection existence is checked on each write
        mock_qdrant_instance.collection_exists.assert_called_once_with(expected_collection)

        # But upsert should still be called
        mock_qdrant_instance.upsert.assert_called_once()

    @patch('trustgraph.storage.doc_embeddings.qdrant.write.QdrantClient')
    @patch('trustgraph.storage.doc_embeddings.qdrant.write.uuid')
    async def test_different_dimensions_different_collections(self, mock_uuid, mock_qdrant_client):
        """Test that different vector dimensions create different collections"""
        # Arrange
        mock_qdrant_instance = MagicMock()
        mock_qdrant_instance.collection_exists.return_value = True
        mock_qdrant_client.return_value = mock_qdrant_instance
        mock_uuid.uuid4.return_value = MagicMock()
        mock_uuid.uuid4.return_value.__str__ = MagicMock(return_value='test-uuid')

        config = {
            'store_uri': 'http://localhost:6333',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock(),
            'id': 'test-doc-qdrant-processor'
        }

        processor = Processor(**config)

        # Add collection to known_collections (simulates config push)
        processor.known_collections[('dim_user', 'dim_collection')] = {}

        # Create mock message with different dimension vectors
        mock_message = MagicMock()
        mock_message.metadata.user = 'dim_user'
        mock_message.metadata.collection = 'dim_collection'

        mock_chunk = MagicMock()
        mock_chunk.chunk.decode.return_value = 'dimension test chunk'
        mock_chunk.vectors = [
            [0.1, 0.2],          # 2 dimensions
            [0.3, 0.4, 0.5]      # 3 dimensions
        ]

        mock_message.chunks = [mock_chunk]

        # Act
        await processor.store_document_embeddings(mock_message)

        # Assert
        # Should check existence of DIFFERENT collections for each dimension
        assert mock_qdrant_instance.collection_exists.call_count == 2

        # Verify the two different collection names were checked
        collection_exists_calls = [call[0][0] for call in mock_qdrant_instance.collection_exists.call_args_list]
        assert 'd_dim_user_dim_collection_2' in collection_exists_calls  # 2-dim vector
        assert 'd_dim_user_dim_collection_3' in collection_exists_calls  # 3-dim vector

        # Should upsert to different collections for each vector
        assert mock_qdrant_instance.upsert.call_count == 2

        upsert_calls = mock_qdrant_instance.upsert.call_args_list
        assert upsert_calls[0][1]['collection_name'] == 'd_dim_user_dim_collection_2'
        assert upsert_calls[1][1]['collection_name'] == 'd_dim_user_dim_collection_3'

    @patch('trustgraph.storage.doc_embeddings.qdrant.write.QdrantClient')
    async def test_add_args_calls_parent(self, mock_qdrant_client):
        """Test that add_args() calls parent add_args method"""
        # Arrange
        mock_qdrant_client.return_value = MagicMock()
        mock_parser = MagicMock()
        
        # Act
        with patch('trustgraph.base.DocumentEmbeddingsStoreService.add_args') as mock_parent_add_args:
            Processor.add_args(mock_parser)

        # Assert
        mock_parent_add_args.assert_called_once_with(mock_parser)
        
        # Verify processor-specific arguments were added
        assert mock_parser.add_argument.call_count >= 2  # At least store-uri and api-key

    @patch('trustgraph.storage.doc_embeddings.qdrant.write.QdrantClient')
    @patch('trustgraph.storage.doc_embeddings.qdrant.write.uuid')
    async def test_utf8_decoding_handling(self, mock_uuid, mock_qdrant_client):
        """Test proper UTF-8 decoding of chunk text"""
        # Arrange
        mock_qdrant_instance = MagicMock()
        mock_qdrant_instance.collection_exists.return_value = True
        mock_qdrant_client.return_value = mock_qdrant_instance
        mock_uuid.uuid4.return_value = MagicMock()
        mock_uuid.uuid4.return_value.__str__ = MagicMock(return_value='test-uuid')
        
        config = {
            'store_uri': 'http://localhost:6333',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock(),
            'id': 'test-doc-qdrant-processor'
        }

        processor = Processor(**config)

        # Add collection to known_collections (simulates config push)
        processor.known_collections[('utf8_user', 'utf8_collection')] = {}

        # Create mock message with UTF-8 encoded text
        mock_message = MagicMock()
        mock_message.metadata.user = 'utf8_user'
        mock_message.metadata.collection = 'utf8_collection'
        
        mock_chunk = MagicMock()
        mock_chunk.chunk.decode.return_value = 'UTF-8 text with special chars: café, naïve, résumé'
        mock_chunk.vectors = [[0.1, 0.2]]
        
        mock_message.chunks = [mock_chunk]
        
        # Act
        await processor.store_document_embeddings(mock_message)

        # Assert
        # Verify chunk.decode was called with 'utf-8'
        mock_chunk.chunk.decode.assert_called_with('utf-8')
        
        # Verify the decoded text was stored in payload
        upsert_call_args = mock_qdrant_instance.upsert.call_args
        point = upsert_call_args[1]['points'][0]
        assert point.payload['doc'] == 'UTF-8 text with special chars: café, naïve, résumé'

    @patch('trustgraph.storage.doc_embeddings.qdrant.write.QdrantClient')
    async def test_chunk_decode_exception_handling(self, mock_qdrant_client):
        """Test handling of chunk decode exceptions"""
        # Arrange
        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance
        
        config = {
            'store_uri': 'http://localhost:6333',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock(),
            'id': 'test-doc-qdrant-processor'
        }

        processor = Processor(**config)

        # Add collection to known_collections (simulates config push)
        processor.known_collections[('decode_user', 'decode_collection')] = {}

        # Create mock message with decode error
        mock_message = MagicMock()
        mock_message.metadata.user = 'decode_user'
        mock_message.metadata.collection = 'decode_collection'
        
        mock_chunk = MagicMock()
        mock_chunk.chunk.decode.side_effect = UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid start byte')
        mock_chunk.vectors = [[0.1, 0.2]]
        
        mock_message.chunks = [mock_chunk]
        
        # Act & Assert
        with pytest.raises(UnicodeDecodeError):
            await processor.store_document_embeddings(mock_message)


if __name__ == '__main__':
    pytest.main([__file__])