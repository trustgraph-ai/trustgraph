from __future__ import annotations

import uuid
import asyncio
import logging
from typing import Any

from . subscriber import Subscriber
from . producer import Producer
from . spec import Spec
from . metrics import ConsumerMetrics, ProducerMetrics, SubscriberMetrics

# Module logger
logger = logging.getLogger(__name__)

class RequestResponse(Subscriber):

    def __init__(
            self, backend, subscription, consumer_name,
            request_topic, request_schema,
            request_metrics,
            response_topic, response_schema,
            response_metrics,
    ):

        super(RequestResponse, self).__init__(
            backend = backend,
            subscription = subscription,
            consumer_name = consumer_name,
            topic = response_topic,
            schema = response_schema,
            metrics = response_metrics,
        )

        self.producer = Producer(
            backend = backend,
            topic = request_topic,
            schema = request_schema,
            metrics = request_metrics,
        )

    async def start(self):
        await self.producer.start()
        await super(RequestResponse, self).start()

    async def stop(self):
        await self.producer.stop()
        await super(RequestResponse, self).stop()

    async def request(self, req, timeout=300, recipient=None):

        id = str(uuid.uuid4())

        q = await self.subscribe(id)

        try:

            await self.producer.send(
                req,
                properties={"id": id}
            )

        except Exception as e:

            logger.error(f"Exception sending request: {e}", exc_info=True)
            raise e


        try:

            while True:

                resp = await asyncio.wait_for(
                    q.get(),
                    timeout=timeout
                )

                if recipient is None:

                    # If no recipient handler, just return the first
                    # response we get
                    return resp
                else:

                    # Recipient handler gets to decide when we're done b
                    # returning a boolean
                    fin = await recipient(resp)

                    # If done, return the last result otherwise loop round for
                    # next response
                    if fin:
                        return resp
                    else:
                        continue

        except Exception as e:

            logger.error(f"Exception processing response: {e}", exc_info=True)
            raise e

        finally:

            await self.unsubscribe(id)

# This deals with the request/response case.  The caller needs to
# use another service in request/response mode.  Uses two topics:
# - we send on the request topic as a producer
# - we receive on the response topic as a subscriber
class RequestResponseSpec(Spec):
    def __init__(
            self, request_name, request_schema, response_name,
            response_schema, impl=RequestResponse, optional=False
    ):
        self.request_name = request_name
        self.request_schema = request_schema
        self.response_name = response_name
        self.response_schema = response_schema
        self.impl = impl
        self.optional = optional

    def add(self, flow: Any, processor: Any, definition: dict[str, Any]) -> None:

        # An optional client binds only when the flow definition declares
        # its topics. Older definitions predating the topics would otherwise
        # KeyError here during Flow construction, which wedges the whole
        # processor in a start-flow retry loop; skipping instead leaves
        # flow(name) returning None for the caller to handle per-request.
        topics = definition.get("topics", {})
        if self.optional and (
                self.request_name not in topics
                or self.response_name not in topics):
            return

        request_metrics = ProducerMetrics(
            processor=flow.id, producer=self.request_name,
            workspace=flow.workspace, flow=flow.name,
        )

        response_metrics = SubscriberMetrics(
            processor=flow.id, subscriber=self.response_name,
            workspace=flow.workspace, flow=flow.name,
        )

        rr = self.impl(
            backend = processor.pubsub,

            # Make subscription names unique, so that all subscribers get
            # to see all response messages
            subscription = (
                processor.id + "--" + flow.workspace + "--" +
                flow.name + "--" + self.request_name + "--" +
                str(uuid.uuid4())
            ),
            consumer_name = flow.id,
            request_topic = definition["topics"][self.request_name],
            request_schema = self.request_schema,
            request_metrics = request_metrics,
            response_topic = definition["topics"][self.response_name],
            response_schema = self.response_schema,
            response_metrics = response_metrics,
        )

        flow.consumer[self.request_name] = rr

    async def register(self, flow: Any, processor: Any, definition: dict[str, Any]) -> Any:

        from .request_response_client import RequestResponseClient

        topics = definition.get("topics", {})
        if self.optional and (
                self.request_name not in topics
                or self.response_name not in topics):
            return None

        rr_client = await RequestResponseClient.create(
            backend=processor.async_backend,
            request_topic=topics[self.request_name],
            response_topic=topics[self.response_name],
            request_schema=self.request_schema,
            response_schema=self.response_schema,
        )

        wrapper = _make_impl_wrapper(rr_client, self.impl)
        flow.consumer[self.request_name] = wrapper
        return wrapper


def _make_impl_wrapper(rr_client, impl_cls):
    """Create a domain-specific wrapper that delegates request() to the
    RequestResponseClient while inheriting business methods from impl_cls."""

    class Wrapper(impl_cls):
        def __init__(self):
            self._rr_client = rr_client

        async def request(self, req, timeout=300, recipient=None):
            if recipient is None:
                return await self._rr_client.request(req, timeout=timeout)

            while True:
                resp = await self._rr_client.request(req, timeout=timeout)
                fin = await recipient(resp)
                if fin:
                    return resp

        async def start(self):
            pass

        async def stop(self):
            await self._rr_client.close()

        async def close(self):
            await self._rr_client.close()

    return Wrapper()

