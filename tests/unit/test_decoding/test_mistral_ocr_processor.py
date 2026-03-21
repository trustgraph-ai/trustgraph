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
from trustgraph.schema import Document, TextDocument, Metadata, Triples


class MockAsyncProcessor:
    def __init__(self, **params):
        self.config_handlers = []
        self.id = params.get('id', 'test-service')
        self.specifications = []
        self.pubsub = MagicMock()
        self.taskgroup = params.get('taskgroup', MagicMock())


class TestMistralOcrProcessor(IsolatedAsyncioTestCase):
    """Test Mistral OCR processor functionality"""

    @patch('trustgraph.decoding.mistral_ocr.processor.Consumer')
    @patch('trustgraph.decoding.mistral_ocr.processor.Producer')
    @patch('trustgraph.decoding.mistral_ocr.processor.Mistral')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_processor_initialization_with_api_key(
        self, mock_mistral_class, mock_producer, mock_consumer
    ):
        """Test Mistral OCR processor initialization with API key"""
        mock_mistral_class.return_value = MagicMock()

        config = {
            'id': 'test-mistral-ocr',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock()
        }

        processor = Processor(**config)

        mock_mistral_class.assert_called_once_with(api_key='test-api-key')

        # Check specs registered: input consumer, output producer, triples producer
        consumer_specs = [s for s in processor.specifications if hasattr(s, 'handler')]
        assert len(consumer_specs) >= 1
        assert consumer_specs[0].name == "input"
        assert consumer_specs[0].schema == Document

    @patch('trustgraph.decoding.mistral_ocr.processor.Consumer')
    @patch('trustgraph.decoding.mistral_ocr.processor.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_processor_initialization_without_api_key(
        self, mock_producer, mock_consumer
    ):
        """Test Mistral OCR processor initialization without API key raises error"""
        config = {
            'id': 'test-mistral-ocr',
            'taskgroup': AsyncMock()
        }

        with pytest.raises(RuntimeError, match="Mistral API key not specified"):
            Processor(**config)

    @patch('trustgraph.decoding.mistral_ocr.processor.Consumer')
    @patch('trustgraph.decoding.mistral_ocr.processor.Producer')
    @patch('trustgraph.decoding.mistral_ocr.processor.Mistral')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_ocr_single_chunk(
        self, mock_mistral_class, mock_producer, mock_consumer
    ):
        """Test OCR processing with a single chunk (less than 5 pages)"""
        mock_mistral = MagicMock()
        mock_mistral_class.return_value = mock_mistral

        # Mock file upload
        mock_uploaded_file = MagicMock(id="file-123")
        mock_mistral.files.upload.return_value = mock_uploaded_file

        # Mock signed URL
        mock_signed_url = MagicMock(url="https://example.com/signed-url")
        mock_mistral.files.get_signed_url.return_value = mock_signed_url

        # Mock OCR response with 2 pages
        mock_page1 = MagicMock(
            markdown="# Page 1\nContent ![img1](img1)",
            images=[MagicMock(id="img1", image_base64="data:image/png;base64,abc123")]
        )
        mock_page2 = MagicMock(
            markdown="# Page 2\nMore content",
            images=[]
        )
        mock_ocr_response = MagicMock(pages=[mock_page1, mock_page2])
        mock_mistral.ocr.process.return_value = mock_ocr_response

        # Mock PyPDF
        mock_pdf_reader = MagicMock()
        mock_pdf_reader.pages = [MagicMock(), MagicMock(), MagicMock()]

        config = {
            'id': 'test-mistral-ocr',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock()
        }

        with patch('trustgraph.decoding.mistral_ocr.processor.PdfReader', return_value=mock_pdf_reader):
            with patch('trustgraph.decoding.mistral_ocr.processor.PdfWriter') as mock_pdf_writer_class:
                mock_pdf_writer = MagicMock()
                mock_pdf_writer_class.return_value = mock_pdf_writer

                processor = Processor(**config)
                result = processor.ocr(b"fake pdf content")

        # Returns list of (markdown, page_num) tuples
        assert len(result) == 2
        assert result[0] == ("# Page 1\nContent ![img1](data:image/png;base64,abc123)", 1)
        assert result[1] == ("# Page 2\nMore content", 2)

        # Verify PDF writer was used
        assert mock_pdf_writer.add_page.call_count == 3
        mock_pdf_writer.write_stream.assert_called_once()

        # Verify Mistral API calls
        mock_mistral.files.upload.assert_called_once()
        mock_mistral.files.get_signed_url.assert_called_once_with(
            file_id="file-123", expiry=1
        )
        mock_mistral.ocr.process.assert_called_once()

    @patch('trustgraph.decoding.mistral_ocr.processor.Consumer')
    @patch('trustgraph.decoding.mistral_ocr.processor.Producer')
    @patch('trustgraph.decoding.mistral_ocr.processor.Mistral')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_on_message_success(
        self, mock_mistral_class, mock_producer, mock_consumer
    ):
        """Test successful message processing"""
        mock_mistral_class.return_value = MagicMock()

        # Mock message
        pdf_content = b"fake pdf content"
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        mock_metadata = Metadata(id="test-doc")
        mock_document = Document(metadata=mock_metadata, data=pdf_base64)
        mock_msg = MagicMock()
        mock_msg.value.return_value = mock_document

        # Mock flow
        mock_output_flow = AsyncMock()
        mock_triples_flow = AsyncMock()
        mock_flow = MagicMock(side_effect=lambda name: {
            "output": mock_output_flow,
            "triples": mock_triples_flow,
        }.get(name))

        config = {
            'id': 'test-mistral-ocr',
            'api_key': 'test-api-key',
            'taskgroup': AsyncMock()
        }

        processor = Processor(**config)

        # Mock ocr to return per-page results
        ocr_result = [
            ("# Page 1\nContent", 1),
            ("# Page 2\nMore content", 2),
        ]

        # Mock save_child_document
        processor.save_child_document = AsyncMock(return_value="mock-doc-id")

        with patch.object(processor, 'ocr', return_value=ocr_result):
            await processor.on_message(mock_msg, None, mock_flow)

        # Verify output was sent for each page
        assert mock_output_flow.send.call_count == 2
        # Verify triples were sent for each page
        assert mock_triples_flow.send.call_count == 2

        # Check output uses UUID-based page URNs
        call_args = mock_output_flow.send.call_args_list[0][0][0]
        assert isinstance(call_args, TextDocument)
        assert call_args.document_id.startswith("urn:page:")
        assert call_args.text == b""  # Content stored in librarian

    @patch('trustgraph.decoding.mistral_ocr.processor.Mistral')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_chunks_function(self, mock_mistral_class):
        """Test the chunks utility function"""
        from trustgraph.decoding.mistral_ocr.processor import chunks

        test_list = list(range(12))
        result = list(chunks(test_list, 5))

        assert len(result) == 3
        assert result[0] == [0, 1, 2, 3, 4]
        assert result[1] == [5, 6, 7, 8, 9]
        assert result[2] == [10, 11]

    @patch('trustgraph.decoding.mistral_ocr.processor.Mistral')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_replace_images_in_markdown(self, mock_mistral_class):
        """Test the replace_images_in_markdown function"""
        from trustgraph.decoding.mistral_ocr.processor import replace_images_in_markdown

        markdown = "# Title\n![image1](image1)\nSome text\n![image2](image2)"
        images_dict = {
            "image1": "data:image/png;base64,abc123",
            "image2": "data:image/png;base64,def456"
        }

        result = replace_images_in_markdown(markdown, images_dict)

        expected = "# Title\n![image1](data:image/png;base64,abc123)\nSome text\n![image2](data:image/png;base64,def456)"
        assert result == expected

    @patch('trustgraph.base.flow_processor.FlowProcessor.add_args')
    def test_add_args(self, mock_parent_add_args):
        """Test add_args adds expected arguments"""
        mock_parser = MagicMock()

        Processor.add_args(mock_parser)

        mock_parent_add_args.assert_called_once_with(mock_parser)
        assert mock_parser.add_argument.call_count == 3
        # Check the API key arg is among them
        call_args_list = [c[0] for c in mock_parser.add_argument.call_args_list]
        assert ('-k', '--api-key') in call_args_list

    @patch('trustgraph.decoding.mistral_ocr.processor.Processor.launch')
    def test_run(self, mock_launch):
        """Test run function"""
        from trustgraph.decoding.mistral_ocr.processor import run
        run()

        mock_launch.assert_called_once()
        args = mock_launch.call_args[0]
        assert args[0] == "pdf-decoder"
        assert "Mistral OCR decoder" in args[1]


if __name__ == '__main__':
    pytest.main([__file__])
