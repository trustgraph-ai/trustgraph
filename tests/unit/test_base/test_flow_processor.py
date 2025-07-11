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


if __name__ == '__main__':
    pytest.main([__file__])