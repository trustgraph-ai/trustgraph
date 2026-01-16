
"""
Knowledge core service, manages cores and exports them
"""

from functools import partial
import asyncio
import base64
import json
import logging

from .. base import AsyncProcessor, Consumer, Producer, Publisher, Subscriber
from .. base import ConsumerMetrics, ProducerMetrics
from .. base.cassandra_config import add_cassandra_args, resolve_cassandra_config

from .. schema import KnowledgeRequest, KnowledgeResponse, Error
from .. schema import knowledge_request_queue, knowledge_response_queue

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

class Processor(AsyncProcessor):

    def __init__(self, **params):

        id = params.get("id")

        knowledge_request_queue = params.get(
            "knowledge_request_queue", default_knowledge_request_queue
        )

        knowledge_response_queue = params.get(
            "knowledge_response_queue", default_knowledge_response_queue
        )

        cassandra_host = params.get("cassandra_host")
        cassandra_username = params.get("cassandra_username")
        cassandra_password = params.get("cassandra_password")

        # Resolve configuration with environment variable fallback
        hosts, username, password, keyspace = resolve_cassandra_config(
            host=cassandra_host,
            username=cassandra_username,
            password=cassandra_password,
            default_keyspace="knowledge"
        )

        # Store resolved configuration
        self.cassandra_host = hosts
        self.cassandra_username = username
        self.cassandra_password = password

        super(Processor, self).__init__(
            **params | {
                "knowledge_request_queue": knowledge_request_queue,
                "knowledge_response_queue": knowledge_response_queue,
                "cassandra_host": self.cassandra_host,
                "cassandra_username": self.cassandra_username,
                "cassandra_password": self.cassandra_password,
            }
        )

        knowledge_request_metrics = ConsumerMetrics(
            processor = self.id, flow = None, name = "knowledge-request"
        )

        knowledge_response_metrics = ProducerMetrics(
            processor = self.id, flow = None, name = "knowledge-response"
        )

        self.knowledge_request_consumer = Consumer(
            taskgroup = self.taskgroup,
            backend = self.pubsub,
            flow = None,
            topic = knowledge_request_queue,
            subscriber = id,
            schema = KnowledgeRequest,
            handler = self.on_knowledge_request,
            metrics = knowledge_request_metrics,
        )

        self.knowledge_response_producer = Producer(
            backend = self.pubsub,
            topic = knowledge_response_queue,
            schema = KnowledgeResponse,
            metrics = knowledge_response_metrics,
        )

        self.knowledge = KnowledgeManager(
            cassandra_host = self.cassandra_host,
            cassandra_username = self.cassandra_username,
            cassandra_password = self.cassandra_password,
            keyspace = keyspace,
            flow_config = self,
        )

        self.register_config_handler(self.on_knowledge_config)

        self.flows = {}

        logger.info("Knowledge service initialized")

    async def start(self):

        await super(Processor, self).start()
        await self.knowledge_request_consumer.start()
        await self.knowledge_response_producer.start()

    async def on_knowledge_config(self, config, version):

        logger.info(f"Configuration version: {version}")

        if "flow" in config:
            self.flows = {
                k: json.loads(v)
                for k, v in config["flow"].items()
            }
        else:
            self.flows = {}

        logger.debug(f"Flows: {self.flows}")

    async def process_request(self, v, id):

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
        }

        if v.operation not in impls:
            raise RequestError(f"Invalid operation: {v.operation}")

        async def respond(x):
            await self.knowledge_response_producer.send(
                x, { "id": id }
            )
        return await impls[v.operation](v, respond)

    async def on_knowledge_request(self, msg, consumer, flow):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        logger.info(f"Handling knowledge input {id}...")

        try:

            # We don't send a response back here, the processing
            # implementation sends whatever it needs to send.
            await self.process_request(v, id)

            return

        except RequestError as e:
            resp = KnowledgeResponse(
                error = Error(
                    type = "request-error",
                    message = str(e),
                )
            )

            await self.knowledge_response_producer.send(
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

            await self.knowledge_response_producer.send(
                resp, properties={"id": id}
            )

            return

        logger.debug("Knowledge input processing complete")

    @staticmethod
    def add_args(parser):

        AsyncProcessor.add_args(parser)

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

