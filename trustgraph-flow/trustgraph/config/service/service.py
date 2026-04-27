
"""
Config service.  Manages system global configuration state
"""

import logging

from trustgraph.schema import Error

from trustgraph.schema import ConfigRequest, ConfigResponse, ConfigPush
from trustgraph.schema import config_request_queue, config_response_queue
from trustgraph.schema import config_push_queue

from trustgraph.base import AsyncProcessor, Consumer, Producer
from trustgraph.base.cassandra_config import add_cassandra_args, resolve_cassandra_config

from . config import Configuration

from ... base import ProcessorMetrics, ConsumerMetrics, ProducerMetrics
from ... base import Consumer, Producer

# Module logger
logger = logging.getLogger(__name__)

default_ident = "config-svc"

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

        self.config_request_topic = config_request_queue
        self.config_request_subscriber = id

        self.config_request_consumer = Consumer(
            taskgroup = self.taskgroup,
            backend = self.pubsub,
            flow = None,
            topic = config_request_queue,
            subscriber = id,
            schema = ConfigRequest,
            handler = self.on_config_request,
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

        logger.info("Config service initialized")

    async def start(self):

        await self.pubsub.ensure_topic(self.config_request_topic)
        await self.push()  # Startup poke: empty types = everything
        await self.config_request_consumer.start()

    async def push(self, changes=None):

        version = await self.config.get_version()

        resp = ConfigPush(
            version = version,
            changes = changes or {},
        )

        await self.config_push_producer.send(resp)

        logger.info(
            f"Pushed config poke version {version}, "
            f"changes={resp.changes}"
        )
        
    async def on_config_request(self, msg, consumer, flow):

        try:

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            logger.debug(f"Handling config request {id}...")

            resp = await self.config.handle(v)

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

