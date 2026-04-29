
import asyncio
from aiohttp import web
import uuid
import logging

# Module logger
logger = logging.getLogger(__name__)

from . config import ConfigRequestor
from . flow import FlowRequestor
from . iam import IamRequestor
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
from . rows_query import RowsQueryRequestor
from . nlp_query import NLPQueryRequestor
from . sparql_query import SparqlQueryRequestor
from . structured_query import StructuredQueryRequestor
from . structured_diag import StructuredDiagRequestor
from . embeddings import EmbeddingsRequestor
from . graph_embeddings_query import GraphEmbeddingsQueryRequestor
from . document_embeddings_query import DocumentEmbeddingsQueryRequestor
from . row_embeddings_query import RowEmbeddingsQueryRequestor
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
from . rows_import import RowsImport

from . core_export import CoreExport
from . core_import import CoreImport
from . document_stream import DocumentStreamExport

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
    "rows": RowsQueryRequestor,
    "nlp-query": NLPQueryRequestor,
    "structured-query": StructuredQueryRequestor,
    "structured-diag": StructuredDiagRequestor,
    "row-embeddings": RowEmbeddingsQueryRequestor,
    "sparql": SparqlQueryRequestor,
}

global_dispatchers = {
    "config": ConfigRequestor,
    "flow": FlowRequestor,
    "iam": IamRequestor,
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
    "rows": RowsImport,
}

class DispatcherWrapper:
    def __init__(self, handler):
        self.handler = handler
    async def process(self, *args):
        return await self.handler(*args)

class DispatcherManager:

    def __init__(self, backend, config_receiver, auth,
                 prefix="api-gateway", queue_overrides=None):
        """
        ``auth`` is required.  It flows into the Mux for first-frame
        WebSocket authentication and into downstream dispatcher
        construction.  There is no permissive default — constructing
        a DispatcherManager without an authenticator would be a
        silent downgrade to no-auth on the socket path.
        """
        if auth is None:
            raise ValueError(
                "DispatcherManager requires an 'auth' argument — there "
                "is no no-auth mode"
            )

        self.backend = backend
        self.config_receiver = config_receiver
        self.config_receiver.add_handler(self)
        self.prefix = prefix

        # Gateway IamAuth — used by the socket Mux for first-frame
        # auth and by any dispatcher that needs to resolve caller
        # identity out-of-band.
        self.auth = auth

        # Store queue overrides for global services
        # Format: {"config": {"request": "...", "response": "..."}, ...}
        self.queue_overrides = queue_overrides or {}

        # Flows keyed by (workspace, flow_id)
        self.flows = {}
        # Dispatchers keyed by (workspace, flow_id, kind)
        self.dispatchers = {}
        self.dispatcher_lock = asyncio.Lock()

    async def start_flow(self, workspace, id, flow):
        logger.info(f"Starting flow {workspace}/{id}")
        self.flows[(workspace, id)] = flow
        return

    async def stop_flow(self, workspace, id, flow):
        logger.info(f"Stopping flow {workspace}/{id}")
        self.flows.pop((workspace, id), None)

        # Drop any cached dispatchers for this (workspace, flow).
        # Their publishers and subscribers were wired to the flow's
        # per-flow exchanges, which flow-svc tears down when the flow
        # stops.  Leaving the cached dispatcher in place means a
        # subsequent restart of the same flow id would reuse a
        # dispatcher whose subscription queue is still bound to the
        # torn-down (now re-created) response exchange — requests go
        # out but responses are silently dropped and the caller hangs.
        #
        # Per-flow dispatchers are keyed (workspace, flow_id, kind).
        # Global dispatchers are keyed (None, kind) — the len==3
        # check naturally excludes them.
        async with self.dispatcher_lock:
            stale_keys = [
                k for k in self.dispatchers
                if isinstance(k, tuple) and len(k) == 3
                   and k[0] == workspace and k[1] == id
            ]
            for key in stale_keys:
                dispatcher = self.dispatchers.pop(key)
                try:
                    await dispatcher.stop()
                except Exception as e:
                    logger.warning(
                        f"Error stopping cached dispatcher {key}: {e}"
                    )

        return

    def dispatch_global_service(self):
        return DispatcherWrapper(self.process_global_service)

    def dispatch_auth_iam(self):
        """Pre-configured IAM dispatcher for the gateway's auth
        endpoints (login, bootstrap, change-password).  Pins the
        kind to ``iam`` so these handlers don't have to supply URL
        params the global dispatcher would expect."""
        async def _process(data, responder):
            return await self.invoke_global_service(data, responder, "iam")
        return DispatcherWrapper(_process)

    def dispatch_core_export(self):
        return DispatcherWrapper(self.process_core_export)

    def dispatch_core_import(self):
        return DispatcherWrapper(self.process_core_import)

    def dispatch_document_stream(self):
        return DispatcherWrapper(self.process_document_stream)

    async def process_document_stream(self, data, error, ok, request):

        ds = DocumentStreamExport(self.backend)
        return await ds.process(data, error, ok, request)

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

        if key not in self.dispatchers:
            async with self.dispatcher_lock:
                if key not in self.dispatchers:
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

        return await self.dispatchers[key].process(data, responder)

    def dispatch_flow_import(self):
        return self.process_flow_import

    def dispatch_flow_export(self):
        return self.process_flow_export

    def dispatch_socket(self):
        return self.process_socket

    def dispatch_flow_service(self):
        return DispatcherWrapper(self.process_flow_service)

    async def process_flow_import(self, ws, running, params):

        workspace = params.get("workspace", "default")
        flow = params.get("flow")
        kind = params.get("kind")

        flow_key = (workspace, flow)
        if flow_key not in self.flows:
            raise RuntimeError(f"Invalid flow {workspace}/{flow}")

        if kind not in import_dispatchers:
            raise RuntimeError("Invalid kind")

        key = (workspace, flow, kind)

        intf_defs = self.flows[flow_key]["interfaces"]

        # FIXME: The -store bit, does it make sense?
        if kind == "entity-contexts":
            int_kind = kind + "-load"
        else:
            int_kind = kind + "-store"

        if int_kind not in intf_defs:
            raise RuntimeError("This kind not supported by flow")

        # FIXME: The -store bit, does it make sense?
        qconfig = intf_defs[int_kind]["flow"]

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

        workspace = params.get("workspace", "default")
        flow = params.get("flow")
        kind = params.get("kind")

        flow_key = (workspace, flow)
        if flow_key not in self.flows:
            raise RuntimeError(f"Invalid flow {workspace}/{flow}")

        if kind not in export_dispatchers:
            raise RuntimeError("Invalid kind")

        key = (workspace, flow, kind)

        intf_defs = self.flows[flow_key]["interfaces"]

        # FIXME: The -store bit, does it make sense?
        if kind == "entity-contexts":
            int_kind = kind + "-load"
        else:
            int_kind = kind + "-store"

        if int_kind not in intf_defs:
            raise RuntimeError("This kind not supported by flow")

        qconfig = intf_defs[int_kind]["flow"]

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

        # The mux self-authenticates via the first-frame protocol;
        # pass the gateway's IamAuth so it can validate tokens
        # without reaching back into the endpoint layer.
        dispatcher = Mux(self, ws, running, auth=self.auth)

        return dispatcher

    async def process_flow_service(self, data, responder, params):

        # Workspace can come from URL or from request body, defaulting
        # to "default". Having it in the URL allows gateway routing to
        # be workspace-aware without touching the body.
        workspace = params.get("workspace")
        if not workspace and isinstance(data, dict):
            workspace = data.get("workspace")
        if not workspace:
            workspace = "default"

        flow = params.get("flow")
        kind = params.get("kind")

        return await self.invoke_flow_service(
            data, responder, workspace, flow, kind,
        )

    async def invoke_flow_service(
        self, data, responder, workspace, flow, kind,
    ):

        flow_key = (workspace, flow)
        if flow_key not in self.flows:
            raise RuntimeError(f"Invalid flow {workspace}/{flow}")

        key = (workspace, flow, kind)

        if key not in self.dispatchers:
            async with self.dispatcher_lock:
                if key not in self.dispatchers:
                    intf_defs = self.flows[flow_key]["interfaces"]

                    if kind not in intf_defs:
                        raise RuntimeError("This kind not supported by flow")

                    qconfig = intf_defs[kind]

                    if kind in request_response_dispatchers:
                        dispatcher = request_response_dispatchers[kind](
                            backend = self.backend,
                            request_queue = qconfig["request"],
                            response_queue = qconfig["response"],
                            timeout = 120,
                            consumer = f"{self.prefix}-{workspace}-{flow}-{kind}-request",
                            subscriber = f"{self.prefix}-{workspace}-{flow}-{kind}-request",
                        )
                    elif kind in sender_dispatchers:
                        dispatcher = sender_dispatchers[kind](
                            backend = self.backend,
                            queue = qconfig["flow"],
                        )
                    else:
                        raise RuntimeError("Invalid kind")

                    await dispatcher.start()
                    self.dispatchers[key] = dispatcher

        return await self.dispatchers[key].process(data, responder)

