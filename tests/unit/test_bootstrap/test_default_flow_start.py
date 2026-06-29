"""
Unit tests for trustgraph.bootstrap.initialisers.DefaultFlowStart

Verifies the list/start timeouts are configurable and that the
configured values actually reach the flow-client request calls.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from trustgraph.bootstrap.initialisers.default_flow_start import (
    DefaultFlowStart,
)


def test_default_timeouts():
    init = DefaultFlowStart(blueprint="bp")
    assert init.list_timeout == 10
    assert init.start_timeout == 30


def test_timeout_overrides_are_stored():
    init = DefaultFlowStart(blueprint="bp", list_timeout=5, start_timeout=99)
    assert init.list_timeout == 5
    assert init.start_timeout == 99


@pytest.mark.asyncio
async def test_run_forwards_configured_timeouts():
    init = DefaultFlowStart(blueprint="bp", list_timeout=5, start_timeout=99)

    # Flow client: list-flows returns no error + empty flow list,
    # start-flow returns no error.
    flow = MagicMock()
    flow.start = AsyncMock()
    flow.stop = AsyncMock()
    flow.request = AsyncMock(side_effect=[
        MagicMock(error=None, flow_ids=[]),  # list-flows response
        MagicMock(error=None),               # start-flow response
    ])

    # Context: workspace "default" exists, hands back our mock flow client.
    ctx = MagicMock()
    ctx.logger = MagicMock()
    ctx.config.keys = AsyncMock(return_value=["default"])
    ctx.make_flow_client = MagicMock(return_value=flow)

    await init.run(ctx, None, "v1")

    calls = flow.request.call_args_list
    assert len(calls) == 2
    assert calls[0].kwargs["timeout"] == 5
    assert calls[1].kwargs["timeout"] == 99
