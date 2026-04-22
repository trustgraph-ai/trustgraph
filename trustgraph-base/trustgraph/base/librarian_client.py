"""
Shared librarian client for services that need to communicate
with the librarian via pub/sub.

Provides request-response and streaming operations over the message
broker, with proper support for large documents via stream-document.

Usage:
    self.librarian = LibrarianClient(
        id=id, backend=self.pubsub, taskgroup=self.taskgroup, **params
    )
    await self.librarian.start()
    content = await self.librarian.fetch_document_content(doc_id, workspace)
"""

import asyncio
import base64
import logging
import uuid

from .consumer import Consumer
from .producer import Producer
from .metrics import ConsumerMetrics, ProducerMetrics

from ..schema import LibrarianRequest, LibrarianResponse, DocumentMetadata
from ..schema import librarian_request_queue, librarian_response_queue

logger = logging.getLogger(__name__)


class LibrarianClient:
    """Client for librarian request-response over the message broker."""

    def __init__(self, id, backend, taskgroup, **params):

        librarian_request_q = params.get(
            "librarian_request_queue", librarian_request_queue,
        )
        librarian_response_q = params.get(
            "librarian_response_queue", librarian_response_queue,
        )

        librarian_request_metrics = ProducerMetrics(
            processor=id, flow=None, name="librarian-request",
        )

        self._producer = Producer(
            backend=backend,
            topic=librarian_request_q,
            schema=LibrarianRequest,
            metrics=librarian_request_metrics,
        )

        librarian_response_metrics = ConsumerMetrics(
            processor=id, flow=None, name="librarian-response",
        )

        self._consumer = Consumer(
            taskgroup=taskgroup,
            backend=backend,
            flow=None,
            topic=librarian_response_q,
            subscriber=f"{id}-librarian",
            schema=LibrarianResponse,
            handler=self._on_response,
            metrics=librarian_response_metrics,
        )

        # Single-response requests: request_id -> asyncio.Future
        self._pending = {}
        # Streaming requests: request_id -> asyncio.Queue
        self._streams = {}

    async def start(self):
        """Start the librarian producer and consumer."""
        await self._producer.start()
        await self._consumer.start()

    async def _on_response(self, msg, consumer, flow):
        """Route librarian responses to the right waiter."""
        response = msg.value()
        request_id = msg.properties().get("id")

        if not request_id:
            return

        if request_id in self._pending:
            future = self._pending.pop(request_id)
            future.set_result(response)
        elif request_id in self._streams:
            await self._streams[request_id].put(response)

    async def request(self, request, timeout=120):
        """Send a request to the librarian and wait for a single response."""
        request_id = str(uuid.uuid4())

        future = asyncio.get_event_loop().create_future()
        self._pending[request_id] = future

        try:
            await self._producer.send(
                request, properties={"id": request_id},
            )
            response = await asyncio.wait_for(future, timeout=timeout)

            if response.error:
                raise RuntimeError(
                    f"Librarian error: {response.error.type}: "
                    f"{response.error.message}"
                )

            return response

        except asyncio.TimeoutError:
            self._pending.pop(request_id, None)
            raise RuntimeError("Timeout waiting for librarian response")

    async def stream(self, request, timeout=120):
        """Send a request and collect streamed response chunks."""
        request_id = str(uuid.uuid4())

        q = asyncio.Queue()
        self._streams[request_id] = q

        try:
            await self._producer.send(
                request, properties={"id": request_id},
            )

            chunks = []
            while True:
                response = await asyncio.wait_for(q.get(), timeout=timeout)

                if response.error:
                    raise RuntimeError(
                        f"Librarian error: {response.error.type}: "
                        f"{response.error.message}"
                    )

                chunks.append(response)

                if response.is_final:
                    break

            return chunks

        except asyncio.TimeoutError:
            self._streams.pop(request_id, None)
            raise RuntimeError("Timeout waiting for librarian stream")
        finally:
            self._streams.pop(request_id, None)

    async def fetch_document_content(self, document_id, workspace, timeout=120):
        """Fetch document content using streaming.

        Returns base64-encoded content. Caller is responsible for decoding.
        """
        req = LibrarianRequest(
            operation="stream-document",
            document_id=document_id,
            workspace=workspace,
        )
        chunks = await self.stream(req, timeout=timeout)

        # Decode each chunk's base64 to raw bytes, concatenate,
        # re-encode for the caller.
        raw = b""
        for chunk in chunks:
            if chunk.content:
                if isinstance(chunk.content, bytes):
                    raw += base64.b64decode(chunk.content)
                else:
                    raw += base64.b64decode(
                        chunk.content.encode("utf-8")
                    )

        return base64.b64encode(raw)

    async def fetch_document_text(self, document_id, workspace, timeout=120):
        """Fetch document content and decode as UTF-8 text."""
        content = await self.fetch_document_content(
            document_id, workspace, timeout=timeout,
        )
        return base64.b64decode(content).decode("utf-8")

    async def fetch_document_metadata(self, document_id, workspace, timeout=120):
        """Fetch document metadata from the librarian."""
        req = LibrarianRequest(
            operation="get-document-metadata",
            document_id=document_id,
            workspace=workspace,
        )
        response = await self.request(req, timeout=timeout)
        return response.document_metadata

    async def save_child_document(self, doc_id, parent_id, workspace, content,
                                  document_type="chunk", title=None,
                                  kind="text/plain", timeout=120):
        """Save a child document to the librarian."""
        if isinstance(content, str):
            content = content.encode("utf-8")

        doc_metadata = DocumentMetadata(
            id=doc_id,
            workspace=workspace,
            kind=kind,
            title=title or doc_id,
            parent_id=parent_id,
            document_type=document_type,
        )

        req = LibrarianRequest(
            operation="add-child-document",
            document_metadata=doc_metadata,
            content=base64.b64encode(content).decode("utf-8"),
        )

        await self.request(req, timeout=timeout)
        return doc_id

    async def save_document(self, doc_id, workspace, content, title=None,
                            document_type="answer", kind="text/plain",
                            timeout=120):
        """Save a document to the librarian."""
        if isinstance(content, str):
            content = content.encode("utf-8")

        doc_metadata = DocumentMetadata(
            id=doc_id,
            workspace=workspace,
            kind=kind,
            title=title or doc_id,
            document_type=document_type,
        )

        req = LibrarianRequest(
            operation="add-document",
            document_id=doc_id,
            document_metadata=doc_metadata,
            content=base64.b64encode(content).decode("utf-8"),
            workspace=workspace,
        )

        await self.request(req, timeout=timeout)
        return doc_id
