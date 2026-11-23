"""
Unit tests for trustgraph.decoding.docling.processor
"""

import pytest
import base64
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

from trustgraph.decoding.docling.processor import (
    Processor, MIME_EXTENSIONS, PAGE_BASED_FORMATS,
)

COMPONENT_NAME = Processor.COMPONENT_NAME
COMPONENT_VERSION = Processor.COMPONENT_VERSION
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
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    def test_single_page_text(self, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        doc = MagicMock()
        doc.iterate_items.return_value = [
            (make_text_item("Hello world", page_no=1), 0),
            (make_text_item("More text", page_no=1), 0),
        ]

        pages = list(processor._get_page_texts(doc))

        assert len(pages) == 1
        text, page_no, section_type = pages[0]
        assert page_no == 1
        assert "Hello world" in text
        assert "More text" in text
        assert section_type == "text"

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    def test_multiple_pages(self, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        doc = MagicMock()
        doc.iterate_items.return_value = [
            (make_text_item("Page 1 text", page_no=1), 0),
            (make_text_item("Page 2 text", page_no=2), 0),
            (make_text_item("Page 3 text", page_no=3), 0),
        ]

        pages = list(processor._get_page_texts(doc))

        assert len(pages) == 3
        assert pages[0][1] == 1
        assert pages[1][1] == 2
        assert pages[2][1] == 3

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    def test_table_counted_and_html_included(self, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        html = "<table><tr><td>A</td></tr></table>"
        doc = MagicMock()
        doc.iterate_items.return_value = [
            (make_text_item("Intro", page_no=1), 0),
            (make_table_item(html=html, page_no=1), 0),
        ]

        pages = list(processor._get_page_texts(doc))

        assert len(pages) == 1
        text, _, section_type = pages[0]
        assert "<table>" in text
        assert "Intro" in text
        assert section_type == "table"

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    def test_picture_counted_not_in_text(self, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        doc = MagicMock()
        doc.iterate_items.return_value = [
            (make_text_item("Text content", page_no=1), 0),
            (make_picture_item(page_no=1), 0),
        ]

        pages = list(processor._get_page_texts(doc))

        assert len(pages) == 1
        text, _, section_type = pages[0]
        assert "Text content" in text
        assert section_type == "image"

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    def test_no_prov_defaults_to_page_1(self, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        doc = MagicMock()
        doc.iterate_items.return_value = [
            (make_text_item("No page info"), 0),
        ]

        pages = list(processor._get_page_texts(doc))

        assert len(pages) == 1
        assert pages[0][1] == 1

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    def test_empty_text_pages_skipped(self, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        item = make_text_item("   ", page_no=1)
        doc = MagicMock()
        doc.iterate_items.return_value = [(item, 0)]

        pages = list(processor._get_page_texts(doc))

        assert len(pages) == 0


class TestGetFullText:
    """Test full document text extraction."""

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    def test_concatenates_text_items(self, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        doc = MagicMock()
        doc.iterate_items.return_value = [
            (make_text_item("First paragraph"), 0),
            (make_text_item("Second paragraph"), 0),
        ]

        result = list(processor._get_full_text(doc))

        assert len(result) == 1
        text, page_no, section_type = result[0]
        assert "First paragraph" in text
        assert "Second paragraph" in text
        assert "\n\n" in text
        assert page_no is None
        assert section_type == "text"

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    def test_tables_as_html(self, mock_conv):
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

        result = list(processor._get_full_text(doc))

        assert len(result) == 1
        text, _, _ = result[0]
        assert "<table>" in text
        assert "Before" in text
        assert "After" in text

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    def test_pictures_not_included(self, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        doc = MagicMock()
        doc.iterate_items.return_value = [
            (make_text_item("Text"), 0),
            (make_picture_item(), 0),
            (make_picture_item(), 0),
        ]

        result = list(processor._get_full_text(doc))

        assert len(result) == 1
        text, _, _ = result[0]
        assert text == "Text"


class TestPageSectionEmission(IsolatedAsyncioTestCase):
    """Test that on_message emits pages/sections with correct shape and provenance."""

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_page_section_emits_page_uri_and_provenance(self, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        content = b"fake document bytes"
        b64 = base64.b64encode(content)

        mock_metadata = Metadata(id="doc-1", root="root-1", collection="default")
        mock_document = Document(
            metadata=mock_metadata, document_id="doc-1",
        )
        mock_msg = MagicMock()
        mock_msg.value.return_value = mock_document

        doc = MagicMock()
        doc.iterate_items.return_value = [
            (make_text_item("Page content here", page_no=3), 0),
        ]
        processor.convert_document = MagicMock(return_value=doc)

        mock_output_flow = AsyncMock()
        mock_triples_flow = AsyncMock()
        mock_flow = MagicMock(side_effect=lambda name: {
            "output": mock_output_flow,
            "triples": mock_triples_flow,
        }.get(name))
        mock_flow.librarian.save_child_document = AsyncMock()
        mock_flow.librarian.fetch_document_metadata = AsyncMock(
            return_value=MagicMock(kind="application/pdf"),
        )
        mock_flow.librarian.fetch_document_content = AsyncMock(
            return_value=b64,
        )

        await processor.on_message(mock_msg, None, mock_flow)

        mock_flow.librarian.save_child_document.assert_called_once()
        save_kwargs = mock_flow.librarian.save_child_document.call_args[1]
        assert save_kwargs["document_type"] == "page"
        assert save_kwargs["title"] == "Page 3"

        mock_triples_flow.send.assert_called_once()
        triples_msg = mock_triples_flow.send.call_args[0][0]
        assert isinstance(triples_msg, Triples)
        assert triples_msg.metadata.root == "root-1"

        mock_output_flow.send.assert_called_once()
        text_doc = mock_output_flow.send.call_args[0][0]
        assert isinstance(text_doc, TextDocument)
        assert text_doc.text == b"Page content here"
        assert text_doc.document_id.startswith("urn:page:")
        assert text_doc.metadata.id == text_doc.document_id

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_non_page_section_emits_section_uri(self, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        content = b"fake document bytes"
        b64 = base64.b64encode(content).decode('utf-8')

        mock_metadata = Metadata(id="doc-1", root="root-1", collection="default")
        mock_document = Document(metadata=mock_metadata, data=b64)
        mock_msg = MagicMock()
        mock_msg.value.return_value = mock_document

        doc = MagicMock()
        doc.iterate_items.return_value = [
            (make_text_item("Section content"), 0),
        ]
        processor.convert_document = MagicMock(return_value=doc)

        mock_output_flow = AsyncMock()
        mock_triples_flow = AsyncMock()
        mock_flow = MagicMock(side_effect=lambda name: {
            "output": mock_output_flow,
            "triples": mock_triples_flow,
        }.get(name))
        mock_flow.librarian.save_child_document = AsyncMock()

        await processor.on_message(mock_msg, None, mock_flow)

        save_kwargs = mock_flow.librarian.save_child_document.call_args[1]
        assert save_kwargs["document_type"] == "section"

        text_doc = mock_output_flow.send.call_args[0][0]
        assert text_doc.document_id.startswith("urn:section:")

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_blank_text_skipped(self, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        content = b"fake document bytes"
        b64 = base64.b64encode(content).decode('utf-8')

        mock_metadata = Metadata(id="doc-1", collection="default")
        mock_document = Document(metadata=mock_metadata, data=b64)
        mock_msg = MagicMock()
        mock_msg.value.return_value = mock_document

        doc = MagicMock()
        doc.iterate_items.return_value = [
            (make_text_item("   ", page_no=1), 0),
        ]
        processor.convert_document = MagicMock(return_value=doc)

        mock_output_flow = AsyncMock()
        mock_triples_flow = AsyncMock()
        mock_flow = MagicMock(side_effect=lambda name: {
            "output": mock_output_flow,
            "triples": mock_triples_flow,
        }.get(name))
        mock_flow.librarian.save_child_document = AsyncMock()

        await processor.on_message(mock_msg, None, mock_flow)

        mock_output_flow.send.assert_not_called()
        mock_flow.librarian.save_child_document.assert_not_called()


class TestHybridChunkEmission(IsolatedAsyncioTestCase):
    """Test hybrid mode chunk emission and multi-page provenance."""

    @patch('trustgraph.decoding.docling.processor.HybridChunker')
    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_chunk_single_page(self, mock_conv, mock_chunker_class):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
            chunking_mode='hybrid',
        )

        content = b"fake document bytes"
        b64 = base64.b64encode(content).decode('utf-8')

        mock_metadata = Metadata(id="doc-1", root="root-1", collection="default")
        mock_document = Document(metadata=mock_metadata, data=b64)
        mock_msg = MagicMock()
        mock_msg.value.return_value = mock_document

        mock_doc = MagicMock()
        processor.convert_document = MagicMock(return_value=mock_doc)

        mock_chunk = MagicMock()
        prov = MagicMock()
        prov.page_no = 5
        doc_item = MagicMock()
        doc_item.prov = [prov]
        mock_chunk.meta.doc_items = [doc_item]

        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [mock_chunk]
        mock_chunker.serialize.return_value = "Chunk text content"
        mock_chunker_class.return_value = mock_chunker

        mock_chunks_flow = AsyncMock()
        mock_triples_flow = AsyncMock()
        mock_flow = MagicMock(side_effect=lambda name: {
            "chunks": mock_chunks_flow,
            "triples": mock_triples_flow,
        }.get(name))
        mock_flow.librarian.save_child_document = AsyncMock()

        await processor.on_message(mock_msg, None, mock_flow)

        mock_chunks_flow.send.assert_called_once()
        chunk_msg = mock_chunks_flow.send.call_args[0][0]
        assert isinstance(chunk_msg, Chunk)
        assert chunk_msg.chunk == b"Chunk text content"
        assert chunk_msg.document_id.startswith("urn:chunk:")

        mock_triples_flow.send.assert_called_once()
        triples_msg = mock_triples_flow.send.call_args[0][0]
        assert isinstance(triples_msg, Triples)

    @patch('trustgraph.decoding.docling.processor.HybridChunker')
    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_chunk_multi_page_provenance(self, mock_conv, mock_chunker_class):
        """Chunks spanning multiple pages emit extra TG_PAGE_NUMBER triples."""
        processor = Processor(
            id='test', taskgroup=MagicMock(),
            chunking_mode='hybrid',
        )

        content = b"fake document bytes"
        b64 = base64.b64encode(content).decode('utf-8')

        mock_metadata = Metadata(id="doc-1", root="root-1", collection="default")
        mock_document = Document(metadata=mock_metadata, data=b64)
        mock_msg = MagicMock()
        mock_msg.value.return_value = mock_document

        mock_doc = MagicMock()
        processor.convert_document = MagicMock(return_value=mock_doc)

        mock_chunk = MagicMock()
        prov3 = MagicMock(); prov3.page_no = 3
        prov4 = MagicMock(); prov4.page_no = 4
        prov5 = MagicMock(); prov5.page_no = 5
        doc_item1 = MagicMock(); doc_item1.prov = [prov3]
        doc_item2 = MagicMock(); doc_item2.prov = [prov4, prov5]
        mock_chunk.meta.doc_items = [doc_item1, doc_item2]

        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [mock_chunk]
        mock_chunker.serialize.return_value = "Chunk spanning pages"
        mock_chunker_class.return_value = mock_chunker

        mock_chunks_flow = AsyncMock()
        mock_triples_flow = AsyncMock()
        mock_flow = MagicMock(side_effect=lambda name: {
            "chunks": mock_chunks_flow,
            "triples": mock_triples_flow,
        }.get(name))
        mock_flow.librarian.save_child_document = AsyncMock()

        await processor.on_message(mock_msg, None, mock_flow)

        triples_msg = mock_triples_flow.send.call_args[0][0]
        all_triples = triples_msg.triples

        page_number_triples = [
            t for t in all_triples
            if t.p.iri == TG_PAGE_NUMBER
        ]

        extra_pages = {t.o.value for t in page_number_triples}
        assert "4" in extra_pages
        assert "5" in extra_pages

    @patch('trustgraph.decoding.docling.processor.HybridChunker')
    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_chunk_skips_blank(self, mock_conv, mock_chunker_class):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
            chunking_mode='hybrid',
        )

        content = b"fake document bytes"
        b64 = base64.b64encode(content).decode('utf-8')

        mock_metadata = Metadata(id="doc-1", collection="default")
        mock_document = Document(metadata=mock_metadata, data=b64)
        mock_msg = MagicMock()
        mock_msg.value.return_value = mock_document

        mock_doc = MagicMock()
        processor.convert_document = MagicMock(return_value=mock_doc)

        mock_chunk = MagicMock()
        mock_chunk.meta.doc_items = []

        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [mock_chunk]
        mock_chunker.serialize.return_value = "  \n  "
        mock_chunker_class.return_value = mock_chunker

        mock_chunks_flow = AsyncMock()
        mock_triples_flow = AsyncMock()
        mock_flow = MagicMock(side_effect=lambda name: {
            "chunks": mock_chunks_flow,
            "triples": mock_triples_flow,
        }.get(name))
        mock_flow.librarian.save_child_document = AsyncMock()

        await processor.on_message(mock_msg, None, mock_flow)

        mock_chunks_flow.send.assert_not_called()
        mock_flow.librarian.save_child_document.assert_not_called()


class TestDecodePages(IsolatedAsyncioTestCase):
    """Test decode_pages dispatches page-based vs full-text correctly."""

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_page_based_format_yields_per_page(self, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        doc = MagicMock()
        doc.iterate_items.return_value = [
            (make_text_item("Page 1", page_no=1), 0),
            (make_text_item("Page 2", page_no=2), 0),
        ]
        processor.convert_document = MagicMock(return_value=doc)

        pages = list(processor.decode_pages(b"fake", mime_type="application/pdf"))

        assert len(pages) == 2
        assert pages[0][1] == 1
        assert pages[1][1] == 2

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_non_page_format_yields_single_section(self, mock_conv):
        processor = Processor(
            id='test', taskgroup=MagicMock(),
        )

        doc = MagicMock()
        doc.iterate_items.return_value = [
            (make_text_item("Full document text"), 0),
        ]
        processor.convert_document = MagicMock(return_value=doc)

        pages = list(processor.decode_pages(b"fake", mime_type="text/html"))

        assert len(pages) == 1
        text, page_no, section_type = pages[0]
        assert page_no is None
        assert "Full document text" in text


class TestProcessorInitialization(IsolatedAsyncioTestCase):
    """Test processor initialization and configuration."""

    @patch('trustgraph.decoding.docling.processor.DocumentConverter')
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_default_page_mode(self, mock_conv):
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
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_hybrid_mode_registers_chunks_producer(self, mock_conv):
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
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_custom_languages(self, mock_conv):
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
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_inline_document_page_mode(self, mock_conv):
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
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_librarian_document_fetch(self, mock_conv):
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
    @patch('trustgraph.base.async_processor.AsyncProcessor', MockAsyncProcessor)
    async def test_conversion_failure_logged_not_raised(self, mock_conv):
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
