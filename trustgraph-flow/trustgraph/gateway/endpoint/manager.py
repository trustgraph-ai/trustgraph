
import asyncio

from aiohttp import web

from . constant_endpoint import ConstantEndpoint
from . variable_endpoint import VariableEndpoint
from . socket import SocketEndpoint
from . metrics import MetricsEndpoint

from .. dispatch.manager import DispatcherManager

class EndpointManager:

    def __init__(
            self, dispatcher_manager, auth, prometheus_url, timeout=600
    ):

        self.dispatcher_manager = dispatcher_manager
        self.timeout = timeout

        self.services = {
        }

        self.endpoints = [
            ConstantEndpoint(
                endpoint_path = "/api/v1/librarian", auth = auth,
                dispatcher = dispatcher_manager.dispatch_librarian(),
            ),
            ConstantEndpoint(
                endpoint_path = "/api/v1/config", auth = auth,
                dispatcher = dispatcher_manager.dispatch_config(),
            ),
            ConstantEndpoint(
                endpoint_path = "/api/v1/flow", auth = auth,
                dispatcher = dispatcher_manager.dispatch_flow(),
            ),
            MetricsEndpoint(
                endpoint_path = "/api/v1/metrics",
                prometheus_url = prometheus_url,
                auth = auth,
            ),
            VariableEndpoint(
                endpoint_path = "/api/v1/flow/{flow}/service/{kind}",
                auth = auth,
                dispatcher = dispatcher_manager.dispatch_service(),
            ),
            SocketEndpoint(
                endpoint_path = "/api/v1/flow/{flow}/import/{kind}",
                auth = auth,
                dispatcher = dispatcher_manager.dispatch_import()
            ),
            SocketEndpoint(
                endpoint_path = "/api/v1/flow/{flow}/export/{kind}",
                auth = auth,
                dispatcher = dispatcher_manager.dispatch_export()
            ),
            SocketEndpoint(
                endpoint_path = "/api/v1/flow/{flow}/socket",
                auth = auth,
                dispatcher = dispatcher_manager.dispatch_socket()
            ),
        ]

    def add_routes(self, app):
        for ep in self.endpoints:
            ep.add_routes(app)

    async def start(self):
        for ep in self.endpoints:
            await ep.start()

