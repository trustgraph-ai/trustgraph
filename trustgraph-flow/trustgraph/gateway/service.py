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
from . dispatch.manager import DispatcherManager

from . endpoint.manager import EndpointManager

import pulsar
from prometheus_client import start_http_server

# Import default queue names
from .. schema import (
    config_request_queue, config_response_queue,
    flow_request_queue, flow_response_queue,
    knowledge_request_queue, knowledge_response_queue,
    librarian_request_queue, librarian_response_queue,
)

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

        # Build queue overrides dictionary from CLI arguments
        queue_overrides = {}

        # Config service
        config_req = config.get("config_request_queue")
        config_resp = config.get("config_response_queue")
        if config_req or config_resp:
            queue_overrides["config"] = {}
            if config_req:
                queue_overrides["config"]["request"] = config_req
            if config_resp:
                queue_overrides["config"]["response"] = config_resp

        # Flow service
        flow_req = config.get("flow_request_queue")
        flow_resp = config.get("flow_response_queue")
        if flow_req or flow_resp:
            queue_overrides["flow"] = {}
            if flow_req:
                queue_overrides["flow"]["request"] = flow_req
            if flow_resp:
                queue_overrides["flow"]["response"] = flow_resp

        # Knowledge service
        knowledge_req = config.get("knowledge_request_queue")
        knowledge_resp = config.get("knowledge_response_queue")
        if knowledge_req or knowledge_resp:
            queue_overrides["knowledge"] = {}
            if knowledge_req:
                queue_overrides["knowledge"]["request"] = knowledge_req
            if knowledge_resp:
                queue_overrides["knowledge"]["response"] = knowledge_resp

        # Librarian service
        librarian_req = config.get("librarian_request_queue")
        librarian_resp = config.get("librarian_response_queue")
        if librarian_req or librarian_resp:
            queue_overrides["librarian"] = {}
            if librarian_req:
                queue_overrides["librarian"]["request"] = librarian_req
            if librarian_resp:
                queue_overrides["librarian"]["response"] = librarian_resp

        self.dispatcher_manager = DispatcherManager(
            pulsar_client = self.pulsar_client,
            config_receiver = self.config_receiver,
            prefix = "gateway",
            queue_overrides = queue_overrides,
        )

        self.endpoint_manager = EndpointManager(
            dispatcher_manager = self.dispatcher_manager,
            auth = self.auth,
            prometheus_url = self.prometheus_url,
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

        self.endpoint_manager.add_routes(self.app)
        await self.endpoint_manager.start()

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
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help=f'Log level (default: INFO)'
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

    # Queue override arguments for multi-tenant deployments
    parser.add_argument(
        '--config-request-queue',
        default=None,
        help=f'Config service request queue (default: {config_request_queue})',
    )

    parser.add_argument(
        '--config-response-queue',
        default=None,
        help=f'Config service response queue (default: {config_response_queue})',
    )

    parser.add_argument(
        '--flow-request-queue',
        default=None,
        help=f'Flow service request queue (default: {flow_request_queue})',
    )

    parser.add_argument(
        '--flow-response-queue',
        default=None,
        help=f'Flow service response queue (default: {flow_response_queue})',
    )

    parser.add_argument(
        '--knowledge-request-queue',
        default=None,
        help=f'Knowledge service request queue (default: {knowledge_request_queue})',
    )

    parser.add_argument(
        '--knowledge-response-queue',
        default=None,
        help=f'Knowledge service response queue (default: {knowledge_response_queue})',
    )

    parser.add_argument(
        '--librarian-request-queue',
        default=None,
        help=f'Librarian service request queue (default: {librarian_request_queue})',
    )

    parser.add_argument(
        '--librarian-response-queue',
        default=None,
        help=f'Librarian service response queue (default: {librarian_response_queue})',
    )

    args = parser.parse_args()
    args = vars(args)

    if args["metrics"]:
        start_http_server(args["metrics_port"])

    a = Api(**args)
    a.run()

