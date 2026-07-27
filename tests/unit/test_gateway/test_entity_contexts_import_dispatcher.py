"""
Unit tests for entity contexts import dispatcher.

Tests the business logic of EntityContextsImport while mocking the
async producer and websocket components.

Regression coverage: a previous version constructed Metadata(metadata=...)
which raised TypeError at runtime as soon as a message was received. These
tests exercise receive() end-to-end so any future schema/kwarg drift in
the Metadata or EntityContexts construction is caught immediately.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from trustgraph.gateway.dispatch.entity_contexts_import import EntityContextsImport
from trustgraph.schema import EntityContexts, EntityContext, Metadata


@pytest.fixture
def mock_backend():
    backend = Mock()
    backend.create_producer = AsyncMock()
    return backend


@pytest.fixture
def mock_running():
    running = Mock()
    running.get.return_value = True
    running.stop = Mock()
    return running


@pytest.fixture
def mock_websocket():
    ws = Mock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def mock_producer():
    producer = AsyncMock()
    return producer


@pytest.fixture
def sample_message():
    """Sample entity-contexts websocket message."""
    return {
        "metadata": {
            "id": "doc-123",
            "user": "testuser",
            "collection": "testcollection",
        },
        "entities": [
            {
                "entity": {"v": "http://example.org/alice", "e": True},
                "context": "Alice is a person.",
            },
            {
                "entity": {"v": "http://example.org/bob", "e": True},
                "context": "Bob is a person.",
            },
        ],
    }


@pytest.fixture
def empty_entities_message():
    return {
        "metadata": {
            "id": "doc-empty",
            "user": "u",
            "collection": "c",
        },
        "entities": [],
    }


class TestEntityContextsImportInitialization:

    def test_init_stores_references_correctly(
        self, mock_backend, mock_websocket, mock_running
    ):
        dispatcher = EntityContextsImport(
            ws=mock_websocket,
            running=mock_running,
            backend=mock_backend,
            queue="ec-queue",
        )

        assert dispatcher.ws is mock_websocket
        assert dispatcher.running is mock_running
        assert dispatcher.backend is mock_backend
        assert dispatcher.queue == "ec-queue"
        assert dispatcher.producer is None


class TestEntityContextsImportLifecycle:

    @pytest.mark.asyncio
    async def test_start_creates_producer(
        self, mock_backend, mock_websocket, mock_running, mock_producer
    ):
        mock_backend.create_producer = AsyncMock(return_value=mock_producer)

        dispatcher = EntityContextsImport(
            ws=mock_websocket, running=mock_running,
            backend=mock_backend, queue="q",
        )
        await dispatcher.start()

        mock_backend.create_producer.assert_called_once_with(
            topic="q", schema=EntityContexts,
        )
        assert dispatcher.producer is mock_producer

    @pytest.mark.asyncio
    async def test_destroy_stops_and_closes_properly(
        self, mock_backend, mock_websocket, mock_running, mock_producer
    ):
        mock_backend.create_producer = AsyncMock(return_value=mock_producer)

        dispatcher = EntityContextsImport(
            ws=mock_websocket, running=mock_running,
            backend=mock_backend, queue="q",
        )
        await dispatcher.start()
        await dispatcher.destroy()

        mock_running.stop.assert_called_once()
        mock_producer.close.assert_called_once()
        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_destroy_handles_none_websocket(
        self, mock_backend, mock_running, mock_producer
    ):
        mock_backend.create_producer = AsyncMock(return_value=mock_producer)

        dispatcher = EntityContextsImport(
            ws=None, running=mock_running,
            backend=mock_backend, queue="q",
        )
        await dispatcher.start()
        await dispatcher.destroy()

        mock_running.stop.assert_called_once()
        mock_producer.close.assert_called_once()


class TestEntityContextsImportMessageProcessing:
    """Regression coverage for receive(): catches Metadata/schema drift."""

    @pytest.mark.asyncio
    async def test_receive_constructs_entity_contexts_correctly(
        self, mock_backend, mock_websocket,
        mock_running, mock_producer, sample_message,
    ):
        mock_backend.create_producer = AsyncMock(return_value=mock_producer)

        dispatcher = EntityContextsImport(
            ws=mock_websocket, running=mock_running,
            backend=mock_backend, queue="q",
        )
        await dispatcher.start()

        mock_msg = Mock()
        mock_msg.json.return_value = sample_message

        # If Metadata or EntityContexts gain/lose kwargs, this raises
        # TypeError — exactly the regression we want to catch.
        await dispatcher.receive(mock_msg)

        mock_producer.send.assert_called_once()
        call_args = mock_producer.send.call_args

        sent = call_args[0][0]
        assert isinstance(sent, EntityContexts)
        assert isinstance(sent.metadata, Metadata)
        assert sent.metadata.id == "doc-123"
        assert sent.metadata.collection == "testcollection"

        assert len(sent.entities) == 2
        assert all(isinstance(e, EntityContext) for e in sent.entities)
        assert sent.entities[0].context == "Alice is a person."
        assert sent.entities[1].context == "Bob is a person."

    @pytest.mark.asyncio
    async def test_receive_handles_empty_entities(
        self, mock_backend, mock_websocket,
        mock_running, mock_producer, empty_entities_message,
    ):
        mock_backend.create_producer = AsyncMock(return_value=mock_producer)

        dispatcher = EntityContextsImport(
            ws=mock_websocket, running=mock_running,
            backend=mock_backend, queue="q",
        )
        await dispatcher.start()

        mock_msg = Mock()
        mock_msg.json.return_value = empty_entities_message

        await dispatcher.receive(mock_msg)

        mock_producer.send.assert_called_once()
        sent = mock_producer.send.call_args[0][0]
        assert isinstance(sent, EntityContexts)
        assert sent.entities == []
        assert sent.metadata.id == "doc-empty"

    @pytest.mark.asyncio
    async def test_receive_propagates_publisher_errors(
        self, mock_backend, mock_websocket,
        mock_running, sample_message,
    ):
        mock_producer = AsyncMock()
        mock_producer.send = AsyncMock(
            side_effect=RuntimeError("publish failed")
        )
        mock_backend.create_producer = AsyncMock(return_value=mock_producer)

        dispatcher = EntityContextsImport(
            ws=mock_websocket, running=mock_running,
            backend=mock_backend, queue="q",
        )
        await dispatcher.start()

        mock_msg = Mock()
        mock_msg.json.return_value = sample_message

        with pytest.raises(RuntimeError, match="publish failed"):
            await dispatcher.receive(mock_msg)
