
"""
Simple decoder, accepts PDF documents on input, outputs pages from the
PDF document as text as separate output objects.

Supports both inline document data and fetching from librarian via Pulsar
for large documents.
"""

import os
import tempfile
import base64
import logging
from langchain_community.document_loaders import PyPDFLoader

from ... schema import Document, TextDocument, Metadata
from ... schema import librarian_request_queue, librarian_response_queue
from ... schema import Triples
from ... base import FlowProcessor, ConsumerSpec, ProducerSpec, LibrarianClient

from ... provenance import (
    document_uri, page_uri as make_page_uri, derived_entity_triples,
    set_graph, GRAPH_SOURCE,
)

# Component identification for provenance
COMPONENT_NAME = "pdf-decoder"
COMPONENT_VERSION = "1.0.0"

# Module logger
logger = logging.getLogger(__name__)

default_ident = "document-decoder"

default_librarian_request_queue = librarian_request_queue
default_librarian_response_queue = librarian_response_queue


class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id", default_ident)

        super(Processor, self).__init__(
            **params | {
                "id": id,
            }
        )

        self.register_specification(
            ConsumerSpec(
                name = "input",
                schema = Document,
                handler = self.on_message,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "output",
                schema = TextDocument,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "triples",
                schema = Triples,
            )
        )

        # Librarian client
        self.librarian = LibrarianClient(
            id=id, backend=self.pubsub, taskgroup=self.taskgroup,
        )

        logger.info("PDF decoder initialized")

    async def start(self):
        await super(Processor, self).start()
        await self.librarian.start()

    async def on_message(self, msg, consumer, flow):

        logger.debug("PDF message received")

        v = msg.value()

        logger.info(f"Decoding PDF {v.metadata.id}...")

        # Check MIME type if fetching from librarian
        if v.document_id:
            doc_meta = await self.librarian.fetch_document_metadata(
                document_id=v.document_id,
                user=v.metadata.user,
            )
            if doc_meta and doc_meta.kind and doc_meta.kind != "application/pdf":
                logger.error(
                    f"Unsupported MIME type: {doc_meta.kind}. "
                    f"PDF decoder only handles application/pdf. "
                    f"Ignoring document {v.metadata.id}."
                )
                return

        with tempfile.NamedTemporaryFile(delete_on_close=False, suffix='.pdf') as fp:
            temp_path = fp.name

            # Check if we should fetch from librarian or use inline data
            if v.document_id:
                # Fetch from librarian via Pulsar
                logger.info(f"Fetching document {v.document_id} from librarian...")
                fp.close()

                content = await self.librarian.fetch_document_content(
                    document_id=v.document_id,
                    user=v.metadata.user,
                )

                # Content is base64 encoded
                if isinstance(content, str):
                    content = content.encode('utf-8')
                decoded_content = base64.b64decode(content)

                with open(temp_path, 'wb') as f:
                    f.write(decoded_content)

                logger.info(f"Fetched {len(decoded_content)} bytes from librarian")
            else:
                # Use inline data (backward compatibility)
                fp.write(base64.b64decode(v.data))
                fp.close()

            loader = PyPDFLoader(temp_path)
            pages = loader.load()

            # Get the source document ID
            source_doc_id = v.document_id or v.metadata.id

            for ix, page in enumerate(pages):
                page_num = ix + 1  # 1-indexed page numbers

                logger.debug(f"Processing page {page_num}")

                # Generate unique page ID
                pg_uri = make_page_uri()
                page_doc_id = pg_uri
                page_content = page.page_content.encode("utf-8")

                # Save page as child document in librarian
                await self.librarian.save_child_document(
                    doc_id=page_doc_id,
                    parent_id=source_doc_id,
                    user=v.metadata.user,
                    content=page_content,
                    document_type="page",
                    title=f"Page {page_num}",
                )

                # Emit provenance triples (stored in source graph for separation from core knowledge)
                doc_uri = document_uri(source_doc_id)

                prov_triples = derived_entity_triples(
                    entity_uri=pg_uri,
                    parent_uri=doc_uri,
                    component_name=COMPONENT_NAME,
                    component_version=COMPONENT_VERSION,
                    label=f"Page {page_num}",
                    page_number=page_num,
                )

                await flow("triples").send(Triples(
                    metadata=Metadata(
                        id=pg_uri,
                        root=v.metadata.root,
                        user=v.metadata.user,
                        collection=v.metadata.collection,
                    ),
                    triples=set_graph(prov_triples, GRAPH_SOURCE),
                ))

                # Forward page document ID to chunker
                # Chunker will fetch content from librarian
                r = TextDocument(
                    metadata=Metadata(
                        id=pg_uri,
                        root=v.metadata.root,
                        user=v.metadata.user,
                        collection=v.metadata.collection,
                    ),
                    document_id=page_doc_id,
                    text=b"",  # Empty, chunker will fetch from librarian
                )

                await flow("output").send(r)

        # Clean up temp file
        try:
            os.unlink(temp_path)
        except OSError:
            pass

        logger.debug("PDF decoding complete")

    @staticmethod
    def add_args(parser):
        FlowProcessor.add_args(parser)

        parser.add_argument(
            '--librarian-request-queue',
            default=default_librarian_request_queue,
            help=f'Librarian request queue (default: {default_librarian_request_queue})',
        )

        parser.add_argument(
            '--librarian-response-queue',
            default=default_librarian_response_queue,
            help=f'Librarian response queue (default: {default_librarian_response_queue})',
        )

def run():

    Processor.launch(default_ident, __doc__)
