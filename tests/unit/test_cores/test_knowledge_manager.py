"""
Unit tests for the KnowledgeManager class in cores/knowledge.py.

Tests the business logic of knowledge core loading with focus on collection
field handling while mocking external dependencies like Cassandra and Pulsar.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from unittest.mock import call

from trustgraph.cores.knowledge import KnowledgeManager
from trustgraph.schema import (
    KnowledgeResponse, Triples, GraphEmbeddings, Metadata, Triple, Term,
    EntityEmbeddings, IRI, LITERAL,
    LibraryMetadata, LibraryBlob,
    LibrarianResponse, DocumentMetadata,
)


@pytest.fixture
def mock_table_store():
    """Mock KnowledgeTableStore."""
    mock_store = AsyncMock()
    mock_store.get_triples = AsyncMock()
    mock_store.get_graph_embeddings = AsyncMock()
    return mock_store


@pytest.fixture
def mock_flow_config():
    """Mock flow configuration."""
    mock_config = Mock()
    mock_config.flows = {
        "test-user": {
            "test-flow": {
                "interfaces": {
                    "triples-store": {"flow": "test-triples-queue"},
                    "graph-embeddings-store": {"flow": "test-ge-queue"}
                }
            }
        }
    }
    mock_config.pulsar_client = AsyncMock()
    return mock_config


@pytest.fixture
def mock_request():
    """Mock knowledge load request."""
    request = Mock()
    request.id = "test-doc-id"
    request.collection = "test-collection"
    request.flow = "test-flow"
    return request


@pytest.fixture
def knowledge_manager(mock_flow_config):
    """Create KnowledgeManager instance with mocked dependencies."""
    with patch('trustgraph.cores.knowledge.KnowledgeTableStore') as mock_store_class:
        manager = KnowledgeManager(
            cassandra_host=["localhost"],
            cassandra_username="test_user", 
            cassandra_password="test_pass",
            keyspace="test_keyspace",
            flow_config=mock_flow_config
        )
        manager.table_store = AsyncMock()
        return manager


@pytest.fixture
def sample_triples():
    """Sample triples data for testing."""
    return Triples(
        metadata=Metadata(
            id="test-doc-id",
            collection="default",  # This should be overridden
        ),
        triples=[
            Triple(
                s=Term(type=IRI, iri="http://example.org/john"),
                p=Term(type=IRI, iri="http://example.org/name"),
                o=Term(type=LITERAL, value="John Smith")
            )
        ]
    )


@pytest.fixture
def sample_graph_embeddings():
    """Sample graph embeddings data for testing."""
    return GraphEmbeddings(
        metadata=Metadata(
            id="test-doc-id",
            collection="default",  # This should be overridden
        ),
        entities=[
            EntityEmbeddings(
                entity=Term(type=IRI, iri="http://example.org/john"),
                vector=[0.1, 0.2, 0.3]
            )
        ]
    )


class TestKnowledgeManagerLoadCore:
    """Test knowledge core loading functionality."""

    @pytest.mark.asyncio
    async def test_load_kg_core_sets_collection_in_triples(self, knowledge_manager, mock_request, sample_triples):
        """Test that load_kg_core properly sets collection field in published triples."""
        mock_respond = AsyncMock()
        
        # Mock the table store to return sample triples
        async def mock_get_triples(user, doc_id, receiver):
            await receiver(sample_triples)
        
        knowledge_manager.table_store.get_triples = mock_get_triples
        
        async def mock_get_graph_embeddings(user, doc_id, receiver):
            # No graph embeddings for this test
            pass
            
        knowledge_manager.table_store.get_graph_embeddings = mock_get_graph_embeddings
        
        # Mock publishers
        mock_triples_pub = AsyncMock()
        mock_ge_pub = AsyncMock()
        
        with patch('trustgraph.cores.knowledge.Publisher') as mock_publisher_class:
            mock_publisher_class.side_effect = [mock_triples_pub, mock_ge_pub]
            
            # Start the core loader background task
            knowledge_manager.background_task = None
            await knowledge_manager.load_kg_core(mock_request, mock_respond, "test-user")

            # Wait for background processing
            import asyncio
            await asyncio.sleep(0.1)

            # Verify publishers were created and started
            assert mock_publisher_class.call_count == 2
            mock_triples_pub.start.assert_called_once()
            mock_ge_pub.start.assert_called_once()

            # Verify triples were sent with correct collection
            mock_triples_pub.send.assert_called_once()
            sent_triples = mock_triples_pub.send.call_args[0][1]
            assert sent_triples.metadata.collection == "test-collection"
            assert sent_triples.metadata.id == "test-doc-id"

    @pytest.mark.asyncio
    async def test_load_kg_core_sets_collection_in_graph_embeddings(self, knowledge_manager, mock_request, sample_graph_embeddings):
        """Test that load_kg_core properly sets collection field in published graph embeddings."""
        mock_respond = AsyncMock()
        
        async def mock_get_triples(user, doc_id, receiver):
            # No triples for this test
            pass
            
        knowledge_manager.table_store.get_triples = mock_get_triples
        
        # Mock the table store to return sample graph embeddings
        async def mock_get_graph_embeddings(user, doc_id, receiver):
            await receiver(sample_graph_embeddings)
        
        knowledge_manager.table_store.get_graph_embeddings = mock_get_graph_embeddings
        
        # Mock publishers
        mock_triples_pub = AsyncMock()
        mock_ge_pub = AsyncMock()
        
        with patch('trustgraph.cores.knowledge.Publisher') as mock_publisher_class:
            mock_publisher_class.side_effect = [mock_triples_pub, mock_ge_pub]
            
            # Start the core loader background task
            knowledge_manager.background_task = None
            await knowledge_manager.load_kg_core(mock_request, mock_respond, "test-user")

            # Wait for background processing
            import asyncio
            await asyncio.sleep(0.1)

            # Verify graph embeddings were sent with correct collection
            mock_ge_pub.send.assert_called_once()
            sent_ge = mock_ge_pub.send.call_args[0][1] 
            assert sent_ge.metadata.collection == "test-collection"
            assert sent_ge.metadata.id == "test-doc-id"

    @pytest.mark.asyncio 
    async def test_load_kg_core_falls_back_to_default_collection(self, knowledge_manager, sample_triples):
        """Test that load_kg_core falls back to 'default' when request.collection is None."""
        # Create request with None collection
        mock_request = Mock()
        mock_request.id = "test-doc-id"
        mock_request.collection = None  # Should fall back to "default"
        mock_request.flow = "test-flow"
        
        mock_respond = AsyncMock()
        
        async def mock_get_triples(user, doc_id, receiver):
            await receiver(sample_triples)
        
        knowledge_manager.table_store.get_triples = mock_get_triples
        knowledge_manager.table_store.get_graph_embeddings = AsyncMock()
        
        # Mock publishers
        mock_triples_pub = AsyncMock()
        mock_ge_pub = AsyncMock()
        
        with patch('trustgraph.cores.knowledge.Publisher') as mock_publisher_class:
            mock_publisher_class.side_effect = [mock_triples_pub, mock_ge_pub]
            
            # Start the core loader background task
            knowledge_manager.background_task = None
            await knowledge_manager.load_kg_core(mock_request, mock_respond, "test-user")

            # Wait for background processing
            import asyncio
            await asyncio.sleep(0.1)

            # Verify triples were sent with default collection
            mock_triples_pub.send.assert_called_once()
            sent_triples = mock_triples_pub.send.call_args[0][1]
            assert sent_triples.metadata.collection == "default"

    @pytest.mark.asyncio
    async def test_load_kg_core_handles_both_triples_and_graph_embeddings(self, knowledge_manager, mock_request, sample_triples, sample_graph_embeddings):
        """Test that load_kg_core handles both triples and graph embeddings with correct collection."""
        mock_respond = AsyncMock()
        
        async def mock_get_triples(user, doc_id, receiver):
            await receiver(sample_triples)
        
        async def mock_get_graph_embeddings(user, doc_id, receiver):
            await receiver(sample_graph_embeddings)
        
        knowledge_manager.table_store.get_triples = mock_get_triples
        knowledge_manager.table_store.get_graph_embeddings = mock_get_graph_embeddings
        
        # Mock publishers
        mock_triples_pub = AsyncMock()
        mock_ge_pub = AsyncMock()
        
        with patch('trustgraph.cores.knowledge.Publisher') as mock_publisher_class:
            mock_publisher_class.side_effect = [mock_triples_pub, mock_ge_pub]
            
            # Start the core loader background task
            knowledge_manager.background_task = None
            await knowledge_manager.load_kg_core(mock_request, mock_respond, "test-user")

            # Wait for background processing
            import asyncio
            await asyncio.sleep(0.1)

            # Verify both publishers were used with correct collection
            mock_triples_pub.send.assert_called_once()
            sent_triples = mock_triples_pub.send.call_args[0][1]
            assert sent_triples.metadata.collection == "test-collection"
            
            mock_ge_pub.send.assert_called_once()
            sent_ge = mock_ge_pub.send.call_args[0][1]
            assert sent_ge.metadata.collection == "test-collection"

    @pytest.mark.asyncio
    async def test_load_kg_core_validates_flow_configuration(self, knowledge_manager):
        """Test that load_kg_core validates flow configuration before processing."""
        # Request with invalid flow
        mock_request = Mock()
        mock_request.id = "test-doc-id"
        mock_request.collection = "test-collection"
        mock_request.flow = "invalid-flow"  # Not in mock_flow_config.flows
        
        mock_respond = AsyncMock()
        
        # Start the core loader background task
        knowledge_manager.background_task = None
        await knowledge_manager.load_kg_core(mock_request, mock_respond, "test-user")

        # Wait for background processing
        import asyncio
        await asyncio.sleep(0.1)

        # Should have responded with error
        mock_respond.assert_called()
        response = mock_respond.call_args[0][0]
        assert response.error is not None
        assert "Invalid flow" in response.error.message

    @pytest.mark.asyncio
    async def test_load_kg_core_requires_id_and_flow(self, knowledge_manager):
        """Test that load_kg_core validates required fields."""
        mock_respond = AsyncMock()
        
        # Test missing ID
        mock_request = Mock()
        mock_request.id = None  # Missing
        mock_request.collection = "test-collection"
        mock_request.flow = "test-flow"
        
        knowledge_manager.background_task = None
        await knowledge_manager.load_kg_core(mock_request, mock_respond, "test-user")

        # Wait for background processing
        import asyncio
        await asyncio.sleep(0.1)

        # Should respond with error
        mock_respond.assert_called()
        response = mock_respond.call_args[0][0]
        assert response.error is not None
        assert "Core ID must be specified" in response.error.message


class TestKnowledgeManagerOtherMethods:
    """Test other KnowledgeManager methods for completeness."""

    @pytest.mark.asyncio
    async def test_get_kg_core_preserves_collection_from_store(self, knowledge_manager, sample_triples):
        """Test that get_kg_core preserves collection field from stored data."""
        mock_request = Mock()
        mock_request.id = "test-doc-id"

        mock_respond = AsyncMock()

        async def mock_get_triples(user, doc_id, receiver):
            await receiver(sample_triples)

        knowledge_manager.table_store.get_triples = mock_get_triples
        knowledge_manager.table_store.get_graph_embeddings = AsyncMock()

        await knowledge_manager.get_kg_core(mock_request, mock_respond, "test-user")
        
        # Should have called respond for triples and final EOS
        assert mock_respond.call_count >= 2
        
        # Find the triples response
        triples_response = None
        for call_args in mock_respond.call_args_list:
            response = call_args[0][0]
            if response.triples is not None:
                triples_response = response
                break
        
        assert triples_response is not None
        assert triples_response.triples.metadata.collection == "default"  # From sample data

    @pytest.mark.asyncio
    async def test_list_kg_cores(self, knowledge_manager):
        """Test listing knowledge cores."""
        mock_request = Mock()

        mock_respond = AsyncMock()

        # Mock return value
        knowledge_manager.table_store.list_kg_cores.return_value = ["doc1", "doc2", "doc3"]

        await knowledge_manager.list_kg_cores(mock_request, mock_respond, "test-user")
        
        # Verify table store was called correctly
        knowledge_manager.table_store.list_kg_cores.assert_called_once_with("test-user")
        
        # Verify response
        mock_respond.assert_called_once()
        response = mock_respond.call_args[0][0]
        assert response.ids == ["doc1", "doc2", "doc3"]
        assert response.error is None

    @pytest.mark.asyncio
    async def test_delete_kg_core(self, knowledge_manager):
        """Test deleting knowledge cores."""
        mock_request = Mock()
        mock_request.id = "test-doc-id"

        mock_respond = AsyncMock()

        await knowledge_manager.delete_kg_core(mock_request, mock_respond, "test-user")

        # Verify table store was called correctly
        knowledge_manager.table_store.delete_kg_core.assert_called_once_with("test-user", "test-doc-id")

        # Verify response
        mock_respond.assert_called_once()
        response = mock_respond.call_args[0][0]
        assert response.error is None


class TestKnowledgeManagerLibraryDownload:
    """Test get_kg_core streaming of library documents."""

    @pytest.fixture
    def manager_with_librarian(self, mock_flow_config):
        with patch('trustgraph.cores.knowledge.KnowledgeTableStore'):
            mock_librarian = AsyncMock()
            manager = KnowledgeManager(
                cassandra_host=["localhost"],
                cassandra_username="test_user",
                cassandra_password="test_pass",
                keyspace="test_keyspace",
                flow_config=mock_flow_config,
                librarian_clients={"test-user": mock_librarian},
            )
            manager.table_store = AsyncMock()
            manager._mock_librarian = mock_librarian
            return manager

    @pytest.mark.asyncio
    async def test_get_kg_core_streams_library_docs(self, manager_with_librarian):
        mock_request = Mock()
        mock_request.id = "root-doc"
        mock_respond = AsyncMock()
        librarian = manager_with_librarian._mock_librarian

        manager_with_librarian.table_store.get_triples = AsyncMock()
        manager_with_librarian.table_store.get_graph_embeddings = AsyncMock()

        root_meta = DocumentMetadata(
            id="root-doc", kind="application/pdf", title="Test PDF",
            document_type="source",
        )
        child_meta = DocumentMetadata(
            id="chunk-1", kind="text/plain", title="Chunk 1",
            parent_id="root-doc", document_type="chunk",
        )

        librarian.fetch_document_metadata.return_value = root_meta
        librarian.request.side_effect = [
            LibrarianResponse(document_metadatas=[child_meta]),
            LibrarianResponse(document_metadatas=[]),
        ]
        librarian.fetch_document_content.side_effect = [
            b"cm9vdCBjb250ZW50",
            b"Y2h1bmsgY29udGVudA==",
        ]

        await manager_with_librarian.get_kg_core(
            mock_request, mock_respond, "test-user"
        )

        responses = [c[0][0] for c in mock_respond.call_args_list]

        lm_responses = [r for r in responses if r.library_metadata is not None]
        lb_responses = [r for r in responses if r.library_blob is not None]
        eos_responses = [r for r in responses if r.eos is True]

        assert len(lm_responses) == 2
        assert lm_responses[0].library_metadata.id == "root-doc"
        assert lm_responses[0].library_metadata.document_type == "source"
        assert lm_responses[1].library_metadata.id == "chunk-1"
        assert lm_responses[1].library_metadata.parent_id == "root-doc"

        assert len(lb_responses) == 2
        assert lb_responses[0].library_blob.id == "root-doc"
        assert lb_responses[0].library_blob.data == b"cm9vdCBjb250ZW50"
        assert lb_responses[1].library_blob.id == "chunk-1"

        assert len(eos_responses) == 1

    @pytest.mark.asyncio
    async def test_get_kg_core_no_librarian_skips_library(self, mock_flow_config):
        with patch('trustgraph.cores.knowledge.KnowledgeTableStore'):
            manager = KnowledgeManager(
                cassandra_host=["localhost"],
                cassandra_username="u", cassandra_password="p",
                keyspace="ks", flow_config=mock_flow_config,
            )
            manager.table_store = AsyncMock()
            manager.table_store.get_triples = AsyncMock()
            manager.table_store.get_graph_embeddings = AsyncMock()

        mock_request = Mock()
        mock_request.id = "doc-1"
        mock_respond = AsyncMock()

        await manager.get_kg_core(mock_request, mock_respond, "w")

        responses = [c[0][0] for c in mock_respond.call_args_list]
        assert all(r.library_metadata is None for r in responses)
        assert all(r.library_blob is None for r in responses)

    @pytest.mark.asyncio
    async def test_get_kg_core_librarian_metadata_failure_is_graceful(
        self, manager_with_librarian,
    ):
        mock_request = Mock()
        mock_request.id = "missing-doc"
        mock_respond = AsyncMock()

        manager_with_librarian.table_store.get_triples = AsyncMock()
        manager_with_librarian.table_store.get_graph_embeddings = AsyncMock()
        manager_with_librarian._mock_librarian.fetch_document_metadata.side_effect = (
            RuntimeError("not found")
        )

        await manager_with_librarian.get_kg_core(
            mock_request, mock_respond, "test-user"
        )

        responses = [c[0][0] for c in mock_respond.call_args_list]
        assert all(r.library_metadata is None for r in responses)
        assert any(r.eos for r in responses)


class TestKnowledgeManagerLibraryUpload:
    """Test put_kg_core handling of library metadata and blob records."""

    @pytest.fixture
    def manager_with_librarian(self, mock_flow_config):
        with patch('trustgraph.cores.knowledge.KnowledgeTableStore'):
            mock_librarian = AsyncMock()
            manager = KnowledgeManager(
                cassandra_host=["localhost"],
                cassandra_username="u", cassandra_password="p",
                keyspace="ks", flow_config=mock_flow_config,
                librarian_clients={"ws": mock_librarian},
            )
            manager.table_store = AsyncMock()
            manager._mock_librarian = mock_librarian
            return manager

    @pytest.mark.asyncio
    async def test_put_metadata_then_blob_calls_librarian(
        self, manager_with_librarian,
    ):
        mock_respond = AsyncMock()
        librarian = manager_with_librarian._mock_librarian
        librarian.request.return_value = LibrarianResponse()

        # First call: metadata
        req_meta = Mock()
        req_meta.triples = None
        req_meta.graph_embeddings = None
        req_meta.library_metadata = LibraryMetadata(
            id="doc-1", kind="application/pdf", title="Test",
            document_type="source",
        )
        req_meta.library_blob = None
        await manager_with_librarian.put_kg_core(req_meta, mock_respond, "ws")

        # Metadata is buffered, librarian not called yet
        librarian.request.assert_not_called()

        # Second call: blob
        req_blob = Mock()
        req_blob.triples = None
        req_blob.graph_embeddings = None
        req_blob.library_metadata = None
        req_blob.library_blob = LibraryBlob(
            id="doc-1", data=b"dGVzdA==",
        )
        await manager_with_librarian.put_kg_core(req_blob, mock_respond, "ws")

        # Now librarian should have been called with add-document
        librarian.request.assert_called_once()
        call_args = librarian.request.call_args[0][0]
        assert call_args.operation == "add-document"
        assert call_args.document_metadata.id == "doc-1"
        assert call_args.document_metadata.kind == "application/pdf"
        assert call_args.content == b"dGVzdA=="

    @pytest.mark.asyncio
    async def test_put_child_document_uses_add_child_operation(
        self, manager_with_librarian,
    ):
        mock_respond = AsyncMock()
        librarian = manager_with_librarian._mock_librarian
        librarian.request.return_value = LibrarianResponse()

        req_meta = Mock()
        req_meta.triples = None
        req_meta.graph_embeddings = None
        req_meta.library_metadata = LibraryMetadata(
            id="chunk-1", kind="text/plain", title="Chunk",
            parent_id="doc-1", document_type="chunk",
        )
        req_meta.library_blob = None
        await manager_with_librarian.put_kg_core(req_meta, mock_respond, "ws")

        req_blob = Mock()
        req_blob.triples = None
        req_blob.graph_embeddings = None
        req_blob.library_metadata = None
        req_blob.library_blob = LibraryBlob(id="chunk-1", data=b"Y2h1bms=")
        await manager_with_librarian.put_kg_core(req_blob, mock_respond, "ws")

        call_args = librarian.request.call_args[0][0]
        assert call_args.operation == "add-child-document"
        assert call_args.document_metadata.parent_id == "doc-1"

    @pytest.mark.asyncio
    async def test_put_blob_without_metadata_logs_warning(
        self, manager_with_librarian,
    ):
        mock_respond = AsyncMock()
        librarian = manager_with_librarian._mock_librarian

        req_blob = Mock()
        req_blob.triples = None
        req_blob.graph_embeddings = None
        req_blob.library_metadata = None
        req_blob.library_blob = LibraryBlob(id="orphan", data=b"data")
        await manager_with_librarian.put_kg_core(req_blob, mock_respond, "ws")

        # Librarian should not be called for orphan blob
        librarian.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_put_existing_document_is_graceful(
        self, manager_with_librarian,
    ):
        mock_respond = AsyncMock()
        librarian = manager_with_librarian._mock_librarian
        librarian.request.side_effect = RuntimeError(
            "Document already exists"
        )

        req_meta = Mock()
        req_meta.triples = None
        req_meta.graph_embeddings = None
        req_meta.library_metadata = LibraryMetadata(
            id="doc-1", kind="application/pdf", title="Test",
            document_type="source",
        )
        req_meta.library_blob = None
        await manager_with_librarian.put_kg_core(req_meta, mock_respond, "ws")

        req_blob = Mock()
        req_blob.triples = None
        req_blob.graph_embeddings = None
        req_blob.library_metadata = None
        req_blob.library_blob = LibraryBlob(id="doc-1", data=b"data")
        await manager_with_librarian.put_kg_core(req_blob, mock_respond, "ws")

        # Should not raise — "already exists" is handled gracefully