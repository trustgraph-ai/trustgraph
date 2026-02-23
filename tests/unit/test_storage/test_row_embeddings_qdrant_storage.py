"""
Unit tests for trustgraph.storage.row_embeddings.qdrant.write
Tests the Stage 2 processor that stores pre-computed row embeddings in Qdrant.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase


class TestQdrantRowEmbeddingsStorage(IsolatedAsyncioTestCase):
    """Test Qdrant row embeddings storage functionality"""

    @patch('trustgraph.storage.row_embeddings.qdrant.write.QdrantClient')
    async def test_processor_initialization_basic(self, mock_qdrant_client):
        """Test basic Qdrant processor initialization"""
        from trustgraph.storage.row_embeddings.qdrant.write import Processor

        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance

        config = {
            'store_uri': 'http://localhost:6333',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock(),
            'id': 'test-qdrant-processor'
        }

        processor = Processor(**config)

        mock_qdrant_client.assert_called_once_with(
            url='http://localhost:6333', api_key='test-api-key'
        )
        assert hasattr(processor, 'qdrant')
        assert processor.qdrant == mock_qdrant_instance

    @patch('trustgraph.storage.row_embeddings.qdrant.write.QdrantClient')
    async def test_processor_initialization_with_defaults(self, mock_qdrant_client):
        """Test processor initialization with default values"""
        from trustgraph.storage.row_embeddings.qdrant.write import Processor

        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-qdrant-processor'
        }

        processor = Processor(**config)

        mock_qdrant_client.assert_called_once_with(
            url='http://localhost:6333', api_key=None
        )

    @patch('trustgraph.storage.row_embeddings.qdrant.write.QdrantClient')
    async def test_sanitize_name(self, mock_qdrant_client):
        """Test name sanitization for Qdrant collections"""
        from trustgraph.storage.row_embeddings.qdrant.write import Processor

        mock_qdrant_client.return_value = MagicMock()

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        # Test basic sanitization
        assert processor.sanitize_name("simple") == "simple"
        assert processor.sanitize_name("with-dash") == "with_dash"
        assert processor.sanitize_name("with.dot") == "with_dot"
        assert processor.sanitize_name("UPPERCASE") == "uppercase"

        # Test numeric prefix handling
        assert processor.sanitize_name("123start") == "r_123start"
        assert processor.sanitize_name("_underscore") == "r__underscore"

    @patch('trustgraph.storage.row_embeddings.qdrant.write.QdrantClient')
    async def test_get_collection_name(self, mock_qdrant_client):
        """Test Qdrant collection name generation"""
        from trustgraph.storage.row_embeddings.qdrant.write import Processor

        mock_qdrant_client.return_value = MagicMock()

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        collection_name = processor.get_collection_name(
            user="test_user",
            collection="test_collection",
            schema_name="customer_data",
            dimension=384
        )

        assert collection_name == "rows_test_user_test_collection_customer_data_384"

    @patch('trustgraph.storage.row_embeddings.qdrant.write.QdrantClient')
    async def test_ensure_collection_creates_new(self, mock_qdrant_client):
        """Test that ensure_collection creates a new collection when needed"""
        from trustgraph.storage.row_embeddings.qdrant.write import Processor

        mock_qdrant_instance = MagicMock()
        mock_qdrant_instance.collection_exists.return_value = False
        mock_qdrant_client.return_value = mock_qdrant_instance

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        processor.ensure_collection("test_collection", 384)

        mock_qdrant_instance.collection_exists.assert_called_once_with("test_collection")
        mock_qdrant_instance.create_collection.assert_called_once()

        # Verify the collection is cached
        assert "test_collection" in processor.created_collections

    @patch('trustgraph.storage.row_embeddings.qdrant.write.QdrantClient')
    async def test_ensure_collection_skips_existing(self, mock_qdrant_client):
        """Test that ensure_collection skips creation when collection exists"""
        from trustgraph.storage.row_embeddings.qdrant.write import Processor

        mock_qdrant_instance = MagicMock()
        mock_qdrant_instance.collection_exists.return_value = True
        mock_qdrant_client.return_value = mock_qdrant_instance

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        processor.ensure_collection("existing_collection", 384)

        mock_qdrant_instance.collection_exists.assert_called_once()
        mock_qdrant_instance.create_collection.assert_not_called()

    @patch('trustgraph.storage.row_embeddings.qdrant.write.QdrantClient')
    async def test_ensure_collection_uses_cache(self, mock_qdrant_client):
        """Test that ensure_collection uses cache for previously created collections"""
        from trustgraph.storage.row_embeddings.qdrant.write import Processor

        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)
        processor.created_collections.add("cached_collection")

        processor.ensure_collection("cached_collection", 384)

        # Should not check or create - just return
        mock_qdrant_instance.collection_exists.assert_not_called()
        mock_qdrant_instance.create_collection.assert_not_called()

    @patch('trustgraph.storage.row_embeddings.qdrant.write.QdrantClient')
    @patch('trustgraph.storage.row_embeddings.qdrant.write.uuid')
    async def test_on_embeddings_basic(self, mock_uuid, mock_qdrant_client):
        """Test processing basic row embeddings message"""
        from trustgraph.storage.row_embeddings.qdrant.write import Processor
        from trustgraph.schema import RowEmbeddings, RowIndexEmbedding, Metadata

        mock_qdrant_instance = MagicMock()
        mock_qdrant_instance.collection_exists.return_value = True
        mock_qdrant_client.return_value = mock_qdrant_instance
        mock_uuid.uuid4.return_value = 'test-uuid-123'

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)
        processor.known_collections[('test_user', 'test_collection')] = {}

        # Create embeddings message
        metadata = MagicMock()
        metadata.user = 'test_user'
        metadata.collection = 'test_collection'
        metadata.id = 'doc-123'

        embedding = RowIndexEmbedding(
            index_name='customer_id',
            index_value=['CUST001'],
            text='CUST001',
            vectors=[[0.1, 0.2, 0.3]]
        )

        embeddings_msg = RowEmbeddings(
            metadata=metadata,
            schema_name='customers',
            embeddings=[embedding]
        )

        # Mock message wrapper
        mock_msg = MagicMock()
        mock_msg.value.return_value = embeddings_msg

        await processor.on_embeddings(mock_msg, MagicMock(), MagicMock())

        # Verify upsert was called
        mock_qdrant_instance.upsert.assert_called_once()

        # Verify upsert parameters
        upsert_call_args = mock_qdrant_instance.upsert.call_args
        assert upsert_call_args[1]['collection_name'] == 'rows_test_user_test_collection_customers_3'

        point = upsert_call_args[1]['points'][0]
        assert point.vector == [0.1, 0.2, 0.3]
        assert point.payload['index_name'] == 'customer_id'
        assert point.payload['index_value'] == ['CUST001']
        assert point.payload['text'] == 'CUST001'

    @patch('trustgraph.storage.row_embeddings.qdrant.write.QdrantClient')
    @patch('trustgraph.storage.row_embeddings.qdrant.write.uuid')
    async def test_on_embeddings_multiple_vectors(self, mock_uuid, mock_qdrant_client):
        """Test processing embeddings with multiple vectors"""
        from trustgraph.storage.row_embeddings.qdrant.write import Processor
        from trustgraph.schema import RowEmbeddings, RowIndexEmbedding

        mock_qdrant_instance = MagicMock()
        mock_qdrant_instance.collection_exists.return_value = True
        mock_qdrant_client.return_value = mock_qdrant_instance
        mock_uuid.uuid4.return_value = 'test-uuid'

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)
        processor.known_collections[('test_user', 'test_collection')] = {}

        metadata = MagicMock()
        metadata.user = 'test_user'
        metadata.collection = 'test_collection'
        metadata.id = 'doc-123'

        # Embedding with multiple vectors
        embedding = RowIndexEmbedding(
            index_name='name',
            index_value=['John Doe'],
            text='John Doe',
            vectors=[[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        )

        embeddings_msg = RowEmbeddings(
            metadata=metadata,
            schema_name='people',
            embeddings=[embedding]
        )

        mock_msg = MagicMock()
        mock_msg.value.return_value = embeddings_msg

        await processor.on_embeddings(mock_msg, MagicMock(), MagicMock())

        # Should be called 3 times (once per vector)
        assert mock_qdrant_instance.upsert.call_count == 3

    @patch('trustgraph.storage.row_embeddings.qdrant.write.QdrantClient')
    async def test_on_embeddings_skips_empty_vectors(self, mock_qdrant_client):
        """Test that embeddings with no vectors are skipped"""
        from trustgraph.storage.row_embeddings.qdrant.write import Processor
        from trustgraph.schema import RowEmbeddings, RowIndexEmbedding

        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)
        processor.known_collections[('test_user', 'test_collection')] = {}

        metadata = MagicMock()
        metadata.user = 'test_user'
        metadata.collection = 'test_collection'
        metadata.id = 'doc-123'

        # Embedding with no vectors
        embedding = RowIndexEmbedding(
            index_name='id',
            index_value=['123'],
            text='123',
            vectors=[]  # Empty vectors
        )

        embeddings_msg = RowEmbeddings(
            metadata=metadata,
            schema_name='items',
            embeddings=[embedding]
        )

        mock_msg = MagicMock()
        mock_msg.value.return_value = embeddings_msg

        await processor.on_embeddings(mock_msg, MagicMock(), MagicMock())

        # Should not call upsert for empty vectors
        mock_qdrant_instance.upsert.assert_not_called()

    @patch('trustgraph.storage.row_embeddings.qdrant.write.QdrantClient')
    async def test_on_embeddings_drops_unknown_collection(self, mock_qdrant_client):
        """Test that messages for unknown collections are dropped"""
        from trustgraph.storage.row_embeddings.qdrant.write import Processor
        from trustgraph.schema import RowEmbeddings, RowIndexEmbedding

        mock_qdrant_instance = MagicMock()
        mock_qdrant_client.return_value = mock_qdrant_instance

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)
        # No collections registered

        metadata = MagicMock()
        metadata.user = 'unknown_user'
        metadata.collection = 'unknown_collection'
        metadata.id = 'doc-123'

        embedding = RowIndexEmbedding(
            index_name='id',
            index_value=['123'],
            text='123',
            vectors=[[0.1, 0.2]]
        )

        embeddings_msg = RowEmbeddings(
            metadata=metadata,
            schema_name='items',
            embeddings=[embedding]
        )

        mock_msg = MagicMock()
        mock_msg.value.return_value = embeddings_msg

        await processor.on_embeddings(mock_msg, MagicMock(), MagicMock())

        # Should not call upsert for unknown collection
        mock_qdrant_instance.upsert.assert_not_called()

    @patch('trustgraph.storage.row_embeddings.qdrant.write.QdrantClient')
    async def test_delete_collection(self, mock_qdrant_client):
        """Test deleting all collections for a user/collection"""
        from trustgraph.storage.row_embeddings.qdrant.write import Processor

        mock_qdrant_instance = MagicMock()

        # Mock collections list
        mock_coll1 = MagicMock()
        mock_coll1.name = 'rows_test_user_test_collection_schema1_384'
        mock_coll2 = MagicMock()
        mock_coll2.name = 'rows_test_user_test_collection_schema2_384'
        mock_coll3 = MagicMock()
        mock_coll3.name = 'rows_other_user_other_collection_schema_384'

        mock_collections = MagicMock()
        mock_collections.collections = [mock_coll1, mock_coll2, mock_coll3]
        mock_qdrant_instance.get_collections.return_value = mock_collections

        mock_qdrant_client.return_value = mock_qdrant_instance

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)
        processor.created_collections.add('rows_test_user_test_collection_schema1_384')

        await processor.delete_collection('test_user', 'test_collection')

        # Should delete only the matching collections
        assert mock_qdrant_instance.delete_collection.call_count == 2

        # Verify the cached collection was removed
        assert 'rows_test_user_test_collection_schema1_384' not in processor.created_collections

    @patch('trustgraph.storage.row_embeddings.qdrant.write.QdrantClient')
    async def test_delete_collection_schema(self, mock_qdrant_client):
        """Test deleting collections for a specific schema"""
        from trustgraph.storage.row_embeddings.qdrant.write import Processor

        mock_qdrant_instance = MagicMock()

        mock_coll1 = MagicMock()
        mock_coll1.name = 'rows_test_user_test_collection_customers_384'
        mock_coll2 = MagicMock()
        mock_coll2.name = 'rows_test_user_test_collection_orders_384'

        mock_collections = MagicMock()
        mock_collections.collections = [mock_coll1, mock_coll2]
        mock_qdrant_instance.get_collections.return_value = mock_collections

        mock_qdrant_client.return_value = mock_qdrant_instance

        config = {
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = Processor(**config)

        await processor.delete_collection_schema(
            'test_user', 'test_collection', 'customers'
        )

        # Should only delete the customers schema collection
        mock_qdrant_instance.delete_collection.assert_called_once()
        call_args = mock_qdrant_instance.delete_collection.call_args[0]
        assert call_args[0] == 'rows_test_user_test_collection_customers_384'


if __name__ == '__main__':
    pytest.main([__file__])
