
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
from trustgraph.schema import ConfigRequest, ConfigResponse, ConfigKey, ConfigValue
from trustgraph.schema import config_request_queue, config_response_queue

from trustgraph.base import WorkspaceProcessor
from trustgraph.base import RequestResponseClient

from . flow import FlowConfig

# Module logger
logger = logging.getLogger(__name__)

default_ident = "flow-svc"

default_flow_request_queue = flow_request_queue
default_flow_response_queue = flow_response_queue

CONFIG_TIMEOUT = 10


def workspace_queue(base_queue, workspace):
    return f"{base_queue}:{workspace}"


class AsyncConfigClient:
    """Wraps a RequestResponseClient to provide the same convenience
    methods as the old ConfigClient (get, put, delete, keys, etc.)."""

    def __init__(self, rr_client):
        self._rr = rr_client

    async def _request(self, timeout=CONFIG_TIMEOUT, **kwargs):
        resp = await self._rr.request(
            ConfigRequest(**kwargs),
            timeout=timeout,
        )
        if resp.error:
            raise RuntimeError(
                f"{resp.error.type}: {resp.error.message}"
            )
        return resp

    async def get(self, workspace, type, key, timeout=CONFIG_TIMEOUT):
        resp = await self._request(
            operation="get",
            workspace=workspace,
            keys=[ConfigKey(type=type, key=key)],
            timeout=timeout,
        )
        if resp.values and len(resp.values) > 0:
            return resp.values[0].value
        return None

    async def put(self, workspace, type, key, value, timeout=CONFIG_TIMEOUT):
        await self._request(
            operation="put",
            workspace=workspace,
            values=[ConfigValue(type=type, key=key, value=value)],
            timeout=timeout,
        )

    async def put_many(self, workspace, values, timeout=CONFIG_TIMEOUT):
        await self._request(
            operation="put",
            workspace=workspace,
            values=[
                ConfigValue(type=t, key=k, value=v)
                for t, k, v in values
            ],
            timeout=timeout,
        )

    async def delete(self, workspace, type, key, timeout=CONFIG_TIMEOUT):
        await self._request(
            operation="delete",
            workspace=workspace,
            keys=[ConfigKey(type=type, key=key)],
            timeout=timeout,
        )

    async def delete_many(self, workspace, keys, timeout=CONFIG_TIMEOUT):
        await self._request(
            operation="delete",
            workspace=workspace,
            keys=[
                ConfigKey(type=t, key=k)
                for t, k in keys
            ],
            timeout=timeout,
        )

    async def keys(self, workspace, type, timeout=CONFIG_TIMEOUT):
        resp = await self._request(
            operation="list",
            workspace=workspace,
            type=type,
            timeout=timeout,
        )
        return resp.directory

    async def get_all(self, workspace, timeout=CONFIG_TIMEOUT):
        resp = await self._request(
            operation="config",
            workspace=workspace,
            timeout=timeout,
        )
        return resp.config

    async def workspaces_for_type(self, type, timeout=CONFIG_TIMEOUT):
        resp = await self._request(
            operation="getvalues-all-ws",
            type=type,
            timeout=timeout,
        )
        return {v.workspace for v in resp.values if v.workspace}

    async def close(self):
        await self._rr.close()


class Processor(WorkspaceProcessor):

    def __init__(self, **params):

        self.flow_request_queue_base = params.get(
            "flow_request_queue", default_flow_request_queue
        )
        self.flow_response_queue_base = params.get(
            "flow_response_queue", default_flow_response_queue
        )

        super(Processor, self).__init__(
            **params | {
                "flow_request_schema": FlowRequest.__name__,
                "flow_response_schema": FlowResponse.__name__,
            }
        )

        self.config_client = None
        self.flow = None

        self.workspace_consumers = {}

        logger.info("Flow service initialized")

    async def start(self):

        await super(Processor, self).start()

        rr_client = await RequestResponseClient.create(
            backend=self.async_backend,
            request_topic=config_request_queue,
            response_topic=config_response_queue,
            request_schema=ConfigRequest,
            response_schema=ConfigResponse,
        )

        self.config_client = AsyncConfigClient(rr_client)

        self.flow = FlowConfig(self.config_client, self.async_backend)

        workspaces = await self.config_client.workspaces_for_type("flow")
        await self.flow.ensure_existing_flow_topics(workspaces)

    async def stop(self):

        if self.config_client:
            await self.config_client.close()

        await super(Processor, self).stop()

    async def on_workspace_created(self, workspace):

        if workspace in self.workspace_consumers:
            return

        req_queue = workspace_queue(
            self.flow_request_queue_base, workspace,
        )
        resp_queue = workspace_queue(
            self.flow_response_queue_base, workspace,
        )

        await self.async_backend.ensure_topic(req_queue)
        await self.async_backend.ensure_topic(resp_queue)

        response_handle = await self.sender_pool.add_producer(
            topic=resp_queue,
            schema=FlowResponse,
        )

        async def handler_wrapper(message):
            await self.on_flow_request(message, None, None, workspace=workspace)

        consumer_reg = await self.receiver_pool.add_consumer(
            topic=req_queue,
            subscription=self.id,
            schema=FlowRequest,
            handler=handler_wrapper,
        )

        self.workspace_consumers[workspace] = {
            "consumer": consumer_reg,
            "response": response_handle,
        }

        logger.info(f"Subscribed to workspace queue: {workspace}")

    async def on_workspace_deleted(self, workspace):

        clients = self.workspace_consumers.pop(workspace, None)
        if clients:
            await clients["consumer"].unregister()
            await clients["response"].unregister()
            logger.info(f"Unsubscribed from workspace queue: {workspace}")

    async def on_flow_request(self, msg, consumer, flow, *, workspace):

        try:

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            logger.debug(f"Handling flow request {id}...")

            producer = self.workspace_consumers[workspace]["response"]

            resp = await self.flow.handle(v, workspace)

            await producer.send(
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

            await producer.send(
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
