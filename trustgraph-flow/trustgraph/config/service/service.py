
"""
Config service.  Manages system global configuration state
"""

from pulsar.schema import JsonSchema

from trustgraph.schema import ConfigRequest, ConfigResponse, ConfigPush
from trustgraph.schema import Error
from trustgraph.schema import config_request_queue, config_response_queue
from trustgraph.schema import config_push_queue
from trustgraph.log_level import LogLevel
from trustgraph.base import AsyncProcessor, Consumer, Producer

from . config import Configuration
from ... base import ProcessorMetrics, ConsumerMetrics, ProducerMetrics
from ... base import Consumer, Producer

default_ident = "config-svc"

default_request_queue = config_request_queue
default_response_queue = config_response_queue
default_push_queue = config_push_queue

class Processor(AsyncProcessor):

    def __init__(self, **params):
        
        request_queue = params.get("request_queue", default_request_queue)
        response_queue = params.get("response_queue", default_response_queue)
        push_queue = params.get("push_queue", default_push_queue)
        id = params.get("id")

        request_schema = ConfigRequest
        response_schema = ConfigResponse
        push_schema = ConfigResponse

        super(Processor, self).__init__(
            **params | {
                "request_schema": request_schema.__name__,
                "response_schema": response_schema.__name__,
                "push_schema": push_schema.__name__,
            }
        )

        request_metrics = ConsumerMetrics(id + "-request")
        response_metrics = ProducerMetrics(id + "-response")
        push_metrics = ProducerMetrics(id + "-push")

        self.push_pub = Producer(
            client = self.client,
            topic = push_queue,
            schema = ConfigPush,
            metrics = push_metrics,
        )

        self.response_pub = Producer(
            client = self.client,
            topic = response_queue,
            schema = ConfigResponse,
            metrics = response_metrics,
        )

        self.subs = Consumer(
            taskgroup = self.taskgroup,
            client = self.client,
            flow = None,
            topic = request_queue,
            subscriber = id,
            schema = request_schema,
            handler = self.on_message,
            metrics = request_metrics,
        )

        self.config = Configuration(self.push)

        print("Service initialised.")

    async def start(self):

        await self.push()
        await self.subs.start()
        
    async def push(self):

        resp = ConfigPush(
            version = self.config.version,
            value = None,
            directory = None,
            values = None,
            config = self.config,
            error = None,
        )

        await self.push_pub.send(resp)

        print("Pushed version ", self.config.version)
        
    async def on_message(self, msg, consumer, flow):

        try:

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            print(f"Handling {id}...", flush=True)

            resp = await self.config.handle(v)

            await self.response_pub.send(resp, properties={"id": id})

        except Exception as e:
            
            resp = ConfigResponse(
                error=Error(
                    type = "unexpected-error",
                    message = str(e),
                ),
                text=None,
            )

            await self.response_pub.send(resp, properties={"id": id})

    @staticmethod
    def add_args(parser):

        AsyncProcessor.add_args(parser)

        parser.add_argument(
            '-q', '--request-queue',
            default=default_request_queue,
            help=f'Request queue (default: {default_request_queue})'
        )

        parser.add_argument(
            '-r', '--response-queue',
            default=default_response_queue,
            help=f'Response queue {default_response_queue}',
        )

        parser.add_argument(
            '--push-queue',
            default=default_push_queue,
            help=f'Config push queue (default: {default_push_queue})'
        )

def run():

    Processor.launch(default_ident, __doc__)

