"""
Registry-driven /api/v1/iam endpoint.

The gateway no longer gates IAM management with a single coarse
``users:admin`` capability.  Instead, each operation declares its
own capability + resource shape in the registry (``registry.py``);
this endpoint reads the body's ``operation`` field, looks up the
declaration, and asks the IAM regime to authorise the call.

Operations not in the registry produce a 400 ``unknown operation``.
This is the gateway's primary mechanism for fail-closed gating of
the IAM surface — the registry is the source of truth.
"""

import logging

from aiohttp import web

from .. capabilities import (
    PUBLIC, AUTHENTICATED, auth_failure,
)
from .. registry import lookup, RequestContext

logger = logging.getLogger("iam-endpoint")
logger.setLevel(logging.INFO)


class IamEndpoint:
    """POST /api/v1/iam — generic forwarder gated by the operation
    registry.  The IAM dispatcher (``iam_dispatcher``) forwards the
    body verbatim to iam-svc once authorisation succeeds."""

    def __init__(self, endpoint_path, auth, dispatcher):
        self.path = endpoint_path
        self.auth = auth
        self.dispatcher = dispatcher

    async def start(self):
        pass

    def add_routes(self, app):
        app.add_routes([web.post(self.path, self.handle)])

    async def handle(self, request):
        try:
            body = await request.json()
        except Exception:
            return web.json_response(
                {"error": "invalid json"}, status=400,
            )
        if not isinstance(body, dict):
            return web.json_response(
                {"error": "body must be an object"}, status=400,
            )

        op_name = body.get("operation", "")
        op = lookup(op_name)
        if op is None:
            return web.json_response(
                {"error": "unknown operation"}, status=400,
            )

        # Authentication: required for everything except PUBLIC.
        identity = None
        if op.capability != PUBLIC:
            try:
                identity = await self.auth.authenticate(request)
            except web.HTTPException:
                raise

        # Authorisation: capability sentinels short-circuit the
        # regime call; capability strings go through authorise().
        if op.capability not in (PUBLIC, AUTHENTICATED):
            ctx = RequestContext(
                body=body,
                match_info=dict(request.match_info),
                identity=identity,
            )
            try:
                resource = op.extract_resource(ctx)
                parameters = op.extract_parameters(ctx)
            except Exception as e:
                logger.warning(
                    f"extractor failed for {op_name!r}: "
                    f"{type(e).__name__}: {e}"
                )
                return web.json_response(
                    {"error": "bad request"}, status=400,
                )

            await self.auth.authorise(
                identity, op.capability, resource, parameters,
            )

        # Plumb the authenticated caller's handle through as ``actor``
        # so iam-svc handlers (e.g. whoami, future actor-scoped
        # checks) know who is making the request.  The gateway is
        # the only authority for this — body-supplied ``actor``
        # values are overwritten so callers can't impersonate.
        if identity is not None:
            body["actor"] = identity.handle

        async def responder(x, fin):
            pass

        try:
            resp = await self.dispatcher.process(body, responder)
        except web.HTTPException:
            raise
        except Exception as e:
            logger.error(f"Exception: {e}", exc_info=True)
            return web.json_response({"error": str(e)})

        return web.json_response(resp)
