
import asyncio

from aiohttp import web

#from . endpoint import ServiceEndpoint

from . constant_endpoint import ConstantEndpoint
from . variable_endpoint import VariableEndpoint
from . socket import SocketEndpoint

from .. dispatch.manager import DispatcherManager

class FlowEndpointManager:

    def __init__(self, dispatcher_manager, auth, timeout=600):

        self.dispatcher_manager = dispatcher_manager
        self.timeout = timeout

        self.services = {
        }

        self.endpoints = [
            ConstantEndpoint(
                endpoint_path = "/api/v1/test",
                auth = auth,
                dispatcher = dispatcher_manager.dispatch_test_service(),
            ),
            VariableEndpoint(
                endpoint_path = "/api/v1/flow/{flow}/{kind}",
                auth = auth,
                dispatcher = dispatcher_manager.dispatch_flow_service(),
            ),
            SocketEndpoint(
                endpoint_path = "/api/v1/test2",
                auth = auth,
                dispatcher = dispatcher_manager.dispatch_socket_service()
            ),
        ]

    def add_routes(self, app):
        for ep in self.endpoints:
            ep.add_routes(app)

    async def start(self):
        for ep in self.endpoints:
            await ep.start()

    async def start_flow(self, id, flow):

        print("START FLOW", id)

        return

        intf = flow["interfaces"]

        kinds = {
            "agent": AgentRequestor,
            "text-completion": TextCompletionRequestor,
            "prompt": PromptRequestor,
            "graph-rag": GraphRagRequestor,
            "document-rag": DocumentRagRequestor,
            "embeddings": EmbeddingsRequestor,
            "graph-embeddings": GraphEmbeddingsQueryRequestor,
            "triples-query": TriplesQueryRequestor,
        }

        for api_kind, requestor in kinds.items():

            if api_kind in intf:

                k = (id, api_kind)
                if k in self.services:
                    await self.services[k].stop()
                    del self.services[k]


                self.services[k] = requestor(
                    pulsar_client=self.pulsar_client, timeout = self.timeout,
                    request_queue = intf[api_kind]["request"],
                    response_queue = intf[api_kind]["response"],
                    consumer = f"api-gateway-{id}-{api_kind}-request",
                    subscriber = f"api-gateway-{id}-{api_kind}-request",
                )
                await self.services[k].start()

        kinds = {
#            "document-embeddings-stream": DocumentEmbeddingsStreamEndpoint,
            "triples-stream": TriplesStream,
#            "bunch": 
        }

        for api_kind, streamer in kinds.items():

#            if api_kind in intf:
            if True:

                k = (id, api_kind)
                if k in self.services:
                    await self.services[k].stop()
                    del self.services[k]

                self.services[k] = Dispatcher(
                    pulsar_client=self.pulsar_client,
                    timeout = self.timeout,
                    input_queue = intf[api_kind],
                    consumer = f"api-gateway-{id}-{api_kind}-stream",
                    subscriber = f"api-gateway-{id}-{api_kind}-stream",
                    impl=streamer,
                )
                await self.services[k].start()

    async def stop_flow(self, id, flow):

        print("STOP FLOW", id)

        return

        svc_list = list(self.services.keys())

        for k in svc_list:

            kid, kkind = k

            if id == kid:
                await self.services[k].stop()
                del self.services[k]
