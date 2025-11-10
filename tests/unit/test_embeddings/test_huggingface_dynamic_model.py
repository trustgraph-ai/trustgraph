"""
Unit tests for HuggingFace dynamic model loading

Tests the model caching and dynamic loading functionality for HuggingFace
embeddings service using LangChain's HuggingFaceEmbeddings.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from trustgraph.embeddings.hf.hf import Processor


class TestHuggingFaceDynamicModelLoading:
    """Test HuggingFace dynamic model loading and caching"""

    @pytest.fixture
    def mock_hf_embeddings_instance(self):
        """Mock HuggingFaceEmbeddings instance"""
        mock = Mock()
        mock.embed_documents.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]]
        return mock

    @pytest.fixture
    def base_params(self):
        """Base parameters for processor initialization"""
        return {
            "id": "test-embeddings",
            "concurrency": 1,
            "model": "test-model"
        }

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    def test_default_model_loaded_on_init(self, mock_hf_class, base_params, mock_hf_embeddings_instance):
        """Test that default model is loaded during initialization"""
        # Arrange
        mock_hf_class.return_value = mock_hf_embeddings_instance

        # Act
        processor = Processor(**base_params)

        # Assert
        mock_hf_class.assert_called_once_with(model_name="test-model")
        assert processor.default_model == "test-model"
        assert processor.cached_model_name == "test-model"
        assert processor.embeddings is not None

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    def test_model_caching_avoids_reload(self, mock_hf_class, base_params, mock_hf_embeddings_instance):
        """Test that using the same model doesn't reload it"""
        # Arrange
        mock_hf_class.return_value = mock_hf_embeddings_instance
        processor = Processor(**base_params)
        mock_hf_class.reset_mock()

        # Act - use same model multiple times
        processor._load_model("test-model")
        processor._load_model("test-model")
        processor._load_model("test-model")

        # Assert - model should not be reloaded
        mock_hf_class.assert_not_called()
        assert processor.cached_model_name == "test-model"

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    def test_model_reload_on_name_change(self, mock_hf_class, base_params, mock_hf_embeddings_instance):
        """Test that changing model name triggers reload"""
        # Arrange
        mock_hf_class.return_value = mock_hf_embeddings_instance
        processor = Processor(**base_params)
        mock_hf_class.reset_mock()

        # Act - switch to different model
        processor._load_model("different-model")

        # Assert
        mock_hf_class.assert_called_once_with(model_name="different-model")
        assert processor.cached_model_name == "different-model"

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    @pytest.mark.asyncio
    async def test_on_embeddings_uses_default_model(self, mock_hf_class, base_params, mock_hf_embeddings_instance):
        """Test that on_embeddings uses default model when no model specified"""
        # Arrange
        mock_hf_class.return_value = mock_hf_embeddings_instance
        processor = Processor(**base_params)
        mock_hf_class.reset_mock()

        # Act
        result = await processor.on_embeddings("test text")

        # Assert
        mock_hf_embeddings_instance.embed_documents.assert_called_once_with(["test text"])
        assert processor.cached_model_name == "test-model"  # Still using default
        assert result == [[0.1, 0.2, 0.3, 0.4, 0.5]]

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    @pytest.mark.asyncio
    async def test_on_embeddings_uses_specified_model(self, mock_hf_class, base_params, mock_hf_embeddings_instance):
        """Test that on_embeddings uses specified model when provided"""
        # Arrange
        mock_hf_class.return_value = mock_hf_embeddings_instance
        processor = Processor(**base_params)
        mock_hf_class.reset_mock()

        # Act
        result = await processor.on_embeddings("test text", model="custom-model")

        # Assert
        mock_hf_class.assert_called_once_with(model_name="custom-model")
        assert processor.cached_model_name == "custom-model"
        mock_hf_embeddings_instance.embed_documents.assert_called_once_with(["test text"])

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    @pytest.mark.asyncio
    async def test_multiple_model_switches(self, mock_hf_class, base_params, mock_hf_embeddings_instance):
        """Test switching between multiple models"""
        # Arrange
        mock_hf_class.return_value = mock_hf_embeddings_instance
        processor = Processor(**base_params)
        mock_hf_class.reset_mock()

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
        assert call_count_after_a == 1  # First load
        assert call_count_after_a_repeat == 1  # No reload
        assert call_count_after_b == 2  # Reload for model-b
        assert call_count_after_a_again == 3  # Reload back to model-a

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    @pytest.mark.asyncio
    async def test_none_model_uses_default(self, mock_hf_class, base_params, mock_hf_embeddings_instance):
        """Test that None model parameter falls back to default"""
        # Arrange
        mock_hf_class.return_value = mock_hf_embeddings_instance
        processor = Processor(**base_params)
        mock_hf_class.reset_mock()

        # Act
        result = await processor.on_embeddings("test text", model=None)

        # Assert
        mock_hf_class.assert_not_called()  # No reload, using cached default
        assert processor.cached_model_name == "test-model"

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    @pytest.mark.asyncio
    async def test_empty_string_model_uses_default(self, mock_hf_class, base_params, mock_hf_embeddings_instance):
        """Test that empty string model parameter falls back to default"""
        # Arrange
        mock_hf_class.return_value = mock_hf_embeddings_instance
        processor = Processor(**base_params)
        mock_hf_class.reset_mock()

        # Act
        result = await processor.on_embeddings("test text", model="")

        # Assert
        # Empty string is falsy, so it should use default
        mock_hf_class.assert_not_called()  # No reload
        assert processor.cached_model_name == "test-model"

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    def test_initialization_with_custom_model(self, mock_hf_class, mock_hf_embeddings_instance):
        """Test initialization with custom model parameter"""
        # Arrange
        mock_hf_class.return_value = mock_hf_embeddings_instance

        # Act
        processor = Processor(
            id="test-embeddings",
            concurrency=1,
            model="custom-init-model"
        )

        # Assert
        mock_hf_class.assert_called_once_with(model_name="custom-init-model")
        assert processor.default_model == "custom-init-model"
        assert processor.cached_model_name == "custom-init-model"

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    def test_initialization_without_model_uses_default(self, mock_hf_class, mock_hf_embeddings_instance):
        """Test initialization without model parameter uses module default"""
        # Arrange
        mock_hf_class.return_value = mock_hf_embeddings_instance

        # Act
        processor = Processor(
            id="test-embeddings",
            concurrency=1
        )

        # Assert
        # Should use default_model from module
        expected_default = "all-MiniLM-L6-v2"
        mock_hf_class.assert_called_once_with(model_name=expected_default)
        assert processor.default_model == expected_default
        assert processor.cached_model_name == expected_default

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    @pytest.mark.asyncio
    async def test_embed_documents_called_correctly(self, mock_hf_class, base_params, mock_hf_embeddings_instance):
        """Test that embed_documents is called with correct format"""
        # Arrange
        mock_hf_class.return_value = mock_hf_embeddings_instance
        processor = Processor(**base_params)

        # Act
        result = await processor.on_embeddings("test text")

        # Assert
        # HuggingFace expects a list of texts
        mock_hf_embeddings_instance.embed_documents.assert_called_once_with(["test text"])
        assert isinstance(result, list)

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    @pytest.mark.asyncio
    async def test_different_text_inputs(self, mock_hf_class, base_params, mock_hf_embeddings_instance):
        """Test with different text inputs"""
        # Arrange
        mock_hf_class.return_value = mock_hf_embeddings_instance
        processor = Processor(**base_params)

        test_texts = [
            "Simple text",
            "Text with\nnewlines",
            "Unicode: 世界 🌍",
            "",
            "Very " * 1000 + "long text"
        ]

        # Act & Assert
        for text in test_texts:
            result = await processor.on_embeddings(text, model="test-model")
            # Verify embed_documents was called with the text in a list
            assert mock_hf_embeddings_instance.embed_documents.called
            last_call = mock_hf_embeddings_instance.embed_documents.call_args
            assert last_call[0][0] == [text]

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    @pytest.mark.asyncio
    async def test_concurrent_requests_with_different_models(self, mock_hf_class, base_params, mock_hf_embeddings_instance):
        """Test that concurrent requests with different models work correctly"""
        # Arrange
        import asyncio
        mock_hf_class.return_value = mock_hf_embeddings_instance
        processor = Processor(**base_params)

        # Act - simulate concurrent requests
        tasks = [
            processor.on_embeddings("text1", model="model-a"),
            processor.on_embeddings("text2", model="model-b"),
            processor.on_embeddings("text3", model="model-a"),
        ]
        results = await asyncio.gather(*tasks)

        # Assert
        assert len(results) == 3
        # Models should have been switched during execution
        # Final cached model depends on execution order

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    @pytest.mark.asyncio
    async def test_embeddings_response_format(self, mock_hf_class, base_params, mock_hf_embeddings_instance):
        """Test that embeddings response is properly formatted"""
        # Arrange
        mock_hf_class.return_value = mock_hf_embeddings_instance
        processor = Processor(**base_params)

        # Act
        result = await processor.on_embeddings("test text")

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], list)
        assert all(isinstance(x, float) for x in result[0])

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    @pytest.mark.asyncio
    async def test_logging_on_model_load(self, mock_hf_class, base_params, mock_hf_embeddings_instance):
        """Test that appropriate logging occurs during model loading"""
        # Arrange
        mock_hf_class.return_value = mock_hf_embeddings_instance
        processor = Processor(**base_params)

        # The test passes if no exceptions are raised during model loading
        # In a real scenario, we'd check logger.info calls, but that requires
        # additional mocking of the logger

        # Act - force a model reload
        processor._load_model("new-model")

        # Assert
        assert processor.cached_model_name == "new-model"
        mock_hf_class.assert_called_with(model_name="new-model")

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    def test_model_caching_attribute_initialization(self, mock_hf_class, base_params, mock_hf_embeddings_instance):
        """Test that caching attributes are properly initialized"""
        # Arrange
        mock_hf_class.return_value = mock_hf_embeddings_instance

        # Act
        processor = Processor(**base_params)

        # Assert
        assert hasattr(processor, 'cached_model_name')
        assert hasattr(processor, 'embeddings')
        assert hasattr(processor, 'default_model')
        assert processor.cached_model_name == "test-model"
        assert processor.embeddings is not None
        assert processor.default_model == "test-model"

    @patch('trustgraph.embeddings.hf.hf.HuggingFaceEmbeddings')
    @pytest.mark.asyncio
    async def test_sequential_requests_same_model(self, mock_hf_class, base_params, mock_hf_embeddings_instance):
        """Test that sequential requests with same model are efficient"""
        # Arrange
        mock_hf_class.return_value = mock_hf_embeddings_instance
        processor = Processor(**base_params)
        initial_call_count = mock_hf_class.call_count

        # Act - multiple sequential requests with same model
        for i in range(10):
            await processor.on_embeddings(f"text {i}", model="test-model")

        # Assert - model should not be reloaded
        assert mock_hf_class.call_count == initial_call_count
        assert processor.cached_model_name == "test-model"
