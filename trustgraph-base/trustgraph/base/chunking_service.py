"""
Base chunking service that provides parameter specification functionality
for chunk-size and chunk-overlap parameters, and librarian client for
fetching large document content.
"""

import asyncio
import base64
import logging
import uuid

from .flow_processor import FlowProcessor
from .parameter_spec import ParameterSpec
from .consumer import Consumer
from .producer import Producer
from .metrics import ConsumerMetrics, ProducerMetrics

from ..schema import LibrarianRequest, LibrarianResponse, DocumentMetadata
from ..schema import librarian_request_queue, librarian_response_queue

# Module logger
logger = logging.getLogger(__name__)

default_librarian_request_queue = librarian_request_queue
default_librarian_response_queue = librarian_response_queue


class ChunkingService(FlowProcessor):
    """Base service for chunking processors with parameter specification support"""

    def __init__(self, **params):

        id = params.get("id", "chunker")

        # Call parent constructor
        super(ChunkingService, self).__init__(**params)

        # Register parameter specifications for chunk-size and chunk-overlap
        self.register_specification(
            ParameterSpec(name="chunk-size")
        )

        self.register_specification(
            ParameterSpec(name="chunk-overlap")
        )

        # Librarian client for fetching document content
        librarian_request_q = params.get(
            "librarian_request_queue", default_librarian_request_queue
        )
        librarian_response_q = params.get(
            "librarian_response_queue", default_librarian_response_queue
        )

        librarian_request_metrics = ProducerMetrics(
            processor=id, flow=None, name="librarian-request"
        )

        self.librarian_request_producer = Producer(
            backend=self.pubsub,
            topic=librarian_request_q,
            schema=LibrarianRequest,
            metrics=librarian_request_metrics,
        )

        librarian_response_metrics = ConsumerMetrics(
            processor=id, flow=None, name="librarian-response"
        )

        self.librarian_response_consumer = Consumer(
            taskgroup=self.taskgroup,
            backend=self.pubsub,
            flow=None,
            topic=librarian_response_q,
            subscriber=f"{id}-librarian",
            schema=LibrarianResponse,
            handler=self.on_librarian_response,
            metrics=librarian_response_metrics,
        )

        # Pending librarian requests: request_id -> asyncio.Future
        self.pending_requests = {}

        logger.debug("ChunkingService initialized with parameter specifications")

    async def start(self):
        await super(ChunkingService, self).start()
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
                                   document_type="chunk", title=None, timeout=120):
        """
        Save a child document (chunk) to the librarian.

        Args:
            doc_id: ID for the new child document
            parent_id: ID of the parent document
            user: User ID
            content: Document content (bytes or str)
            document_type: Type of document ("chunk", etc.)
            title: Optional title
            timeout: Request timeout in seconds

        Returns:
            The document ID on success
        """
        request_id = str(uuid.uuid4())

        if isinstance(content, str):
            content = content.encode("utf-8")

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
                    f"Librarian error saving chunk: {response.error.type}: {response.error.message}"
                )

            return doc_id

        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            raise RuntimeError(f"Timeout saving chunk {doc_id}")

    async def get_document_text(self, doc):
        """
        Get text content from a TextDocument, fetching from librarian if needed.

        Args:
            doc: TextDocument with either inline text or document_id

        Returns:
            str: The document text content
        """
        if doc.document_id and not doc.text:
            logger.info(f"Fetching document {doc.document_id} from librarian...")
            content = await self.fetch_document_content(
                document_id=doc.document_id,
                user=doc.metadata.user,
            )
            # Content is base64 encoded
            if isinstance(content, str):
                content = content.encode('utf-8')
            text = base64.b64decode(content).decode("utf-8")
            logger.info(f"Fetched {len(text)} characters from librarian")
            return text
        else:
            return doc.text.decode("utf-8")

    async def chunk_document(self, msg, consumer, flow, default_chunk_size, default_chunk_overlap):
        """
        Extract chunk parameters from flow and return effective values

        Args:
            msg: The message containing the document to chunk
            consumer: The consumer spec
            flow: The flow context
            default_chunk_size: Default chunk size from processor config
            default_chunk_overlap: Default chunk overlap from processor config

        Returns:
            tuple: (chunk_size, chunk_overlap) - effective values to use
        """
        # Extract parameters from flow (flow-configurable parameters)
        chunk_size = flow("chunk-size")
        chunk_overlap = flow("chunk-overlap")

        # Use provided values or fall back to defaults
        effective_chunk_size = chunk_size if chunk_size is not None else default_chunk_size
        effective_chunk_overlap = chunk_overlap if chunk_overlap is not None else default_chunk_overlap

        logger.debug(f"Using chunk-size: {effective_chunk_size}")
        logger.debug(f"Using chunk-overlap: {effective_chunk_overlap}")

        return effective_chunk_size, effective_chunk_overlap

    @staticmethod
    def add_args(parser):
        """Add chunking service arguments to parser"""
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