"""
Unit tests for embedding utilities and common functionality

Tests dimension consistency, batch processing, error handling patterns,
and other utilities common across embedding services.
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
import numpy as np

from trustgraph.schema import EmbeddingsRequest, EmbeddingsResponse, Error
from trustgraph.exceptions import TooManyRequests


class MockEmbeddingProcessor:
    """Simple mock embedding processor for testing functionality"""
    
    def __init__(self, embedding_function=None, **params):
        # Store embedding function for mocking
        self.embedding_function = embedding_function
        self.model = params.get('model', 'test-model')
    
    async def on_embeddings(self, text):
        if self.embedding_function:
            return self.embedding_function(text)
        return [0.1, 0.2, 0.3, 0.4, 0.5]  # Default test embedding


class TestEmbeddingDimensionConsistency:
    """Test cases for embedding dimension consistency"""

    async def test_consistent_dimensions_single_processor(self):
        """Test that a single processor returns consistent dimensions"""
        # Arrange
        dimension = 128
        def mock_embedding(text):
            return [0.1] * dimension
        
        processor = MockEmbeddingProcessor(embedding_function=mock_embedding)
        
        # Act
        results = []
        test_texts = ["Text 1", "Text 2", "Text 3", "Text 4", "Text 5"]
        
        for text in test_texts:
            result = await processor.on_embeddings(text)
            results.append(result)
        
        # Assert
        for result in results:
            assert len(result) == dimension, f"Expected dimension {dimension}, got {len(result)}"
        
        # All results should have same dimensions
        first_dim = len(results[0])
        for i, result in enumerate(results[1:], 1):
            assert len(result) == first_dim, f"Dimension mismatch at index {i}"

    async def test_dimension_consistency_across_text_lengths(self):
        """Test dimension consistency across varying text lengths"""
        # Arrange
        dimension = 384
        def mock_embedding(text):
            # Dimension should not depend on text length
            return [0.1] * dimension
        
        processor = MockEmbeddingProcessor(embedding_function=mock_embedding)
        
        # Act - Test various text lengths
        test_texts = [
            "",  # Empty text
            "Hi",  # Very short
            "This is a medium length sentence for testing.",  # Medium
            "This is a very long text that should still produce embeddings of consistent dimension regardless of the input text length and content." * 10  # Very long
        ]
        
        results = []
        for text in test_texts:
            result = await processor.on_embeddings(text)
            results.append(result)
        
        # Assert
        for i, result in enumerate(results):
            assert len(result) == dimension, f"Text length {len(test_texts[i])} produced wrong dimension"

    async def test_dimension_validation_different_models(self):
        """Test dimension validation for different model configurations"""
        # Arrange
        models_and_dims = [
            ("small-model", 128),
            ("medium-model", 384),
            ("large-model", 1536)
        ]
        
        for model_name, expected_dim in models_and_dims:
            def mock_embedding(text):
                return [0.1] * expected_dim
            
            processor = MockEmbeddingProcessor(
                model=model_name,
                embedding_function=mock_embedding
            )
            
            # Act
            result = await processor.on_embeddings("Test text")
            
            # Assert
            assert len(result) == expected_dim, f"Model {model_name} produced wrong dimension"


class TestEmbeddingBatchProcessing:
    """Test cases for batch processing logic"""

    async def test_sequential_processing_maintains_order(self):
        """Test that sequential processing maintains text order"""
        # Arrange
        def mock_embedding(text):
            # Return embedding that encodes the text for verification
            return [ord(text[0]) / 255.0] if text else [0.0]  # Normalize to [0,1]
        
        processor = MockEmbeddingProcessor(embedding_function=mock_embedding)
        
        # Act
        test_texts = ["A", "B", "C", "D", "E"]
        results = []
        
        for text in test_texts:
            result = await processor.on_embeddings(text)
            results.append((text, result))
        
        # Assert
        for i, (original_text, embedding) in enumerate(results):
            assert original_text == test_texts[i]
            expected_value = ord(test_texts[i][0]) / 255.0
            assert abs(embedding[0] - expected_value) < 0.001

    async def test_batch_processing_throughput(self):
        """Test batch processing capabilities"""
        # Arrange
        call_count = 0
        def mock_embedding(text):
            nonlocal call_count
            call_count += 1
            return [0.1, 0.2, 0.3]
        
        processor = MockEmbeddingProcessor(embedding_function=mock_embedding)
        
        # Act - Process multiple texts
        batch_size = 10
        test_texts = [f"Text {i}" for i in range(batch_size)]
        
        results = []
        for text in test_texts:
            result = await processor.on_embeddings(text)
            results.append(result)
        
        # Assert
        assert call_count == batch_size
        assert len(results) == batch_size
        for result in results:
            assert result == [0.1, 0.2, 0.3]

    async def test_concurrent_processing_simulation(self):
        """Test concurrent processing behavior simulation"""
        # Arrange
        import asyncio
        
        processing_times = []
        def mock_embedding(text):
            import time
            processing_times.append(time.time())
            return [len(text) / 100.0]  # Encoding text length
        
        processor = MockEmbeddingProcessor(embedding_function=mock_embedding)
        
        # Act - Simulate concurrent processing
        test_texts = [f"Text {i}" for i in range(5)]
        
        tasks = [processor.on_embeddings(text) for text in test_texts]
        results = await asyncio.gather(*tasks)
        
        # Assert
        assert len(results) == 5
        assert len(processing_times) == 5
        
        # Results should correspond to text lengths
        for i, result in enumerate(results):
            expected_value = len(test_texts[i]) / 100.0
            assert abs(result[0] - expected_value) < 0.001


class TestEmbeddingErrorHandling:
    """Test cases for error handling in embedding services"""

    async def test_embedding_function_error_handling(self):
        """Test error handling in embedding function"""
        # Arrange
        def failing_embedding(text):
            raise Exception("Embedding model failed")
        
        processor = MockEmbeddingProcessor(embedding_function=failing_embedding)
        
        # Act & Assert
        with pytest.raises(Exception, match="Embedding model failed"):
            await processor.on_embeddings("Test text")

    async def test_rate_limit_exception_propagation(self):
        """Test that rate limit exceptions are properly propagated"""
        # Arrange
        def rate_limited_embedding(text):
            raise TooManyRequests("Rate limit exceeded")
        
        processor = MockEmbeddingProcessor(embedding_function=rate_limited_embedding)
        
        # Act & Assert
        with pytest.raises(TooManyRequests, match="Rate limit exceeded"):
            await processor.on_embeddings("Test text")

    async def test_none_result_handling(self):
        """Test handling when embedding function returns None"""
        # Arrange
        def none_embedding(text):
            return None
        
        processor = MockEmbeddingProcessor(embedding_function=none_embedding)
        
        # Act
        result = await processor.on_embeddings("Test text")
        
        # Assert
        assert result is None

    async def test_invalid_embedding_format_handling(self):
        """Test handling of invalid embedding formats"""
        # Arrange
        def invalid_embedding(text):
            return "not a list"  # Invalid format
        
        processor = MockEmbeddingProcessor(embedding_function=invalid_embedding)
        
        # Act
        result = await processor.on_embeddings("Test text")
        
        # Assert
        assert result == "not a list"  # Returns what the function provides


class TestEmbeddingUtilities:
    """Test cases for embedding utility functions and helpers"""

    def test_vector_normalization_simulation(self):
        """Test vector normalization logic simulation"""
        # Arrange
        test_vectors = [
            [1.0, 2.0, 3.0],
            [0.5, -0.5, 1.0],
            [10.0, 20.0, 30.0]
        ]
        
        # Act - Simulate L2 normalization
        normalized_vectors = []
        for vector in test_vectors:
            magnitude = sum(x**2 for x in vector) ** 0.5
            if magnitude > 0:
                normalized = [x / magnitude for x in vector]
            else:
                normalized = vector
            normalized_vectors.append(normalized)
        
        # Assert
        for normalized in normalized_vectors:
            magnitude = sum(x**2 for x in normalized) ** 0.5
            assert abs(magnitude - 1.0) < 0.0001, "Vector should be unit length"

    def test_cosine_similarity_calculation(self):
        """Test cosine similarity calculation between embeddings"""
        # Arrange
        vector1 = [1.0, 0.0, 0.0]
        vector2 = [0.0, 1.0, 0.0]
        vector3 = [1.0, 0.0, 0.0]  # Same as vector1
        
        # Act - Calculate cosine similarities
        def cosine_similarity(v1, v2):
            dot_product = sum(a * b for a, b in zip(v1, v2))
            mag1 = sum(x**2 for x in v1) ** 0.5
            mag2 = sum(x**2 for x in v2) ** 0.5
            return dot_product / (mag1 * mag2) if mag1 * mag2 > 0 else 0
        
        sim_12 = cosine_similarity(vector1, vector2)
        sim_13 = cosine_similarity(vector1, vector3)
        
        # Assert
        assert abs(sim_12 - 0.0) < 0.0001, "Orthogonal vectors should have 0 similarity"
        assert abs(sim_13 - 1.0) < 0.0001, "Identical vectors should have 1.0 similarity"

    def test_embedding_validation_helpers(self):
        """Test embedding validation helper functions"""
        # Arrange
        valid_embeddings = [
            [0.1, 0.2, 0.3],
            [1.0, -1.0, 0.0],
            []  # Empty embedding
        ]
        
        invalid_embeddings = [
            None,
            "not a list",
            [1, 2, "three"],  # Mixed types
            [[1, 2], [3, 4]]  # Nested lists
        ]
        
        # Act & Assert
        def is_valid_embedding(embedding):
            if not isinstance(embedding, list):
                return False
            return all(isinstance(x, (int, float)) for x in embedding)
        
        for embedding in valid_embeddings:
            assert is_valid_embedding(embedding), f"Should be valid: {embedding}"
        
        for embedding in invalid_embeddings:
            assert not is_valid_embedding(embedding), f"Should be invalid: {embedding}"

    async def test_embedding_metadata_handling(self):
        """Test handling of embedding metadata and properties"""
        # Arrange
        def metadata_embedding(text):
            return {
                "vectors": [0.1, 0.2, 0.3],
                "model": "test-model",
                "dimension": 3,
                "text_length": len(text)
            }
        
        # Mock processor that returns metadata
        class MetadataProcessor(MockEmbeddingProcessor):
            async def on_embeddings(self, text):
                result = metadata_embedding(text)
                return result["vectors"]  # Return only vectors for compatibility
        
        processor = MetadataProcessor()
        
        # Act
        result = await processor.on_embeddings("Test text with metadata")
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == 3
        assert result == [0.1, 0.2, 0.3]