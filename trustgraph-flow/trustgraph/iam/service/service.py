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
from trustgraph.schema import ConfigRequest, ConfigValue

from trustgraph.base import AsyncProcessor
from trustgraph.base import AuditPublisher
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

        hosts, username, password, keyspace, replication_factor = resolve_cassandra_config(
            host=cassandra_host,
            username=cassandra_username,
            password=cassandra_password,
            default_keyspace="iam",
            replication_factor=params.get("cassandra_replication_factor"),
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

        self.iam_request_topic = iam_req_q
        self.iam_response_topic = iam_resp_q

        self.audit = AuditPublisher(
            component_name="iam-service",
            processor_id=self.id,
        )

        self.iam = IamService(
            host=self.cassandra_host,
            username=self.cassandra_username,
            password=self.cassandra_password,
            keyspace=keyspace,
            replication_factor=replication_factor,
            bootstrap_mode=self.bootstrap_mode,
            bootstrap_token=self.bootstrap_token,
            on_workspace_created=self._ensure_workspace_registered,
            on_workspace_deleted=self._announce_workspace_deleted,
        )

        logger.info(
            f"IAM service initialised (bootstrap-mode={self.bootstrap_mode})"
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

        await self.audit.start(self.sender_pool)

        # Token-mode auto-bootstrap runs before we accept requests so
        # the first inbound call always sees a populated table.
        await self.iam.auto_bootstrap_if_token_mode()

    async def _config_put(self, workspace, type, key, value):
        client = await self._create_config_client()
        try:
            await client.request(
                ConfigRequest(
                    operation="put",
                    workspace=workspace,
                    values=[ConfigValue(type=type, key=key, value=value)],
                ),
                timeout=10,
            )
        finally:
            await client.close()

    async def _config_delete(self, workspace, type, key):
        from trustgraph.schema import ConfigKey
        client = await self._create_config_client()
        try:
            await client.request(
                ConfigRequest(
                    operation="delete",
                    workspace=workspace,
                    keys=[ConfigKey(type=type, key=key)],
                ),
                timeout=10,
            )
        finally:
            await client.close()

    async def _ensure_workspace_registered(self, workspace_id):
        await self._config_put(
            "__workspaces__", "workspace", workspace_id,
            '{"enabled": true}',
        )
        logger.info(
            f"Registered workspace in config: {workspace_id}"
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

    AUTHENTICATE_OPS = frozenset({
        "resolve-api-key", "login", "authenticate-anonymous",
    })
    AUTHORISE_OPS = frozenset({
        "authorise", "authorise-many",
    })
    MANAGEMENT_OPS = frozenset({
        "create-user", "update-user", "disable-user", "enable-user",
        "delete-user", "create-api-key", "revoke-api-key",
        "create-workspace", "update-workspace", "disable-workspace",
        "reset-password", "rotate-signing-key", "bootstrap",
    })

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
            await self._emit_audit(v, resp)
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

    async def _emit_audit(self, v, resp):
        try:
            op = v.operation
            if op in self.AUTHENTICATE_OPS:
                await self._emit_authenticate(v, resp)
            elif op in self.AUTHORISE_OPS:
                await self._emit_authorise(v, resp)
            elif op in self.MANAGEMENT_OPS:
                await self._emit_management(v, resp)
        except Exception:
            logger.debug("Failed to emit IAM audit event", exc_info=True)

    async def _emit_authenticate(self, v, resp):
        has_error = resp.error is not None
        payload = {
            "request_id": v.request_id,
            "credential_type": self._credential_type(v.operation),
            "identity": resp.resolved_user_id if not has_error else "unknown",
            "outcome": "failure" if has_error else "success",
            "client_ip": v.client_ip,
        }
        if has_error:
            payload["failure_reason"] = resp.error.type
        if v.key_id:
            payload["key_id"] = v.key_id
        await self.audit.emit("iam.authenticate", payload)

    async def _emit_authorise(self, v, resp):
        import json as _json
        workspace = v.workspace
        if not workspace:
            try:
                resource = _json.loads(v.resource_json or "{}")
                workspace = resource.get("workspace", "")
            except Exception:
                pass
        payload = {
            "request_id": v.request_id,
            "identity": v.user_id,
            "capability": v.capability,
            "outcome": "allow" if resp.decision_allow else "deny",
        }
        if workspace:
            payload["workspace"] = workspace
        if not resp.decision_allow:
            payload["denial_reason"] = "capability-not-in-role"
        await self.audit.emit("iam.authorise", payload)

    async def _emit_management(self, v, resp):
        has_error = resp.error is not None
        payload = {
            "request_id": v.request_id,
            "actor": v.actor,
            "operation": v.operation,
            "outcome": "error" if has_error else "success",
        }
        if v.user_id:
            payload["target_identity"] = v.user_id
        if v.workspace:
            payload["target_workspace"] = v.workspace
        await self.audit.emit("iam.management", payload)

    @staticmethod
    def _credential_type(operation):
        if operation == "resolve-api-key":
            return "api-key"
        if operation == "login":
            return "login-password"
        return "anonymous"

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
