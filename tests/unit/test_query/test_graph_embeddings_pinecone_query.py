"""
Tests for Pinecone graph embeddings query service
"""

import pytest
from unittest.mock import MagicMock, patch

# Skip all tests in this module due to missing Pinecone dependency
pytest.skip("Pinecone library missing protoc_gen_openapiv2 dependency", allow_module_level=True)

from trustgraph.query.graph_embeddings.pinecone.service import Processor
from trustgraph.schema import Value


class TestPineconeGraphEmbeddingsQueryProcessor:
    """Test cases for Pinecone graph embeddings query processor"""

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
        with patch('trustgraph.query.graph_embeddings.pinecone.service.Pinecone') as mock_pinecone_class:
            mock_pinecone = MagicMock()
            mock_pinecone_class.return_value = mock_pinecone
            
            processor = Processor(
                taskgroup=MagicMock(),
                id='test-pinecone-ge-query',
                api_key='test-api-key'
            )
            
            return processor

    @patch('trustgraph.query.graph_embeddings.pinecone.service.Pinecone')
    @patch('trustgraph.query.graph_embeddings.pinecone.service.default_api_key', 'env-api-key')
    def test_processor_initialization_with_defaults(self, mock_pinecone_class):
        """Test processor initialization with default parameters"""
        mock_pinecone = MagicMock()
        mock_pinecone_class.return_value = mock_pinecone
        taskgroup_mock = MagicMock()
        
        processor = Processor(taskgroup=taskgroup_mock)
        
        mock_pinecone_class.assert_called_once_with(api_key='env-api-key')
        assert processor.pinecone == mock_pinecone
        assert processor.api_key == 'env-api-key'

    @patch('trustgraph.query.graph_embeddings.pinecone.service.Pinecone')
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

    @patch('trustgraph.query.graph_embeddings.pinecone.service.PineconeGRPC')
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

    @patch('trustgraph.query.graph_embeddings.pinecone.service.default_api_key', 'not-specified')
    def test_processor_initialization_missing_api_key(self):
        """Test processor initialization fails with missing API key"""
        taskgroup_mock = MagicMock()
        
        with pytest.raises(RuntimeError, match="Pinecone API key must be specified"):
            Processor(taskgroup=taskgroup_mock)

    def test_create_value_uri(self, processor):
        """Test create_value method for URI entities"""
        uri_entity = "http://example.org/entity"
        value = processor.create_value(uri_entity)
        
        assert isinstance(value, Value)
        assert value.value == uri_entity
        assert value.is_uri == True

    def test_create_value_https_uri(self, processor):
        """Test create_value method for HTTPS URI entities"""
        uri_entity = "https://example.org/entity"
        value = processor.create_value(uri_entity)
        
        assert isinstance(value, Value)
        assert value.value == uri_entity
        assert value.is_uri == True

    def test_create_value_literal(self, processor):
        """Test create_value method for literal entities"""
        literal_entity = "literal_entity"
        value = processor.create_value(literal_entity)
        
        assert isinstance(value, Value)
        assert value.value == literal_entity
        assert value.is_uri == False

    @pytest.mark.asyncio
    async def test_query_graph_embeddings_single_vector(self, processor):
        """Test querying graph embeddings with a single vector"""
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
            MagicMock(metadata={'entity': 'http://example.org/entity1'}),
            MagicMock(metadata={'entity': 'entity2'}),
            MagicMock(metadata={'entity': 'http://example.org/entity3'})
        ]
        mock_index.query.return_value = mock_results
        
        entities = await processor.query_graph_embeddings(message)
        
        # Verify index was accessed correctly (with dimension suffix)
        expected_index_name = "t-test_user-test_collection-3"  # 3 dimensions
        processor.pinecone.Index.assert_called_once_with(expected_index_name)
        
        # Verify query parameters
        mock_index.query.assert_called_once_with(
            vector=[0.1, 0.2, 0.3],
            top_k=6,  # 2 * limit
            include_values=False,
            include_metadata=True
        )
        
        # Verify results
        assert len(entities) == 3
        assert entities[0].value == 'http://example.org/entity1'
        assert entities[0].is_uri == True
        assert entities[1].value == 'entity2'
        assert entities[1].is_uri == False
        assert entities[2].value == 'http://example.org/entity3'
        assert entities[2].is_uri == True

    @pytest.mark.asyncio
    async def test_query_graph_embeddings_multiple_vectors(self, processor, mock_query_message):
        """Test querying graph embeddings with multiple vectors"""
        # Mock index and query results
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        # First query results
        mock_results1 = MagicMock()
        mock_results1.matches = [
            MagicMock(metadata={'entity': 'entity1'}),
            MagicMock(metadata={'entity': 'entity2'})
        ]
        
        # Second query results
        mock_results2 = MagicMock()
        mock_results2.matches = [
            MagicMock(metadata={'entity': 'entity2'}),  # Duplicate
            MagicMock(metadata={'entity': 'entity3'})
        ]
        
        mock_index.query.side_effect = [mock_results1, mock_results2]
        
        entities = await processor.query_graph_embeddings(mock_query_message)
        
        # Verify both queries were made
        assert mock_index.query.call_count == 2
        
        # Verify deduplication occurred
        entity_values = [e.value for e in entities]
        assert len(entity_values) == 3
        assert 'entity1' in entity_values
        assert 'entity2' in entity_values
        assert 'entity3' in entity_values

    @pytest.mark.asyncio
    async def test_query_graph_embeddings_limit_handling(self, processor):
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
            MagicMock(metadata={'entity': f'entity{i}'}) for i in range(10)
        ]
        mock_index.query.return_value = mock_results
        
        entities = await processor.query_graph_embeddings(message)
        
        # Verify limit is respected
        assert len(entities) == 2

    @pytest.mark.asyncio
    async def test_query_graph_embeddings_zero_limit(self, processor):
        """Test querying with zero limit returns empty results"""
        message = MagicMock()
        message.vectors = [[0.1, 0.2, 0.3]]
        message.limit = 0
        message.user = 'test_user'
        message.collection = 'test_collection'
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        entities = await processor.query_graph_embeddings(message)
        
        # Verify no query was made and empty result returned
        mock_index.query.assert_not_called()
        assert entities == []

    @pytest.mark.asyncio
    async def test_query_graph_embeddings_negative_limit(self, processor):
        """Test querying with negative limit returns empty results"""
        message = MagicMock()
        message.vectors = [[0.1, 0.2, 0.3]]
        message.limit = -1
        message.user = 'test_user'
        message.collection = 'test_collection'
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        entities = await processor.query_graph_embeddings(message)
        
        # Verify no query was made and empty result returned
        mock_index.query.assert_not_called()
        assert entities == []

    @pytest.mark.asyncio
    async def test_query_graph_embeddings_different_vector_dimensions(self, processor):
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
        mock_results_2d.matches = [MagicMock(metadata={'entity': 'entity_2d'})]

        mock_results_4d = MagicMock()
        mock_results_4d.matches = [MagicMock(metadata={'entity': 'entity_4d'})]

        mock_index.query.side_effect = [mock_results_2d, mock_results_4d]

        entities = await processor.query_graph_embeddings(message)

        # Verify different indexes used for different dimensions
        assert processor.pinecone.Index.call_count == 2
        index_calls = processor.pinecone.Index.call_args_list
        index_names = [call[0][0] for call in index_calls]
        assert "t-test_user-test_collection-2" in index_names  # 2D vector
        assert "t-test_user-test_collection-4" in index_names  # 4D vector

        # Verify both queries were made
        assert mock_index.query.call_count == 2

        # Verify results from both dimensions
        entity_values = [e.value for e in entities]
        assert 'entity_2d' in entity_values
        assert 'entity_4d' in entity_values

    @pytest.mark.asyncio
    async def test_query_graph_embeddings_empty_vectors_list(self, processor):
        """Test querying with empty vectors list"""
        message = MagicMock()
        message.vectors = []
        message.limit = 5
        message.user = 'test_user'
        message.collection = 'test_collection'
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        entities = await processor.query_graph_embeddings(message)
        
        # Verify no queries were made and empty result returned
        processor.pinecone.Index.assert_not_called()
        mock_index.query.assert_not_called()
        assert entities == []

    @pytest.mark.asyncio
    async def test_query_graph_embeddings_no_results(self, processor):
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
        
        entities = await processor.query_graph_embeddings(message)
        
        # Verify empty results
        assert entities == []

    @pytest.mark.asyncio
    async def test_query_graph_embeddings_deduplication_across_vectors(self, processor):
        """Test that deduplication works correctly across multiple vector queries"""
        message = MagicMock()
        message.vectors = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6]
        ]
        message.limit = 3
        message.user = 'test_user'
        message.collection = 'test_collection'
        
        mock_index = MagicMock()
        processor.pinecone.Index.return_value = mock_index
        
        # Both queries return overlapping results
        mock_results1 = MagicMock()
        mock_results1.matches = [
            MagicMock(metadata={'entity': 'entity1'}),
            MagicMock(metadata={'entity': 'entity2'}),
            MagicMock(metadata={'entity': 'entity3'}),
            MagicMock(metadata={'entity': 'entity4'})
        ]
        
        mock_results2 = MagicMock()
        mock_results2.matches = [
            MagicMock(metadata={'entity': 'entity2'}),  # Duplicate
            MagicMock(metadata={'entity': 'entity3'}),  # Duplicate
            MagicMock(metadata={'entity': 'entity5'})
        ]
        
        mock_index.query.side_effect = [mock_results1, mock_results2]
        
        entities = await processor.query_graph_embeddings(message)
        
        # Should get exactly 3 unique entities (respecting limit)
        assert len(entities) == 3
        entity_values = [e.value for e in entities]
        assert len(set(entity_values)) == 3  # All unique

    @pytest.mark.asyncio
    async def test_query_graph_embeddings_early_termination_on_limit(self, processor):
        """Test that querying stops early when limit is reached"""
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
        
        # First query returns enough results to meet limit
        mock_results1 = MagicMock()
        mock_results1.matches = [
            MagicMock(metadata={'entity': 'entity1'}),
            MagicMock(metadata={'entity': 'entity2'}),
            MagicMock(metadata={'entity': 'entity3'})
        ]
        mock_index.query.return_value = mock_results1
        
        entities = await processor.query_graph_embeddings(message)
        
        # Should only make one query since limit was reached
        mock_index.query.assert_called_once()
        assert len(entities) == 2

    @pytest.mark.asyncio
    async def test_query_graph_embeddings_exception_handling(self, processor):
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
            await processor.query_graph_embeddings(message)

    def test_add_args_method(self):
        """Test that add_args properly configures argument parser"""
        from argparse import ArgumentParser
        from unittest.mock import patch
        
        parser = ArgumentParser()
        
        # Mock the parent class add_args method
        with patch('trustgraph.query.graph_embeddings.pinecone.service.GraphEmbeddingsQueryService.add_args') as mock_parent_add_args:
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
        
        with patch('trustgraph.query.graph_embeddings.pinecone.service.GraphEmbeddingsQueryService.add_args'):
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
        
        with patch('trustgraph.query.graph_embeddings.pinecone.service.GraphEmbeddingsQueryService.add_args'):
            Processor.add_args(parser)
        
        # Test parsing with short form
        args = parser.parse_args([
            '-a', 'short-api-key',
            '-u', 'https://short-host.pinecone.io'
        ])
        
        assert args.api_key == 'short-api-key'
        assert args.url == 'https://short-host.pinecone.io'

    @patch('trustgraph.query.graph_embeddings.pinecone.service.Processor.launch')
    def test_run_function(self, mock_launch):
        """Test the run function calls Processor.launch with correct parameters"""
        from trustgraph.query.graph_embeddings.pinecone.service import run, default_ident
        
        run()
        
        mock_launch.assert_called_once_with(
            default_ident,
            "\nGraph embeddings query service.  Input is vector, output is list of\nentities.  Pinecone implementation.\n"
        )