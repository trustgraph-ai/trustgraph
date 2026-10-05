"""
Gateway auth endpoints.

Dedicated paths:
  POST /api/v1/auth/login            — unauthenticated; username/password → JWT
  POST /api/v1/auth/bootstrap         — unauthenticated; IAM bootstrap op
  POST /api/v1/auth/change-password   — authenticated; any role
  POST /api/v1/auth/mint-token        — admin; mint JWT with user context

These are the only IAM-surface operations that can be reached from
outside.  Everything else routes through ``/api/v1/iam`` gated by
``users:admin``.
"""

import json
import logging

from aiohttp import web

from .. capabilities import enforce, PUBLIC, AUTHENTICATED

logger = logging.getLogger("auth-endpoints")
logger.setLevel(logging.INFO)


class AuthEndpoints:
    """Groups the three auth-surface handlers.  Each forwards to the
    IAM service via the existing ``IamRequestor`` dispatcher."""

    def __init__(self, iam_dispatcher, auth):
        self.iam = iam_dispatcher
        self.auth = auth

    async def start(self):
        pass

    def add_routes(self, app):
        app.add_routes([
            web.post("/api/v1/auth/login", self.login),
            web.post("/api/v1/auth/bootstrap", self.bootstrap),
            web.post(
                "/api/v1/auth/bootstrap-status",
                self.bootstrap_status,
            ),
            web.post(
                "/api/v1/auth/change-password",
                self.change_password,
            ),
            web.post(
                "/api/v1/auth/mint-token",
                self.mint_token,
            ),
        ])

    async def _forward(self, body):
        async def responder(x, fin):
            pass
        return await self.iam.process(body, responder)

    async def login(self, request):
        """Public.  Accepts {username, password, workspace?}.  Returns
        {jwt, jwt_expires} on success; IAM's masked auth failure on
        anything else."""
        await enforce(request, self.auth, PUBLIC)
        try:
            body = await request.json()
        except Exception:
            return web.json_response(
                {"error": "invalid json"}, status=400,
            )
        req = {
            "operation": "login",
            "username": body.get("username", ""),
            "password": body.get("password", ""),
            "workspace": body.get("workspace", ""),
        }
        resp = await self._forward(req)
        if "error" in resp:
            return web.json_response(
                {"error": "auth failure"}, status=401,
            )
        return web.json_response(resp)

    async def bootstrap(self, request):
        """Public.  Valid only when IAM is running in bootstrap mode
        with empty tables.  In every other case the IAM service
        returns a masked auth-failure."""
        await enforce(request, self.auth, PUBLIC)
        resp = await self._forward({"operation": "bootstrap"})
        if "error" in resp:
            return web.json_response(
                {"error": "auth failure"}, status=401,
            )
        return web.json_response(resp)

    async def bootstrap_status(self, request):
        """Public, side-effect-free.  Returns ``{"bootstrap_available":
        bool}`` so a UI can decide whether to render first-run setup
        without invoking the consuming ``bootstrap`` op."""
        await enforce(request, self.auth, PUBLIC)
        resp = await self._forward({"operation": "bootstrap-status"})
        if "error" in resp:
            return web.json_response(
                {"error": "auth failure"}, status=401,
            )
        return web.json_response(resp)

    async def change_password(self, request):
        """Authenticated (any role).  Accepts {current_password,
        new_password}; user_id is taken from the authenticated
        identity — the caller cannot change someone else's password
        this way (reset-password is the admin path)."""
        identity = await enforce(request, self.auth, AUTHENTICATED)
        try:
            body = await request.json()
        except Exception:
            return web.json_response(
                {"error": "invalid json"}, status=400,
            )
        req = {
            "operation": "change-password",
            "user_id": identity.handle,
            "password": body.get("current_password", ""),
            "new_password": body.get("new_password", ""),
        }
        resp = await self._forward(req)
        if "error" in resp:
            err_type = resp.get("error", {}).get("type", "")
            if err_type == "auth-failed":
                return web.json_response(
                    {"error": "auth failure"}, status=401,
                )
            return web.json_response(
                {"error": resp.get("error", {}).get("message", "error")},
                status=400,
            )
        return web.json_response(resp)

    async def mint_token(self, request):
        """Admin-only.  Accepts {user_id, workspace, user_context}.
        Mints a signed JWT containing the supplied UserContext in its
        claims.  The caller must hold the ``mint-token`` capability."""
        identity = await enforce(request, self.auth, "mint-token")
        try:
            body = await request.json()
        except Exception:
            return web.json_response(
                {"error": "invalid json"}, status=400,
            )

        user_context = body.get("user_context")
        if not isinstance(user_context, dict):
            return web.json_response(
                {"error": "user_context must be a JSON object"},
                status=400,
            )

        req = {
            "operation": "mint-token",
            "user_id": body.get("user_id", ""),
            "workspace": body.get("workspace", ""),
            "user_context_json": json.dumps(user_context),
        }
        resp = await self._forward(req)
        if "error" in resp:
            err_type = resp.get("error", {}).get("type", "")
            if err_type == "auth-failed":
                return web.json_response(
                    {"error": "access denied"}, status=403,
                )
            return web.json_response(
                {"error": resp.get("error", {}).get("message", "error")},
                status=400,
            )
        return web.json_response(resp)
