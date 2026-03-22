
"""
Simple decoder, accepts PDF documents on input, outputs pages from the
PDF document as text as separate output objects.

Supports both inline document data and fetching from librarian via Pulsar
for large documents.
"""

import asyncio
import base64
import logging
import uuid
import pytesseract
from pdf2image import convert_from_bytes

from ... schema import Document, TextDocument, Metadata
from ... schema import LibrarianRequest, LibrarianResponse, DocumentMetadata
from ... schema import librarian_request_queue, librarian_response_queue
from ... schema import Triples
from ... base import FlowProcessor, ConsumerSpec, ProducerSpec
from ... base import Consumer, Producer, ConsumerMetrics, ProducerMetrics

from ... provenance import (
    document_uri, page_uri as make_page_uri, derived_entity_triples,
    set_graph, GRAPH_SOURCE,
)

# Component identification for provenance
COMPONENT_NAME = "tesseract-ocr-decoder"
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

        # Librarian client for fetching document content
        librarian_request_q = params.get(
            "librarian_request_queue", default_librarian_request_queue
        )
        librarian_response_q = params.get(
            "librarian_response_queue", default_librarian_response_queue
        )

        librarian_request_metrics = ProducerMetrics(
            processor = id, flow = None, name = "librarian-request"
        )

        self.librarian_request_producer = Producer(
            backend = self.pubsub,
            topic = librarian_request_q,
            schema = LibrarianRequest,
            metrics = librarian_request_metrics,
        )

        librarian_response_metrics = ConsumerMetrics(
            processor = id, flow = None, name = "librarian-response"
        )

        self.librarian_response_consumer = Consumer(
            taskgroup = self.taskgroup,
            backend = self.pubsub,
            flow = None,
            topic = librarian_response_q,
            subscriber = f"{id}-librarian",
            schema = LibrarianResponse,
            handler = self.on_librarian_response,
            metrics = librarian_response_metrics,
        )

        # Pending librarian requests: request_id -> asyncio.Future
        self.pending_requests = {}

        logger.info("PDF OCR processor initialized")

    async def start(self):
        await super(Processor, self).start()
        await self.librarian_request_producer.start()
        await self.librarian_response_consumer.start()

    async def on_librarian_response(self, msg, consumer, flow):
        """Handle responses from the librarian service."""
        response = msg.value()
        request_id = msg.properties().get("id")

        if request_id and request_id in self.pending_requests:
            future = self.pending_requests.pop(request_id)
            future.set_result(response)
        else:
            logger.warning(f"Received unexpected librarian response: {request_id}")

    async def fetch_document_metadata(self, document_id, user, timeout=120):
        """
        Fetch document metadata from librarian via Pulsar.
        """
        request_id = str(uuid.uuid4())

        request = LibrarianRequest(
            operation="get-document-metadata",
            document_id=document_id,
            user=user,
        )

        future = asyncio.get_event_loop().create_future()
        self.pending_requests[request_id] = future

        try:
            await self.librarian_request_producer.send(
                request, properties={"id": request_id}
            )

            response = await asyncio.wait_for(future, timeout=timeout)

            if response.error:
                raise RuntimeError(
                    f"Librarian error: {response.error.type}: {response.error.message}"
                )

            return response.document_metadata

        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            raise RuntimeError(f"Timeout fetching metadata for {document_id}")

    async def fetch_document_content(self, document_id, user, timeout=120):
        """
        Fetch document content from librarian via Pulsar.
        """
        request_id = str(uuid.uuid4())

        request = LibrarianRequest(
            operation="get-document-content",
            document_id=document_id,
            user=user,
        )

        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self.pending_requests[request_id] = future

        try:
            # Send request
            await self.librarian_request_producer.send(
                request, properties={"id": request_id}
            )

            # Wait for response
            response = await asyncio.wait_for(future, timeout=timeout)

            if response.error:
                raise RuntimeError(
                    f"Librarian error: {response.error.type}: {response.error.message}"
                )

            return response.content

        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            raise RuntimeError(f"Timeout fetching document {document_id}")

    async def save_child_document(self, doc_id, parent_id, user, content,
                                   document_type="page", title=None, timeout=120):
        """
        Save a child document to the librarian.
        """
        request_id = str(uuid.uuid4())

        doc_metadata = DocumentMetadata(
            id=doc_id,
            user=user,
            kind="text/plain",
            title=title or doc_id,
            parent_id=parent_id,
            document_type=document_type,
        )

        request = LibrarianRequest(
            operation="add-child-document",
            document_metadata=doc_metadata,
            content=base64.b64encode(content).decode("utf-8"),
        )

        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self.pending_requests[request_id] = future

        try:
            # Send request
            await self.librarian_request_producer.send(
                request, properties={"id": request_id}
            )

            # Wait for response
            response = await asyncio.wait_for(future, timeout=timeout)

            if response.error:
                raise RuntimeError(
                    f"Librarian error saving child document: {response.error.type}: {response.error.message}"
                )

            return doc_id

        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            raise RuntimeError(f"Timeout saving child document {doc_id}")

    async def on_message(self, msg, consumer, flow):

        logger.info("PDF message received")

        v = msg.value()

        logger.info(f"Decoding {v.metadata.id}...")

        # Check MIME type if fetching from librarian
        if v.document_id:
            doc_meta = await self.fetch_document_metadata(
                document_id=v.document_id,
                user=v.metadata.user,
            )
            if doc_meta and doc_meta.kind and doc_meta.kind != "application/pdf":
                logger.error(
                    f"Unsupported MIME type: {doc_meta.kind}. "
                    f"Tesseract OCR decoder only handles application/pdf. "
                    f"Ignoring document {v.metadata.id}."
                )
                return

        # Get PDF content - fetch from librarian or use inline data
        if v.document_id:
            logger.info(f"Fetching document {v.document_id} from librarian...")
            content = await self.fetch_document_content(
                document_id=v.document_id,
                user=v.metadata.user,
            )
            if isinstance(content, str):
                content = content.encode('utf-8')
            blob = base64.b64decode(content)
            logger.info(f"Fetched {len(blob)} bytes from librarian")
        else:
            blob = base64.b64decode(v.data)

        # Get the source document ID
        source_doc_id = v.document_id or v.metadata.id

        pages = convert_from_bytes(blob)

        for ix, page in enumerate(pages):

            page_num = ix + 1  # 1-indexed

            try:
                text = pytesseract.image_to_string(page, lang='eng')
            except Exception as e:
                logger.warning(f"Page {page_num} did not OCR: {e}")
                continue

            logger.debug(f"Processing page {page_num}")

            # Generate unique page ID
            pg_uri = make_page_uri()
            page_doc_id = pg_uri
            page_content = text.encode("utf-8")

            # Save page as child document in librarian
            await self.save_child_document(
                doc_id=page_doc_id,
                parent_id=source_doc_id,
                user=v.metadata.user,
                content=page_content,
                document_type="page",
                title=f"Page {page_num}",
            )

            # Emit provenance triples
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

        logger.info("PDF decoding complete")

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
