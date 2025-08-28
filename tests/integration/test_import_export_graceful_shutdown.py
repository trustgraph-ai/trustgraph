"""Integration tests for import/export graceful shutdown functionality."""

import pytest
import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import web, WSMsgType, ClientWebSocketResponse
from trustgraph.gateway.dispatch.triples_import import TriplesImport
from trustgraph.gateway.dispatch.triples_export import TriplesExport
from trustgraph.gateway.running import Running
from trustgraph.base.publisher import Publisher
from trustgraph.base.subscriber import Subscriber


class MockPulsarMessage:
    """Mock Pulsar message for testing."""
    
    def __init__(self, data, message_id="test-id"):
        self._data = data
        self._message_id = message_id
        self._properties = {"id": message_id}
    
    def value(self):
        return self._data
    
    def properties(self):
        return self._properties


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.messages = []
        self.closed = False
        self._close_called = False
    
    async def send_json(self, data):
        if self.closed:
            raise Exception("WebSocket is closed")
        self.messages.append(data)
    
    async def close(self):
        self._close_called = True
        self.closed = True
    
    def json(self):
        """Mock message json() method."""
        return {
            "metadata": {
                "id": "test-id",
                "metadata": {},
                "user": "test-user", 
                "collection": "test-collection"
            },
            "triples": [["subject", "predicate", "object"]]
        }


@pytest.fixture
def mock_pulsar_client():
    """Mock Pulsar client for integration testing."""
    client = MagicMock()
    
    # Mock producer
    producer = MagicMock()
    producer.send = MagicMock()
    producer.flush = MagicMock()
    producer.close = MagicMock()
    client.create_producer.return_value = producer
    
    # Mock consumer
    consumer = MagicMock()
    consumer.receive = AsyncMock()
    consumer.acknowledge = MagicMock()
    consumer.negative_acknowledge = MagicMock()
    consumer.pause_message_listener = MagicMock()
    consumer.unsubscribe = MagicMock()
    consumer.close = MagicMock()
    client.subscribe.return_value = consumer
    
    return client


@pytest.mark.asyncio
async def test_import_graceful_shutdown_integration():
    """Test import path handles shutdown gracefully with real message flow."""
    mock_client = MagicMock()
    mock_producer = MagicMock()
    mock_client.create_producer.return_value = mock_producer
    
    # Track sent messages
    sent_messages = []
    def track_send(message, properties=None):
        sent_messages.append((message, properties))
    
    mock_producer.send.side_effect = track_send
    
    ws = MockWebSocket()
    running = Running()
    
    # Create import handler
    import_handler = TriplesImport(
        ws=ws,
        running=running,
        pulsar_client=mock_client,
        queue="test-triples-import"
    )
    
    await import_handler.start()
    
    # Send multiple messages rapidly
    messages = []
    for i in range(10):
        msg_data = {
            "metadata": {
                "id": f"msg-{i}",
                "metadata": {},
                "user": "test-user",
                "collection": "test-collection"
            },
            "triples": [[f"subject-{i}", "predicate", f"object-{i}"]]
        }
        messages.append(msg_data)
        
        # Create mock message with json() method
        mock_msg = MagicMock()
        mock_msg.json.return_value = msg_data
        
        await import_handler.receive(mock_msg)
    
    # Allow brief processing time
    await asyncio.sleep(0.1)
    
    # Shutdown while messages may be in flight
    await import_handler.destroy()
    
    # Verify all messages reached producer
    assert len(sent_messages) == 10
    
    # Verify proper shutdown order was followed
    mock_producer.flush.assert_called_once()
    mock_producer.close.assert_called_once()
    
    # Verify messages have correct content
    for i, (message, properties) in enumerate(sent_messages):
        assert message.metadata.id == f"msg-{i}"
        assert len(message.triples) == 1
        assert message.triples[0][0] == f"subject-{i}"


@pytest.mark.asyncio
async def test_export_no_message_loss_integration():
    """Test export path doesn't lose acknowledged messages."""
    mock_client = MagicMock()
    mock_consumer = MagicMock()
    mock_client.subscribe.return_value = mock_consumer
    
    # Create test messages
    test_messages = []
    for i in range(20):
        msg_data = {
            "metadata": {
                "id": f"export-msg-{i}",
                "metadata": {},
                "user": "test-user",
                "collection": "test-collection"
            },
            "triples": [[f"export-subject-{i}", "predicate", f"export-object-{i}"]]
        }
        test_messages.append(MockPulsarMessage(msg_data, f"export-msg-{i}"))
    
    # Mock consumer to provide messages
    message_iter = iter(test_messages)
    async def mock_receive():
        try:
            return next(message_iter)
        except StopIteration:
            # Simulate no more messages
            await asyncio.sleep(1)
            raise StopIteration
    
    mock_consumer.receive = mock_receive
    
    ws = MockWebSocket()
    running = Running()
    
    # Create export handler
    export_handler = TriplesExport(
        ws=ws,
        running=running,
        pulsar_client=mock_client,
        queue="test-triples-export",
        consumer="test-consumer",
        subscriber="test-subscriber"
    )
    
    # Start export in background
    export_task = asyncio.create_task(export_handler.run())
    
    # Allow some messages to be processed
    await asyncio.sleep(0.5)
    
    # Verify some messages were sent to websocket
    initial_count = len(ws.messages)
    assert initial_count > 0
    
    # Force shutdown
    await export_handler.destroy()
    
    # Wait for export task to complete
    try:
        await asyncio.wait_for(export_task, timeout=2.0)
    except asyncio.TimeoutError:
        export_task.cancel()
    
    # Verify websocket was closed
    assert ws._close_called is True
    
    # Verify messages that were acknowledged were actually sent
    final_count = len(ws.messages)
    assert final_count >= initial_count
    
    # Verify no partial/corrupted messages
    for msg in ws.messages:
        assert "metadata" in msg
        assert "triples" in msg
        assert msg["metadata"]["id"].startswith("export-msg-")


@pytest.mark.asyncio
async def test_concurrent_import_export_shutdown():
    """Test concurrent import and export shutdown scenarios."""
    # Setup mock clients
    import_client = MagicMock()
    export_client = MagicMock()
    
    import_producer = MagicMock()
    export_consumer = MagicMock()
    
    import_client.create_producer.return_value = import_producer
    export_client.subscribe.return_value = export_consumer
    
    # Track operations
    import_operations = []
    export_operations = []
    
    def track_import_send(message, properties=None):
        import_operations.append(("send", message.metadata.id))
    
    def track_import_flush():
        import_operations.append(("flush",))
    
    def track_export_ack(msg):
        export_operations.append(("ack", msg.properties()["id"]))
    
    import_producer.send.side_effect = track_import_send
    import_producer.flush.side_effect = track_import_flush
    export_consumer.acknowledge.side_effect = track_export_ack
    
    # Create handlers
    import_ws = MockWebSocket()
    export_ws = MockWebSocket()
    import_running = Running()
    export_running = Running()
    
    import_handler = TriplesImport(
        ws=import_ws,
        running=import_running,
        pulsar_client=import_client,
        queue="concurrent-import"
    )
    
    export_handler = TriplesExport(
        ws=export_ws,
        running=export_running,
        pulsar_client=export_client,
        queue="concurrent-export",
        consumer="concurrent-consumer",
        subscriber="concurrent-subscriber"
    )
    
    # Start both handlers
    await import_handler.start()
    
    # Send messages to import
    for i in range(5):
        msg = MagicMock()
        msg.json.return_value = {
            "metadata": {
                "id": f"concurrent-{i}",
                "metadata": {},
                "user": "test-user",
                "collection": "test-collection"
            },
            "triples": [[f"concurrent-subject-{i}", "predicate", "object"]]
        }
        await import_handler.receive(msg)
    
    # Shutdown both concurrently
    import_shutdown = asyncio.create_task(import_handler.destroy())
    export_shutdown = asyncio.create_task(export_handler.destroy())
    
    await asyncio.gather(import_shutdown, export_shutdown)
    
    # Verify import operations completed properly
    assert len(import_operations) == 6  # 5 sends + 1 flush
    assert ("flush",) in import_operations
    
    # Verify all import messages were processed
    send_ops = [op for op in import_operations if op[0] == "send"]
    assert len(send_ops) == 5


@pytest.mark.asyncio
async def test_websocket_close_during_message_processing():
    """Test graceful handling when websocket closes during active message processing."""
    mock_client = MagicMock()
    mock_producer = MagicMock()
    mock_client.create_producer.return_value = mock_producer
    
    # Simulate slow message processing
    processed_messages = []
    async def slow_send(message, properties=None):
        processed_messages.append(message.metadata.id)
        await asyncio.sleep(0.1)  # Simulate processing delay
    
    mock_producer.send.side_effect = slow_send
    
    ws = MockWebSocket()
    running = Running()
    
    import_handler = TriplesImport(
        ws=ws,
        running=running,
        pulsar_client=mock_client,
        queue="slow-processing-import"
    )
    
    await import_handler.start()
    
    # Send many messages rapidly
    message_tasks = []
    for i in range(10):
        msg = MagicMock()
        msg.json.return_value = {
            "metadata": {
                "id": f"slow-msg-{i}",
                "metadata": {},
                "user": "test-user",
                "collection": "test-collection"
            },
            "triples": [[f"slow-subject-{i}", "predicate", "object"]]
        }
        task = asyncio.create_task(import_handler.receive(msg))
        message_tasks.append(task)
    
    # Allow some processing to start
    await asyncio.sleep(0.05)
    
    # Close websocket while messages are being processed
    ws.closed = True
    
    # Shutdown handler
    await import_handler.destroy()
    
    # Wait for all message tasks to complete
    await asyncio.gather(*message_tasks, return_exceptions=True)
    
    # Verify that messages that were being processed completed
    # (graceful shutdown should allow in-flight processing to finish)
    assert len(processed_messages) > 0
    
    # Verify producer was properly flushed and closed
    mock_producer.flush.assert_called_once()
    mock_producer.close.assert_called_once()


@pytest.mark.asyncio  
async def test_backpressure_during_shutdown():
    """Test graceful shutdown under backpressure conditions."""
    mock_client = MagicMock()
    mock_consumer = MagicMock()
    mock_client.subscribe.return_value = mock_consumer
    
    # Create messages that will cause backpressure
    large_messages = []
    for i in range(50):
        msg_data = {
            "metadata": {
                "id": f"large-msg-{i}",
                "metadata": {"large_field": "x" * 1000},  # Large metadata
                "user": "test-user",
                "collection": "test-collection"
            },
            "triples": [[f"large-subject-{i}", "predicate", f"large-object-{i}"]]
        }
        large_messages.append(MockPulsarMessage(msg_data, f"large-msg-{i}"))
    
    # Mock slow websocket
    class SlowWebSocket(MockWebSocket):
        async def send_json(self, data):
            await asyncio.sleep(0.02)  # Slow send
            await super().send_json(data)
    
    ws = SlowWebSocket()
    running = Running()
    
    export_handler = TriplesExport(
        ws=ws,
        running=running, 
        pulsar_client=mock_client,
        queue="backpressure-export",
        consumer="backpressure-consumer",
        subscriber="backpressure-subscriber"
    )
    
    # Mock consumer with backpressure
    message_queue = asyncio.Queue(maxsize=5)  # Small queue
    for msg in large_messages[:10]:  # Only add first 10
        await message_queue.put(msg)
    
    async def mock_receive_with_backpressure():
        return await message_queue.get()
    
    mock_consumer.receive = mock_receive_with_backpressure
    
    # Start export task
    export_task = asyncio.create_task(export_handler.run())
    
    # Allow some processing
    await asyncio.sleep(0.3)
    
    # Shutdown under backpressure
    shutdown_start = time.time()
    await export_handler.destroy()
    shutdown_duration = time.time() - shutdown_start
    
    # Cancel export task
    export_task.cancel()
    try:
        await export_task
    except asyncio.CancelledError:
        pass
    
    # Verify graceful shutdown completed within reasonable time
    assert shutdown_duration < 10.0  # Should not hang indefinitely
    
    # Verify some messages were processed before shutdown
    assert len(ws.messages) > 0
    
    # Verify websocket was closed
    assert ws._close_called is True