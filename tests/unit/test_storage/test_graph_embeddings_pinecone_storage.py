"""
Tests for Pinecone graph embeddings storage service
"""

import pytest
from unittest.mock import MagicMock, patch
import uuid

from trustgraph.storage.graph_embeddings.pinecone.write import Processor
from trustgraph.schema import EntityEmbeddings, Value


class TestPineconeGraphEmbeddingsStorageProcessor:
    """Test cases for Pinecone graph embeddings storage processor"""

    @pytest.fixture
    def mock_message(self):
        """Create a mock message for testing"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        # Create test entity embeddings
        entity1 = EntityEmbeddings(
            entity=Value(value="http://example.org/entity1", is_uri=True),
            vectors=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        )
        entity2 = EntityEmbeddings(
            entity=Value(value="entity2", is_uri=False),
            vectors=[[0.7, 0.8, 0.9]]
        )
        message.entities = [entity1, entity2]
        
        return message

    @pytest.fixture
    def processor(self):
        """Create a processor instance for testing"""
        with patch('trustgraph.storage.graph_embeddings.pinecone.write.Pinecone') as mock_pinecone_class:
            mock_pinecone = MagicMock()
            mock_pinecone_class.return_value = mock_pinecone
            
            processor = Processor(
                taskgroup=MagicMock(),
                id='test-pinecone-ge-storage',
                api_key='test-api-key'
            )
            
            return processor

    @patch('trustgraph.storage.graph_embeddings.pinecone.write.Pinecone')
    @patch('trustgraph.storage.graph_embeddings.pinecone.write.default_api_key', 'env-api-key')
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

    @patch('trustgraph.storage.graph_embeddings.pinecone.write.Pinecone')
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

    @patch('trustgraph.storage.graph_embeddings.pinecone.write.PineconeGRPC')
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

    @patch('trustgraph.storage.graph_embeddings.pinecone.write.default_api_key', 'not-specified')
    def test_processor_initialization_missing_api_key(self):
        """Test processor initialization fails with missing API key"""
        taskgroup_mock = MagicMock()
        
        with pytest.raises(RuntimeError, match="Pinecone API key must be specified"):
            Processor(taskgroup=taskgroup_mock)

    @pytest.mark.asyncio
    async def test_store_graph_embeddings_single_entity(self, processor):
        """Test storing graph embeddings for a single entity"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        entity = EntityEmbeddings(
            entity=Value(value="http://example.org/entity1", is_uri=True),
            vectors=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        )
        message.entities = [entity]
        
        # Mock index operations
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        processor.pinecone.has_index.return_value = True
        
        with patch('uuid.uuid4', side_effect=['id1', 'id2']):
            await processor.store_graph_embeddings(message)
        
        # Verify index name and operations
        expected_index_name = "t-test_user-test_collection-3"
        processor.pinecone.Index.assert_called_with(expected_index_name)
        
        # Verify upsert was called for each vector
        assert mock_index.upsert.call_count == 2
        
        # Check first vector upsert
        first_call = mock_index.upsert.call_args_list[0]
        first_vectors = first_call[1]['vectors']
        assert len(first_vectors) == 1
        assert first_vectors[0]['id'] == 'id1'
        assert first_vectors[0]['values'] == [0.1, 0.2, 0.3]
        assert first_vectors[0]['metadata']['entity'] == "http://example.org/entity1"
        
        # Check second vector upsert
        second_call = mock_index.upsert.call_args_list[1]
        second_vectors = second_call[1]['vectors']
        assert len(second_vectors) == 1
        assert second_vectors[0]['id'] == 'id2'
        assert second_vectors[0]['values'] == [0.4, 0.5, 0.6]
        assert second_vectors[0]['metadata']['entity'] == "http://example.org/entity1"

    @pytest.mark.asyncio
    async def test_store_graph_embeddings_multiple_entities(self, processor, mock_message):
        """Test storing graph embeddings for multiple entities"""
        # Mock index operations
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        processor.pinecone.has_index.return_value = True
        
        with patch('uuid.uuid4', side_effect=['id1', 'id2', 'id3']):
            await processor.store_graph_embeddings(mock_message)
        
        # Verify upsert was called for each vector (3 total)
        assert mock_index.upsert.call_count == 3
        
        # Verify entity values in metadata
        calls = mock_index.upsert.call_args_list
        assert calls[0][1]['vectors'][0]['metadata']['entity'] == "http://example.org/entity1"
        assert calls[1][1]['vectors'][0]['metadata']['entity'] == "http://example.org/entity1"
        assert calls[2][1]['vectors'][0]['metadata']['entity'] == "entity2"

    @pytest.mark.asyncio
    async def test_store_graph_embeddings_index_creation(self, processor):
        """Test automatic index creation when index doesn't exist"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        entity = EntityEmbeddings(
            entity=Value(value="test_entity", is_uri=False),
            vectors=[[0.1, 0.2, 0.3]]
        )
        message.entities = [entity]
        
        # Mock index doesn't exist initially
        processor.pinecone.has_index.return_value = False
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        # Mock index creation
        processor.pinecone.describe_index.return_value.status = {"ready": True}
        
        with patch('uuid.uuid4', return_value='test-id'):
            await processor.store_graph_embeddings(message)
        
        # Verify index creation was called
        expected_index_name = "t-test_user-test_collection-3"
        processor.pinecone.create_index.assert_called_once()
        create_call = processor.pinecone.create_index.call_args
        assert create_call[1]['name'] == expected_index_name
        assert create_call[1]['dimension'] == 3
        assert create_call[1]['metric'] == "cosine"

    @pytest.mark.asyncio
    async def test_store_graph_embeddings_empty_entity_value(self, processor):
        """Test storing graph embeddings with empty entity value (should be skipped)"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        entity = EntityEmbeddings(
            entity=Value(value="", is_uri=False),
            vectors=[[0.1, 0.2, 0.3]]
        )
        message.entities = [entity]
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        await processor.store_graph_embeddings(message)
        
        # Verify no upsert was called for empty entity
        mock_index.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_graph_embeddings_none_entity_value(self, processor):
        """Test storing graph embeddings with None entity value (should be skipped)"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        entity = EntityEmbeddings(
            entity=Value(value=None, is_uri=False),
            vectors=[[0.1, 0.2, 0.3]]
        )
        message.entities = [entity]
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        await processor.store_graph_embeddings(message)
        
        # Verify no upsert was called for None entity
        mock_index.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_graph_embeddings_different_vector_dimensions(self, processor):
        """Test storing graph embeddings with different vector dimensions"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        entity = EntityEmbeddings(
            entity=Value(value="test_entity", is_uri=False),
            vectors=[
                [0.1, 0.2],  # 2D vector
                [0.3, 0.4, 0.5, 0.6],  # 4D vector
                [0.7, 0.8, 0.9]  # 3D vector
            ]
        )
        message.entities = [entity]
        
        mock_index_2d = MagicMock()
        mock_index_4d = MagicMock()
        mock_index_3d = MagicMock()
        
        def mock_index_side_effect(name):
            if name.endswith("-2"):
                return mock_index_2d
            elif name.endswith("-4"):
                return mock_index_4d
            elif name.endswith("-3"):
                return mock_index_3d
        
        processor.pinecone.Index.side_effect = mock_index_side_effect
        processor.pinecone.has_index.return_value = True
        
        with patch('uuid.uuid4', side_effect=['id1', 'id2', 'id3']):
            await processor.store_graph_embeddings(message)
        
        # Verify different indexes were used for different dimensions
        assert processor.pinecone.Index.call_count == 3
        mock_index_2d.upsert.assert_called_once()
        mock_index_4d.upsert.assert_called_once()
        mock_index_3d.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_graph_embeddings_empty_entities_list(self, processor):
        """Test storing graph embeddings with empty entities list"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        message.entities = []
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        await processor.store_graph_embeddings(message)
        
        # Verify no operations were performed
        processor.pinecone.Index.assert_not_called()
        mock_index.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_graph_embeddings_entity_with_no_vectors(self, processor):
        """Test storing graph embeddings for entity with no vectors"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        entity = EntityEmbeddings(
            entity=Value(value="test_entity", is_uri=False),
            vectors=[]
        )
        message.entities = [entity]
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        await processor.store_graph_embeddings(message)
        
        # Verify no upsert was called (no vectors to insert)
        mock_index.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_graph_embeddings_index_creation_failure(self, processor):
        """Test handling of index creation failure"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        entity = EntityEmbeddings(
            entity=Value(value="test_entity", is_uri=False),
            vectors=[[0.1, 0.2, 0.3]]
        )
        message.entities = [entity]
        
        # Mock index doesn't exist and creation fails
        processor.pinecone.has_index.return_value = False
        processor.pinecone.create_index.side_effect = Exception("Index creation failed")
        
        with pytest.raises(Exception, match="Index creation failed"):
            await processor.store_graph_embeddings(message)

    @pytest.mark.asyncio
    async def test_store_graph_embeddings_index_creation_timeout(self, processor):
        """Test handling of index creation timeout"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        entity = EntityEmbeddings(
            entity=Value(value="test_entity", is_uri=False),
            vectors=[[0.1, 0.2, 0.3]]
        )
        message.entities = [entity]
        
        # Mock index doesn't exist and never becomes ready
        processor.pinecone.has_index.return_value = False
        processor.pinecone.describe_index.return_value.status = {"ready": False}
        
        with patch('time.sleep'):  # Speed up the test
            with pytest.raises(RuntimeError, match="Gave up waiting for index creation"):
                await processor.store_graph_embeddings(message)

    def test_add_args_method(self):
        """Test that add_args properly configures argument parser"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        # Mock the parent class add_args method
        with patch('trustgraph.storage.graph_embeddings.pinecone.write.GraphEmbeddingsStoreService.add_args') as mock_parent_add_args:
            Processor.add_args(parser)
            
            # Verify parent add_args was called
            mock_parent_add_args.assert_called_once()
        
        # Verify our specific arguments were added by parsing empty args
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
        
        with patch('trustgraph.storage.graph_embeddings.pinecone.write.GraphEmbeddingsStoreService.add_args'):
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
        
        with patch('trustgraph.storage.graph_embeddings.pinecone.write.GraphEmbeddingsStoreService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with short form
        args = parser.parse_args([
            '-a', 'short-api-key',
            '-u', 'https://short-host.pinecone.io'
        ])
        
        assert args.api_key == 'short-api-key'
        assert args.url == 'https://short-host.pinecone.io'

    @patch('trustgraph.storage.graph_embeddings.pinecone.write.Processor.launch')
    def test_run_function(self, mock_launch):
        """Test the run function calls Processor.launch with correct parameters"""
        from trustgraph.storage.graph_embeddings.pinecone.write import run, default_ident
        
        run()
        
        mock_launch.assert_called_once_with(
            default_ident,
            "\nAccepts entity/vector pairs and writes them to a Pinecone store.\n"
        )