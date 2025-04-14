
"""
Config service.  Fetchs an extract from the Wikipedia page
using the API.
"""

from pulsar.schema import JsonSchema
from prometheus_client import Histogram, Counter

from trustgraph.schema import ConfigRequest, ConfigResponse, ConfigPush
from trustgraph.schema import Error
from trustgraph.schema import config_request_queue, config_response_queue
from trustgraph.schema import config_push_queue
from trustgraph.log_level import LogLevel
from trustgraph.base import AsyncProcessor, Consumer, Producer

from . config import Configuration

module = "config-svc"

default_request_queue = config_request_queue
default_response_queue = config_response_queue
default_push_queue = config_push_queue
default_subscriber = module

# This behaves just like a dict, should be easier to add persistent storage
# later

class Processor(AsyncProcessor):

    def __init__(self, **params):
        
        request_queue = params.get("request_queue", default_request_queue)
        response_queue = params.get("response_queue", default_response_queue)
        push_queue = params.get("push_queue", default_push_queue)
        subscriber = params.get("subscriber", default_subscriber)
        id = params.get("id")

        request_schema = ConfigRequest
        response_schema = ConfigResponse
        push_schema = ConfigResponse

        self.set_processor_state(id, "starting")

        self.set_pubsub_info(
            id
            {
                "id": id,
                "subscriber": subscriber,
                "request_queue": request_queue,
                "request_schema": request_schema.__name__,
                "response_queue": response_queue,
                "response_schema": request_schema.__name__,
#                 "rate_limit_retry": str(self.rate_limit_retry),
#                 "rate_limit_timeout": str(self.rate_limit_timeout),
            }
        )

        super(Processor, self).__init__(
            **params | {
                "request_schema": request_schema.__name__,
                "response_schema": response_schema.__name__,
                "push_schema": push_schema.__name__,
            }
        )

        if not hasattr(__class__, "request_metric"):
            __class__.request_metric = Histogram(
                'request_latency', 'Request latency (seconds)'
            )

        if not hasattr(__class__, "processing_metric"):
            __class__.processing_metric = Counter(
                'processing_count', 'Processing count',
                ["status"]
            )

        self.push_pub = self.publish(
            queue = push_queue,
            schema = ConfigPush
        )

        self.out_pub = self.publish(
            queue = response_queue,
            schema = ConfigResponse
        )

        self.subs = self.subscribe(
            queue = request_queue,
            subscriber = subscriber,
            schema = request_schema,
            handler = self.on_message,
        )

        self.config = Configuration()

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

        print("Pushed.")
        
    async def on_message(self, msg, consumer):


        try:

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            print(f"Handling {id}...", flush=True)

            resp = await self.config.handle(v)

            await self.out_pub.send(resp, properties={"id": id})

            consumer.acknowledge(msg)

        except Exception as e:
            
            resp = ConfigResponse(
                error=Error(
                    type = "unexpected-error",
                    message = str(e),
                ),
                text=None,
            )

            await self.out_pub.send(resp, properties={"id": id})

            consumer.acknowledge(msg)

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
            '-P', '--push-queue',
            default=default_push_queue,
            help=f'Config push queue (default: {default_push_queue})'
        )

def run():

    Processor.launch(module, __doc__)

