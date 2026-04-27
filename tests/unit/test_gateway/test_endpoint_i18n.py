"""Tests for Gateway i18n pack endpoint."""

import json
from unittest.mock import MagicMock

import pytest
from aiohttp import web

from trustgraph.gateway.endpoint.i18n import I18nPackEndpoint


class TestI18nPackEndpoint:

    def test_i18n_endpoint_initialization(self):
        mock_auth = MagicMock()

        endpoint = I18nPackEndpoint(
            endpoint_path="/api/v1/i18n/packs/{lang}",
            auth=mock_auth,
        )

        assert endpoint.path == "/api/v1/i18n/packs/{lang}"
        assert endpoint.auth == mock_auth
        assert endpoint.operation == "service"

    @pytest.mark.asyncio
    async def test_i18n_endpoint_start_method(self):
        mock_auth = MagicMock()
        endpoint = I18nPackEndpoint("/api/v1/i18n/packs/{lang}", mock_auth)
        await endpoint.start()

    def test_add_routes_registers_get_handler(self):
        mock_auth = MagicMock()
        mock_app = MagicMock()

        endpoint = I18nPackEndpoint("/api/v1/i18n/packs/{lang}", mock_auth)
        endpoint.add_routes(mock_app)

        mock_app.add_routes.assert_called_once()
        call_args = mock_app.add_routes.call_args[0][0]
        assert len(call_args) == 1

    @pytest.mark.asyncio
    async def test_handle_unauthorized_on_invalid_auth_scheme(self):
        mock_auth = MagicMock()
        mock_auth.permitted.return_value = True

        endpoint = I18nPackEndpoint("/api/v1/i18n/packs/{lang}", mock_auth)

        request = MagicMock()
        request.path = "/api/v1/i18n/packs/en"
        request.headers = {"Authorization": "Token abc"}
        request.match_info = {"lang": "en"}

        resp = await endpoint.handle(request)
        assert isinstance(resp, web.HTTPUnauthorized)

    @pytest.mark.asyncio
    async def test_handle_returns_pack_when_permitted(self):
        mock_auth = MagicMock()
        mock_auth.permitted.return_value = True

        endpoint = I18nPackEndpoint("/api/v1/i18n/packs/{lang}", mock_auth)

        request = MagicMock()
        request.path = "/api/v1/i18n/packs/en"
        request.headers = {}
        request.match_info = {"lang": "en"}

        resp = await endpoint.handle(request)

        assert resp.status == 200
        payload = json.loads(resp.body.decode("utf-8"))
        assert isinstance(payload, dict)
        assert "cli.verify_system_status.title" in payload
