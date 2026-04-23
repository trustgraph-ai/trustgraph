
import asyncio

from aiohttp import web

from . stream_endpoint import StreamEndpoint
from . variable_endpoint import VariableEndpoint
from . socket import SocketEndpoint
from . metrics import MetricsEndpoint
from . i18n import I18nPackEndpoint
from . auth_endpoints import AuthEndpoints

from .. capabilities import PUBLIC, AUTHENTICATED

from .. dispatch.manager import DispatcherManager


# Capability required for each kind on the /api/v1/{kind} generic
# endpoint (global services).  Coarse gating — the IAM bundle split
# of "read vs write" per admin subsystem is not applied here because
# this endpoint forwards an opaque operation in the body.  Writes
# are the upper bound on what the endpoint can do, so we gate on
# the write/admin capability.
GLOBAL_KIND_CAPABILITY = {
    "config": "config:write",
    "flow": "flows:write",
    "librarian": "documents:write",
    "knowledge": "knowledge:write",
    "collection-management": "collections:write",
    # IAM endpoints land on /api/v1/iam and require the admin bundle.
    # Login / bootstrap / change-password are served by
    # AuthEndpoints, which handle their own gating (PUBLIC /
    # AUTHENTICATED).
    "iam": "users:admin",
}


# Capability required for each kind on the
# /api/v1/flow/{flow}/service/{kind} endpoint (per-flow data-plane).
FLOW_KIND_CAPABILITY = {
    "agent": "agent",
    "text-completion": "llm",
    "prompt": "llm",
    "mcp-tool": "mcp",
    "graph-rag": "graph:read",
    "document-rag": "documents:read",
    "embeddings": "embeddings",
    "graph-embeddings": "graph:read",
    "document-embeddings": "documents:read",
    "triples": "graph:read",
    "rows": "rows:read",
    "nlp-query": "rows:read",
    "structured-query": "rows:read",
    "structured-diag": "rows:read",
    "row-embeddings": "rows:read",
    "sparql": "graph:read",
}


# Capability for the streaming flow import/export endpoints,
# keyed by the "kind" URL segment.
FLOW_IMPORT_CAPABILITY = {
    "triples": "graph:write",
    "graph-embeddings": "graph:write",
    "document-embeddings": "documents:write",
    "entity-contexts": "documents:write",
    "rows": "rows:write",
}

FLOW_EXPORT_CAPABILITY = {
    "triples": "graph:read",
    "graph-embeddings": "graph:read",
    "document-embeddings": "documents:read",
    "entity-contexts": "documents:read",
}


from .. capabilities import enforce, enforce_workspace
import logging as _mgr_logging
_mgr_logger = _mgr_logging.getLogger("endpoint")


class _RoutedVariableEndpoint:
    """HTTP endpoint whose required capability is looked up per
    request from the URL's ``kind`` parameter.  Used for the two
    generic dispatch paths (``/api/v1/{kind}`` and
    ``/api/v1/flow/{flow}/service/{kind}``).  Self-contained rather
    than subclassing ``VariableEndpoint`` to avoid mutating shared
    state across concurrent requests."""

    def __init__(self, endpoint_path, auth, dispatcher, capability_map):
        self.path = endpoint_path
        self.auth = auth
        self.dispatcher = dispatcher
        self._capability_map = capability_map

    async def start(self):
        pass

    def add_routes(self, app):
        app.add_routes([web.post(self.path, self.handle)])

    async def handle(self, request):
        kind = request.match_info.get("kind", "")
        cap = self._capability_map.get(kind)
        if cap is None:
            return web.json_response(
                {"error": "unknown kind"}, status=404,
            )

        identity = await enforce(request, self.auth, cap)

        try:
            data = await request.json()
            if identity is not None:
                enforce_workspace(data, identity)

            async def responder(x, fin):
                pass

            resp = await self.dispatcher.process(
                data, responder, request.match_info,
            )
            return web.json_response(resp)

        except web.HTTPException:
            raise
        except Exception as e:
            _mgr_logger.error(f"Exception: {e}", exc_info=True)
            return web.json_response({"error": str(e)})


class _RoutedSocketEndpoint:
    """WebSocket endpoint whose required capability is looked up per
    request from the URL's ``kind`` parameter.  Used for the flow
    import/export streaming endpoints."""

    def __init__(self, endpoint_path, auth, dispatcher, capability_map):
        self.path = endpoint_path
        self.auth = auth
        self.dispatcher = dispatcher
        self._capability_map = capability_map

    async def start(self):
        pass

    def add_routes(self, app):
        app.add_routes([web.get(self.path, self.handle)])

    async def handle(self, request):
        from .. capabilities import check, auth_failure, access_denied

        kind = request.match_info.get("kind", "")
        cap = self._capability_map.get(kind)
        if cap is None:
            return web.json_response(
                {"error": "unknown kind"}, status=404,
            )

        token = request.query.get("token", "")
        if not token:
            return auth_failure()

        from . socket import _QueryTokenRequest
        try:
            identity = await self.auth.authenticate(
                _QueryTokenRequest(token)
            )
        except web.HTTPException as e:
            return e
        if not check(identity, cap):
            return access_denied()

        # Delegate the websocket handling to a standalone SocketEndpoint
        # with the resolved capability, bypassing the per-request mutation
        # concern by instantiating fresh state.
        ws_ep = SocketEndpoint(
            endpoint_path=self.path,
            auth=self.auth,
            dispatcher=self.dispatcher,
            capability=cap,
        )
        return await ws_ep.handle(request)


class EndpointManager:

    def __init__(
            self, dispatcher_manager, auth, prometheus_url, timeout=600,
    ):

        self.dispatcher_manager = dispatcher_manager
        self.timeout = timeout

        self.endpoints = [

            # Auth surface — public / authenticated-any.  Must come
            # before the generic /api/v1/{kind} routes to win the
            # match for /api/v1/auth/* paths.  aiohttp routes in
            # registration order, so we prepend here.
            AuthEndpoints(
                iam_dispatcher=dispatcher_manager.dispatch_auth_iam(),
                auth=auth,
            ),

            I18nPackEndpoint(
                endpoint_path="/api/v1/i18n/packs/{lang}",
                auth=auth,
                capability=PUBLIC,
            ),
            MetricsEndpoint(
                endpoint_path="/api/metrics",
                prometheus_url=prometheus_url,
                auth=auth,
                capability="metrics:read",
            ),

            # Global services: capability chosen per-kind.
            _RoutedVariableEndpoint(
                endpoint_path="/api/v1/{kind}",
                auth=auth,
                dispatcher=dispatcher_manager.dispatch_global_service(),
                capability_map=GLOBAL_KIND_CAPABILITY,
            ),

            # /api/v1/socket: WebSocket handshake accepts
            # unconditionally; the Mux dispatcher runs the
            # first-frame auth protocol.  Handshake-time 401s break
            # browser reconnection, so authentication is always
            # in-band for this endpoint.
            SocketEndpoint(
                endpoint_path="/api/v1/socket",
                auth=auth,
                dispatcher=dispatcher_manager.dispatch_socket(),
                capability=AUTHENTICATED,  # informational only; bypassed
                in_band_auth=True,
            ),

            # Per-flow request/response services — capability per kind.
            _RoutedVariableEndpoint(
                endpoint_path="/api/v1/flow/{flow}/service/{kind}",
                auth=auth,
                dispatcher=dispatcher_manager.dispatch_flow_service(),
                capability_map=FLOW_KIND_CAPABILITY,
            ),

            # Per-flow streaming import/export — capability per kind.
            _RoutedSocketEndpoint(
                endpoint_path="/api/v1/flow/{flow}/import/{kind}",
                auth=auth,
                dispatcher=dispatcher_manager.dispatch_flow_import(),
                capability_map=FLOW_IMPORT_CAPABILITY,
            ),
            _RoutedSocketEndpoint(
                endpoint_path="/api/v1/flow/{flow}/export/{kind}",
                auth=auth,
                dispatcher=dispatcher_manager.dispatch_flow_export(),
                capability_map=FLOW_EXPORT_CAPABILITY,
            ),

            StreamEndpoint(
                endpoint_path="/api/v1/import-core",
                auth=auth,
                method="POST",
                dispatcher=dispatcher_manager.dispatch_core_import(),
                # Cross-subject import — require the admin bundle via a
                # single representative capability.
                capability="users:admin",
            ),
            StreamEndpoint(
                endpoint_path="/api/v1/export-core",
                auth=auth,
                method="GET",
                dispatcher=dispatcher_manager.dispatch_core_export(),
                capability="users:admin",
            ),
            StreamEndpoint(
                endpoint_path="/api/v1/document-stream",
                auth=auth,
                method="GET",
                dispatcher=dispatcher_manager.dispatch_document_stream(),
                capability="documents:read",
            ),
        ]

    def add_routes(self, app):
        for ep in self.endpoints:
            ep.add_routes(app)

    async def start(self):
        for ep in self.endpoints:
            await ep.start()
