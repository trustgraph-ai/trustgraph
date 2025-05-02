
import asyncio
import uuid

from . config import ConfigRequestor
from . flow import FlowRequestor
from . librarian import LibrarianRequestor

from . embeddings import EmbeddingsRequestor
from . agent import AgentRequestor
from . text_completion import TextCompletionRequestor
from . prompt import PromptRequestor
from . graph_rag import GraphRagRequestor
from . document_rag import DocumentRagRequestor
from . triples_query import TriplesQueryRequestor
from . embeddings import EmbeddingsRequestor
from . graph_embeddings_query import GraphEmbeddingsQueryRequestor
from . prompt import PromptRequestor

from . triples_stream import TriplesStream
from . graph_embeddings_stream import GraphEmbeddingsStream
from . document_embeddings_stream import DocumentEmbeddingsStream

request_response_dispatchers = {
    "agent": AgentRequestor,
    "text-completion": TextCompletionRequestor,
    "prompt": PromptRequestor,
    "graph-rag": GraphRagRequestor,
    "document-rag": DocumentRagRequestor,
    "embeddings": EmbeddingsRequestor,
    "graph-embeddings": GraphEmbeddingsQueryRequestor,
    "triples-query": TriplesQueryRequestor,
}

receive_dispatchers = {
    "triples": TriplesStream,
    "graph-embeddings": GraphEmbeddingsStream,
    "document-embeddings": DocumentEmbeddingsStream,
}

class DispatcherWrapper:
    def __init__(self, mgr, name, impl):
        self.mgr = mgr
        self.name = name
        self.impl = impl
    async def process(self, data, responder):
        return await self.mgr.process_impl(
            data, responder, self.name, self.impl
        )

class DispatcherManager:

    def __init__(self, pulsar_client, config_receiver):
        self.pulsar_client = pulsar_client
        self.config_receiver = config_receiver
        self.config_receiver.add_handler(self)

        self.flows = {}
        self.dispatchers = {}

    async def start_flow(self, id, flow):
        print("Start flow", id)
        self.flows[id] = flow
        return

    async def stop_flow(self, id, flow):
        print("Stop flow", id)
        del self.flows[id]
        return

    def dispatch_config(self):
        return DispatcherWrapper(self, "config", ConfigRequestor)

    def dispatch_flow(self):
        return DispatcherWrapper(self, "flow", FlowRequestor)

    def dispatch_librarian(self):
        return DispatcherWrapper(self, "librarian", LibrarianRequestor)

    async def process_impl(self, data, responder, name, impl):

        key = (None, name)

        if key in self.dispatchers:
            return await self.dispatchers[key].process(data, responder)

        dispatcher = impl(
            pulsar_client = self.pulsar_client
        )

        await dispatcher.start()

        self.dispatchers[key] = dispatcher

        return await dispatcher.process(data, responder)

    def dispatch_flow_service(self):
        return self

    def dispatch_flow_receive(self):
        return self.dispatch_receive

    async def dispatch_receive(self, ws, running, params):

        flow = params.get("flow")
        kind = params.get("kind")

        if flow not in self.flows:
            raise RuntimeError("Invalid flow")

        if kind not in receive_dispatchers:
            raise RuntimeError("Invalid kind")

        key = (flow, kind)

        intf_defs = self.flows[flow]["interfaces"]

        if kind not in intf_defs:
            raise RuntimeError("This kind not supported by flow")

        # FIXME: The -store bit, does it make sense?
        qconfig = intf_defs[kind + "-store"]

        id = str(uuid.uuid4())
        dispatcher = receive_dispatchers[kind](
            pulsar_client = self.pulsar_client,
            ws = ws,
            running = running,
            queue = qconfig,
            consumer = f"api-gateway-{id}",
            subscriber = f"api-gateway-{id}",
        )

        return dispatcher

    async def process(self, data, responder, params):

        flow = params.get("flow")
        kind = params.get("kind")

        if flow not in self.flows:
            raise RuntimeError("Invalid flow")

        if kind not in request_response_dispatchers:
            raise RuntimeError("Invalid kind")

        key = (flow, kind)

        if key in self.dispatchers:
            return await self.dispatchers[key].process(data, responder)

        intf_defs = self.flows[flow]["interfaces"]

        if kind not in intf_defs:
            raise RuntimeError("This kind not supported by flow")

        qconfig = intf_defs[kind]

        dispatcher = request_response_dispatchers[kind](
            pulsar_client = self.pulsar_client,
            request_queue = qconfig["request"],
            response_queue = qconfig["response"],
            timeout = 120,
            consumer = f"api-gateway-{flow}-{kind}-request",
            subscriber = f"api-gateway-{flow}-{kind}-request",
        )

        await dispatcher.start()

        self.dispatchers[key] = dispatcher

        return await dispatcher.process(data, responder)

