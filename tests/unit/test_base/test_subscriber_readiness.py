"""
Regression tests for Subscriber.start() readiness barrier.

Background: prior to the eager-connect fix, Subscriber.start() created
the run() task and returned immediately. The underlying backend consumer
was lazily connected on its first receive() call, which left a setup
race for request/response clients using ephemeral per-subscriber response
queues (RabbitMQ auto-delete exclusive queues): the request would be
published before the response queue was bound, and the broker would
silently drop the reply. fetch_config(), document-embeddings, and
api-gateway all hit this with "Failed to fetch config on notify" /
"Request timeout exception" symptoms.

These tests pin the readiness contract:

    await subscriber.start()
    # at this point, consumer.ensure_connected() MUST have run

so that any future change which removes the eager bind, or moves it
back to lazy initialisation, fails CI loudly.
"""

import asyncio

import pytest
from unittest.mock import MagicMock

from trustgraph.base.subscriber import Subscriber


def _make_backend(ensure_connected_side_effect=None,
                  receive_side_effect=None):
    """Build a fake backend whose consumer records ensure_connected /
    receive calls. ensure_connected_side_effect lets a test inject a
    delay or exception."""
    backend = MagicMock()
    consumer = MagicMock()

    consumer.ensure_connected = MagicMock(
        side_effect=ensure_connected_side_effect,
    )

    # By default receive raises a timeout-style exception that the
    # subscriber loop is supposed to swallow as a "no message yet" — this
    # keeps the subscriber idling cleanly while the test inspects state.
    if receive_side_effect is None:
        receive_side_effect = TimeoutError("No message received within timeout")
    consumer.receive = MagicMock(side_effect=receive_side_effect)

    consumer.acknowledge = MagicMock()
    consumer.negative_acknowledge = MagicMock()
    consumer.pause_message_listener = MagicMock()
    consumer.unsubscribe = MagicMock()
    consumer.close = MagicMock()

    backend.create_consumer.return_value = consumer
    return backend, consumer


def _make_subscriber(backend):
    return Subscriber(
        backend=backend,
        topic="response:tg:config",
        subscription="test-sub",
        consumer_name="test-consumer",
        schema=dict,
        max_size=10,
        drain_timeout=1.0,
        backpressure_strategy="block",
    )


class TestSubscriberReadiness:

    @pytest.mark.asyncio
    async def test_start_calls_ensure_connected_before_returning(self):
        """The barrier: ensure_connected must have been invoked at least
        once by the time start() returns."""
        backend, consumer = _make_backend()
        subscriber = _make_subscriber(backend)

        await subscriber.start()

        try:
            consumer.ensure_connected.assert_called_once()
        finally:
            await subscriber.stop()

    @pytest.mark.asyncio
    async def test_start_blocks_until_ensure_connected_completes(self):
        """If ensure_connected is slow, start() must wait for it. This is
        the actual race-condition guard — it would have failed against
        the buggy version where start() returned before run() had even
        scheduled the consumer creation."""
        connect_started = asyncio.Event()
        release_connect = asyncio.Event()

        # ensure_connected runs in the executor thread, so we need a
        # threading-safe gate. Use a simple busy-wait on a flag set by
        # the asyncio side via call_soon_threadsafe — but the simpler
        # path is to give it a sleep and observe ordering.
        import threading
        gate = threading.Event()

        def slow_connect():
            connect_started.set()  # safe: only mutates the Event flag
            gate.wait(timeout=2.0)

        backend, consumer = _make_backend(
            ensure_connected_side_effect=slow_connect,
        )
        subscriber = _make_subscriber(backend)

        start_task = asyncio.create_task(subscriber.start())

        # Wait until ensure_connected has begun executing.
        await asyncio.wait_for(connect_started.wait(), timeout=2.0)

        # ensure_connected is in flight — start() must NOT have returned.
        assert not start_task.done(), (
            "start() returned before ensure_connected() completed — "
            "the readiness barrier is broken and the request/response "
            "race condition is back."
        )

        # Release the gate; start() should now complete promptly.
        gate.set()
        await asyncio.wait_for(start_task, timeout=2.0)

        consumer.ensure_connected.assert_called_once()

        await subscriber.stop()

    @pytest.mark.asyncio
    async def test_start_propagates_consumer_creation_failure(self):
        """If create_consumer() raises, start() must surface the error
        rather than hang on the readiness future. The old code path
        retried indefinitely inside run() and never let start() unblock."""
        backend = MagicMock()
        backend.create_consumer.side_effect = RuntimeError("broker down")

        subscriber = _make_subscriber(backend)

        with pytest.raises(RuntimeError, match="broker down"):
            await asyncio.wait_for(subscriber.start(), timeout=2.0)

    @pytest.mark.asyncio
    async def test_start_propagates_ensure_connected_failure(self):
        """Same contract for an ensure_connected() that raises (e.g. the
        broker is up but the queue declare/bind fails)."""
        backend, consumer = _make_backend(
            ensure_connected_side_effect=RuntimeError("queue declare failed"),
        )
        subscriber = _make_subscriber(backend)

        with pytest.raises(RuntimeError, match="queue declare failed"):
            await asyncio.wait_for(subscriber.start(), timeout=2.0)

    @pytest.mark.asyncio
    async def test_ensure_connected_runs_before_subscriber_running_log(self):
        """Subtle ordering: ensure_connected MUST happen before the
        receive loop, so that any reply is captured. We assert this by
        checking ensure_connected was called before any receive call."""
        call_order = []

        def record_ensure():
            call_order.append("ensure_connected")

        def record_receive(*args, **kwargs):
            call_order.append("receive")
            raise TimeoutError("No message received within timeout")

        backend, consumer = _make_backend(
            ensure_connected_side_effect=record_ensure,
            receive_side_effect=record_receive,
        )
        subscriber = _make_subscriber(backend)

        await subscriber.start()

        # Give the receive loop a tick to run at least once.
        await asyncio.sleep(0.05)

        await subscriber.stop()

        # ensure_connected must come first; receive may not have happened
        # yet on a fast machine, but if it did, it must come after.
        assert call_order, "neither ensure_connected nor receive was called"
        assert call_order[0] == "ensure_connected"
