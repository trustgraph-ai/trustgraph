"""
Unit tests for objects import dispatcher.

Tests the business logic of objects import dispatcher
while mocking the Publisher and websocket components.
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from aiohttp import web

from trustgraph.gateway.dispatch.objects_import import ObjectsImport
from trustgraph.schema import Metadata, ExtractedObject


@pytest.fixture
def mock_pulsar_client():
    """Mock Pulsar client."""
    client = Mock()
    return client


@pytest.fixture
def mock_publisher():
    """Mock Publisher with async methods."""
    publisher = Mock()
    publisher.start = AsyncMock()
    publisher.stop = AsyncMock()
    publisher.send = AsyncMock()
    return publisher


@pytest.fixture
def mock_running():
    """Mock Running state handler."""
    running = Mock()
    running.get.return_value = True
    running.stop = Mock()
    return running


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection."""
    ws = Mock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def sample_objects_message():
    """Sample objects message data."""
    return {
        "metadata": {
            "id": "obj-123",
            "metadata": [
                {
                    "s": {"v": "obj-123", "e": False},
                    "p": {"v": "source", "e": False},
                    "o": {"v": "test", "e": False}
                }
            ],
            "user": "testuser",
            "collection": "testcollection"
        },
        "schema_name": "person",
        "values": [{
            "name": "John Doe",
            "age": "30",
            "city": "New York"
        }],
        "confidence": 0.95,
        "source_span": "John Doe, age 30, lives in New York"
    }


@pytest.fixture
def minimal_objects_message():
    """Minimal required objects message data."""
    return {
        "metadata": {
            "id": "obj-456",
            "user": "testuser",
            "collection": "testcollection"
        },
        "schema_name": "simple_schema",
        "values": [{
            "field1": "value1"
        }]
    }


class TestObjectsImportInitialization:
    """Test ObjectsImport initialization."""

    @patch('trustgraph.gateway.dispatch.objects_import.Publisher')
    def test_init_creates_publisher_with_correct_params(self, mock_publisher_class, mock_pulsar_client, mock_websocket, mock_running):
        """Test that ObjectsImport creates Publisher with correct parameters."""
        mock_publisher_instance = Mock()
        mock_publisher_class.return_value = mock_publisher_instance
        
        objects_import = ObjectsImport(
            ws=mock_websocket,
            running=mock_running,
            pulsar_client=mock_pulsar_client,
            queue="test-objects-queue"
        )
        
        # Verify Publisher was created with correct parameters
        mock_publisher_class.assert_called_once_with(
            mock_pulsar_client,
            topic="test-objects-queue",
            schema=ExtractedObject
        )
        
        # Verify instance variables are set correctly
        assert objects_import.ws == mock_websocket
        assert objects_import.running == mock_running
        assert objects_import.publisher == mock_publisher_instance

    @patch('trustgraph.gateway.dispatch.objects_import.Publisher')
    def test_init_stores_references_correctly(self, mock_publisher_class, mock_pulsar_client, mock_websocket, mock_running):
        """Test that ObjectsImport stores all required references."""
        objects_import = ObjectsImport(
            ws=mock_websocket,
            running=mock_running,
            pulsar_client=mock_pulsar_client,
            queue="objects-queue"
        )
        
        assert objects_import.ws is mock_websocket
        assert objects_import.running is mock_running


class TestObjectsImportLifecycle:
    """Test ObjectsImport lifecycle methods."""

    @patch('trustgraph.gateway.dispatch.objects_import.Publisher')
    @pytest.mark.asyncio
    async def test_start_calls_publisher_start(self, mock_publisher_class, mock_pulsar_client, mock_websocket, mock_running):
        """Test that start() calls publisher.start()."""
        mock_publisher_instance = Mock()
        mock_publisher_instance.start = AsyncMock()
        mock_publisher_class.return_value = mock_publisher_instance
        
        objects_import = ObjectsImport(
            ws=mock_websocket,
            running=mock_running,
            pulsar_client=mock_pulsar_client,
            queue="test-queue"
        )
        
        await objects_import.start()
        
        mock_publisher_instance.start.assert_called_once()

    @patch('trustgraph.gateway.dispatch.objects_import.Publisher')
    @pytest.mark.asyncio
    async def test_destroy_stops_and_closes_properly(self, mock_publisher_class, mock_pulsar_client, mock_websocket, mock_running):
        """Test that destroy() properly stops publisher and closes websocket."""
        mock_publisher_instance = Mock()
        mock_publisher_instance.stop = AsyncMock()
        mock_publisher_class.return_value = mock_publisher_instance
        
        objects_import = ObjectsImport(
            ws=mock_websocket,
            running=mock_running,
            pulsar_client=mock_pulsar_client,
            queue="test-queue"
        )
        
        await objects_import.destroy()
        
        # Verify sequence of operations
        mock_running.stop.assert_called_once()
        mock_publisher_instance.stop.assert_called_once()
        mock_websocket.close.assert_called_once()

    @patch('trustgraph.gateway.dispatch.objects_import.Publisher')
    @pytest.mark.asyncio
    async def test_destroy_handles_none_websocket(self, mock_publisher_class, mock_pulsar_client, mock_running):
        """Test that destroy() handles None websocket gracefully."""
        mock_publisher_instance = Mock()
        mock_publisher_instance.stop = AsyncMock()
        mock_publisher_class.return_value = mock_publisher_instance
        
        objects_import = ObjectsImport(
            ws=None,  # None websocket
            running=mock_running,
            pulsar_client=mock_pulsar_client,
            queue="test-queue"
        )
        
        # Should not raise exception
        await objects_import.destroy()
        
        mock_running.stop.assert_called_once()
        mock_publisher_instance.stop.assert_called_once()


class TestObjectsImportMessageProcessing:
    """Test ObjectsImport message processing."""

    @patch('trustgraph.gateway.dispatch.objects_import.Publisher')
    @pytest.mark.asyncio
    async def test_receive_processes_full_message_correctly(self, mock_publisher_class, mock_pulsar_client, mock_websocket, mock_running, sample_objects_message):
        """Test that receive() processes complete message correctly."""
        mock_publisher_instance = Mock()
        mock_publisher_instance.send = AsyncMock()
        mock_publisher_class.return_value = mock_publisher_instance
        
        objects_import = ObjectsImport(
            ws=mock_websocket,
            running=mock_running,
            pulsar_client=mock_pulsar_client,
            queue="test-queue"
        )
        
        # Create mock message
        mock_msg = Mock()
        mock_msg.json.return_value = sample_objects_message
        
        await objects_import.receive(mock_msg)
        
        # Verify publisher.send was called
        mock_publisher_instance.send.assert_called_once()
        
        # Get the call arguments
        call_args = mock_publisher_instance.send.call_args
        assert call_args[0][0] is None  # First argument should be None
        
        # Check the ExtractedObject that was sent
        sent_object = call_args[0][1]
        assert isinstance(sent_object, ExtractedObject)
        assert sent_object.schema_name == "person"
        assert sent_object.values[0]["name"] == "John Doe"
        assert sent_object.values[0]["age"] == "30"
        assert sent_object.confidence == 0.95
        assert sent_object.source_span == "John Doe, age 30, lives in New York"
        
        # Check metadata
        assert sent_object.metadata.id == "obj-123"
        assert sent_object.metadata.user == "testuser"
        assert sent_object.metadata.collection == "testcollection"
        assert len(sent_object.metadata.metadata) == 1  # One triple in metadata

    @patch('trustgraph.gateway.dispatch.objects_import.Publisher')
    @pytest.mark.asyncio
    async def test_receive_handles_minimal_message(self, mock_publisher_class, mock_pulsar_client, mock_websocket, mock_running, minimal_objects_message):
        """Test that receive() handles message with minimal required fields."""
        mock_publisher_instance = Mock()
        mock_publisher_instance.send = AsyncMock()
        mock_publisher_class.return_value = mock_publisher_instance
        
        objects_import = ObjectsImport(
            ws=mock_websocket,
            running=mock_running,
            pulsar_client=mock_pulsar_client,
            queue="test-queue"
        )
        
        # Create mock message
        mock_msg = Mock()
        mock_msg.json.return_value = minimal_objects_message
        
        await objects_import.receive(mock_msg)
        
        # Verify publisher.send was called
        mock_publisher_instance.send.assert_called_once()
        
        # Get the sent object
        sent_object = mock_publisher_instance.send.call_args[0][1]
        assert isinstance(sent_object, ExtractedObject)
        assert sent_object.schema_name == "simple_schema"
        assert sent_object.values[0]["field1"] == "value1"
        assert sent_object.confidence == 1.0  # Default value
        assert sent_object.source_span == ""  # Default value
        assert len(sent_object.metadata.metadata) == 0  # Default empty list

    @patch('trustgraph.gateway.dispatch.objects_import.Publisher')
    @pytest.mark.asyncio
    async def test_receive_uses_default_values(self, mock_publisher_class, mock_pulsar_client, mock_websocket, mock_running):
        """Test that receive() uses appropriate default values for optional fields."""
        mock_publisher_instance = Mock()
        mock_publisher_instance.send = AsyncMock()
        mock_publisher_class.return_value = mock_publisher_instance
        
        objects_import = ObjectsImport(
            ws=mock_websocket,
            running=mock_running,
            pulsar_client=mock_pulsar_client,
            queue="test-queue"
        )
        
        # Message without optional fields
        message_data = {
            "metadata": {
                "id": "obj-789",
                "user": "testuser",
                "collection": "testcollection"
            },
            "schema_name": "test_schema",
            "values": [{"key": "value"}]
            # No confidence or source_span
        }
        
        mock_msg = Mock()
        mock_msg.json.return_value = message_data
        
        await objects_import.receive(mock_msg)
        
        # Get the sent object and verify defaults
        sent_object = mock_publisher_instance.send.call_args[0][1]
        assert sent_object.confidence == 1.0
        assert sent_object.source_span == ""


class TestObjectsImportRunMethod:
    """Test ObjectsImport run method."""

    @patch('trustgraph.gateway.dispatch.objects_import.Publisher')
    @patch('trustgraph.gateway.dispatch.objects_import.asyncio.sleep')
    @pytest.mark.asyncio
    async def test_run_loops_while_running(self, mock_sleep, mock_publisher_class, mock_pulsar_client, mock_websocket, mock_running):
        """Test that run() loops while running.get() returns True."""
        mock_sleep.return_value = None
        mock_publisher_class.return_value = Mock()
        
        # Set up running state to return True twice, then False
        mock_running.get.side_effect = [True, True, False]
        
        objects_import = ObjectsImport(
            ws=mock_websocket,
            running=mock_running,
            pulsar_client=mock_pulsar_client,
            queue="test-queue"
        )
        
        await objects_import.run()
        
        # Verify sleep was called twice (for the two True iterations)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(0.5)
        
        # Verify websocket was closed
        mock_websocket.close.assert_called_once()
        
        # Verify websocket was set to None
        assert objects_import.ws is None

    @patch('trustgraph.gateway.dispatch.objects_import.Publisher')
    @patch('trustgraph.gateway.dispatch.objects_import.asyncio.sleep')
    @pytest.mark.asyncio
    async def test_run_handles_none_websocket_gracefully(self, mock_sleep, mock_publisher_class, mock_pulsar_client, mock_running):
        """Test that run() handles None websocket gracefully."""
        mock_sleep.return_value = None
        mock_publisher_class.return_value = Mock()
        
        mock_running.get.return_value = False  # Exit immediately
        
        objects_import = ObjectsImport(
            ws=None,  # None websocket
            running=mock_running,
            pulsar_client=mock_pulsar_client,
            queue="test-queue"
        )
        
        # Should not raise exception
        await objects_import.run()
        
        # Verify websocket remains None
        assert objects_import.ws is None


class TestObjectsImportBatchProcessing:
    """Test ObjectsImport batch processing functionality."""

    @pytest.fixture
    def batch_objects_message(self):
        """Sample batch objects message data."""
        return {
            "metadata": {
                "id": "batch-001",
                "metadata": [
                    {
                        "s": {"v": "batch-001", "e": False},
                        "p": {"v": "source", "e": False},
                        "o": {"v": "test", "e": False}
                    }
                ],
                "user": "testuser",
                "collection": "testcollection"
            },
            "schema_name": "person",
            "values": [
                {
                    "name": "John Doe",
                    "age": "30",
                    "city": "New York"
                },
                {
                    "name": "Jane Smith",
                    "age": "25",
                    "city": "Boston"
                },
                {
                    "name": "Bob Johnson",
                    "age": "45",
                    "city": "Chicago"
                }
            ],
            "confidence": 0.85,
            "source_span": "Multiple people found in document"
        }

    @patch('trustgraph.gateway.dispatch.objects_import.Publisher')
    @pytest.mark.asyncio
    async def test_receive_processes_batch_message_correctly(self, mock_publisher_class, mock_pulsar_client, mock_websocket, mock_running, batch_objects_message):
        """Test that receive() processes batch message correctly."""
        mock_publisher_instance = Mock()
        mock_publisher_instance.send = AsyncMock()
        mock_publisher_class.return_value = mock_publisher_instance
        
        objects_import = ObjectsImport(
            ws=mock_websocket,
            running=mock_running,
            pulsar_client=mock_pulsar_client,
            queue="test-queue"
        )
        
        # Create mock message
        mock_msg = Mock()
        mock_msg.json.return_value = batch_objects_message
        
        await objects_import.receive(mock_msg)
        
        # Verify publisher.send was called
        mock_publisher_instance.send.assert_called_once()
        
        # Get the call arguments
        call_args = mock_publisher_instance.send.call_args
        assert call_args[0][0] is None  # First argument should be None
        
        # Check the ExtractedObject that was sent
        sent_object = call_args[0][1]
        assert isinstance(sent_object, ExtractedObject)
        assert sent_object.schema_name == "person"
        
        # Check that all batch values are present
        assert len(sent_object.values) == 3
        assert sent_object.values[0]["name"] == "John Doe"
        assert sent_object.values[0]["age"] == "30"
        assert sent_object.values[0]["city"] == "New York"
        
        assert sent_object.values[1]["name"] == "Jane Smith"
        assert sent_object.values[1]["age"] == "25"
        assert sent_object.values[1]["city"] == "Boston"
        
        assert sent_object.values[2]["name"] == "Bob Johnson"
        assert sent_object.values[2]["age"] == "45"
        assert sent_object.values[2]["city"] == "Chicago"
        
        assert sent_object.confidence == 0.85
        assert sent_object.source_span == "Multiple people found in document"

    @patch('trustgraph.gateway.dispatch.objects_import.Publisher')
    @pytest.mark.asyncio
    async def test_receive_handles_empty_batch(self, mock_publisher_class, mock_pulsar_client, mock_websocket, mock_running):
        """Test that receive() handles empty batch correctly."""
        mock_publisher_instance = Mock()
        mock_publisher_instance.send = AsyncMock()
        mock_publisher_class.return_value = mock_publisher_instance
        
        objects_import = ObjectsImport(
            ws=mock_websocket,
            running=mock_running,
            pulsar_client=mock_pulsar_client,
            queue="test-queue"
        )
        
        # Message with empty values array
        empty_batch_message = {
            "metadata": {
                "id": "empty-batch-001",
                "user": "testuser",
                "collection": "testcollection"
            },
            "schema_name": "empty_schema",
            "values": []
        }
        
        mock_msg = Mock()
        mock_msg.json.return_value = empty_batch_message
        
        await objects_import.receive(mock_msg)
        
        # Should still send the message
        mock_publisher_instance.send.assert_called_once()
        sent_object = mock_publisher_instance.send.call_args[0][1]
        assert len(sent_object.values) == 0


class TestObjectsImportErrorHandling:
    """Test error handling in ObjectsImport."""

    @patch('trustgraph.gateway.dispatch.objects_import.Publisher')
    @pytest.mark.asyncio
    async def test_receive_propagates_publisher_errors(self, mock_publisher_class, mock_pulsar_client, mock_websocket, mock_running, sample_objects_message):
        """Test that receive() propagates publisher send errors."""
        mock_publisher_instance = Mock()
        mock_publisher_instance.send = AsyncMock(side_effect=Exception("Publisher error"))
        mock_publisher_class.return_value = mock_publisher_instance
        
        objects_import = ObjectsImport(
            ws=mock_websocket,
            running=mock_running,
            pulsar_client=mock_pulsar_client,
            queue="test-queue"
        )
        
        mock_msg = Mock()
        mock_msg.json.return_value = sample_objects_message
        
        with pytest.raises(Exception, match="Publisher error"):
            await objects_import.receive(mock_msg)

    @patch('trustgraph.gateway.dispatch.objects_import.Publisher')
    @pytest.mark.asyncio
    async def test_receive_handles_malformed_json(self, mock_publisher_class, mock_pulsar_client, mock_websocket, mock_running):
        """Test that receive() handles malformed JSON appropriately."""
        mock_publisher_class.return_value = Mock()
        
        objects_import = ObjectsImport(
            ws=mock_websocket,
            running=mock_running,
            pulsar_client=mock_pulsar_client,
            queue="test-queue"
        )
        
        mock_msg = Mock()
        mock_msg.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        with pytest.raises(json.JSONDecodeError):
            await objects_import.receive(mock_msg)