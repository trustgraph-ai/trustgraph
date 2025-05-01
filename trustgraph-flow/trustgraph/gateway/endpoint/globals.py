
from . endpoint import ServiceEndpoint

from .. dispatch.librarian import LibrarianRequestor
from .. dispatch.config import ConfigRequestor
from .. dispatch.flow import FlowRequestor
from . metrics import MetricsEndpoint

class GlobalEndpointManager:

    def __init__(self, pulsar_client, auth, prometheus_url, timeout=600):

        self.pulsar_client = pulsar_client

        self.services = {
            "librarian": LibrarianRequestor(
                pulsar_client=self.pulsar_client, timeout=timeout,
            ),
            "config": ConfigRequestor(
                pulsar_client=self.pulsar_client, timeout=timeout,
            ),
            "flow": FlowRequestor(
                pulsar_client=self.pulsar_client, timeout=timeout,
            )
        }

        self.endpoints = [
            ServiceEndpoint(
                endpoint_path = "/api/v1/librarian", auth = auth,
                requestor = self.services["librarian"],
            ),
            ServiceEndpoint(
                endpoint_path = "/api/v1/config", auth = auth,
                requestor = self.services["config"],
            ),
            ServiceEndpoint(
                endpoint_path = "/api/v1/flow", auth = auth,
                requestor = self.services["flow"],
            ),
            MetricsEndpoint(
                endpoint_path = "/api/v1/metrics",
                prometheus_url = prometheus_url,
                auth = auth,
            ),
        ]

    def add_routes(self, app):

        for ep in self.endpoints:
            ep.add_routes(app)

    async def start(self):

        for ep in self.endpoints:
            await ep.start()

