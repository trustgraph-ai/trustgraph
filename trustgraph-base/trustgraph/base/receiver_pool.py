"""
ReceiverPool — async consumer runtime for the producer/consumer
message pattern.

Manages broker subscriptions, receiver coroutines, a shared work
queue, and a pool of worker coroutines. All pub/sub communication
stays in the receiver coroutines; workers only process messages and
signal completion via futures.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from .async_backend import AsyncPubSubBackend, AsyncBackendConsumer, Message

logger = logging.getLogger(__name__)


@dataclass
class ConsumerRegistration:
    """Handle returned by add_consumer, used to remove it later."""
    topic: str
    subscription: str
    backend_consumer: AsyncBackendConsumer
    receiver_task: asyncio.Task
    pool: 'ReceiverPool'

    async def unregister(self):
        await self.pool.remove_consumer(self)


@dataclass
class WorkItem:
    """Item placed on the work queue for worker dispatch."""
    message: Message
    handler: Callable[..., Awaitable[None]]
    future: asyncio.Future


class ReceiverPool:
    """Manages async consumer receive loops and a worker pool.

    Usage:
        pool = ReceiverPool(backend=backend, concurrency=4)
        await pool.start()

        reg = await pool.add_consumer(
            topic="flow:tg:request:ws1:default",
            subscription="my-processor",
            schema=MyRequest,
            handler=self.on_request,
        )

        # ... later ...
        await reg.unregister()
        await pool.stop()
    """

    def __init__(self, backend: AsyncPubSubBackend, concurrency: int = 1):
        self.backend = backend
        self.concurrency = concurrency
        self.work_queue = asyncio.Queue(maxsize=concurrency)
        self.registrations: list[ConsumerRegistration] = []
        self.worker_tasks: list[asyncio.Task] = []
        self.running = False

    async def start(self):
        self.running = True
        for i in range(self.concurrency):
            task = asyncio.create_task(
                self._worker(i), name=f"worker-{i}",
            )
            self.worker_tasks.append(task)
        logger.info(
            f"ReceiverPool started with {self.concurrency} workers"
        )

    async def stop(self, drain_timeout: float = 5.0):
        self.running = False

        for reg in list(self.registrations):
            try:
                await reg.backend_consumer.close()
            except BaseException as e:
                logger.warning(f"Error closing consumer: {e}")

        for reg in list(self.registrations):
            reg.receiver_task.cancel()
        for reg in list(self.registrations):
            try:
                await reg.receiver_task
            except BaseException:
                pass
        self.registrations.clear()

        if not self.work_queue.empty():
            logger.info(
                f"Draining {self.work_queue.qsize()} pending work items"
            )
            try:
                await asyncio.wait_for(
                    self._drain_work_queue(), timeout=drain_timeout,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    f"Drain timeout, {self.work_queue.qsize()} items "
                    f"remaining"
                )

        for task in self.worker_tasks:
            task.cancel()
        for task in self.worker_tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self.worker_tasks.clear()

        logger.info("ReceiverPool stopped")

    async def _drain_work_queue(self):
        while not self.work_queue.empty():
            await asyncio.sleep(0.1)

    async def add_consumer(
        self, topic: str, subscription: str, schema: type,
        handler: Callable[..., Awaitable[None]],
        initial_position: str = 'latest',
    ) -> ConsumerRegistration:
        backend_consumer = await self.backend.create_consumer(
            topic=topic,
            subscription=subscription,
            schema=schema,
            initial_position=initial_position,
        )

        receiver_task = asyncio.create_task(
            self._receiver_loop(backend_consumer, handler),
            name=f"receiver-{topic}",
        )

        reg = ConsumerRegistration(
            topic=topic,
            subscription=subscription,
            backend_consumer=backend_consumer,
            receiver_task=receiver_task,
            pool=self,
        )
        self.registrations.append(reg)

        logger.info(f"Added consumer: {topic}")
        return reg

    async def remove_consumer(self, reg: ConsumerRegistration):
        try:
            await reg.backend_consumer.close()
        except BaseException as e:
            logger.warning(f"Error closing consumer for {reg.topic}: {e}")

        reg.receiver_task.cancel()
        try:
            await reg.receiver_task
        except (asyncio.CancelledError, Exception):
            pass

        if reg in self.registrations:
            self.registrations.remove(reg)

        logger.info(f"Removed consumer: {reg.topic}")

    async def _receiver_loop(
        self, backend_consumer: AsyncBackendConsumer,
        handler: Callable[..., Awaitable[None]],
    ):
        pending_acks: set[asyncio.Task] = set()

        try:
            receive_task = asyncio.create_task(backend_consumer.receive())

            while self.running:
                wait_set = {receive_task} | pending_acks
                done, _ = await asyncio.wait(
                    wait_set,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in done:
                    if task is receive_task:
                        msg = task.result()
                        future = asyncio.get_event_loop().create_future()
                        await self.work_queue.put(
                            WorkItem(
                                message=msg,
                                handler=handler,
                                future=future,
                            )
                        )

                        ack_task = asyncio.create_task(
                            self._await_and_ack(
                                future, msg, backend_consumer,
                            )
                        )
                        pending_acks.add(ack_task)

                        receive_task = asyncio.create_task(
                            backend_consumer.receive()
                        )
                    else:
                        pending_acks.discard(task)
                        try:
                            task.result()
                        except Exception as e:
                            logger.error(
                                f"Ack task error: {e}", exc_info=True,
                            )

        except asyncio.CancelledError:
            receive_task.cancel()
            for task in pending_acks:
                task.cancel()
            raise
        except BaseException as e:
            if not self.running:
                return
            logger.error(
                f"Receiver loop error: {e}", exc_info=True,
            )

    async def _await_and_ack(
        self, future: asyncio.Future, msg: Message,
        consumer: AsyncBackendConsumer,
    ):
        try:
            await future
            await consumer.acknowledge(msg)
        except Exception:
            await consumer.negative_acknowledge(msg)

    async def _worker(self, worker_id: int):
        logger.debug(f"Worker {worker_id} started")

        try:
            while self.running:
                try:
                    item = await asyncio.wait_for(
                        self.work_queue.get(), timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    continue

                try:
                    await item.handler(item.message)
                    item.future.set_result(None)
                except Exception as e:
                    item.future.set_exception(e)

        except asyncio.CancelledError:
            pass

        logger.debug(f"Worker {worker_id} stopped")
