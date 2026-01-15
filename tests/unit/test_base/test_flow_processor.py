"""
Unit tests for trustgraph.base.flow_processor
Starting small with a single test to verify basic functionality
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.base.flow_processor import FlowProcessor


class TestFlowProcessorSimple(IsolatedAsyncioTestCase):
    """Test FlowProcessor base class functionality"""

    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.async_processor.AsyncProcessor.register_config_handler')
    async def test_flow_processor_initialization_basic(self, mock_register_config, mock_async_init):
        """Test basic FlowProcessor initialization"""
        # Arrange
        mock_async_init.return_value = None
        mock_register_config.return_value = None
        
        config = {
            'id': 'test-flow-processor',
            'taskgroup': AsyncMock()
        }

        # Act
        processor = FlowProcessor(**config)

        # Assert
        # Verify AsyncProcessor.__init__ was called
        mock_async_init.assert_called_once()
        
        # Verify register_config_handler was called with the correct handler
        mock_register_config.assert_called_once_with(processor.on_configure_flows)
        
        # Verify FlowProcessor-specific initialization
        assert hasattr(processor, 'flows')
        assert processor.flows == {}
        assert hasattr(processor, 'specifications')
        assert processor.specifications == []

    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.async_processor.AsyncProcessor.register_config_handler')
    async def test_register_specification(self, mock_register_config, mock_async_init):
        """Test registering a specification"""
        # Arrange
        mock_async_init.return_value = None
        mock_register_config.return_value = None
        
        config = {
            'id': 'test-flow-processor',
            'taskgroup': AsyncMock()
        }

        processor = FlowProcessor(**config)
        mock_spec = MagicMock()
        mock_spec.name = 'test-spec'

        # Act
        processor.register_specification(mock_spec)

        # Assert
        assert len(processor.specifications) == 1
        assert processor.specifications[0] == mock_spec

    @patch('trustgraph.base.flow_processor.Flow')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.async_processor.AsyncProcessor.register_config_handler')
    async def test_start_flow(self, mock_register_config, mock_async_init, mock_flow_class):
        """Test starting a flow"""
        # Arrange
        mock_async_init.return_value = None
        mock_register_config.return_value = None
        
        config = {
            'id': 'test-flow-processor',
            'taskgroup': AsyncMock()
        }

        processor = FlowProcessor(**config)
        processor.id = 'test-processor'  # Set id for Flow creation
        
        mock_flow = AsyncMock()
        mock_flow_class.return_value = mock_flow
        
        flow_name = 'test-flow'
        flow_defn = {'config': 'test-config'}

        # Act
        await processor.start_flow(flow_name, flow_defn)

        # Assert
        assert flow_name in processor.flows
        # Verify Flow was created with correct parameters
        mock_flow_class.assert_called_once_with('test-processor', flow_name, processor, flow_defn)
        # Verify the flow's start method was called
        mock_flow.start.assert_called_once()

    @patch('trustgraph.base.flow_processor.Flow')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.async_processor.AsyncProcessor.register_config_handler')
    async def test_stop_flow(self, mock_register_config, mock_async_init, mock_flow_class):
        """Test stopping a flow"""
        # Arrange
        mock_async_init.return_value = None
        mock_register_config.return_value = None
        
        config = {
            'id': 'test-flow-processor',
            'taskgroup': AsyncMock()
        }

        processor = FlowProcessor(**config)
        processor.id = 'test-processor'
        
        mock_flow = AsyncMock()
        mock_flow_class.return_value = mock_flow
        
        flow_name = 'test-flow'
        flow_defn = {'config': 'test-config'}

        # Start a flow first
        await processor.start_flow(flow_name, flow_defn)
        
        # Act
        await processor.stop_flow(flow_name)

        # Assert
        assert flow_name not in processor.flows
        mock_flow.stop.assert_called_once()

    @patch('trustgraph.base.flow_processor.Flow')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.async_processor.AsyncProcessor.register_config_handler')
    async def test_stop_flow_not_exists(self, mock_register_config, mock_async_init, mock_flow_class):
        """Test stopping a flow that doesn't exist"""
        # Arrange
        mock_async_init.return_value = None
        mock_register_config.return_value = None
        
        config = {
            'id': 'test-flow-processor',
            'taskgroup': AsyncMock()
        }

        processor = FlowProcessor(**config)
        
        # Act - should not raise an exception
        await processor.stop_flow('non-existent-flow')

        # Assert - flows dict should still be empty
        assert processor.flows == {}

    @patch('trustgraph.base.flow_processor.Flow')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.async_processor.AsyncProcessor.register_config_handler')
    async def test_on_configure_flows_basic(self, mock_register_config, mock_async_init, mock_flow_class):
        """Test basic flow configuration handling"""
        # Arrange
        mock_async_init.return_value = None
        mock_register_config.return_value = None
        
        config = {
            'id': 'test-flow-processor',
            'taskgroup': AsyncMock()
        }

        processor = FlowProcessor(**config)
        processor.id = 'test-processor'
        
        mock_flow = AsyncMock()
        mock_flow_class.return_value = mock_flow
        
        # Configuration with flows for this processor
        flow_config = {
            'test-flow': {'config': 'test-config'}
        }
        config_data = {
            'active-flow': {
                'test-processor': '{"test-flow": {"config": "test-config"}}'
            }
        }
        
        # Act
        await processor.on_configure_flows(config_data, version=1)

        # Assert
        assert 'test-flow' in processor.flows
        mock_flow_class.assert_called_once_with('test-processor', 'test-flow', processor, {'config': 'test-config'})
        mock_flow.start.assert_called_once()

    @patch('trustgraph.base.flow_processor.Flow')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.async_processor.AsyncProcessor.register_config_handler')
    async def test_on_configure_flows_no_config(self, mock_register_config, mock_async_init, mock_flow_class):
        """Test flow configuration handling when no config exists for this processor"""
        # Arrange
        mock_async_init.return_value = None
        mock_register_config.return_value = None
        
        config = {
            'id': 'test-flow-processor',
            'taskgroup': AsyncMock()
        }

        processor = FlowProcessor(**config)
        processor.id = 'test-processor'
        
        # Configuration without flows for this processor
        config_data = {
            'active-flow': {
                'other-processor': '{"other-flow": {"config": "other-config"}}'
            }
        }
        
        # Act
        await processor.on_configure_flows(config_data, version=1)

        # Assert
        assert processor.flows == {}
        mock_flow_class.assert_not_called()

    @patch('trustgraph.base.flow_processor.Flow')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.async_processor.AsyncProcessor.register_config_handler')
    async def test_on_configure_flows_invalid_config(self, mock_register_config, mock_async_init, mock_flow_class):
        """Test flow configuration handling with invalid config format"""
        # Arrange
        mock_async_init.return_value = None
        mock_register_config.return_value = None
        
        config = {
            'id': 'test-flow-processor',
            'taskgroup': AsyncMock()
        }

        processor = FlowProcessor(**config)
        processor.id = 'test-processor'
        
        # Configuration without active-flow key
        config_data = {
            'other-data': 'some-value'
        }
        
        # Act
        await processor.on_configure_flows(config_data, version=1)

        # Assert
        assert processor.flows == {}
        mock_flow_class.assert_not_called()

    @patch('trustgraph.base.flow_processor.Flow')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.async_processor.AsyncProcessor.register_config_handler')
    async def test_on_configure_flows_start_and_stop(self, mock_register_config, mock_async_init, mock_flow_class):
        """Test flow configuration handling with starting and stopping flows"""
        # Arrange
        mock_async_init.return_value = None
        mock_register_config.return_value = None
        
        config = {
            'id': 'test-flow-processor',
            'taskgroup': AsyncMock()
        }

        processor = FlowProcessor(**config)
        processor.id = 'test-processor'
        
        mock_flow1 = AsyncMock()
        mock_flow2 = AsyncMock()
        mock_flow_class.side_effect = [mock_flow1, mock_flow2]
        
        # First configuration - start flow1
        config_data1 = {
            'active-flow': {
                'test-processor': '{"flow1": {"config": "config1"}}'
            }
        }

        await processor.on_configure_flows(config_data1, version=1)

        # Second configuration - stop flow1, start flow2
        config_data2 = {
            'active-flow': {
                'test-processor': '{"flow2": {"config": "config2"}}'
            }
        }
        
        # Act
        await processor.on_configure_flows(config_data2, version=2)

        # Assert
        # flow1 should be stopped and removed
        assert 'flow1' not in processor.flows
        mock_flow1.stop.assert_called_once()
        
        # flow2 should be started and added
        assert 'flow2' in processor.flows
        mock_flow2.start.assert_called_once()

    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.async_processor.AsyncProcessor.register_config_handler')
    @patch('trustgraph.base.async_processor.AsyncProcessor.start')
    async def test_start_calls_parent(self, mock_parent_start, mock_register_config, mock_async_init):
        """Test that start() calls parent start method"""
        # Arrange
        mock_async_init.return_value = None
        mock_register_config.return_value = None
        mock_parent_start.return_value = None
        
        config = {
            'id': 'test-flow-processor',
            'taskgroup': AsyncMock()
        }

        processor = FlowProcessor(**config)
        
        # Act
        await processor.start()

        # Assert
        mock_parent_start.assert_called_once()

    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.async_processor.AsyncProcessor.register_config_handler')
    async def test_add_args_calls_parent(self, mock_register_config, mock_async_init):
        """Test that add_args() calls parent add_args method"""
        # Arrange
        mock_async_init.return_value = None
        mock_register_config.return_value = None
        
        mock_parser = MagicMock()
        
        # Act
        with patch('trustgraph.base.async_processor.AsyncProcessor.add_args') as mock_parent_add_args:
            FlowProcessor.add_args(mock_parser)

        # Assert
        mock_parent_add_args.assert_called_once_with(mock_parser)


if __name__ == '__main__':
    pytest.main([__file__])