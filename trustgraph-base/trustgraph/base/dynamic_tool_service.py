"""
Base class for dynamically pluggable tool services.

Tool services are Pulsar services that can be invoked as agent tools.
They receive a ToolServiceRequest with config and arguments,
and return a ToolServiceResponse with the result.

Uses direct Pulsar topics (no flow configuration required):
- Request: non-persistent://tg/request/{topic}
- Response: non-persistent://tg/response/{topic}
"""

from __future__ import annotations

from argparse import ArgumentParser

import json
import logging
import asyncio
import argparse
from prometheus_client import Counter

from .. schema import ToolServiceRequest, ToolServiceResponse, Error
from .. exceptions import TooManyRequests
from . async_processor import AsyncProcessor

logger = logging.getLogger(__name__)

default_concurrency = 1
default_topic = "tool"


class DynamicToolService(AsyncProcessor):
    """
    Base class for implementing dynamic tool services.

    Subclasses should override the `invoke` method to implement
    the tool's logic.

    The invoke method receives:
    - config: Dict of config values from the tool descriptor
    - arguments: Dict of arguments from the LLM

    And should return a string response (the observation).
    """

    def __init__(self, **params):

        super(DynamicToolService, self).__init__(**params)

        self.id = params.get("id")
        self._topic = params.get("topic", default_topic)

        self._consumer_reg = None
        self._producer_handle = None

        if not hasattr(__class__, "tool_service_metric"):
            __class__.tool_service_metric = Counter(
                'dynamic_tool_service_invocation_count',
                'Dynamic tool service invocation count',
                ["processor"],
            )

    async def start(self):
        await super(DynamicToolService, self).start()

        request_topic = f"non-persistent://tg/request/{self._topic}"
        response_topic = f"non-persistent://tg/response/{self._topic}"

        logger.info(
            f"Tool service topics: "
            f"request={request_topic}, response={response_topic}"
        )

        self._producer_handle = await self.sender_pool.add_producer(
            topic=response_topic,
            schema=ToolServiceResponse,
        )

        async def handler(message):
            await self.on_request(message, None, None)

        self._consumer_reg = await self.receiver_pool.add_consumer(
            topic=request_topic,
            subscription=f"{self.id}-request",
            schema=ToolServiceRequest,
            handler=handler,
        )

        logger.info(f"Tool service {self.id} started")

    async def on_request(self, msg, consumer, flow):

        id = None

        try:

            request = msg.value()

            id = msg.properties().get("id", "unknown")

            config = json.loads(request.config) if request.config else {}
            arguments = (
                json.loads(request.arguments) if request.arguments
                else {}
            )

            logger.debug(
                f"Tool service request: "
                f"config={config}, arguments={arguments}"
            )

            response = await self.invoke(config, arguments)

            await self._producer_handle.send(
                ToolServiceResponse(
                    error=None,
                    response=(
                        response if isinstance(response, str)
                        else json.dumps(response)
                    ),
                    end_of_stream=True,
                ),
                properties={"id": id}
            )

            __class__.tool_service_metric.labels(
                processor=self.id,
            ).inc()

        except TooManyRequests as e:
            raise e

        except Exception as e:

            logger.error(
                f"Exception in dynamic tool service: {e}",
                exc_info=True,
            )

            logger.info("Sending error response...")

            await self._producer_handle.send(
                ToolServiceResponse(
                    error=Error(
                        type="tool-service-error",
                        message=str(e),
                    ),
                    response="",
                    end_of_stream=True,
                ),
                properties={"id": id if id else "unknown"}
            )

    async def invoke(self, config, arguments):
        raise NotImplementedError("Subclasses must implement invoke()")

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:

        AsyncProcessor.add_args(parser)

        parser.add_argument(
            '-t', '--topic',
            default=default_topic,
            help=f'Topic name for request/response '
                 f'(default: {default_topic})'
        )
