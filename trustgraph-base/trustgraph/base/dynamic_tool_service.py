
"""
Base class for dynamically pluggable tool services.

Tool services are Pulsar services that can be invoked as agent tools.
They receive a ToolServiceRequest with user, config, and arguments,
and return a ToolServiceResponse with the result.

Uses direct Pulsar topics (no flow configuration required):
- Request: non-persistent://tg/request/{topic}-request
- Response: non-persistent://tg/response/{topic}-response
"""

import json
import logging
import asyncio
import argparse
from prometheus_client import Counter

from .. schema import ToolServiceRequest, ToolServiceResponse, Error
from .. exceptions import TooManyRequests
from . async_processor import AsyncProcessor
from . consumer import Consumer
from . producer import Producer
from . metrics import ConsumerMetrics, ProducerMetrics

# Module logger
logger = logging.getLogger(__name__)

default_concurrency = 1
default_topic = "tool"


class DynamicToolService(AsyncProcessor):
    """
    Base class for implementing dynamic tool services.

    Subclasses should override the `invoke` method to implement
    the tool's logic.

    The invoke method receives:
    - user: The user context for multi-tenancy
    - config: Dict of config values from the tool descriptor
    - arguments: Dict of arguments from the LLM

    And should return a string response (the observation).
    """

    def __init__(self, **params):

        super(DynamicToolService, self).__init__(**params)

        self.id = params.get("id")
        topic = params.get("topic", default_topic)

        # Build direct Pulsar topic paths
        request_topic = f"non-persistent://tg/request/{topic}-request"
        response_topic = f"non-persistent://tg/response/{topic}-response"

        logger.info(f"Tool service topics: request={request_topic}, response={response_topic}")

        # Create consumer for requests
        consumer_metrics = ConsumerMetrics(
            processor=self.id, flow=None, name="request"
        )

        self.consumer = Consumer(
            taskgroup=self.taskgroup,
            backend=self.pubsub,
            subscriber=f"{self.id}-request",
            flow=None,
            topic=request_topic,
            schema=ToolServiceRequest,
            handler=self.on_request,
            metrics=consumer_metrics,
        )

        # Create producer for responses
        producer_metrics = ProducerMetrics(
            processor=self.id, flow=None, name="response"
        )

        self.producer = Producer(
            backend=self.pubsub,
            topic=response_topic,
            schema=ToolServiceResponse,
            metrics=producer_metrics,
        )

        if not hasattr(__class__, "tool_service_metric"):
            __class__.tool_service_metric = Counter(
                'dynamic_tool_service_invocation_count',
                'Dynamic tool service invocation count',
                ["id"],
            )

    async def start(self):
        await super(DynamicToolService, self).start()
        await self.producer.start()
        await self.consumer.start()
        logger.info(f"Tool service {self.id} started")

    async def on_request(self, msg, consumer, flow):

        id = None

        try:

            request = msg.value()

            # Sender-produced ID for correlation
            id = msg.properties().get("id", "unknown")

            # Parse the request
            user = request.user or "trustgraph"
            config = json.loads(request.config) if request.config else {}
            arguments = json.loads(request.arguments) if request.arguments else {}

            logger.debug(f"Tool service request: user={user}, config={config}, arguments={arguments}")

            # Invoke the tool implementation
            response = await self.invoke(user, config, arguments)

            # Send success response
            await self.producer.send(
                ToolServiceResponse(
                    error=None,
                    response=response if isinstance(response, str) else json.dumps(response),
                    end_of_stream=True,
                ),
                properties={"id": id}
            )

            __class__.tool_service_metric.labels(
                id=self.id,
            ).inc()

        except TooManyRequests as e:
            raise e

        except Exception as e:

            logger.error(f"Exception in dynamic tool service: {e}", exc_info=True)

            logger.info("Sending error response...")

            await self.producer.send(
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

    async def invoke(self, user, config, arguments):
        """
        Invoke the tool service.

        Override this method in subclasses to implement the tool's logic.

        Args:
            user: The user context for multi-tenancy
            config: Dict of config values from the tool descriptor
            arguments: Dict of arguments from the LLM

        Returns:
            A string response (the observation) or a dict/list that will be JSON-encoded
        """
        raise NotImplementedError("Subclasses must implement invoke()")

    @staticmethod
    def add_args(parser):

        AsyncProcessor.add_args(parser)

        parser.add_argument(
            '-t', '--topic',
            default=default_topic,
            help=f'Topic name for request/response (default: {default_topic})'
        )
