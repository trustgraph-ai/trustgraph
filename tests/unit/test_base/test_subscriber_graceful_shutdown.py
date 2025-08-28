"""Unit tests for Subscriber graceful shutdown functionality."""

import pytest
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from trustgraph.base.subscriber import Subscriber


@pytest.fixture
def mock_pulsar_client():
    """Mock Pulsar client for testing."""
    client = MagicMock()
    consumer = MagicMock()
    consumer.receive = MagicMock()
    consumer.acknowledge = MagicMock()
    consumer.negative_acknowledge = MagicMock()
    consumer.pause_message_listener = MagicMock()
    consumer.unsubscribe = MagicMock()
    consumer.close = MagicMock()
    client.subscribe.return_value = consumer
    return client


@pytest.fixture
def subscriber(mock_pulsar_client):
    """Create Subscriber instance for testing."""
    return Subscriber(
        client=mock_pulsar_client,
        topic="test-topic",
        subscription="test-subscription",
        consumer_name="test-consumer",
        schema=dict,
        max_size=10,
        drain_timeout=2.0,
        backpressure_strategy="block"
    )


def create_mock_message(message_id="test-id", data=None):
    """Create a mock Pulsar message."""
    msg = MagicMock()
    msg.properties.return_value = {"id": message_id}
    msg.value.return_value = data or {"test": "data"}
    return msg


@pytest.mark.asyncio
async def test_subscriber_deferred_acknowledgment_success():
    """Verify Subscriber only acks on successful delivery."""
    mock_client = MagicMock()
    mock_consumer = MagicMock()
    mock_client.subscribe.return_value = mock_consumer
    
    subscriber = Subscriber(
        client=mock_client,
        topic="test-topic",
        subscription="test-subscription", 
        consumer_name="test-consumer",
        schema=dict,
        max_size=10,
        backpressure_strategy="block"
    )
    
    # Create queue for subscription
    queue = await subscriber.subscribe("test-queue")
    
    # Create mock message
    msg = create_mock_message("msg-1", {"data": "test"})
    
    # Process message
    await subscriber._process_message(msg)
    
    # Should acknowledge successful delivery
    mock_consumer.acknowledge.assert_called_once_with(msg)
    mock_consumer.negative_acknowledge.assert_not_called()
    
    # Message should be in queue
    assert not queue.empty()
    received_msg = await queue.get()
    assert received_msg == {"data": "test"}


@pytest.mark.asyncio
async def test_subscriber_deferred_acknowledgment_failure():
    """Verify Subscriber negative acks on delivery failure."""
    mock_client = MagicMock()
    mock_consumer = MagicMock()
    mock_client.subscribe.return_value = mock_consumer
    
    subscriber = Subscriber(
        client=mock_client,
        topic="test-topic",
        subscription="test-subscription",
        consumer_name="test-consumer", 
        schema=dict,
        max_size=1,  # Very small queue
        backpressure_strategy="drop_new"
    )
    
    # Create queue and fill it
    queue = await subscriber.subscribe("test-queue")
    await queue.put({"existing": "data"})
    
    # Create mock message - should be dropped
    msg = create_mock_message("msg-1", {"data": "test"})
    
    # Process message (should fail due to full queue + drop_new strategy)
    await subscriber._process_message(msg)
    
    # Should negative acknowledge failed delivery
    mock_consumer.negative_acknowledge.assert_called_once_with(msg)
    mock_consumer.acknowledge.assert_not_called()


@pytest.mark.asyncio
async def test_subscriber_backpressure_strategies():
    """Test different backpressure strategies."""
    mock_client = MagicMock()
    mock_consumer = MagicMock()
    mock_client.subscribe.return_value = mock_consumer
    
    # Test drop_oldest strategy
    subscriber = Subscriber(
        client=mock_client,
        topic="test-topic", 
        subscription="test-subscription",
        consumer_name="test-consumer",
        schema=dict,
        max_size=2,
        backpressure_strategy="drop_oldest"
    )
    
    queue = await subscriber.subscribe("test-queue")
    
    # Fill queue
    await queue.put({"data": "old1"})
    await queue.put({"data": "old2"})
    
    # Add new message (should drop oldest)
    msg = create_mock_message("msg-1", {"data": "new"})
    await subscriber._process_message(msg)
    
    # Should acknowledge delivery
    mock_consumer.acknowledge.assert_called_once_with(msg)
    
    # Queue should have new message (old one dropped)
    messages = []
    while not queue.empty():
        messages.append(await queue.get())
    
    # Should contain old2 and new (old1 was dropped)
    assert len(messages) == 2
    assert {"data": "new"} in messages


@pytest.mark.asyncio
async def test_subscriber_graceful_shutdown():
    """Test Subscriber graceful shutdown with queue draining."""
    mock_client = MagicMock()
    mock_consumer = MagicMock()
    mock_client.subscribe.return_value = mock_consumer
    
    subscriber = Subscriber(
        client=mock_client,
        topic="test-topic",
        subscription="test-subscription",
        consumer_name="test-consumer",
        schema=dict,
        max_size=10,
        drain_timeout=1.0
    )
    
    await subscriber.start()
    
    # Create subscription with messages
    queue = await subscriber.subscribe("test-queue")
    await queue.put({"data": "msg1"})
    await queue.put({"data": "msg2"})
    
    # Initial state
    assert subscriber.running is True
    assert subscriber.draining is False
    
    # Start shutdown
    stop_task = asyncio.create_task(subscriber.stop())
    
    # Allow brief processing
    await asyncio.sleep(0.1)
    
    # Should be in drain state
    assert subscriber.running is False
    assert subscriber.draining is True
    
    # Should pause message listener
    mock_consumer.pause_message_listener.assert_called_once()
    
    # Complete shutdown
    await stop_task
    
    # Should have cleaned up
    mock_consumer.unsubscribe.assert_called_once()
    mock_consumer.close.assert_called_once()


@pytest.mark.asyncio
async def test_subscriber_drain_timeout():
    """Test Subscriber respects drain timeout."""
    mock_client = MagicMock()
    mock_consumer = MagicMock()
    mock_client.subscribe.return_value = mock_consumer
    
    subscriber = Subscriber(
        client=mock_client,
        topic="test-topic",
        subscription="test-subscription", 
        consumer_name="test-consumer",
        schema=dict,
        max_size=10,
        drain_timeout=0.1  # Very short timeout
    )
    
    await subscriber.start()
    
    # Create subscription with many messages
    queue = await subscriber.subscribe("test-queue")
    for i in range(20):
        await queue.put({"data": f"msg{i}"})
    
    import time
    start_time = time.time()
    await subscriber.stop()
    end_time = time.time()
    
    # Should timeout quickly
    assert end_time - start_time < 1.0
    
    # Queue should still have messages (drain timed out)
    assert not queue.empty()


@pytest.mark.asyncio
async def test_subscriber_pending_acks_cleanup():
    """Test Subscriber cleans up pending acknowledgments on shutdown."""
    mock_client = MagicMock()
    mock_consumer = MagicMock()
    mock_client.subscribe.return_value = mock_consumer
    
    subscriber = Subscriber(
        client=mock_client,
        topic="test-topic",
        subscription="test-subscription",
        consumer_name="test-consumer",
        schema=dict,
        max_size=10
    )
    
    await subscriber.start()
    
    # Add pending acknowledgments manually (simulating in-flight messages)
    msg1 = create_mock_message("msg-1")
    msg2 = create_mock_message("msg-2") 
    subscriber.pending_acks["ack-1"] = msg1
    subscriber.pending_acks["ack-2"] = msg2
    
    # Stop subscriber
    await subscriber.stop()
    
    # Should negative acknowledge pending messages
    assert mock_consumer.negative_acknowledge.call_count == 2
    mock_consumer.negative_acknowledge.assert_any_call(msg1)
    mock_consumer.negative_acknowledge.assert_any_call(msg2)
    
    # Pending acks should be cleared
    assert len(subscriber.pending_acks) == 0


@pytest.mark.asyncio
async def test_subscriber_multiple_subscribers():
    """Test Subscriber with multiple concurrent subscribers."""
    mock_client = MagicMock()
    mock_consumer = MagicMock()
    mock_client.subscribe.return_value = mock_consumer
    
    subscriber = Subscriber(
        client=mock_client,
        topic="test-topic",
        subscription="test-subscription",
        consumer_name="test-consumer",
        schema=dict,
        max_size=10
    )
    
    # Create multiple subscriptions
    queue1 = await subscriber.subscribe("queue-1")
    queue2 = await subscriber.subscribe("queue-2")
    queue_all = await subscriber.subscribe_all("queue-all")
    
    # Process message
    msg = create_mock_message("msg-1", {"data": "broadcast"})
    await subscriber._process_message(msg)
    
    # Should acknowledge (successful delivery to all queues)
    mock_consumer.acknowledge.assert_called_once_with(msg)
    
    # Message should be in specific queue (queue-1) and broadcast queue
    assert not queue1.empty()
    assert queue2.empty()  # No message for queue-2
    assert not queue_all.empty()
    
    # Verify message content
    msg1 = await queue1.get()
    msg_all = await queue_all.get()
    assert msg1 == {"data": "broadcast"}
    assert msg_all == {"data": "broadcast"}