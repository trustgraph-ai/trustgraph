"""
Contract test: the full iam-svc MUST reject authenticate-anonymous.

This is a safety pin — if someone accidentally adds anonymous access
to the production IAM handler, this test catches it.
"""

import asyncio
from unittest.mock import Mock, AsyncMock

import pytest

from trustgraph.iam.service.iam import IamService


def _make_request(**kwargs):
    req = Mock()
    for k, v in kwargs.items():
        setattr(req, k, v)
    return req


class TestIamRejectsAnonymous:

    @pytest.fixture
    def handler(self):
        svc = object.__new__(IamService)
        svc.table_store = Mock(spec=[])
        svc.bootstrap_mode = "token"
        svc.bootstrap_token = "tok"
        svc._on_workspace_created = None
        svc._on_workspace_deleted = None
        svc._signing_key = None
        svc._signing_key_lock = asyncio.Lock()
        return svc

    @pytest.mark.asyncio
    async def test_authenticate_anonymous_returns_auth_failed(self, handler):
        resp = await handler.handle(
            _make_request(operation="authenticate-anonymous")
        )
        assert resp.error is not None
        assert resp.error.type == "auth-failed"
        assert "anonymous" in resp.error.message.lower()
