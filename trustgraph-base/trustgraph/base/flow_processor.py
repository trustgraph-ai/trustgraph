from __future__ import annotations

from typing import Any
from argparse import ArgumentParser

# Base class for processor with management of flows in & out which are managed
# by configuration.  This is probably all processor types, except for the
# configuration service which can't manage itself.

import json
import logging

from .. schema import Error
from .. schema import config_request_queue, config_response_queue
from .. schema import config_push_queue
from .. log_level import LogLevel
from . workspace_processor import WorkspaceProcessor
from . flow import Flow

# Module logger
logger = logging.getLogger(__name__)

# Parent class for configurable processors, configured with flows by
# the config service
class FlowProcessor(WorkspaceProcessor):

    def __init__(self, **params):

        # Initialise base class
        super(FlowProcessor, self).__init__(**params)

        # Register configuration handler for this processor's config type
        self.register_config_handler(
            self.on_configure_flows, types=[f"processor:{self.id}"]
        )

        # Initialise flow information state
        # Keyed by (workspace, flow) tuples; each workspace has its own
        # set of flow variants for this processor.
        self.flows = {}

        # These can be overriden by a derived class:

        # Array of specifications: ConsumerSpec, ProducerSpec, ParameterSpec
        self.specifications = []

        logger.info("Service initialised.")

    # Register a configuration variable
    def register_specification(self, spec: Any) -> None:
        self.specifications.append(spec)

    # Start processing for a new flow within a workspace
    async def start_flow(self, workspace, flow, defn):
        key = (workspace, flow)
        self.flows[key] = Flow(self.id, flow, workspace, self, defn)
        await self.flows[key].start()
        logger.info(f"Started flow: {workspace}/{flow}")

    # Stop processing for a flow within a workspace
    async def stop_flow(self, workspace, flow):
        key = (workspace, flow)
        if key in self.flows:
            await self.flows[key].stop()
            del self.flows[key]
            logger.info(f"Stopped flow: {workspace}/{flow}")

    # Event handler - called for a configuration change for a single
    # workspace
    async def on_configure_flows(self, workspace, config, version):

        logger.info(
            f"Got config version {version} for workspace {workspace}"
        )

        config_type = f"processor:{self.id}"

        # Get my flow config — each key is a variant, each value is
        # the JSON config for that flow variant
        if config_type in config:
            flow_config = {
                k: json.loads(v)
                for k, v in config[config_type].items()
            }
        else:
            logger.debug(
                f"No configuration settings for me in {workspace}."
            )
            flow_config = {}

        # Get list of flows which should be running in this workspace,
        # and the list currently running in this workspace
        wanted_flows = set(flow_config.keys())
        current_flows = {
            f for (ws, f) in self.flows.keys() if ws == workspace
        }

        # Start all the flows which aren't currently running in this
        # workspace
        for flow in wanted_flows - current_flows:
            await self.start_flow(workspace, flow, flow_config[flow])

        # Stop all the unwanted flows in this workspace
        for flow in current_flows - wanted_flows:
            await self.stop_flow(workspace, flow)

        logger.info(f"Handled config update for workspace {workspace}")

    # Start threads, just call parent
    async def start(self):
        await super(FlowProcessor, self).start()

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:

        WorkspaceProcessor.add_args(parser)

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


