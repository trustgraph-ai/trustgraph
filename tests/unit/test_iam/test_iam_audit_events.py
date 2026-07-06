"""
Tests for IAM service audit event emission.

Verifies that the IAM Processor emits correctly categorised audit
events (iam.authenticate, iam.authorise, iam.management) after
handling each request type.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock

from trustgraph.schema import IamRequest, IamResponse, Error
from trustgraph.iam.service.service import Processor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_msg(request, msg_id="test-msg-1"):
    msg = MagicMock()
    msg.value.return_value = request
    msg.properties.return_value = {"id": msg_id}
    return msg


def _make_processor():
    """Create a Processor with stubbed dependencies."""
    proc = object.__new__(Processor)
    proc.id = "test-iam-svc"
    proc.iam_response_producer = AsyncMock()
    proc.audit = AsyncMock()
    return proc


# ---------------------------------------------------------------------------
# Authentication events
# ---------------------------------------------------------------------------

class TestAuthenticateAuditEvents:

    @pytest.mark.asyncio
    async def test_resolve_api_key_success(self):
        proc = _make_processor()
        resp = IamResponse(
            resolved_user_id="user-123",
            resolved_default_workspace="default",
        )
        proc.iam = MagicMock()
        proc.iam.handle = AsyncMock(return_value=resp)

        req = IamRequest(
            operation="resolve-api-key",
            api_key="tg_test",
            request_id="req-1",
            client_ip="10.0.0.1",
        )
        await proc.on_iam_request(_make_msg(req), None, None)

        proc.audit.emit.assert_called_once()
        event_type, payload = proc.audit.emit.call_args[0]
        assert event_type == "iam.authenticate"
        assert payload["credential_type"] == "api-key"
        assert payload["identity"] == "user-123"
        assert payload["outcome"] == "success"
        assert payload["request_id"] == "req-1"
        assert payload["client_ip"] == "10.0.0.1"
        assert "failure_reason" not in payload

    @pytest.mark.asyncio
    async def test_resolve_api_key_failure(self):
        proc = _make_processor()
        resp = IamResponse(error=Error(type="auth-failed", message="unknown"))
        proc.iam = MagicMock()
        proc.iam.handle = AsyncMock(return_value=resp)

        req = IamRequest(
            operation="resolve-api-key",
            api_key="tg_bad",
            request_id="req-2",
            client_ip="10.0.0.2",
        )
        await proc.on_iam_request(_make_msg(req), None, None)

        _, payload = proc.audit.emit.call_args[0]
        assert payload["outcome"] == "failure"
        assert payload["identity"] == "unknown"
        assert payload["failure_reason"] == "auth-failed"

    @pytest.mark.asyncio
    async def test_login_emits_authenticate(self):
        proc = _make_processor()
        resp = IamResponse(
            resolved_user_id="user-456",
            jwt="eyJ...",
            jwt_expires="2026-07-06T10:00:00Z",
        )
        proc.iam = MagicMock()
        proc.iam.handle = AsyncMock(return_value=resp)

        req = IamRequest(
            operation="login",
            username="mark",
            password="secret",
            request_id="req-3",
        )
        await proc.on_iam_request(_make_msg(req), None, None)

        event_type, payload = proc.audit.emit.call_args[0]
        assert event_type == "iam.authenticate"
        assert payload["credential_type"] == "login-password"

    @pytest.mark.asyncio
    async def test_anonymous_emits_authenticate(self):
        proc = _make_processor()
        resp = IamResponse(error=Error(type="auth-failed", message="no"))
        proc.iam = MagicMock()
        proc.iam.handle = AsyncMock(return_value=resp)

        req = IamRequest(operation="authenticate-anonymous")
        await proc.on_iam_request(_make_msg(req), None, None)

        event_type, payload = proc.audit.emit.call_args[0]
        assert event_type == "iam.authenticate"
        assert payload["credential_type"] == "anonymous"
        assert payload["outcome"] == "failure"


# ---------------------------------------------------------------------------
# Authorise events
# ---------------------------------------------------------------------------

class TestAuthoriseAuditEvents:

    @pytest.mark.asyncio
    async def test_authorise_allow(self):
        proc = _make_processor()
        resp = IamResponse(decision_allow=True, decision_ttl_seconds=60)
        proc.iam = MagicMock()
        proc.iam.handle = AsyncMock(return_value=resp)

        req = IamRequest(
            operation="authorise",
            user_id="user-1",
            capability="config:read",
            resource_json='{"workspace": "production"}',
            request_id="req-4",
        )
        await proc.on_iam_request(_make_msg(req), None, None)

        event_type, payload = proc.audit.emit.call_args[0]
        assert event_type == "iam.authorise"
        assert payload["outcome"] == "allow"
        assert payload["capability"] == "config:read"
        assert payload["identity"] == "user-1"
        assert payload["workspace"] == "production"
        assert "denial_reason" not in payload

    @pytest.mark.asyncio
    async def test_authorise_deny(self):
        proc = _make_processor()
        resp = IamResponse(decision_allow=False, decision_ttl_seconds=5)
        proc.iam = MagicMock()
        proc.iam.handle = AsyncMock(return_value=resp)

        req = IamRequest(
            operation="authorise",
            user_id="user-2",
            capability="users:admin",
            resource_json='{}',
            request_id="req-5",
        )
        await proc.on_iam_request(_make_msg(req), None, None)

        _, payload = proc.audit.emit.call_args[0]
        assert payload["outcome"] == "deny"
        assert payload["denial_reason"] == "capability-not-in-role"

    @pytest.mark.asyncio
    async def test_authorise_extracts_workspace_from_resource_json(self):
        proc = _make_processor()
        resp = IamResponse(decision_allow=True, decision_ttl_seconds=60)
        proc.iam = MagicMock()
        proc.iam.handle = AsyncMock(return_value=resp)

        req = IamRequest(
            operation="authorise",
            user_id="user-1",
            capability="graph-rag:query",
            resource_json='{"workspace": "engineering"}',
        )
        await proc.on_iam_request(_make_msg(req), None, None)

        _, payload = proc.audit.emit.call_args[0]
        assert payload["workspace"] == "engineering"

    @pytest.mark.asyncio
    async def test_authorise_omits_empty_workspace(self):
        proc = _make_processor()
        resp = IamResponse(decision_allow=True, decision_ttl_seconds=60)
        proc.iam = MagicMock()
        proc.iam.handle = AsyncMock(return_value=resp)

        req = IamRequest(
            operation="authorise",
            user_id="user-1",
            capability="metrics:read",
            resource_json='{}',
        )
        await proc.on_iam_request(_make_msg(req), None, None)

        _, payload = proc.audit.emit.call_args[0]
        assert "workspace" not in payload


# ---------------------------------------------------------------------------
# Management events
# ---------------------------------------------------------------------------

class TestManagementAuditEvents:

    @pytest.mark.asyncio
    async def test_create_user_emits_management(self):
        proc = _make_processor()
        resp = IamResponse()
        proc.iam = MagicMock()
        proc.iam.handle = AsyncMock(return_value=resp)

        req = IamRequest(
            operation="create-user",
            actor="admin-1",
            user_id="new-user",
            workspace="default",
            request_id="req-6",
        )
        await proc.on_iam_request(_make_msg(req), None, None)

        event_type, payload = proc.audit.emit.call_args[0]
        assert event_type == "iam.management"
        assert payload["operation"] == "create-user"
        assert payload["actor"] == "admin-1"
        assert payload["target_identity"] == "new-user"
        assert payload["target_workspace"] == "default"
        assert payload["outcome"] == "success"

    @pytest.mark.asyncio
    async def test_revoke_api_key_emits_management(self):
        proc = _make_processor()
        resp = IamResponse()
        proc.iam = MagicMock()
        proc.iam.handle = AsyncMock(return_value=resp)

        req = IamRequest(
            operation="revoke-api-key",
            actor="admin-1",
            key_id="key-abc",
            workspace="production",
            request_id="req-7",
        )
        await proc.on_iam_request(_make_msg(req), None, None)

        event_type, payload = proc.audit.emit.call_args[0]
        assert event_type == "iam.management"
        assert payload["operation"] == "revoke-api-key"
        assert payload["outcome"] == "success"

    @pytest.mark.asyncio
    async def test_management_error_outcome(self):
        proc = _make_processor()
        resp = IamResponse(
            error=Error(type="not-found", message="user not found"),
        )
        proc.iam = MagicMock()
        proc.iam.handle = AsyncMock(return_value=resp)

        req = IamRequest(
            operation="delete-user",
            actor="admin-1",
            user_id="ghost",
        )
        await proc.on_iam_request(_make_msg(req), None, None)

        _, payload = proc.audit.emit.call_args[0]
        assert payload["outcome"] == "error"

    @pytest.mark.asyncio
    async def test_management_omits_empty_target_fields(self):
        proc = _make_processor()
        resp = IamResponse()
        proc.iam = MagicMock()
        proc.iam.handle = AsyncMock(return_value=resp)

        req = IamRequest(
            operation="rotate-signing-key",
            actor="admin-1",
        )
        await proc.on_iam_request(_make_msg(req), None, None)

        _, payload = proc.audit.emit.call_args[0]
        assert "target_identity" not in payload
        assert "target_workspace" not in payload


# ---------------------------------------------------------------------------
# Non-audited operations
# ---------------------------------------------------------------------------

class TestNonAuditedOperations:

    @pytest.mark.asyncio
    async def test_whoami_does_not_emit(self):
        proc = _make_processor()
        resp = IamResponse()
        proc.iam = MagicMock()
        proc.iam.handle = AsyncMock(return_value=resp)

        req = IamRequest(operation="whoami", actor="user-1")
        await proc.on_iam_request(_make_msg(req), None, None)

        proc.audit.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_users_does_not_emit(self):
        proc = _make_processor()
        resp = IamResponse()
        proc.iam = MagicMock()
        proc.iam.handle = AsyncMock(return_value=resp)

        req = IamRequest(operation="list-users", workspace="default")
        await proc.on_iam_request(_make_msg(req), None, None)

        proc.audit.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_signing_key_does_not_emit(self):
        proc = _make_processor()
        resp = IamResponse(signing_key_public="PEM...")
        proc.iam = MagicMock()
        proc.iam.handle = AsyncMock(return_value=resp)

        req = IamRequest(operation="get-signing-key-public")
        await proc.on_iam_request(_make_msg(req), None, None)

        proc.audit.emit.assert_not_called()
