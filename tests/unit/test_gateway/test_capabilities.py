"""
Tests for gateway/capabilities.py — the thin authorisation surface
under the IAM contract.

The gateway no longer holds policy state (roles, capability sets,
workspace scopes); those live in iam-svc.  These tests cover only
what the gateway shim does itself: PUBLIC / AUTHENTICATED short-
circuiting, default-fill of workspace, and forwarding of capability
checks to ``auth.authorise``.
"""

import pytest
from aiohttp import web
from unittest.mock import AsyncMock, MagicMock

from trustgraph.gateway.capabilities import (
    PUBLIC, AUTHENTICATED,
    enforce, enforce_workspace,
    access_denied, auth_failure,
)


# -- test fixtures ---------------------------------------------------------


class _Identity:
    """Stand-in for auth.Identity — under the IAM contract it has
    just ``handle``, ``workspace``, ``principal_id``, ``source``."""

    def __init__(self, handle="user-1", workspace="default"):
        self.handle = handle
        self.workspace = workspace
        self.principal_id = handle
        self.source = "api-key"


def _allow_auth(identity=None, workspaces=None):
    """Build an Auth double that authenticates to ``identity`` and
    allows every authorise() call."""
    auth = MagicMock()
    auth.authenticate = AsyncMock(
        return_value=identity or _Identity(),
    )
    auth.authorise = AsyncMock(return_value=None)
    auth.known_workspaces = workspaces or {"default", "acme"}
    return auth


def _deny_auth(identity=None, workspaces=None):
    """Build an Auth double that authenticates but denies authorise."""
    auth = MagicMock()
    auth.authenticate = AsyncMock(
        return_value=identity or _Identity(),
    )
    auth.authorise = AsyncMock(side_effect=access_denied())
    auth.known_workspaces = workspaces or {"default", "acme"}
    return auth


# -- enforce() -------------------------------------------------------------


class TestEnforce:

    @pytest.mark.asyncio
    async def test_public_returns_none_no_auth(self):
        auth = _allow_auth()
        result = await enforce(MagicMock(), auth, PUBLIC)
        assert result is None
        auth.authenticate.assert_not_called()
        auth.authorise.assert_not_called()

    @pytest.mark.asyncio
    async def test_authenticated_skips_authorise(self):
        identity = _Identity()
        auth = _allow_auth(identity)
        result = await enforce(MagicMock(), auth, AUTHENTICATED)
        assert result is identity
        auth.authenticate.assert_awaited_once()
        auth.authorise.assert_not_called()

    @pytest.mark.asyncio
    async def test_capability_calls_authorise_system_level(self):
        identity = _Identity()
        auth = _allow_auth(identity)
        result = await enforce(MagicMock(), auth, "graph:read")
        assert result is identity
        auth.authorise.assert_awaited_once_with(
            identity, "graph:read", {}, {},
        )

    @pytest.mark.asyncio
    async def test_capability_denied_raises_forbidden(self):
        auth = _deny_auth()
        with pytest.raises(web.HTTPForbidden):
            await enforce(MagicMock(), auth, "users:admin")


# -- enforce_workspace() ---------------------------------------------------


class TestEnforceWorkspace:

    @pytest.mark.asyncio
    async def test_default_fills_from_identity(self):
        data = {"operation": "x"}
        auth = _allow_auth()
        await enforce_workspace(data, _Identity(workspace="default"), auth)
        assert data["workspace"] == "default"

    @pytest.mark.asyncio
    async def test_caller_supplied_workspace_kept(self):
        data = {"workspace": "acme", "operation": "x"}
        auth = _allow_auth()
        await enforce_workspace(data, _Identity(workspace="default"), auth)
        assert data["workspace"] == "acme"

    @pytest.mark.asyncio
    async def test_no_capability_skips_authorise(self):
        data = {"workspace": "default"}
        auth = _allow_auth()
        await enforce_workspace(data, _Identity(), auth)
        auth.authorise.assert_not_called()

    @pytest.mark.asyncio
    async def test_capability_calls_authorise_with_resource(self):
        data = {"workspace": "acme"}
        identity = _Identity()
        auth = _allow_auth(identity)
        await enforce_workspace(
            data, identity, auth, capability="graph:read",
        )
        auth.authorise.assert_awaited_once_with(
            identity, "graph:read", {"workspace": "acme"}, {},
        )

    @pytest.mark.asyncio
    async def test_capability_denied_propagates(self):
        data = {"workspace": "acme"}
        auth = _deny_auth()
        with pytest.raises(web.HTTPForbidden):
            await enforce_workspace(
                data, _Identity(), auth, capability="users:admin",
            )

    @pytest.mark.asyncio
    async def test_non_dict_passthrough(self):
        auth = _allow_auth()
        result = await enforce_workspace("not-a-dict", _Identity(), auth)
        assert result == "not-a-dict"
        auth.authorise.assert_not_called()


# -- helpers ---------------------------------------------------------------


class TestResponseHelpers:

    def test_auth_failure_is_401(self):
        exc = auth_failure()
        assert exc.status == 401
        assert "auth failure" in exc.text

    def test_access_denied_is_403(self):
        exc = access_denied()
        assert exc.status == 403
        assert "access denied" in exc.text


class TestSentinels:

    def test_public_and_authenticated_are_distinct(self):
        assert PUBLIC != AUTHENTICATED
