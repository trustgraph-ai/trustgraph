"""
SenderPool — async producer runtime for the producer/consumer
message pattern.

Manages broker producers, send queues, and a sender task that
dispatches messages to backend producers. Decouples application
send calls from broker I/O.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from .async_backend import AsyncPubSubBackend, AsyncBackendProducer

logger = logging.getLogger(__name__)


@dataclass
class SendItem:
    """Item placed on the send queue for dispatch."""
    message: Any
    properties: dict
    future: asyncio.Future | None


class ProducerHandle:
    """Handle returned by add_producer, used to send messages."""

    def __init__(
        self, topic: str, backend_producer: AsyncBackendProducer,
        send_queue: asyncio.Queue, pool: 'SenderPool',
    ):
        self.topic = topic
        self.backend_producer = backend_producer
        self.send_queue = send_queue
        self.pool = pool

    async def send(
        self, message: Any, properties: dict = {}, wait: bool = False,
    ):
        if wait:
            future = asyncio.get_event_loop().create_future()
        else:
            future = None

        await self.send_queue.put(
            SendItem(message=message, properties=properties, future=future)
        )

        if future is not None:
            await future

    async def unregister(self):
        await self.pool.remove_producer(self)


class SenderPool:
    """Manages async producer send dispatch.

    Usage:
        pool = SenderPool(backend=backend)
        await pool.start()

        handle = await pool.add_producer(
            topic="flow:tg:text-completion-response:ws1:default",
            schema=TextCompletionResponse,
        )
        await handle.send(message, properties={"id": req_id})

        await handle.unregister()
        await pool.stop()
    """

    def __init__(
        self, backend: AsyncPubSubBackend, send_queue_size: int = 64,
    ):
        self.backend = backend
        self.send_queue_size = send_queue_size
        self.handles: list[ProducerHandle] = []
        self.sender_task: asyncio.Task | None = None
        self.running = False

    async def start(self):
        self.running = True
        self.sender_task = asyncio.create_task(
            self._sender_loop(), name="sender-pool",
        )
        logger.info("SenderPool started")

    async def stop(self, drain_timeout: float = 5.0):
        self.running = False

        if self.handles:
            try:
                await asyncio.wait_for(
                    self._drain_all(), timeout=drain_timeout,
                )
            except asyncio.TimeoutError:
                logger.warning("Drain timeout, some messages not sent")

        if self.sender_task:
            self.sender_task.cancel()
            try:
                await self.sender_task
            except asyncio.CancelledError:
                pass
            self.sender_task = None

        for handle in list(self.handles):
            try:
                await handle.backend_producer.close()
            except Exception as e:
                logger.warning(f"Error closing producer: {e}")
        self.handles.clear()

        logger.info("SenderPool stopped")

    async def _drain_all(self):
        while any(not h.send_queue.empty() for h in self.handles):
            await asyncio.sleep(0.1)

    async def add_producer(
        self, topic: str, schema: type, **options,
    ) -> ProducerHandle:
        backend_producer = await self.backend.create_producer(
            topic=topic, schema=schema, **options,
        )

        send_queue = asyncio.Queue(maxsize=self.send_queue_size)

        handle = ProducerHandle(
            topic=topic,
            backend_producer=backend_producer,
            send_queue=send_queue,
            pool=self,
        )
        self.handles.append(handle)

        logger.info(f"Added producer: {topic}")
        return handle

    async def remove_producer(self, handle: ProducerHandle):
        while not handle.send_queue.empty():
            await asyncio.sleep(0.05)

        try:
            await handle.backend_producer.close()
        except Exception as e:
            logger.warning(
                f"Error closing producer for {handle.topic}: {e}"
            )

        if handle in self.handles:
            self.handles.remove(handle)

        logger.info(f"Removed producer: {handle.topic}")

    async def _sender_loop(self):
        try:
            while self.running:
                if not self.handles:
                    await asyncio.sleep(0.1)
                    continue

                queues = {
                    asyncio.create_task(h.send_queue.get()): h
                    for h in self.handles
                    if not h.send_queue.empty()
                }

                if not queues:
                    await asyncio.sleep(0.01)
                    continue

                done, pending = await asyncio.wait(
                    queues.keys(),
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in pending:
                    task.cancel()

                for task in done:
                    handle = queues[task]
                    try:
                        item: SendItem = task.result()
                        await handle.backend_producer.send(
                            item.message, item.properties,
                        )
                        if item.future is not None:
                            item.future.set_result(None)
                    except Exception as e:
                        logger.error(
                            f"Send error for {handle.topic}: {e}",
                            exc_info=True,
                        )
                        if item.future is not None:
                            item.future.set_exception(e)

        except asyncio.CancelledError:
            pass
