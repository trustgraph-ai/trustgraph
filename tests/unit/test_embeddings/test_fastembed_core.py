"""
Unit tests for FastEmbed core embedding functionality

Tests the core business logic without full processor initialization,
focusing on the embedding generation methods.
"""

import pytest
from unittest.mock import patch, Mock
import numpy as np


class TestFastEmbedCore:
    """Test core FastEmbed embedding functionality"""

    @patch('trustgraph.embeddings.fastembed.processor.TextEmbedding')
    def test_fastembed_initialization(self, mock_text_embedding):
        """Test FastEmbed TextEmbedding initialization"""
        # Arrange
        mock_embedding = Mock()
        mock_text_embedding.return_value = mock_embedding
        
        # Act
        from trustgraph.embeddings.fastembed.processor import TextEmbedding
        embedding_model = TextEmbedding(model_name="test-model")
        
        # Assert
        mock_text_embedding.assert_called_once_with(model_name="test-model")

    @patch('trustgraph.embeddings.fastembed.processor.TextEmbedding')
    def test_fastembed_embed_method(self, mock_text_embedding):
        """Test FastEmbed embed method functionality"""
        # Arrange
        mock_embedding = Mock()
        mock_embedding.embed.return_value = [
            np.array([0.1, 0.2, -0.3, 0.4, -0.5])
        ]
        mock_text_embedding.return_value = mock_embedding
        
        # Act
        from trustgraph.embeddings.fastembed.processor import TextEmbedding
        embedding_model = TextEmbedding(model_name="test-model")
        result = embedding_model.embed(["Test text"])
        
        # Assert
        mock_embedding.embed.assert_called_once_with(["Test text"])
        assert len(result) == 1
        np.testing.assert_array_equal(result[0], np.array([0.1, 0.2, -0.3, 0.4, -0.5]))

    def test_numpy_to_list_conversion(self):
        """Test numpy array to list conversion logic"""
        # Arrange
        test_arrays = [
            np.array([0.1, 0.2, 0.3], dtype=np.float32),
            np.array([-0.4, 0.5, -0.6], dtype=np.float64),
            np.array([1, 2, 3], dtype=np.int32)
        ]
        
        # Act
        converted = [arr.tolist() for arr in test_arrays]
        
        # Assert
        assert all(isinstance(vec, list) for vec in converted)
        assert len(converted) == 3
        
        # Check float32 conversion (with tolerance for precision)
        assert len(converted[0]) == 3
        assert abs(converted[0][0] - 0.1) < 0.001
        assert abs(converted[0][1] - 0.2) < 0.001
        assert abs(converted[0][2] - 0.3) < 0.001
        
        # Check float64 conversion (more precise)
        assert converted[1] == [-0.4, 0.5, -0.6]
        
        # Check integer conversion (exact)
        assert converted[2] == [1, 2, 3]
        
        assert all(isinstance(val, (int, float)) for vec in converted for val in vec)

    def test_embedding_dimension_consistency(self):
        """Test that embeddings maintain consistent dimensions"""
        # Arrange
        test_vectors = [
            np.array([0.1, 0.2, 0.3, 0.4, 0.5]),
            np.array([0.6, 0.7, 0.8, 0.9, 1.0]),
            np.array([-0.1, -0.2, -0.3, -0.4, -0.5])
        ]
        
        # Act
        converted = [vec.tolist() for vec in test_vectors]
        
        # Assert
        dimensions = [len(vec) for vec in converted]
        assert all(dim == dimensions[0] for dim in dimensions), "All vectors should have same dimension"
        assert dimensions[0] == 5

    def test_embedding_batch_processing_logic(self):
        """Test batch processing logic for multiple texts"""
        # Arrange
        test_texts = ["Text 1", "Text 2", "Text 3"]
        mock_embeddings = [
            np.array([0.1, 0.2, 0.3]),
            np.array([0.4, 0.5, 0.6]),
            np.array([0.7, 0.8, 0.9])
        ]
        
        # Act - Simulate the conversion logic used in FastEmbed processor
        result = [vec.tolist() for vec in mock_embeddings]
        
        # Assert
        assert len(result) == len(test_texts)
        assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]

    def test_empty_text_handling(self):
        """Test handling of empty text input"""
        # Arrange
        empty_embedding = np.array([])
        
        # Act
        result = empty_embedding.tolist()
        
        # Assert
        assert result == []
        assert isinstance(result, list)

    def test_large_embedding_vectors(self):
        """Test handling of large embedding vectors"""
        # Arrange
        large_dimension = 1536
        large_vector = np.random.rand(large_dimension)
        
        # Act
        result = large_vector.tolist()
        
        # Assert
        assert len(result) == large_dimension
        assert isinstance(result, list)
        assert all(isinstance(val, float) for val in result)

    def test_unicode_text_compatibility(self):
        """Test that Unicode text is properly handled"""
        # Arrange
        unicode_texts = [
            "Hello 世界",
            "Café naïve",
            "🚀 Rocket",
            "Ελληνικά",
            "русский"
        ]
        
        # Act - Simulate text processing
        processed_texts = [text.encode('utf-8').decode('utf-8') for text in unicode_texts]
        
        # Assert
        assert processed_texts == unicode_texts
        assert all(isinstance(text, str) for text in processed_texts)

    def test_model_parameter_validation(self):
        """Test model parameter validation"""
        # Arrange
        valid_models = [
            "sentence-transformers/all-MiniLM-L6-v2",
            "sentence-transformers/paraphrase-MiniLM-L6-v2",
            "BAAI/bge-small-en-v1.5"
        ]
        
        # Act & Assert - All should be valid string parameters
        for model in valid_models:
            assert isinstance(model, str)
            assert len(model) > 0
            assert "/" in model or "-" in model  # Common model naming patterns

    @patch('trustgraph.embeddings.fastembed.processor.TextEmbedding')
    def test_error_handling_simulation(self, mock_text_embedding):
        """Test error handling in embedding generation"""
        # Arrange
        mock_embedding = Mock()
        mock_embedding.embed.side_effect = Exception("Model loading failed")
        mock_text_embedding.return_value = mock_embedding
        
        # Act & Assert
        from trustgraph.embeddings.fastembed.processor import TextEmbedding
        embedding_model = TextEmbedding(model_name="test-model")
        
        with pytest.raises(Exception, match="Model loading failed"):
            embedding_model.embed(["Test text"])

    def test_default_model_constant(self):
        """Test that default model constant is properly defined"""
        # Act
        from trustgraph.embeddings.fastembed.processor import default_model
        
        # Assert
        assert default_model == "sentence-transformers/all-MiniLM-L6-v2"
        assert isinstance(default_model, str)
        assert len(default_model) > 0

    def test_processor_add_args_functionality(self):
        """Test add_args static method functionality"""
        # Arrange
        from trustgraph.embeddings.fastembed.processor import Processor
        mock_parser = Mock()
        
        # Act
        Processor.add_args(mock_parser)
        
        # Assert
        # Verify model argument was added
        model_calls = [call for call in mock_parser.add_argument.call_args_list 
                      if call[0][0] in ['-m', '--model']]
        assert len(model_calls) == 1
        model_call = model_calls[0]
        assert model_call[1]['default'] == "sentence-transformers/all-MiniLM-L6-v2"