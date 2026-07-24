"""
RequestResponseClient — async request/response over pub/sub.

Manages a producer for requests, a consumer for responses, and a
dedicated receiver coroutine that routes responses to waiting callers
via futures. No worker pool involvement.
"""

import asyncio
import logging
import uuid
from typing import Any

from .async_backend import AsyncPubSubBackend

logger = logging.getLogger(__name__)


class RequestResponseClient:
    """Async request/response client over pub/sub.

    Usage:
        client = await RequestResponseClient.create(
            backend=backend,
            request_topic="request:tg:triples:ws1:default",
            response_topic="response:tg:triples:ws1:default",
            request_schema=TriplesRequest,
            response_schema=TriplesResponse,
        )

        response = await client.request(my_request, timeout=60)

        await client.close()
    """

    def __init__(self):
        self.producer = None
        self.consumer = None
        self.receiver_task = None
        self.pending: dict[str, asyncio.Future] = {}
        self.running = False

    @classmethod
    async def create(
        cls,
        backend: AsyncPubSubBackend,
        request_topic: str,
        response_topic: str,
        request_schema: type,
        response_schema: type,
        subscription: str | None = None,
    ) -> 'RequestResponseClient':
        client = cls()

        client.producer = await backend.create_producer(
            topic=request_topic,
            schema=request_schema,
        )

        if subscription is None:
            subscription = f"rr-{uuid.uuid4().hex[:12]}"

        client.consumer = await backend.create_consumer(
            topic=response_topic,
            subscription=subscription,
            schema=response_schema,
            initial_position='latest',
        )

        client.running = True
        client.receiver_task = asyncio.create_task(
            client._response_loop(),
            name=f"rr-receiver-{response_topic}",
        )

        logger.info(
            f"RequestResponseClient created: "
            f"req={request_topic}, resp={response_topic}"
        )
        return client

    async def request(
        self, message: Any, timeout: float = 60,
        properties: dict | None = None,
    ) -> Any:
        request_id = str(uuid.uuid4())
        future = asyncio.get_event_loop().create_future()
        self.pending[request_id] = future

        send_properties = {"id": request_id}
        if properties:
            send_properties.update(properties)

        await self.producer.send(message, send_properties)

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self.pending.pop(request_id, None)
            raise

    async def _response_loop(self):
        try:
            while self.running:
                msg = await self.consumer.receive()
                request_id = msg.properties().get("id")

                if request_id is not None:
                    future = self.pending.pop(request_id, None)
                    if future is not None and not future.done():
                        future.set_result(msg.value())

                await self.consumer.acknowledge(msg)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            if not self.running:
                return
            logger.error(
                f"Response loop error: {e}", exc_info=True,
            )

    async def close(self):
        self.running = False

        if self.consumer:
            try:
                await self.consumer.close()
            except Exception as e:
                logger.warning(f"Error closing consumer: {e}")

        if self.receiver_task:
            self.receiver_task.cancel()
            try:
                await self.receiver_task
            except asyncio.CancelledError:
                pass

        for future in self.pending.values():
            if not future.done():
                future.cancel()
        self.pending.clear()

        if self.producer:
            try:
                await self.producer.close()
            except Exception as e:
                logger.warning(f"Error closing producer: {e}")

        logger.info("RequestResponseClient closed")
