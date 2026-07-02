"""
Unit tests for trustgraph.decoding.docling.processor
"""

import pytest
import base64
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

from trustgraph.decoding.docling.processor import (
    Processor, MIME_EXTENSIONS, PAGE_BASED_FORMATS,
    COMPONENT_NAME, COMPONENT_VERSION,
)
from trustgraph.schema import (
    Document, TextDocument, Chunk, Metadata, Triples,
    Triple, Term, IRI, LITERAL,
)
from trustgraph.provenance import TG_PAGE_NUMBER


class MockAsyncProcessor:
    def __init__(self, **params):
        self.config_handlers = []
        self.id = params.get('id', 'test-service')
        self.specifications = []
        self.pubsub = MagicMock()
        self.taskgroup = params.get('taskgroup', MagicMock())


def make_text_item(text="Some text", page_no=None):
    """Create a mock Docling TextItem."""
    item = MagicMock()
    type(item).__name__ = "TextItem"
    item.text = text
    if page_no is not None:
        prov_entry = MagicMock()
        prov_entry.page_no = page_no
        item.prov = [prov_entry]
    else:
        item.prov = []
    return item


def make_table_item(html="<table><tr><td>data</td></tr></table>",
                    page_no=None):
    """Create a mock Docling TableItem."""
    item = MagicMock()
    type(item).__name__ = "TableItem"
    item.text = "table text"
    item.export_to_html = MagicMock(return_value=html)
    if page_no is not None:
        prov_entry = MagicMock()
        prov_entry.page_no = page_no
        item.prov = [prov_entry]
    else:
        item.prov = []
    return item


def make_picture_item(page_no=None):
    """Create a mock Docling PictureItem."""
    item = MagicMock()
    type(item).__name__ = "PictureItem"
    item.text = ""
    if page_no is not None:
        prov_entry = MagicMock()
        prov_entry.page_no = page_no
        item.prov = [prov_entry]
    else:
        item.prov = []
    return item


class TestMimeExtensions:
    """Test the MIME type to extension mapping."""

    def test_pdf_extension(self):
        assert MIME_EXTENSIONS["application/pdf"] == ".pdf"

    def test_docx_extension(self):
        key = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert MIME_EXTENSIONS[key] == ".docx"

    def test_xlsx_extension(self):
        key = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert MIME_EXTENSIONS[key] == ".xlsx"

    def test_pptx_extension(self):
        key = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        assert MIME_EXTENSIONS[key] == ".pptx"

    def test_html_extension(self):
        assert MIME_EXTENSIONS["text/html"] == ".html"

    def test_markdown_extension(self):
        assert MIME_EXTENSIONS["text/markdown"] == ".md"

    def test_plain_text_extension(self):
        assert MIME_EXTENSIONS["text/plain"] == ".md"

    def test_csv_extension(self):
        assert MIME_EXTENSIONS["text/csv"] == ".csv"

    def test_unknown_mime_falls_back(self):
        assert MIME_EXTENSIONS.get("application/octet-stream", ".bin") == ".bin"


class TestPageBasedFormats:
    """Test page-based format detection."""

    def test_pdf_is_page_based(self):
        assert "application/pdf" in PAGE_BASED_FORMATS

    def test_pptx_is_page_based(self):
        pptx = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        assert pptx in PAGE_BASED_FORMATS

    def test_html_is_not_page_based(self):
        assert "text/html" not in PAGE_BASED_FORMATS

    def test_docx_is_not_page_based(self):
        docx = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert docx not in PAGE_BASED_FORMATS

    def test_markdown_is_not_page_based(self):
        assert "text/markdown" not in PAGE_BASED_FORMATS


class TestGetPageTexts:
    """Test page text extraction from DoclingDocument."""

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    def test_single_page_text(self, mock_prod, mock_cons, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        doc = MagicMock()
        doc.iterate_items.return_value = [
            (make_text_item("Hello world", page_no=1), 0),
            (make_text_item("More text", page_no=1), 0),
        ]

        pages = processor.get_page_texts(doc)

        assert len(pages) == 1
        page_no, text, table_count, image_count = pages[0]
        assert page_no == 1
        assert "Hello world" in text
        assert "More text" in text
        assert table_count == 0
        assert image_count == 0

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    def test_multiple_pages(self, mock_prod, mock_cons, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        doc = MagicMock()
        doc.iterate_items.return_value = [
            (make_text_item("Page 1 text", page_no=1), 0),
            (make_text_item("Page 2 text", page_no=2), 0),
            (make_text_item("Page 3 text", page_no=3), 0),
        ]

        pages = processor.get_page_texts(doc)

        assert len(pages) == 3
        assert pages[0][0] == 1
        assert pages[1][0] == 2
        assert pages[2][0] == 3

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    def test_table_counted_and_html_included(self, mock_prod, mock_cons,
                                             mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        html = "<table><tr><td>A</td></tr></table>"
        doc = MagicMock()
        doc.iterate_items.return_value = [
            (make_text_item("Intro", page_no=1), 0),
            (make_table_item(html=html, page_no=1), 0),
        ]

        pages = processor.get_page_texts(doc)

        assert len(pages) == 1
        _, text, table_count, image_count = pages[0]
        assert "<table>" in text
        assert "Intro" in text
        assert table_count == 1
        assert image_count == 0

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    def test_picture_counted_not_in_text(self, mock_prod, mock_cons,
                                        mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        doc = MagicMock()
        doc.iterate_items.return_value = [
            (make_text_item("Text content", page_no=1), 0),
            (make_picture_item(page_no=1), 0),
        ]

        pages = processor.get_page_texts(doc)

        assert len(pages) == 1
        _, text, table_count, image_count = pages[0]
        assert "Text content" in text
        assert image_count == 1
        assert table_count == 0

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    def test_no_prov_defaults_to_page_1(self, mock_prod, mock_cons, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        doc = MagicMock()
        doc.iterate_items.return_value = [
            (make_text_item("No page info"), 0),
        ]

        pages = processor.get_page_texts(doc)

        assert len(pages) == 1
        assert pages[0][0] == 1

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    def test_empty_text_pages_skipped(self, mock_prod, mock_cons, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        item = make_text_item("   ", page_no=1)
        doc = MagicMock()
        doc.iterate_items.return_value = [(item, 0)]

        pages = processor.get_page_texts(doc)

        assert len(pages) == 0


class TestGetFullText:
    """Test full document text extraction."""

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    def test_concatenates_text_items(self, mock_prod, mock_cons, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        doc = MagicMock()
        doc.iterate_items.return_value = [
            (make_text_item("First paragraph"), 0),
            (make_text_item("Second paragraph"), 0),
        ]

        text, table_count, image_count = processor.get_full_text(doc)

        assert "First paragraph" in text
        assert "Second paragraph" in text
        assert "\n\n" in text
        assert table_count == 0
        assert image_count == 0

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    def test_tables_as_html(self, mock_prod, mock_cons, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        html = "<table><tr><td>cell</td></tr></table>"
        doc = MagicMock()
        doc.iterate_items.return_value = [
            (make_text_item("Before"), 0),
            (make_table_item(html=html), 0),
            (make_text_item("After"), 0),
        ]

        text, table_count, image_count = processor.get_full_text(doc)

        assert "<table>" in text
        assert "Before" in text
        assert "After" in text
        assert table_count == 1
        assert image_count == 0

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    def test_pictures_counted_not_included(self, mock_prod, mock_cons,
                                           mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        doc = MagicMock()
        doc.iterate_items.return_value = [
            (make_text_item("Text"), 0),
            (make_picture_item(), 0),
            (make_picture_item(), 0),
        ]

        text, table_count, image_count = processor.get_full_text(doc)

        assert text == "Text"
        assert image_count == 2
        assert table_count == 0


class TestEmitSection(IsolatedAsyncioTestCase):
    """Test emit_section output shape and provenance."""

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_emit_page_section(self, mock_prod, mock_cons, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        mock_output_flow = AsyncMock()
        mock_triples_flow = AsyncMock()
        mock_flow = MagicMock(side_effect=lambda name: {
            "output": mock_output_flow,
            "triples": mock_triples_flow,
        }.get(name))
        mock_flow.librarian.save_child_document = AsyncMock()

        metadata = Metadata(id="doc-1", root="root-1", collection="default")

        uri = await processor.emit_section(
            text="Page content here",
            parent_doc_id="parent-doc",
            doc_uri_str="urn:doc:parent",
            metadata=metadata,
            flow=mock_flow,
            mime_type="application/pdf",
            page_number=3,
        )

        assert uri is not None
        assert uri.startswith("urn:page:")

        mock_flow.librarian.save_child_document.assert_called_once()
        save_kwargs = mock_flow.librarian.save_child_document.call_args
        assert save_kwargs[1]["document_type"] == "page"
        assert save_kwargs[1]["title"] == "Page 3"

        mock_triples_flow.send.assert_called_once()
        triples_msg = mock_triples_flow.send.call_args[0][0]
        assert isinstance(triples_msg, Triples)
        assert triples_msg.metadata.root == "root-1"

        mock_output_flow.send.assert_called_once()
        text_doc = mock_output_flow.send.call_args[0][0]
        assert isinstance(text_doc, TextDocument)
        assert text_doc.text == b"Page content here"
        assert text_doc.metadata.id == uri

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_emit_non_page_section(self, mock_prod, mock_cons,
                                         mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        mock_output_flow = AsyncMock()
        mock_triples_flow = AsyncMock()
        mock_flow = MagicMock(side_effect=lambda name: {
            "output": mock_output_flow,
            "triples": mock_triples_flow,
        }.get(name))
        mock_flow.librarian.save_child_document = AsyncMock()

        metadata = Metadata(id="doc-1", root="root-1", collection="default")

        uri = await processor.emit_section(
            text="Section content",
            parent_doc_id="parent-doc",
            doc_uri_str="urn:doc:parent",
            metadata=metadata,
            flow=mock_flow,
            section_index=1,
        )

        assert uri is not None
        assert uri.startswith("urn:section:")

        save_kwargs = mock_flow.librarian.save_child_document.call_args
        assert save_kwargs[1]["document_type"] == "section"

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_emit_section_skips_blank_text(self, mock_prod, mock_cons,
                                                 mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        mock_flow = MagicMock()
        metadata = Metadata(id="doc-1", collection="default")

        uri = await processor.emit_section(
            text="   ",
            parent_doc_id="parent-doc",
            doc_uri_str="urn:doc:parent",
            metadata=metadata,
            flow=mock_flow,
        )

        assert uri is None


class TestEmitChunk(IsolatedAsyncioTestCase):
    """Test emit_chunk output shape and multi-page provenance."""

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_emit_chunk_single_page(self, mock_prod, mock_cons,
                                          mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
            chunking_mode='hybrid',
        )

        mock_chunks_flow = AsyncMock()
        mock_triples_flow = AsyncMock()
        mock_flow = MagicMock(side_effect=lambda name: {
            "chunks": mock_chunks_flow,
            "triples": mock_triples_flow,
        }.get(name))
        mock_flow.librarian.save_child_document = AsyncMock()

        metadata = Metadata(id="doc-1", root="root-1", collection="default")

        uri = await processor.emit_chunk(
            text="Chunk text content",
            chunk_index=1,
            parent_doc_id="parent-doc",
            doc_uri_str="urn:doc:parent",
            metadata=metadata,
            flow=mock_flow,
            page_numbers=[5],
        )

        assert uri is not None
        assert uri.startswith("urn:chunk:")

        mock_chunks_flow.send.assert_called_once()
        chunk_msg = mock_chunks_flow.send.call_args[0][0]
        assert isinstance(chunk_msg, Chunk)
        assert chunk_msg.chunk == b"Chunk text content"

        mock_triples_flow.send.assert_called_once()
        triples_msg = mock_triples_flow.send.call_args[0][0]
        assert isinstance(triples_msg, Triples)

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_emit_chunk_multi_page_provenance(self, mock_prod, mock_cons,
                                                    mock_conv):
        """Chunks spanning multiple pages emit extra TG_PAGE_NUMBER triples."""
        processor = Processor(
            id='test', taskgroup=MagicMock(),
            chunking_mode='hybrid',
        )

        mock_chunks_flow = AsyncMock()
        mock_triples_flow = AsyncMock()
        mock_flow = MagicMock(side_effect=lambda name: {
            "chunks": mock_chunks_flow,
            "triples": mock_triples_flow,
        }.get(name))
        mock_flow.librarian.save_child_document = AsyncMock()

        metadata = Metadata(id="doc-1", root="root-1", collection="default")

        uri = await processor.emit_chunk(
            text="Chunk spanning pages",
            chunk_index=2,
            parent_doc_id="parent-doc",
            doc_uri_str="urn:doc:parent",
            metadata=metadata,
            flow=mock_flow,
            page_numbers=[3, 4, 5],
        )

        assert uri is not None

        triples_msg = mock_triples_flow.send.call_args[0][0]
        all_triples = triples_msg.triples

        page_number_triples = [
            t for t in all_triples
            if t.p.iri == TG_PAGE_NUMBER
        ]

        extra_pages = {t.o.value for t in page_number_triples}
        assert "4" in extra_pages
        assert "5" in extra_pages

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_emit_chunk_skips_blank(self, mock_prod, mock_cons,
                                          mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
            chunking_mode='hybrid',
        )

        mock_flow = MagicMock()
        metadata = Metadata(id="doc-1", collection="default")

        uri = await processor.emit_chunk(
            text="  \n  ",
            chunk_index=1,
            parent_doc_id="parent-doc",
            doc_uri_str="urn:doc:parent",
            metadata=metadata,
            flow=mock_flow,
        )

        assert uri is None


class TestProcessPageMode(IsolatedAsyncioTestCase):
    """Test page mode processing."""

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_page_based_format_emits_per_page(self, mock_prod, mock_cons,
                                                    mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        doc = MagicMock()
        doc.iterate_items.return_value = [
            (make_text_item("Page 1", page_no=1), 0),
            (make_text_item("Page 2", page_no=2), 0),
        ]

        mock_output_flow = AsyncMock()
        mock_triples_flow = AsyncMock()
        mock_flow = MagicMock(side_effect=lambda name: {
            "output": mock_output_flow,
            "triples": mock_triples_flow,
        }.get(name))
        mock_flow.librarian.save_child_document = AsyncMock()

        metadata = Metadata(id="doc-1", root="root-1", collection="default")

        await processor.process_page_mode(
            doc, "parent-doc", "urn:doc:parent",
            metadata, mock_flow, "application/pdf",
        )

        assert mock_output_flow.send.call_count == 2
        assert mock_triples_flow.send.call_count == 2

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_non_page_format_emits_single_section(self, mock_prod,
                                                        mock_cons, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        doc = MagicMock()
        doc.iterate_items.return_value = [
            (make_text_item("Full document text"), 0),
        ]

        mock_output_flow = AsyncMock()
        mock_triples_flow = AsyncMock()
        mock_flow = MagicMock(side_effect=lambda name: {
            "output": mock_output_flow,
            "triples": mock_triples_flow,
        }.get(name))
        mock_flow.librarian.save_child_document = AsyncMock()

        metadata = Metadata(id="doc-1", root="root-1", collection="default")

        await processor.process_page_mode(
            doc, "parent-doc", "urn:doc:parent",
            metadata, mock_flow, "text/html",
        )

        assert mock_output_flow.send.call_count == 1

        text_doc = mock_output_flow.send.call_args[0][0]
        assert isinstance(text_doc, TextDocument)
        assert text_doc.document_id.startswith("urn:section:")


class TestProcessorInitialization(IsolatedAsyncioTestCase):
    """Test processor initialization and configuration."""

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_default_page_mode(self, mock_prod, mock_cons, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        assert processor.chunking_mode == "page"
        assert processor.chunk_max_tokens == 512

        consumer_specs = [
            s for s in processor.specifications if hasattr(s, 'handler')
        ]
        assert len(consumer_specs) >= 1
        assert consumer_specs[0].name == "input"
        assert consumer_specs[0].schema == Document

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_hybrid_mode_registers_chunks_producer(self, mock_prod,
                                                         mock_cons, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
            chunking_mode='hybrid',
        )

        assert processor.chunking_mode == "hybrid"

        producer_specs = [
            s for s in processor.specifications
            if not hasattr(s, 'handler') and hasattr(s, 'schema')
        ]
        producer_names = [s.name for s in producer_specs]
        assert "chunks" in producer_names
        assert "output" in producer_names
        assert "triples" in producer_names

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_custom_languages(self, mock_prod, mock_cons, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
            languages='eng,deu,fra',
        )

        assert processor.languages == ['eng', 'deu', 'fra']


class TestAddArgs:
    """Test CLI argument registration."""

    @patch('trustgraph.base.flow_processor.FlowProcessor.add_args')
    def test_add_args_registers_expected_args(self, mock_parent):
        mock_parser = MagicMock()

        Processor.add_args(mock_parser)

        mock_parent.assert_called_once_with(mock_parser)

        arg_names = [c[0] for c in mock_parser.add_argument.call_args_list]
        assert ('--chunking-mode',) in arg_names
        assert ('--languages',) in arg_names
        assert ('--chunk-max-tokens',) in arg_names


class TestRun:
    """Test the run entry point."""

    @patch('trustgraph.decoding.docling.processor.Processor.launch')
    def test_run_calls_launch(self, mock_launch):
        from trustgraph.decoding.docling.processor import run
        run()

        mock_launch.assert_called_once()
        args = mock_launch.call_args[0]
        assert args[0] == "document-decoder"


class TestOnMessage(IsolatedAsyncioTestCase):
    """Test the on_message entry point."""

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_inline_document_page_mode(self, mock_prod, mock_cons,
                                             mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        content = b"fake document bytes"
        b64 = base64.b64encode(content).decode('utf-8')

        mock_metadata = Metadata(id="test-doc", root="root", collection="col")
        mock_document = Document(metadata=mock_metadata, data=b64)
        mock_msg = MagicMock()
        mock_msg.value.return_value = mock_document

        mock_doc = MagicMock()
        mock_doc.iterate_items.return_value = [
            (make_text_item("Converted text"), 0),
        ]
        processor.convert_document = MagicMock(return_value=mock_doc)

        mock_output_flow = AsyncMock()
        mock_triples_flow = AsyncMock()
        mock_flow = MagicMock(side_effect=lambda name: {
            "output": mock_output_flow,
            "triples": mock_triples_flow,
        }.get(name))
        mock_flow.librarian.save_child_document = AsyncMock()

        await processor.on_message(mock_msg, None, mock_flow)

        assert mock_output_flow.send.call_count == 1

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_librarian_document_fetch(self, mock_prod, mock_cons,
                                            mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        content = b"fetched document bytes"
        b64_content = base64.b64encode(content)

        mock_metadata = Metadata(id="test-doc", root="root", collection="col")
        mock_document = Document(
            metadata=mock_metadata,
            document_id="lib-doc-123",
        )
        mock_msg = MagicMock()
        mock_msg.value.return_value = mock_document

        mock_doc = MagicMock()
        mock_doc.iterate_items.return_value = [
            (make_text_item("Fetched text"), 0),
        ]
        processor.convert_document = MagicMock(return_value=mock_doc)

        mock_output_flow = AsyncMock()
        mock_triples_flow = AsyncMock()
        mock_flow = MagicMock(side_effect=lambda name: {
            "output": mock_output_flow,
            "triples": mock_triples_flow,
        }.get(name))
        mock_flow.librarian.fetch_document_metadata = AsyncMock(
            return_value=MagicMock(kind="application/pdf")
        )
        mock_flow.librarian.fetch_document_content = AsyncMock(
            return_value=b64_content
        )
        mock_flow.librarian.save_child_document = AsyncMock()

        await processor.on_message(mock_msg, None, mock_flow)

        mock_flow.librarian.fetch_document_metadata.assert_called_once_with(
            document_id="lib-doc-123",
        )
        mock_flow.librarian.fetch_document_content.assert_called_once_with(
            document_id="lib-doc-123",
        )

        processor.convert_document.assert_called_once()
        call_args = processor.convert_document.call_args
        assert call_args[0][1] == "application/pdf"

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.librarian_client.Consumer')
    @patch('trustgraph.base.librarian_client.Producer')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_conversion_failure_logged_not_raised(self, mock_prod,
                                                       mock_cons, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        content = b"bad document"
        b64 = base64.b64encode(content).decode('utf-8')

        mock_metadata = Metadata(id="test-doc", root="root", collection="col")
        mock_document = Document(metadata=mock_metadata, data=b64)
        mock_msg = MagicMock()
        mock_msg.value.return_value = mock_document

        processor.convert_document = MagicMock(
            side_effect=ValueError("Conversion failed")
        )

        mock_flow = MagicMock()

        await processor.on_message(mock_msg, None, mock_flow)


if __name__ == '__main__':
    pytest.main([__file__])
