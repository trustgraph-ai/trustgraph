
import asyncio
import base64
import logging

from .. schema import Document, TextDocument, Metadata
from .. schema import Triples
from .. schema import DocumentDecoderRequest, DocumentDecoderResponse, Error
from . flow_processor import FlowProcessor
from . consumer_spec import ConsumerSpec
from . producer_spec import ProducerSpec
from . librarian_spec import LibrarianSpec

from .. provenance import (
    document_uri, page_uri as make_page_uri,
    section_uri as make_section_uri,
    derived_entity_triples, set_graph, GRAPH_SOURCE,
)

logger = logging.getLogger(__name__)

default_ident = "document-decoder"


class DocumentDecoderBase(FlowProcessor):

    COMPONENT_NAME = "decoder"
    COMPONENT_VERSION = "1.0.0"

    def __init__(self, **params):

        id = params.get("id", default_ident)

        super(DocumentDecoderBase, self).__init__(
            **params | {"id": id}
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

        self.register_specification(
            LibrarianSpec()
        )

        self.register_specification(
            ConsumerSpec(
                name="request",
                schema=DocumentDecoderRequest,
                handler=self.on_decode_request,
            )
        )

        self.register_specification(
            ProducerSpec(
                name="response",
                schema=DocumentDecoderResponse,
            )
        )

    def decode_pages(self, blob, mime_type=None):
        """
        Yield (text, page_number, section_type) tuples from raw
        document bytes.

        page_number is 1-indexed, or None for non-page-based content.
        section_type is "text", "table", or "image".

        Subclass must implement.
        """
        raise NotImplementedError

    async def _decode_pages_async(self, blob, mime_type):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: list(self.decode_pages(blob, mime_type))
        )

    async def fetch_blob(self, msg_value, flow):
        """
        Fetch document content from librarian or inline data.
        Returns (blob, mime_type, source_doc_id).
        """
        v = msg_value
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

        return blob, mime_type, source_doc_id

    async def on_message(self, msg, consumer, flow):

        v = msg.value()

        logger.info(f"Decoding {v.metadata.id}...")

        blob, mime_type, source_doc_id = await self.fetch_blob(v, flow)
        doc_uri_str = document_uri(source_doc_id)

        try:
            pages = await self._decode_pages_async(blob, mime_type)
        except Exception as e:
            logger.error(
                f"Failed to decode {source_doc_id}: "
                f"{type(e).__name__}: {e}",
                exc_info=True,
            )
            return

        for text, page_number, section_type in pages:
            if not text or not text.strip():
                continue

            is_page = page_number is not None

            if is_page:
                entity_uri = make_page_uri()
                label = f"Page {page_number}"
            else:
                entity_uri = make_section_uri()
                label = "Section"

            content = text.encode("utf-8")

            await flow.librarian.save_child_document(
                doc_id=entity_uri,
                parent_id=source_doc_id,
                content=content,
                document_type="page" if is_page else "section",
                title=label,
            )

            prov_triples = derived_entity_triples(
                entity_uri=entity_uri,
                parent_uri=doc_uri_str,
                component_name=self.COMPONENT_NAME,
                component_version=self.COMPONENT_VERSION,
                label=label,
                page_number=page_number,
                section=not is_page,
                char_length=len(text),
            )

            await flow("triples").send(Triples(
                metadata=Metadata(
                    id=entity_uri,
                    root=v.metadata.root,
                    collection=v.metadata.collection,
                ),
                triples=set_graph(prov_triples, GRAPH_SOURCE),
            ))

            r = TextDocument(
                metadata=Metadata(
                    id=entity_uri,
                    root=v.metadata.root,
                    collection=v.metadata.collection,
                ),
                document_id=entity_uri,
                text=content,
            )

            await flow("output").send(r)

        logger.info("Document decoding complete")

    async def on_decode_request(self, msg, consumer, flow):

        id = msg.properties()["id"]

        try:

            v = msg.value()
            document_id = v.document_id
            mode = v.mode or "page"

            logger.info(
                f"Decode request {id}: document={document_id} mode={mode}"
            )

            doc_meta = await flow.librarian.fetch_document_metadata(
                document_id=document_id,
            )
            mime_type = doc_meta.kind if doc_meta else None

            content = await flow.librarian.fetch_document_content(
                document_id=document_id,
            )

            if isinstance(content, str):
                content = content.encode('utf-8')
            blob = base64.b64decode(content)

            logger.info(
                f"Decode request {id}: fetched {len(blob)} bytes, "
                f"mime={mime_type}"
            )

            pages = await self._decode_pages_async(blob, mime_type)

            for text, page_number, section_type in pages:
                if not text or not text.strip():
                    continue

                section_id = (
                    make_page_uri() if page_number
                    else make_section_uri()
                )
                section_content = text.encode("utf-8")

                await flow.librarian.save_child_document(
                    doc_id=section_id,
                    parent_id=document_id,
                    content=section_content,
                    document_type="page" if page_number else "section",
                    title=(
                        f"Page {page_number}" if page_number
                        else "Section"
                    ),
                )

                await flow("response").send(
                    DocumentDecoderResponse(
                        document_id=section_id,
                        page=page_number or 0,
                        section_type=section_type,
                    ),
                    properties={"id": id},
                )

            await flow("response").send(
                DocumentDecoderResponse(end_of_stream=True),
                properties={"id": id},
            )

            logger.info(f"Decode request {id}: complete")

        except Exception as e:

            logger.error(
                f"Decode request {id} failed: {type(e).__name__}: {e}",
                exc_info=True,
            )

            await flow("response").send(
                DocumentDecoderResponse(
                    error=Error(
                        type="document-decode-error",
                        message=str(e),
                    ),
                    end_of_stream=True,
                ),
                properties={"id": id},
            )

    @staticmethod
    def add_args(parser):
        FlowProcessor.add_args(parser)
