"""
Unit tests for the ImageToTextService base class
Following the same pattern as the LLM service parameter tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

from trustgraph.base.image_to_text_service import (
    ImageToTextService, ImageDescriptionResult,
)
from trustgraph.base import ParameterSpec, ConsumerSpec, ProducerSpec
from trustgraph.schema import ImageToTextRequest, ImageToTextResponse
from trustgraph.exceptions import TooManyRequests


class MockAsyncProcessor:
    def __init__(self, **params):
        self.config_handlers = []
        self.id = params.get('id', 'test-service')
        self.specifications = []


class TestImageToTextService(IsolatedAsyncioTestCase):
    """Test image-to-text service base class functionality"""

    def make_service(self):
        config = {
            'id': 'test-image-to-text-service',
            'concurrency': 1,
            'taskgroup': AsyncMock()
        }
        return ImageToTextService(**config)

    def make_message(self, image="aW1hZ2U=", mime_type="image/png",
                     prompt="Describe this image", system="Be concise"):
        mock_message = MagicMock()
        mock_message.value.return_value = MagicMock()
        mock_message.value.return_value.image = image
        mock_message.value.return_value.mime_type = mime_type
        mock_message.value.return_value.prompt = prompt
        mock_message.value.return_value.system = system
        mock_message.properties.return_value = {"id": "test-id"}
        return mock_message

    def make_flow(self, model="vision-model"):
        mock_response_producer = AsyncMock()

        mock_flow = MagicMock()
        mock_flow.name = "test-flow"
        mock_flow.side_effect = lambda param: {
            "model": model,
            "response": mock_response_producer,
        }.get(param)

        mock_error_producer = AsyncMock()
        mock_flow.producer = {"response": mock_error_producer}

        return mock_flow, mock_response_producer, mock_error_producer

    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    def test_specification_registration(self):
        """Test that the service registers request/response/model specs"""
        # Act
        service = self.make_service()

        # Assert
        consumer_specs = {spec.name: spec for spec in service.specifications
                          if isinstance(spec, ConsumerSpec)}
        producer_specs = {spec.name: spec for spec in service.specifications
                          if isinstance(spec, ProducerSpec)}
        param_specs = {spec.name: spec for spec in service.specifications
                       if isinstance(spec, ParameterSpec)}

        assert "request" in consumer_specs
        assert consumer_specs["request"].schema == ImageToTextRequest
        assert "response" in producer_specs
        assert producer_specs["response"].schema == ImageToTextResponse
        assert "model" in param_specs

    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_on_request_dispatches_to_describe_image(self):
        """Test that on_request dispatches request fields to describe_image"""
        # Arrange
        service = self.make_service()

        service.describe_image = AsyncMock(return_value=ImageDescriptionResult(
            text="A cat on a mat",
            in_token=10,
            out_token=5,
            model="vision-model"
        ))

        mock_message = self.make_message()
        mock_consumer = MagicMock()
        mock_consumer.name = "request"
        mock_flow, mock_producer, _ = self.make_flow()

        # Act
        await service.on_request(mock_message, mock_consumer, mock_flow)

        # Assert
        service.describe_image.assert_called_once()
        call_args = service.describe_image.call_args

        assert call_args[0][0] == "aW1hZ2U="             # image
        assert call_args[0][1] == "image/png"            # mime_type
        assert call_args[0][2] == "Describe this image"  # prompt
        assert call_args[0][3] == "Be concise"           # system
        assert call_args[0][4] == "vision-model"         # model

        # Verify flow was queried for the model parameter
        mock_flow.assert_any_call("model")

    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_on_request_formats_response(self):
        """Test that on_request propagates description/tokens/model"""
        # Arrange
        service = self.make_service()

        service.describe_image = AsyncMock(return_value=ImageDescriptionResult(
            text="A cat on a mat",
            in_token=10,
            out_token=5,
            model="vision-model"
        ))

        mock_message = self.make_message()
        mock_consumer = MagicMock()
        mock_consumer.name = "request"
        mock_flow, mock_producer, _ = self.make_flow()

        # Act
        await service.on_request(mock_message, mock_consumer, mock_flow)

        # Assert
        mock_producer.send.assert_called_once()
        response = mock_producer.send.call_args[0][0]
        properties = mock_producer.send.call_args[1]["properties"]

        assert response.error is None
        assert response.description == "A cat on a mat"
        assert response.in_token == 10
        assert response.out_token == 5
        assert response.model == "vision-model"
        assert properties == {"id": "test-id"}

    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_on_request_handles_missing_model_parameter(self):
        """Test that on_request passes None model when flow has none"""
        # Arrange
        service = self.make_service()

        service.describe_image = AsyncMock(return_value=ImageDescriptionResult(
            text="A cat on a mat",
            in_token=10,
            out_token=5,
            model="default-model"
        ))

        mock_message = self.make_message()
        mock_consumer = MagicMock()
        mock_consumer.name = "request"
        mock_flow, mock_producer, _ = self.make_flow(model=None)

        # Act
        await service.on_request(mock_message, mock_consumer, mock_flow)

        # Assert
        service.describe_image.assert_called_once()
        call_args = service.describe_image.call_args

        assert call_args[0][4] is None  # model (will use processor default)

    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_on_request_error_produces_structured_error(self):
        """Test that a backend exception produces a structured error response"""
        # Arrange
        service = self.make_service()

        service.describe_image = AsyncMock(side_effect=Exception("Test error"))

        mock_message = self.make_message()
        mock_consumer = MagicMock()
        mock_consumer.name = "request"
        mock_flow, _, mock_error_producer = self.make_flow()

        # Act
        await service.on_request(mock_message, mock_consumer, mock_flow)

        # Assert
        mock_error_producer.send.assert_called_once()
        error_response = mock_error_producer.send.call_args[0][0]

        assert error_response.error is not None
        assert error_response.error.type == "image-to-text-error"
        assert "Test error" in error_response.error.message
        assert error_response.description is None

    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_on_request_reraises_too_many_requests(self):
        """Test that TooManyRequests is re-raised for the retry machinery"""
        # Arrange
        service = self.make_service()

        service.describe_image = AsyncMock(side_effect=TooManyRequests())

        mock_message = self.make_message()
        mock_consumer = MagicMock()
        mock_consumer.name = "request"
        mock_flow, mock_producer, mock_error_producer = self.make_flow()

        # Act & Assert
        with pytest.raises(TooManyRequests):
            await service.on_request(mock_message, mock_consumer, mock_flow)

        # No response of any kind should have been sent
        mock_producer.send.assert_not_called()
        mock_error_producer.send.assert_not_called()


if __name__ == '__main__':
    pytest.main([__file__])
