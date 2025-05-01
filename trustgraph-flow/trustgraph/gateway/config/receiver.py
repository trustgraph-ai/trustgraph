"""
API gateway.  Offers HTTP services which are translated to interaction on the
Pulsar bus.
"""

module = "api-gateway"

# FIXME: Subscribes to Pulsar unnecessarily, should only do it when there
# are active listeners

# FIXME: Connection errors in publishers / subscribers cause those threads
# to fail and are not failed or retried

import asyncio
import argparse
from aiohttp import web
import logging
import os
import base64
import uuid
import json

import pulsar
from prometheus_client import start_http_server

from ... schema import ConfigPush, config_push_queue
from ... base import Consumer

logger = logging.getLogger("config.receiver")
logger.setLevel(logging.INFO)

class ConfigReceiver:

    def __init__(self, pulsar_client):

        self.pulsar_client = pulsar_client

        self.flow_handlers = []

        self.flows = {}

    def add_handler(self, h):
        self.flow_handlers.append(h)

    async def on_config(self, msg, proc, flow):

        try:

            v = msg.value()

            print(f"Config version", v.version)

            if "flows" in v.config:

                flows = v.config["flows"]

                wanted = list(flows.keys())
                current = list(self.flows.keys())

                for k in wanted:
                    if k not in current:
                        self.flows[k] = json.loads(flows[k])
                        await self.start_flow(k, self.flows[k])

                for k in current:
                    if k not in wanted:
                        await self.stop_flow(k, self.flows[k])
                        del self.flows[k]

        except Exception as e:
            print(f"Exception: {e}", flush=True)

    async def start_flow(self, id, flow):

        print("Start flow", id)

        for handler in self.flow_handlers:

            try:
                await handler.start_flow(id, flow)
            except Exception as e:
                print(f"Exception: {e}", flush=True)

    async def stop_flow(self, id, flow):

        print("Stop flow", id)

        for handler in self.flow_handlers:

            try:
                await handler.stop_flow(id, flow)
            except Exception as e:
                print(f"Exception: {e}", flush=True)

    async def config_loader(self):

        async with asyncio.TaskGroup() as tg:

            id = str(uuid.uuid4())

            self.config_cons = Consumer(
                taskgroup = tg,
                flow = None,
                client = self.pulsar_client,
                subscriber = f"gateway-{id}",                
                topic = config_push_queue,
                schema = ConfigPush,
                handler = self.on_config,
                start_of_messages = True,
            )

            await self.config_cons.start()

            print("Waiting...")

        print("Config consumer done. :/")

    async def start(self):
        
        asyncio.create_task(self.config_loader())

