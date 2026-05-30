"""
Tests for the no-auth IAM handler.

Verifies that NoAuthHandler returns the expected permissive responses
and that the always-allow authorise path returns the correct shape.
"""

import json
from unittest.mock import Mock

import pytest

from trustgraph.iam.noauth.handler import NoAuthHandler


def _make_request(**kwargs):
    req = Mock()
    for k, v in kwargs.items():
        setattr(req, k, v)
    return req


class TestAuthenticateAnonymous:

    @pytest.mark.asyncio
    async def test_returns_default_identity(self):
        h = NoAuthHandler(
            default_user_id="anon", default_workspace="ws",
        )
        resp = await h.handle(
            _make_request(operation="authenticate-anonymous")
        )
        assert resp.error is None
        assert resp.resolved_user_id == "anon"
        assert resp.resolved_workspace == "ws"
        assert "admin" in list(resp.resolved_roles)

    @pytest.mark.asyncio
    async def test_custom_defaults_propagate(self):
        h = NoAuthHandler(
            default_user_id="dev-user", default_workspace="dev-ws",
        )
        resp = await h.handle(
            _make_request(operation="authenticate-anonymous")
        )
        assert resp.resolved_user_id == "dev-user"
        assert resp.resolved_workspace == "dev-ws"


class TestResolveApiKey:

    @pytest.mark.asyncio
    async def test_any_key_resolves_to_default_identity(self):
        h = NoAuthHandler()
        resp = await h.handle(
            _make_request(operation="resolve-api-key", api_key="tg_bogus")
        )
        assert resp.error is None
        assert resp.resolved_user_id == "anonymous"
        assert resp.resolved_workspace == "default"


class TestAuthorise:

    @pytest.mark.asyncio
    async def test_always_allows(self):
        h = NoAuthHandler()
        resp = await h.handle(
            _make_request(
                operation="authorise",
                user_id="anyone",
                capability="anything",
                resource_json="{}",
                parameters_json="{}",
            )
        )
        assert resp.error is None
        assert resp.decision_allow is True
        assert resp.decision_ttl_seconds > 0

    @pytest.mark.asyncio
    async def test_authorise_many_returns_matching_count(self):
        h = NoAuthHandler()
        checks = [
            {"capability": "a", "resource": {}, "parameters": {}},
            {"capability": "b", "resource": {}, "parameters": {}},
            {"capability": "c", "resource": {}, "parameters": {}},
        ]
        resp = await h.handle(
            _make_request(
                operation="authorise-many",
                user_id="u",
                authorise_checks=json.dumps(checks),
            )
        )
        assert resp.error is None
        decisions = json.loads(resp.decisions_json)
        assert len(decisions) == 3
        assert all(d["allow"] is True for d in decisions)


class TestCreateWorkspaceCallback:

    @pytest.mark.asyncio
    async def test_create_workspace_calls_callback(self):
        called_with = []

        async def on_created(ws_id):
            called_with.append(ws_id)

        h = NoAuthHandler(on_workspace_created=on_created)
        req = _make_request(operation="create-workspace")
        req.workspace_record = Mock()
        req.workspace_record.id = "test-ws"
        resp = await h.handle(req)
        assert resp.error is None
        assert called_with == ["test-ws"]

    @pytest.mark.asyncio
    async def test_create_workspace_without_callback_still_succeeds(self):
        h = NoAuthHandler()
        req = _make_request(operation="create-workspace")
        req.workspace_record = Mock()
        req.workspace_record.id = "test-ws"
        resp = await h.handle(req)
        assert resp.error is None


class TestUnknownOperation:

    @pytest.mark.asyncio
    async def test_unknown_op_returns_error(self):
        h = NoAuthHandler()
        resp = await h.handle(
            _make_request(operation="not-a-real-op")
        )
        assert resp.error is not None
        assert resp.error.type == "invalid-argument"
