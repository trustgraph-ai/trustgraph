"""
IAM service processor.  Terminates the IAM request queue and forwards
each request to the IamService business logic, then returns the
response on the IAM response queue.

Shape mirrors trustgraph.config.service.
"""

import logging
import os

from trustgraph.schema import Error
from trustgraph.schema import IamRequest, IamResponse
from trustgraph.schema import iam_request_queue, iam_response_queue
from trustgraph.schema import ConfigRequest, ConfigResponse, ConfigValue
from trustgraph.schema import config_request_queue, config_response_queue

from trustgraph.base import AsyncProcessor, Consumer, Producer
from trustgraph.base import ConsumerMetrics, ProducerMetrics
from trustgraph.base.metrics import SubscriberMetrics
from trustgraph.base.request_response_spec import RequestResponse
from trustgraph.base.cassandra_config import (
    add_cassandra_args, resolve_cassandra_config,
)

from . iam import IamService

logger = logging.getLogger(__name__)

default_ident = "iam-svc"

default_iam_request_queue = iam_request_queue
default_iam_response_queue = iam_response_queue

# Environment variables consulted as a fallback when the
# corresponding params field is not set in the processor-group YAML
# or via CLI.  Intended for K8s Secret / env-var injection so the
# bootstrap token never has to live in the YAML (and thus in git).
ENV_BOOTSTRAP_MODE = "IAM_BOOTSTRAP_MODE"
ENV_BOOTSTRAP_TOKEN = "IAM_BOOTSTRAP_TOKEN"


class Processor(AsyncProcessor):

    def __init__(self, **params):

        iam_req_q = params.get(
            "iam_request_queue", default_iam_request_queue,
        )
        iam_resp_q = params.get(
            "iam_response_queue", default_iam_response_queue,
        )

        # Resolve bootstrap mode + token.  Precedence: explicit
        # params (CLI / processor-group YAML) → environment variable
        # → unset (fail-closed).  The env-var path is the K8s-native
        # injection point: an `IAM_BOOTSTRAP_TOKEN` from a Secret
        # never has to land in the YAML, and therefore never enters
        # git history.
        bootstrap_mode = (
            params.get("bootstrap_mode")
            or os.environ.get(ENV_BOOTSTRAP_MODE)
        )
        bootstrap_token = (
            params.get("bootstrap_token")
            or os.environ.get(ENV_BOOTSTRAP_TOKEN)
        )

        if bootstrap_mode not in ("token", "bootstrap"):
            raise RuntimeError(
                "iam-svc: bootstrap-mode is required.  Set to 'token' "
                "(with bootstrap-token) for production, or 'bootstrap' "
                "to enable the explicit bootstrap operation over the "
                "pub/sub bus (dev / quick-start only, not safe under "
                "public exposure).  Configurable via processor-group "
                f"params or the {ENV_BOOTSTRAP_MODE} environment "
                "variable.  Refusing to start."
            )
        if bootstrap_mode == "token" and not bootstrap_token:
            raise RuntimeError(
                "iam-svc: bootstrap-mode=token requires bootstrap-token "
                f"(or the {ENV_BOOTSTRAP_TOKEN} environment "
                "variable).  Refusing to start."
            )
        if bootstrap_mode == "bootstrap" and bootstrap_token:
            raise RuntimeError(
                "iam-svc: bootstrap-token is not accepted when "
                "bootstrap-mode=bootstrap.  Ambiguous intent.  "
                "Refusing to start."
            )

        self.bootstrap_mode = bootstrap_mode
        self.bootstrap_token = bootstrap_token

        cassandra_host = params.get("cassandra_host")
        cassandra_username = params.get("cassandra_username")
        cassandra_password = params.get("cassandra_password")

        hosts, username, password, keyspace = resolve_cassandra_config(
            host=cassandra_host,
            username=cassandra_username,
            password=cassandra_password,
            default_keyspace="iam",
        )

        self.cassandra_host = hosts
        self.cassandra_username = username
        self.cassandra_password = password

        super().__init__(
            **params | {
                "iam_request_schema": IamRequest.__name__,
                "iam_response_schema": IamResponse.__name__,
                "cassandra_host": self.cassandra_host,
                "cassandra_username": self.cassandra_username,
                "cassandra_password": self.cassandra_password,
            }
        )

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

        self.iam = IamService(
            host=self.cassandra_host,
            username=self.cassandra_username,
            password=self.cassandra_password,
            keyspace=keyspace,
            bootstrap_mode=self.bootstrap_mode,
            bootstrap_token=self.bootstrap_token,
            on_workspace_created=self._announce_workspace_created,
            on_workspace_deleted=self._announce_workspace_deleted,
        )

        logger.info(
            f"IAM service initialised (bootstrap-mode={self.bootstrap_mode})"
        )

    async def start(self):
        await self.pubsub.ensure_topic(self.iam_request_topic)
        # Token-mode auto-bootstrap runs before we accept requests so
        # the first inbound call always sees a populated table.
        await self.iam.auto_bootstrap_if_token_mode()
        await self.iam_request_consumer.start()

    def _create_config_client(self):
        import uuid
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

    async def _config_put(self, workspace, type, key, value):
        client = self._create_config_client()
        try:
            await client.start()
            await client.request(
                ConfigRequest(
                    operation="put",
                    workspace=workspace,
                    values=[ConfigValue(type=type, key=key, value=value)],
                ),
                timeout=10,
            )
        finally:
            await client.stop()

    async def _config_delete(self, workspace, type, key):
        from trustgraph.schema import ConfigKey
        client = self._create_config_client()
        try:
            await client.start()
            await client.request(
                ConfigRequest(
                    operation="delete",
                    workspace=workspace,
                    keys=[ConfigKey(type=type, key=key)],
                ),
                timeout=10,
            )
        finally:
            await client.stop()

    async def _announce_workspace_created(self, workspace_id):
        try:
            await self._config_put(
                "__workspaces__", "workspace", workspace_id,
                '{"enabled": true}',
            )
            logger.info(
                f"Announced workspace creation: {workspace_id}"
            )
        except Exception as e:
            logger.error(
                f"Failed to announce workspace creation "
                f"{workspace_id}: {e}", exc_info=True,
            )

    async def _announce_workspace_deleted(self, workspace_id):
        try:
            await self._config_delete(
                "__workspaces__", "workspace", workspace_id,
            )
            logger.info(
                f"Announced workspace deletion: {workspace_id}"
            )
        except Exception as e:
            logger.error(
                f"Failed to announce workspace deletion "
                f"{workspace_id}: {e}", exc_info=True,
            )

    async def on_iam_request(self, msg, consumer, flow):

        id = None
        try:
            v = msg.value()
            id = msg.properties()["id"]
            logger.debug(
                f"Handling IAM request {id} op={v.operation!r}"
            )
            resp = await self.iam.handle(v)
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
            "--bootstrap-mode",
            default=None,
            choices=["token", "bootstrap"],
            help=(
                "IAM bootstrap mode (required).  "
                "'token' = operator supplies the initial admin API "
                "key via --bootstrap-token; auto-seeds on first start, "
                "bootstrap operation refused.  "
                "'bootstrap' = bootstrap operation is live over the "
                "bus until tables are populated; a token is generated "
                "and returned by tg-bootstrap-iam.  Unsafe to run "
                "'bootstrap' mode with public exposure."
            ),
        )
        parser.add_argument(
            "--bootstrap-token",
            default=None,
            help=(
                "Initial admin API key plaintext, required when "
                "--bootstrap-mode=token.  Treat as a one-time "
                "credential: the operator should rotate to a new key "
                "and revoke this one after first use."
            ),
        )

        add_cassandra_args(parser)


def run():
    Processor.launch(default_ident, __doc__)
