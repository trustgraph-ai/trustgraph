
"""
Universal document decoder powered by the unstructured library.

Accepts documents in any common format (PDF, DOCX, XLSX, HTML, Markdown,
plain text, PPTX, etc.) on input, outputs pages or sections as text
as separate output objects.

Supports both inline document data and fetching from librarian via Pulsar
for large documents. Fetches document metadata from the librarian to
determine mime type for format detection.

Tables are preserved as HTML markup for better downstream extraction.
Images are stored in the librarian but not sent to the text pipeline.
"""

import base64
import logging
import magic
import tempfile
import os

from unstructured.partition.auto import partition

from ... schema import Document, TextDocument, Metadata
from ... schema import librarian_request_queue, librarian_response_queue
from ... schema import Triples
from ... base import FlowProcessor, ConsumerSpec, ProducerSpec, LibrarianClient

from ... provenance import (
    document_uri, page_uri as make_page_uri,
    section_uri as make_section_uri, image_uri as make_image_uri,
    derived_entity_triples, set_graph, GRAPH_SOURCE,
)

from . strategies import get_strategy

# Component identification for provenance
COMPONENT_NAME = "universal-decoder"
COMPONENT_VERSION = "1.0.0"

# Module logger
logger = logging.getLogger(__name__)

default_ident = "document-decoder"

default_librarian_request_queue = librarian_request_queue
default_librarian_response_queue = librarian_response_queue

# Mime type to unstructured content_type mapping
# unstructured auto-detects most formats, but we pass the hint when available
MIME_EXTENSIONS = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/html": ".html",
    "text/markdown": ".md",
    "text/plain": ".txt",
    "text/csv": ".csv",
    "text/tab-separated-values": ".tsv",
    "application/rtf": ".rtf",
    "text/x-rst": ".rst",
    "application/vnd.oasis.opendocument.text": ".odt",
}

# Formats that have natural page boundaries
PAGE_BASED_FORMATS = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
}


def assemble_section_text(elements):
    """
    Assemble text from a list of unstructured elements.

    - Text elements: plain text, joined with double newlines
    - Table elements: HTML table markup from text_as_html
    - Image elements: skipped (stored separately, not in text output)

    Returns:
        tuple: (assembled_text, element_types_set, table_count, image_count)
    """
    parts = []
    element_types = set()
    table_count = 0
    image_count = 0

    for el in elements:
        category = getattr(el, 'category', 'UncategorizedText')
        element_types.add(category)

        if category == 'Image':
            image_count += 1
            continue  # Images are NOT included in text output

        if category == 'Table':
            table_count += 1
            # Prefer HTML representation for tables
            html = getattr(el.metadata, 'text_as_html', None) if hasattr(el, 'metadata') else None
            if html:
                parts.append(html)
            else:
                # Fallback to plain text
                text = getattr(el, 'text', '') or ''
                if text:
                    parts.append(text)
        else:
            text = getattr(el, 'text', '') or ''
            if text:
                parts.append(text)

    return '\n\n'.join(parts), element_types, table_count, image_count


class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id", default_ident)

        self.partition_strategy = params.get("strategy", "auto")
        self.languages = params.get("languages", "eng").split(",")
        self.section_strategy_name = params.get(
            "section_strategy", "whole-document"
        )
        self.section_element_count = params.get("section_element_count", 20)
        self.section_max_size = params.get("section_max_size", 4000)
        self.section_within_pages = params.get("section_within_pages", False)

        self.section_strategy = get_strategy(self.section_strategy_name)

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

        self.register_specification(
            ProducerSpec(
                name="triples",
                schema=Triples,
            )
        )

        # Librarian client
        self.librarian = LibrarianClient(
            id=id, backend=self.pubsub, taskgroup=self.taskgroup,
        )

        logger.info("Universal decoder initialized")

    async def start(self):
        await super(Processor, self).start()
        await self.librarian.start()

    def extract_elements(self, blob, mime_type=None):
        """
        Extract elements from a document using unstructured.

        Args:
            blob: Raw document bytes
            mime_type: Optional mime type hint

        Returns:
            List of unstructured Element objects
        """
        # Determine file extension for unstructured
        suffix = MIME_EXTENSIONS.get(mime_type, "") if mime_type else ""
        if not suffix:
            suffix = ".bin"

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix
        ) as fp:
            fp.write(blob)
            temp_path = fp.name

        try:
            kwargs = {
                "filename": temp_path,
                "strategy": self.partition_strategy,
                "languages": self.languages,
            }

            # For hi_res strategy, request image extraction
            if self.partition_strategy == "hi_res":
                kwargs["extract_image_block_to_payload"] = True

            elements = partition(**kwargs)

            logger.info(
                f"Extracted {len(elements)} elements "
                f"(strategy: {self.partition_strategy})"
            )

            return elements

        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    def group_by_page(self, elements):
        """
        Group elements by page number.

        Returns list of (page_number, elements) tuples.
        """
        pages = {}

        for el in elements:
            page_num = getattr(
                el.metadata, 'page_number', None
            ) if hasattr(el, 'metadata') else None
            if page_num is None:
                page_num = 1
            if page_num not in pages:
                pages[page_num] = []
            pages[page_num].append(el)

        return sorted(pages.items())

    async def emit_section(self, elements, parent_doc_id, doc_uri_str,
                           metadata, flow, mime_type=None,
                           page_number=None, section_index=None):
        """
        Process a group of elements as a page or section.

        Assembles text, saves to librarian, emits provenance, sends
        TextDocument downstream. Returns the entity URI.
        """
        text, element_types, table_count, image_count = (
            assemble_section_text(elements)
        )

        if not text.strip():
            logger.debug("Skipping empty section")
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
        page_content = text.encode("utf-8")

        # Save to librarian
        await self.librarian.save_child_document(
            doc_id=doc_id,
            parent_id=parent_doc_id,
            workspace=flow.workspace,
            content=page_content,
            document_type="page" if is_page else "section",
            title=label,
        )

        # Emit provenance triples
        element_types_str = ",".join(sorted(element_types)) if element_types else None

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
            element_types=element_types_str,
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

        # Send TextDocument downstream (chunker will fetch from librarian)
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

    async def emit_image(self, element, parent_uri, parent_doc_id,
                         metadata, flow, mime_type=None, page_number=None):
        """
        Store an image element in the librarian with provenance.

        Images are stored but NOT sent downstream to the text pipeline.
        """
        img_uri = make_image_uri()

        # Get image data
        img_data = None
        if hasattr(element, 'metadata'):
            img_data = getattr(element.metadata, 'image_base64', None)

        if not img_data:
            # No image payload available, just record provenance
            logger.debug("Image element without payload, recording provenance only")
            img_content = b""
            img_kind = "image/unknown"
        else:
            if isinstance(img_data, str):
                img_content = base64.b64decode(img_data)
            else:
                img_content = img_data
            img_kind = "image/png"  # unstructured typically extracts as PNG

        # Save to librarian
        if img_content:
            await self.librarian.save_child_document(
                doc_id=img_uri,
                parent_id=parent_doc_id,
                workspace=flow.workspace,
                content=img_content,
                document_type="image",
                title=f"Image from page {page_number}" if page_number else "Image",
                kind=img_kind,
            )

        # Emit provenance triples
        prov_triples = derived_entity_triples(
            entity_uri=img_uri,
            parent_uri=parent_uri,
            component_name=COMPONENT_NAME,
            component_version=COMPONENT_VERSION,
            label=f"Image from page {page_number}" if page_number else "Image",
            image=True,
            page_number=page_number,
            mime_type=mime_type,
        )

        await flow("triples").send(Triples(
            metadata=Metadata(
                id=img_uri,
                root=metadata.root,
                collection=metadata.collection,
            ),
            triples=set_graph(prov_triples, GRAPH_SOURCE),
        ))

    async def on_message(self, msg, consumer, flow):

        logger.debug("Document message received")

        v = msg.value()

        logger.info(f"Decoding {v.metadata.id}...")

        # Determine content and mime type
        mime_type = None

        if v.document_id:
            # Librarian path: fetch metadata then content
            logger.info(
                f"Fetching document {v.document_id} from librarian..."
            )

            doc_meta = await self.librarian.fetch_document_metadata(
                document_id=v.document_id,
                workspace=flow.workspace,
            )
            mime_type = doc_meta.kind if doc_meta else None

            content = await self.librarian.fetch_document_content(
                document_id=v.document_id,
                workspace=flow.workspace,
            )

            if isinstance(content, str):
                content = content.encode('utf-8')
            blob = base64.b64decode(content)

            logger.info(
                f"Fetched {len(blob)} bytes, mime: {mime_type}"
            )
        else:
            # Inline path: detect format from content
            blob = base64.b64decode(v.data)
            try:
                mime_type = magic.from_buffer(blob, mime=True)
                logger.info(f"Detected mime type: {mime_type}")
            except Exception as e:
                logger.warning(f"Could not detect mime type: {e}")

        # Get the source document ID
        source_doc_id = v.document_id or v.metadata.id
        doc_uri_str = document_uri(source_doc_id)

        # Extract elements using unstructured
        elements = self.extract_elements(blob, mime_type)

        if not elements:
            logger.warning("No elements extracted from document")
            return

        # Determine if this is a page-based format
        is_page_based = mime_type in PAGE_BASED_FORMATS if mime_type else False

        # Also check if elements actually have page numbers
        if not is_page_based:
            has_pages = any(
                getattr(el.metadata, 'page_number', None) is not None
                for el in elements
                if hasattr(el, 'metadata')
            )
            if has_pages:
                is_page_based = True

        if is_page_based:
            # Group by page
            page_groups = self.group_by_page(elements)

            for page_num, page_elements in page_groups:

                # Extract and store images separately
                image_elements = [
                    el for el in page_elements
                    if getattr(el, 'category', '') == 'Image'
                ]
                text_elements = [
                    el for el in page_elements
                    if getattr(el, 'category', '') != 'Image'
                ]

                # Emit the page as a text section
                page_uri_str = await self.emit_section(
                    text_elements, source_doc_id, doc_uri_str,
                    v.metadata, flow,
                    mime_type=mime_type, page_number=page_num,
                )

                # Store images (not sent to text pipeline)
                for img_el in image_elements:
                    await self.emit_image(
                        img_el,
                        page_uri_str or doc_uri_str,
                        source_doc_id,
                        v.metadata, flow,
                        mime_type=mime_type, page_number=page_num,
                    )

        else:
            # Non-page format: use section strategy

            # Separate images from text elements
            image_elements = [
                el for el in elements
                if getattr(el, 'category', '') == 'Image'
            ]
            text_elements = [
                el for el in elements
                if getattr(el, 'category', '') != 'Image'
            ]

            # Apply section strategy to text elements
            strategy_kwargs = {
                'element_count': self.section_element_count,
                'max_size': self.section_max_size,
            }
            groups = self.section_strategy(text_elements, **strategy_kwargs)

            for idx, group in enumerate(groups):
                section_idx = idx + 1

                await self.emit_section(
                    group, source_doc_id, doc_uri_str,
                    v.metadata, flow,
                    mime_type=mime_type, section_index=section_idx,
                )

            # Store images (not sent to text pipeline)
            for img_el in image_elements:
                await self.emit_image(
                    img_el, doc_uri_str, source_doc_id,
                    v.metadata, flow,
                    mime_type=mime_type,
                )

        logger.info("Document decoding complete")

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

        parser.add_argument(
            '--strategy',
            default='auto',
            choices=['auto', 'hi_res', 'fast'],
            help='Partitioning strategy (default: auto)',
        )

        parser.add_argument(
            '--languages',
            default='eng',
            help='Comma-separated OCR language codes (default: eng)',
        )

        parser.add_argument(
            '--section-strategy',
            default='whole-document',
            choices=[
                'whole-document', 'heading', 'element-type', 'count', 'size'
            ],
            help='Section grouping strategy for non-page formats '
                 '(default: whole-document)',
        )

        parser.add_argument(
            '--section-element-count',
            type=int,
            default=20,
            help='Elements per section for count strategy (default: 20)',
        )

        parser.add_argument(
            '--section-max-size',
            type=int,
            default=4000,
            help='Max chars per section for size strategy (default: 4000)',
        )

        parser.add_argument(
            '--section-within-pages',
            action='store_true',
            default=False,
            help='Apply section strategy within pages too (default: false)',
        )

        parser.add_argument(
            '--librarian-request-queue',
            default=default_librarian_request_queue,
            help=f'Librarian request queue '
                 f'(default: {default_librarian_request_queue})',
        )

        parser.add_argument(
            '--librarian-response-queue',
            default=default_librarian_response_queue,
            help=f'Librarian response queue '
                 f'(default: {default_librarian_response_queue})',
        )


def run():

    Processor.launch(default_ident, __doc__)
