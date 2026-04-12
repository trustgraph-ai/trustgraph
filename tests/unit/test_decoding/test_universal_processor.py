"""
Unit tests for trustgraph.decoding.universal.processor
"""

import pytest
import base64
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

from trustgraph.decoding.universal.processor import (
    Processor, assemble_section_text, MIME_EXTENSIONS, PAGE_BASED_FORMATS,
)
from trustgraph.schema import Document, TextDocument, Metadata, Triples


class MockAsyncProcessor:
    def __init__(self, **params):
        self.config_handlers = []
        self.id = params.get('id', 'test-service')
        self.specifications = []
        self.pubsub = MagicMock()
        self.taskgroup = params.get('taskgroup', MagicMock())


def make_element(category="NarrativeText", text="Some text",
                 page_number=None, text_as_html=None, image_base64=None):
    """Create a mock unstructured element."""
    el = MagicMock()
    el.category = category
    el.text = text
    el.metadata = MagicMock()
    el.metadata.page_number = page_number
    el.metadata.text_as_html = text_as_html
    el.metadata.image_base64 = image_base64
    return el


class TestAssembleSectionText:
    """Test the text assembly function."""

    def test_narrative_text(self):
        elements = [
            make_element("NarrativeText", "Paragraph one."),
            make_element("NarrativeText", "Paragraph two."),
        ]
        text, types, tables, images = assemble_section_text(elements)
        assert text == "Paragraph one.\n\nParagraph two."
        assert "NarrativeText" in types
        assert tables == 0
        assert images == 0

    def test_table_with_html(self):
        elements = [
            make_element("NarrativeText", "Before table."),
            make_element(
                "Table", "Col1 Col2",
                text_as_html="<table><tr><td>Col1</td><td>Col2</td></tr></table>"
            ),
        ]
        text, types, tables, images = assemble_section_text(elements)
        assert "<table>" in text
        assert "Before table." in text
        assert tables == 1
        assert "Table" in types

    def test_table_without_html_fallback(self):
        el = make_element("Table", "plain table text")
        el.metadata.text_as_html = None
        elements = [el]
        text, types, tables, images = assemble_section_text(elements)
        assert text == "plain table text"
        assert tables == 1

    def test_images_skipped(self):
        elements = [
            make_element("NarrativeText", "Text content"),
            make_element("Image", "OCR text from image"),
        ]
        text, types, tables, images = assemble_section_text(elements)
        assert "OCR text" not in text
        assert "Text content" in text
        assert images == 1
        assert "Image" in types

    def test_empty_elements(self):
        text, types, tables, images = assemble_section_text([])
        assert text == ""
        assert len(types) == 0
        assert tables == 0
        assert images == 0

    def test_mixed_elements(self):
        elements = [
            make_element("Title", "Section Heading"),
            make_element("NarrativeText", "Body text."),
            make_element(
                "Table", "data",
                text_as_html="<table><tr><td>data</td></tr></table>"
            ),
            make_element("Image", "img text"),
            make_element("ListItem", "- item one"),
        ]
        text, types, tables, images = assemble_section_text(elements)
        assert "Section Heading" in text
        assert "Body text." in text
        assert "<table>" in text
        assert "img text" not in text
        assert "- item one" in text
        assert tables == 1
        assert images == 1
        assert {"Title", "NarrativeText", "Table", "Image", "ListItem"} == types


class TestMimeExtensions:
    """Test the mime type to extension mapping."""

    def test_pdf_extension(self):
        assert MIME_EXTENSIONS["application/pdf"] == ".pdf"

    def test_docx_extension(self):
        key = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert MIME_EXTENSIONS[key] == ".docx"

    def test_html_extension(self):
        assert MIME_EXTENSIONS["text/html"] == ".html"


class TestPageBasedFormats:
    """Test page-based format detection."""

    def test_pdf_is_page_based(self):
        assert "application/pdf" in PAGE_BASED_FORMATS

    def test_html_is_not_page_based(self):
        assert "text/html" not in PAGE_BASED_FORMATS

    def test_pptx_is_page_based(self):
        pptx = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        assert pptx in PAGE_BASED_FORMATS


class TestUniversalProcessor(IsolatedAsyncioTestCase):
    """Test universal decoder processor."""

    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_processor_initialization(
        self, mock_producer, mock_consumer
    ):
        """Test processor initialization with defaults."""
        config = {
            'id': 'test-universal',
            'taskgroup': AsyncMock(),
        }

        processor = Processor(**config)

        assert processor.partition_strategy == "auto"
        assert processor.section_strategy_name == "whole-document"
        assert processor.section_element_count == 20
        assert processor.section_max_size == 4000

        # Check specs: input consumer, output producer, triples producer
        consumer_specs = [
            s for s in processor.specifications if hasattr(s, 'handler')
        ]
        assert len(consumer_specs) >= 1
        assert consumer_specs[0].name == "input"
        assert consumer_specs[0].schema == Document

    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_processor_custom_strategy(
        self, mock_producer, mock_consumer
    ):
        """Test processor initialization with custom section strategy."""
        config = {
            'id': 'test-universal',
            'taskgroup': AsyncMock(),
            'section_strategy': 'heading',
            'strategy': 'hi_res',
        }

        processor = Processor(**config)

        assert processor.partition_strategy == "hi_res"
        assert processor.section_strategy_name == "heading"

    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_group_by_page(self, mock_producer, mock_consumer):
        """Test page grouping of elements."""
        config = {
            'id': 'test-universal',
            'taskgroup': AsyncMock(),
        }

        processor = Processor(**config)

        elements = [
            make_element("NarrativeText", "Page 1 text", page_number=1),
            make_element("NarrativeText", "More page 1", page_number=1),
            make_element("NarrativeText", "Page 2 text", page_number=2),
        ]

        result = processor.group_by_page(elements)

        assert len(result) == 2
        assert result[0][0] == 1  # page number
        assert len(result[0][1]) == 2  # 2 elements on page 1
        assert result[1][0] == 2
        assert len(result[1][1]) == 1

    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.decoding.universal.processor.partition')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_on_message_inline_non_page(
        self, mock_partition, mock_producer, mock_consumer
    ):
        """Test processing an inline non-page document."""
        config = {
            'id': 'test-universal',
            'taskgroup': AsyncMock(),
        }

        processor = Processor(**config)

        # Mock partition to return elements without page numbers
        mock_partition.return_value = [
            make_element("Title", "Document Title"),
            make_element("NarrativeText", "Body text content."),
        ]

        # Mock message with inline data
        content = b"# Document Title\nBody text content."
        mock_metadata = Metadata(id="test-doc", user="testuser",
                                 collection="default")
        mock_document = Document(
            metadata=mock_metadata,
            data=base64.b64encode(content).decode('utf-8'),
        )
        mock_msg = MagicMock()
        mock_msg.value.return_value = mock_document

        # Mock flow
        mock_output_flow = AsyncMock()
        mock_triples_flow = AsyncMock()
        mock_flow = MagicMock(side_effect=lambda name: {
            "output": mock_output_flow,
            "triples": mock_triples_flow,
        }.get(name))

        # Mock save_child_document and magic
        processor.librarian.save_child_document = AsyncMock(return_value="mock-id")

        with patch('trustgraph.decoding.universal.processor.magic') as mock_magic:
            mock_magic.from_buffer.return_value = "text/markdown"
            await processor.on_message(mock_msg, None, mock_flow)

        # Should emit one section (whole-document strategy)
        assert mock_output_flow.send.call_count == 1
        assert mock_triples_flow.send.call_count == 1

        # Check output
        call_args = mock_output_flow.send.call_args[0][0]
        assert isinstance(call_args, TextDocument)
        assert call_args.document_id.startswith("urn:section:")
        assert call_args.text == b""

    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.decoding.universal.processor.partition')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_on_message_page_based(
        self, mock_partition, mock_producer, mock_consumer
    ):
        """Test processing a page-based document."""
        config = {
            'id': 'test-universal',
            'taskgroup': AsyncMock(),
        }

        processor = Processor(**config)

        # Mock partition to return elements with page numbers
        mock_partition.return_value = [
            make_element("NarrativeText", "Page 1 content", page_number=1),
            make_element("NarrativeText", "Page 2 content", page_number=2),
        ]

        # Mock message
        content = b"fake pdf"
        mock_metadata = Metadata(id="test-doc", user="testuser",
                                 collection="default")
        mock_document = Document(
            metadata=mock_metadata,
            data=base64.b64encode(content).decode('utf-8'),
        )
        mock_msg = MagicMock()
        mock_msg.value.return_value = mock_document

        mock_output_flow = AsyncMock()
        mock_triples_flow = AsyncMock()
        mock_flow = MagicMock(side_effect=lambda name: {
            "output": mock_output_flow,
            "triples": mock_triples_flow,
        }.get(name))

        processor.librarian.save_child_document = AsyncMock(return_value="mock-id")

        with patch('trustgraph.decoding.universal.processor.magic') as mock_magic:
            mock_magic.from_buffer.return_value = "application/pdf"
            await processor.on_message(mock_msg, None, mock_flow)

        # Should emit two pages
        assert mock_output_flow.send.call_count == 2

        # Check first output uses page URI
        call_args = mock_output_flow.send.call_args_list[0][0][0]
        assert call_args.document_id.startswith("urn:page:")

    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.decoding.universal.processor.partition')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_images_stored_not_emitted(
        self, mock_partition, mock_producer, mock_consumer
    ):
        """Test that images are stored but not sent to text pipeline."""
        config = {
            'id': 'test-universal',
            'taskgroup': AsyncMock(),
        }

        processor = Processor(**config)

        mock_partition.return_value = [
            make_element("NarrativeText", "Some text", page_number=1),
            make_element("Image", "img ocr", page_number=1,
                         image_base64="aW1hZ2VkYXRh"),
        ]

        content = b"fake pdf"
        mock_metadata = Metadata(id="test-doc", user="testuser",
                                 collection="default")
        mock_document = Document(
            metadata=mock_metadata,
            data=base64.b64encode(content).decode('utf-8'),
        )
        mock_msg = MagicMock()
        mock_msg.value.return_value = mock_document

        mock_output_flow = AsyncMock()
        mock_triples_flow = AsyncMock()
        mock_flow = MagicMock(side_effect=lambda name: {
            "output": mock_output_flow,
            "triples": mock_triples_flow,
        }.get(name))

        processor.librarian.save_child_document = AsyncMock(return_value="mock-id")

        with patch('trustgraph.decoding.universal.processor.magic') as mock_magic:
            mock_magic.from_buffer.return_value = "application/pdf"
            await processor.on_message(mock_msg, None, mock_flow)

        # Only 1 TextDocument output (the page text, not the image)
        assert mock_output_flow.send.call_count == 1

        # But 2 triples outputs (page provenance + image provenance)
        assert mock_triples_flow.send.call_count == 2

        # save_child_document called twice (page + image)
        assert processor.librarian.save_child_document.call_count == 2

    @patch('trustgraph.base.flow_processor.FlowProcessor.add_args')
    def test_add_args(self, mock_parent_add_args):
        """Test add_args registers all expected arguments."""
        mock_parser = MagicMock()

        Processor.add_args(mock_parser)

        mock_parent_add_args.assert_called_once_with(mock_parser)

        # Check key arguments are registered
        arg_names = [
            c[0] for c in mock_parser.add_argument.call_args_list
        ]
        assert ('--strategy',) in arg_names
        assert ('--languages',) in arg_names
        assert ('--section-strategy',) in arg_names
        assert ('--section-element-count',) in arg_names
        assert ('--section-max-size',) in arg_names
        assert ('--section-within-pages',) in arg_names

    @patch('trustgraph.decoding.universal.processor.Processor.launch')
    def test_run(self, mock_launch):
        """Test run function."""
        from trustgraph.decoding.universal.processor import run
        run()

        mock_launch.assert_called_once()
        args = mock_launch.call_args[0]
        assert args[0] == "document-decoder"
        assert "Universal document decoder" in args[1]


if __name__ == '__main__':
    pytest.main([__file__])
