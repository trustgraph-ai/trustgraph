"""
Unit tests for trustgraph.base.async_processor
Starting small with a single test to verify basic functionality
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.base.async_processor import AsyncProcessor


class TestAsyncProcessorSimple(IsolatedAsyncioTestCase):
    """Test AsyncProcessor base class functionality"""

    @patch('trustgraph.base.async_processor.PulsarClient')
    @patch('trustgraph.base.async_processor.Consumer')
    @patch('trustgraph.base.async_processor.ProcessorMetrics')
    @patch('trustgraph.base.async_processor.ConsumerMetrics')
    async def test_async_processor_initialization_basic(self, mock_consumer_metrics, mock_processor_metrics, 
                                                       mock_consumer, mock_pulsar_client):
        """Test basic AsyncProcessor initialization"""
        # Arrange
        mock_pulsar_client.return_value = MagicMock()
        mock_consumer.return_value = MagicMock()
        mock_processor_metrics.return_value = MagicMock()
        mock_consumer_metrics.return_value = MagicMock()
        
        config = {
            'id': 'test-async-processor',
            'taskgroup': AsyncMock()
        }

        # Act
        processor = AsyncProcessor(**config)

        # Assert
        # Verify basic attributes are set
        assert processor.id == 'test-async-processor'
        assert processor.taskgroup == config['taskgroup']
        assert processor.running == True
        assert hasattr(processor, 'config_handlers')
        assert processor.config_handlers == []
        
        # Verify PulsarClient was created
        mock_pulsar_client.assert_called_once_with(**config)
        
        # Verify metrics were initialized
        mock_processor_metrics.assert_called_once()
        mock_consumer_metrics.assert_called_once()
        
        # Verify Consumer was created for config subscription
        mock_consumer.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__])