
"""
Config service.  Manages system global configuration state.

Operates a dual-queue regime:
- System queue (config-request): handles cross-workspace operations like
  getvalues-all-ws and bootstrapper put/delete on __workspaces__.
  The gateway NEVER routes to this queue.
- Per-workspace queues (config-request:<workspace>): handles
  workspace-scoped operations where workspace identity comes from
  queue infrastructure, not message body.
"""

import logging
from functools import partial

from trustgraph.schema import Error

from trustgraph.schema import ConfigRequest, ConfigResponse, ConfigPush
from trustgraph.schema import WorkspaceChanges
from trustgraph.schema import config_request_queue, config_response_queue
from trustgraph.schema import config_push_queue

from trustgraph.base import AsyncProcessor
from trustgraph.base.cassandra_config import add_cassandra_args, resolve_cassandra_config

from . config import Configuration, WORKSPACES_NAMESPACE, WORKSPACE_TYPE

from ... base import ProcessorMetrics, ConsumerMetrics, ProducerMetrics

# Module logger
logger = logging.getLogger(__name__)

default_ident = "config-svc"


def is_reserved_workspace(workspace):
    """Reserved workspaces are storage-only.

    Any workspace id beginning with ``_`` is reserved for internal use
    (e.g. ``__template__`` holding factory-default seed config).
    Reads and writes work normally so bootstrap and provisioning code
    can use the standard config API, but **change notifications for
    reserved workspaces are suppressed**.  Services subscribed to the
    config push therefore never see reserved-workspace events and
    cannot accidentally act on template content as if it were live
    state.
    """
    return workspace.startswith("_")


def workspace_queue(base_queue, workspace):
    return f"{base_queue}:{workspace}"


default_config_request_queue = config_request_queue
default_config_response_queue = config_response_queue
default_config_push_queue = config_push_queue

default_cassandra_host = "cassandra"

class Processor(AsyncProcessor):

    def __init__(self, **params):

        config_request_queue = params.get(
            "config_request_queue", default_config_request_queue
        )
        self.config_response_queue_base = params.get(
            "config_response_queue", default_config_response_queue
        )
        self.config_push_queue_name = params.get(
            "config_push_queue", default_config_push_queue
        )

        cassandra_host = params.get("cassandra_host")
        cassandra_username = params.get("cassandra_username")
        cassandra_password = params.get("cassandra_password")

        # Resolve configuration with environment variable fallback
        hosts, username, password, keyspace, replication_factor = resolve_cassandra_config(
            host=cassandra_host,
            username=cassandra_username,
            password=cassandra_password,
            default_keyspace="config",
            replication_factor=params.get("cassandra_replication_factor"),
        )

        # Store resolved configuration
        self.cassandra_host = hosts
        self.cassandra_username = username
        self.cassandra_password = password

        id = params.get("id")

        super(Processor, self).__init__(
            **params | {
                "config_request_schema": ConfigRequest.__name__,
                "config_response_schema": ConfigResponse.__name__,
                "config_push_schema": ConfigPush.__name__,
                "cassandra_host": self.cassandra_host,
                "cassandra_username": self.cassandra_username,
                "cassandra_password": self.cassandra_password,
            }
        )

        # Store queue names and schemas for pool registration in start()
        self.config_request_queue_base = config_request_queue
        self.config_request_subscriber = id

        self.config = Configuration(
            host = self.cassandra_host,
            username = self.cassandra_username,
            password = self.cassandra_password,
            keyspace = keyspace,
            replication_factor = replication_factor,
            push = self.push
        )

        self.workspace_consumers = {}

        self.register_workspace_handler(self._handle_workspace_changes)

        logger.info("Config service initialized")

    async def _discover_workspaces(self):
        logger.info("Discovering workspaces from Cassandra...")
        try:
            workspaces = await self.config.table_store.get_keys(
                WORKSPACES_NAMESPACE, WORKSPACE_TYPE
            )
            logger.info(f"Discovered workspaces: {workspaces}")
        except Exception as e:
            logger.error(
                f"Workspace discovery failed: {e}", exc_info=True
            )
            return

        for workspace_id in workspaces:
            if workspace_id not in self.workspace_consumers:
                await self._add_workspace_consumer(workspace_id)

    async def _handle_workspace_changes(self, workspace_changes):
        for workspace_id in workspace_changes.created:
            if workspace_id not in self.workspace_consumers:
                logger.info(f"Workspace created: {workspace_id}")
                await self._add_workspace_consumer(workspace_id)
                await self._provision_workspace(workspace_id)

        for workspace_id in workspace_changes.deleted:
            if workspace_id in self.workspace_consumers:
                logger.info(f"Workspace deleted: {workspace_id}")
                await self._remove_workspace_consumer(workspace_id)

    async def _provision_workspace(self, workspace_id):
        try:
            written = await self.config.provision_from_template(
                workspace_id
            )
            if written > 0:
                logger.info(
                    f"Provisioned workspace {workspace_id} with "
                    f"{written} entries from template"
                )
                # Notify other services about the new config
                types = {}
                template = await self.config.get_config(workspace_id)
                for t in template:
                    types[t] = [workspace_id]
                await self.push(changes=types)
        except Exception as e:
            logger.error(
                f"Failed to provision workspace {workspace_id}: {e}",
                exc_info=True,
            )

    async def _add_workspace_consumer(self, workspace_id):
        req_queue = workspace_queue(
            self.config_request_queue_base, workspace_id,
        )
        resp_queue = workspace_queue(
            self.config_response_queue_base, workspace_id,
        )

        await self.async_backend.ensure_topic(req_queue)
        await self.async_backend.ensure_topic(resp_queue)

        response_handle = await self.sender_pool.add_producer(
            topic=resp_queue,
            schema=ConfigResponse,
        )

        handler = partial(
            self.on_workspace_config_request,
            workspace=workspace_id,
        )

        async def wrapper(message):
            await handler(message, None, None)

        consumer_reg = await self.receiver_pool.add_consumer(
            topic=req_queue,
            subscription=self.id,
            schema=ConfigRequest,
            handler=wrapper,
        )

        self.workspace_consumers[workspace_id] = {
            "consumer": consumer_reg,
            "response": response_handle,
        }

        logger.info(
            f"Subscribed to workspace config queue: {workspace_id}"
        )

    async def _remove_workspace_consumer(self, workspace_id):
        clients = self.workspace_consumers.pop(workspace_id, None)
        if clients:
            await clients["consumer"].unregister()
            await clients["response"].unregister()
            logger.info(
                f"Unsubscribed from workspace config queue: {workspace_id}"
            )

    async def start(self):

        # Start the pools since we don't call super().start()
        await self.receiver_pool.start()
        await self.sender_pool.start()

        await self.async_backend.ensure_topic(self.config_request_queue_base)

        # Create system-level producers via sender_pool
        self.config_response_handle = await self.sender_pool.add_producer(
            topic=self.config_response_queue_base,
            schema=ConfigResponse,
        )

        self.config_push_handle = await self.sender_pool.add_producer(
            topic=self.config_push_queue_name,
            schema=ConfigPush,
        )

        await self.push()  # Startup poke: empty types = everything

        # Create system consumer via receiver_pool
        async def system_handler_wrapper(message):
            await self.on_system_config_request(message, None, None)

        self._system_consumer_reg = await self.receiver_pool.add_consumer(
            topic=self.config_request_queue_base,
            subscription=self.id,
            schema=ConfigRequest,
            handler=system_handler_wrapper,
        )

        # Start the config push subscriber so we receive our own
        # workspace change notifications.
        async def config_notify_wrapper(message):
            await self.on_config_notify(message, None, None)

        self._config_sub_reg = await self.receiver_pool.add_consumer(
            topic=self.config_push_queue,
            subscription=self.id,
            schema=ConfigPush,
            handler=config_notify_wrapper,
        )

        await self._discover_workspaces()

    async def push(self, changes=None, workspace_changes=None):

        # Suppress notifications from reserved workspaces (ids starting
        # with "_", e.g. "__template__") for regular config changes.
        # The __workspaces__ namespace is handled separately via
        # workspace_changes.
        if changes:
            filtered = {}
            for type_name, workspaces in changes.items():
                visible = [
                    w for w in workspaces
                    if not is_reserved_workspace(w)
                ]
                if visible:
                    filtered[type_name] = visible
            changes = filtered

        version = await self.config.get_version()

        resp = ConfigPush(
            version = version,
            changes = changes or {},
            workspace_changes = workspace_changes,
        )

        await self.config_push_handle.send(resp)

        logger.info(
            f"Pushed config poke version {version}, "
            f"changes={resp.changes}, "
            f"workspace_changes={resp.workspace_changes}"
        )

    async def on_workspace_config_request(
        self, msg, consumer, flow, *, workspace
    ):

        try:

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            logger.debug(
                f"Handling workspace config request {id} "
                f"workspace={workspace}..."
            )

            handle = self.workspace_consumers[workspace]["response"]

            resp = await self.config.handle_workspace(v, workspace)

            await handle.send(
                resp, properties={"id": id}
            )

        except Exception as e:

            resp = ConfigResponse(
                error=Error(
                    type = "config-error",
                    message = str(e),
                ),
            )

            await handle.send(
                resp, properties={"id": id}
            )

    async def on_system_config_request(self, msg, consumer, flow):

        try:

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            logger.debug(f"Handling system config request {id}...")

            resp = await self.config.handle_system(v)

            await self.config_response_handle.send(
                resp, properties={"id": id}
            )

        except Exception as e:

            resp = ConfigResponse(
                error=Error(
                    type = "config-error",
                    message = str(e),
                ),
            )

            await self.config_response_handle.send(
                resp, properties={"id": id}
            )

    @staticmethod
    def add_args(parser):

        AsyncProcessor.add_args(parser)

        parser.add_argument(
            '--config-request-queue',
            default=default_config_request_queue,
            help=f'Config request queue (default: {default_config_request_queue})'
        )

        parser.add_argument(
            '--config-response-queue',
            default=default_config_response_queue,
            help=f'Config response queue {default_config_response_queue}',
        )

        # Note: --config-push-queue is already added by AsyncProcessor.add_args()

        add_cassandra_args(parser)

def run():

    Processor.launch(default_ident, __doc__)
