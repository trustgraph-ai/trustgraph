"""
No-auth IAM service.  Drop-in replacement for iam-svc that permits
all access unconditionally.  No database, no bootstrap, no signing keys.
"""

import logging
import uuid

from trustgraph.schema import Error
from trustgraph.schema import IamRequest, IamResponse
from trustgraph.schema import iam_request_queue, iam_response_queue
from trustgraph.schema import ConfigRequest, ConfigResponse, ConfigValue
from trustgraph.schema import config_request_queue, config_response_queue

from trustgraph.base import AsyncProcessor, Consumer, Producer
from trustgraph.base import ConsumerMetrics, ProducerMetrics
from trustgraph.base.metrics import SubscriberMetrics
from trustgraph.base.request_response_spec import RequestResponse

from . handler import NoAuthHandler

logger = logging.getLogger(__name__)

default_ident = "no-auth-svc"

default_iam_request_queue = iam_request_queue
default_iam_response_queue = iam_response_queue


class Processor(AsyncProcessor):

    def __init__(self, **params):

        iam_req_q = params.get(
            "iam_request_queue", default_iam_request_queue,
        )
        iam_resp_q = params.get(
            "iam_response_queue", default_iam_response_queue,
        )

        default_user_id = params.get("default_user_id", "anonymous")
        default_workspace = params.get("default_workspace", "default")

        super().__init__(**params)

        iam_request_metrics = ConsumerMetrics(
            processor=self.id, flow=None, name="iam-request",
        )
        iam_response_metrics = ProducerMetrics(
            processor=self.id, flow=None, name="iam-response",
        )

        self.iam_request_topic = iam_req_q

        self.iam_request_consumer = Consumer(
            taskgroup=self.taskgroup,
            backend=self.pubsub,
            flow=None,
            topic=iam_req_q,
            subscriber=self.id,
            schema=IamRequest,
            handler=self.on_iam_request,
            metrics=iam_request_metrics,
        )

        self.iam_response_producer = Producer(
            backend=self.pubsub,
            topic=iam_resp_q,
            schema=IamResponse,
            metrics=iam_response_metrics,
        )

        self.handler = NoAuthHandler(
            default_user_id=default_user_id,
            default_workspace=default_workspace,
            on_workspace_created=self._ensure_workspace_registered,
        )

        logger.info(
            f"No-auth IAM service initialised "
            f"(user={default_user_id}, workspace={default_workspace})"
        )

    async def start(self):
        await self.pubsub.ensure_topic(self.iam_request_topic)
        await self.iam_request_consumer.start()

    def _create_config_client(self):
        config_rr_id = str(uuid.uuid4())
        config_req_metrics = ProducerMetrics(
            processor=self.id, flow=None, name="config-request",
        )
        config_resp_metrics = SubscriberMetrics(
            processor=self.id, flow=None, name="config-response",
        )
        return RequestResponse(
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

    async def _ensure_workspace_registered(self, workspace_id):
        client = self._create_config_client()
        try:
            await client.start()
            await client.request(
                ConfigRequest(
                    operation="put",
                    workspace="__workspaces__",
                    values=[ConfigValue(
                        type="workspace", key=workspace_id,
                        value='{"enabled": true}',
                    )],
                ),
                timeout=10,
            )
        finally:
            await client.stop()
        logger.info(
            f"Registered workspace in config: {workspace_id}"
        )

    async def on_iam_request(self, msg, consumer, flow):

        id = None
        try:
            v = msg.value()
            id = msg.properties()["id"]
            logger.debug(
                f"Handling IAM request {id} op={v.operation!r}"
            )
            resp = await self.handler.handle(v)
            await self.iam_response_producer.send(
                resp, properties={"id": id},
            )
        except Exception as e:
            logger.error(
                f"IAM request failed: {type(e).__name__}: {e}",
                exc_info=True,
            )
            resp = IamResponse(
                error=Error(type="internal-error", message=str(e)),
            )
            if id is not None:
                await self.iam_response_producer.send(
                    resp, properties={"id": id},
                )

    @staticmethod
    def add_args(parser):
        AsyncProcessor.add_args(parser)

        parser.add_argument(
            "--iam-request-queue",
            default=default_iam_request_queue,
            help=f"IAM request queue (default: {default_iam_request_queue})",
        )
        parser.add_argument(
            "--iam-response-queue",
            default=default_iam_response_queue,
            help=f"IAM response queue (default: {default_iam_response_queue})",
        )
        parser.add_argument(
            "--default-user-id",
            default="anonymous",
            help="User ID for all requests (default: anonymous)",
        )
        parser.add_argument(
            "--default-workspace",
            default="default",
            help="Workspace for all requests (default: default)",
        )


def run():
    Processor.launch(default_ident, __doc__)
