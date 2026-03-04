
"""
Simple decoder, accepts text documents on input, outputs chunks from the
as text as separate output objects.
"""

import asyncio
import base64
import logging
import uuid
from langchain_text_splitters import RecursiveCharacterTextSplitter
from prometheus_client import Histogram

from ... schema import TextDocument, Chunk
from ... schema import LibrarianRequest, LibrarianResponse
from ... schema import librarian_request_queue, librarian_response_queue
from ... base import ChunkingService, ConsumerSpec, ProducerSpec
from ... base import Consumer, Producer, ConsumerMetrics, ProducerMetrics

# Module logger
logger = logging.getLogger(__name__)

default_ident = "chunker"

default_librarian_request_queue = librarian_request_queue
default_librarian_response_queue = librarian_response_queue


class Processor(ChunkingService):

    def __init__(self, **params):

        id = params.get("id", default_ident)
        chunk_size = params.get("chunk_size", 2000)
        chunk_overlap = params.get("chunk_overlap", 100)

        super(Processor, self).__init__(
            **params | { "id": id }
        )

        # Store default values for parameter override
        self.default_chunk_size = chunk_size
        self.default_chunk_overlap = chunk_overlap

        if not hasattr(__class__, "chunk_metric"):
            __class__.chunk_metric = Histogram(
                'chunk_size', 'Chunk size',
                ["id", "flow"],
                buckets=[100, 160, 250, 400, 650, 1000, 1600,
                         2500, 4000, 6400, 10000, 16000]
            )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )

        self.register_specification(
            ConsumerSpec(
                name = "input",
                schema = TextDocument,
                handler = self.on_message,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "output",
                schema = Chunk,
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

        logger.info("Recursive chunker initialized")

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

    async def on_message(self, msg, consumer, flow):

        v = msg.value()
        logger.info(f"Chunking document {v.metadata.id}...")

        # Check if we need to fetch content from librarian
        if v.document_id and not v.text:
            logger.info(f"Fetching document {v.document_id} from librarian...")
            content = await self.fetch_document_content(
                document_id=v.document_id,
                user=v.metadata.user,
            )
            # Content is base64 encoded
            if isinstance(content, str):
                content = content.encode('utf-8')
            text = base64.b64decode(content).decode("utf-8")
            logger.info(f"Fetched {len(text)} characters from librarian")
        else:
            text = v.text.decode("utf-8")

        # Extract chunk parameters from flow (allows runtime override)
        chunk_size, chunk_overlap = await self.chunk_document(
            msg, consumer, flow,
            self.default_chunk_size,
            self.default_chunk_overlap
        )

        # Convert to int if they're strings (flow parameters are always strings)
        if isinstance(chunk_size, str):
            chunk_size = int(chunk_size)
        if isinstance(chunk_overlap, str):
            chunk_overlap = int(chunk_overlap)

        # Create text splitter with effective parameters
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )

        texts = text_splitter.create_documents([text])

        for ix, chunk in enumerate(texts):

            logger.debug(f"Created chunk of size {len(chunk.page_content)}")

            r = Chunk(
                metadata=v.metadata,
                chunk=chunk.page_content.encode("utf-8"),
            )

            __class__.chunk_metric.labels(
                id=consumer.id, flow=consumer.flow
            ).observe(len(chunk.page_content))

            await flow("output").send(r)

        logger.debug("Document chunking complete")

    @staticmethod
    def add_args(parser):

        ChunkingService.add_args(parser)

        parser.add_argument(
            '-z', '--chunk-size',
            type=int,
            default=2000,
            help=f'Chunk size (default: 2000)'
        )

        parser.add_argument(
            '-v', '--chunk-overlap',
            type=int,
            default=100,
            help=f'Chunk overlap (default: 100)'
        )

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
