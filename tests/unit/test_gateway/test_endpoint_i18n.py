"""Tests for Gateway i18n pack endpoint.

Production registers this endpoint with ``capability=PUBLIC``: the
login UI needs to render its own i18n strings before any user has
authenticated, so the endpoint is deliberately pre-auth.  These
tests exercise the PUBLIC configuration — that is the production
contract.  Behaviour of authenticated endpoints is covered by the
IamAuth tests in ``test_auth.py``.
"""

import json
from unittest.mock import MagicMock

import pytest
from aiohttp import web

from trustgraph.gateway.endpoint.i18n import I18nPackEndpoint
from trustgraph.gateway.capabilities import PUBLIC


class TestI18nPackEndpoint:

    def test_i18n_endpoint_initialization(self):
        mock_auth = MagicMock()

        endpoint = I18nPackEndpoint(
            endpoint_path="/api/v1/i18n/packs/{lang}",
            auth=mock_auth,
            capability=PUBLIC,
        )

        assert endpoint.path == "/api/v1/i18n/packs/{lang}"
        assert endpoint.auth == mock_auth
        assert endpoint.capability == PUBLIC

    @pytest.mark.asyncio
    async def test_i18n_endpoint_start_method(self):
        mock_auth = MagicMock()
        endpoint = I18nPackEndpoint(
            "/api/v1/i18n/packs/{lang}", mock_auth, capability=PUBLIC,
        )
        await endpoint.start()

    def test_add_routes_registers_get_handler(self):
        mock_auth = MagicMock()
        mock_app = MagicMock()

        endpoint = I18nPackEndpoint(
            "/api/v1/i18n/packs/{lang}", mock_auth, capability=PUBLIC,
        )
        endpoint.add_routes(mock_app)

        mock_app.add_routes.assert_called_once()
        call_args = mock_app.add_routes.call_args[0][0]
        assert len(call_args) == 1

    @pytest.mark.asyncio
    async def test_handle_returns_pack_without_authenticating(self):
        """The PUBLIC endpoint serves the language pack without
        invoking the auth handler at all — pre-login UI must be
        reachable.  The test uses an auth mock that raises if
        touched, so any auth attempt by the endpoint is caught."""
        mock_auth = MagicMock()

        def _should_not_be_called(*args, **kwargs):
            raise AssertionError(
                "PUBLIC endpoint must not invoke auth.authenticate"
            )
        mock_auth.authenticate = _should_not_be_called

        endpoint = I18nPackEndpoint(
            "/api/v1/i18n/packs/{lang}", mock_auth, capability=PUBLIC,
        )

        request = MagicMock()
        request.path = "/api/v1/i18n/packs/en"
        # A caller-supplied Authorization header of any form should
        # be ignored — PUBLIC means we don't look at it.
        request.headers = {"Authorization": "Token abc"}
        request.match_info = {"lang": "en"}

        resp = await endpoint.handle(request)

        assert resp.status == 200
        payload = json.loads(resp.body.decode("utf-8"))
        assert isinstance(payload, dict)
        assert "cli.verify_system_status.title" in payload

    @pytest.mark.asyncio
    async def test_handle_rejects_path_traversal(self):
        """The ``lang`` path parameter is reflected through to the
        filesystem-backed pack loader.  The endpoint contains an
        explicit defense against ``/`` and ``..`` in the value; this
        test pins that defense in place."""
        mock_auth = MagicMock()
        endpoint = I18nPackEndpoint(
            "/api/v1/i18n/packs/{lang}", mock_auth, capability=PUBLIC,
        )

        for bad in ("../../etc/passwd", "en/../fr", "a/b"):
            request = MagicMock()
            request.path = f"/api/v1/i18n/packs/{bad}"
            request.headers = {}
            request.match_info = {"lang": bad}

            resp = await endpoint.handle(request)
            assert isinstance(resp, web.HTTPBadRequest), (
                f"path-traversal defense did not reject lang={bad!r}"
            )
