"""
Tests for GraphRAG retrieval implementation
"""

import pytest
import unittest.mock
from unittest.mock import MagicMock, AsyncMock

from trustgraph.retrieval.graph_rag.graph_rag import GraphRag, Query


class TestGraphRag:
    """Test cases for GraphRag class"""

    def test_graph_rag_initialization_with_defaults(self):
        """Test GraphRag initialization with default verbose setting"""
        # Create mock clients
        mock_prompt_client = MagicMock()
        mock_embeddings_client = MagicMock()
        mock_graph_embeddings_client = MagicMock()
        mock_triples_client = MagicMock()
        
        # Initialize GraphRag
        graph_rag = GraphRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            graph_embeddings_client=mock_graph_embeddings_client,
            triples_client=mock_triples_client
        )
        
        # Verify initialization
        assert graph_rag.prompt_client == mock_prompt_client
        assert graph_rag.embeddings_client == mock_embeddings_client
        assert graph_rag.graph_embeddings_client == mock_graph_embeddings_client
        assert graph_rag.triples_client == mock_triples_client
        assert graph_rag.verbose is False  # Default value
        assert graph_rag.label_cache == {}  # Empty cache initially

    def test_graph_rag_initialization_with_verbose(self):
        """Test GraphRag initialization with verbose enabled"""
        # Create mock clients
        mock_prompt_client = MagicMock()
        mock_embeddings_client = MagicMock()
        mock_graph_embeddings_client = MagicMock()
        mock_triples_client = MagicMock()
        
        # Initialize GraphRag with verbose=True
        graph_rag = GraphRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            graph_embeddings_client=mock_graph_embeddings_client,
            triples_client=mock_triples_client,
            verbose=True
        )
        
        # Verify initialization
        assert graph_rag.prompt_client == mock_prompt_client
        assert graph_rag.embeddings_client == mock_embeddings_client
        assert graph_rag.graph_embeddings_client == mock_graph_embeddings_client
        assert graph_rag.triples_client == mock_triples_client
        assert graph_rag.verbose is True
        assert graph_rag.label_cache == {}  # Empty cache initially


class TestQuery:
    """Test cases for Query class"""

    def test_query_initialization_with_defaults(self):
        """Test Query initialization with default parameters"""
        # Create mock GraphRag
        mock_rag = MagicMock()
        
        # Initialize Query with defaults
        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False
        )
        
        # Verify initialization
        assert query.rag == mock_rag
        assert query.user == "test_user"
        assert query.collection == "test_collection"
        assert query.verbose is False
        assert query.entity_limit == 50  # Default value
        assert query.triple_limit == 30  # Default value
        assert query.max_subgraph_size == 1000  # Default value
        assert query.max_path_length == 2  # Default value

    def test_query_initialization_with_custom_params(self):
        """Test Query initialization with custom parameters"""
        # Create mock GraphRag
        mock_rag = MagicMock()
        
        # Initialize Query with custom parameters
        query = Query(
            rag=mock_rag,
            user="custom_user",
            collection="custom_collection",
            verbose=True,
            entity_limit=100,
            triple_limit=60,
            max_subgraph_size=2000,
            max_path_length=3
        )
        
        # Verify initialization
        assert query.rag == mock_rag
        assert query.user == "custom_user"
        assert query.collection == "custom_collection"
        assert query.verbose is True
        assert query.entity_limit == 100
        assert query.triple_limit == 60
        assert query.max_subgraph_size == 2000
        assert query.max_path_length == 3

    @pytest.mark.asyncio
    async def test_get_vector_method(self):
        """Test Query.get_vector method calls embeddings client correctly"""
        # Create mock GraphRag with embeddings client
        mock_rag = MagicMock()
        mock_embeddings_client = AsyncMock()
        mock_rag.embeddings_client = mock_embeddings_client
        
        # Mock the embed method to return test vectors
        expected_vectors = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_embeddings_client.embed.return_value = expected_vectors
        
        # Initialize Query
        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False
        )
        
        # Call get_vector
        test_query = "What is the capital of France?"
        result = await query.get_vector(test_query)
        
        # Verify embeddings client was called correctly
        mock_embeddings_client.embed.assert_called_once_with(test_query)
        
        # Verify result matches expected vectors
        assert result == expected_vectors

    @pytest.mark.asyncio
    async def test_get_vector_method_with_verbose(self):
        """Test Query.get_vector method with verbose output"""
        # Create mock GraphRag with embeddings client
        mock_rag = MagicMock()
        mock_embeddings_client = AsyncMock()
        mock_rag.embeddings_client = mock_embeddings_client
        
        # Mock the embed method
        expected_vectors = [[0.7, 0.8, 0.9]]
        mock_embeddings_client.embed.return_value = expected_vectors
        
        # Initialize Query with verbose=True
        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=True
        )
        
        # Call get_vector
        test_query = "Test query for embeddings"
        result = await query.get_vector(test_query)
        
        # Verify embeddings client was called correctly
        mock_embeddings_client.embed.assert_called_once_with(test_query)
        
        # Verify result matches expected vectors
        assert result == expected_vectors

    @pytest.mark.asyncio
    async def test_get_entities_method(self):
        """Test Query.get_entities method retrieves entities correctly"""
        # Create mock GraphRag with clients
        mock_rag = MagicMock()
        mock_embeddings_client = AsyncMock()
        mock_graph_embeddings_client = AsyncMock()
        mock_rag.embeddings_client = mock_embeddings_client
        mock_rag.graph_embeddings_client = mock_graph_embeddings_client
        
        # Mock the embedding and entity query responses
        test_vectors = [[0.1, 0.2, 0.3]]
        mock_embeddings_client.embed.return_value = test_vectors
        
        # Mock entity objects that have string representation
        mock_entity1 = MagicMock()
        mock_entity1.__str__ = MagicMock(return_value="entity1")
        mock_entity2 = MagicMock()
        mock_entity2.__str__ = MagicMock(return_value="entity2")
        mock_graph_embeddings_client.query.return_value = [mock_entity1, mock_entity2]
        
        # Initialize Query
        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False,
            entity_limit=25
        )
        
        # Call get_entities
        test_query = "Find related entities"
        result = await query.get_entities(test_query)
        
        # Verify embeddings client was called
        mock_embeddings_client.embed.assert_called_once_with(test_query)
        
        # Verify graph embeddings client was called correctly
        mock_graph_embeddings_client.query.assert_called_once_with(
            vectors=test_vectors,
            limit=25,
            user="test_user",
            collection="test_collection"
        )
        
        # Verify result is list of entity strings
        assert result == ["entity1", "entity2"]

    @pytest.mark.asyncio
    async def test_maybe_label_with_cached_label(self):
        """Test Query.maybe_label method with cached label"""
        # Create mock GraphRag with label cache
        mock_rag = MagicMock()
        mock_rag.label_cache = {"entity1": "Entity One Label"}
        
        # Initialize Query
        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False
        )
        
        # Call maybe_label with cached entity
        result = await query.maybe_label("entity1")
        
        # Verify cached label is returned
        assert result == "Entity One Label"

    @pytest.mark.asyncio
    async def test_maybe_label_with_label_lookup(self):
        """Test Query.maybe_label method with database label lookup"""
        # Create mock GraphRag with triples client
        mock_rag = MagicMock()
        mock_rag.label_cache = {}  # Empty cache
        mock_triples_client = AsyncMock()
        mock_rag.triples_client = mock_triples_client
        
        # Mock triple result with label
        mock_triple = MagicMock()
        mock_triple.o = "Human Readable Label"
        mock_triples_client.query.return_value = [mock_triple]
        
        # Initialize Query
        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False
        )
        
        # Call maybe_label
        result = await query.maybe_label("http://example.com/entity")
        
        # Verify triples client was called correctly
        mock_triples_client.query.assert_called_once_with(
            s="http://example.com/entity",
            p="http://www.w3.org/2000/01/rdf-schema#label",
            o=None,
            limit=1,
            user="test_user",
            collection="test_collection"
        )
        
        # Verify result and cache update
        assert result == "Human Readable Label"
        assert mock_rag.label_cache["http://example.com/entity"] == "Human Readable Label"

    @pytest.mark.asyncio
    async def test_maybe_label_with_no_label_found(self):
        """Test Query.maybe_label method when no label is found"""
        # Create mock GraphRag with triples client
        mock_rag = MagicMock()
        mock_rag.label_cache = {}  # Empty cache
        mock_triples_client = AsyncMock()
        mock_rag.triples_client = mock_triples_client
        
        # Mock empty result (no label found)
        mock_triples_client.query.return_value = []
        
        # Initialize Query
        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False
        )
        
        # Call maybe_label
        result = await query.maybe_label("unlabeled_entity")
        
        # Verify triples client was called
        mock_triples_client.query.assert_called_once_with(
            s="unlabeled_entity",
            p="http://www.w3.org/2000/01/rdf-schema#label",
            o=None,
            limit=1,
            user="test_user",
            collection="test_collection"
        )
        
        # Verify result is entity itself and cache is updated
        assert result == "unlabeled_entity"
        assert mock_rag.label_cache["unlabeled_entity"] == "unlabeled_entity"

    @pytest.mark.asyncio
    async def test_follow_edges_basic_functionality(self):
        """Test Query.follow_edges method basic triple discovery"""
        # Create mock GraphRag with triples client
        mock_rag = MagicMock()
        mock_triples_client = AsyncMock()
        mock_rag.triples_client = mock_triples_client
        
        # Mock triple results for different query patterns
        mock_triple1 = MagicMock()
        mock_triple1.s, mock_triple1.p, mock_triple1.o = "entity1", "predicate1", "object1"
        
        mock_triple2 = MagicMock()
        mock_triple2.s, mock_triple2.p, mock_triple2.o = "subject2", "entity1", "object2"
        
        mock_triple3 = MagicMock()
        mock_triple3.s, mock_triple3.p, mock_triple3.o = "subject3", "predicate3", "entity1"
        
        # Setup query responses for s=ent, p=ent, o=ent patterns
        mock_triples_client.query.side_effect = [
            [mock_triple1],  # s=ent, p=None, o=None
            [mock_triple2],  # s=None, p=ent, o=None  
            [mock_triple3],  # s=None, p=None, o=ent
        ]
        
        # Initialize Query
        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False,
            triple_limit=10
        )
        
        # Call follow_edges
        subgraph = set()
        await query.follow_edges("entity1", subgraph, path_length=1)
        
        # Verify all three query patterns were called
        assert mock_triples_client.query.call_count == 3
        
        # Verify query calls
        mock_triples_client.query.assert_any_call(
            s="entity1", p=None, o=None, limit=10,
            user="test_user", collection="test_collection"
        )
        mock_triples_client.query.assert_any_call(
            s=None, p="entity1", o=None, limit=10,
            user="test_user", collection="test_collection"
        )
        mock_triples_client.query.assert_any_call(
            s=None, p=None, o="entity1", limit=10,
            user="test_user", collection="test_collection"
        )
        
        # Verify subgraph contains discovered triples
        expected_subgraph = {
            ("entity1", "predicate1", "object1"),
            ("subject2", "entity1", "object2"),
            ("subject3", "predicate3", "entity1")
        }
        assert subgraph == expected_subgraph

    @pytest.mark.asyncio
    async def test_follow_edges_with_path_length_zero(self):
        """Test Query.follow_edges method with path_length=0"""
        # Create mock GraphRag
        mock_rag = MagicMock()
        mock_triples_client = AsyncMock()
        mock_rag.triples_client = mock_triples_client
        
        # Initialize Query
        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False
        )
        
        # Call follow_edges with path_length=0
        subgraph = set()
        await query.follow_edges("entity1", subgraph, path_length=0)
        
        # Verify no queries were made
        mock_triples_client.query.assert_not_called()
        
        # Verify subgraph remains empty
        assert subgraph == set()

    @pytest.mark.asyncio
    async def test_follow_edges_with_max_subgraph_size_limit(self):
        """Test Query.follow_edges method respects max_subgraph_size"""
        # Create mock GraphRag
        mock_rag = MagicMock()
        mock_triples_client = AsyncMock()
        mock_rag.triples_client = mock_triples_client
        
        # Initialize Query with small max_subgraph_size
        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False,
            max_subgraph_size=2
        )
        
        # Pre-populate subgraph to exceed limit
        subgraph = {("s1", "p1", "o1"), ("s2", "p2", "o2"), ("s3", "p3", "o3")}
        
        # Call follow_edges
        await query.follow_edges("entity1", subgraph, path_length=1)
        
        # Verify no queries were made due to size limit
        mock_triples_client.query.assert_not_called()
        
        # Verify subgraph unchanged
        assert len(subgraph) == 3

    @pytest.mark.asyncio
    async def test_get_subgraph_method(self):
        """Test Query.get_subgraph method orchestrates entity and edge discovery"""
        # Create mock Query that patches get_entities and follow_edges
        mock_rag = MagicMock()
        
        query = Query(
            rag=mock_rag,
            user="test_user", 
            collection="test_collection",
            verbose=False,
            max_path_length=1
        )
        
        # Mock get_entities to return test entities
        query.get_entities = AsyncMock(return_value=["entity1", "entity2"])
        
        # Mock follow_edges to add triples to subgraph
        async def mock_follow_edges(ent, subgraph, path_length):
            subgraph.add((ent, "predicate", "object"))
        
        query.follow_edges = AsyncMock(side_effect=mock_follow_edges)
        
        # Call get_subgraph
        result = await query.get_subgraph("test query")
        
        # Verify get_entities was called
        query.get_entities.assert_called_once_with("test query")
        
        # Verify follow_edges was called for each entity
        assert query.follow_edges.call_count == 2
        query.follow_edges.assert_any_call("entity1", unittest.mock.ANY, 1)
        query.follow_edges.assert_any_call("entity2", unittest.mock.ANY, 1)
        
        # Verify result is list format
        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_labelgraph_method(self):
        """Test Query.get_labelgraph method converts entities to labels"""
        # Create mock Query
        mock_rag = MagicMock()
        
        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection", 
            verbose=False,
            max_subgraph_size=100
        )
        
        # Mock get_subgraph to return test triples
        test_subgraph = [
            ("entity1", "predicate1", "object1"),
            ("subject2", "http://www.w3.org/2000/01/rdf-schema#label", "Label Value"),  # Should be filtered
            ("entity3", "predicate3", "object3")
        ]
        query.get_subgraph = AsyncMock(return_value=test_subgraph)
        
        # Mock maybe_label to return human-readable labels
        async def mock_maybe_label(entity):
            label_map = {
                "entity1": "Human Entity One",
                "predicate1": "Human Predicate One", 
                "object1": "Human Object One",
                "entity3": "Human Entity Three",
                "predicate3": "Human Predicate Three",
                "object3": "Human Object Three"
            }
            return label_map.get(entity, entity)
            
        query.maybe_label = AsyncMock(side_effect=mock_maybe_label)
        
        # Call get_labelgraph
        result = await query.get_labelgraph("test query")
        
        # Verify get_subgraph was called
        query.get_subgraph.assert_called_once_with("test query")
        
        # Verify label triples are filtered out
        assert len(result) == 2  # Label triple should be excluded
        
        # Verify maybe_label was called for non-label triples
        expected_calls = [
            (("entity1",), {}), (("predicate1",), {}), (("object1",), {}),
            (("entity3",), {}), (("predicate3",), {}), (("object3",), {})
        ]
        assert query.maybe_label.call_count == 6
        
        # Verify result contains human-readable labels
        expected_result = [
            ("Human Entity One", "Human Predicate One", "Human Object One"),
            ("Human Entity Three", "Human Predicate Three", "Human Object Three")
        ]
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_graph_rag_query_method(self):
        """Test GraphRag.query method orchestrates full RAG pipeline"""
        # Create mock clients
        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_graph_embeddings_client = AsyncMock()
        mock_triples_client = AsyncMock()
        
        # Mock prompt client response
        expected_response = "This is the RAG response"
        mock_prompt_client.kg_prompt.return_value = expected_response
        
        # Initialize GraphRag
        graph_rag = GraphRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            graph_embeddings_client=mock_graph_embeddings_client,
            triples_client=mock_triples_client,
            verbose=False
        )
        
        # Mock the Query class behavior by patching get_labelgraph
        test_labelgraph = [("Subject", "Predicate", "Object")]
        
        # We need to patch the Query class's get_labelgraph method
        original_query_init = Query.__init__
        original_get_labelgraph = Query.get_labelgraph
        
        def mock_query_init(self, *args, **kwargs):
            original_query_init(self, *args, **kwargs)
        
        async def mock_get_labelgraph(self, query_text):
            return test_labelgraph
            
        Query.__init__ = mock_query_init
        Query.get_labelgraph = mock_get_labelgraph
        
        try:
            # Call GraphRag.query
            result = await graph_rag.query(
                query="test query",
                user="test_user",
                collection="test_collection",
                entity_limit=25,
                triple_limit=15
            )
            
            # Verify prompt client was called with knowledge graph and query
            mock_prompt_client.kg_prompt.assert_called_once_with("test query", test_labelgraph)
            
            # Verify result
            assert result == expected_response
            
        finally:
            # Restore original methods
            Query.__init__ = original_query_init
            Query.get_labelgraph = original_get_labelgraph