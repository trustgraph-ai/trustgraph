
import asyncio
from aiohttp import web
import uuid
import logging

# Module logger
logger = logging.getLogger(__name__)

from . config import ConfigRequestor
from . flow import FlowRequestor
from . librarian import LibrarianRequestor
from . knowledge import KnowledgeRequestor
from . collection_management import CollectionManagementRequestor

from . embeddings import EmbeddingsRequestor
from . agent import AgentRequestor
from . text_completion import TextCompletionRequestor
from . prompt import PromptRequestor
from . graph_rag import GraphRagRequestor
from . document_rag import DocumentRagRequestor
from . triples_query import TriplesQueryRequestor
from . objects_query import ObjectsQueryRequestor
from . nlp_query import NLPQueryRequestor
from . structured_query import StructuredQueryRequestor
from . structured_diag import StructuredDiagRequestor
from . embeddings import EmbeddingsRequestor
from . graph_embeddings_query import GraphEmbeddingsQueryRequestor
from . document_embeddings_query import DocumentEmbeddingsQueryRequestor
from . mcp_tool import McpToolRequestor
from . text_load import TextLoad
from . document_load import DocumentLoad

from . triples_export import TriplesExport
from . graph_embeddings_export import GraphEmbeddingsExport
from . document_embeddings_export import DocumentEmbeddingsExport
from . entity_contexts_export import EntityContextsExport

from . triples_import import TriplesImport
from . graph_embeddings_import import GraphEmbeddingsImport
from . document_embeddings_import import DocumentEmbeddingsImport
from . entity_contexts_import import EntityContextsImport
from . objects_import import ObjectsImport

from . core_export import CoreExport
from . core_import import CoreImport

from . mux import Mux

request_response_dispatchers = {
    "agent": AgentRequestor,
    "text-completion": TextCompletionRequestor,
    "prompt": PromptRequestor,
    "mcp-tool": McpToolRequestor,
    "graph-rag": GraphRagRequestor,
    "document-rag": DocumentRagRequestor,
    "embeddings": EmbeddingsRequestor,
    "graph-embeddings": GraphEmbeddingsQueryRequestor,
    "document-embeddings": DocumentEmbeddingsQueryRequestor,
    "triples": TriplesQueryRequestor,
    "objects": ObjectsQueryRequestor,
    "nlp-query": NLPQueryRequestor,
    "structured-query": StructuredQueryRequestor,
    "structured-diag": StructuredDiagRequestor,
}

global_dispatchers = {
    "config": ConfigRequestor,
    "flow": FlowRequestor,
    "librarian": LibrarianRequestor,
    "knowledge": KnowledgeRequestor,
    "collection-management": CollectionManagementRequestor,
}

sender_dispatchers = {
    "text-load": TextLoad,
    "document-load": DocumentLoad,
}

export_dispatchers = {
    "triples": TriplesExport,
    "graph-embeddings": GraphEmbeddingsExport,
    "document-embeddings": DocumentEmbeddingsExport,
    "entity-contexts": EntityContextsExport,
}

import_dispatchers = {
    "triples": TriplesImport,
    "graph-embeddings": GraphEmbeddingsImport,
    "document-embeddings": DocumentEmbeddingsImport,
    "entity-contexts": EntityContextsImport,
    "objects": ObjectsImport,
}

class DispatcherWrapper:
    def __init__(self, handler):
        self.handler = handler
    async def process(self, *args):
        return await self.handler(*args)

class DispatcherManager:

    def __init__(self, backend, config_receiver, prefix="api-gateway",
                 queue_overrides=None):
        self.backend = backend
        self.config_receiver = config_receiver
        self.config_receiver.add_handler(self)
        self.prefix = prefix

        # Store queue overrides for global services
        # Format: {"config": {"request": "...", "response": "..."}, ...}
        self.queue_overrides = queue_overrides or {}

        self.flows = {}
        self.dispatchers = {}

    async def start_flow(self, id, flow):
        logger.info(f"Starting flow {id}")
        self.flows[id] = flow
        return

    async def stop_flow(self, id, flow):
        logger.info(f"Stopping flow {id}")
        del self.flows[id]
        return

    def dispatch_global_service(self):
        return DispatcherWrapper(self.process_global_service)

    def dispatch_core_export(self):
        return DispatcherWrapper(self.process_core_export)

    def dispatch_core_import(self):
        return DispatcherWrapper(self.process_core_import)

    async def process_core_import(self, data, error, ok, request):

        ci = CoreImport(self.backend)
        return await ci.process(data, error, ok, request)

    async def process_core_export(self, data, error, ok, request):

        ce = CoreExport(self.backend)
        return await ce.process(data, error, ok, request)

    async def process_global_service(self, data, responder, params):

        kind = params.get("kind")
        return await self.invoke_global_service(data, responder, kind)

    async def invoke_global_service(self, data, responder, kind):

        key = (None, kind)

        if key in self.dispatchers:
            return await self.dispatchers[key].process(data, responder)

        # Get queue overrides if specified for this service
        request_queue = None
        response_queue = None
        if kind in self.queue_overrides:
            request_queue = self.queue_overrides[kind].get("request")
            response_queue = self.queue_overrides[kind].get("response")

        dispatcher = global_dispatchers[kind](
            backend = self.backend,
            timeout = 120,
            consumer = f"{self.prefix}-{kind}-request",
            subscriber = f"{self.prefix}-{kind}-request",
            request_queue = request_queue,
            response_queue = response_queue,
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

        # FIXME: The -store bit, does it make sense?
        if kind == "entity-contexts":
            int_kind = kind + "-load"
        else:
            int_kind = kind + "-store"

        if int_kind not in intf_defs:
            raise RuntimeError("This kind not supported by flow")

        # FIXME: The -store bit, does it make sense?
        qconfig = intf_defs[int_kind]

        id = str(uuid.uuid4())
        dispatcher = import_dispatchers[kind](
            backend = self.backend,
            ws = ws,
            running = running,
            queue = qconfig,
        )

        await dispatcher.start()

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

        # FIXME: The -store bit, does it make sense?
        if kind == "entity-contexts":
            int_kind = kind + "-load"
        else:
            int_kind = kind + "-store"

        if int_kind not in intf_defs:
            raise RuntimeError("This kind not supported by flow")

        qconfig = intf_defs[int_kind]

        id = str(uuid.uuid4())
        dispatcher = export_dispatchers[kind](
            backend = self.backend,
            ws = ws,
            running = running,
            queue = qconfig,
            consumer = f"{self.prefix}-{id}",
            subscriber = f"{self.prefix}-{id}",
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
                backend = self.backend,
                request_queue = qconfig["request"],
                response_queue = qconfig["response"],
                timeout = 120,
                consumer = f"{self.prefix}-{flow}-{kind}-request",
                subscriber = f"{self.prefix}-{flow}-{kind}-request",
            )
        elif kind in sender_dispatchers:
            dispatcher = sender_dispatchers[kind](
                backend = self.backend,
                queue = qconfig,
            )
        else:
            raise RuntimeError("Invalid kind")
            
        await dispatcher.start()

        self.dispatchers[key] = dispatcher

        return await dispatcher.process(data, responder)

