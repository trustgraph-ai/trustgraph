"""
Unit tests for trustgraph.decoding.mistral_ocr.processor
"""

import pytest
import base64
import uuid
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from unittest import IsolatedAsyncioTestCase
from io import BytesIO

from trustgraph.decoding.mistral_ocr.processor import Processor
from trustgraph.schema import Document, TextDocument, Metadata


class TestMistralOcrProcessor(IsolatedAsyncioTestCase):
    """Test Mistral OCR processor functionality"""

    @patch('trustgraph.decoding.mistral_ocr.processor.Mistral')
    @patch('trustgraph.base.flow_processor.FlowProcessor.__init__')
    async def test_processor_initialization_with_api_key(self, mock_flow_init, mock_mistral_class):
        """Test Mistral OCR processor initialization with API key"""
        # Arrange
        mock_flow_init.return_value = None
        mock_mistral = MagicMock()
        mock_mistral_class.return_value = mock_mistral
        
        config = {
            'id': 'test-mistral-ocr',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock()
        }

        # Act
        with patch.object(Processor, 'register_specification') as mock_register:
            processor = Processor(**config)

        # Assert
        mock_flow_init.assert_called_once()
        mock_mistral_class.assert_called_once_with(api_key='test-api-key')
        
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

    @patch('trustgraph.base.flow_processor.FlowProcessor.__init__')
    async def test_processor_initialization_without_api_key(self, mock_flow_init):
        """Test Mistral OCR processor initialization without API key raises error"""
        # Arrange
        mock_flow_init.return_value = None
        
        config = {
            'id': 'test-mistral-ocr',
            'taskgroup': AsyncMock()
        }

        # Act & Assert
        with patch.object(Processor, 'register_specification'):
            with pytest.raises(RuntimeError, match="Mistral API key not specified"):
                processor = Processor(**config)

    @patch('trustgraph.decoding.mistral_ocr.processor.uuid.uuid4')
    @patch('trustgraph.decoding.mistral_ocr.processor.Mistral')
    @patch('trustgraph.base.flow_processor.FlowProcessor.__init__')
    async def test_ocr_single_chunk(self, mock_flow_init, mock_mistral_class, mock_uuid):
        """Test OCR processing with a single chunk (less than 5 pages)"""
        # Arrange
        mock_flow_init.return_value = None
        mock_uuid.return_value = "test-uuid-1234"
        
        # Mock Mistral client
        mock_mistral = MagicMock()
        mock_mistral_class.return_value = mock_mistral
        
        # Mock file upload
        mock_uploaded_file = MagicMock(id="file-123")
        mock_mistral.files.upload.return_value = mock_uploaded_file
        
        # Mock signed URL
        mock_signed_url = MagicMock(url="https://example.com/signed-url")
        mock_mistral.files.get_signed_url.return_value = mock_signed_url
        
        # Mock OCR response
        mock_page = MagicMock(
            markdown="# Page 1\nContent ![img1](img1)",
            images=[MagicMock(id="img1", image_base64="data:image/png;base64,abc123")]
        )
        mock_ocr_response = MagicMock(pages=[mock_page])
        mock_mistral.ocr.process.return_value = mock_ocr_response
        
        # Mock PyPDF
        mock_pdf_reader = MagicMock()
        mock_pdf_reader.pages = [MagicMock(), MagicMock(), MagicMock()]  # 3 pages
        
        config = {
            'id': 'test-mistral-ocr',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock()
        }

        with patch.object(Processor, 'register_specification'):
            with patch('trustgraph.decoding.mistral_ocr.processor.PdfReader', return_value=mock_pdf_reader):
                with patch('trustgraph.decoding.mistral_ocr.processor.PdfWriter') as mock_pdf_writer_class:
                    mock_pdf_writer = MagicMock()
                    mock_pdf_writer_class.return_value = mock_pdf_writer
                    
                    processor = Processor(**config)
                    
                    # Act
                    result = processor.ocr(b"fake pdf content")

        # Assert
        assert result == "# Page 1\nContent ![img1](data:image/png;base64,abc123)"
        
        # Verify PDF writer was used to create chunk
        assert mock_pdf_writer.add_page.call_count == 3
        mock_pdf_writer.write_stream.assert_called_once()
        
        # Verify Mistral API calls
        mock_mistral.files.upload.assert_called_once()
        upload_call = mock_mistral.files.upload.call_args[1]
        assert upload_call['file']['file_name'] == "test-uuid-1234"
        assert upload_call['purpose'] == 'ocr'
        
        mock_mistral.files.get_signed_url.assert_called_once_with(
            file_id="file-123", expiry=1
        )
        
        mock_mistral.ocr.process.assert_called_once_with(
            model="mistral-ocr-latest",
            include_image_base64=True,
            document={
                "type": "document_url",
                "document_url": "https://example.com/signed-url",
            }
        )

    @patch('trustgraph.decoding.mistral_ocr.processor.uuid.uuid4')
    @patch('trustgraph.decoding.mistral_ocr.processor.Mistral')
    @patch('trustgraph.base.flow_processor.FlowProcessor.__init__')
    async def test_on_message_success(self, mock_flow_init, mock_mistral_class, mock_uuid):
        """Test successful message processing"""
        # Arrange
        mock_flow_init.return_value = None
        mock_uuid.return_value = "test-uuid-5678"
        
        # Mock Mistral client with simple OCR response
        mock_mistral = MagicMock()
        mock_mistral_class.return_value = mock_mistral
        
        # Mock the ocr method to return simple markdown
        ocr_result = "# Document Title\nThis is the OCR content"
        
        # Mock message
        pdf_content = b"fake pdf content"
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        mock_metadata = Metadata(id="test-doc")
        mock_document = Document(metadata=mock_metadata, data=pdf_base64)
        mock_msg = MagicMock()
        mock_msg.value.return_value = mock_document
        
        # Mock flow - needs to be a callable that returns an object with send method
        mock_output_flow = AsyncMock()
        mock_flow = MagicMock(return_value=mock_output_flow)
        
        config = {
            'id': 'test-mistral-ocr',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock()
        }

        with patch.object(Processor, 'register_specification'):
            processor = Processor(**config)
            
            # Mock the ocr method
            with patch.object(processor, 'ocr', return_value=ocr_result):
                # Act
                await processor.on_message(mock_msg, None, mock_flow)

        # Assert
        # Verify output was sent
        mock_output_flow.send.assert_called_once()
        
        # Check output
        call_args = mock_output_flow.send.call_args[0][0]
        assert isinstance(call_args, TextDocument)
        assert call_args.metadata == mock_metadata
        assert call_args.text == ocr_result.encode('utf-8')

    @patch('trustgraph.decoding.mistral_ocr.processor.Mistral')
    @patch('trustgraph.base.flow_processor.FlowProcessor.__init__')
    async def test_chunks_function(self, mock_flow_init, mock_mistral_class):
        """Test the chunks utility function"""
        # Arrange
        from trustgraph.decoding.mistral_ocr.processor import chunks
        
        test_list = list(range(12))
        
        # Act
        result = list(chunks(test_list, 5))
        
        # Assert
        assert len(result) == 3
        assert result[0] == [0, 1, 2, 3, 4]
        assert result[1] == [5, 6, 7, 8, 9]
        assert result[2] == [10, 11]

    @patch('trustgraph.decoding.mistral_ocr.processor.Mistral')
    @patch('trustgraph.base.flow_processor.FlowProcessor.__init__')
    async def test_replace_images_in_markdown(self, mock_flow_init, mock_mistral_class):
        """Test the replace_images_in_markdown function"""
        # Arrange
        from trustgraph.decoding.mistral_ocr.processor import replace_images_in_markdown
        
        markdown = "# Title\n![image1](image1)\nSome text\n![image2](image2)"
        images_dict = {
            "image1": "data:image/png;base64,abc123",
            "image2": "data:image/png;base64,def456"
        }
        
        # Act
        result = replace_images_in_markdown(markdown, images_dict)
        
        # Assert
        expected = "# Title\n![image1](data:image/png;base64,abc123)\nSome text\n![image2](data:image/png;base64,def456)"
        assert result == expected

    @patch('trustgraph.decoding.mistral_ocr.processor.Mistral')
    @patch('trustgraph.base.flow_processor.FlowProcessor.__init__')
    async def test_get_combined_markdown(self, mock_flow_init, mock_mistral_class):
        """Test the get_combined_markdown function"""
        # Arrange
        from trustgraph.decoding.mistral_ocr.processor import get_combined_markdown
        from mistralai.models import OCRResponse
        
        # Mock OCR response with multiple pages
        mock_page1 = MagicMock(
            markdown="# Page 1\n![img1](img1)",
            images=[MagicMock(id="img1", image_base64="base64_img1")]
        )
        mock_page2 = MagicMock(
            markdown="# Page 2\n![img2](img2)",
            images=[MagicMock(id="img2", image_base64="base64_img2")]
        )
        mock_ocr_response = MagicMock(pages=[mock_page1, mock_page2])
        
        # Act
        result = get_combined_markdown(mock_ocr_response)
        
        # Assert
        expected = "# Page 1\n![img1](base64_img1)\n\n# Page 2\n![img2](base64_img2)"
        assert result == expected

    @patch('trustgraph.base.flow_processor.FlowProcessor.add_args')
    def test_add_args(self, mock_parent_add_args):
        """Test add_args adds API key argument"""
        # Arrange
        mock_parser = MagicMock()
        
        # Act
        Processor.add_args(mock_parser)
        
        # Assert
        mock_parent_add_args.assert_called_once_with(mock_parser)
        mock_parser.add_argument.assert_called_once_with(
            '-k', '--api-key',
            default=None,  # default_api_key is None in test environment
            help='Mistral API Key'
        )

    @patch('trustgraph.decoding.mistral_ocr.processor.Processor.launch')
    def test_run(self, mock_launch):
        """Test run function"""
        # Act
        from trustgraph.decoding.mistral_ocr.processor import run
        run()
        
        # Assert
        mock_launch.assert_called_once_with("pdf-decoder",
            "\nSimple decoder, accepts PDF documents on input, outputs pages from the\nPDF document as text as separate output objects.\n")


if __name__ == '__main__':
    pytest.main([__file__])
