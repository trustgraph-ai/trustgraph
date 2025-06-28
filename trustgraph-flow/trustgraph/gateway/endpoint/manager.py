
import asyncio

from aiohttp import web

from . stream_endpoint import StreamEndpoint
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
            MetricsEndpoint(
                endpoint_path = "/api/metrics",
                prometheus_url = prometheus_url,
                auth = auth,
            ),
            VariableEndpoint(
                endpoint_path = "/api/v1/{kind}", auth = auth,
                dispatcher = dispatcher_manager.dispatch_global_service(),
            ),
            SocketEndpoint(
                endpoint_path = "/api/v1/socket",
                auth = auth,
                dispatcher = dispatcher_manager.dispatch_socket()
            ),
            VariableEndpoint(
                endpoint_path = "/api/v1/flow/{flow}/service/{kind}",
                auth = auth,
                dispatcher = dispatcher_manager.dispatch_flow_service(),
            ),
            SocketEndpoint(
                endpoint_path = "/api/v1/flow/{flow}/import/{kind}",
                auth = auth,
                dispatcher = dispatcher_manager.dispatch_flow_import()
            ),
            SocketEndpoint(
                endpoint_path = "/api/v1/flow/{flow}/export/{kind}",
                auth = auth,
                dispatcher = dispatcher_manager.dispatch_flow_export()
            ),
            StreamEndpoint(
                endpoint_path = "/api/v1/import-core",
                auth = auth,
                method = "POST",
                dispatcher = dispatcher_manager.dispatch_core_import(),
            ),
            StreamEndpoint(
                endpoint_path = "/api/v1/export-core",
                auth = auth,
                method = "GET",
                dispatcher = dispatcher_manager.dispatch_core_export(),
            ),
        ]

    def add_routes(self, app):
        for ep in self.endpoints:
            ep.add_routes(app)

    async def start(self):
        for ep in self.endpoints:
            await ep.start()

