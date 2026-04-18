"""
Unit tests for graph embeddings import dispatcher.

Tests the business logic of GraphEmbeddingsImport while mocking the
Publisher and websocket components.

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
    return Mock()


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

    @patch('trustgraph.gateway.dispatch.graph_embeddings_import.Publisher')
    def test_init_creates_publisher_with_correct_params(
        self, mock_publisher_class, mock_backend, mock_websocket, mock_running
    ):
        instance = Mock()
        mock_publisher_class.return_value = instance

        dispatcher = GraphEmbeddingsImport(
            ws=mock_websocket,
            running=mock_running,
            backend=mock_backend,
            queue="ge-queue",
        )

        mock_publisher_class.assert_called_once_with(
            mock_backend,
            topic="ge-queue",
            schema=GraphEmbeddings,
        )
        assert dispatcher.ws is mock_websocket
        assert dispatcher.running is mock_running
        assert dispatcher.publisher is instance


class TestGraphEmbeddingsImportLifecycle:

    @patch('trustgraph.gateway.dispatch.graph_embeddings_import.Publisher')
    @pytest.mark.asyncio
    async def test_start_calls_publisher_start(
        self, mock_publisher_class, mock_backend, mock_websocket, mock_running
    ):
        instance = Mock()
        instance.start = AsyncMock()
        mock_publisher_class.return_value = instance

        dispatcher = GraphEmbeddingsImport(
            ws=mock_websocket, running=mock_running,
            backend=mock_backend, queue="q",
        )
        await dispatcher.start()
        instance.start.assert_called_once()

    @patch('trustgraph.gateway.dispatch.graph_embeddings_import.Publisher')
    @pytest.mark.asyncio
    async def test_destroy_stops_and_closes_properly(
        self, mock_publisher_class, mock_backend, mock_websocket, mock_running
    ):
        instance = Mock()
        instance.stop = AsyncMock()
        mock_publisher_class.return_value = instance

        dispatcher = GraphEmbeddingsImport(
            ws=mock_websocket, running=mock_running,
            backend=mock_backend, queue="q",
        )
        await dispatcher.destroy()

        mock_running.stop.assert_called_once()
        instance.stop.assert_called_once()
        mock_websocket.close.assert_called_once()

    @patch('trustgraph.gateway.dispatch.graph_embeddings_import.Publisher')
    @pytest.mark.asyncio
    async def test_destroy_handles_none_websocket(
        self, mock_publisher_class, mock_backend, mock_running
    ):
        instance = Mock()
        instance.stop = AsyncMock()
        mock_publisher_class.return_value = instance

        dispatcher = GraphEmbeddingsImport(
            ws=None, running=mock_running,
            backend=mock_backend, queue="q",
        )
        await dispatcher.destroy()

        mock_running.stop.assert_called_once()
        instance.stop.assert_called_once()


class TestGraphEmbeddingsImportMessageProcessing:
    """Regression coverage for receive(): catches Metadata/schema drift."""

    @patch('trustgraph.gateway.dispatch.graph_embeddings_import.Publisher')
    @pytest.mark.asyncio
    async def test_receive_constructs_graph_embeddings_correctly(
        self, mock_publisher_class, mock_backend, mock_websocket,
        mock_running, sample_message,
    ):
        instance = Mock()
        instance.send = AsyncMock()
        mock_publisher_class.return_value = instance

        dispatcher = GraphEmbeddingsImport(
            ws=mock_websocket, running=mock_running,
            backend=mock_backend, queue="q",
        )

        mock_msg = Mock()
        mock_msg.json.return_value = sample_message

        # If Metadata, GraphEmbeddings, or EntityEmbeddings gain/lose
        # kwargs, this raises TypeError — exactly the regression we want
        # to catch.
        await dispatcher.receive(mock_msg)

        instance.send.assert_called_once()
        call_args = instance.send.call_args
        assert call_args[0][0] is None

        sent = call_args[0][1]
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

    @patch('trustgraph.gateway.dispatch.graph_embeddings_import.Publisher')
    @pytest.mark.asyncio
    async def test_receive_handles_empty_entities(
        self, mock_publisher_class, mock_backend, mock_websocket,
        mock_running, empty_entities_message,
    ):
        instance = Mock()
        instance.send = AsyncMock()
        mock_publisher_class.return_value = instance

        dispatcher = GraphEmbeddingsImport(
            ws=mock_websocket, running=mock_running,
            backend=mock_backend, queue="q",
        )

        mock_msg = Mock()
        mock_msg.json.return_value = empty_entities_message

        await dispatcher.receive(mock_msg)

        instance.send.assert_called_once()
        sent = instance.send.call_args[0][1]
        assert isinstance(sent, GraphEmbeddings)
        assert sent.entities == []
        assert sent.metadata.id == "doc-empty"

    @patch('trustgraph.gateway.dispatch.graph_embeddings_import.Publisher')
    @pytest.mark.asyncio
    async def test_receive_propagates_publisher_errors(
        self, mock_publisher_class, mock_backend, mock_websocket,
        mock_running, sample_message,
    ):
        instance = Mock()
        instance.send = AsyncMock(side_effect=RuntimeError("publish failed"))
        mock_publisher_class.return_value = instance

        dispatcher = GraphEmbeddingsImport(
            ws=mock_websocket, running=mock_running,
            backend=mock_backend, queue="q",
        )

        mock_msg = Mock()
        mock_msg.json.return_value = sample_message

        with pytest.raises(RuntimeError, match="publish failed"):
            await dispatcher.receive(mock_msg)
