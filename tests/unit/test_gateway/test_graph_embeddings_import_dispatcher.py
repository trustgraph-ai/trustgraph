"""
Unit tests for graph embeddings import dispatcher.

Tests the business logic of GraphEmbeddingsImport while mocking the
async producer and websocket components.

Regression coverage: a previous version of EntityContextsImport
constructed Metadata(metadata=...) which raised TypeError at runtime as
soon as a message was received. The same shape of bug can occur here, so
these tests exercise receive() end-to-end to catch any future schema or
kwarg drift in Metadata / GraphEmbeddings / EntityEmbeddings construction.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from trustgraph.gateway.dispatch.graph_embeddings_import import GraphEmbeddingsImport
from trustgraph.schema import GraphEmbeddings, EntityEmbeddings, Metadata


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
    """Sample graph-embeddings websocket message."""
    return {
        "metadata": {
            "id": "doc-123",
            "user": "testuser",
            "collection": "testcollection",
        },
        "entities": [
            {
                "entity": {"v": "http://example.org/alice", "e": True},
                "vector": [0.1, 0.2, 0.3],
            },
            {
                "entity": {"v": "http://example.org/bob", "e": True},
                "vector": [0.4, 0.5, 0.6],
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


class TestGraphEmbeddingsImportInitialization:

    def test_init_stores_references_correctly(
        self, mock_backend, mock_websocket, mock_running
    ):
        dispatcher = GraphEmbeddingsImport(
            ws=mock_websocket,
            running=mock_running,
            backend=mock_backend,
            queue="ge-queue",
        )

        assert dispatcher.ws is mock_websocket
        assert dispatcher.running is mock_running
        assert dispatcher.backend is mock_backend
        assert dispatcher.queue == "ge-queue"
        assert dispatcher.producer is None


class TestGraphEmbeddingsImportLifecycle:

    @pytest.mark.asyncio
    async def test_start_creates_producer(
        self, mock_backend, mock_websocket, mock_running, mock_producer
    ):
        mock_backend.create_producer = AsyncMock(return_value=mock_producer)

        dispatcher = GraphEmbeddingsImport(
            ws=mock_websocket, running=mock_running,
            backend=mock_backend, queue="q",
        )
        await dispatcher.start()

        mock_backend.create_producer.assert_called_once_with(
            topic="q", schema=GraphEmbeddings,
        )
        assert dispatcher.producer is mock_producer

    @pytest.mark.asyncio
    async def test_destroy_stops_and_closes_properly(
        self, mock_backend, mock_websocket, mock_running, mock_producer
    ):
        mock_backend.create_producer = AsyncMock(return_value=mock_producer)

        dispatcher = GraphEmbeddingsImport(
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

        dispatcher = GraphEmbeddingsImport(
            ws=None, running=mock_running,
            backend=mock_backend, queue="q",
        )
        await dispatcher.start()
        await dispatcher.destroy()

        mock_running.stop.assert_called_once()
        mock_producer.close.assert_called_once()


class TestGraphEmbeddingsImportMessageProcessing:
    """Regression coverage for receive(): catches Metadata/schema drift."""

    @pytest.mark.asyncio
    async def test_receive_constructs_graph_embeddings_correctly(
        self, mock_backend, mock_websocket,
        mock_running, mock_producer, sample_message,
    ):
        mock_backend.create_producer = AsyncMock(return_value=mock_producer)

        dispatcher = GraphEmbeddingsImport(
            ws=mock_websocket, running=mock_running,
            backend=mock_backend, queue="q",
        )
        await dispatcher.start()

        mock_msg = Mock()
        mock_msg.json.return_value = sample_message

        await dispatcher.receive(mock_msg)

        mock_producer.send.assert_called_once()
        call_args = mock_producer.send.call_args

        sent = call_args[0][0]
        assert isinstance(sent, GraphEmbeddings)
        assert isinstance(sent.metadata, Metadata)
        assert sent.metadata.id == "doc-123"
        assert sent.metadata.collection == "testcollection"

        assert len(sent.entities) == 2
        assert all(isinstance(e, EntityEmbeddings) for e in sent.entities)
        # Lock in the wire format: incoming "vector" key (singular,
        # list[float]) maps to EntityEmbeddings.vector. This mirrors
        # serialize_graph_embeddings() on the export side.
        assert sent.entities[0].vector == [0.1, 0.2, 0.3]
        assert sent.entities[1].vector == [0.4, 0.5, 0.6]

    @pytest.mark.asyncio
    async def test_receive_handles_empty_entities(
        self, mock_backend, mock_websocket,
        mock_running, mock_producer, empty_entities_message,
    ):
        mock_backend.create_producer = AsyncMock(return_value=mock_producer)

        dispatcher = GraphEmbeddingsImport(
            ws=mock_websocket, running=mock_running,
            backend=mock_backend, queue="q",
        )
        await dispatcher.start()

        mock_msg = Mock()
        mock_msg.json.return_value = empty_entities_message

        await dispatcher.receive(mock_msg)

        mock_producer.send.assert_called_once()
        sent = mock_producer.send.call_args[0][0]
        assert isinstance(sent, GraphEmbeddings)
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

        dispatcher = GraphEmbeddingsImport(
            ws=mock_websocket, running=mock_running,
            backend=mock_backend, queue="q",
        )
        await dispatcher.start()

        mock_msg = Mock()
        mock_msg.json.return_value = sample_message

        with pytest.raises(RuntimeError, match="publish failed"):
            await dispatcher.receive(mock_msg)
