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
        # Verify label_cache is an LRUCacheWithTTL instance
        from trustgraph.retrieval.graph_rag.graph_rag import LRUCacheWithTTL
        assert isinstance(graph_rag.label_cache, LRUCacheWithTTL)

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
        # Verify label_cache is an LRUCacheWithTTL instance
        from trustgraph.retrieval.graph_rag.graph_rag import LRUCacheWithTTL
        assert isinstance(graph_rag.label_cache, LRUCacheWithTTL)


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
        
        # Mock the embed method to return test vectors (batch format)
        expected_vectors = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_embeddings_client.embed.return_value = [expected_vectors]

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

        # Verify embeddings client was called correctly (now expects list)
        mock_embeddings_client.embed.assert_called_once_with([test_query])

        # Verify result matches expected vectors (extracted from batch)
        assert result == expected_vectors

    @pytest.mark.asyncio
    async def test_get_vector_method_with_verbose(self):
        """Test Query.get_vector method with verbose output"""
        # Create mock GraphRag with embeddings client
        mock_rag = MagicMock()
        mock_embeddings_client = AsyncMock()
        mock_rag.embeddings_client = mock_embeddings_client
        
        # Mock the embed method (batch format)
        expected_vectors = [[0.7, 0.8, 0.9]]
        mock_embeddings_client.embed.return_value = [expected_vectors]

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

        # Verify embeddings client was called correctly (now expects list)
        mock_embeddings_client.embed.assert_called_once_with([test_query])

        # Verify result matches expected vectors (extracted from batch)
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
        
        # Mock the embedding and entity query responses (batch format)
        test_vectors = [[0.1, 0.2, 0.3]]
        mock_embeddings_client.embed.return_value = [test_vectors]

        # Mock EntityMatch objects with entity as Term-like object
        mock_entity1 = MagicMock()
        mock_entity1.type = "i"  # IRI type
        mock_entity1.iri = "entity1"
        mock_match1 = MagicMock()
        mock_match1.entity = mock_entity1
        mock_match1.score = 0.95

        mock_entity2 = MagicMock()
        mock_entity2.type = "i"  # IRI type
        mock_entity2.iri = "entity2"
        mock_match2 = MagicMock()
        mock_match2.entity = mock_entity2
        mock_match2.score = 0.85

        mock_graph_embeddings_client.query.return_value = [mock_match1, mock_match2]

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

        # Verify embeddings client was called (now expects list)
        mock_embeddings_client.embed.assert_called_once_with([test_query])

        # Verify graph embeddings client was called correctly (with extracted vector)
        mock_graph_embeddings_client.query.assert_called_once_with(
            vector=test_vectors,
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
        # Create mock LRUCacheWithTTL
        mock_cache = MagicMock()
        mock_cache.get.return_value = "Entity One Label"
        mock_rag.label_cache = mock_cache

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
        # Verify cache was checked with proper key format (user:collection:entity)
        mock_cache.get.assert_called_once_with("test_user:test_collection:entity1")

    @pytest.mark.asyncio
    async def test_maybe_label_with_label_lookup(self):
        """Test Query.maybe_label method with database label lookup"""
        # Create mock GraphRag with triples client
        mock_rag = MagicMock()
        # Create mock LRUCacheWithTTL that returns None (cache miss)
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_rag.label_cache = mock_cache
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

        # Verify result and cache update with proper key
        assert result == "Human Readable Label"
        cache_key = "test_user:test_collection:http://example.com/entity"
        mock_cache.put.assert_called_once_with(cache_key, "Human Readable Label")

    @pytest.mark.asyncio
    async def test_maybe_label_with_no_label_found(self):
        """Test Query.maybe_label method when no label is found"""
        # Create mock GraphRag with triples client
        mock_rag = MagicMock()
        # Create mock LRUCacheWithTTL that returns None (cache miss)
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_rag.label_cache = mock_cache
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
        cache_key = "test_user:test_collection:unlabeled_entity"
        mock_cache.put.assert_called_once_with(cache_key, "unlabeled_entity")

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
        
        # Setup query_stream responses for s=ent, p=ent, o=ent patterns
        mock_triples_client.query_stream.side_effect = [
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
        assert mock_triples_client.query_stream.call_count == 3

        # Verify query_stream calls
        mock_triples_client.query_stream.assert_any_call(
            s="entity1", p=None, o=None, limit=10,
            user="test_user", collection="test_collection", batch_size=20
        )
        mock_triples_client.query_stream.assert_any_call(
            s=None, p="entity1", o=None, limit=10,
            user="test_user", collection="test_collection", batch_size=20
        )
        mock_triples_client.query_stream.assert_any_call(
            s=None, p=None, o="entity1", limit=10,
            user="test_user", collection="test_collection", batch_size=20
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
        mock_triples_client.query_stream.assert_not_called()
        
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
        mock_triples_client.query_stream.assert_not_called()
        
        # Verify subgraph unchanged
        assert len(subgraph) == 3

    @pytest.mark.asyncio
    async def test_get_subgraph_method(self):
        """Test Query.get_subgraph method orchestrates entity and edge discovery"""
        # Create mock Query that patches get_entities and follow_edges_batch
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

        # Mock follow_edges_batch to return test triples
        query.follow_edges_batch = AsyncMock(return_value={
            ("entity1", "predicate1", "object1"),
            ("entity2", "predicate2", "object2")
        })

        # Call get_subgraph
        result = await query.get_subgraph("test query")

        # Verify get_entities was called
        query.get_entities.assert_called_once_with("test query")

        # Verify follow_edges_batch was called with entities and max_path_length
        query.follow_edges_batch.assert_called_once_with(["entity1", "entity2"], 1)

        # Verify result is list format and contains expected triples
        assert isinstance(result, list)
        assert len(result) == 2
        assert ("entity1", "predicate1", "object1") in result
        assert ("entity2", "predicate2", "object2") in result

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
        labeled_edges, uri_map = await query.get_labelgraph("test query")

        # Verify get_subgraph was called
        query.get_subgraph.assert_called_once_with("test query")

        # Verify label triples are filtered out
        assert len(labeled_edges) == 2  # Label triple should be excluded

        # Verify maybe_label was called for non-label triples
        expected_calls = [
            (("entity1",), {}), (("predicate1",), {}), (("object1",), {}),
            (("entity3",), {}), (("predicate3",), {}), (("object3",), {})
        ]
        assert query.maybe_label.call_count == 6

        # Verify result contains human-readable labels
        expected_edges = [
            ("Human Entity One", "Human Predicate One", "Human Object One"),
            ("Human Entity Three", "Human Predicate Three", "Human Object Three")
        ]
        assert labeled_edges == expected_edges

        # Verify uri_map maps labeled edges back to original URIs
        assert len(uri_map) == 2

    @pytest.mark.asyncio
    async def test_graph_rag_query_method(self):
        """Test GraphRag.query method orchestrates full RAG pipeline with real-time provenance"""
        import json
        from trustgraph.retrieval.graph_rag.graph_rag import edge_id

        # Create mock clients
        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_graph_embeddings_client = AsyncMock()
        mock_triples_client = AsyncMock()

        # Mock prompt client responses for two-step process
        expected_response = "This is the RAG response"
        test_labelgraph = [("Subject", "Predicate", "Object")]

        # Compute the edge ID for the test edge
        test_edge_id = edge_id("Subject", "Predicate", "Object")

        # Create uri_map for the test edge (maps labeled edge ID to original URIs)
        test_uri_map = {
            test_edge_id: ("http://example.org/subject", "http://example.org/predicate", "http://example.org/object")
        }

        # Mock edge selection response (JSONL format)
        edge_selection_response = json.dumps({"id": test_edge_id, "reasoning": "relevant"})

        # Configure prompt mock to return different responses based on prompt name
        async def mock_prompt(prompt_name, variables=None, streaming=False, chunk_callback=None):
            if prompt_name == "kg-edge-selection":
                return edge_selection_response
            elif prompt_name == "kg-synthesis":
                return expected_response
            return ""

        mock_prompt_client.prompt = mock_prompt

        # Initialize GraphRag
        graph_rag = GraphRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            graph_embeddings_client=mock_graph_embeddings_client,
            triples_client=mock_triples_client,
            verbose=False
        )

        # We need to patch the Query class's get_labelgraph method
        original_query_init = Query.__init__
        original_get_labelgraph = Query.get_labelgraph

        def mock_query_init(self, *args, **kwargs):
            original_query_init(self, *args, **kwargs)

        async def mock_get_labelgraph(self, query_text):
            return test_labelgraph, test_uri_map

        Query.__init__ = mock_query_init
        Query.get_labelgraph = mock_get_labelgraph

        # Collect provenance emitted via callback
        provenance_events = []

        async def collect_provenance(triples, prov_id):
            provenance_events.append((triples, prov_id))

        try:
            # Call GraphRag.query with provenance callback
            response = await graph_rag.query(
                query="test query",
                user="test_user",
                collection="test_collection",
                entity_limit=25,
                triple_limit=15,
                explain_callback=collect_provenance
            )

            # Verify response text
            assert response == expected_response

            # Verify provenance was emitted incrementally (4 events: session, retrieval, selection, answer)
            assert len(provenance_events) == 4

            # Verify each event has triples and a URN
            for triples, prov_id in provenance_events:
                assert isinstance(triples, list)
                assert len(triples) > 0
                assert prov_id.startswith("urn:trustgraph:")

            # Verify order: session, retrieval, selection, answer
            assert "session" in provenance_events[0][1]
            assert "retrieval" in provenance_events[1][1]
            assert "selection" in provenance_events[2][1]
            assert "answer" in provenance_events[3][1]

        finally:
            # Restore original methods
            Query.__init__ = original_query_init
            Query.get_labelgraph = original_get_labelgraph