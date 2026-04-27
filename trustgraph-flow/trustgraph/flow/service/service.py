
"""
Flow service.  Manages flow lifecycle — starting and stopping flows
by coordinating with the config service via pub/sub.
"""

import logging
import uuid

from trustgraph.schema import Error

from trustgraph.schema import FlowRequest, FlowResponse
from trustgraph.schema import flow_request_queue, flow_response_queue
from trustgraph.schema import ConfigRequest, ConfigResponse
from trustgraph.schema import config_request_queue, config_response_queue

from trustgraph.base import AsyncProcessor, Consumer, Producer
from trustgraph.base import ConsumerMetrics, ProducerMetrics, SubscriberMetrics
from trustgraph.base import ConfigClient

from . flow import FlowConfig

# Module logger
logger = logging.getLogger(__name__)

default_ident = "flow-svc"

default_flow_request_queue = flow_request_queue
default_flow_response_queue = flow_response_queue


class Processor(AsyncProcessor):

    def __init__(self, **params):

        flow_request_queue = params.get(
            "flow_request_queue", default_flow_request_queue
        )
        flow_response_queue = params.get(
            "flow_response_queue", default_flow_response_queue
        )

        id = params.get("id")

        super(Processor, self).__init__(
            **params | {
                "flow_request_schema": FlowRequest.__name__,
                "flow_response_schema": FlowResponse.__name__,
            }
        )

        flow_request_metrics = ConsumerMetrics(
            processor = self.id, flow = None, name = "flow-request"
        )
        flow_response_metrics = ProducerMetrics(
            processor = self.id, flow = None, name = "flow-response"
        )

        self.flow_request_topic = flow_request_queue
        self.flow_request_subscriber = id

        self.flow_request_consumer = Consumer(
            taskgroup = self.taskgroup,
            backend = self.pubsub,
            flow = None,
            topic = flow_request_queue,
            subscriber = id,
            schema = FlowRequest,
            handler = self.on_flow_request,
            metrics = flow_request_metrics,
        )

        self.flow_response_producer = Producer(
            backend = self.pubsub,
            topic = flow_response_queue,
            schema = FlowResponse,
            metrics = flow_response_metrics,
        )

        config_req_metrics = ProducerMetrics(
            processor=self.id, flow=None, name="config-request",
        )
        config_resp_metrics = SubscriberMetrics(
            processor=self.id, flow=None, name="config-response",
        )

        # Unique subscription suffix per process instance.  Pulsar's
        # exclusive subscriptions reject a second consumer on the same
        # (topic, subscription-name) — so a deterministic name here
        # collides with its own ghost when the supervisor restarts the
        # process before Pulsar has timed out the previous session
        # (ConsumerBusy).  Matches the uuid convention used elsewhere
        # (gateway/config/receiver.py, AsyncProcessor._create_config_client).
        config_rr_id = str(uuid.uuid4())
        self.config_client = ConfigClient(
            backend=self.pubsub,
            subscription=f"{self.id}--config--{config_rr_id}",
            consumer_name=self.id,
            request_topic=config_request_queue,
            request_schema=ConfigRequest,
            request_metrics=config_req_metrics,
            response_topic=config_response_queue,
            response_schema=ConfigResponse,
            response_metrics=config_resp_metrics,
        )

        self.flow = FlowConfig(self.config_client, self.pubsub)

        logger.info("Flow service initialized")

    async def start(self):

        await self.pubsub.ensure_topic(self.flow_request_topic)
        await self.config_client.start()

        # Discover workspaces with existing flow config and ensure
        # their topics exist before we start accepting requests.
        workspaces = await self.config_client.workspaces_for_type("flow")
        await self.flow.ensure_existing_flow_topics(workspaces)

        await self.flow_request_consumer.start()

    async def on_flow_request(self, msg, consumer, flow):

        try:

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            logger.debug(f"Handling flow request {id}...")

            resp = await self.flow.handle(v)

            await self.flow_response_producer.send(
                resp, properties={"id": id}
            )

        except Exception as e:

            logger.error(f"Flow request failed: {e}")

            resp = FlowResponse(
                error=Error(
                    type = "flow-error",
                    message = str(e),
                ),
            )

            await self.flow_response_producer.send(
                resp, properties={"id": id}
            )

    @staticmethod
    def add_args(parser):

        AsyncProcessor.add_args(parser)

        parser.add_argument(
            '--flow-request-queue',
            default=default_flow_request_queue,
            help=f'Flow request queue (default: {default_flow_request_queue})'
        )

        parser.add_argument(
            '--flow-response-queue',
            default=default_flow_response_queue,
            help=f'Flow response queue {default_flow_response_queue}',
        )

def run():

    Processor.launch(default_ident, __doc__)
