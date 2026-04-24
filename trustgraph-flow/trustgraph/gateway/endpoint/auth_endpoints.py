"""
Gateway auth endpoints.

Three dedicated paths:
  POST /api/v1/auth/login            — unauthenticated; username/password → JWT
  POST /api/v1/auth/bootstrap         — unauthenticated; IAM bootstrap op
  POST /api/v1/auth/change-password   — authenticated; any role

These are the only IAM-surface operations that can be reached from
outside.  Everything else routes through ``/api/v1/iam`` gated by
``users:admin``.
"""

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
                "/api/v1/auth/change-password",
                self.change_password,
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
            "user_id": identity.user_id,
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
