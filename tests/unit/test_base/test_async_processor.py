"""
Unit tests for trustgraph.base.async_processor
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

from trustgraph.base.async_processor import AsyncProcessor


class TestAsyncProcessorSimple(IsolatedAsyncioTestCase):
    """Test AsyncProcessor base class functionality"""

    @patch('trustgraph.base.async_processor.get_async_pubsub')
    async def test_async_processor_initialization_basic(
        self, mock_get_pubsub,
    ):
        """Test basic AsyncProcessor initialization"""
        mock_backend = MagicMock()
        mock_get_pubsub.return_value = mock_backend

        config = {
            'id': 'test-async-processor',
            'taskgroup': AsyncMock()
        }

        processor = AsyncProcessor(**config)

        assert processor.id == 'test-async-processor'
        assert processor.taskgroup == config['taskgroup']
        assert processor.running == True
        assert hasattr(processor, 'config_handlers')
        assert processor.config_handlers == []

        mock_get_pubsub.assert_called_once_with(**config)

    @patch('trustgraph.base.async_processor.get_async_pubsub')
    async def test_async_processor_config_queue_overrides(
        self, mock_get_pubsub,
    ):
        """Test --config-push-queue, --config-request-queue, and --config-response-queue overrides"""
        import argparse
        mock_get_pubsub.return_value = MagicMock()

        parser = argparse.ArgumentParser()
        AsyncProcessor.add_args(parser)
        args = parser.parse_args([
            '--config-push-queue', 'persistent://tg-dev/config/push',
            '--config-request-queue', 'persistent://tg-dev/config/req',
            '--config-response-queue', 'persistent://tg-dev/config/resp',
        ])
        assert args.config_push_queue == 'persistent://tg-dev/config/push'
        assert args.config_request_queue == 'persistent://tg-dev/config/req'
        assert args.config_response_queue == 'persistent://tg-dev/config/resp'

        processor = AsyncProcessor(
            id='test-proc',
            taskgroup=AsyncMock(),
            config_push_queue='persistent://tg-dev/config/push',
            config_request_queue='persistent://tg-dev/config/req',
            config_response_queue='persistent://tg-dev/config/resp',
        )
        assert processor.config_push_queue == 'persistent://tg-dev/config/push'
        assert processor.config_request_queue == 'persistent://tg-dev/config/req'
        assert processor.config_response_queue == 'persistent://tg-dev/config/resp'


if __name__ == '__main__':
    pytest.main([__file__])
