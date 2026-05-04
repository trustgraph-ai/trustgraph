
"""
Flow service.  Manages flow lifecycle — starting and stopping flows
by coordinating with the config service via pub/sub.
"""

from functools import partial
import logging
import uuid

from trustgraph.schema import Error

from trustgraph.schema import FlowRequest, FlowResponse
from trustgraph.schema import flow_request_queue, flow_response_queue
from trustgraph.schema import ConfigRequest, ConfigResponse
from trustgraph.schema import config_request_queue, config_response_queue

from trustgraph.base import WorkspaceProcessor, Consumer, Producer
from trustgraph.base import ConsumerMetrics, ProducerMetrics, SubscriberMetrics
from trustgraph.base import ConfigClient

from . flow import FlowConfig

# Module logger
logger = logging.getLogger(__name__)

default_ident = "flow-svc"

default_flow_request_queue = flow_request_queue
default_flow_response_queue = flow_response_queue


def workspace_queue(base_queue, workspace):
    return f"{base_queue}:{workspace}"


class Processor(WorkspaceProcessor):

    def __init__(self, **params):

        self.flow_request_queue_base = params.get(
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

        flow_response_metrics = ProducerMetrics(
            processor = self.id, flow = None, name = "flow-response"
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

        self.workspace_consumers = {}

        logger.info("Flow service initialized")

    async def on_workspace_created(self, workspace):

        if workspace in self.workspace_consumers:
            return

        queue = workspace_queue(
            self.flow_request_queue_base, workspace,
        )

        await self.pubsub.ensure_topic(queue)

        consumer = Consumer(
            taskgroup=self.taskgroup,
            backend=self.pubsub,
            flow=None,
            topic=queue,
            subscriber=self.id,
            schema=FlowRequest,
            handler=partial(
                self.on_flow_request, workspace=workspace,
            ),
            metrics=ConsumerMetrics(
                processor=self.id, flow=None,
                name=f"flow-request-{workspace}",
            ),
        )

        await consumer.start()
        self.workspace_consumers[workspace] = consumer

        logger.info(f"Subscribed to workspace queue: {workspace}")

    async def on_workspace_deleted(self, workspace):

        consumer = self.workspace_consumers.pop(workspace, None)
        if consumer:
            await consumer.stop()
            logger.info(f"Unsubscribed from workspace queue: {workspace}")

    async def start(self):

        await super(Processor, self).start()
        await self.config_client.start()

        workspaces = await self.config_client.workspaces_for_type("flow")
        await self.flow.ensure_existing_flow_topics(workspaces)

    async def on_flow_request(self, msg, consumer, flow, *, workspace):

        try:

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            logger.debug(f"Handling flow request {id}...")

            resp = await self.flow.handle(v, workspace)

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

        WorkspaceProcessor.add_args(parser)

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
