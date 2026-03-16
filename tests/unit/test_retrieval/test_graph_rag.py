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
    async def test_get_vectors_method(self):
        """Test Query.get_vectors method calls embeddings client correctly"""
        mock_rag = MagicMock()
        mock_embeddings_client = AsyncMock()
        mock_rag.embeddings_client = mock_embeddings_client

        # Mock embed to return vectors for a list of concepts
        expected_vectors = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_embeddings_client.embed.return_value = expected_vectors

        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False
        )

        concepts = ["machine learning", "neural networks"]
        result = await query.get_vectors(concepts)

        mock_embeddings_client.embed.assert_called_once_with(concepts)
        assert result == expected_vectors

    @pytest.mark.asyncio
    async def test_get_vectors_method_with_verbose(self):
        """Test Query.get_vectors method with verbose output"""
        mock_rag = MagicMock()
        mock_embeddings_client = AsyncMock()
        mock_rag.embeddings_client = mock_embeddings_client

        expected_vectors = [[0.7, 0.8, 0.9]]
        mock_embeddings_client.embed.return_value = expected_vectors

        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=True
        )

        result = await query.get_vectors(["test concept"])

        mock_embeddings_client.embed.assert_called_once_with(["test concept"])
        assert result == expected_vectors

    @pytest.mark.asyncio
    async def test_extract_concepts(self):
        """Test Query.extract_concepts parses LLM response into concept list"""
        mock_rag = MagicMock()
        mock_prompt_client = AsyncMock()
        mock_rag.prompt_client = mock_prompt_client

        mock_prompt_client.prompt.return_value = "machine learning\nneural networks\n"

        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False
        )

        result = await query.extract_concepts("What is machine learning?")

        mock_prompt_client.prompt.assert_called_once_with(
            "extract-concepts",
            variables={"query": "What is machine learning?"}
        )
        assert result == ["machine learning", "neural networks"]

    @pytest.mark.asyncio
    async def test_extract_concepts_fallback_to_raw_query(self):
        """Test extract_concepts falls back to raw query when LLM returns empty"""
        mock_rag = MagicMock()
        mock_prompt_client = AsyncMock()
        mock_rag.prompt_client = mock_prompt_client

        mock_prompt_client.prompt.return_value = ""

        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False
        )

        result = await query.extract_concepts("test query")
        assert result == ["test query"]

    @pytest.mark.asyncio
    async def test_get_entities_method(self):
        """Test Query.get_entities extracts concepts, embeds, and retrieves entities"""
        mock_rag = MagicMock()
        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_graph_embeddings_client = AsyncMock()
        mock_rag.prompt_client = mock_prompt_client
        mock_rag.embeddings_client = mock_embeddings_client
        mock_rag.graph_embeddings_client = mock_graph_embeddings_client

        # extract_concepts returns empty -> falls back to [query]
        mock_prompt_client.prompt.return_value = ""

        # embed returns one vector set for the single concept
        test_vectors = [[0.1, 0.2, 0.3]]
        mock_embeddings_client.embed.return_value = test_vectors

        # Mock entity matches
        mock_entity1 = MagicMock()
        mock_entity1.type = "i"
        mock_entity1.iri = "entity1"
        mock_match1 = MagicMock()
        mock_match1.entity = mock_entity1

        mock_entity2 = MagicMock()
        mock_entity2.type = "i"
        mock_entity2.iri = "entity2"
        mock_match2 = MagicMock()
        mock_match2.entity = mock_entity2

        mock_graph_embeddings_client.query.return_value = [mock_match1, mock_match2]

        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False,
            entity_limit=25
        )

        entities, concepts = await query.get_entities("Find related entities")

        # Verify embeddings client was called with the fallback concept
        mock_embeddings_client.embed.assert_called_once_with(["Find related entities"])

        # Verify result
        assert entities == ["entity1", "entity2"]
        assert concepts == ["Find related entities"]

    @pytest.mark.asyncio
    async def test_maybe_label_with_cached_label(self):
        """Test Query.maybe_label method with cached label"""
        mock_rag = MagicMock()
        mock_cache = MagicMock()
        mock_cache.get.return_value = "Entity One Label"
        mock_rag.label_cache = mock_cache

        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False
        )

        result = await query.maybe_label("entity1")

        assert result == "Entity One Label"
        mock_cache.get.assert_called_once_with("test_user:test_collection:entity1")

    @pytest.mark.asyncio
    async def test_maybe_label_with_label_lookup(self):
        """Test Query.maybe_label method with database label lookup"""
        mock_rag = MagicMock()
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_rag.label_cache = mock_cache
        mock_triples_client = AsyncMock()
        mock_rag.triples_client = mock_triples_client

        mock_triple = MagicMock()
        mock_triple.o = "Human Readable Label"
        mock_triples_client.query.return_value = [mock_triple]

        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False
        )

        result = await query.maybe_label("http://example.com/entity")

        mock_triples_client.query.assert_called_once_with(
            s="http://example.com/entity",
            p="http://www.w3.org/2000/01/rdf-schema#label",
            o=None,
            limit=1,
            user="test_user",
            collection="test_collection",
            g=""
        )

        assert result == "Human Readable Label"
        cache_key = "test_user:test_collection:http://example.com/entity"
        mock_cache.put.assert_called_once_with(cache_key, "Human Readable Label")

    @pytest.mark.asyncio
    async def test_maybe_label_with_no_label_found(self):
        """Test Query.maybe_label method when no label is found"""
        mock_rag = MagicMock()
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_rag.label_cache = mock_cache
        mock_triples_client = AsyncMock()
        mock_rag.triples_client = mock_triples_client

        mock_triples_client.query.return_value = []

        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False
        )

        result = await query.maybe_label("unlabeled_entity")

        mock_triples_client.query.assert_called_once_with(
            s="unlabeled_entity",
            p="http://www.w3.org/2000/01/rdf-schema#label",
            o=None,
            limit=1,
            user="test_user",
            collection="test_collection",
            g=""
        )

        assert result == "unlabeled_entity"
        cache_key = "test_user:test_collection:unlabeled_entity"
        mock_cache.put.assert_called_once_with(cache_key, "unlabeled_entity")

    @pytest.mark.asyncio
    async def test_follow_edges_basic_functionality(self):
        """Test Query.follow_edges method basic triple discovery"""
        mock_rag = MagicMock()
        mock_triples_client = AsyncMock()
        mock_rag.triples_client = mock_triples_client

        mock_triple1 = MagicMock()
        mock_triple1.s, mock_triple1.p, mock_triple1.o = "entity1", "predicate1", "object1"

        mock_triple2 = MagicMock()
        mock_triple2.s, mock_triple2.p, mock_triple2.o = "subject2", "entity1", "object2"

        mock_triple3 = MagicMock()
        mock_triple3.s, mock_triple3.p, mock_triple3.o = "subject3", "predicate3", "entity1"

        mock_triples_client.query_stream.side_effect = [
            [mock_triple1],  # s=ent
            [mock_triple2],  # p=ent
            [mock_triple3],  # o=ent
        ]

        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False,
            triple_limit=10
        )

        subgraph = set()
        await query.follow_edges("entity1", subgraph, path_length=1)

        assert mock_triples_client.query_stream.call_count == 3

        mock_triples_client.query_stream.assert_any_call(
            s="entity1", p=None, o=None, limit=10,
            user="test_user", collection="test_collection", batch_size=20, g=""
        )
        mock_triples_client.query_stream.assert_any_call(
            s=None, p="entity1", o=None, limit=10,
            user="test_user", collection="test_collection", batch_size=20, g=""
        )
        mock_triples_client.query_stream.assert_any_call(
            s=None, p=None, o="entity1", limit=10,
            user="test_user", collection="test_collection", batch_size=20, g=""
        )

        expected_subgraph = {
            ("entity1", "predicate1", "object1"),
            ("subject2", "entity1", "object2"),
            ("subject3", "predicate3", "entity1")
        }
        assert subgraph == expected_subgraph

    @pytest.mark.asyncio
    async def test_follow_edges_with_path_length_zero(self):
        """Test Query.follow_edges method with path_length=0"""
        mock_rag = MagicMock()
        mock_triples_client = AsyncMock()
        mock_rag.triples_client = mock_triples_client

        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False
        )

        subgraph = set()
        await query.follow_edges("entity1", subgraph, path_length=0)

        mock_triples_client.query_stream.assert_not_called()
        assert subgraph == set()

    @pytest.mark.asyncio
    async def test_follow_edges_with_max_subgraph_size_limit(self):
        """Test Query.follow_edges method respects max_subgraph_size"""
        mock_rag = MagicMock()
        mock_triples_client = AsyncMock()
        mock_rag.triples_client = mock_triples_client

        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False,
            max_subgraph_size=2
        )

        subgraph = {("s1", "p1", "o1"), ("s2", "p2", "o2"), ("s3", "p3", "o3")}

        await query.follow_edges("entity1", subgraph, path_length=1)

        mock_triples_client.query_stream.assert_not_called()
        assert len(subgraph) == 3

    @pytest.mark.asyncio
    async def test_get_subgraph_method(self):
        """Test Query.get_subgraph returns (subgraph, entities, concepts) tuple"""
        mock_rag = MagicMock()

        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False,
            max_path_length=1
        )

        # Mock get_entities to return (entities, concepts) tuple
        query.get_entities = AsyncMock(
            return_value=(["entity1", "entity2"], ["concept1"])
        )

        query.follow_edges_batch = AsyncMock(return_value={
            ("entity1", "predicate1", "object1"),
            ("entity2", "predicate2", "object2")
        })

        subgraph, entities, concepts = await query.get_subgraph("test query")

        query.get_entities.assert_called_once_with("test query")
        query.follow_edges_batch.assert_called_once_with(["entity1", "entity2"], 1)

        assert isinstance(subgraph, list)
        assert len(subgraph) == 2
        assert ("entity1", "predicate1", "object1") in subgraph
        assert ("entity2", "predicate2", "object2") in subgraph
        assert entities == ["entity1", "entity2"]
        assert concepts == ["concept1"]

    @pytest.mark.asyncio
    async def test_get_labelgraph_method(self):
        """Test Query.get_labelgraph returns (labeled_edges, uri_map, entities, concepts)"""
        mock_rag = MagicMock()

        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False,
            max_subgraph_size=100
        )

        test_subgraph = [
            ("entity1", "predicate1", "object1"),
            ("subject2", "http://www.w3.org/2000/01/rdf-schema#label", "Label Value"),
            ("entity3", "predicate3", "object3")
        ]
        test_entities = ["entity1", "entity3"]
        test_concepts = ["concept1"]
        query.get_subgraph = AsyncMock(
            return_value=(test_subgraph, test_entities, test_concepts)
        )

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

        labeled_edges, uri_map, entities, concepts = await query.get_labelgraph("test query")

        query.get_subgraph.assert_called_once_with("test query")

        # Label triples filtered out
        assert len(labeled_edges) == 2

        # maybe_label called for non-label triples
        assert query.maybe_label.call_count == 6

        expected_edges = [
            ("Human Entity One", "Human Predicate One", "Human Object One"),
            ("Human Entity Three", "Human Predicate Three", "Human Object Three")
        ]
        assert labeled_edges == expected_edges

        assert len(uri_map) == 2
        assert entities == test_entities
        assert concepts == test_concepts

    @pytest.mark.asyncio
    async def test_graph_rag_query_method(self):
        """Test GraphRag.query method orchestrates full RAG pipeline with provenance"""
        import json
        from trustgraph.retrieval.graph_rag.graph_rag import edge_id

        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_graph_embeddings_client = AsyncMock()
        mock_triples_client = AsyncMock()

        expected_response = "This is the RAG response"
        test_labelgraph = [("Subject", "Predicate", "Object")]
        test_edge_id = edge_id("Subject", "Predicate", "Object")
        test_uri_map = {
            test_edge_id: ("http://example.org/subject", "http://example.org/predicate", "http://example.org/object")
        }
        test_entities = ["http://example.org/subject"]
        test_concepts = ["test concept"]

        # Mock prompt responses for the multi-step process
        async def mock_prompt(prompt_name, variables=None, streaming=False, chunk_callback=None):
            if prompt_name == "extract-concepts":
                return ""  # Falls back to raw query
            elif prompt_name == "kg-edge-scoring":
                return json.dumps({"id": test_edge_id, "score": 0.9})
            elif prompt_name == "kg-edge-reasoning":
                return json.dumps({"id": test_edge_id, "reasoning": "relevant"})
            elif prompt_name == "kg-synthesis":
                return expected_response
            return ""

        mock_prompt_client.prompt = mock_prompt

        graph_rag = GraphRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            graph_embeddings_client=mock_graph_embeddings_client,
            triples_client=mock_triples_client,
            verbose=False
        )

        # Patch Query.get_labelgraph to return test data
        original_get_labelgraph = Query.get_labelgraph

        async def mock_get_labelgraph(self, query_text):
            return test_labelgraph, test_uri_map, test_entities, test_concepts

        Query.get_labelgraph = mock_get_labelgraph

        provenance_events = []

        async def collect_provenance(triples, prov_id):
            provenance_events.append((triples, prov_id))

        try:
            response = await graph_rag.query(
                query="test query",
                user="test_user",
                collection="test_collection",
                entity_limit=25,
                triple_limit=15,
                explain_callback=collect_provenance
            )

            assert response == expected_response

            # 5 events: question, grounding, exploration, focus, synthesis
            assert len(provenance_events) == 5

            for triples, prov_id in provenance_events:
                assert isinstance(triples, list)
                assert len(triples) > 0
                assert prov_id.startswith("urn:trustgraph:")

            # Verify order
            assert "question" in provenance_events[0][1]
            assert "grounding" in provenance_events[1][1]
            assert "exploration" in provenance_events[2][1]
            assert "focus" in provenance_events[3][1]
            assert "synthesis" in provenance_events[4][1]

        finally:
            Query.get_labelgraph = original_get_labelgraph
