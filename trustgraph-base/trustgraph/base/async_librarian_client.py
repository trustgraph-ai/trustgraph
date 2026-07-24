"""
Async librarian client using the async pub/sub backend directly.

Replaces LibrarianClient's Consumer+Producer (which create OS threads)
with async backend producers/consumers and a dedicated receiver
coroutine. Supports both single-response and streaming operations.
"""

import asyncio
import base64
import logging
import uuid

from ..schema import LibrarianRequest, LibrarianResponse, DocumentMetadata

logger = logging.getLogger(__name__)


class AsyncLibrarianClient:

    def __init__(self):
        self._producer = None
        self._consumer = None
        self._receiver_task = None
        self._pending = {}
        self._streams = {}
        self.running = False

    @classmethod
    async def create(
        cls, backend, request_topic, response_topic,
        subscription=None,
    ):
        client = cls()

        client._producer = await backend.create_producer(
            topic=request_topic,
            schema=LibrarianRequest,
        )

        if subscription is None:
            subscription = f"librarian-{uuid.uuid4().hex[:12]}"

        client._consumer = await backend.create_consumer(
            topic=response_topic,
            subscription=subscription,
            schema=LibrarianResponse,
            initial_position='latest',
        )

        client.running = True
        client._receiver_task = asyncio.create_task(
            client._response_loop(),
            name=f"librarian-receiver-{response_topic}",
        )

        logger.info(
            f"AsyncLibrarianClient created: "
            f"req={request_topic}, resp={response_topic}"
        )
        return client

    async def start(self):
        pass

    async def _response_loop(self):
        try:
            while self.running:
                msg = await self._consumer.receive()
                response = msg.value()
                request_id = msg.properties().get("id")

                if request_id:
                    if request_id in self._pending:
                        future = self._pending.pop(request_id)
                        if not future.done():
                            future.set_result(response)
                    elif request_id in self._streams:
                        await self._streams[request_id].put(response)

                await self._consumer.acknowledge(msg)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(
                f"Librarian response loop error: {e}", exc_info=True,
            )

    async def request(self, request, timeout=120):
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
        request_id = str(uuid.uuid4())

        q = asyncio.Queue()
        self._streams[request_id] = q

        try:
            await self._producer.send(
                request, properties={"id": request_id},
            )

            chunks = []
            while True:
                response = await asyncio.wait_for(
                    q.get(), timeout=timeout,
                )

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

    async def stop(self):
        self.running = False

        if self._receiver_task:
            self._receiver_task.cancel()
            try:
                await self._receiver_task
            except asyncio.CancelledError:
                pass

        for future in self._pending.values():
            if not future.done():
                future.cancel()
        self._pending.clear()

        for q in self._streams.values():
            await q.put(None)
        self._streams.clear()

        if self._producer:
            try:
                await self._producer.close()
            except Exception as e:
                logger.warning(f"Error closing librarian producer: {e}")

        if self._consumer:
            try:
                await self._consumer.close()
            except Exception as e:
                logger.warning(f"Error closing librarian consumer: {e}")

        logger.info("AsyncLibrarianClient closed")

    async def fetch_document_content(self, document_id, timeout=120):
        req = LibrarianRequest(
            operation="stream-document",
            document_id=document_id,
        )
        chunks = await self.stream(req, timeout=timeout)

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

    async def fetch_document_text(self, document_id, timeout=120):
        content = await self.fetch_document_content(
            document_id, timeout=timeout,
        )
        return base64.b64decode(content).decode("utf-8")

    async def fetch_document_metadata(self, document_id, timeout=120):
        req = LibrarianRequest(
            operation="get-document-metadata",
            document_id=document_id,
        )
        response = await self.request(req, timeout=timeout)
        return response.document_metadata

    async def save_child_document(self, doc_id, parent_id, content,
                                  document_type="chunk", title=None,
                                  kind="text/plain", timeout=120):
        if isinstance(content, str):
            content = content.encode("utf-8")

        doc_metadata = DocumentMetadata(
            id=doc_id,
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

    async def save_document(self, doc_id, content, title=None,
                            document_type="answer", kind="text/plain",
                            timeout=120):
        if isinstance(content, str):
            content = content.encode("utf-8")

        doc_metadata = DocumentMetadata(
            id=doc_id,
            kind=kind,
            title=title or doc_id,
            document_type=document_type,
        )

        req = LibrarianRequest(
            operation="add-document",
            document_id=doc_id,
            document_metadata=doc_metadata,
            content=base64.b64encode(content).decode("utf-8"),
        )

        await self.request(req, timeout=timeout)
        return doc_id
