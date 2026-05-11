"""
Unit tests for trustgraph.base.flow_processor
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

from trustgraph.base.flow_processor import FlowProcessor


# Patches needed to let AsyncProcessor.__init__ run without real
# infrastructure while still setting self.id correctly.
ASYNC_PROCESSOR_PATCHES = [
    patch('trustgraph.base.async_processor.get_pubsub', return_value=MagicMock()),
    patch('trustgraph.base.async_processor.ProcessorMetrics', return_value=MagicMock()),
    patch('trustgraph.base.async_processor.Consumer', return_value=MagicMock()),
]


def with_async_processor_patches(func):
    """Apply all AsyncProcessor dependency patches to a test."""
    for p in reversed(ASYNC_PROCESSOR_PATCHES):
        func = p(func)
    return func


class TestFlowProcessorSimple(IsolatedAsyncioTestCase):
    """Test FlowProcessor base class functionality"""

    @with_async_processor_patches
    async def test_flow_processor_initialization_basic(self, *mocks):
        """Test basic FlowProcessor initialization"""
        config = {
            'id': 'test-flow-processor',
            'taskgroup': AsyncMock()
        }

        processor = FlowProcessor(**config)

        assert processor.id == 'test-flow-processor'
        assert processor.flows == {}
        assert processor.specifications == []

    @with_async_processor_patches
    async def test_register_specification(self, *mocks):
        """Test registering a specification"""
        config = {
            'id': 'test-flow-processor',
            'taskgroup': AsyncMock()
        }

        processor = FlowProcessor(**config)
        mock_spec = MagicMock()
        mock_spec.name = 'test-spec'

        processor.register_specification(mock_spec)

        assert len(processor.specifications) == 1
        assert processor.specifications[0] == mock_spec

    @patch('trustgraph.base.flow_processor.Flow')
    @with_async_processor_patches
    async def test_start_flow(self, *mocks):
        """Test starting a flow"""
        mock_flow_class = mocks[-1]

        config = {
            'id': 'test-processor',
            'taskgroup': AsyncMock()
        }

        processor = FlowProcessor(**config)

        mock_flow = AsyncMock()
        mock_flow_class.return_value = mock_flow

        flow_name = 'test-flow'
        flow_defn = {'config': 'test-config'}

        await processor.start_flow("default", flow_name, flow_defn)

        assert ("default", flow_name) in processor.flows
        mock_flow_class.assert_called_once_with(
            'test-processor', flow_name, "default", processor, flow_defn
        )
        mock_flow.start.assert_called_once()

    @patch('trustgraph.base.flow_processor.Flow')
    @with_async_processor_patches
    async def test_stop_flow(self, *mocks):
        """Test stopping a flow"""
        mock_flow_class = mocks[-1]

        config = {
            'id': 'test-processor',
            'taskgroup': AsyncMock()
        }

        processor = FlowProcessor(**config)

        mock_flow = AsyncMock()
        mock_flow_class.return_value = mock_flow

        flow_name = 'test-flow'
        await processor.start_flow("default", flow_name, {'config': 'test-config'})

        await processor.stop_flow("default", flow_name)

        assert ("default", flow_name) not in processor.flows
        mock_flow.stop.assert_called_once()

    @with_async_processor_patches
    async def test_stop_flow_not_exists(self, *mocks):
        """Test stopping a flow that doesn't exist"""
        config = {
            'id': 'test-flow-processor',
            'taskgroup': AsyncMock()
        }

        processor = FlowProcessor(**config)

        await processor.stop_flow("default", 'non-existent-flow')

        assert processor.flows == {}

    @patch('trustgraph.base.flow_processor.Flow')
    @with_async_processor_patches
    async def test_on_configure_flows_basic(self, *mocks):
        """Test basic flow configuration handling"""
        mock_flow_class = mocks[-1]

        config = {
            'id': 'test-processor',
            'taskgroup': AsyncMock()
        }

        processor = FlowProcessor(**config)

        mock_flow = AsyncMock()
        mock_flow_class.return_value = mock_flow

        config_data = {
            'processor:test-processor': {
                'test-flow': '{"config": "test-config"}'
            }
        }

        await processor.on_configure_flows("default", config_data, version=1)

        assert ("default", 'test-flow') in processor.flows
        mock_flow_class.assert_called_once_with(
            'test-processor', 'test-flow', "default", processor,
            {'config': 'test-config'}
        )
        mock_flow.start.assert_called_once()

    @with_async_processor_patches
    async def test_on_configure_flows_no_config(self, *mocks):
        """Test flow configuration handling when no config exists for this processor"""
        config = {
            'id': 'test-processor',
            'taskgroup': AsyncMock()
        }

        processor = FlowProcessor(**config)

        config_data = {
            'processor:other-processor': {
                'other-flow': '{"config": "other-config"}'
            }
        }

        await processor.on_configure_flows("default", config_data, version=1)

        assert processor.flows == {}

    @with_async_processor_patches
    async def test_on_configure_flows_invalid_config(self, *mocks):
        """Test flow configuration handling with invalid config format"""
        config = {
            'id': 'test-processor',
            'taskgroup': AsyncMock()
        }

        processor = FlowProcessor(**config)

        config_data = {
            'other-data': 'some-value'
        }

        await processor.on_configure_flows("default", config_data, version=1)

        assert processor.flows == {}

    @patch('trustgraph.base.flow_processor.Flow')
    @with_async_processor_patches
    async def test_on_configure_flows_start_and_stop(self, *mocks):
        """Test flow configuration handling with starting and stopping flows"""
        mock_flow_class = mocks[-1]

        config = {
            'id': 'test-processor',
            'taskgroup': AsyncMock()
        }

        processor = FlowProcessor(**config)

        mock_flow1 = AsyncMock()
        mock_flow2 = AsyncMock()
        mock_flow_class.side_effect = [mock_flow1, mock_flow2]

        config_data1 = {
            'processor:test-processor': {
                'flow1': '{"config": "config1"}'
            }
        }

        await processor.on_configure_flows("default", config_data1, version=1)

        config_data2 = {
            'processor:test-processor': {
                'flow2': '{"config": "config2"}'
            }
        }

        await processor.on_configure_flows("default", config_data2, version=2)

        assert ("default", 'flow1') not in processor.flows
        mock_flow1.stop.assert_called_once()

        assert ("default", 'flow2') in processor.flows
        mock_flow2.start.assert_called_once()

    @with_async_processor_patches
    @patch('trustgraph.base.workspace_processor.WorkspaceProcessor.start')
    async def test_start_calls_parent(self, mock_parent_start, *mocks):
        """Test that start() calls parent start method"""
        mock_parent_start.return_value = None

        config = {
            'id': 'test-flow-processor',
            'taskgroup': AsyncMock()
        }

        processor = FlowProcessor(**config)

        await processor.start()

        mock_parent_start.assert_called_once()

    async def test_add_args_calls_parent(self):
        """Test that add_args() calls parent add_args method"""
        mock_parser = MagicMock()

        with patch('trustgraph.base.async_processor.AsyncProcessor.add_args') as mock_parent_add_args:
            FlowProcessor.add_args(mock_parser)

        mock_parent_add_args.assert_called_once_with(mock_parser)


if __name__ == '__main__':
    pytest.main([__file__])
