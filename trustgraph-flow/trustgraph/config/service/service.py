
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

default_input_queue = config_request_queue
default_output_queue = config_response_queue
default_push_queue = config_push_queue
default_subscriber = module

# This behaves just like a dict, should be easier to add persistent storage
# later

class Processor(AsyncProcessor):

    def __init__(self, **params):
        
        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        push_queue = params.get("push_queue", default_push_queue)
        subscriber = params.get("subscriber", default_subscriber)

        input_schema = ConfigRequest
        output_schema = ConfigResponse
        push_schema = ConfigResponse

        self.set_processor_state("FIXME", "starting")

        self.set_pubsub_info(
            "FIXME",
            {
                "input_queue": input_queue,
                "subscriber": subscriber,
                "input_schema": input_schema.__name__,
#                 "rate_limit_retry": str(self.rate_limit_retry),
#                 "rate_limit_timeout": str(self.rate_limit_timeout),
            }
        )

        super(Processor, self).__init__(
            **params | {
                "input_schema": input_schema.__name__,
                "output_schema": output_schema.__name__,
                "push_schema": push_schema.__name__,
            }
        )

        self.subs = self.subscribe(
            queue = input_queue,
            subscriber = subscriber,
            schema = input_schema,
            handler = self.on_message,
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
            queue = output_queue,
            schema = ConfigResponse
        )

        self.config = Configuration()

        # Version counter
        self.version = 0

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
            '-i', '--input-queue',
            default=default_input_queue,
            help=f'Input queue (default: {default_input_queue})'
        )

        parser.add_argument(
            '-q', '--push-queue',
            default=default_push_queue,
            help=f'Config push queue (default: {default_push_queue})'
        )

def run():

    Processor.launch(module, __doc__)

