"""
Tests for GraphRAG orchestrator (new 4-client constructor).
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from trustgraph.retrieval.graph_rag.graph_rag import GraphRag
from trustgraph.schema import KnowledgeRetrievalResponse, RetrievedEdge
from trustgraph.base import PromptResult


class TestGraphRag:
    """Test cases for GraphRag class"""

    def test_graph_rag_initialization_with_defaults(self):
        """Test GraphRag initialization with default verbose setting"""
        mock_concept_extraction_client = MagicMock()
        mock_knowledge_retrieval_client = MagicMock()
        mock_triples_client = MagicMock()
        mock_prompt_client = MagicMock()

        graph_rag = GraphRag(
            concept_extraction_client=mock_concept_extraction_client,
            knowledge_retrieval_client=mock_knowledge_retrieval_client,
            triples_client=mock_triples_client,
            prompt_client=mock_prompt_client,
        )

        assert graph_rag.concept_extraction_client == mock_concept_extraction_client
        assert graph_rag.knowledge_retrieval_client == mock_knowledge_retrieval_client
        assert graph_rag.triples_client == mock_triples_client
        assert graph_rag.prompt_client == mock_prompt_client
        assert graph_rag.verbose is False

    def test_graph_rag_initialization_with_verbose(self):
        """Test GraphRag initialization with verbose enabled"""
        mock_concept_extraction_client = MagicMock()
        mock_knowledge_retrieval_client = MagicMock()
        mock_triples_client = MagicMock()
        mock_prompt_client = MagicMock()

        graph_rag = GraphRag(
            concept_extraction_client=mock_concept_extraction_client,
            knowledge_retrieval_client=mock_knowledge_retrieval_client,
            triples_client=mock_triples_client,
            prompt_client=mock_prompt_client,
            verbose=True,
        )

        assert graph_rag.concept_extraction_client == mock_concept_extraction_client
        assert graph_rag.knowledge_retrieval_client == mock_knowledge_retrieval_client
        assert graph_rag.triples_client == mock_triples_client
        assert graph_rag.prompt_client == mock_prompt_client
        assert graph_rag.verbose is True


class TestGraphRagQuery:
    """Test GraphRag.query orchestration"""

    def _make_rag(self, concepts=None, edges=None, synthesis_text="answer"):
        concept_extraction_client = AsyncMock()
        concept_extraction_client.extract.return_value = concepts or ["test concept"]

        knowledge_retrieval_client = AsyncMock()
        knowledge_retrieval_client.retrieve.return_value = KnowledgeRetrievalResponse(
            edges=edges or [],
            seed_entities=["http://example.com/e1"],
        )

        triples_client = AsyncMock()
        triples_client.query.return_value = []

        prompt_client = AsyncMock()
        prompt_client.prompt.return_value = PromptResult(
            response_type="text", text=synthesis_text,
        )

        rag = GraphRag(
            concept_extraction_client=concept_extraction_client,
            knowledge_retrieval_client=knowledge_retrieval_client,
            triples_client=triples_client,
            prompt_client=prompt_client,
            verbose=False,
        )
        return rag, concept_extraction_client, knowledge_retrieval_client, triples_client, prompt_client

    @pytest.mark.asyncio
    async def test_query_calls_concept_extraction(self):
        rag, ce_client, _, _, _ = self._make_rag()

        await rag.query(query="What is ML?", collection="test")

        ce_client.extract.assert_called_once_with("What is ML?", timeout=300)

    @pytest.mark.asyncio
    async def test_query_calls_knowledge_retrieval(self):
        rag, _, kr_client, _, _ = self._make_rag(concepts=["ml", "ai"])

        await rag.query(
            query="test", collection="test",
            entity_limit=25, triple_limit=15,
        )

        kr_client.retrieve.assert_called_once()
        call_kwargs = kr_client.retrieve.call_args.kwargs
        assert call_kwargs["concepts"] == ["ml", "ai"]
        assert call_kwargs["entity_limit"] == 25
        assert call_kwargs["triple_limit"] == 15

    @pytest.mark.asyncio
    async def test_query_calls_synthesis_prompt(self):
        rag, _, _, _, prompt_client = self._make_rag()

        await rag.query(query="test", collection="test")

        assert prompt_client.prompt.call_count == 1
        call_args = prompt_client.prompt.call_args
        assert call_args.args[0] == "kg-synthesis"

    @pytest.mark.asyncio
    async def test_query_returns_response_tuple(self):
        rag, _, _, _, _ = self._make_rag(synthesis_text="The answer is 42.")

        result = await rag.query(query="test", collection="test")

        response_text, usage, sources = result
        assert response_text == "The answer is 42."

    @pytest.mark.asyncio
    async def test_query_with_edges_builds_knowledge(self):
        edges = [
            RetrievedEdge(
                s="http://e.com/s1", p="http://e.com/p1", o="http://e.com/o1",
                s_label="Subject", p_label="relates to", o_label="Object",
                score=0.9, concept="test",
            ),
        ]
        rag, _, _, _, prompt_client = self._make_rag(edges=edges)

        await rag.query(query="test", collection="test")

        synthesis_call = prompt_client.prompt.call_args
        knowledge = synthesis_call.kwargs["variables"]["knowledge"]
        assert any(
            d["s"] == "Subject" and d["p"] == "relates to"
            for d in knowledge
        )

    @pytest.mark.asyncio
    async def test_query_provenance_emits_five_events(self):
        rag, _, _, _, _ = self._make_rag()

        events = []

        async def explain_callback(triples, explain_id):
            events.append((triples, explain_id))

        await rag.query(
            query="test", collection="test",
            explain_callback=explain_callback,
        )

        assert len(events) == 5
        for triples, prov_id in events:
            assert isinstance(triples, list)
            assert prov_id.startswith("urn:trustgraph:")

    @pytest.mark.asyncio
    async def test_query_grounding_seeds_skip_concept_extraction(self):
        rag, ce_client, kr_client, _, _ = self._make_rag()

        await rag.query(
            query="test", collection="test",
            grounding_seeds=["concept_a", "concept_b"],
        )

        ce_client.extract.assert_not_called()
        call_kwargs = kr_client.retrieve.call_args.kwargs
        assert call_kwargs["concepts"] == ["concept_a", "concept_b"]

    @pytest.mark.asyncio
    async def test_query_graph_seeds_skip_concept_extraction(self):
        rag, ce_client, kr_client, _, _ = self._make_rag()

        seeds = ["http://example.org/e1", "http://example.org/e2"]
        await rag.query(
            query="test", collection="test",
            graph_seeds=seeds,
        )

        ce_client.extract.assert_not_called()
        call_kwargs = kr_client.retrieve.call_args.kwargs
        assert call_kwargs["entities"] == seeds

    @pytest.mark.asyncio
    async def test_query_document_tracing_uses_triples_client(self):
        edges = [
            RetrievedEdge(
                s="http://e.com/s1", p="http://e.com/p1", o="http://e.com/o1",
                s_label="S", p_label="P", o_label="O",
                score=0.9, concept="test",
            ),
        ]
        rag, _, _, triples_client, _ = self._make_rag(edges=edges)

        await rag.query(query="test", collection="test")

        assert triples_client.query.call_count > 0
