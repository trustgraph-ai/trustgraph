"""
Tests for message queue subscriber resilience: unexpected message handling,
orphaned message detection, backpressure strategies, graceful draining,
and timeout recovery.
"""

import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from trustgraph.base.subscriber import Subscriber


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_subscriber(max_size=10, backpressure_strategy="block",
                     drain_timeout=5.0):
    """Create a Subscriber without connecting to any backend."""
    backend = MagicMock()
    sub = Subscriber(
        backend=backend,
        topic="test-topic",
        subscription="test-sub",
        consumer_name="test",
        max_size=max_size,
        backpressure_strategy=backpressure_strategy,
        drain_timeout=drain_timeout,
    )
    sub.consumer = MagicMock()
    return sub


def _make_msg(id=None, value="test-value"):
    """Create a mock message with optional properties."""
    msg = MagicMock()
    if id is not None:
        msg.properties.return_value = {"id": id}
    else:
        msg.properties.side_effect = KeyError("id")
    msg.value.return_value = value
    return msg


# ---------------------------------------------------------------------------
# Message property extraction resilience
# ---------------------------------------------------------------------------

class TestMessagePropertyResilience:

    @pytest.mark.asyncio
    async def test_missing_id_property_handled(self):
        """Messages without 'id' property should not crash."""
        sub = _make_subscriber()
        msg = MagicMock()
        msg.properties.side_effect = Exception("no properties")
        msg.value.return_value = "some-value"

        # Should not raise
        await sub._process_message(msg)

        # Message should still be acknowledged
        sub.consumer.acknowledge.assert_called_once_with(msg)

    @pytest.mark.asyncio
    async def test_message_with_valid_id_delivered(self):
        """Messages with matching subscriber ID should be delivered."""
        sub = _make_subscriber()
        q = await sub.subscribe("req-1")

        msg = _make_msg(id="req-1", value="response-data")
        await sub._process_message(msg)

        assert not q.empty()
        assert q.get_nowait() == "response-data"
        sub.consumer.acknowledge.assert_called_once()


# ---------------------------------------------------------------------------
# Orphaned message handling
# ---------------------------------------------------------------------------

class TestOrphanedMessages:

    @pytest.mark.asyncio
    async def test_orphaned_message_acknowledged(self):
        """Messages with no matching waiter should still be acknowledged."""
        sub = _make_subscriber()
        msg = _make_msg(id="unknown-id", value="orphan")

        await sub._process_message(msg)

        # Orphaned message is acknowledged (not negative-acknowledged)
        sub.consumer.acknowledge.assert_called_once_with(msg)

    @pytest.mark.asyncio
    async def test_orphaned_message_not_queued(self):
        """Orphaned messages should not appear in any subscriber queue."""
        sub = _make_subscriber()
        q = await sub.subscribe("req-1")

        msg = _make_msg(id="different-id", value="orphan")
        await sub._process_message(msg)

        assert q.empty()


# ---------------------------------------------------------------------------
# Backpressure strategies
# ---------------------------------------------------------------------------

class TestBackpressureStrategies:

    @pytest.mark.asyncio
    async def test_drop_new_rejects_when_full(self):
        """drop_new strategy should reject new messages when queue is full."""
        sub = _make_subscriber(max_size=1, backpressure_strategy="drop_new")
        q = await sub.subscribe("req-1")

        # Fill the queue
        msg1 = _make_msg(id="req-1", value="first")
        await sub._process_message(msg1)
        assert q.qsize() == 1

        # Second message should be dropped
        msg2 = _make_msg(id="req-1", value="second")
        await sub._process_message(msg2)

        # Queue still has only the first message
        assert q.qsize() == 1
        assert q.get_nowait() == "first"

    @pytest.mark.asyncio
    async def test_drop_oldest_evicts_when_full(self):
        """drop_oldest strategy should evict oldest message when full."""
        sub = _make_subscriber(max_size=1, backpressure_strategy="drop_oldest")
        q = await sub.subscribe("req-1")

        msg1 = _make_msg(id="req-1", value="first")
        await sub._process_message(msg1)

        msg2 = _make_msg(id="req-1", value="second")
        await sub._process_message(msg2)

        # Queue should have the newer message
        assert q.qsize() == 1
        assert q.get_nowait() == "second"

    @pytest.mark.asyncio
    async def test_block_strategy_delivers(self):
        """block strategy should deliver messages normally."""
        sub = _make_subscriber(max_size=10, backpressure_strategy="block")
        q = await sub.subscribe("req-1")

        msg = _make_msg(id="req-1", value="data")
        await sub._process_message(msg)

        assert q.get_nowait() == "data"


# ---------------------------------------------------------------------------
# Full subscribers (subscribe_all)
# ---------------------------------------------------------------------------

class TestFullSubscribers:

    @pytest.mark.asyncio
    async def test_subscribe_all_receives_all_messages(self):
        sub = _make_subscriber()
        q = await sub.subscribe_all("listener-1")

        msg = _make_msg(id="any-id", value="broadcast")
        await sub._process_message(msg)

        assert q.get_nowait() == "broadcast"

    @pytest.mark.asyncio
    async def test_multiple_full_subscribers_all_receive(self):
        sub = _make_subscriber()
        q1 = await sub.subscribe_all("l1")
        q2 = await sub.subscribe_all("l2")

        msg = _make_msg(id="any", value="data")
        await sub._process_message(msg)

        assert q1.get_nowait() == "data"
        assert q2.get_nowait() == "data"


# ---------------------------------------------------------------------------
# Subscribe / unsubscribe lifecycle
# ---------------------------------------------------------------------------

class TestSubscribeLifecycle:

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_queue(self):
        sub = _make_subscriber()
        await sub.subscribe("req-1")
        await sub.unsubscribe("req-1")

        assert "req-1" not in sub.q

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_is_noop(self):
        sub = _make_subscriber()
        await sub.unsubscribe("nonexistent")  # Should not raise

    @pytest.mark.asyncio
    async def test_unsubscribe_all_removes_queue(self):
        sub = _make_subscriber()
        await sub.subscribe_all("l1")
        await sub.unsubscribe_all("l1")

        assert "l1" not in sub.full


# ---------------------------------------------------------------------------
# Pending ack tracking
# ---------------------------------------------------------------------------

class TestPendingAckTracking:

    @pytest.mark.asyncio
    async def test_processed_message_cleared_from_pending(self):
        sub = _make_subscriber()
        msg = _make_msg(id="req-1", value="data")

        await sub._process_message(msg)

        # After processing, pending_acks should be empty
        assert len(sub.pending_acks) == 0
