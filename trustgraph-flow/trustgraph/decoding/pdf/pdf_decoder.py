
"""
Simple decoder, accepts PDF documents on input, outputs pages from the
PDF document as text as separate output objects.

Supports both inline document data and fetching from librarian via Pulsar
for large documents.
"""

import asyncio
import os
import tempfile
import base64
import logging
import uuid
from langchain_community.document_loaders import PyPDFLoader

from ... schema import Document, TextDocument, Metadata
from ... schema import LibrarianRequest, LibrarianResponse
from ... schema import librarian_request_queue, librarian_response_queue
from ... base import FlowProcessor, ConsumerSpec, ProducerSpec
from ... base import Consumer, Producer, ConsumerMetrics, ProducerMetrics

# Module logger
logger = logging.getLogger(__name__)

default_ident = "pdf-decoder"

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

        logger.info("PDF decoder initialized")

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

        logger.debug("PDF message received")

        v = msg.value()

        logger.info(f"Decoding PDF {v.metadata.id}...")

        with tempfile.NamedTemporaryFile(delete_on_close=False, suffix='.pdf') as fp:
            temp_path = fp.name

            # Check if we should fetch from librarian or use inline data
            if v.document_id:
                # Fetch from librarian via Pulsar
                logger.info(f"Fetching document {v.document_id} from librarian...")
                fp.close()

                content = await self.fetch_document_content(
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

            for ix, page in enumerate(pages):

                logger.debug(f"Processing page {ix}")

                r = TextDocument(
                    metadata=v.metadata,
                    text=page.page_content.encode("utf-8"),
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
