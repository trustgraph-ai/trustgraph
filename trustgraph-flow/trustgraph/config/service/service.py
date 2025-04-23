
"""
Config service.  Manages system global configuration state
"""

from pulsar.schema import JsonSchema

from trustgraph.schema import Error

from trustgraph.schema import ConfigRequest, ConfigResponse, ConfigPush
from trustgraph.schema import config_request_queue, config_response_queue
from trustgraph.schema import config_push_queue

from trustgraph.schema import FlowRequest, FlowResponse
from trustgraph.schema import flow_request_queue, flow_response_queue

from trustgraph.log_level import LogLevel
from trustgraph.base import AsyncProcessor, Consumer, Producer

from . config import Configuration
from . flow import FlowConfig

from ... base import ProcessorMetrics, ConsumerMetrics, ProducerMetrics
from ... base import Consumer, Producer

default_ident = "config-svc"

default_config_request_queue = config_request_queue
default_config_response_queue = config_response_queue
default_config_push_queue = config_push_queue

default_flow_request_queue = flow_request_queue
default_flow_response_queue = flow_response_queue

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

        flow_request_queue = params.get(
            "flow_request_queue", default_flow_request_queue
        )
        flow_response_queue = params.get(
            "flow_response_queue", default_flow_response_queue
        )

        id = params.get("id")

        flow_request_schema = FlowRequest
        flow_response_schema = FlowResponse

        super(Processor, self).__init__(
            **params | {
                "config_request_schema": ConfigRequest.__name__,
                "config_response_schema": ConfigResponse.__name__,
                "config_push_schema": ConfigPush.__name__,
                "flow_request_schema": FlowRequest.__name__,
                "flow_response_schema": FlowResponse.__name__,
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

        flow_request_metrics = ConsumerMetrics(
            processor = self.id, flow = None, name = "flow-request"
        )
        flow_response_metrics = ProducerMetrics(
            processor = self.id, flow = None, name = "flow-response"
        )

        self.config_request_consumer = Consumer(
            taskgroup = self.taskgroup,
            client = self.pulsar_client,
            flow = None,
            topic = config_request_queue,
            subscriber = id,
            schema = ConfigRequest,
            handler = self.on_config_request,
            metrics = config_request_metrics,
        )

        self.config_response_producer = Producer(
            client = self.pulsar_client,
            topic = config_response_queue,
            schema = ConfigResponse,
            metrics = config_response_metrics,
        )

        self.config_push_producer = Producer(
            client = self.pulsar_client,
            topic = config_push_queue,
            schema = ConfigPush,
            metrics = config_push_metrics,
        )

        self.flow_request_consumer = Consumer(
            taskgroup = self.taskgroup,
            client = self.pulsar_client,
            flow = None,
            topic = flow_request_queue,
            subscriber = id,
            schema = FlowRequest,
            handler = self.on_flow_request,
            metrics = flow_request_metrics,
        )

        self.flow_response_producer = Producer(
            client = self.pulsar_client,
            topic = flow_response_queue,
            schema = FlowResponse,
            metrics = flow_response_metrics,
        )

        self.config = Configuration(self.push)
        self.flow = FlowConfig(self.config)

        print("Service initialised.")

    async def start(self):

        await self.push()
        await self.config_request_consumer.start()
        await self.flow_request_consumer.start()
        
    async def push(self):

        resp = ConfigPush(
            version = self.config.version,
            value = None,
            directory = None,
            values = None,
            config = self.config,
            error = None,
        )

        await self.config_push_producer.send(resp)

        print("Pushed version ", self.config.version)
        
    async def on_config_request(self, msg, consumer, flow):

        try:

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            print(f"Handling {id}...", flush=True)

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
                text=None,
            )

            await self.config_response_producer.send(
                resp, properties={"id": id}
            )

    async def on_flow_request(self, msg, consumer, flow):

        try:

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            print(f"Handling {id}...", flush=True)

            resp = await self.flow.handle(v)

            await self.flow_response_producer.send(
                resp, properties={"id": id}
            )

        except Exception as e:
            
            resp = FlowResponse(
                error=Error(
                    type = "flow-error",
                    message = str(e),
                ),
                text=None,
            )

            await self.flow_response_producer.send(
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

        parser.add_argument(
            '--push-queue',
            default=default_config_push_queue,
            help=f'Config push queue (default: {default_config_push_queue})'
        )

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

