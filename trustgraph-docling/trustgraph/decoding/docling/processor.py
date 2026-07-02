
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

import base64
import io
import logging

from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, DocumentStream
from docling.chunking import HybridChunker

from ... schema import Document, TextDocument, Chunk, Metadata
from ... schema import Triples
from ... base import FlowProcessor, ConsumerSpec, ProducerSpec, LibrarianSpec

from ... provenance import (
    document_uri, page_uri as make_page_uri,
    section_uri as make_section_uri, chunk_uri as make_chunk_uri,
    image_uri as make_image_uri,
    derived_entity_triples, set_graph, GRAPH_SOURCE,
)

COMPONENT_NAME = "docling-decoder"
COMPONENT_VERSION = "1.0.0"

logger = logging.getLogger(__name__)

default_ident = "document-decoder"

MIME_TO_FORMAT = {
    "application/pdf": InputFormat.PDF,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": InputFormat.DOCX,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": InputFormat.XLSX,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": InputFormat.PPTX,
    "text/html": InputFormat.HTML,
    "text/markdown": InputFormat.MD,
    "text/csv": InputFormat.CSV,
}

MIME_EXTENSIONS = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/html": ".html",
    "text/markdown": ".md",
    "text/plain": ".txt",
    "text/csv": ".csv",
}

PAGE_BASED_FORMATS = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id", default_ident)

        self.chunking_mode = params.get("chunking_mode", "page")
        self.chunk_max_tokens = params.get("chunk_max_tokens", 512)
        self.languages = params.get("languages", "eng").split(",")

        self.converter = DocumentConverter()

        super(Processor, self).__init__(
            **params | {
                "id": id,
            }
        )

        self.register_specification(
            ConsumerSpec(
                name="input",
                schema=Document,
                handler=self.on_message,
            )
        )

        self.register_specification(
            ProducerSpec(
                name="output",
                schema=TextDocument,
            )
        )

        if self.chunking_mode == "hybrid":
            self.register_specification(
                ProducerSpec(
                    name="chunks",
                    schema=Chunk,
                )
            )

        self.register_specification(
            ProducerSpec(
                name="triples",
                schema=Triples,
            )
        )

        self.register_specification(
            LibrarianSpec()
        )

        logger.info(
            f"Docling decoder initialized (mode: {self.chunking_mode})"
        )

    def convert_document(self, blob, mime_type=None, name_hint="document"):
        """
        Convert raw bytes to a DoclingDocument.

        Uses DocumentStream for in-memory processing — no temp files.
        """
        suffix = MIME_EXTENSIONS.get(mime_type, ".bin")
        filename = f"{name_hint}{suffix}"

        buf = io.BytesIO(blob)
        stream = DocumentStream(name=filename, stream=buf)

        result = self.converter.convert(stream)

        logger.info("Docling conversion complete")

        return result.document

    def get_page_texts(self, doc):
        """
        Extract text grouped by page from a DoclingDocument.

        Returns list of (page_number, text, table_count, image_count).
        """
        md = doc.export_to_markdown(image_placeholder="")

        pages = []
        page_map = {}

        for item, _level in doc.iterate_items():
            prov = getattr(item, 'prov', None)
            if not prov:
                continue

            for p in prov:
                page_no = getattr(p, 'page_no', None)
                if page_no is not None and page_no not in page_map:
                    page_map[page_no] = {
                        "texts": [],
                        "table_count": 0,
                        "image_count": 0,
                    }

                if page_no is None:
                    page_no = 1
                    if page_no not in page_map:
                        page_map[page_no] = {
                            "texts": [],
                            "table_count": 0,
                            "image_count": 0,
                        }

                item_type = type(item).__name__

                if item_type == "PictureItem":
                    page_map[page_no]["image_count"] += 1
                    continue

                if item_type == "TableItem":
                    page_map[page_no]["table_count"] += 1
                    html = item.export_to_html()
                    if html:
                        page_map[page_no]["texts"].append(html)
                    continue

                text = item.export_to_markdown()
                if text and text.strip():
                    page_map[page_no]["texts"].append(text)

        for page_no in sorted(page_map.keys()):
            info = page_map[page_no]
            text = "\n\n".join(info["texts"])
            if text.strip():
                pages.append((
                    page_no, text,
                    info["table_count"], info["image_count"],
                ))

        if not pages and md.strip():
            pages.append((1, md, 0, 0))

        return pages

    def get_full_text(self, doc):
        """
        Export the full document as markdown text.

        Tables are exported as HTML for structural fidelity.
        """
        parts = []
        table_count = 0
        image_count = 0

        for item, _level in doc.iterate_items():
            item_type = type(item).__name__

            if item_type == "PictureItem":
                image_count += 1
                continue

            if item_type == "TableItem":
                table_count += 1
                html = item.export_to_html()
                if html:
                    parts.append(html)
                continue

            text = item.export_to_markdown()
            if text and text.strip():
                parts.append(text)

        return "\n\n".join(parts), table_count, image_count

    async def emit_section(self, text, parent_doc_id, doc_uri_str,
                           metadata, flow, mime_type=None,
                           page_number=None, section_index=None,
                           table_count=0, image_count=0):
        """
        Save a page or section to the librarian, emit provenance,
        and send a TextDocument downstream.
        """
        if not text.strip():
            return None

        is_page = page_number is not None
        char_length = len(text)

        if is_page:
            entity_uri = make_page_uri()
            label = f"Page {page_number}"
        else:
            entity_uri = make_section_uri()
            label = f"Section {section_index}" if section_index else "Section"

        doc_id = entity_uri
        content = text.encode("utf-8")

        await flow.librarian.save_child_document(
            doc_id=doc_id,
            parent_id=parent_doc_id,
            content=content,
            document_type="page" if is_page else "section",
            title=label,
        )

        prov_triples = derived_entity_triples(
            entity_uri=entity_uri,
            parent_uri=doc_uri_str,
            component_name=COMPONENT_NAME,
            component_version=COMPONENT_VERSION,
            label=label,
            page_number=page_number,
            section=not is_page,
            char_length=char_length,
            mime_type=mime_type,
            table_count=table_count if table_count > 0 else None,
            image_count=image_count if image_count > 0 else None,
        )

        await flow("triples").send(Triples(
            metadata=Metadata(
                id=entity_uri,
                root=metadata.root,
                collection=metadata.collection,
            ),
            triples=set_graph(prov_triples, GRAPH_SOURCE),
        ))

        r = TextDocument(
            metadata=Metadata(
                id=entity_uri,
                root=metadata.root,
                collection=metadata.collection,
            ),
            document_id=doc_id,
            text=b"",
        )

        await flow("output").send(r)

        return entity_uri

    async def emit_chunk(self, text, chunk_index, parent_doc_id,
                         doc_uri_str, metadata, flow,
                         page_numbers=None, char_offset=None):
        """
        Save a chunk to the librarian, emit provenance, and send
        a Chunk message downstream.
        """
        if not text.strip():
            return None

        c_uri = make_chunk_uri()
        chunk_content = text.encode("utf-8")
        char_length = len(text)

        page_number = page_numbers[0] if page_numbers else None

        await flow.librarian.save_child_document(
            doc_id=c_uri,
            parent_id=parent_doc_id,
            content=chunk_content,
            document_type="chunk",
            title=f"Chunk {chunk_index}",
        )

        prov_triples = derived_entity_triples(
            entity_uri=c_uri,
            parent_uri=doc_uri_str,
            component_name=COMPONENT_NAME,
            component_version=COMPONENT_VERSION,
            label=f"Chunk {chunk_index}",
            chunk_index=chunk_index,
            char_offset=char_offset,
            char_length=char_length,
            page_number=page_number,
        )

        await flow("triples").send(Triples(
            metadata=Metadata(
                id=c_uri,
                root=metadata.root,
                collection=metadata.collection,
            ),
            triples=set_graph(prov_triples, GRAPH_SOURCE),
        ))

        r = Chunk(
            metadata=Metadata(
                id=c_uri,
                root=metadata.root,
                collection=metadata.collection,
            ),
            chunk=chunk_content,
            document_id=c_uri,
        )

        await flow("chunks").send(r)

        return c_uri

    async def process_page_mode(self, doc, source_doc_id, doc_uri_str,
                                metadata, flow, mime_type):
        """Page mode: emit pages or sections as TextDocument."""
        is_page_based = mime_type in PAGE_BASED_FORMATS if mime_type else False

        if is_page_based:
            pages = self.get_page_texts(doc)
            for page_num, text, table_count, image_count in pages:
                await self.emit_section(
                    text, source_doc_id, doc_uri_str,
                    metadata, flow,
                    mime_type=mime_type, page_number=page_num,
                    table_count=table_count, image_count=image_count,
                )
        else:
            text, table_count, image_count = self.get_full_text(doc)
            if text.strip():
                await self.emit_section(
                    text, source_doc_id, doc_uri_str,
                    metadata, flow,
                    mime_type=mime_type, section_index=1,
                    table_count=table_count, image_count=image_count,
                )

    async def process_hybrid_mode(self, doc, source_doc_id, doc_uri_str,
                                  metadata, flow, mime_type):
        """Hybrid mode: use Docling HybridChunker, emit Chunk directly."""
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

            await self.emit_chunk(
                text, chunk_index, source_doc_id, doc_uri_str,
                metadata, flow,
                page_numbers=page_numbers,
                char_offset=char_offset,
            )

            char_offset += len(text)

    async def on_message(self, msg, consumer, flow):

        logger.debug("Document message received")

        v = msg.value()

        logger.info(f"Decoding {v.metadata.id}...")

        mime_type = None

        if v.document_id:
            logger.info(
                f"Fetching document {v.document_id} from librarian..."
            )

            doc_meta = await flow.librarian.fetch_document_metadata(
                document_id=v.document_id,
            )
            mime_type = doc_meta.kind if doc_meta else None

            content = await flow.librarian.fetch_document_content(
                document_id=v.document_id,
            )

            if isinstance(content, str):
                content = content.encode('utf-8')
            blob = base64.b64decode(content)

            logger.info(
                f"Fetched {len(blob)} bytes, mime: {mime_type}"
            )
        else:
            blob = base64.b64decode(v.data)

        source_doc_id = v.document_id or v.metadata.id
        doc_uri_str = document_uri(source_doc_id)

        try:
            doc = self.convert_document(
                blob, mime_type, name_hint=source_doc_id,
            )
        except Exception as e:
            logger.error(
                f"Failed to convert {source_doc_id}: "
                f"{type(e).__name__}: {e}"
            )
            return

        if self.chunking_mode == "hybrid":
            await self.process_hybrid_mode(
                doc, source_doc_id, doc_uri_str,
                v.metadata, flow, mime_type,
            )
        else:
            await self.process_page_mode(
                doc, source_doc_id, doc_uri_str,
                v.metadata, flow, mime_type,
            )

        logger.info("Document decoding complete")

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

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
