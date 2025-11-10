"""
Unit tests for HuggingFace dynamic model loading

Tests the model caching and dynamic loading functionality for HuggingFace
embeddings service using LangChain's HuggingFaceEmbeddings.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from unittest import IsolatedAsyncioTestCase

# Skip all tests in this module if trustgraph.embeddings.hf is not installed
pytest.importorskip("trustgraph.embeddings.hf")

from trustgraph.embeddings.hf.hf import Processor


class TestHuggingFaceDynamicModelLoading(IsolatedAsyncioTestCase):
    """Test HuggingFace dynamic model loading and caching"""

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.embeddings_service.EmbeddingsService.__init__')
    async def test_default_model_loaded_on_init(self, mock_embeddings_init, mock_async_init, mock_hf_class):
        """Test that default model is loaded during initialization"""
        # Arrange
        mock_hf_instance = Mock()
        mock_hf_instance.embed_documents.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]]
        mock_hf_class.return_value = mock_hf_instance
        mock_async_init.return_value = None
        mock_embeddings_init.return_value = None

        # Act
        processor = Processor(id="test", concurrency=1, model="test-model", taskgroup=AsyncMock())

        # Assert
        mock_hf_class.assert_called_once_with(model_name="test-model")
        assert processor.default_model == "test-model"
        assert processor.cached_model_name == "test-model"
        assert processor.embeddings is not None

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.embeddings_service.EmbeddingsService.__init__')
    async def test_model_caching_avoids_reload(self, mock_embeddings_init, mock_async_init, mock_hf_class):
        """Test that using the same model doesn't reload it"""
        # Arrange
        mock_hf_instance = Mock()
        mock_hf_instance.embed_documents.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]]
        mock_hf_class.return_value = mock_hf_instance
        mock_async_init.return_value = None
        mock_embeddings_init.return_value = None

        processor = Processor(id="test", concurrency=1, model="test-model", taskgroup=AsyncMock())
        mock_hf_class.reset_mock()

        # Act - use same model multiple times
        processor._load_model("test-model")
        processor._load_model("test-model")
        processor._load_model("test-model")

        # Assert - model should not be reloaded
        mock_hf_class.assert_not_called()
        assert processor.cached_model_name == "test-model"

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.embeddings_service.EmbeddingsService.__init__')
    async def test_model_reload_on_name_change(self, mock_embeddings_init, mock_async_init, mock_hf_class):
        """Test that changing model name triggers reload"""
        # Arrange
        mock_hf_instance = Mock()
        mock_hf_class.return_value = mock_hf_instance
        mock_async_init.return_value = None
        mock_embeddings_init.return_value = None

        processor = Processor(id="test", concurrency=1, model="test-model", taskgroup=AsyncMock())
        mock_hf_class.reset_mock()

        # Act - switch to different model
        processor._load_model("different-model")

        # Assert
        mock_hf_class.assert_called_once_with(model_name="different-model")
        assert processor.cached_model_name == "different-model"

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.embeddings_service.EmbeddingsService.__init__')
    async def test_on_embeddings_uses_default_model(self, mock_embeddings_init, mock_async_init, mock_hf_class):
        """Test that on_embeddings uses default model when no model specified"""
        # Arrange
        mock_hf_instance = Mock()
        mock_hf_instance.embed_documents.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]]
        mock_hf_class.return_value = mock_hf_instance
        mock_async_init.return_value = None
        mock_embeddings_init.return_value = None

        processor = Processor(id="test", concurrency=1, model="test-model", taskgroup=AsyncMock())
        mock_hf_class.reset_mock()

        # Act
        result = await processor.on_embeddings("test text")

        # Assert
        mock_hf_instance.embed_documents.assert_called_once_with(["test text"])
        assert processor.cached_model_name == "test-model"  # Still using default
        assert result == [[0.1, 0.2, 0.3, 0.4, 0.5]]

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.embeddings_service.EmbeddingsService.__init__')
    async def test_on_embeddings_uses_specified_model(self, mock_embeddings_init, mock_async_init, mock_hf_class):
        """Test that on_embeddings uses specified model when provided"""
        # Arrange
        mock_hf_instance = Mock()
        mock_hf_instance.embed_documents.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]]
        mock_hf_class.return_value = mock_hf_instance
        mock_async_init.return_value = None
        mock_embeddings_init.return_value = None

        processor = Processor(id="test", concurrency=1, model="test-model", taskgroup=AsyncMock())
        mock_hf_class.reset_mock()

        # Act
        result = await processor.on_embeddings("test text", model="custom-model")

        # Assert
        mock_hf_class.assert_called_once_with(model_name="custom-model")
        assert processor.cached_model_name == "custom-model"
        mock_hf_instance.embed_documents.assert_called_once_with(["test text"])

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.embeddings_service.EmbeddingsService.__init__')
    async def test_multiple_model_switches(self, mock_embeddings_init, mock_async_init, mock_hf_class):
        """Test switching between multiple models"""
        # Arrange
        mock_hf_instance = Mock()
        mock_hf_instance.embed_documents.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]]
        mock_hf_class.return_value = mock_hf_instance
        mock_async_init.return_value = None
        mock_embeddings_init.return_value = None

        processor = Processor(id="test", concurrency=1, model="test-model", taskgroup=AsyncMock())
        initial_call_count = mock_hf_class.call_count

        # Act - switch between models
        await processor.on_embeddings("text1", model="model-a")
        call_count_after_a = mock_hf_class.call_count

        await processor.on_embeddings("text2", model="model-a")  # Same, no reload
        call_count_after_a_repeat = mock_hf_class.call_count

        await processor.on_embeddings("text3", model="model-b")  # Different, reload
        call_count_after_b = mock_hf_class.call_count

        await processor.on_embeddings("text4", model="model-a")  # Back to A, reload
        call_count_after_a_again = mock_hf_class.call_count

        # Assert
        assert call_count_after_a == initial_call_count + 1  # First load
        assert call_count_after_a_repeat == initial_call_count + 1  # No reload
        assert call_count_after_b == initial_call_count + 2  # Reload for model-b
        assert call_count_after_a_again == initial_call_count + 3  # Reload back to model-a

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.embeddings_service.EmbeddingsService.__init__')
    async def test_none_model_uses_default(self, mock_embeddings_init, mock_async_init, mock_hf_class):
        """Test that None model parameter falls back to default"""
        # Arrange
        mock_hf_instance = Mock()
        mock_hf_instance.embed_documents.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]]
        mock_hf_class.return_value = mock_hf_instance
        mock_async_init.return_value = None
        mock_embeddings_init.return_value = None

        processor = Processor(id="test", concurrency=1, model="test-model", taskgroup=AsyncMock())
        initial_count = mock_hf_class.call_count

        # Act
        result = await processor.on_embeddings("test text", model=None)

        # Assert
        # No reload, using cached default
        assert mock_hf_class.call_count == initial_count
        assert processor.cached_model_name == "test-model"

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.embeddings_service.EmbeddingsService.__init__')
    async def test_initialization_without_model_uses_default(self, mock_embeddings_init, mock_async_init, mock_hf_class):
        """Test initialization without model parameter uses module default"""
        # Arrange
        mock_hf_instance = Mock()
        mock_hf_class.return_value = mock_hf_instance
        mock_async_init.return_value = None
        mock_embeddings_init.return_value = None

        # Act
        processor = Processor(id="test-embeddings", concurrency=1, taskgroup=AsyncMock())

        # Assert
        # Should use default_model from module
        expected_default = "all-MiniLM-L6-v2"
        mock_hf_class.assert_called_once_with(model_name=expected_default)
        assert processor.default_model == expected_default
        assert processor.cached_model_name == expected_default


if __name__ == '__main__':
    pytest.main([__file__])
