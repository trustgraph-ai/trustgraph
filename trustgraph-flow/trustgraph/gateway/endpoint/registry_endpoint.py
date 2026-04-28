"""
Registry-driven dispatch for ``/api/v1/{kind}`` global services.

The body's ``operation`` field plus the URL's ``{kind}`` together
form the canonical operation name (``<kind>:<operation>``) that the
gateway looks up in ``registry.py``.  The matched operation
declares its capability and resource shape; this endpoint asks the
IAM regime to authorise the call before forwarding the body
verbatim to the backend dispatcher.

The dispatcher is the same ``dispatch_global_service()`` factory the
old coarse path used; only the gating layer has changed.

Operations not present in the registry are rejected with 400
``unknown operation`` — fail closed.
"""

import logging

from aiohttp import web

from .. capabilities import (
    PUBLIC, AUTHENTICATED, auth_failure,
)
from .. registry import lookup, RequestContext

logger = logging.getLogger("registry-endpoint")
logger.setLevel(logging.INFO)


class RegistryRoutedVariableEndpoint:
    """POST /api/v1/{kind} — kind comes from the URL, operation comes
    from the body, both are joined as the registry key."""

    def __init__(self, endpoint_path, auth, dispatcher):
        self.path = endpoint_path
        self.auth = auth
        self.dispatcher = dispatcher

    async def start(self):
        pass

    def add_routes(self, app):
        app.add_routes([web.post(self.path, self.handle)])

    async def handle(self, request):
        kind = request.match_info.get("kind", "")
        if not kind:
            return web.json_response(
                {"error": "missing kind"}, status=404,
            )

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
        if not op_name:
            return web.json_response(
                {"error": "missing operation"}, status=400,
            )

        registry_key = f"{kind}:{op_name}"
        op = lookup(registry_key)
        if op is None:
            return web.json_response(
                {"error": "unknown operation"}, status=400,
            )

        identity = None
        if op.capability != PUBLIC:
            identity = await self.auth.authenticate(request)

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
                    f"extractor failed for {registry_key!r}: "
                    f"{type(e).__name__}: {e}"
                )
                return web.json_response(
                    {"error": "bad request"}, status=400,
                )

            await self.auth.authorise(
                identity, op.capability, resource, parameters,
            )

            # Default-fill workspace into the body so downstream
            # dispatchers see the canonical resolved value.  The
            # extractor has already pulled the workspace out;
            # mirror it back to the body for the verbatim forward.
            if "workspace" in resource:
                body["workspace"] = resource["workspace"]

        async def responder(x, fin):
            pass

        try:
            resp = await self.dispatcher.process(
                body, responder, request.match_info,
            )
        except web.HTTPException:
            raise
        except Exception as e:
            logger.error(f"Exception: {e}", exc_info=True)
            return web.json_response({"error": str(e)})

        return web.json_response(resp)
