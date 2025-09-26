"""
Unit tests for trustgraph.chunking.token
Testing parameter override functionality for chunk-size and chunk-overlap
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

# Import the service under test
from trustgraph.chunking.token.chunker import Processor
from trustgraph.schema import TextDocument, Chunk


class MockAsyncProcessor:
    def __init__(self, **params):
        self.config_handlers = []
        self.id = params.get('id', 'test-service')
        self.specifications = []


class TestTokenChunkerSimple(IsolatedAsyncioTestCase):
    """Test Token chunker functionality"""

    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    def test_processor_initialization_basic(self):
        """Test basic processor initialization"""
        # Arrange
        config = {
            'id': 'test-chunker',
            'chunk_size': 300,
            'chunk_overlap': 20,
            'concurrency': 1,
            'taskgroup': AsyncMock()
        }

        # Act
        processor = Processor(**config)

        # Assert
        assert processor.default_chunk_size == 300
        assert processor.default_chunk_overlap == 20
        assert hasattr(processor, 'text_splitter')

        # Verify parameter specs are registered
        param_specs = [spec for spec in processor.specifications
                      if hasattr(spec, 'name') and spec.name in ['chunk-size', 'chunk-overlap']]
        assert len(param_specs) == 2

    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_chunk_document_with_chunk_size_override(self):
        """Test chunk_document with chunk-size parameter override"""
        # Arrange
        config = {
            'id': 'test-chunker',
            'chunk_size': 250,  # Default chunk size
            'chunk_overlap': 15,
            'concurrency': 1,
            'taskgroup': AsyncMock()
        }

        processor = Processor(**config)

        # Mock message and flow
        mock_message = MagicMock()
        mock_consumer = MagicMock()
        mock_flow = MagicMock()
        mock_flow.side_effect = lambda param: {
            "chunk-size": 400,  # Override chunk size
            "chunk-overlap": None  # Use default chunk overlap
        }.get(param)

        # Act
        chunk_size, chunk_overlap = await processor.chunk_document(
            mock_message, mock_consumer, mock_flow, 250, 15
        )

        # Assert
        assert chunk_size == 400  # Should use overridden value
        assert chunk_overlap == 15  # Should use default value

    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_chunk_document_with_chunk_overlap_override(self):
        """Test chunk_document with chunk-overlap parameter override"""
        # Arrange
        config = {
            'id': 'test-chunker',
            'chunk_size': 250,
            'chunk_overlap': 15,  # Default chunk overlap
            'concurrency': 1,
            'taskgroup': AsyncMock()
        }

        processor = Processor(**config)

        # Mock message and flow
        mock_message = MagicMock()
        mock_consumer = MagicMock()
        mock_flow = MagicMock()
        mock_flow.side_effect = lambda param: {
            "chunk-size": None,  # Use default chunk size
            "chunk-overlap": 25  # Override chunk overlap
        }.get(param)

        # Act
        chunk_size, chunk_overlap = await processor.chunk_document(
            mock_message, mock_consumer, mock_flow, 250, 15
        )

        # Assert
        assert chunk_size == 250  # Should use default value
        assert chunk_overlap == 25  # Should use overridden value

    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_chunk_document_with_both_parameters_override(self):
        """Test chunk_document with both chunk-size and chunk-overlap overrides"""
        # Arrange
        config = {
            'id': 'test-chunker',
            'chunk_size': 250,
            'chunk_overlap': 15,
            'concurrency': 1,
            'taskgroup': AsyncMock()
        }

        processor = Processor(**config)

        # Mock message and flow
        mock_message = MagicMock()
        mock_consumer = MagicMock()
        mock_flow = MagicMock()
        mock_flow.side_effect = lambda param: {
            "chunk-size": 350,    # Override chunk size
            "chunk-overlap": 30   # Override chunk overlap
        }.get(param)

        # Act
        chunk_size, chunk_overlap = await processor.chunk_document(
            mock_message, mock_consumer, mock_flow, 250, 15
        )

        # Assert
        assert chunk_size == 350   # Should use overridden value
        assert chunk_overlap == 30 # Should use overridden value

    @patch('trustgraph.chunking.token.chunker.TokenTextSplitter')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_on_message_uses_flow_parameters(self, mock_splitter_class):
        """Test that on_message method uses parameters from flow"""
        # Arrange
        mock_splitter = MagicMock()
        mock_document = MagicMock()
        mock_document.page_content = "Test token chunk content"
        mock_splitter.create_documents.return_value = [mock_document]
        mock_splitter_class.return_value = mock_splitter

        config = {
            'id': 'test-chunker',
            'chunk_size': 250,
            'chunk_overlap': 15,
            'concurrency': 1,
            'taskgroup': AsyncMock()
        }

        processor = Processor(**config)

        # Mock message with TextDocument
        mock_message = MagicMock()
        mock_text_doc = MagicMock()
        mock_text_doc.metadata.id = "test-doc-456"
        mock_text_doc.text = b"This is test document content for token chunking"
        mock_message.value.return_value = mock_text_doc

        # Mock consumer and flow with parameter overrides
        mock_consumer = MagicMock()
        mock_flow = MagicMock()
        mock_flow.side_effect = lambda param: {
            "chunk-size": 400,
            "chunk-overlap": 40
        }.get(param)

        mock_producer = AsyncMock()
        mock_flow.return_value = mock_producer

        # Act
        await processor.on_message(mock_message, mock_consumer, mock_flow)

        # Assert
        # Verify TokenTextSplitter was created with overridden parameters
        mock_splitter_class.assert_called_once_with(
            encoding_name="cl100k_base",
            chunk_size=400,
            chunk_overlap=40,
        )

        # Verify chunk was sent to output
        mock_producer.send.assert_called_once()
        sent_chunk = mock_producer.send.call_args[0][0]
        assert isinstance(sent_chunk, Chunk)

    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_chunk_document_with_no_overrides(self):
        """Test chunk_document when no parameters are overridden (flow returns None)"""
        # Arrange
        config = {
            'id': 'test-chunker',
            'chunk_size': 250,
            'chunk_overlap': 15,
            'concurrency': 1,
            'taskgroup': AsyncMock()
        }

        processor = Processor(**config)

        # Mock message and flow that returns None for all parameters
        mock_message = MagicMock()
        mock_consumer = MagicMock()
        mock_flow = MagicMock()
        mock_flow.return_value = None  # No overrides

        # Act
        chunk_size, chunk_overlap = await processor.chunk_document(
            mock_message, mock_consumer, mock_flow, 250, 15
        )

        # Assert
        assert chunk_size == 250   # Should use default value
        assert chunk_overlap == 15 # Should use default value

    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    def test_token_chunker_uses_different_defaults(self):
        """Test that token chunker has different defaults than recursive chunker"""
        # Arrange & Act
        config = {
            'id': 'test-chunker',
            'concurrency': 1,
            'taskgroup': AsyncMock()
        }

        processor = Processor(**config)

        # Assert - Token chunker should have different defaults
        assert processor.default_chunk_size == 250   # Token chunker default
        assert processor.default_chunk_overlap == 15  # Token chunker default


if __name__ == '__main__':
    pytest.main([__file__])