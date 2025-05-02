
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
from . text_load import TextLoad
from . document_load import DocumentLoad

from . triples_export import TriplesExport
from . graph_embeddings_export import GraphEmbeddingsExport
from . document_embeddings_export import DocumentEmbeddingsExport

from . triples_import import TriplesImport
from . graph_embeddings_import import GraphEmbeddingsImport
from . document_embeddings_import import DocumentEmbeddingsImport

from . mux import Mux

request_response_dispatchers = {
    "agent": AgentRequestor,
    "text-completion": TextCompletionRequestor,
    "prompt": PromptRequestor,
    "graph-rag": GraphRagRequestor,
    "document-rag": DocumentRagRequestor,
    "embeddings": EmbeddingsRequestor,
    "graph-embeddings": GraphEmbeddingsQueryRequestor,
    "triples": TriplesQueryRequestor,
}

global_dispatchers = {
    "config": ConfigRequestor,
    "flow": FlowRequestor,
    "librarian": LibrarianRequestor,
}

sender_dispatchers = {
    "text-load": TextLoad,
    "document-load": DocumentLoad,
}

export_dispatchers = {
    "triples": TriplesExport,
    "graph-embeddings": GraphEmbeddingsExport,
    "document-embeddings": DocumentEmbeddingsExport,
}

import_dispatchers = {
    "triples": TriplesImport,
    "graph-embeddings": GraphEmbeddingsImport,
    "document-embeddings": DocumentEmbeddingsImport,
}

class DispatcherWrapper:
    def __init__(self, handler):
        self.handler = handler
    async def process(self, *args):
        return await self.handler(*args)

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

    def dispatch_global_service(self):
        return DispatcherWrapper(self.process_global_service)

    async def process_global_service(self, data, responder, params):

        kind = params.get("kind")
        return await self.invoke_global_service(data, responder, kind)

    async def invoke_global_service(self, data, responder, kind):

        key = (None, kind)

        if key in self.dispatchers:
            return await self.dispatchers[key].process(data, responder)

        dispatcher = global_dispatchers[kind](
            pulsar_client = self.pulsar_client,
            timeout = 120,
            consumer = f"api-gateway-{kind}-request",
            subscriber = f"api-gateway-{kind}-request",
        )

        await dispatcher.start()

        self.dispatchers[key] = dispatcher

        return await dispatcher.process(data, responder)

    def dispatch_flow_import(self):
        return self.process_flow_import

    def dispatch_flow_export(self):
        return self.process_flow_export

    def dispatch_socket(self):
        return self.process_socket

    def dispatch_flow_service(self):
        return DispatcherWrapper(self.process_flow_service)

    async def process_flow_import(self, ws, running, params):

        flow = params.get("flow")
        kind = params.get("kind")

        if flow not in self.flows:
            raise RuntimeError("Invalid flow")

        if kind not in import_dispatchers:
            raise RuntimeError("Invalid kind")

        key = (flow, kind)

        intf_defs = self.flows[flow]["interfaces"]

        if kind not in intf_defs:
            raise RuntimeError("This kind not supported by flow")

        # FIXME: The -store bit, does it make sense?
        qconfig = intf_defs[kind + "-store"]

        id = str(uuid.uuid4())
        dispatcher = import_dispatchers[kind](
            pulsar_client = self.pulsar_client,
            ws = ws,
            running = running,
            queue = qconfig,
        )

        return dispatcher

    async def process_flow_export(self, ws, running, params):

        flow = params.get("flow")
        kind = params.get("kind")

        if flow not in self.flows:
            raise RuntimeError("Invalid flow")

        if kind not in export_dispatchers:
            raise RuntimeError("Invalid kind")

        key = (flow, kind)

        intf_defs = self.flows[flow]["interfaces"]

        if kind not in intf_defs:
            raise RuntimeError("This kind not supported by flow")

        # FIXME: The -store bit, does it make sense?
        qconfig = intf_defs[kind + "-store"]

        id = str(uuid.uuid4())
        dispatcher = export_dispatchers[kind](
            pulsar_client = self.pulsar_client,
            ws = ws,
            running = running,
            queue = qconfig,
            consumer = f"api-gateway-{id}",
            subscriber = f"api-gateway-{id}",
        )

        return dispatcher

    async def process_socket(self, ws, running, params):

        dispatcher = Mux(self, ws, running)

        return dispatcher

    async def process_flow_service(self, data, responder, params):

        flow = params.get("flow")
        kind = params.get("kind")

        return await self.invoke_flow_service(data, responder, flow, kind)

    async def invoke_flow_service(self, data, responder, flow, kind):

        if flow not in self.flows:
            raise RuntimeError("Invalid flow")

        key = (flow, kind)

        if key in self.dispatchers:
            return await self.dispatchers[key].process(data, responder)

        intf_defs = self.flows[flow]["interfaces"]

        if kind not in intf_defs:
            raise RuntimeError("This kind not supported by flow")

        qconfig = intf_defs[kind]

        if kind in request_response_dispatchers:
            dispatcher = request_response_dispatchers[kind](
                pulsar_client = self.pulsar_client,
                request_queue = qconfig["request"],
                response_queue = qconfig["response"],
                timeout = 120,
                consumer = f"api-gateway-{flow}-{kind}-request",
                subscriber = f"api-gateway-{flow}-{kind}-request",
            )
        elif kind in sender_dispatchers:
            dispatcher = sender_dispatchers[kind](
                pulsar_client = self.pulsar_client,
                queue = qconfig,
            )
        else:
            raise RuntimeError("Invalid kind")
            
        await dispatcher.start()

        self.dispatchers[key] = dispatcher

        return await dispatcher.process(data, responder)

