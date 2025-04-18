
# Base class for processor with management of flows in & out which are managed
# by configuration.  This is probably all processor types, except for the
# configuration service which can't manage itself.

import json

from pulsar.schema import JsonSchema

from .. schema import Error
from .. schema import config_request_queue, config_response_queue
from .. schema import config_push_queue
from .. log_level import LogLevel
from . async_processor import AsyncProcessor
from . subscriber import Subscriber
from . flow import Flow

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

