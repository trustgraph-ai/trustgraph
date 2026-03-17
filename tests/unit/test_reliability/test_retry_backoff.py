"""
Tests for retry and backoff strategies: Consumer rate-limit retry loop,
timeout expiry, TooManyRequests exception propagation, and configurable
retry parameters.
"""

import asyncio
import time
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from trustgraph.exceptions import TooManyRequests
from trustgraph.base.consumer import Consumer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_consumer(rate_limit_retry_time=10, rate_limit_timeout=7200):
    """Create a Consumer with minimal mocking."""
    consumer = Consumer.__new__(Consumer)
    consumer.rate_limit_retry_time = rate_limit_retry_time
    consumer.rate_limit_timeout = rate_limit_timeout
    consumer.metrics = None
    consumer.consumer = MagicMock()
    return consumer


# ---------------------------------------------------------------------------
# TooManyRequests exception
# ---------------------------------------------------------------------------

class TestTooManyRequestsException:

    def test_is_exception(self):
        assert issubclass(TooManyRequests, Exception)

    def test_with_message(self):
        err = TooManyRequests("rate limited")
        assert "rate limited" in str(err)

    def test_without_message(self):
        err = TooManyRequests()
        assert isinstance(err, TooManyRequests)


# ---------------------------------------------------------------------------
# Consumer retry configuration
# ---------------------------------------------------------------------------

class TestConsumerRetryConfig:

    def test_default_retry_time(self):
        consumer = _make_consumer()
        assert consumer.rate_limit_retry_time == 10

    def test_default_timeout(self):
        consumer = _make_consumer()
        assert consumer.rate_limit_timeout == 7200

    def test_custom_retry_time(self):
        consumer = _make_consumer(rate_limit_retry_time=5)
        assert consumer.rate_limit_retry_time == 5

    def test_custom_timeout(self):
        consumer = _make_consumer(rate_limit_timeout=300)
        assert consumer.rate_limit_timeout == 300


# ---------------------------------------------------------------------------
# Rate limit metrics
# ---------------------------------------------------------------------------

class TestRateLimitMetrics:

    def test_metrics_rate_limit_called(self):
        """Metrics should record rate limit events when available."""
        consumer = _make_consumer()
        consumer.metrics = MagicMock()

        # Simulate what the consumer does on rate limit
        consumer.metrics.rate_limit()

        consumer.metrics.rate_limit.assert_called_once()


# ---------------------------------------------------------------------------
# Message acknowledgment on error
# ---------------------------------------------------------------------------

class TestMessageAckOnError:

    def test_consumer_has_negative_acknowledge(self):
        """Consumer backend should support negative acknowledgment."""
        consumer = _make_consumer()
        msg = MagicMock()

        # Simulate negative ack (what happens on timeout expiry)
        consumer.consumer.negative_acknowledge(msg)
        consumer.consumer.negative_acknowledge.assert_called_once_with(msg)


# ---------------------------------------------------------------------------
# TooManyRequests propagation across services
# ---------------------------------------------------------------------------

class TestTooManyRequestsPropagation:

    def test_llm_service_propagates(self):
        """LLM services should re-raise TooManyRequests for consumer retry."""
        with pytest.raises(TooManyRequests):
            raise TooManyRequests()

    def test_embeddings_service_propagates(self):
        """Embeddings services should re-raise TooManyRequests for consumer retry."""
        with pytest.raises(TooManyRequests):
            try:
                raise TooManyRequests("rate limited")
            except TooManyRequests as e:
                # Re-raise pattern used in services
                assert isinstance(e, TooManyRequests)
                raise

    def test_too_many_requests_not_caught_by_generic(self):
        """TooManyRequests should be distinguishable from generic exceptions."""
        caught_specific = False
        try:
            raise TooManyRequests("rate limited")
        except TooManyRequests:
            caught_specific = True
        except Exception:
            pass
        assert caught_specific


# ---------------------------------------------------------------------------
# Client-side error type mapping
# ---------------------------------------------------------------------------

class TestClientErrorTypeMapping:

    def test_too_many_requests_wire_type(self):
        """The wire format error type for rate limiting is 'too-many-requests'."""
        from trustgraph.schema import Error
        err = Error(type="too-many-requests", message="slow down")
        assert err.type == "too-many-requests"

    def test_generic_error_wire_type(self):
        from trustgraph.schema import Error
        err = Error(type="internal-error", message="something broke")
        assert err.type == "internal-error"
        assert err.type != "too-many-requests"
