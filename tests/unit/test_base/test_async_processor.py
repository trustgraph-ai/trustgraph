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


if __name__ == '__main__':
    pytest.main([__file__])
