"""
Tests for Consumer concurrency: TaskGroup-based concurrent message processing,
rate-limit retry with backpressure, and message acknowledgement.
"""

import asyncio
import time

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from trustgraph.base.consumer import Consumer
from trustgraph.exceptions import TooManyRequests


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_consumer(
    concurrency=1,
    handler=None,
    rate_limit_retry_time=0.01,
    rate_limit_timeout=1,
):
    """Create a Consumer with mocked infrastructure."""
    taskgroup = MagicMock()
    flow = MagicMock()
    backend = MagicMock()
    schema = MagicMock()
    handler = handler or AsyncMock()

    consumer = Consumer(
        taskgroup=taskgroup,
        flow=flow,
        backend=backend,
        topic="test-topic",
        subscriber="test-sub",
        schema=schema,
        handler=handler,
        rate_limit_retry_time=rate_limit_retry_time,
        rate_limit_timeout=rate_limit_timeout,
        concurrency=concurrency,
    )

    return consumer


def _make_msg():
    """Create a mock Pulsar message."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Concurrency configuration tests
# ---------------------------------------------------------------------------

class TestConcurrencyConfiguration:

    def test_default_concurrency_is_1(self):
        consumer = _make_consumer()
        assert consumer.concurrency == 1

    def test_custom_concurrency(self):
        consumer = _make_consumer(concurrency=10)
        assert consumer.concurrency == 10

    def test_concurrency_stored(self):
        for n in [1, 5, 20, 100]:
            consumer = _make_consumer(concurrency=n)
            assert consumer.concurrency == n


class TestTaskGroupConcurrency:

    @pytest.mark.asyncio
    async def test_creates_n_concurrent_tasks(self):
        """consumer_run should create exactly N concurrent consume_from_queue tasks."""
        concurrency = 5
        consumer = _make_consumer(concurrency=concurrency)

        # Track how many consume_from_queue calls are made
        call_count = 0
        original_running = True

        async def mock_consume(backend_consumer):
            nonlocal call_count
            call_count += 1
            # Wait a bit to let all tasks start, then signal stop
            await asyncio.sleep(0.05)
            consumer.running = False

        consumer.consume_from_queue = mock_consume

        # Mock the backend.create_consumer
        consumer.backend.create_consumer = MagicMock(return_value=MagicMock())

        # Run consumer_run - it will create TaskGroup with N tasks
        consumer.running = True
        await consumer.consumer_run()

        assert call_count == concurrency

    @pytest.mark.asyncio
    async def test_single_concurrency_creates_one_task(self):
        """With concurrency=1, only one consume_from_queue task is created."""
        consumer = _make_consumer(concurrency=1)
        call_count = 0

        async def mock_consume(backend_consumer):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            consumer.running = False

        consumer.consume_from_queue = mock_consume
        consumer.backend.create_consumer = MagicMock(return_value=MagicMock())

        consumer.running = True
        await consumer.consumer_run()

        assert call_count == 1


# ---------------------------------------------------------------------------
# Rate-limit retry tests
# ---------------------------------------------------------------------------

class TestRateLimitRetry:

    @pytest.mark.asyncio
    async def test_rate_limit_retries_then_succeeds(self):
        """TooManyRequests should cause retry, then succeed on next attempt."""
        call_count = 0

        async def handler_with_retry(msg, consumer_ref, flow):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TooManyRequests("rate limited")
            # Second call succeeds

        consumer = _make_consumer(
            handler=handler_with_retry,
            rate_limit_retry_time=0.01,
        )
        mock_msg = _make_msg()
        consumer.consumer = MagicMock()

        await consumer.handle_one_from_queue(mock_msg, consumer.consumer)

        assert call_count == 2
        consumer.consumer.acknowledge.assert_called_once_with(mock_msg)

    @pytest.mark.asyncio
    async def test_rate_limit_timeout_negative_acks(self):
        """If rate limit retries exhaust the timeout, message is negative-acked."""
        async def always_rate_limited(msg, consumer_ref, flow):
            raise TooManyRequests("rate limited")

        consumer = _make_consumer(
            handler=always_rate_limited,
            rate_limit_retry_time=0.01,
            rate_limit_timeout=0.05,
        )
        mock_msg = _make_msg()
        consumer.consumer = MagicMock()

        await consumer.handle_one_from_queue(mock_msg, consumer.consumer)

        consumer.consumer.negative_acknowledge.assert_called_with(mock_msg)
        consumer.consumer.acknowledge.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_rate_limit_error_negative_acks_immediately(self):
        """Non-TooManyRequests errors should negative-ack immediately (no retry)."""
        call_count = 0

        async def failing_handler(msg, consumer_ref, flow):
            nonlocal call_count
            call_count += 1
            raise ValueError("bad data")

        consumer = _make_consumer(handler=failing_handler)
        mock_msg = _make_msg()
        consumer.consumer = MagicMock()

        await consumer.handle_one_from_queue(mock_msg, consumer.consumer)

        assert call_count == 1
        consumer.consumer.negative_acknowledge.assert_called_once_with(mock_msg)

    @pytest.mark.asyncio
    async def test_successful_message_acknowledged(self):
        """Successfully processed messages are acknowledged."""
        consumer = _make_consumer(handler=AsyncMock())
        mock_msg = _make_msg()
        consumer.consumer = MagicMock()

        await consumer.handle_one_from_queue(mock_msg, consumer.consumer)

        consumer.consumer.acknowledge.assert_called_once_with(mock_msg)


# ---------------------------------------------------------------------------
# Metrics integration
# ---------------------------------------------------------------------------

class TestMetricsIntegration:

    @pytest.mark.asyncio
    async def test_success_metric_on_success(self):
        consumer = _make_consumer(handler=AsyncMock())
        mock_msg = _make_msg()
        consumer.consumer = MagicMock()

        mock_metrics = MagicMock()
        mock_metrics.record_time.return_value.__enter__ = MagicMock()
        mock_metrics.record_time.return_value.__exit__ = MagicMock()
        consumer.metrics = mock_metrics

        await consumer.handle_one_from_queue(mock_msg, consumer.consumer)

        mock_metrics.process.assert_called_once_with("success")

    @pytest.mark.asyncio
    async def test_error_metric_on_failure(self):
        async def failing(msg, c, f):
            raise ValueError("fail")

        consumer = _make_consumer(handler=failing)
        mock_msg = _make_msg()
        consumer.consumer = MagicMock()

        mock_metrics = MagicMock()
        consumer.metrics = mock_metrics

        await consumer.handle_one_from_queue(mock_msg, consumer.consumer)

        mock_metrics.process.assert_called_once_with("error")

    @pytest.mark.asyncio
    async def test_rate_limit_metric_on_too_many_requests(self):
        call_count = 0

        async def handler(msg, c, f):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TooManyRequests("limited")

        consumer = _make_consumer(
            handler=handler,
            rate_limit_retry_time=0.01,
        )
        mock_msg = _make_msg()
        consumer.consumer = MagicMock()

        mock_metrics = MagicMock()
        mock_metrics.record_time.return_value.__enter__ = MagicMock()
        mock_metrics.record_time.return_value.__exit__ = MagicMock(return_value=False)
        consumer.metrics = mock_metrics

        await consumer.handle_one_from_queue(mock_msg, consumer.consumer)

        mock_metrics.rate_limit.assert_called_once()


# ---------------------------------------------------------------------------
# Poll timeout
# ---------------------------------------------------------------------------

class TestPollTimeout:

    @pytest.mark.asyncio
    async def test_poll_timeout_is_100ms(self):
        """Consumer receive timeout should be 100ms, not the original 2000ms.

        A 2000ms poll timeout means every service adds up to 2s of idle
        blocking between message bursts. With many sequential hops in a
        query pipeline, this compounds into seconds of unnecessary latency.
        100ms keeps responsiveness high without significant CPU overhead.
        """
        consumer = _make_consumer()

        # Wire up a mock Pulsar consumer that records the receive kwargs
        mock_pulsar_consumer = MagicMock()
        received_kwargs = {}

        def capture_receive(**kwargs):
            received_kwargs.update(kwargs)
            # Stop after one call
            consumer.running = False
            raise type('Timeout', (Exception,), {})("timeout")

        mock_pulsar_consumer.receive = capture_receive

        await consumer.consume_from_queue(mock_pulsar_consumer)

        assert received_kwargs.get("timeout_millis") == 100


# ---------------------------------------------------------------------------
# Stop / running flag
# ---------------------------------------------------------------------------

class TestStopBehaviour:

    @pytest.mark.asyncio
    async def test_stop_sets_running_false(self):
        consumer = _make_consumer()
        consumer.running = True

        await consumer.stop()

        assert consumer.running is False

    def test_initial_running_state(self):
        consumer = _make_consumer()
        assert consumer.running is True
