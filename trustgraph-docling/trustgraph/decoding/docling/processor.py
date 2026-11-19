
"""
Document decoder powered by Docling.

Accepts documents in common formats (PDF, DOCX, XLSX, HTML, Markdown,
plain text, PPTX, etc.) on input.  Two output modes:

- page mode: emits pages/sections as TextDocument objects for
  downstream chunking (drop-in replacement for the unstructured decoder)
- hybrid mode: uses Docling's HybridChunker to emit Chunk objects
  directly, bypassing the downstream chunker

Supports both inline document data and fetching from librarian via
Pulsar for large documents.

Tables are preserved as HTML markup for better downstream extraction.
Images are stored in the librarian but not sent to the text pipeline.
"""

import os
os.environ.setdefault("DOCLING_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import io
import logging

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, DocumentStream, PdfFormatOption
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.chunking import HybridChunker

from ... schema import Chunk, Metadata
from ... schema import Triples, Triple, Term, IRI, LITERAL
from ... base import DocumentDecoderBase, ConsumerSpec, ProducerSpec

from ... provenance import (
    document_uri, chunk_uri as make_chunk_uri,
    derived_entity_triples, set_graph, GRAPH_SOURCE,
    TG_PAGE_NUMBER,
)

logger = logging.getLogger(__name__)

default_ident = "document-decoder"

MIME_EXTENSIONS = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/html": ".html",
    "text/markdown": ".md",
    "text/plain": ".md",
    "text/csv": ".csv",
}

PAGE_BASED_FORMATS = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


class Processor(DocumentDecoderBase):

    COMPONENT_NAME = "docling-decoder"
    COMPONENT_VERSION = "1.0.0"

    def __init__(self, **params):

        self.chunking_mode = params.get("chunking_mode", "page")
        self.chunk_max_tokens = params.get("chunk_max_tokens", 512)
        self.languages = params.get("languages", "eng").split(",")

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        pipeline_options.generate_page_images = True

        self.converter = DocumentConverter(
            allowed_formats=[
                InputFormat.PDF, InputFormat.DOCX, InputFormat.XLSX,
                InputFormat.PPTX, InputFormat.HTML, InputFormat.MD,
                InputFormat.CSV,
            ],
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                    backend=PyPdfiumDocumentBackend,
                ),
            },
        )

        super(Processor, self).__init__(**params)

        if self.chunking_mode == "hybrid":
            self.register_specification(
                ProducerSpec(
                    name="chunks",
                    schema=Chunk,
                )
            )

        logger.info(
            f"Docling decoder initialized (mode: {self.chunking_mode})"
        )

    def convert_document(self, blob, mime_type=None, name_hint="document"):
        suffix = MIME_EXTENSIONS.get(mime_type, ".bin")
        routing_filename = f"source_file{suffix}"

        buf = io.BytesIO(blob)
        stream = DocumentStream(name=routing_filename, stream=buf)

        result = self.converter.convert(stream, raises_on_error=True)

        if result.errors:
            logger.error(
                f"Docling backend failed processing pages for {name_hint}"
            )
            for err in result.errors:
                logger.error(
                    f"-> Conversion error: {err!r} "
                    f"attrs={vars(err) if hasattr(err, '__dict__') else 'N/A'}"
                )

            if result.document:
                logger.warning(
                    "Returning partially recovered layout context."
                )
                return result.document

            raise ValueError(
                f"Conversion completely failed for {name_hint}. "
                f"First error: {repr(result.errors[0])}"
            )

        logger.info(f"Docling conversion complete for {routing_filename}")
        return result.document

    def _get_page_texts(self, doc):
        page_map = {}

        for item, _level in doc.iterate_items():
            prov = getattr(item, 'prov', None)

            page_nos = set()
            if prov:
                for p in prov:
                    pg = getattr(p, 'page_no', None)
                    if pg is not None:
                        page_nos.add(pg)

            if not page_nos:
                page_nos.add(1)

            item_type = type(item).__name__

            for page_no in page_nos:
                if page_no not in page_map:
                    page_map[page_no] = {
                        "texts": [],
                        "table_count": 0,
                        "image_count": 0,
                    }

                if item_type == "PictureItem":
                    page_map[page_no]["image_count"] += 1
                    continue

                if item_type == "TableItem":
                    page_map[page_no]["table_count"] += 1
                    html = item.export_to_html(doc=doc)
                    if html:
                        page_map[page_no]["texts"].append(html)
                    continue

                text = getattr(item, 'text', None)
                if text and text.strip():
                    page_map[page_no]["texts"].append(text)

        for page_no in sorted(page_map.keys()):
            info = page_map[page_no]
            text = "\n\n".join(info["texts"])
            if text.strip():
                section_type = "text"
                if info["table_count"] > 0 and info["image_count"] == 0:
                    section_type = "table"
                elif info["image_count"] > 0 and info["table_count"] == 0:
                    section_type = "image"
                yield (text, page_no, section_type)

    def _get_full_text(self, doc):
        parts = []

        for item, _level in doc.iterate_items():
            item_type = type(item).__name__

            if item_type == "PictureItem":
                continue

            if item_type == "TableItem":
                html = item.export_to_html(doc=doc)
                if html:
                    parts.append(html)
                continue

            text = getattr(item, 'text', None)
            if text and text.strip():
                parts.append(text)

        full_text = "\n\n".join(parts)
        if full_text.strip():
            yield (full_text, None, "text")

    def decode_pages(self, blob, mime_type=None):

        doc = self.convert_document(blob, mime_type)

        is_page_based = mime_type in PAGE_BASED_FORMATS if mime_type else False

        if is_page_based:
            yield from self._get_page_texts(doc)
        else:
            yield from self._get_full_text(doc)

    async def on_message(self, msg, consumer, flow):

        if self.chunking_mode == "hybrid":
            await self._on_message_hybrid(msg, consumer, flow)
        else:
            await super().on_message(msg, consumer, flow)

    async def _on_message_hybrid(self, msg, consumer, flow):

        v = msg.value()

        logger.info(f"Decoding {v.metadata.id} (hybrid mode)...")

        blob, mime_type, source_doc_id = await self.fetch_blob(v, flow)
        doc_uri_str = document_uri(source_doc_id)

        try:
            doc = self.convert_document(
                blob, mime_type, name_hint=source_doc_id,
            )
        except Exception as e:
            logger.error(
                f"Failed to convert {source_doc_id}: "
                f"{type(e).__name__}: {e}",
                exc_info=True,
            )
            return

        chunker = HybridChunker(
            max_tokens=self.chunk_max_tokens,
        )

        chunks = chunker.chunk(doc)
        char_offset = 0

        for idx, chunk in enumerate(chunks):
            chunk_index = idx + 1
            text = chunker.serialize(chunk)

            page_numbers = None
            meta = getattr(chunk, 'meta', None)
            if meta:
                pn = getattr(meta, 'doc_items', None)
                if pn:
                    pages = set()
                    for di in pn:
                        for p in getattr(di, 'prov', []):
                            pg = getattr(p, 'page_no', None)
                            if pg is not None:
                                pages.add(pg)
                    if pages:
                        page_numbers = sorted(pages)

            if not text or not text.strip():
                continue

            c_uri = make_chunk_uri()
            chunk_content = text.encode("utf-8")
            char_length = len(text)
            primary_page = page_numbers[0] if page_numbers else None

            await flow.librarian.save_child_document(
                doc_id=c_uri,
                parent_id=source_doc_id,
                content=chunk_content,
                document_type="chunk",
                title=f"Chunk {chunk_index}",
            )

            prov_triples = derived_entity_triples(
                entity_uri=c_uri,
                parent_uri=doc_uri_str,
                component_name=self.COMPONENT_NAME,
                component_version=self.COMPONENT_VERSION,
                label=f"Chunk {chunk_index}",
                chunk_index=chunk_index,
                char_offset=char_offset,
                char_length=char_length,
                page_number=primary_page,
            )

            if page_numbers and len(page_numbers) > 1:
                for extra_page in page_numbers[1:]:
                    prov_triples.append(Triple(
                        s=Term(type=IRI, iri=c_uri),
                        p=Term(type=IRI, iri=TG_PAGE_NUMBER),
                        o=Term(type=LITERAL, value=str(extra_page)),
                    ))

            await flow("triples").send(Triples(
                metadata=Metadata(
                    id=c_uri,
                    root=v.metadata.root,
                    collection=v.metadata.collection,
                ),
                triples=set_graph(prov_triples, GRAPH_SOURCE),
            ))

            r = Chunk(
                metadata=Metadata(
                    id=c_uri,
                    root=v.metadata.root,
                    collection=v.metadata.collection,
                ),
                chunk=chunk_content,
                document_id=c_uri,
            )

            await flow("chunks").send(r)

            char_offset += len(text)

        logger.info("Document decoding complete (hybrid)")

    @staticmethod
    def add_args(parser):

        DocumentDecoderBase.add_args(parser)

        parser.add_argument(
            '--chunking-mode',
            default='page',
            choices=['page', 'hybrid'],
            help='Chunking mode: page emits TextDocument for downstream '
                 'chunker, hybrid uses Docling HybridChunker directly '
                 '(default: page)',
        )

        parser.add_argument(
            '--languages',
            default='eng',
            help='Comma-separated OCR language codes (default: eng)',
        )

        parser.add_argument(
            '--chunk-max-tokens',
            type=int,
            default=512,
            help='Max tokens per chunk for hybrid mode (default: 512)',
        )


def run():

    Processor.launch(default_ident, __doc__)
