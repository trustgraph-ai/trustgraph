
from . endpoint import ServiceEndpoint

from . flow_endpoint import FlowEndpoint

class FlowEndpointManager:

    def __init__(self, config_receiver, pulsar_client, auth, timeout=600):

        self.config_receiver = config_receiver
        self.pulsar_client = pulsar_client

        self.services = {
        }

        self.endpoints = [
            FlowEndpoint(
                endpoint_path = "/api/v1/flow/{flow}/{kind}",
                auth = auth,
                requestors = self.services,
            ),
        ]

        self.config_receiver.add_handler(self)

    def add_routes(self, app):
        for ep in self.endpoints:
            ep.add_routes(app)

    async def start(self):
        for ep in self.endpoints:
            await ep.start()

    async def start_flow(self, id, flow):
        print("START FLOW", id)

    async def stop_flow(self, id, flow):
        print("STOP FLOW", id)        

