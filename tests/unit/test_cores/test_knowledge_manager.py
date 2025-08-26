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
from trustgraph.schema import KnowledgeResponse, Triples, GraphEmbeddings, Metadata, Triple, Value, EntityEmbeddings


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
        "test-flow": {
            "interfaces": {
                "triples-store": "test-triples-queue",
                "graph-embeddings-store": "test-ge-queue"
            }
        }
    }
    mock_config.pulsar_client = AsyncMock()
    return mock_config


@pytest.fixture
def mock_request():
    """Mock knowledge load request."""
    request = Mock()
    request.user = "test-user"
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
            cassandra_user="test_user", 
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
            user="test-user", 
            collection="default",  # This should be overridden
            metadata=[]
        ),
        triples=[
            Triple(
                s=Value(value="http://example.org/john", is_uri=True),
                p=Value(value="http://example.org/name", is_uri=True),
                o=Value(value="John Smith", is_uri=False)
            )
        ]
    )


@pytest.fixture
def sample_graph_embeddings():
    """Sample graph embeddings data for testing."""
    return GraphEmbeddings(
        metadata=Metadata(
            id="test-doc-id",
            user="test-user",
            collection="default",  # This should be overridden
            metadata=[]
        ),
        entities=[
            EntityEmbeddings(
                entity=Value(value="http://example.org/john", is_uri=True),
                vectors=[[0.1, 0.2, 0.3]]
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
            await knowledge_manager.load_kg_core(mock_request, mock_respond)
            
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
            assert sent_triples.metadata.user == "test-user"
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
            await knowledge_manager.load_kg_core(mock_request, mock_respond)
            
            # Wait for background processing
            import asyncio
            await asyncio.sleep(0.1)
            
            # Verify graph embeddings were sent with correct collection
            mock_ge_pub.send.assert_called_once()
            sent_ge = mock_ge_pub.send.call_args[0][1] 
            assert sent_ge.metadata.collection == "test-collection"
            assert sent_ge.metadata.user == "test-user"
            assert sent_ge.metadata.id == "test-doc-id"

    @pytest.mark.asyncio 
    async def test_load_kg_core_falls_back_to_default_collection(self, knowledge_manager, sample_triples):
        """Test that load_kg_core falls back to 'default' when request.collection is None."""
        # Create request with None collection
        mock_request = Mock()
        mock_request.user = "test-user"
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
            await knowledge_manager.load_kg_core(mock_request, mock_respond)
            
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
            await knowledge_manager.load_kg_core(mock_request, mock_respond)
            
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
        mock_request.user = "test-user"
        mock_request.id = "test-doc-id"
        mock_request.collection = "test-collection"
        mock_request.flow = "invalid-flow"  # Not in mock_flow_config.flows
        
        mock_respond = AsyncMock()
        
        # Start the core loader background task
        knowledge_manager.background_task = None
        await knowledge_manager.load_kg_core(mock_request, mock_respond)
        
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
        mock_request.user = "test-user"
        mock_request.id = None  # Missing
        mock_request.collection = "test-collection"
        mock_request.flow = "test-flow"
        
        knowledge_manager.background_task = None
        await knowledge_manager.load_kg_core(mock_request, mock_respond)
        
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
        mock_request.user = "test-user"
        mock_request.id = "test-doc-id"
        
        mock_respond = AsyncMock()
        
        async def mock_get_triples(user, doc_id, receiver):
            await receiver(sample_triples)
        
        knowledge_manager.table_store.get_triples = mock_get_triples
        knowledge_manager.table_store.get_graph_embeddings = AsyncMock()
        
        await knowledge_manager.get_kg_core(mock_request, mock_respond)
        
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
        mock_request.user = "test-user"
        
        mock_respond = AsyncMock()
        
        # Mock return value
        knowledge_manager.table_store.list_kg_cores.return_value = ["doc1", "doc2", "doc3"]
        
        await knowledge_manager.list_kg_cores(mock_request, mock_respond)
        
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
        mock_request.user = "test-user"
        mock_request.id = "test-doc-id"
        
        mock_respond = AsyncMock()
        
        await knowledge_manager.delete_kg_core(mock_request, mock_respond)
        
        # Verify table store was called correctly
        knowledge_manager.table_store.delete_kg_core.assert_called_once_with("test-user", "test-doc-id")
        
        # Verify response
        mock_respond.assert_called_once()
        response = mock_respond.call_args[0][0]
        assert response.error is None