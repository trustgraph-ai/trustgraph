
import asyncio

from . endpoint import ServiceEndpoint

from . flow_endpoint import FlowEndpoint

from .. dispatch.agent import AgentRequestor
from .. dispatch.text_completion import TextCompletionRequestor
from .. dispatch.prompt import PromptRequestor
from .. dispatch.graph_rag import GraphRagRequestor
from .. dispatch.document_rag import DocumentRagRequestor
from .. dispatch.triples_query import TriplesQueryRequestor
from .. dispatch.embeddings import EmbeddingsRequestor
from .. dispatch.graph_embeddings_query import GraphEmbeddingsQueryRequestor
from .. dispatch.prompt import PromptRequestor
from . stream import StreamEndpoint

class FlowEndpointManager:

    def __init__(self, config_receiver, pulsar_client, auth, timeout=600):

        self.config_receiver = config_receiver
        self.pulsar_client = pulsar_client
        self.timeout = timeout

        self.services = {
        }

        class DispInst:
            def __init__(self, ws, running):
                self.ws = ws
                self.running = running
                self.num = 1
            async def destroy(self):
                print("Destroy..")
                await self.ws.close()
                self.running.stop()
            async def run(self):
                while self.running.get():
                    await asyncio.sleep(1)
                    await self.ws.send_json({"number": self.num})
                    self.num += 1
                    print("Tick")
            async def receive(self, msg):
                print("Message...")
                print(msg.data)

        class Dispatcher:
            def __init__(self):
                pass
            async def create(self, ws, running, request):
                print("Create")
                return DispInst(ws, running)
        
        self.endpoints = [
            FlowEndpoint(
                endpoint_path = "/api/v1/flow/{flow}/{kind}",
                auth = auth,
                requestors = self.services,
            ),
            StreamEndpoint(
                endpoint_path = "/api/v1/flow/{flow}/stream/{kind}",
                auth = auth,
                dispatcher = Dispatcher(),
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
#            "triples-store"
#            "bunch": 
        }

        for api_kind, streamer in kinds.items():

#            if api_kind in intf:
            if True:

                k = (id, api_kind)
                if k in self.services:
                    await self.services[k].stop()
                    del self.services[k]

                self.services[k] = streamer(
#                    pulsar_client=self.pulsar_client,
#                    timeout = self.timeout,
#                    input_queue = intf[api_kind],
#                    consumer = f"api-gateway-{id}-{api_kind}-stream",
#                    subscriber = f"api-gateway-{id}-{api_kind}-stream",
                )
                await self.services[k].start()

    async def stop_flow(self, id, flow):

        print("STOP FLOW", id)        

        svc_list = list(self.services.keys())

        for k in svc_list:

            kid, kkind = k

            if id == kid:
                await self.services[k].stop()
                del self.services[k]
