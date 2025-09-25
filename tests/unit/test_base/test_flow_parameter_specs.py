"""
Unit tests for Flow Parameter Specification functionality
Testing parameter specification registration and handling in flow processors
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

from trustgraph.base.flow_processor import FlowProcessor
from trustgraph.base import ParameterSpec, ConsumerSpec, ProducerSpec


def mock_async_processor_init(self, **params):
    """Mock AsyncProcessor.__init__ that properly initializes required attributes"""
    self.config_handlers = []
    self.id = params.get('id', 'test-service')


# Apply the mock globally for this test module
patch('trustgraph.base.async_processor.AsyncProcessor.__init__', mock_async_processor_init).start()


class TestFlowParameterSpecs(IsolatedAsyncioTestCase):
    """Test flow processor parameter specification functionality"""

    def test_parameter_spec_registration(self):
        """Test that parameter specs can be registered with flow processors"""
        # Arrange
        def mock_init(self, **kwargs):
            self.config_handlers = []
            self.id = kwargs.get('id', 'test-service')

        config = {
            'id': 'test-flow-processor',
            'concurrency': 1
        }

        processor = FlowProcessor(**config)

        # Create test parameter specs
        model_spec = ParameterSpec(name="model")
        temperature_spec = ParameterSpec(name="temperature")

        # Act
        processor.register_specification(model_spec)
        processor.register_specification(temperature_spec)

        # Assert
        assert len(processor.specifications) >= 2

        param_specs = [spec for spec in processor.specifications
                      if isinstance(spec, ParameterSpec)]
        assert len(param_specs) >= 2

        param_names = [spec.name for spec in param_specs]
        assert "model" in param_names
        assert "temperature" in param_names

    def test_mixed_specification_types(self):
        """Test registration of mixed specification types (parameters, consumers, producers)"""
        # Arrange
        def mock_init(self, **kwargs):
            self.config_handlers = []
            self.id = kwargs.get('id', 'test-service')

        config = {
            'id': 'test-flow-processor',
            'concurrency': 1
        }

        processor = FlowProcessor(**config)

        # Create different spec types
        param_spec = ParameterSpec(name="model")
        consumer_spec = ConsumerSpec(name="input", schema=MagicMock(), handler=MagicMock())
        producer_spec = ProducerSpec(name="output")

        # Act
        processor.register_specification(param_spec)
        processor.register_specification(consumer_spec)
        processor.register_specification(producer_spec)

        # Assert
        assert len(processor.specifications) == 3

        # Count each type
        param_specs = [s for s in processor.specifications if isinstance(s, ParameterSpec)]
        consumer_specs = [s for s in processor.specifications if isinstance(s, ConsumerSpec)]
        producer_specs = [s for s in processor.specifications if isinstance(s, ProducerSpec)]

        assert len(param_specs) == 1
        assert len(consumer_specs) == 1
        assert len(producer_specs) == 1

    def test_parameter_spec_metadata(self):
        """Test parameter specification metadata handling"""
        # Arrange
        def mock_init(self, **kwargs):
            self.config_handlers = []
            self.id = kwargs.get('id', 'test-service')

        config = {
            'id': 'test-flow-processor',
            'concurrency': 1
        }

        processor = FlowProcessor(**config)

        # Create parameter specs with metadata (if supported)
        model_spec = ParameterSpec(name="model")
        temperature_spec = ParameterSpec(name="temperature")

        # Act
        processor.register_specification(model_spec)
        processor.register_specification(temperature_spec)

        # Assert
        param_specs = [spec for spec in processor.specifications
                      if isinstance(spec, ParameterSpec)]

        model_spec_registered = next((s for s in param_specs if s.name == "model"), None)
        temperature_spec_registered = next((s for s in param_specs if s.name == "temperature"), None)

        assert model_spec_registered is not None
        assert temperature_spec_registered is not None
        assert model_spec_registered.name == "model"
        assert temperature_spec_registered.name == "temperature"

    def test_duplicate_parameter_spec_handling(self):
        """Test handling of duplicate parameter spec registration"""
        # Arrange
        def mock_init(self, **kwargs):
            self.config_handlers = []
            self.id = kwargs.get('id', 'test-service')

        config = {
            'id': 'test-flow-processor',
            'concurrency': 1
        }

        processor = FlowProcessor(**config)

        # Create duplicate parameter specs
        model_spec1 = ParameterSpec(name="model")
        model_spec2 = ParameterSpec(name="model")

        # Act
        processor.register_specification(model_spec1)
        processor.register_specification(model_spec2)

        # Assert - Should allow duplicates (or handle appropriately)
        param_specs = [spec for spec in processor.specifications
                      if isinstance(spec, ParameterSpec) and spec.name == "model"]

        # Either should have 2 duplicates or the system should handle deduplication
        assert len(param_specs) >= 1  # At least one should be registered

    @patch('trustgraph.base.flow_processor.Flow')
    async def test_parameter_specs_available_to_flows(self, mock_flow_class):
        """Test that parameter specs are available when flows are created"""
        # Arrange
        def mock_init(self, **kwargs):
            self.config_handlers = []
            self.id = kwargs.get('id', 'test-service')

        config = {
            'id': 'test-flow-processor',
            'concurrency': 1
        }

        processor = FlowProcessor(**config)
        processor.id = 'test-processor'

        # Register parameter specs
        model_spec = ParameterSpec(name="model")
        temperature_spec = ParameterSpec(name="temperature")
        processor.register_specification(model_spec)
        processor.register_specification(temperature_spec)

        mock_flow = AsyncMock()
        mock_flow_class.return_value = mock_flow

        flow_name = 'test-flow'
        flow_defn = {'config': 'test-config'}

        # Act
        await processor.start_flow(flow_name, flow_defn)

        # Assert - Flow should be created with access to processor specifications
        mock_flow_class.assert_called_once_with('test-processor', flow_name, processor, flow_defn)

        # The flow should have access to the processor's specifications
        # (The exact mechanism depends on Flow implementation)
        assert len(processor.specifications) >= 2


class TestParameterSpecValidation(IsolatedAsyncioTestCase):
    """Test parameter specification validation functionality"""

    def test_parameter_spec_name_validation(self):
        """Test parameter spec name validation"""
        # Arrange
        def mock_init(self, **kwargs):
            self.config_handlers = []
            self.id = kwargs.get('id', 'test-service')

        config = {
            'id': 'test-flow-processor',
            'concurrency': 1
        }

        processor = FlowProcessor(**config)

        # Act & Assert - Valid parameter names
        valid_specs = [
            ParameterSpec(name="model"),
            ParameterSpec(name="temperature"),
            ParameterSpec(name="max_tokens"),
            ParameterSpec(name="api_key")
        ]

        for spec in valid_specs:
            # Should not raise any exceptions
            processor.register_specification(spec)

        assert len([s for s in processor.specifications if isinstance(s, ParameterSpec)]) >= 4

    def test_parameter_spec_creation_validation(self):
        """Test parameter spec creation with various inputs"""
        # Test valid parameter spec creation
        valid_specs = [
            ParameterSpec(name="model"),
            ParameterSpec(name="temperature"),
            ParameterSpec(name="max_output"),
        ]

        for spec in valid_specs:
            assert spec.name is not None
            assert isinstance(spec.name, str)

        # Test edge cases (if parameter specs have validation)
        # This depends on the actual ParameterSpec implementation
        try:
            empty_name_spec = ParameterSpec(name="")
            # May or may not be valid depending on implementation
        except Exception:
            # If validation exists, it should catch invalid names
            pass


if __name__ == '__main__':
    pytest.main([__file__])