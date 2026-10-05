"""
Tests for the mint-token IAM operation.

Exercises handle_mint_token directly against a stub table store,
verifying input validation, workspace checks, and JWT production
with embedded user_context claims.
"""

import asyncio
import json
import time
from unittest.mock import Mock, AsyncMock

import pytest

from trustgraph.iam.service.iam import (
    IamService, _sign_jwt, _generate_signing_keypair,
)


def _make_service():
    svc = object.__new__(IamService)
    svc.table_store = Mock()
    svc.bootstrap_mode = "token"
    svc.bootstrap_token = "tok"
    svc._on_workspace_created = None
    svc._on_workspace_deleted = None
    svc._signing_key = None
    svc._signing_key_lock = asyncio.Lock()

    kid, priv, pub = _generate_signing_keypair()
    svc._signing_key = (kid, priv, pub)

    return svc


def _make_request(**kwargs):
    defaults = dict(
        operation="mint-token",
        user_id="",
        workspace="",
        user_context_json="",
    )
    defaults.update(kwargs)
    req = Mock()
    for k, v in defaults.items():
        setattr(req, k, v)
    return req


USER_CONTEXT = {
    "user_id": "alice",
    "roles": ["analyst"],
    "assignments": [],
    "entitlements": [],
    "organisational_units": ["research"],
    "override_authorities": [],
    "delegation": None,
    "purpose": "quarterly review",
}


class TestMintTokenValidation:

    @pytest.mark.asyncio
    async def test_missing_user_id(self):
        svc = _make_service()
        req = _make_request(
            workspace="default",
            user_context_json=json.dumps(USER_CONTEXT),
        )
        resp = await svc.handle_mint_token(req)
        assert resp.error is not None
        assert resp.error.type == "invalid-argument"
        assert "user_id" in resp.error.message

    @pytest.mark.asyncio
    async def test_missing_workspace(self):
        svc = _make_service()
        req = _make_request(
            user_id="alice",
            user_context_json=json.dumps(USER_CONTEXT),
        )
        resp = await svc.handle_mint_token(req)
        assert resp.error is not None
        assert resp.error.type == "invalid-argument"
        assert "workspace" in resp.error.message

    @pytest.mark.asyncio
    async def test_missing_user_context(self):
        svc = _make_service()
        req = _make_request(user_id="alice", workspace="default")
        resp = await svc.handle_mint_token(req)
        assert resp.error is not None
        assert resp.error.type == "invalid-argument"
        assert "user_context" in resp.error.message

    @pytest.mark.asyncio
    async def test_invalid_json_user_context(self):
        svc = _make_service()
        req = _make_request(
            user_id="alice",
            workspace="default",
            user_context_json="{not valid json",
        )
        resp = await svc.handle_mint_token(req)
        assert resp.error is not None
        assert resp.error.type == "invalid-argument"
        assert "json" in resp.error.message.lower()


class TestMintTokenWorkspaceCheck:

    @pytest.mark.asyncio
    async def test_nonexistent_workspace(self):
        svc = _make_service()
        svc.table_store.get_workspace = AsyncMock(return_value=None)
        req = _make_request(
            user_id="alice",
            workspace="ghost",
            user_context_json=json.dumps(USER_CONTEXT),
        )
        resp = await svc.handle_mint_token(req)
        assert resp.error is not None
        assert resp.error.type == "not-found"

    @pytest.mark.asyncio
    async def test_disabled_workspace(self):
        svc = _make_service()
        svc.table_store.get_workspace = AsyncMock(
            return_value=("default", "Default", False, None),
        )
        req = _make_request(
            user_id="alice",
            workspace="default",
            user_context_json=json.dumps(USER_CONTEXT),
        )
        resp = await svc.handle_mint_token(req)
        assert resp.error is not None
        assert resp.error.type == "not-found"


class TestMintTokenSuccess:

    @pytest.mark.asyncio
    async def test_returns_jwt_and_expiry(self):
        svc = _make_service()
        svc.table_store.get_workspace = AsyncMock(
            return_value=("default", "Default", True, None),
        )
        req = _make_request(
            user_id="alice",
            workspace="default",
            user_context_json=json.dumps(USER_CONTEXT),
        )
        resp = await svc.handle_mint_token(req)
        assert resp.error is None
        assert resp.jwt != ""
        assert resp.jwt_expires != ""

    @pytest.mark.asyncio
    async def test_jwt_contains_user_context_in_claims(self):
        svc = _make_service()
        svc.table_store.get_workspace = AsyncMock(
            return_value=("default", "Default", True, None),
        )
        req = _make_request(
            user_id="alice",
            workspace="default",
            user_context_json=json.dumps(USER_CONTEXT),
        )
        resp = await svc.handle_mint_token(req)

        import base64
        parts = resp.jwt.split(".")
        payload = json.loads(
            base64.urlsafe_b64decode(parts[1] + "==")
        )
        assert payload["sub"] == "alice"
        assert payload["default_workspace"] == "default"
        assert payload["user_context"] == USER_CONTEXT
        assert payload["iss"] == "trustgraph-iam"
        assert "iat" in payload
        assert "exp" in payload

    @pytest.mark.asyncio
    async def test_jwt_expiry_is_in_the_future(self):
        svc = _make_service()
        svc.table_store.get_workspace = AsyncMock(
            return_value=("default", "Default", True, None),
        )
        req = _make_request(
            user_id="alice",
            workspace="default",
            user_context_json=json.dumps(USER_CONTEXT),
        )
        resp = await svc.handle_mint_token(req)

        import base64
        parts = resp.jwt.split(".")
        payload = json.loads(
            base64.urlsafe_b64decode(parts[1] + "==")
        )
        assert payload["exp"] > time.time()


class TestMintTokenDispatch:

    @pytest.mark.asyncio
    async def test_dispatch_routes_to_handler(self):
        svc = _make_service()
        svc.table_store.get_workspace = AsyncMock(
            return_value=("default", "Default", True, None),
        )
        req = _make_request(
            user_id="alice",
            workspace="default",
            user_context_json=json.dumps(USER_CONTEXT),
        )
        resp = await svc.handle(req)
        assert resp.error is None
        assert resp.jwt != ""


class TestMintTokenCapability:

    def test_mint_token_in_admin_caps(self):
        from trustgraph.iam.service.iam import _ADMIN_CAPS
        assert "mint-token" in _ADMIN_CAPS

    def test_mint_token_not_in_reader_or_writer(self):
        from trustgraph.iam.service.iam import _READER_CAPS, _WRITER_CAPS
        assert "mint-token" not in _READER_CAPS
        assert "mint-token" not in _WRITER_CAPS
