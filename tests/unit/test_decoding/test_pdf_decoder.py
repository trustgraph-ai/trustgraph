"""
Unit tests for trustgraph.decoding.pdf.pdf_decoder
"""

import pytest
import base64
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch, call
from unittest import IsolatedAsyncioTestCase

from trustgraph.decoding.pdf.pdf_decoder import Processor
from trustgraph.schema import Document, TextDocument, Metadata


class MockAsyncProcessor:
    def __init__(self, **params):
        self.config_handlers = []
        self.id = params.get('id', 'test-service')
        self.specifications = []
        self.pubsub = MagicMock()
        self.taskgroup = params.get('taskgroup', MagicMock())


class TestPdfDecoderProcessor(IsolatedAsyncioTestCase):
    """Test PDF decoder processor functionality"""

    @patch('trustgraph.base.chunking_service.Consumer')
    @patch('trustgraph.base.chunking_service.Producer')
    @patch('trustgraph.decoding.pdf.pdf_decoder.Consumer')
    @patch('trustgraph.decoding.pdf.pdf_decoder.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_processor_initialization(self, mock_producer, mock_consumer, mock_cs_producer, mock_cs_consumer):
        """Test PDF decoder processor initialization"""
        config = {
            'id': 'test-pdf-decoder',
            'taskgroup': AsyncMock()
        }

        processor = Processor(**config)

        # Check consumer spec
        consumer_specs = [s for s in processor.specifications if hasattr(s, 'handler')]
        assert len(consumer_specs) >= 1
        assert consumer_specs[0].name == "input"
        assert consumer_specs[0].schema == Document

    @patch('trustgraph.base.chunking_service.Consumer')
    @patch('trustgraph.base.chunking_service.Producer')
    @patch('trustgraph.decoding.pdf.pdf_decoder.Consumer')
    @patch('trustgraph.decoding.pdf.pdf_decoder.Producer')
    @patch('trustgraph.decoding.pdf.pdf_decoder.PyPDFLoader')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_on_message_success(self, mock_pdf_loader_class, mock_producer, mock_consumer, mock_cs_producer, mock_cs_consumer):
        """Test successful PDF processing"""
        # Mock PDF content
        pdf_content = b"fake pdf content"
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

        # Mock PyPDFLoader
        mock_loader = MagicMock()
        mock_page1 = MagicMock(page_content="Page 1 content")
        mock_page2 = MagicMock(page_content="Page 2 content")
        mock_loader.load.return_value = [mock_page1, mock_page2]
        mock_pdf_loader_class.return_value = mock_loader

        # Mock message
        mock_metadata = Metadata(id="test-doc")
        mock_document = Document(metadata=mock_metadata, data=pdf_base64)
        mock_msg = MagicMock()
        mock_msg.value.return_value = mock_document

        # Mock flow
        mock_output_flow = AsyncMock()
        mock_flow = MagicMock(return_value=mock_output_flow)

        config = {
            'id': 'test-pdf-decoder',
            'taskgroup': AsyncMock()
        }

        processor = Processor(**config)

        await processor.on_message(mock_msg, None, mock_flow)

        # Verify output was sent for each page
        assert mock_output_flow.send.call_count == 2

    @patch('trustgraph.base.chunking_service.Consumer')
    @patch('trustgraph.base.chunking_service.Producer')
    @patch('trustgraph.decoding.pdf.pdf_decoder.Consumer')
    @patch('trustgraph.decoding.pdf.pdf_decoder.Producer')
    @patch('trustgraph.decoding.pdf.pdf_decoder.PyPDFLoader')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_on_message_empty_pdf(self, mock_pdf_loader_class, mock_producer, mock_consumer, mock_cs_producer, mock_cs_consumer):
        """Test handling of empty PDF"""
        pdf_content = b"fake pdf content"
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

        mock_loader = MagicMock()
        mock_loader.load.return_value = []
        mock_pdf_loader_class.return_value = mock_loader

        mock_metadata = Metadata(id="test-doc")
        mock_document = Document(metadata=mock_metadata, data=pdf_base64)
        mock_msg = MagicMock()
        mock_msg.value.return_value = mock_document

        mock_output_flow = AsyncMock()
        mock_flow = MagicMock(return_value=mock_output_flow)

        config = {
            'id': 'test-pdf-decoder',
            'taskgroup': AsyncMock()
        }

        processor = Processor(**config)

        await processor.on_message(mock_msg, None, mock_flow)

        mock_output_flow.send.assert_not_called()

    @patch('trustgraph.base.chunking_service.Consumer')
    @patch('trustgraph.base.chunking_service.Producer')
    @patch('trustgraph.decoding.pdf.pdf_decoder.Consumer')
    @patch('trustgraph.decoding.pdf.pdf_decoder.Producer')
    @patch('trustgraph.decoding.pdf.pdf_decoder.PyPDFLoader')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_on_message_unicode_content(self, mock_pdf_loader_class, mock_producer, mock_consumer, mock_cs_producer, mock_cs_consumer):
        """Test handling of unicode content in PDF"""
        pdf_content = b"fake pdf content"
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

        mock_loader = MagicMock()
        mock_page = MagicMock(page_content="Page with unicode: 你好世界 🌍")
        mock_loader.load.return_value = [mock_page]
        mock_pdf_loader_class.return_value = mock_loader

        mock_metadata = Metadata(id="test-doc")
        mock_document = Document(metadata=mock_metadata, data=pdf_base64)
        mock_msg = MagicMock()
        mock_msg.value.return_value = mock_document

        mock_output_flow = AsyncMock()
        mock_flow = MagicMock(return_value=mock_output_flow)

        config = {
            'id': 'test-pdf-decoder',
            'taskgroup': AsyncMock()
        }

        processor = Processor(**config)

        await processor.on_message(mock_msg, None, mock_flow)

        mock_output_flow.send.assert_called_once()
        call_args = mock_output_flow.send.call_args[0][0]
        assert call_args.text == "Page with unicode: 你好世界 🌍".encode('utf-8')

    @patch('trustgraph.base.flow_processor.FlowProcessor.add_args')
    def test_add_args(self, mock_parent_add_args):
        """Test add_args calls parent method"""
        mock_parser = MagicMock()
        Processor.add_args(mock_parser)
        mock_parent_add_args.assert_called_once_with(mock_parser)

    @patch('trustgraph.decoding.pdf.pdf_decoder.Processor.launch')
    def test_run(self, mock_launch):
        """Test run function"""
        from trustgraph.decoding.pdf.pdf_decoder import run
        run()
        mock_launch.assert_called_once_with("pdf-decoder",
            "\nSimple decoder, accepts PDF documents on input, outputs pages from the\nPDF document as text as separate output objects.\n\nSupports both inline document data and fetching from librarian via Pulsar\nfor large documents.\n")


if __name__ == '__main__':
    pytest.main([__file__])
