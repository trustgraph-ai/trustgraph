"""
Tests for the gateway audit middleware.

Verifies that gateway.request events are emitted with correct
metadata for success, error, and auth failure paths.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from aiohttp import web
from aiohttp.test_utils import make_mocked_request

from trustgraph.gateway.audit import make_audit_middleware, _client_ip, _outcome_from_status


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(method="POST", path="/api/v1/config", headers=None,
                  remote="10.0.0.1"):
    hdrs = headers or {}
    req = make_mocked_request(method, path, headers=hdrs)
    req._transport_peername = (remote, 0)
    return req


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

class TestClientIp:

    def test_uses_x_forwarded_for(self):
        req = _make_request(headers={"X-Forwarded-For": "1.2.3.4, 10.0.0.1"})
        assert _client_ip(req) == "1.2.3.4"

    def test_falls_back_to_remote(self):
        req = _make_request(remote="192.168.1.1")
        assert _client_ip(req) == "192.168.1.1"


class TestOutcomeFromStatus:

    def test_success_range(self):
        assert _outcome_from_status(200) == "success"
        assert _outcome_from_status(201) == "success"
        assert _outcome_from_status(204) == "success"
        assert _outcome_from_status(301) == "success"

    def test_unauthenticated(self):
        assert _outcome_from_status(401) == "unauthenticated"

    def test_denied(self):
        assert _outcome_from_status(403) == "denied"

    def test_error(self):
        assert _outcome_from_status(400) == "error"
        assert _outcome_from_status(404) == "error"
        assert _outcome_from_status(500) == "error"


# ---------------------------------------------------------------------------
# Middleware integration
# ---------------------------------------------------------------------------

class TestAuditMiddleware:

    @pytest.fixture
    def audit_publisher(self):
        pub = AsyncMock()
        pub.emit = AsyncMock()
        return pub

    @pytest.fixture
    def middleware(self, audit_publisher):
        return make_audit_middleware(audit_publisher)

    @pytest.mark.asyncio
    async def test_emits_event_on_success(self, middleware, audit_publisher):
        async def handler(request):
            return web.json_response({"ok": True})

        req = _make_request()
        await middleware(req, handler)

        audit_publisher.emit.assert_called_once()
        event_type, payload = audit_publisher.emit.call_args[0]
        assert event_type == "gateway.request"
        assert payload["method"] == "POST"
        assert payload["path"] == "/api/v1/config"
        assert payload["status_code"] == 200
        assert payload["outcome"] == "success"
        assert "request_id" in payload
        assert "duration_ms" in payload
        assert "error" not in payload

    @pytest.mark.asyncio
    async def test_emits_event_on_http_exception(self, middleware,
                                                  audit_publisher):
        async def handler(request):
            raise web.HTTPForbidden(reason="access denied")

        req = _make_request()
        with pytest.raises(web.HTTPForbidden):
            await middleware(req, handler)

        audit_publisher.emit.assert_called_once()
        _, payload = audit_publisher.emit.call_args[0]
        assert payload["status_code"] == 403
        assert payload["outcome"] == "denied"
        assert payload["error"] == "access denied"

    @pytest.mark.asyncio
    async def test_emits_event_on_unhandled_exception(self, middleware,
                                                       audit_publisher):
        async def handler(request):
            raise ValueError("boom")

        req = _make_request()
        with pytest.raises(ValueError):
            await middleware(req, handler)

        audit_publisher.emit.assert_called_once()
        _, payload = audit_publisher.emit.call_args[0]
        assert payload["status_code"] == 500
        assert payload["outcome"] == "error"
        assert payload["error"] == "ValueError"

    @pytest.mark.asyncio
    async def test_includes_identity_when_annotated(self, middleware,
                                                     audit_publisher):
        async def handler(request):
            request['audit_identity'] = "user:mark"
            return web.json_response({"ok": True})

        req = _make_request()
        await middleware(req, handler)

        _, payload = audit_publisher.emit.call_args[0]
        assert payload["identity"] == "user:mark"

    @pytest.mark.asyncio
    async def test_includes_capability_when_annotated(self, middleware,
                                                       audit_publisher):
        async def handler(request):
            request['audit_capability'] = "config:read"
            request['audit_workspace'] = "production"
            return web.json_response({"ok": True})

        req = _make_request()
        await middleware(req, handler)

        _, payload = audit_publisher.emit.call_args[0]
        assert payload["capability"] == "config:read"
        assert payload["workspace"] == "production"

    @pytest.mark.asyncio
    async def test_omits_unannotated_fields(self, middleware,
                                             audit_publisher):
        async def handler(request):
            return web.json_response({"ok": True})

        req = _make_request()
        await middleware(req, handler)

        _, payload = audit_publisher.emit.call_args[0]
        assert "identity" not in payload
        assert "capability" not in payload
        assert "workspace" not in payload

    @pytest.mark.asyncio
    async def test_assigns_request_id(self, middleware, audit_publisher):
        captured_id = None

        async def handler(request):
            nonlocal captured_id
            captured_id = request.get('audit_request_id')
            return web.json_response({"ok": True})

        req = _make_request()
        await middleware(req, handler)

        assert captured_id is not None
        _, payload = audit_publisher.emit.call_args[0]
        assert payload["request_id"] == captured_id

    @pytest.mark.asyncio
    async def test_still_returns_response_if_emit_fails(self, middleware,
                                                         audit_publisher):
        audit_publisher.emit.side_effect = RuntimeError("pub/sub down")

        async def handler(request):
            return web.json_response({"ok": True})

        req = _make_request()
        resp = await middleware(req, handler)
        assert resp.status == 200
