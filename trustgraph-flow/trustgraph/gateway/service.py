"""
API gateway.  Offers HTTP services which are translated to interaction on the
Pulsar bus.
"""

import asyncio
import argparse
from aiohttp import web
import logging
import os

from .. log_level import LogLevel

from . auth import Authenticator
from . config.receiver import ConfigReceiver
from . endpoint.globals import GlobalEndpointManager
from . endpoint.flows import FlowEndpointManager

import pulsar
from prometheus_client import start_http_server

logger = logging.getLogger("api")
logger.setLevel(logging.INFO)

default_pulsar_host = os.getenv("PULSAR_HOST", "pulsar://pulsar:6650")
default_prometheus_url = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
default_pulsar_api_key = os.getenv("PULSAR_API_KEY", None)
default_timeout = 600
default_port = 8088
default_api_token = os.getenv("GATEWAY_SECRET", "")

class Api:

    def __init__(self, **config):

        self.port = int(config.get("port", default_port))
        self.timeout = int(config.get("timeout", default_timeout))
        self.pulsar_host = config.get("pulsar_host", default_pulsar_host)
        self.pulsar_api_key = config.get(
            "pulsar_api_key", default_pulsar_api_key
        )

        self.pulsar_listener = config.get("pulsar_listener", None)

        if self.pulsar_api_key:
            self.pulsar_client = pulsar.Client(
                self.pulsar_host, listener_name=self.pulsar_listener,
                authentication=pulsar.AuthenticationToken(self.pulsar_api_key)
            )
        else:
            self.pulsar_client = pulsar.Client(
                self.pulsar_host, listener_name=self.pulsar_listener,
            )

        self.prometheus_url = config.get(
            "prometheus_url", default_prometheus_url,
        )

        if not self.prometheus_url.endswith("/"):
            self.prometheus_url += "/"

        api_token = config.get("api_token", default_api_token)

        # Token not set, or token equal empty string means no auth
        if api_token:
            self.auth = Authenticator(token=api_token)
        else:
            self.auth = Authenticator(allow_all=True)

        self.config_receiver = ConfigReceiver(self.pulsar_client)

        self.global_manager = GlobalEndpointManager(
            pulsar_client = self.pulsar_client,
            auth = self.auth,
            prometheus_url = self.prometheus_url,
            timeout = self.timeout,
        )

        self.flow_manager = FlowEndpointManager(
            config_receiver = self.config_receiver,
            pulsar_client = self.pulsar_client,
            auth = self.auth,
            timeout = self.timeout,
            
        )

        self.endpoints = [
        ]

    async def app_factory(self):
        
        self.app = web.Application(
            middlewares=[],
            client_max_size=256 * 1024 * 1024
        )

        await self.config_receiver.start()


        for ep in self.endpoints:
            ep.add_routes(self.app)

        for ep in self.endpoints:
            await ep.start()

        self.global_manager.add_routes(self.app)
        await self.global_manager.start()

        self.flow_manager.add_routes(self.app)
        await self.flow_manager.start()

        return self.app

    def run(self):
        web.run_app(self.app_factory(), port=self.port)

def run():

    parser = argparse.ArgumentParser(
        prog="api-gateway",
        description=__doc__
    )

    parser.add_argument(
        '-p', '--pulsar-host',
        default=default_pulsar_host,
        help=f'Pulsar host (default: {default_pulsar_host})',
    )
    
    parser.add_argument(
        '--pulsar-api-key',
        default=default_pulsar_api_key,
        help=f'Pulsar API key',
    )

    parser.add_argument(
        '--pulsar-listener',
        help=f'Pulsar listener (default: none)',
    )

    parser.add_argument(
        '-m', '--prometheus-url',
        default=default_prometheus_url,
        help=f'Prometheus URL (default: {default_prometheus_url})',
    )

    parser.add_argument(
        '--port',
        type=int,
        default=default_port,
        help=f'Port number to listen on (default: {default_port})',
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=default_timeout,
        help=f'API request timeout in seconds (default: {default_timeout})',
    )

    parser.add_argument(
        '--api-token',
        default=default_api_token,
        help=f'Secret API token (default: no auth)',
    )

    parser.add_argument(
        '-l', '--log-level',
        type=LogLevel,
        default=LogLevel.INFO,
        choices=list(LogLevel),
        help=f'Output queue (default: info)'
    )

    parser.add_argument(
        '--metrics',
        action=argparse.BooleanOptionalAction,
        default=True,
        help=f'Metrics enabled (default: true)',
    )

    parser.add_argument(
        '-P', '--metrics-port',
        type=int,
        default=8000,
        help=f'Prometheus metrics port (default: 8000)',
    )

    args = parser.parse_args()
    args = vars(args)

    if args["metrics"]:
        start_http_server(args["metrics_port"])

    a = Api(**args)
    a.run()

