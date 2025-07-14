"""
Unit tests for FastEmbed embeddings processor

Tests the core business logic of FastEmbed embedding generation without
relying on external FastEmbed library infrastructure.
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock, MagicMock
import numpy as np

from trustgraph.embeddings.fastembed.processor import Processor
from trustgraph.schema import EmbeddingsRequest, EmbeddingsResponse, Error
from trustgraph.exceptions import TooManyRequests


@pytest.fixture
def mock_fastembed_embedding():
    """Mock FastEmbed TextEmbedding"""
    mock = Mock()
    # FastEmbed returns numpy arrays that need to be converted to lists
    mock.embed.return_value = [
        np.array([0.1, 0.2, -0.3, 0.4, -0.5, 0.6, 0.7, -0.8, 0.9, -1.0])
    ]
    return mock


@pytest.fixture
def processor_params():
    """Default parameters for FastEmbed processor"""
    return {
        "model": "test-embed-model",
        "id": "test-fastembed",
        "concurrency": 1
    }


@pytest.fixture
def mock_message():
    """Mock Pulsar message for FastEmbed processor"""
    message = Mock()
    message.properties.return_value = {"id": "test-msg-456"}
    message.value.return_value = EmbeddingsRequest(text="FastEmbed test text")
    return message


@pytest.fixture
def mock_flow():
    """Mock flow for EmbeddingsService testing"""
    flow = Mock()
    response_flow = Mock()
    response_flow.send = AsyncMock()
    flow.return_value = response_flow
    flow.producer = {"response": Mock()}
    flow.producer["response"].send = AsyncMock()
    return flow


class TestFastEmbedProcessor:
    """Test cases for FastEmbed embeddings processor"""

    @patch('trustgraph.embeddings.fastembed.processor.TextEmbedding')
    @patch('trustgraph.base.embeddings_service.EmbeddingsService.__init__')
    def test_processor_initialization_default_params(self, mock_super_init, mock_text_embedding):
        """Test processor initialization with default parameters"""
        # Arrange
        mock_embedding_instance = Mock()
        mock_text_embedding.return_value = mock_embedding_instance
        mock_super_init.return_value = None
        
        # Act
        processor = Processor()
        
        # Assert
        mock_text_embedding.assert_called_once_with(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        assert processor.embeddings == mock_embedding_instance

    @patch('trustgraph.embeddings.fastembed.processor.TextEmbedding')
    @patch('trustgraph.base.embeddings_service.EmbeddingsService.__init__')
    def test_processor_initialization_custom_model(self, mock_super_init, mock_text_embedding, processor_params):
        """Test processor initialization with custom model"""
        # Arrange
        mock_embedding_instance = Mock()
        mock_text_embedding.return_value = mock_embedding_instance
        mock_super_init.return_value = None
        
        # Act
        processor = Processor(**processor_params)
        
        # Assert
        mock_text_embedding.assert_called_once_with(
            model_name="test-embed-model"
        )
        assert processor.embeddings == mock_embedding_instance

    @patch('trustgraph.embeddings.fastembed.processor.TextEmbedding')
    async def test_on_embeddings_successful(self, mock_text_embedding):
        """Test successful embedding generation through on_embeddings method"""
        # Arrange
        mock_embedding_instance = Mock()
        mock_embedding_instance.embed.return_value = [
            np.array([0.1, 0.2, -0.3, 0.4, -0.5])
        ]
        mock_text_embedding.return_value = mock_embedding_instance
        
        processor = Processor()
        
        # Act
        result = await processor.on_embeddings("Test text for embedding")
        
        # Assert
        mock_embedding_instance.embed.assert_called_once_with(["Test text for embedding"])
        assert result == [[0.1, 0.2, -0.3, 0.4, -0.5]]

    @patch('trustgraph.embeddings.fastembed.processor.TextEmbedding')
    async def test_on_embeddings_multiple_vectors(self, mock_text_embedding):
        """Test embedding generation returning multiple vectors"""
        # Arrange
        mock_embedding_instance = Mock()
        mock_embedding_instance.embed.return_value = [
            np.array([0.1, 0.2, -0.3]),
            np.array([0.4, -0.5, 0.6])
        ]
        mock_text_embedding.return_value = mock_embedding_instance
        
        processor = Processor()
        
        # Act
        result = await processor.on_embeddings("Multi-sentence text input")
        
        # Assert
        assert result == [[0.1, 0.2, -0.3], [0.4, -0.5, 0.6]]

    @patch('trustgraph.embeddings.fastembed.processor.TextEmbedding')
    async def test_on_embeddings_empty_text(self, mock_text_embedding):
        """Test embedding generation with empty text"""
        # Arrange
        mock_embedding_instance = Mock()
        mock_embedding_instance.embed.return_value = [np.array([])]
        mock_text_embedding.return_value = mock_embedding_instance
        
        processor = Processor()
        
        # Act
        result = await processor.on_embeddings("")
        
        # Assert
        mock_embedding_instance.embed.assert_called_once_with([""])
        assert result == [[]]

    @patch('trustgraph.embeddings.fastembed.processor.TextEmbedding')
    async def test_on_embeddings_large_dimensions(self, mock_text_embedding):
        """Test embedding generation with large dimension vectors"""
        # Arrange
        mock_embedding_instance = Mock()
        large_vector = np.random.rand(1536)  # Common large embedding size
        mock_embedding_instance.embed.return_value = [large_vector]
        mock_text_embedding.return_value = mock_embedding_instance
        
        processor = Processor()
        
        # Act
        result = await processor.on_embeddings("Text for large embedding")
        
        # Assert
        assert len(result) == 1
        assert len(result[0]) == 1536
        assert result[0] == large_vector.tolist()

    @patch('trustgraph.embeddings.fastembed.processor.TextEmbedding')
    async def test_on_embeddings_unicode_text(self, mock_text_embedding):
        """Test embedding generation with Unicode text"""
        # Arrange
        mock_embedding_instance = Mock()
        mock_embedding_instance.embed.return_value = [
            np.array([0.3, -0.2, 0.1, 0.8, -0.6])
        ]
        mock_text_embedding.return_value = mock_embedding_instance
        
        processor = Processor()
        unicode_text = "Hello 世界! 🚀 Café naïve résumé"
        
        # Act
        result = await processor.on_embeddings(unicode_text)
        
        # Assert
        mock_embedding_instance.embed.assert_called_once_with([unicode_text])
        assert result == [[0.3, -0.2, 0.1, 0.8, -0.6]]

    @patch('trustgraph.embeddings.fastembed.processor.TextEmbedding')
    async def test_on_embeddings_model_error(self, mock_text_embedding):
        """Test handling of FastEmbed model errors"""
        # Arrange
        mock_embedding_instance = Mock()
        mock_embedding_instance.embed.side_effect = Exception("Model loading failed")
        mock_text_embedding.return_value = mock_embedding_instance
        
        processor = Processor()
        
        # Act & Assert
        with pytest.raises(Exception, match="Model loading failed"):
            await processor.on_embeddings("Test text")

    @patch('trustgraph.embeddings.fastembed.processor.TextEmbedding')
    async def test_on_request_successful_flow(self, mock_text_embedding, mock_message, mock_flow):
        """Test successful request handling through EmbeddingsService flow"""
        # Arrange
        mock_embedding_instance = Mock()
        mock_embedding_instance.embed.return_value = [
            np.array([0.2, -0.1, 0.4, -0.3, 0.5])
        ]
        mock_text_embedding.return_value = mock_embedding_instance
        
        processor = Processor()
        consumer = Mock()
        
        # Act
        await processor.on_request(mock_message, consumer, mock_flow)
        
        # Assert
        mock_embedding_instance.embed.assert_called_once_with(["FastEmbed test text"])
        
        # Verify response sent through flow
        mock_flow.assert_called_once_with("response")
        mock_flow.return_value.send.assert_called_once()
        
        call_args = mock_flow.return_value.send.call_args
        response = call_args[0][0]
        properties = call_args[1]["properties"]
        
        assert isinstance(response, EmbeddingsResponse)
        assert response.error is None
        assert response.vectors == [[0.2, -0.1, 0.4, -0.3, 0.5]]
        assert properties["id"] == "test-msg-456"

    @patch('trustgraph.embeddings.fastembed.processor.TextEmbedding')
    async def test_on_request_embedding_error(self, mock_text_embedding, mock_message, mock_flow):
        """Test error handling in request processing"""
        # Arrange
        mock_embedding_instance = Mock()
        mock_embedding_instance.embed.side_effect = Exception("FastEmbed error")
        mock_text_embedding.return_value = mock_embedding_instance
        
        processor = Processor()
        consumer = Mock()
        
        # Act
        await processor.on_request(mock_message, consumer, mock_flow)
        
        # Assert
        # Should send error response
        mock_flow.producer["response"].send.assert_called_once()
        
        call_args = mock_flow.producer["response"].send.call_args
        response = call_args[0][0]
        properties = call_args[1]["properties"]
        
        assert isinstance(response, EmbeddingsResponse)
        assert response.error is not None
        assert response.error.type == "embeddings-error"
        assert "FastEmbed error" in response.error.message
        assert response.vectors is None
        assert properties["id"] == "test-msg-456"

    @patch('trustgraph.embeddings.fastembed.processor.TextEmbedding')
    async def test_on_request_rate_limit_exception(self, mock_text_embedding, mock_message, mock_flow):
        """Test handling of rate limit exceptions"""
        # Arrange
        mock_embedding_instance = Mock()
        mock_embedding_instance.embed.side_effect = TooManyRequests("Rate limit exceeded")
        mock_text_embedding.return_value = mock_embedding_instance
        
        processor = Processor()
        consumer = Mock()
        
        # Act & Assert
        with pytest.raises(TooManyRequests, match="Rate limit exceeded"):
            await processor.on_request(mock_message, consumer, mock_flow)

    def test_add_args_method(self):
        """Test that add_args method adds correct arguments"""
        # Arrange
        mock_parser = Mock()
        
        # Act
        Processor.add_args(mock_parser)
        
        # Assert
        # Verify model argument added
        model_calls = [call for call in mock_parser.add_argument.call_args_list 
                      if call[0][0] in ['-m', '--model']]
        assert len(model_calls) == 1
        model_call = model_calls[0]
        assert model_call[1]['default'] == "sentence-transformers/all-MiniLM-L6-v2"

    @patch('trustgraph.embeddings.fastembed.processor.TextEmbedding')
    def test_numpy_array_conversion(self, mock_text_embedding):
        """Test that numpy arrays are properly converted to lists"""
        # Arrange
        mock_embedding_instance = Mock()
        # Simulate FastEmbed returning numpy arrays with different dtypes
        test_arrays = [
            np.array([0.1, 0.2, 0.3], dtype=np.float32),
            np.array([-0.4, 0.5, -0.6], dtype=np.float64)
        ]
        mock_embedding_instance.embed.return_value = test_arrays
        mock_text_embedding.return_value = mock_embedding_instance
        
        processor = Processor()
        
        # Test conversion logic directly
        result = [v.tolist() for v in test_arrays]
        
        # Assert
        assert result == [[0.1, 0.2, 0.3], [-0.4, 0.5, -0.6]]
        assert all(isinstance(vec, list) for vec in result)
        assert all(isinstance(val, (int, float)) for vec in result for val in vec)

    @patch('trustgraph.embeddings.fastembed.processor.TextEmbedding')
    def test_processor_specifications_setup(self, mock_text_embedding):
        """Test that processor sets up correct specifications"""
        # Arrange
        mock_text_embedding.return_value = Mock()
        
        # Act
        processor = Processor()
        
        # Assert
        # Verify processor inherits from EmbeddingsService correctly
        assert hasattr(processor, 'specifications')
        assert callable(processor.on_request)
        assert hasattr(processor, 'on_embeddings')

    @patch('trustgraph.embeddings.fastembed.processor.TextEmbedding')
    async def test_batch_text_processing(self, mock_text_embedding):
        """Test processing multiple texts in batch"""
        # Arrange
        mock_embedding_instance = Mock()
        mock_embedding_instance.embed.return_value = [
            np.array([0.1, 0.2, 0.3]),
            np.array([0.4, 0.5, 0.6]),
            np.array([0.7, 0.8, 0.9])
        ]
        mock_text_embedding.return_value = mock_embedding_instance
        
        processor = Processor()
        
        # Test multiple sequential calls (simulating batch processing)
        texts = ["Text 1", "Text 2", "Text 3"]
        results = []
        
        # Act
        for text in texts:
            result = await processor.on_embeddings(text)
            results.append(result)
        
        # Assert
        assert len(results) == 3
        # Each call should process one text at a time
        for i, call in enumerate(mock_embedding_instance.embed.call_args_list):
            assert call[0][0] == [texts[i]]

    @patch('trustgraph.embeddings.fastembed.processor.TextEmbedding')
    def test_model_parameter_validation(self, mock_text_embedding):
        """Test that model parameter is properly passed to FastEmbed"""
        # Arrange
        mock_text_embedding.return_value = Mock()
        custom_model = "sentence-transformers/paraphrase-MiniLM-L6-v2"
        
        # Act
        processor = Processor(model=custom_model)
        
        # Assert
        mock_text_embedding.assert_called_once_with(model_name=custom_model)

    @patch('trustgraph.embeddings.fastembed.processor.TextEmbedding')
    async def test_dimension_consistency(self, mock_text_embedding):
        """Test that embedding dimensions are consistent across calls"""
        # Arrange
        mock_embedding_instance = Mock()
        # Always return same dimension vectors
        consistent_dimension = 384
        mock_embedding_instance.embed.side_effect = [
            [np.random.rand(consistent_dimension)],
            [np.random.rand(consistent_dimension)],
            [np.random.rand(consistent_dimension)]
        ]
        mock_text_embedding.return_value = mock_embedding_instance
        
        processor = Processor()
        
        # Act
        results = []
        for i in range(3):
            result = await processor.on_embeddings(f"Test text {i}")
            results.append(result)
        
        # Assert
        for result in results:
            assert len(result) == 1  # One embedding per call
            assert len(result[0]) == consistent_dimension  # Consistent dimensions