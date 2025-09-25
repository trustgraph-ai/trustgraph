"""
Unit tests for LLM Service Parameter Specifications
Testing the new parameter-aware functionality added to the LLM base service
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

from trustgraph.base.llm_service import LlmService, LlmResult
from trustgraph.base import ParameterSpec


class TestLlmServiceParameters(IsolatedAsyncioTestCase):
    """Test LLM service parameter specification functionality"""

    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    def test_parameter_specs_registration(self, mock_async_init):
        """Test that LLM service registers model and temperature parameter specs"""
        # Arrange
        mock_async_init.return_value = None

        config = {
            'id': 'test-llm-service',
            'concurrency': 1
        }

        # Act
        service = LlmService(**config)

        # Assert
        param_specs = {spec.name: spec for spec in service.specifications
                      if isinstance(spec, ParameterSpec)}

        assert "model" in param_specs
        assert "temperature" in param_specs
        assert len(param_specs) >= 2  # May have other parameter specs

    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    def test_model_parameter_spec_properties(self, mock_async_init):
        """Test that model parameter spec has correct properties"""
        # Arrange
        mock_async_init.return_value = None

        config = {
            'id': 'test-llm-service',
            'concurrency': 1
        }

        # Act
        service = LlmService(**config)

        # Assert
        model_spec = None
        for spec in service.specifications:
            if isinstance(spec, ParameterSpec) and spec.name == "model":
                model_spec = spec
                break

        assert model_spec is not None
        assert model_spec.name == "model"

    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    def test_temperature_parameter_spec_properties(self, mock_async_init):
        """Test that temperature parameter spec has correct properties"""
        # Arrange
        mock_async_init.return_value = None

        config = {
            'id': 'test-llm-service',
            'concurrency': 1
        }

        # Act
        service = LlmService(**config)

        # Assert
        temperature_spec = None
        for spec in service.specifications:
            if isinstance(spec, ParameterSpec) and spec.name == "temperature":
                temperature_spec = spec
                break

        assert temperature_spec is not None
        assert temperature_spec.name == "temperature"

    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    async def test_on_request_extracts_parameters_from_flow(self, mock_async_init):
        """Test that on_request method extracts model and temperature from flow"""
        # Arrange
        mock_async_init.return_value = None

        config = {
            'id': 'test-llm-service',
            'concurrency': 1
        }

        service = LlmService(**config)

        # Mock the generate_content method to capture parameters
        service.generate_content = AsyncMock(return_value=LlmResult(
            text="test response",
            in_token=10,
            out_token=5,
            model="gpt-4"
        ))

        # Mock message and flow
        mock_message = MagicMock()
        mock_message.value.return_value = MagicMock()
        mock_message.value.return_value.system = "system prompt"
        mock_message.value.return_value.prompt = "user prompt"
        mock_message.properties.return_value = {"id": "test-id"}

        mock_consumer = MagicMock()
        mock_consumer.name = "request"

        mock_flow = MagicMock()
        mock_flow.name = "test-flow"
        mock_flow.return_value = "test-model"  # flow("model") returns this
        mock_flow.side_effect = lambda param: {
            "model": "gpt-4",
            "temperature": 0.7
        }.get(param, f"mock-{param}")

        mock_producer = AsyncMock()
        mock_flow.return_value = mock_producer  # flow("response") returns producer

        # Act
        await service.on_request(mock_message, mock_consumer, mock_flow)

        # Assert
        # Verify that generate_content was called with parameters from flow
        service.generate_content.assert_called_once()
        call_args = service.generate_content.call_args

        assert call_args[0][0] == "system prompt"  # system
        assert call_args[0][1] == "user prompt"    # prompt
        assert call_args[0][2] == "gpt-4"          # model
        assert call_args[0][3] == 0.7              # temperature

        # Verify flow was queried for both parameters
        mock_flow.assert_any_call("model")
        mock_flow.assert_any_call("temperature")

    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    async def test_on_request_handles_missing_parameters_gracefully(self, mock_async_init):
        """Test that on_request handles missing parameters gracefully"""
        # Arrange
        mock_async_init.return_value = None

        config = {
            'id': 'test-llm-service',
            'concurrency': 1
        }

        service = LlmService(**config)

        # Mock the generate_content method
        service.generate_content = AsyncMock(return_value=LlmResult(
            text="test response",
            in_token=10,
            out_token=5,
            model="default-model"
        ))

        # Mock message and flow where flow returns None for parameters
        mock_message = MagicMock()
        mock_message.value.return_value = MagicMock()
        mock_message.value.return_value.system = "system prompt"
        mock_message.value.return_value.prompt = "user prompt"
        mock_message.properties.return_value = {"id": "test-id"}

        mock_consumer = MagicMock()
        mock_consumer.name = "request"

        mock_flow = MagicMock()
        mock_flow.name = "test-flow"
        mock_flow.return_value = None  # Both parameters return None

        mock_producer = AsyncMock()
        mock_flow.return_value = mock_producer

        # Act
        await service.on_request(mock_message, mock_consumer, mock_flow)

        # Assert
        # Should still call generate_content, with None values that will use processor defaults
        service.generate_content.assert_called_once()
        call_args = service.generate_content.call_args

        assert call_args[0][0] == "system prompt"  # system
        assert call_args[0][1] == "user prompt"    # prompt
        assert call_args[0][2] is None             # model (will use processor default)
        assert call_args[0][3] is None             # temperature (will use processor default)

    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    async def test_on_request_error_handling_preserves_behavior(self, mock_async_init):
        """Test that parameter extraction doesn't break existing error handling"""
        # Arrange
        mock_async_init.return_value = None

        config = {
            'id': 'test-llm-service',
            'concurrency': 1
        }

        service = LlmService(**config)

        # Mock generate_content to raise an exception
        service.generate_content = AsyncMock(side_effect=Exception("Test error"))

        # Mock message and flow
        mock_message = MagicMock()
        mock_message.value.return_value = MagicMock()
        mock_message.value.return_value.system = "system prompt"
        mock_message.value.return_value.prompt = "user prompt"
        mock_message.properties.return_value = {"id": "test-id"}

        mock_consumer = MagicMock()
        mock_consumer.name = "request"

        mock_flow = MagicMock()
        mock_flow.name = "test-flow"
        mock_flow.side_effect = lambda param: {
            "model": "gpt-4",
            "temperature": 0.7
        }.get(param, f"mock-{param}")

        mock_producer = AsyncMock()
        mock_flow.producer = {"response": mock_producer}

        # Act
        await service.on_request(mock_message, mock_consumer, mock_flow)

        # Assert
        # Should have sent error response
        mock_producer.send.assert_called_once()
        error_response = mock_producer.send.call_args[0][0]

        assert error_response.error is not None
        assert error_response.error.type == "llm-error"
        assert "Test error" in error_response.error.message
        assert error_response.response is None


if __name__ == '__main__':
    pytest.main([__file__])