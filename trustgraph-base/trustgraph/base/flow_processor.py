
# Base class for processor with management of flows in & out which are managed
# by configuration.  This is probably all processor types, except for the
# configuration service which can't manage itself.

import json

from pulsar.schema import JsonSchema

from .. schema import Error
from .. schema import config_request_queue, config_response_queue
from .. schema import config_push_queue
from .. log_level import LogLevel
from .. base import AsyncProcessor, Consumer, Producer, Subscriber
from . metrics import ConsumerMetrics, ProducerMetrics

class Spec:
    pass

class SubscriberSpec(Spec):
    def __init__(self, name, schema):
        self.name = name
        self.schema = schema

    def add(self, flow, processor, definition):

        subscriber_metrics = ConsumerMetrics(
            flow.id, f"{flow.name}-{self.name}"
        )

        subscriber = Subscriber(
            pulsar_client = processor.client.client,
            topic = definition[self.name],
            subscription = flow.id,
            consumer_name = flow.id,
            schema = self.schema,
        )

        # Put it in the consumer map, does that work?
        # It means it gets start/stop call.
        flow.consumer[self.name] = subscriber

        if not hasattr(flow, self.name):
            setattr(flow, self.name, subscriber)

class ConsumerSpec(Spec):
    def __init__(self, name, schema, handler):
        self.name = name
        self.schema = schema
        self.handler = handler

    def add(self, flow, processor, definition):

        consumer_metrics = ConsumerMetrics(
            flow.id, f"{flow.name}-{self.name}"
        )

        consumer = processor.subscribe(
            flow = flow,
            queue = definition[self.name],
            subscriber = flow.id,
            schema = self.schema,
            handler = self.handler,
            metrics = consumer_metrics,
        )

        # Consumer handle gets access to producers and other
        # metadata
        consumer.id = flow.id
        consumer.name = self.name
        consumer.flow = flow

        flow.consumer[self.name] = consumer

        if not hasattr(flow, self.name):
            setattr(flow, self.name, consumer)

class ProducerSpec(Spec):
    def __init__(self, name, schema):
        self.name = name
        self.schema = schema

    def add(self, flow, processor, definition):

        producer_metrics = ProducerMetrics(
            flow.id, f"{flow.name}-{self.name}"
        )

        producer = processor.publish(
            queue = definition[self.name],
            schema = self.schema,
            metrics = producer_metrics,
        )

        flow.producer[self.name] = producer

        if not hasattr(self, self.name):
            setattr(flow, self.name, producer)

class SettingSpec(Spec):
    def __init__(self, name):
        self.name = name

    def add(self, flow, processor, definition):

        flow.config[self.name] = definition[self.name]

        if not hasattr(flow, self.name):
            setattr(flow, self.name, definition[self.name])

class Flow:
    def __init__(self, id, flow, processor, defn):

        self.id = id
        self.name = flow

        self.producer = {}
        self.consumer = {}
        self.setting = {}

        for spec in processor.specifications:
            spec.add(self, processor, defn)

    async def start(self):
        for c in self.consumer.values():
            await c.start()

    async def stop(self):
        for c in self.consumer.values():
            await c.stop()
                
# Parent class for configurable processors, configured with flows by
# the config service
class FlowProcessor(AsyncProcessor):

    def __init__(self, **params):

        # Initialise base class
        super(FlowProcessor, self).__init__(**params)

        # Register configuration handler
        self.register_config_handler(self.on_configuration)

        # Initialise flow information state
        self.flows = {}

        # These can be overriden by a derived class:

        # Array of specifications: ConsumerSpec, ProducerSpec, SettingSpec
        self.specifications = []

        print("Service initialised.")

    # Register a new consumer name
    def register_consumer(self, name, schema, handler):
        self.specifications.append(ConsumerSpec(name, schema, handler))

    # Register a producer name
    def register_producer(self, name, schema):
        self.specifications.append(ProducerSpec(name, schema))

    # Register a configuration variable
    def register_config(self, name):
        self.specifications.append(SettingSpec(name))

    # Register a configuration variable
    def register_specification(self, spec):
        self.specifications.append(spec)

    # Start processing for a new flow
    async def start_flow(self, flow, defn):
        self.flows[flow] = Flow(self.id, flow, self, defn)
        await self.flows[flow].start()
        print("Started flow: ", flow)
        
    # Stop processing for a new flow
    async def stop_flow(self, flow):
        if flow in self.flows:
            await self.flows[flow].stop()
            del self.flows[flow]
            print("Stopped flow: ", flow, flush=True)

    # Event handler - called for a configuration change
    async def on_configuration(self, config, version):

        print("Got config version", version, flush=True)

        # Skip over invalid data
        if "flows" not in config: return

        # Check there's configuration information for me
        if self.id in config["flows"]:

            # Get my flow config
            flow_config = json.loads(config["flows"][self.id])

            # Get list of flows which should be running and are currently
            # running
            wanted_flows = flow_config.keys()
            current_flows = self.flows.keys()

            # Start all the flows which arent currently running
            for flow in wanted_flows:
                if flow not in current_flows:
                    await self.start_flow(flow, flow_config[flow])

            # Stop all the unwanted flows which are due to be stopped
            for flow in current_flows:
                if flow not in wanted_flows:
                    await self.stop_flow(flow)

            print("Handled config update")

        else:

            print("No configuration settings for me!", flush=True)

    # Start threads, just call parent
    async def start(self):
        await super(FlowProcessor, self).start()

    @staticmethod
    def add_args(parser):

        AsyncProcessor.add_args(parser)

        # parser.add_argument(
        #     '--rate-limit-retry',
        #     type=int,
        #     default=default_rate_limit_retry,
        #     help=f'Rate limit retry (default: {default_rate_limit_retry})'
        # )

        # parser.add_argument(
        #     '--rate-limit-timeout',
        #     type=int,
        #     default=default_rate_limit_timeout,
        #     help=f'Rate limit timeout (default: {default_rate_limit_timeout})'
        # )

def run():

    Processor.launch(module, __doc__)

