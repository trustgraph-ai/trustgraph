"""
No-auth IAM service.  Drop-in replacement for iam-svc that permits
all access unconditionally.  No database, no bootstrap, no signing keys.
"""

import logging

from trustgraph.schema import Error
from trustgraph.schema import IamRequest, IamResponse
from trustgraph.schema import iam_request_queue, iam_response_queue
from trustgraph.schema import ConfigRequest, ConfigValue

from trustgraph.base import AsyncProcessor

from . handler import NoAuthHandler

logger = logging.getLogger(__name__)

default_ident = "no-auth-svc"

default_iam_request_queue = iam_request_queue
default_iam_response_queue = iam_response_queue


class Processor(AsyncProcessor):

    def __init__(self, **params):

        self.iam_request_topic = params.get(
            "iam_request_queue", default_iam_request_queue,
        )
        self.iam_response_topic = params.get(
            "iam_response_queue", default_iam_response_queue,
        )

        default_user_id = params.get("default_user_id", "anonymous")
        default_workspace = params.get("default_workspace", "default")

        super().__init__(**params)

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
        await super().start()

        await self.async_backend.ensure_topic(self.iam_request_topic)

        async def wrapper(message):
            await self.on_iam_request(message, None, None)

        self.iam_request_consumer = \
            await self.receiver_pool.add_consumer(
                topic=self.iam_request_topic,
                subscription=self.id,
                schema=IamRequest,
                handler=wrapper,
            )

        self.iam_response_producer = \
            await self.sender_pool.add_producer(
                topic=self.iam_response_topic,
                schema=IamResponse,
            )

    async def _ensure_workspace_registered(self, workspace_id):
        client = await self._create_config_client()
        try:
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
            await client.close()
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
