"""
Tests for Milvus graph embeddings storage service
"""

import pytest
from unittest.mock import MagicMock, patch

from trustgraph.storage.graph_embeddings.milvus.write import Processor
from trustgraph.schema import Term, EntityEmbeddings, IRI, LITERAL


class TestMilvusGraphEmbeddingsStorageProcessor:
    """Test cases for Milvus graph embeddings storage processor"""

    @pytest.fixture
    def mock_message(self):
        """Create a mock message for testing"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        # Create test entities with embeddings
        entity1 = EntityEmbeddings(
            entity=Term(type=IRI, iri='http://example.com/entity1'),
            vectors=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        )
        entity2 = EntityEmbeddings(
            entity=Term(type=LITERAL, value='literal entity'),
            vectors=[[0.7, 0.8, 0.9]]
        )
        message.entities = [entity1, entity2]
        
        return message

    @pytest.fixture
    def processor(self):
        """Create a processor instance for testing"""
        with patch('trustgraph.storage.graph_embeddings.milvus.write.EntityVectors') as mock_entity_vectors:
            mock_vecstore = MagicMock()
            mock_entity_vectors.return_value = mock_vecstore
            
            processor = Processor(
                taskgroup=MagicMock(),
                id='test-milvus-ge-storage',
                store_uri='http://localhost:19530'
            )
            
            return processor

    @patch('trustgraph.storage.graph_embeddings.milvus.write.EntityVectors')
    def test_processor_initialization_with_defaults(self, mock_entity_vectors):
        """Test processor initialization with default parameters"""
        taskgroup_mock = MagicMock()
        mock_vecstore = MagicMock()
        mock_entity_vectors.return_value = mock_vecstore
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        mock_entity_vectors.assert_called_once_with('http://localhost:19530')
        assert processor.vecstore == mock_vecstore

    @patch('trustgraph.storage.graph_embeddings.milvus.write.EntityVectors')
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

    @pytest.mark.asyncio
    async def test_store_graph_embeddings_single_entity(self, processor):
        """Test storing graph embeddings for a single entity"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        entity = EntityEmbeddings(
            entity=Term(type=IRI, iri='http://example.com/entity'),
            vectors=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        )
        message.entities = [entity]
        
        await processor.store_graph_embeddings(message)
        
        # Verify insert was called for each vector with user/collection parameters
        expected_calls = [
            ([0.1, 0.2, 0.3], 'http://example.com/entity', 'test_user', 'test_collection'),
            ([0.4, 0.5, 0.6], 'http://example.com/entity', 'test_user', 'test_collection'),
        ]
        
        assert processor.vecstore.insert.call_count == 2
        for i, (expected_vec, expected_entity, expected_user, expected_collection) in enumerate(expected_calls):
            actual_call = processor.vecstore.insert.call_args_list[i]
            assert actual_call[0][0] == expected_vec
            assert actual_call[0][1] == expected_entity
            assert actual_call[0][2] == expected_user
            assert actual_call[0][3] == expected_collection

    @pytest.mark.asyncio
    async def test_store_graph_embeddings_multiple_entities(self, processor, mock_message):
        """Test storing graph embeddings for multiple entities"""
        await processor.store_graph_embeddings(mock_message)
        
        # Verify insert was called for each vector of each entity with user/collection parameters
        expected_calls = [
            # Entity 1 vectors
            ([0.1, 0.2, 0.3], 'http://example.com/entity1', 'test_user', 'test_collection'),
            ([0.4, 0.5, 0.6], 'http://example.com/entity1', 'test_user', 'test_collection'),
            # Entity 2 vectors
            ([0.7, 0.8, 0.9], 'literal entity', 'test_user', 'test_collection'),
        ]
        
        assert processor.vecstore.insert.call_count == 3
        for i, (expected_vec, expected_entity, expected_user, expected_collection) in enumerate(expected_calls):
            actual_call = processor.vecstore.insert.call_args_list[i]
            assert actual_call[0][0] == expected_vec
            assert actual_call[0][1] == expected_entity
            assert actual_call[0][2] == expected_user
            assert actual_call[0][3] == expected_collection

    @pytest.mark.asyncio
    async def test_store_graph_embeddings_empty_entity_value(self, processor):
        """Test storing graph embeddings with empty entity value (should be skipped)"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        entity = EntityEmbeddings(
            entity=Value(value='', is_uri=False),
            vectors=[[0.1, 0.2, 0.3]]
        )
        message.entities = [entity]
        
        await processor.store_graph_embeddings(message)
        
        # Verify no insert was called for empty entity
        processor.vecstore.insert.assert_not_called()

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
        
        await processor.store_graph_embeddings(message)
        
        # Verify no insert was called for None entity
        processor.vecstore.insert.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_graph_embeddings_mixed_valid_invalid_entities(self, processor):
        """Test storing graph embeddings with mix of valid and invalid entities"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        valid_entity = EntityEmbeddings(
            entity=Value(value='http://example.com/valid', is_uri=True),
            vectors=[[0.1, 0.2, 0.3]]
        )
        empty_entity = EntityEmbeddings(
            entity=Value(value='', is_uri=False),
            vectors=[[0.4, 0.5, 0.6]]
        )
        none_entity = EntityEmbeddings(
            entity=Value(value=None, is_uri=False),
            vectors=[[0.7, 0.8, 0.9]]
        )
        message.entities = [valid_entity, empty_entity, none_entity]
        
        await processor.store_graph_embeddings(message)
        
        # Verify only valid entity was inserted with user/collection parameters
        processor.vecstore.insert.assert_called_once_with(
            [0.1, 0.2, 0.3], 'http://example.com/valid', 'test_user', 'test_collection'
        )

    @pytest.mark.asyncio
    async def test_store_graph_embeddings_empty_entities_list(self, processor):
        """Test storing graph embeddings with empty entities list"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        message.entities = []
        
        await processor.store_graph_embeddings(message)
        
        # Verify no insert was called
        processor.vecstore.insert.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_graph_embeddings_entity_with_no_vectors(self, processor):
        """Test storing graph embeddings for entity with no vectors"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        entity = EntityEmbeddings(
            entity=Value(value='http://example.com/entity', is_uri=True),
            vectors=[]
        )
        message.entities = [entity]
        
        await processor.store_graph_embeddings(message)
        
        # Verify no insert was called (no vectors to insert)
        processor.vecstore.insert.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_graph_embeddings_different_vector_dimensions(self, processor):
        """Test storing graph embeddings with different vector dimensions"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        entity = EntityEmbeddings(
            entity=Value(value='http://example.com/entity', is_uri=True),
            vectors=[
                [0.1, 0.2],  # 2D vector
                [0.3, 0.4, 0.5, 0.6],  # 4D vector
                [0.7, 0.8, 0.9]  # 3D vector
            ]
        )
        message.entities = [entity]
        
        await processor.store_graph_embeddings(message)
        
        # Verify all vectors were inserted regardless of dimension
        expected_calls = [
            ([0.1, 0.2], 'http://example.com/entity'),
            ([0.3, 0.4, 0.5, 0.6], 'http://example.com/entity'),
            ([0.7, 0.8, 0.9], 'http://example.com/entity'),
        ]
        
        assert processor.vecstore.insert.call_count == 3
        for i, (expected_vec, expected_entity) in enumerate(expected_calls):
            actual_call = processor.vecstore.insert.call_args_list[i]
            assert actual_call[0][0] == expected_vec
            assert actual_call[0][1] == expected_entity

    @pytest.mark.asyncio
    async def test_store_graph_embeddings_uri_and_literal_entities(self, processor):
        """Test storing graph embeddings for both URI and literal entities"""
        message = MagicMock()
        message.metadata = MagicMock()
        message.metadata.user = 'test_user'
        message.metadata.collection = 'test_collection'
        
        uri_entity = EntityEmbeddings(
            entity=Value(value='http://example.com/uri_entity', is_uri=True),
            vectors=[[0.1, 0.2, 0.3]]
        )
        literal_entity = EntityEmbeddings(
            entity=Value(value='literal entity text', is_uri=False),
            vectors=[[0.4, 0.5, 0.6]]
        )
        message.entities = [uri_entity, literal_entity]
        
        await processor.store_graph_embeddings(message)
        
        # Verify both entities were inserted
        expected_calls = [
            ([0.1, 0.2, 0.3], 'http://example.com/uri_entity'),
            ([0.4, 0.5, 0.6], 'literal entity text'),
        ]
        
        assert processor.vecstore.insert.call_count == 2
        for i, (expected_vec, expected_entity) in enumerate(expected_calls):
            actual_call = processor.vecstore.insert.call_args_list[i]
            assert actual_call[0][0] == expected_vec
            assert actual_call[0][1] == expected_entity

    def test_add_args_method(self):
        """Test that add_args properly configures argument parser"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        # Mock the parent class add_args method
        with patch('trustgraph.storage.graph_embeddings.milvus.write.GraphEmbeddingsStoreService.add_args') as mock_parent_add_args:
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
        
        with patch('trustgraph.storage.graph_embeddings.milvus.write.GraphEmbeddingsStoreService.add_args'):
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
        
        with patch('trustgraph.storage.graph_embeddings.milvus.write.GraphEmbeddingsStoreService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with short form
        args = parser.parse_args(['-t', 'http://short-milvus:19530'])
        
        assert args.store_uri == 'http://short-milvus:19530'

    @patch('trustgraph.storage.graph_embeddings.milvus.write.Processor.launch')
    def test_run_function(self, mock_launch):
        """Test the run function calls Processor.launch with correct parameters"""
        from trustgraph.storage.graph_embeddings.milvus.write import run, default_ident
        
        run()
        
        mock_launch.assert_called_once_with(
            default_ident,
            "\nAccepts entity/vector pairs and writes them to a Milvus store.\n"
        )