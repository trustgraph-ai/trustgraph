"""
Unit tests for trustgraph.base.request_response_spec RequestResponse
Testing default_timeout resolution in request()
"""

import inspect
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

from trustgraph.base.request_response_spec import RequestResponse


def _bare_client(default_timeout):
    """RequestResponse with the pub/sub machinery stubbed out."""
    rr = RequestResponse.__new__(RequestResponse)
    rr.default_timeout = default_timeout
    rr.subscribe = AsyncMock(return_value=MagicMock())
    rr.unsubscribe = AsyncMock()
    rr.producer = AsyncMock()
    return rr


class TestRequestResponseTimeout(IsolatedAsyncioTestCase):

    def test_constructor_default_preserves_prior_behaviour(self):
        sig = inspect.signature(RequestResponse.__init__)
        assert sig.parameters["default_timeout"].default == 300

    async def test_request_resolves_none_to_default_timeout(self):
        rr = _bare_client(default_timeout=45)

        with patch(
            'trustgraph.base.request_response_spec.asyncio.wait_for',
            new_callable=AsyncMock,
            return_value="resp",
        ) as mock_wait:
            result = await rr.request("req")

        assert result == "resp"
        assert mock_wait.call_args.kwargs["timeout"] == 45

    async def test_request_explicit_timeout_wins(self):
        rr = _bare_client(default_timeout=45)

        with patch(
            'trustgraph.base.request_response_spec.asyncio.wait_for',
            new_callable=AsyncMock,
            return_value="resp",
        ) as mock_wait:
            result = await rr.request("req", timeout=7)

        assert result == "resp"
        assert mock_wait.call_args.kwargs["timeout"] == 7
