"""
Unit tests for trustgraph.base.config_client
Testing configurable timeout behaviour
"""

from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

from trustgraph.base.config_client import ConfigClient, CONFIG_TIMEOUT


def _empty_response():
    resp = MagicMock()
    resp.error = None
    resp.values = []
    return resp


class TestConfigClientTimeout(IsolatedAsyncioTestCase):
    """Constructor timeout becomes the client default; per-call overrides."""

    @patch('trustgraph.base.request_response_spec.RequestResponse.__init__')
    async def test_default_timeout_passed_to_parent(self, mock_parent_init):
        mock_parent_init.return_value = None
        ConfigClient(backend=MagicMock(), subscription="s")

        assert mock_parent_init.call_args.kwargs["default_timeout"] \
            == CONFIG_TIMEOUT

    @patch('trustgraph.base.request_response_spec.RequestResponse.__init__')
    async def test_constructor_timeout_passed_to_parent(
            self, mock_parent_init):
        mock_parent_init.return_value = None
        ConfigClient(timeout=45, backend=MagicMock(), subscription="s")

        assert mock_parent_init.call_args.kwargs["default_timeout"] == 45

    @patch('trustgraph.base.request_response_spec.RequestResponse.__init__')
    async def test_no_timeout_defers_to_client_default(
            self, mock_parent_init):
        mock_parent_init.return_value = None
        client = ConfigClient(timeout=45)
        client.request = AsyncMock(return_value=_empty_response())

        await client.get("ws", "prompt", "k")

        # None reaches request(), which resolves it to default_timeout
        assert client.request.call_args.kwargs["timeout"] is None

    @patch('trustgraph.base.request_response_spec.RequestResponse.__init__')
    async def test_per_call_timeout_overrides(self, mock_parent_init):
        mock_parent_init.return_value = None
        client = ConfigClient(timeout=45)
        client.request = AsyncMock(return_value=_empty_response())

        await client.get("ws", "prompt", "k", timeout=7)

        assert client.request.call_args.kwargs["timeout"] == 7
