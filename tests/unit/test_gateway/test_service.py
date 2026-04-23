"""
Tests for gateway/service.py — the Api class that wires together
the pub/sub backend, IAM auth, config receiver, dispatcher manager,
and endpoint manager.

The legacy ``GATEWAY_SECRET`` / ``default_api_token`` / allow-all
surface is gone, so the tests here focus on the Api's construction
and composition rather than the removed auth behaviour.  IamAuth's
own behaviour is covered in test_auth.py.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from aiohttp import web

from trustgraph.gateway.service import (
    Api,
    default_pulsar_host, default_prometheus_url,
    default_timeout, default_port,
)
from trustgraph.gateway.auth import IamAuth


# -- constants -------------------------------------------------------------


class TestDefaults:

    def test_exports_default_constants(self):
        # These are consumed by CLIs / tests / docs.  Sanity-check
        # that they're the expected shape.
        assert default_port == 8088
        assert default_timeout == 600
        assert default_pulsar_host.startswith("pulsar://")
        assert default_prometheus_url.startswith("http")


# -- Api construction ------------------------------------------------------


@pytest.fixture
def mock_backend():
    return Mock()


@pytest.fixture
def api(mock_backend):
    with patch(
        "trustgraph.gateway.service.get_pubsub",
        return_value=mock_backend,
    ):
        yield Api()


class TestApiConstruction:

    def test_defaults(self, api):
        assert api.port == default_port
        assert api.timeout == default_timeout
        assert api.pulsar_host == default_pulsar_host
        assert api.pulsar_api_key is None
        # prometheus_url gets normalised with a trailing slash
        assert api.prometheus_url == default_prometheus_url + "/"

    def test_auth_is_iam_backed(self, api):
        # Any Api always gets an IamAuth.  There is no "no auth" mode
        # (GATEWAY_SECRET / allow_all has been removed — see IAM spec).
        assert isinstance(api.auth, IamAuth)

    def test_components_wired(self, api):
        assert api.config_receiver is not None
        assert api.dispatcher_manager is not None
        assert api.endpoint_manager is not None

    def test_dispatcher_manager_has_auth(self, api):
        # The Mux uses this handle for first-frame socket auth.
        assert api.dispatcher_manager.auth is api.auth

    def test_custom_config(self, mock_backend):
        config = {
            "port": 9000,
            "timeout": 300,
            "pulsar_host": "pulsar://custom-host:6650",
            "pulsar_api_key": "custom-key",
            "prometheus_url": "http://custom-prometheus:9090",
        }
        with patch(
            "trustgraph.gateway.service.get_pubsub",
            return_value=mock_backend,
        ):
            a = Api(**config)

        assert a.port == 9000
        assert a.timeout == 300
        assert a.pulsar_host == "pulsar://custom-host:6650"
        assert a.pulsar_api_key == "custom-key"
        # Trailing slash added.
        assert a.prometheus_url == "http://custom-prometheus:9090/"

    def test_prometheus_url_already_has_trailing_slash(self, mock_backend):
        with patch(
            "trustgraph.gateway.service.get_pubsub",
            return_value=mock_backend,
        ):
            a = Api(prometheus_url="http://p:9090/")
        assert a.prometheus_url == "http://p:9090/"

    def test_queue_overrides_parsed_for_config(self, mock_backend):
        with patch(
            "trustgraph.gateway.service.get_pubsub",
            return_value=mock_backend,
        ):
            a = Api(
                config_request_queue="alt-config-req",
                config_response_queue="alt-config-resp",
            )
        overrides = a.dispatcher_manager.queue_overrides
        assert overrides.get("config", {}).get("request") == "alt-config-req"
        assert overrides.get("config", {}).get("response") == "alt-config-resp"


# -- app_factory -----------------------------------------------------------


class TestAppFactory:

    @pytest.mark.asyncio
    async def test_creates_aiohttp_app(self, api):
        # Stub out the long-tail dependencies that reach out to IAM /
        # pub/sub so we can exercise the factory in isolation.
        api.auth.start = AsyncMock()
        api.config_receiver = Mock()
        api.config_receiver.start = AsyncMock()
        api.endpoint_manager = Mock()
        api.endpoint_manager.add_routes = Mock()
        api.endpoint_manager.start = AsyncMock()
        api.endpoints = []

        app = await api.app_factory()

        assert isinstance(app, web.Application)
        assert app._client_max_size == 256 * 1024 * 1024
        api.auth.start.assert_called_once()
        api.config_receiver.start.assert_called_once()
        api.endpoint_manager.add_routes.assert_called_once_with(app)
        api.endpoint_manager.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_auth_start_runs_before_accepting_traffic(self, api):
        """``auth.start()`` fetches the IAM signing key, and must
        complete (or time out) before the gateway begins accepting
        requests.  It's the first await in app_factory."""
        order = []

        # AsyncMock.side_effect expects a sync callable (its return
        # value becomes the coroutine's return); a plain list.append
        # avoids the "coroutine was never awaited" trap of an async
        # side_effect.
        api.auth.start = AsyncMock(
            side_effect=lambda: order.append("auth"),
        )
        api.config_receiver = Mock()
        api.config_receiver.start = AsyncMock(
            side_effect=lambda: order.append("config"),
        )
        api.endpoint_manager = Mock()
        api.endpoint_manager.add_routes = Mock()
        api.endpoint_manager.start = AsyncMock(
            side_effect=lambda: order.append("endpoints"),
        )
        api.endpoints = []

        await api.app_factory()

        # auth.start must be first (before config receiver, before
        # any endpoint starts).
        assert order[0] == "auth"
        # All three must have run.
        assert set(order) == {"auth", "config", "endpoints"}
