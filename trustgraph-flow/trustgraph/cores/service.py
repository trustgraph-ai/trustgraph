
"""
Knowledge core service, manages cores and exports them
"""

from functools import partial
import asyncio
import base64
import json
import logging

from .. base import WorkspaceProcessor, Consumer, Producer, Publisher, Subscriber
from .. base import ConsumerMetrics, ProducerMetrics
from .. base.cassandra_config import add_cassandra_args, resolve_cassandra_config
from .. base import LibrarianClient

from .. schema import KnowledgeRequest, KnowledgeResponse, Error
from .. schema import knowledge_request_queue, knowledge_response_queue
from .. schema import librarian_request_queue, librarian_response_queue

from .. schema import Document, Metadata
from .. schema import TextDocument, Metadata

from .. exceptions import RequestError

from . knowledge import KnowledgeManager

# Module logger
logger = logging.getLogger(__name__)

default_ident = "knowledge"

default_knowledge_request_queue = knowledge_request_queue
default_knowledge_response_queue = knowledge_response_queue

default_cassandra_host = "cassandra"


def workspace_queue(base_queue, workspace):
    return f"{base_queue}:{workspace}"


class Processor(WorkspaceProcessor):

    def __init__(self, **params):

        id = params.get("id")

        self.knowledge_request_queue_base = params.get(
            "knowledge_request_queue", default_knowledge_request_queue
        )

        self.knowledge_response_queue_base = params.get(
            "knowledge_response_queue", default_knowledge_response_queue
        )

        cassandra_host = params.get("cassandra_host")
        cassandra_username = params.get("cassandra_username")
        cassandra_password = params.get("cassandra_password")

        hosts, username, password, keyspace, replication_factor = resolve_cassandra_config(
            host=cassandra_host,
            username=cassandra_username,
            password=cassandra_password,
            default_keyspace="knowledge",
            replication_factor=params.get("cassandra_replication_factor"),
        )

        self.cassandra_host = hosts
        self.cassandra_username = username
        self.cassandra_password = password

        super(Processor, self).__init__(
            **params | {
                "knowledge_request_queue": self.knowledge_request_queue_base,
                "knowledge_response_queue": self.knowledge_response_queue_base,
                "cassandra_host": self.cassandra_host,
                "cassandra_username": self.cassandra_username,
                "cassandra_password": self.cassandra_password,
            }
        )

        self.librarian_clients = {}

        self.knowledge = KnowledgeManager(
            cassandra_host = self.cassandra_host,
            cassandra_username = self.cassandra_username,
            cassandra_password = self.cassandra_password,
            keyspace = keyspace,
            flow_config = self,
            librarian_clients = self.librarian_clients,
            replication_factor = replication_factor,
        )

        self.register_config_handler(self.on_knowledge_config, types=["flow"])

        self.flows = {}

        self.workspace_consumers = {}

        logger.info("Knowledge service initialized")

    async def on_workspace_created(self, workspace):

        if workspace in self.workspace_consumers:
            return

        req_queue = workspace_queue(
            self.knowledge_request_queue_base, workspace,
        )
        resp_queue = workspace_queue(
            self.knowledge_response_queue_base, workspace,
        )

        await self.pubsub.ensure_topic(req_queue)
        await self.pubsub.ensure_topic(resp_queue)

        response_producer = Producer(
            backend=self.pubsub,
            topic=resp_queue,
            schema=KnowledgeResponse,
            metrics=ProducerMetrics(
                processor=self.id, producer="knowledge-response",
                workspace=workspace,
            ),
        )

        consumer = Consumer(
            taskgroup=self.taskgroup,
            backend=self.pubsub,
            flow=None,
            topic=req_queue,
            subscriber=self.id,
            schema=KnowledgeRequest,
            handler=partial(
                self.on_knowledge_request, workspace=workspace,
            ),
            metrics=ConsumerMetrics(
                processor=self.id, consumer="knowledge-request",
                workspace=workspace,
            ),
        )

        librarian_client = LibrarianClient(
            id=self.id,
            backend=self.pubsub,
            taskgroup=self.taskgroup,
            librarian_request_queue=workspace_queue(
                librarian_request_queue, workspace,
            ),
            librarian_response_queue=workspace_queue(
                librarian_response_queue, workspace,
            ),
            librarian_subscriber=(
                f"{self.id}--{workspace}--librarian"
            ),
        )

        await response_producer.start()
        await consumer.start()
        await librarian_client.start()

        self.librarian_clients[workspace] = librarian_client

        self.workspace_consumers[workspace] = {
            "consumer": consumer,
            "response": response_producer,
            "librarian": librarian_client,
        }

        logger.info(f"Subscribed to workspace queue: {workspace}")

    async def on_workspace_deleted(self, workspace):

        self.librarian_clients.pop(workspace, None)

        clients = self.workspace_consumers.pop(workspace, None)
        if clients:
            for client in clients.values():
                await client.stop()
            logger.info(f"Unsubscribed from workspace queue: {workspace}")

    async def start(self):

        await super(Processor, self).start()

    async def on_knowledge_config(self, workspace, config, version):

        logger.info(
            f"Configuration version: {version} workspace: {workspace}"
        )

        if "flow" in config:
            self.flows[workspace] = {
                k: json.loads(v)
                for k, v in config["flow"].items()
            }
        else:
            self.flows[workspace] = {}

        logger.debug(f"Flows for {workspace}: {self.flows[workspace]}")

    async def process_request(self, v, id, workspace, producer):

        if v.operation is None:
            raise RequestError("Null operation")

        logger.debug(f"Knowledge request: {v.operation}")

        impls = {
            "list-kg-cores": self.knowledge.list_kg_cores,
            "get-kg-core": self.knowledge.get_kg_core,
            "delete-kg-core": self.knowledge.delete_kg_core,
            "put-kg-core": self.knowledge.put_kg_core,
            "load-kg-core": self.knowledge.load_kg_core,
            "unload-kg-core": self.knowledge.unload_kg_core,
            "list-de-cores": self.knowledge.list_de_cores,
            "get-de-core": self.knowledge.get_de_core,
            "delete-de-core": self.knowledge.delete_de_core,
            "put-de-core": self.knowledge.put_de_core,
            "load-de-core": self.knowledge.load_de_core,
        }

        if v.operation not in impls:
            raise RequestError(f"Invalid operation: {v.operation}")

        async def respond(x):
            await producer.send(
                x, { "id": id }
            )
        return await impls[v.operation](v, respond, workspace)

    async def on_knowledge_request(self, msg, consumer, flow, *, workspace):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        logger.info(f"Handling knowledge input {id}...")

        producer = self.workspace_consumers[workspace]["response"]

        try:

            # We don't send a response back here, the processing
            # implementation sends whatever it needs to send.
            await self.process_request(v, id, workspace, producer)

            return

        except RequestError as e:
            resp = KnowledgeResponse(
                error = Error(
                    type = "request-error",
                    message = str(e),
                )
            )

            await producer.send(
                resp, properties={"id": id}
            )

            return
        except Exception as e:
            resp = KnowledgeResponse(
                error = Error(
                    type = "unexpected-error",
                    message = str(e),
                )
            )

            await producer.send(
                resp, properties={"id": id}
            )

            return

        logger.debug("Knowledge input processing complete")

    @staticmethod
    def add_args(parser):

        WorkspaceProcessor.add_args(parser)

        parser.add_argument(
            '--knowledge-request-queue',
            default=default_knowledge_request_queue,
            help=f'Config request queue (default: {default_knowledge_request_queue})'
        )

        parser.add_argument(
            '--knowledge-response-queue',
            default=default_knowledge_response_queue,
            help=f'Config response queue {default_knowledge_response_queue}',
        )

        add_cassandra_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

