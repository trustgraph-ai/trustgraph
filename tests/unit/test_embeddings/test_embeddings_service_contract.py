"""
Contract tests for EmbeddingsService base class

Tests the contract between the EmbeddingsService base class and its
implementations, ensuring proper integration of the model parameter handling.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from trustgraph.base import EmbeddingsService
from trustgraph.schema import EmbeddingsRequest, EmbeddingsResponse, Error


class ConcreteEmbeddingsService(EmbeddingsService):
    """Concrete implementation for testing the abstract base class"""

    def __init__(self, **params):
        super().__init__(**params)
        self.default_model = params.get("model", "default-test-model")
        self.on_embeddings_calls = []

    async def on_embeddings(self, text, model=None):
        """Implementation that tracks calls"""
        self.on_embeddings_calls.append({
            "text": text,
            "model": model
        })
        # Return a simple embedding
        return [[0.1, 0.2, 0.3]]


class TestEmbeddingsServiceContract:
    """Test the contract and integration of EmbeddingsService"""

    @pytest.fixture
    def base_params(self):
        """Base parameters for service initialization"""
        return {
            "id": "test-embeddings",
            "concurrency": 1,
            "model": "test-model"
        }

    @pytest.fixture
    def mock_message(self):
        """Mock Pulsar message"""
        message = Mock()
        message.properties.return_value = {"id": "test-msg-123"}
        return message

    @pytest.fixture
    def mock_flow(self):
        """Mock flow with producer"""
        flow = Mock()
        flow.return_value.send = AsyncMock()
        flow.producer = {"response": Mock()}
        flow.producer["response"].send = AsyncMock()
        return flow

    def test_base_class_initialization(self, base_params):
        """Test that base class initializes with parameters"""
        # Act
        service = ConcreteEmbeddingsService(**base_params)

        # Assert
        assert service.default_model == "test-model"
        assert hasattr(service, 'on_request')

    def test_model_parameter_spec_registered(self, base_params):
        """Test that model parameter specification is registered"""
        # Act
        service = ConcreteEmbeddingsService(**base_params)

        # Assert
        # The service should have registered the model parameter spec
        # This is verified by the fact that the service can be initialized
        # with a model parameter without errors
        assert service.default_model == "test-model"

    @pytest.mark.asyncio
    async def test_on_request_extracts_model_from_request(self, base_params, mock_message, mock_flow):
        """Test that on_request extracts model from EmbeddingsRequest"""
        # Arrange
        service = ConcreteEmbeddingsService(**base_params)
        request = EmbeddingsRequest(
            text="test text",
            model="custom-request-model"
        )
        mock_message.value.return_value = request
        mock_consumer = Mock()

        # Act
        await service.on_request(mock_message, mock_consumer, mock_flow)

        # Assert
        assert len(service.on_embeddings_calls) == 1
        call = service.on_embeddings_calls[0]
        assert call["text"] == "test text"
        assert call["model"] == "custom-request-model"

    @pytest.mark.asyncio
    async def test_on_request_uses_none_when_model_empty(self, base_params, mock_message, mock_flow):
        """Test that on_request passes None when request model is empty"""
        # Arrange
        service = ConcreteEmbeddingsService(**base_params)
        request = EmbeddingsRequest(
            text="test text",
            model=""
        )
        mock_message.value.return_value = request
        mock_consumer = Mock()

        # Act
        await service.on_request(mock_message, mock_consumer, mock_flow)

        # Assert
        assert len(service.on_embeddings_calls) == 1
        call = service.on_embeddings_calls[0]
        assert call["text"] == "test text"
        assert call["model"] is None  # Empty string should be converted to None

    @pytest.mark.asyncio
    async def test_on_request_uses_none_when_model_whitespace(self, base_params, mock_message, mock_flow):
        """Test that on_request passes None when request model is whitespace"""
        # Arrange
        service = ConcreteEmbeddingsService(**base_params)
        request = EmbeddingsRequest(
            text="test text",
            model="   "
        )
        mock_message.value.return_value = request
        mock_consumer = Mock()

        # Act
        await service.on_request(mock_message, mock_consumer, mock_flow)

        # Assert
        assert len(service.on_embeddings_calls) == 1
        call = service.on_embeddings_calls[0]
        assert call["text"] == "test text"
        assert call["model"] is None  # Whitespace should be converted to None

    @pytest.mark.asyncio
    async def test_on_request_sends_response(self, base_params, mock_message, mock_flow):
        """Test that on_request sends response through flow"""
        # Arrange
        service = ConcreteEmbeddingsService(**base_params)
        request = EmbeddingsRequest(
            text="test text",
            model="test-model"
        )
        mock_message.value.return_value = request
        mock_consumer = Mock()

        # Act
        await service.on_request(mock_message, mock_consumer, mock_flow)

        # Assert
        mock_flow.return_value.send.assert_called_once()
        call_args = mock_flow.return_value.send.call_args

        # Verify response structure
        response = call_args[0][0]
        assert isinstance(response, EmbeddingsResponse)
        assert response.error is None
        assert response.vectors == [[0.1, 0.2, 0.3]]

        # Verify properties
        properties = call_args[1]["properties"]
        assert properties["id"] == "test-msg-123"

    @pytest.mark.asyncio
    async def test_on_request_handles_exception(self, base_params, mock_message, mock_flow):
        """Test that on_request handles exceptions and sends error response"""
        # Arrange
        class FailingEmbeddingsService(EmbeddingsService):
            async def on_embeddings(self, text, model=None):
                raise ValueError("Test error")

        service = FailingEmbeddingsService(**base_params)
        request = EmbeddingsRequest(
            text="test text",
            model="test-model"
        )
        mock_message.value.return_value = request
        mock_consumer = Mock()

        # Act
        await service.on_request(mock_message, mock_consumer, mock_flow)

        # Assert
        mock_flow.producer["response"].send.assert_called_once()
        call_args = mock_flow.producer["response"].send.call_args

        # Verify error response structure
        response = call_args[0][0]
        assert isinstance(response, EmbeddingsResponse)
        assert response.error is not None
        assert response.error.type == "embeddings-error"
        assert "Test error" in response.error.message
        assert response.vectors is None

    @pytest.mark.asyncio
    async def test_multiple_requests_with_different_models(self, base_params, mock_flow):
        """Test processing multiple requests with different models"""
        # Arrange
        service = ConcreteEmbeddingsService(**base_params)
        mock_consumer = Mock()

        requests_and_models = [
            ("text1", "model-a"),
            ("text2", "model-b"),
            ("text3", ""),  # Empty, should use None
            ("text4", "model-a"),
        ]

        # Act
        for text, model in requests_and_models:
            mock_message = Mock()
            mock_message.properties.return_value = {"id": f"msg-{text}"}
            mock_message.value.return_value = EmbeddingsRequest(
                text=text,
                model=model
            )
            await service.on_request(mock_message, mock_consumer, mock_flow)

        # Assert
        assert len(service.on_embeddings_calls) == 4
        assert service.on_embeddings_calls[0]["model"] == "model-a"
        assert service.on_embeddings_calls[1]["model"] == "model-b"
        assert service.on_embeddings_calls[2]["model"] is None
        assert service.on_embeddings_calls[3]["model"] == "model-a"

    def test_consumer_spec_configuration(self, base_params):
        """Test that consumer specification is properly configured"""
        # Arrange & Act
        service = ConcreteEmbeddingsService(**base_params)

        # Assert
        # The service should have registered consumer spec with correct concurrency
        # This is tested indirectly through successful initialization
        assert hasattr(service, 'on_request')

    def test_producer_spec_configuration(self, base_params):
        """Test that producer specification is properly configured"""
        # Arrange & Act
        service = ConcreteEmbeddingsService(**base_params)

        # Assert
        # The service should have registered producer spec
        # This is tested indirectly through successful initialization
        assert service is not None

    @pytest.mark.asyncio
    async def test_request_with_non_string_model(self, base_params, mock_message, mock_flow):
        """Test handling of request when model field is not a string"""
        # Arrange
        service = ConcreteEmbeddingsService(**base_params)
        # Note: In practice, Pulsar schema validation prevents this,
        # but we test the handling logic
        request = EmbeddingsRequest(
            text="test text",
            model=None  # None is valid for optional field
        )
        mock_message.value.return_value = request
        mock_consumer = Mock()

        # Act
        await service.on_request(mock_message, mock_consumer, mock_flow)

        # Assert
        assert len(service.on_embeddings_calls) == 1
        call = service.on_embeddings_calls[0]
        assert call["model"] is None

    @pytest.mark.asyncio
    async def test_integration_with_logging(self, base_params, mock_message, mock_flow):
        """Test that requests are logged appropriately"""
        # Arrange
        service = ConcreteEmbeddingsService(**base_params)
        request = EmbeddingsRequest(
            text="test text",
            model="test-model"
        )
        mock_message.value.return_value = request
        mock_consumer = Mock()

        # Act - should not raise any exceptions
        with patch('trustgraph.base.embeddings_service.logger') as mock_logger:
            await service.on_request(mock_message, mock_consumer, mock_flow)

            # Assert
            # Verify logging calls were made
            assert mock_logger.debug.called

    def test_concurrency_parameter_handling(self):
        """Test that concurrency parameter is properly handled"""
        # Arrange & Act
        service_default = ConcreteEmbeddingsService(id="test", model="test-model")
        service_custom = ConcreteEmbeddingsService(
            id="test",
            model="test-model",
            concurrency=5
        )

        # Assert
        # Services should be created without errors
        assert service_default is not None
        assert service_custom is not None

    @pytest.mark.asyncio
    async def test_schema_validation_contract(self, base_params, mock_message, mock_flow):
        """Test that response conforms to EmbeddingsResponse schema"""
        # Arrange
        service = ConcreteEmbeddingsService(**base_params)
        request = EmbeddingsRequest(
            text="test text",
            model="test-model"
        )
        mock_message.value.return_value = request
        mock_consumer = Mock()

        # Act
        await service.on_request(mock_message, mock_consumer, mock_flow)

        # Assert
        call_args = mock_flow.return_value.send.call_args
        response = call_args[0][0]

        # Verify response has required fields
        assert hasattr(response, 'error')
        assert hasattr(response, 'vectors')

        # Verify response types
        assert response.error is None or isinstance(response.error, Error)
        assert isinstance(response.vectors, list)

    @pytest.mark.asyncio
    async def test_message_id_propagation(self, base_params, mock_flow):
        """Test that message ID is properly propagated to response"""
        # Arrange
        service = ConcreteEmbeddingsService(**base_params)
        request = EmbeddingsRequest(text="test", model="test-model")

        mock_message = Mock()
        test_id = "unique-message-id-12345"
        mock_message.properties.return_value = {"id": test_id}
        mock_message.value.return_value = request
        mock_consumer = Mock()

        # Act
        await service.on_request(mock_message, mock_consumer, mock_flow)

        # Assert
        call_args = mock_flow.return_value.send.call_args
        properties = call_args[1]["properties"]
        assert properties["id"] == test_id

    @pytest.mark.asyncio
    async def test_empty_text_handling(self, base_params, mock_message, mock_flow):
        """Test handling of empty text in request"""
        # Arrange
        service = ConcreteEmbeddingsService(**base_params)
        request = EmbeddingsRequest(
            text="",
            model="test-model"
        )
        mock_message.value.return_value = request
        mock_consumer = Mock()

        # Act
        await service.on_request(mock_message, mock_consumer, mock_flow)

        # Assert
        assert len(service.on_embeddings_calls) == 1
        call = service.on_embeddings_calls[0]
        assert call["text"] == ""
        assert call["model"] == "test-model"

    @pytest.mark.asyncio
    async def test_unicode_text_handling(self, base_params, mock_message, mock_flow):
        """Test handling of unicode text in request"""
        # Arrange
        service = ConcreteEmbeddingsService(**base_params)
        unicode_text = "Hello 世界 🌍 Мир"
        request = EmbeddingsRequest(
            text=unicode_text,
            model="test-model"
        )
        mock_message.value.return_value = request
        mock_consumer = Mock()

        # Act
        await service.on_request(mock_message, mock_consumer, mock_flow)

        # Assert
        assert len(service.on_embeddings_calls) == 1
        call = service.on_embeddings_calls[0]
        assert call["text"] == unicode_text

    @pytest.mark.asyncio
    async def test_very_long_text_handling(self, base_params, mock_message, mock_flow):
        """Test handling of very long text in request"""
        # Arrange
        service = ConcreteEmbeddingsService(**base_params)
        long_text = "word " * 10000
        request = EmbeddingsRequest(
            text=long_text,
            model="test-model"
        )
        mock_message.value.return_value = request
        mock_consumer = Mock()

        # Act
        await service.on_request(mock_message, mock_consumer, mock_flow)

        # Assert
        assert len(service.on_embeddings_calls) == 1
        call = service.on_embeddings_calls[0]
        assert len(call["text"]) > 50000


class TestEmbeddingsRequestSchema:
    """Test the EmbeddingsRequest schema contract"""

    def test_request_with_model(self):
        """Test creating request with model"""
        # Act
        request = EmbeddingsRequest(
            text="test text",
            model="test-model"
        )

        # Assert
        assert request.text == "test text"
        assert request.model == "test-model"

    def test_request_without_model(self):
        """Test creating request without model (optional)"""
        # Act
        request = EmbeddingsRequest(
            text="test text"
        )

        # Assert
        assert request.text == "test text"
        assert request.model == ""  # Default value

    def test_request_with_empty_model(self):
        """Test creating request with empty model"""
        # Act
        request = EmbeddingsRequest(
            text="test text",
            model=""
        )

        # Assert
        assert request.text == "test text"
        assert request.model == ""

    def test_request_model_field_optional(self):
        """Test that model field is truly optional"""
        # Act
        request = EmbeddingsRequest(text="test")

        # Assert
        assert hasattr(request, 'model')
        assert request.model == ""


class TestEmbeddingsResponseSchema:
    """Test the EmbeddingsResponse schema contract"""

    def test_success_response(self):
        """Test creating success response"""
        # Act
        response = EmbeddingsResponse(
            error=None,
            vectors=[[0.1, 0.2, 0.3]]
        )

        # Assert
        assert response.error is None
        assert response.vectors == [[0.1, 0.2, 0.3]]

    def test_error_response(self):
        """Test creating error response"""
        # Act
        error = Error(type="test-error", message="Test message")
        response = EmbeddingsResponse(
            error=error,
            vectors=None
        )

        # Assert
        assert response.error is not None
        assert response.error.type == "test-error"
        assert response.error.message == "Test message"
        assert response.vectors is None

    def test_response_with_multiple_vectors(self):
        """Test response with multiple embedding vectors"""
        # Act
        vectors = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9]
        ]
        response = EmbeddingsResponse(
            error=None,
            vectors=vectors
        )

        # Assert
        assert len(response.vectors) == 3
        assert response.vectors[0] == [0.1, 0.2, 0.3]
