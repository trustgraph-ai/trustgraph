
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

from trustgraph.base import AsyncProcessor, Consumer, Producer
from trustgraph.base.cassandra_config import add_cassandra_args, resolve_cassandra_config

from . config import Configuration, WORKSPACES_NAMESPACE, WORKSPACE_TYPE

from ... base import ProcessorMetrics, ConsumerMetrics, ProducerMetrics
from ... base import Consumer, Producer

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
        config_response_queue = params.get(
            "config_response_queue", default_config_response_queue
        )
        config_push_queue = params.get(
            "config_push_queue", default_config_push_queue
        )

        cassandra_host = params.get("cassandra_host")
        cassandra_username = params.get("cassandra_username")
        cassandra_password = params.get("cassandra_password")

        # Resolve configuration with environment variable fallback
        hosts, username, password, keyspace = resolve_cassandra_config(
            host=cassandra_host,
            username=cassandra_username,
            password=cassandra_password,
            default_keyspace="config"
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

        config_request_metrics = ConsumerMetrics(
            processor = self.id, flow = None, name = "config-request"
        )
        config_response_metrics = ProducerMetrics(
            processor = self.id, flow = None, name = "config-response"
        )
        config_push_metrics = ProducerMetrics(
            processor = self.id, flow = None, name = "config-push"
        )

        self.config_request_queue_base = config_request_queue
        self.config_request_subscriber = id

        self.system_consumer = Consumer(
            taskgroup = self.taskgroup,
            backend = self.pubsub,
            flow = None,
            topic = config_request_queue,
            subscriber = id,
            schema = ConfigRequest,
            handler = self.on_system_config_request,
            metrics = config_request_metrics,
        )

        self.config_response_producer = Producer(
            backend = self.pubsub,
            topic = config_response_queue,
            schema = ConfigResponse,
            metrics = config_response_metrics,
        )

        self.config_push_producer = Producer(
            backend = self.pubsub,
            topic = config_push_queue,
            schema = ConfigPush,
            metrics = config_push_metrics,
        )

        self.config = Configuration(
            host = self.cassandra_host,
            username = self.cassandra_username,
            password = self.cassandra_password,
            keyspace = keyspace,
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
        queue = workspace_queue(
            self.config_request_queue_base, workspace_id,
        )

        await self.pubsub.ensure_topic(queue)

        consumer = Consumer(
            taskgroup=self.taskgroup,
            backend=self.pubsub,
            flow=None,
            topic=queue,
            subscriber=self.id,
            schema=ConfigRequest,
            handler=partial(
                self.on_workspace_config_request,
                workspace=workspace_id,
            ),
            metrics=ConsumerMetrics(
                processor=self.id, flow=None,
                name=f"config-request-{workspace_id}",
            ),
        )

        await consumer.start()
        self.workspace_consumers[workspace_id] = consumer

        logger.info(
            f"Subscribed to workspace config queue: {workspace_id}"
        )

    async def _remove_workspace_consumer(self, workspace_id):
        consumer = self.workspace_consumers.pop(workspace_id, None)
        if consumer:
            await consumer.stop()
            logger.info(
                f"Unsubscribed from workspace config queue: {workspace_id}"
            )

    async def start(self):

        await self.pubsub.ensure_topic(self.config_request_queue_base)
        await self.push()  # Startup poke: empty types = everything
        await self.system_consumer.start()

        # Start the config push subscriber so we receive our own
        # workspace change notifications.
        await self.config_sub_task.start()

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

        await self.config_push_producer.send(resp)

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

            resp = await self.config.handle_workspace(v, workspace)

            await self.config_response_producer.send(
                resp, properties={"id": id}
            )

        except Exception as e:

            resp = ConfigResponse(
                error=Error(
                    type = "config-error",
                    message = str(e),
                ),
            )

            await self.config_response_producer.send(
                resp, properties={"id": id}
            )

    async def on_system_config_request(self, msg, consumer, flow):

        try:

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            logger.debug(f"Handling system config request {id}...")

            resp = await self.config.handle_system(v)

            await self.config_response_producer.send(
                resp, properties={"id": id}
            )

        except Exception as e:

            resp = ConfigResponse(
                error=Error(
                    type = "config-error",
                    message = str(e),
                ),
            )

            await self.config_response_producer.send(
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
