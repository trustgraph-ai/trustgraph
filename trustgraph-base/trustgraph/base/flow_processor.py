
# Base class for processor with management of flows in & out which are managed
# by configuration.  This is probably all processor types, except for the
# configuration service which can't manage itself.

import json

from pulsar.schema import JsonSchema

from .. schema import Error
from .. schema import config_request_queue, config_response_queue
from .. schema import config_push_queue
from .. log_level import LogLevel
from .. base import AsyncProcessor, Consumer, Producer

from .. base import ProcessorMetrics, ConsumerMetrics, ProducerMetrics

class Flow:
    pass

# Parent class for configurable processors, configured with flows by
# the config service
class FlowProcessor(AsyncProcessor):

    def __init__(self, **params):

        # Initialise base class
        super(FlowProcessor, self).__init__(**params)

        # Initialise metrics, records the parameters
        ProcessorMetrics(id=self.id).info(params)

        # Register configuration handler
        self.register_config_handler(self.on_configuration)

        # Initialise flow information state
        self.flows = {}

        # These can be overriden by a derived class:

        # Consumer specification, array of ("name", SchemaType, handler)
        self.consumer_spec = []

        # Producer specification, array of ("name", SchemaType)
        self.producer_spec = []

        # Configuration specification, collects some flow variables from
        # config, array of "name"
        self.config_spec = []

        print("Service initialised.")

    # Register a new consumer name
    def register_consumer(self, name, schema, handler):
        self.consumer_spec.append((name, schema, handler))

    # Register a producer name
    def register_producer(self, name, schema):
        self.producer_spec.append((name, schema))

    # Register a configuration variable
    def register_config(self, name):
        self.config_spec.append(name)

    # Start processing for a new flow
    async def start_flow(self, flow, defn):

        flow_obj = Flow()
        flow_obj.producer = {}
        flow_obj.consumer = {}
        flow_obj.config = {}

        for spec in self.config_spec:
            name = spec[0]
            flow_obj.config[name] = defn[name]

            setattr(flow_obj, name, defn[name])

        for spec in self.producer_spec:

            name, schema = spec

            producer_metrics = ProducerMetrics(
                self.id, f"{flow}-{name}"
            )

            producer = self.publish(
                queue = defn[name],
                schema = schema,
                metrics = producer_metrics,
            )

            flow_obj.producer[name] = producer

            setattr(flow_obj, name, producer)

        for spec in self.consumer_spec:

            name, schema, handler = spec

            consumer_metrics = ConsumerMetrics(
                self.id, f"{flow}-{name}"
            )

            consumer = self.subscribe(
                flow = flow_obj,
                queue = defn[name],
                subscriber = self.subscriber,
                schema = schema,
                handler = handler,
                metrics = consumer_metrics,
            )

            # Consumer handle gets access to producers and other
            # metadata
            consumer.id = self.id
            consumer.name = name
            consumer.flow = flow_obj
            consumer.flow.name = flow

            await consumer.start()

            flow_obj.consumer[name] = consumer

            setattr(flow_obj, name, consumer)

        self.flows[flow] = flow_obj
            
        print("Started flow: ", flow)

    # Stop processing for a new flow
    async def stop_flow(self, flow):

        for c in self.flows[flow].consumer:
            await c.stop()

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

