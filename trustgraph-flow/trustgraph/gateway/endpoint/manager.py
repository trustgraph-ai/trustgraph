
import asyncio

from aiohttp import web

from . stream_endpoint import StreamEndpoint
from . variable_endpoint import VariableEndpoint
from . socket import SocketEndpoint
from . metrics import MetricsEndpoint
from . i18n import I18nPackEndpoint
from . auth_endpoints import AuthEndpoints
from . iam_endpoint import IamEndpoint
from . registry_endpoint import RegistryRoutedVariableEndpoint

from .. capabilities import PUBLIC, AUTHENTICATED, auth_failure, workspace_not_found
from .. registry import lookup as _registry_lookup, RequestContext, ResourceLevel

from .. dispatch.manager import DispatcherManager


# /api/v1/{kind} (config / flow / librarian / knowledge /
# collection-management), /api/v1/iam, and /api/v1/flow/{flow}/...
# routes are all gated per-operation by the registry, not by a
# per-kind capability map.  Login / bootstrap / change-password are
# served by AuthEndpoints with their own PUBLIC / AUTHENTICATED
# sentinels.


import logging as _mgr_logging
_mgr_logger = _mgr_logging.getLogger("endpoint")


class _RoutedVariableEndpoint:
    """HTTP endpoint that gates per request via the operation
    registry.  The URL's ``kind`` parameter combined with a fixed
    ``registry_prefix`` yields the registry key — e.g. prefix
    ``flow-service`` and kind ``agent`` looks up
    ``flow-service:agent``.

    Used for ``/api/v1/flow/{flow}/service/{kind}`` (per-flow
    data-plane services).  ``/api/v1/{kind}`` (workspace-level
    global services) goes through ``RegistryRoutedVariableEndpoint``
    which discriminates on body operation as well as URL kind."""

    def __init__(self, endpoint_path, auth, dispatcher, registry_prefix):
        self.path = endpoint_path
        self.auth = auth
        self.dispatcher = dispatcher
        self._registry_prefix = registry_prefix

    async def start(self):
        pass

    def add_routes(self, app):
        app.add_routes([web.post(self.path, self.handle)])

    async def handle(self, request):
        kind = request.match_info.get("kind", "")
        op = _registry_lookup(f"{self._registry_prefix}:{kind}")
        if op is None:
            return web.json_response(
                {"error": "unknown kind"}, status=404,
            )

        identity = await self.auth.authenticate(request)

        try:
            data = await request.json()
            ctx = RequestContext(
                body=data if isinstance(data, dict) else {},
                match_info=dict(request.match_info),
                identity=identity,
            )
            resource = op.extract_resource(ctx)
            parameters = op.extract_parameters(ctx)
            await self.auth.authorise(
                identity, op.capability, resource, parameters,
            )

            ws = resource.get("workspace", "")
            if ws and ws not in self.auth.known_workspaces:
                raise workspace_not_found()

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
    """WebSocket endpoint gated per request via the operation
    registry.  Like ``_RoutedVariableEndpoint`` but for the
    streaming flow import / export socket paths."""

    def __init__(self, endpoint_path, auth, dispatcher, registry_prefix):
        self.path = endpoint_path
        self.auth = auth
        self.dispatcher = dispatcher
        self._registry_prefix = registry_prefix

    async def start(self):
        pass

    def add_routes(self, app):
        app.add_routes([web.get(self.path, self.handle)])

    async def handle(self, request):
        kind = request.match_info.get("kind", "")
        op = _registry_lookup(f"{self._registry_prefix}:{kind}")
        if op is None:
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

        ctx = RequestContext(
            body={},
            match_info=dict(request.match_info),
            identity=identity,
        )
        try:
            resource = op.extract_resource(ctx)
            parameters = op.extract_parameters(ctx)
            await self.auth.authorise(
                identity, op.capability, resource, parameters,
            )

            ws = resource.get("workspace", "")
            if ws and ws not in self.auth.known_workspaces:
                raise workspace_not_found()

        except web.HTTPException as e:
            return e

        # Delegate the websocket handling to a standalone SocketEndpoint
        # with the resolved capability, bypassing the per-request mutation
        # concern by instantiating fresh state.
        ws_ep = SocketEndpoint(
            endpoint_path=self.path,
            auth=self.auth,
            dispatcher=self.dispatcher,
            capability=op.capability,
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

            # /api/v1/iam — registry-driven IAM management.  Per
            # operation gating happens inside IamEndpoint via the
            # operation registry; the dispatcher forwards verbatim
            # to iam-svc once authorisation has succeeded.  Listed
            # before the generic /api/v1/{kind} route so it wins
            # the match for "iam".
            IamEndpoint(
                endpoint_path="/api/v1/iam",
                auth=auth,
                dispatcher=dispatcher_manager.dispatch_auth_iam(),
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

            # Global services: registry-driven per-operation gating.
            # Each kind+op combination has a registry entry that
            # declares its capability and resource shape.  Listed
            # after the IAM and auth-surface routes; aiohttp's
            # path matcher prefers the more-specific path so this
            # variable route doesn't shadow them.
            RegistryRoutedVariableEndpoint(
                endpoint_path="/api/v1/{kind}",
                auth=auth,
                dispatcher=dispatcher_manager.dispatch_global_service(),
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

            # Per-flow request/response services — gated per
            # ``flow-service:<kind>`` registry entry.
            _RoutedVariableEndpoint(
                endpoint_path="/api/v1/flow/{flow}/service/{kind}",
                auth=auth,
                dispatcher=dispatcher_manager.dispatch_flow_service(),
                registry_prefix="flow-service",
            ),

            # Per-flow streaming import/export — gated per
            # ``flow-import:<kind>`` / ``flow-export:<kind>`` registry
            # entry.
            _RoutedSocketEndpoint(
                endpoint_path="/api/v1/flow/{flow}/import/{kind}",
                auth=auth,
                dispatcher=dispatcher_manager.dispatch_flow_import(),
                registry_prefix="flow-import",
            ),
            _RoutedSocketEndpoint(
                endpoint_path="/api/v1/flow/{flow}/export/{kind}",
                auth=auth,
                dispatcher=dispatcher_manager.dispatch_flow_export(),
                registry_prefix="flow-export",
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
