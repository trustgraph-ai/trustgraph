"""
Audit middleware for the API gateway.

Wraps every HTTP request with timing and metadata collection, then
emits a ``gateway.request`` audit event after the response is sent.
Handlers can enrich the event by annotating the request dict:

    request['audit_identity'] = identity.principal_id
    request['audit_capability'] = capability
    request['audit_workspace'] = workspace
"""

import time
import logging
from uuid import uuid4

from aiohttp import web

from trustgraph.base import AuditPublisher

logger = logging.getLogger("audit")


def _client_ip(request):
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    peer = request.remote
    return peer or ""


def _outcome_from_status(status):
    if 200 <= status < 400:
        return "success"
    if status == 401:
        return "unauthenticated"
    if status == 403:
        return "denied"
    return "error"


def make_audit_middleware(audit_publisher):

    @web.middleware
    async def audit_middleware(request, handler):
        request_id = str(uuid4())
        request['audit_request_id'] = request_id
        start = time.monotonic()

        status_code = 500
        error = None
        response_size = 0

        try:
            response = await handler(request)
            status_code = response.status
            response_size = response.content_length or 0
            return response
        except web.HTTPException as exc:
            status_code = exc.status
            error = exc.reason
            raise
        except Exception as exc:
            status_code = 500
            error = type(exc).__name__
            raise
        finally:
            duration_ms = int((time.monotonic() - start) * 1000)
            outcome = _outcome_from_status(status_code)

            payload = {
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "client_ip": _client_ip(request),
                "user_agent": request.headers.get("User-Agent", ""),
                "status_code": status_code,
                "outcome": outcome,
                "duration_ms": duration_ms,
                "request_size_bytes": request.content_length or 0,
                "response_size_bytes": response_size,
            }

            identity = request.get('audit_identity')
            if identity:
                payload["identity"] = identity

            capability = request.get('audit_capability')
            if capability:
                payload["capability"] = capability

            workspace = request.get('audit_workspace')
            if workspace:
                payload["workspace"] = workspace

            if error and outcome != "success":
                payload["error"] = error

            try:
                await audit_publisher.emit("gateway.request", payload)
            except Exception:
                logger.debug("Failed to emit gateway audit event",
                             exc_info=True)

    return audit_middleware
