"""
Tests for GraphRAG retrieval implementation
"""

import pytest
import unittest.mock
from unittest.mock import MagicMock, AsyncMock

from trustgraph.retrieval.graph_rag.graph_rag import GraphRag, Query
from trustgraph.base import PromptResult


class TestGraphRag:
    """Test cases for GraphRag class"""

    def test_graph_rag_initialization_with_defaults(self):
        """Test GraphRag initialization with default verbose setting"""
        mock_prompt_client = MagicMock()
        mock_embeddings_client = MagicMock()
        mock_graph_embeddings_client = MagicMock()
        mock_triples_client = MagicMock()
        mock_reranker_client = MagicMock()

        graph_rag = GraphRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            graph_embeddings_client=mock_graph_embeddings_client,
            triples_client=mock_triples_client,
            reranker_client=mock_reranker_client,
        )

        assert graph_rag.prompt_client == mock_prompt_client
        assert graph_rag.embeddings_client == mock_embeddings_client
        assert graph_rag.graph_embeddings_client == mock_graph_embeddings_client
        assert graph_rag.triples_client == mock_triples_client
        assert graph_rag.reranker_client == mock_reranker_client
        assert graph_rag.verbose is False
        from trustgraph.retrieval.graph_rag.graph_rag import LRUCacheWithTTL
        assert isinstance(graph_rag.label_cache, LRUCacheWithTTL)

    def test_graph_rag_initialization_with_verbose(self):
        """Test GraphRag initialization with verbose enabled"""
        mock_prompt_client = MagicMock()
        mock_embeddings_client = MagicMock()
        mock_graph_embeddings_client = MagicMock()
        mock_triples_client = MagicMock()
        mock_reranker_client = MagicMock()

        graph_rag = GraphRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            graph_embeddings_client=mock_graph_embeddings_client,
            triples_client=mock_triples_client,
            reranker_client=mock_reranker_client,
            verbose=True,
        )

        assert graph_rag.prompt_client == mock_prompt_client
        assert graph_rag.embeddings_client == mock_embeddings_client
        assert graph_rag.graph_embeddings_client == mock_graph_embeddings_client
        assert graph_rag.triples_client == mock_triples_client
        assert graph_rag.reranker_client == mock_reranker_client
        assert graph_rag.verbose is True
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
            collection="test_collection",
            verbose=False
        )

        # Verify initialization
        assert query.rag == mock_rag
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
            collection="custom_collection",
            verbose=True,
            entity_limit=100,
            triple_limit=60,
            max_subgraph_size=2000,
            max_path_length=3
        )

        # Verify initialization
        assert query.rag == mock_rag
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

        mock_prompt_client.prompt.return_value = PromptResult(response_type="text", text="machine learning\nneural networks\n")

        query = Query(
            rag=mock_rag,
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

        mock_prompt_client.prompt.return_value = PromptResult(response_type="text", text="")

        query = Query(
            rag=mock_rag,
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
        mock_prompt_client.prompt.return_value = PromptResult(response_type="text", text="")

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
            collection="test_collection",
            verbose=False
        )

        result = await query.maybe_label("entity1")

        assert result == "Entity One Label"
        mock_cache.get.assert_called_once_with("test_collection:entity1")

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
            collection="test_collection",
            verbose=False
        )

        result = await query.maybe_label("http://example.com/entity")

        mock_triples_client.query.assert_called_once_with(
            s="http://example.com/entity",
            p="http://www.w3.org/2000/01/rdf-schema#label",
            o=None,
            limit=1,
            collection="test_collection",
            g=""
        )

        assert result == "Human Readable Label"
        cache_key = "test_collection:http://example.com/entity"
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
            collection="test_collection",
            verbose=False
        )

        result = await query.maybe_label("unlabeled_entity")

        mock_triples_client.query.assert_called_once_with(
            s="unlabeled_entity",
            p="http://www.w3.org/2000/01/rdf-schema#label",
            o=None,
            limit=1,
            collection="test_collection",
            g=""
        )

        assert result == "unlabeled_entity"
        cache_key = "test_collection:unlabeled_entity"
        mock_cache.put.assert_called_once_with(cache_key, "unlabeled_entity")

    @pytest.mark.asyncio
    async def test_triples_query_never_passes_workspace(self):
        """Workspace isolation is handled by pub/sub topic routing, not
        by passing workspace to TriplesClient.query(). Verify that
        GraphRAG never passes workspace as a keyword argument."""
        mock_rag = MagicMock()
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_rag.label_cache = mock_cache
        mock_triples_client = AsyncMock()
        mock_rag.triples_client = mock_triples_client

        mock_triple = MagicMock()
        mock_triple.o = "Label"
        mock_triples_client.query.return_value = [mock_triple]

        query = Query(
            rag=mock_rag,
            collection="test_collection",
            verbose=False
        )

        await query.maybe_label("http://example.com/entity")

        for c in mock_triples_client.query.call_args_list:
            assert "workspace" not in c.kwargs

    @pytest.mark.asyncio
    async def test_hop_and_filter_never_passes_workspace(self):
        """Verify hop_and_filter never passes workspace to query_stream."""
        mock_rag = MagicMock()
        mock_triples_client = AsyncMock()
        mock_reranker_client = AsyncMock()
        mock_rag.triples_client = mock_triples_client
        mock_rag.reranker_client = mock_reranker_client
        mock_rag.label_cache = MagicMock()
        mock_rag.label_cache.get.return_value = None

        mock_triple = MagicMock()
        mock_triple.s = "e1"
        mock_triple.p = "p1"
        mock_triple.o = "o1"
        mock_triples_client.query_stream.return_value = [mock_triple]
        mock_triples_client.query.return_value = []

        result = MagicMock()
        result.document_id = "0"
        result.query_id = "0"
        result.score = 0.9
        mock_reranker_client.rerank.return_value = [result]

        query = Query(
            rag=mock_rag,
            collection="test_collection",
            verbose=False,
            triple_limit=10,
        )

        await query.hop_and_filter(["e1"], ["concept"])

        for c in mock_triples_client.query_stream.call_args_list:
            assert "workspace" not in c.kwargs

    @pytest.mark.asyncio
    async def test_hop_and_filter_basic_functionality(self):
        """Test hop_and_filter retrieves edges and scores them with reranker."""
        mock_rag = MagicMock()
        mock_triples_client = AsyncMock()
        mock_reranker_client = AsyncMock()
        mock_rag.triples_client = mock_triples_client
        mock_rag.reranker_client = mock_reranker_client
        mock_rag.label_cache = MagicMock()
        mock_rag.label_cache.get.return_value = None

        mock_triple = MagicMock()
        mock_triple.s = "entity1"
        mock_triple.p = "predicate1"
        mock_triple.o = "object1"
        mock_triples_client.query_stream.return_value = [mock_triple]
        mock_triples_client.query.return_value = []

        result = MagicMock()
        result.document_id = "0"
        result.query_id = "0"
        result.score = 0.95
        mock_reranker_client.rerank.return_value = [result]

        query = Query(
            rag=mock_rag,
            collection="test_collection",
            verbose=False,
            triple_limit=10,
            edge_limit=25,
        )

        selected, uri_map, edge_meta = await query.hop_and_filter(
            ["entity1"], ["test concept"],
        )

        assert len(selected) == 1
        assert len(uri_map) == 1
        assert len(edge_meta) == 1

        mock_reranker_client.rerank.assert_called_once()
        call_kwargs = mock_reranker_client.rerank.call_args
        assert call_kwargs.kwargs["limit"] == 25

    @pytest.mark.asyncio
    async def test_hop_and_filter_with_empty_frontier(self):
        """Test hop_and_filter with no seed entities returns empty."""
        mock_rag = MagicMock()

        query = Query(
            rag=mock_rag,
            collection="test_collection",
            verbose=False,
        )

        selected, uri_map, edge_meta = await query.hop_and_filter([], ["concept"])

        assert selected == []
        assert uri_map == {}
        assert edge_meta == {}

    @pytest.mark.asyncio
    async def test_hop_and_filter_filters_label_triples(self):
        """Test hop_and_filter skips rdfs:label edges."""
        mock_rag = MagicMock()
        mock_triples_client = AsyncMock()
        mock_reranker_client = AsyncMock()
        mock_rag.triples_client = mock_triples_client
        mock_rag.reranker_client = mock_reranker_client
        mock_rag.label_cache = MagicMock()
        mock_rag.label_cache.get.return_value = None

        label_triple = MagicMock()
        label_triple.s = "entity1"
        label_triple.p = "http://www.w3.org/2000/01/rdf-schema#label"
        label_triple.o = "Entity One"

        mock_triples_client.query_stream.return_value = [label_triple]
        mock_triples_client.query.return_value = []

        query = Query(
            rag=mock_rag,
            collection="test_collection",
            verbose=False,
            triple_limit=10,
        )

        selected, uri_map, edge_meta = await query.hop_and_filter(
            ["entity1"], ["concept"],
        )

        assert selected == []
        mock_reranker_client.rerank.assert_not_called()

    @pytest.mark.asyncio
    async def test_graph_rag_query_method(self):
        """Test GraphRag.query method orchestrates full RAG pipeline with provenance"""
        from trustgraph.retrieval.graph_rag.graph_rag import edge_id

        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_graph_embeddings_client = AsyncMock()
        mock_triples_client = AsyncMock()
        mock_reranker_client = AsyncMock()

        expected_response = "This is the RAG response"
        test_selected_edges = [("Subject", "Predicate", "Object")]
        test_eid = edge_id("Subject", "Predicate", "Object")
        test_uri_map = {
            test_eid: ("http://example.org/subject", "http://example.org/predicate", "http://example.org/object")
        }
        test_edge_metadata = {
            test_eid: {"concept": "test concept", "score": 0.95}
        }

        mock_embeddings_client.embed.return_value = [[0.1, 0.2]]
        mock_graph_embeddings_client.query.return_value = []

        async def mock_prompt(prompt_name, variables=None, streaming=False, chunk_callback=None):
            if prompt_name == "extract-concepts":
                return PromptResult(response_type="text", text="test concept")
            elif prompt_name == "kg-synthesis":
                return PromptResult(response_type="text", text=expected_response)
            return PromptResult(response_type="text", text="")

        mock_prompt_client.prompt = mock_prompt

        graph_rag = GraphRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            graph_embeddings_client=mock_graph_embeddings_client,
            triples_client=mock_triples_client,
            reranker_client=mock_reranker_client,
            verbose=False,
        )

        original_hop_and_filter = Query.hop_and_filter

        async def mock_hop_and_filter(self, seed_entities, concepts):
            return test_selected_edges, test_uri_map, test_edge_metadata

        Query.hop_and_filter = mock_hop_and_filter

        provenance_events = []

        async def collect_provenance(triples, prov_id):
            provenance_events.append((triples, prov_id))

        try:
            response = await graph_rag.query(
                query="test query",
                collection="test_collection",
                entity_limit=25,
                triple_limit=15,
                explain_callback=collect_provenance,
            )

            response_text, usage, sources = response
            assert response_text == expected_response

            # 5 events: question, grounding, exploration, focus, synthesis
            assert len(provenance_events) == 5

            for triples, prov_id in provenance_events:
                assert isinstance(triples, list)
                assert len(triples) > 0
                assert prov_id.startswith("urn:trustgraph:")

            assert "question" in provenance_events[0][1]
            assert "grounding" in provenance_events[1][1]
            assert "exploration" in provenance_events[2][1]
            assert "focus" in provenance_events[3][1]
            assert "synthesis" in provenance_events[4][1]

        finally:
            Query.hop_and_filter = original_hop_and_filter
