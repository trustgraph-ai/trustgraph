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


class TestPdfDecoderProcessor(IsolatedAsyncioTestCase):
    """Test PDF decoder processor functionality"""

    @patch('trustgraph.base.flow_processor.FlowProcessor.__init__')
    async def test_processor_initialization(self, mock_flow_init):
        """Test PDF decoder processor initialization"""
        # Arrange
        mock_flow_init.return_value = None
        
        config = {
            'id': 'test-pdf-decoder',
            'taskgroup': AsyncMock()
        }

        # Act
        with patch.object(Processor, 'register_specification') as mock_register:
            processor = Processor(**config)

        # Assert
        mock_flow_init.assert_called_once()
        # Verify register_specification was called twice (consumer and producer)
        assert mock_register.call_count == 2
        
        # Check consumer spec
        consumer_call = mock_register.call_args_list[0]
        consumer_spec = consumer_call[0][0]
        assert consumer_spec.name == "input"
        assert consumer_spec.schema == Document
        assert consumer_spec.handler == processor.on_message
        
        # Check producer spec
        producer_call = mock_register.call_args_list[1]
        producer_spec = producer_call[0][0]
        assert producer_spec.name == "output"
        assert producer_spec.schema == TextDocument

    @patch('trustgraph.decoding.pdf.pdf_decoder.PyPDFLoader')
    @patch('trustgraph.base.flow_processor.FlowProcessor.__init__')
    async def test_on_message_success(self, mock_flow_init, mock_pdf_loader_class):
        """Test successful PDF processing"""
        # Arrange
        mock_flow_init.return_value = None
        
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
        
        # Mock flow - needs to be a callable that returns an object with send method
        mock_output_flow = AsyncMock()
        mock_flow = MagicMock(return_value=mock_output_flow)
        
        config = {
            'id': 'test-pdf-decoder',
            'taskgroup': AsyncMock()
        }

        with patch.object(Processor, 'register_specification'):
            processor = Processor(**config)

        # Act
        await processor.on_message(mock_msg, None, mock_flow)

        # Assert
        # Verify PyPDFLoader was called
        mock_pdf_loader_class.assert_called_once()
        mock_loader.load.assert_called_once()
        
        # Verify output was sent for each page
        assert mock_output_flow.send.call_count == 2
        
        # Check first page output
        first_call = mock_output_flow.send.call_args_list[0]
        first_output = first_call[0][0]
        assert isinstance(first_output, TextDocument)
        assert first_output.metadata == mock_metadata
        assert first_output.text == b"Page 1 content"
        
        # Check second page output
        second_call = mock_output_flow.send.call_args_list[1]
        second_output = second_call[0][0]
        assert isinstance(second_output, TextDocument)
        assert second_output.metadata == mock_metadata
        assert second_output.text == b"Page 2 content"

    @patch('trustgraph.decoding.pdf.pdf_decoder.PyPDFLoader')
    @patch('trustgraph.base.flow_processor.FlowProcessor.__init__')
    async def test_on_message_empty_pdf(self, mock_flow_init, mock_pdf_loader_class):
        """Test handling of empty PDF"""
        # Arrange
        mock_flow_init.return_value = None
        
        # Mock PDF content
        pdf_content = b"fake pdf content"
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        
        # Mock PyPDFLoader with no pages
        mock_loader = MagicMock()
        mock_loader.load.return_value = []
        mock_pdf_loader_class.return_value = mock_loader
        
        # Mock message
        mock_metadata = Metadata(id="test-doc")
        mock_document = Document(metadata=mock_metadata, data=pdf_base64)
        mock_msg = MagicMock()
        mock_msg.value.return_value = mock_document
        
        # Mock flow - needs to be a callable that returns an object with send method
        mock_output_flow = AsyncMock()
        mock_flow = MagicMock(return_value=mock_output_flow)
        
        config = {
            'id': 'test-pdf-decoder',
            'taskgroup': AsyncMock()
        }

        with patch.object(Processor, 'register_specification'):
            processor = Processor(**config)

        # Act
        await processor.on_message(mock_msg, None, mock_flow)

        # Assert
        # Verify PyPDFLoader was called
        mock_pdf_loader_class.assert_called_once()
        mock_loader.load.assert_called_once()
        
        # Verify no output was sent
        mock_output_flow.send.assert_not_called()

    @patch('trustgraph.decoding.pdf.pdf_decoder.PyPDFLoader')
    @patch('trustgraph.base.flow_processor.FlowProcessor.__init__')
    async def test_on_message_unicode_content(self, mock_flow_init, mock_pdf_loader_class):
        """Test handling of unicode content in PDF"""
        # Arrange
        mock_flow_init.return_value = None
        
        # Mock PDF content
        pdf_content = b"fake pdf content"
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        
        # Mock PyPDFLoader with unicode content
        mock_loader = MagicMock()
        mock_page = MagicMock(page_content="Page with unicode: 你好世界 🌍")
        mock_loader.load.return_value = [mock_page]
        mock_pdf_loader_class.return_value = mock_loader
        
        # Mock message
        mock_metadata = Metadata(id="test-doc")
        mock_document = Document(metadata=mock_metadata, data=pdf_base64)
        mock_msg = MagicMock()
        mock_msg.value.return_value = mock_document
        
        # Mock flow - needs to be a callable that returns an object with send method
        mock_output_flow = AsyncMock()
        mock_flow = MagicMock(return_value=mock_output_flow)
        
        config = {
            'id': 'test-pdf-decoder',
            'taskgroup': AsyncMock()
        }

        with patch.object(Processor, 'register_specification'):
            processor = Processor(**config)

        # Act
        await processor.on_message(mock_msg, None, mock_flow)

        # Assert
        # Verify output was sent
        mock_output_flow.send.assert_called_once()
        
        # Check output
        call_args = mock_output_flow.send.call_args[0][0]
        assert isinstance(call_args, TextDocument)
        assert call_args.text == "Page with unicode: 你好世界 🌍".encode('utf-8')

    @patch('trustgraph.base.flow_processor.FlowProcessor.add_args')
    def test_add_args(self, mock_parent_add_args):
        """Test add_args calls parent method"""
        # Arrange
        mock_parser = MagicMock()
        
        # Act
        Processor.add_args(mock_parser)
        
        # Assert
        mock_parent_add_args.assert_called_once_with(mock_parser)

    @patch('trustgraph.decoding.pdf.pdf_decoder.Processor.launch')
    def test_run(self, mock_launch):
        """Test run function"""
        # Act
        from trustgraph.decoding.pdf.pdf_decoder import run
        run()
        
        # Assert
        mock_launch.assert_called_once_with("pdf-decoder", 
            "\nSimple decoder, accepts PDF documents on input, outputs pages from the\nPDF document as text as separate output objects.\n")


if __name__ == '__main__':
    pytest.main([__file__])