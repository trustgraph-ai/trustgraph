"""
Tests for the optional cross-encoder reranking pass in DocumentRag.query().

Two behaviours are covered:

  1. No-op: when no reranker_client is wired (the default), query() must feed
     the LLM the exact same chunks, in the same order, that retrieval produced
     - byte-identical to the pre-reranker behaviour - and must NOT emit a
     chunk-selection provenance event.

  2. Rerank: when a reranker_client is wired, the retrieved chunks are reordered
     and truncated according to the reranker's results, the LLM receives the
     reranked top-N, and a tg:ChunkSelection (focus) provenance event is emitted
     carrying the per-surviving-chunk scores and chunk references.

These are pure orchestration tests - the reranker is a stub, so there is no
torch / network dependency.
"""

import pytest
from unittest.mock import AsyncMock
from dataclasses import dataclass

from trustgraph.retrieval.document_rag.document_rag import DocumentRag
from trustgraph.base import PromptResult
from trustgraph.schema import RerankerResult

from trustgraph.provenance.namespaces import (
    RDF_TYPE, PROV_WAS_DERIVED_FROM,
    TG_DOC_RAG_QUESTION, TG_GROUNDING, TG_EXPLORATION,
    TG_FOCUS, TG_SYNTHESIS,
    TG_CHUNK_SELECTION, TG_SELECTED_CHUNK, TG_SCORE, TG_DOCUMENT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_triple(triples, predicate, subject=None):
    for t in triples:
        if t.p.iri == predicate:
            if subject is None or t.s.iri == subject:
                return t
    return None


def find_triples(triples, predicate, subject=None):
    return [
        t for t in triples
        if t.p.iri == predicate
        and (subject is None or t.s.iri == subject)
    ]


def has_type(triples, subject, rdf_type):
    return any(
        t.s.iri == subject and t.p.iri == RDF_TYPE and t.o.iri == rdf_type
        for t in triples
    )


def derived_from(triples, subject):
    t = find_triple(triples, PROV_WAS_DERIVED_FROM, subject)
    return t.o.iri if t else None


@dataclass
class ChunkMatch:
    """Mimics the result from doc_embeddings_client.query()."""
    chunk_id: str


# ---------------------------------------------------------------------------
# Fixtures: three retrievable chunks
# ---------------------------------------------------------------------------

CHUNK_A = "urn:chunk:policy-doc-1:chunk-0"
CHUNK_B = "urn:chunk:policy-doc-1:chunk-1"
CHUNK_C = "urn:chunk:policy-doc-1:chunk-2"

CHUNK_A_CONTENT = "Customers may return items within 30 days of purchase."
CHUNK_B_CONTENT = "Our stores are open from 9am to 5pm on weekdays."
CHUNK_C_CONTENT = "Refunds are processed to the original payment method."

# Retrieval (post-dedupe) order is A, B, C.
ORDERED_CONTENT = [CHUNK_A_CONTENT, CHUNK_B_CONTENT, CHUNK_C_CONTENT]
ORDERED_CHUNK_IDS = [CHUNK_A, CHUNK_B, CHUNK_C]


def build_mock_clients():
    """
    Build mock subsidiary clients for a document-rag query returning three
    distinct chunks (A, B, C) in that order.
    """
    prompt_client = AsyncMock()
    embeddings_client = AsyncMock()
    doc_embeddings_client = AsyncMock()
    fetch_chunk = AsyncMock()

    async def mock_prompt(template_id, variables=None, **kwargs):
        if template_id == "extract-concepts":
            return PromptResult(response_type="text", text="return policy\nrefund")
        return PromptResult(response_type="text", text="")

    prompt_client.prompt.side_effect = mock_prompt

    embeddings_client.embed.return_value = [[0.1, 0.2], [0.3, 0.4]]

    # Each concept query returns the same three chunks; dedupe keeps A, B, C.
    doc_embeddings_client.query.return_value = [
        ChunkMatch(chunk_id=CHUNK_A),
        ChunkMatch(chunk_id=CHUNK_B),
        ChunkMatch(chunk_id=CHUNK_C),
    ]

    async def mock_fetch(chunk_id):
        return {
            CHUNK_A: CHUNK_A_CONTENT,
            CHUNK_B: CHUNK_B_CONTENT,
            CHUNK_C: CHUNK_C_CONTENT,
        }[chunk_id]

    fetch_chunk.side_effect = mock_fetch

    prompt_client.document_prompt.return_value = PromptResult(
        response_type="text",
        text="Items can be returned within 30 days for a full refund.",
    )

    return prompt_client, embeddings_client, doc_embeddings_client, fetch_chunk


class StubReranker:
    """
    Stub reranker_client mirroring RerankerClient.rerank(): returns a fixed,
    pre-sorted, truncated list of RerankerResult - exactly the contract the
    flashrank service guarantees (sorted desc by score, truncated to limit).
    """

    def __init__(self, results):
        self._results = results
        self.calls = []

    async def rerank(self, queries, documents, limit=10, timeout=300):
        self.calls.append(
            {"queries": queries, "documents": documents, "limit": limit}
        )
        return self._results


# ---------------------------------------------------------------------------
# 1. No-op: reranker_client=None must not change anything
# ---------------------------------------------------------------------------

class TestRerankNoOp:

    @pytest.mark.asyncio
    async def test_documents_passed_to_llm_are_unchanged(self):
        """
        With no reranker wired, document_prompt must receive the retrieved
        chunks in the original order and length.
        """
        clients = build_mock_clients()
        rag = DocumentRag(*clients)  # reranker_client defaults to None

        await rag.query(query="What is the return policy?")

        call = rag.prompt_client.document_prompt.call_args
        passed_docs = call.kwargs["documents"]
        assert passed_docs == ORDERED_CONTENT

    @pytest.mark.asyncio
    async def test_no_chunk_selection_event_emitted(self):
        """
        Without a reranker, the provenance chain is the original 4 stages:
        question, grounding, exploration, synthesis - no focus stage.
        """
        clients = build_mock_clients()
        rag = DocumentRag(*clients)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is the return policy?",
            explain_callback=explain_callback,
        )

        assert len(events) == 4
        types = [
            TG_DOC_RAG_QUESTION, TG_GROUNDING, TG_EXPLORATION, TG_SYNTHESIS,
        ]
        for i, expected in enumerate(types):
            assert has_type(events[i]["triples"], events[i]["explain_id"], expected)

        # No chunk-selection entity anywhere.
        for e in events:
            assert not any(
                t.o.iri == TG_CHUNK_SELECTION
                for t in e["triples"]
                if t.p.iri == RDF_TYPE
            )

    @pytest.mark.asyncio
    async def test_synthesis_derives_from_exploration_when_no_rerank(self):
        """
        No-op lineage is unchanged: synthesis derives from exploration
        (there is no focus stage). Guards the conditional synthesis parent.
        """
        clients = build_mock_clients()
        rag = DocumentRag(*clients)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is the return policy?",
            explain_callback=explain_callback,
        )

        # events: question, grounding, exploration, synthesis
        exp_uri = events[2]["explain_id"]
        syn_event = events[3]
        assert derived_from(syn_event["triples"], syn_event["explain_id"]) == exp_uri


# ---------------------------------------------------------------------------
# 2. Rerank: reorder + truncate + provenance
# ---------------------------------------------------------------------------

class TestRerankActive:

    def _reranker_keeping_C_then_A(self):
        # Reranker says chunk index 2 (C) is best, then index 0 (A); B dropped.
        # Pre-sorted desc by score and truncated to limit, per the contract.
        return StubReranker([
            RerankerResult(document_id="2", query_id="0", score=0.95),
            RerankerResult(document_id="0", query_id="0", score=0.42),
        ])

    @pytest.mark.asyncio
    async def test_documents_reordered_and_truncated(self):
        clients = build_mock_clients()
        reranker = self._reranker_keeping_C_then_A()
        rag = DocumentRag(*clients, reranker_client=reranker)

        await rag.query(query="What is the return policy?")

        call = rag.prompt_client.document_prompt.call_args
        passed_docs = call.kwargs["documents"]
        assert passed_docs == [CHUNK_C_CONTENT, CHUNK_A_CONTENT]

    @pytest.mark.asyncio
    async def test_reranker_called_with_single_query_and_all_docs(self):
        clients = build_mock_clients()
        reranker = self._reranker_keeping_C_then_A()
        rag = DocumentRag(*clients, reranker_client=reranker)

        await rag.query(query="What is the return policy?", doc_limit=2)

        assert len(reranker.calls) == 1
        c = reranker.calls[0]
        assert c["queries"] == [{"id": "0", "text": "What is the return policy?"}]
        assert c["documents"] == [
            {"id": "0", "text": CHUNK_A_CONTENT},
            {"id": "1", "text": CHUNK_B_CONTENT},
            {"id": "2", "text": CHUNK_C_CONTENT},
        ]
        # The rerank narrows down to the final doc_limit, NOT fetch_limit
        # (fetch_limit is the over-fetched candidate pool size).
        assert c["limit"] == 2

    @pytest.mark.asyncio
    async def test_explicit_fetch_limit_over_fetches_then_narrows(self):
        """
        Semantic guard for the value of reranking AND the maintainer's two-limit
        contract: an explicit fetch_limit makes retrieval OVER-FETCH a wider
        candidate pool so the cross-encoder can surface chunks the bi-encoder
        ranked outside the final doc_limit, then the rerank narrows the pool back
        down to doc_limit. The fetch_limit is honoured directly (caller controls
        how hard the reranker works), not overridden by any heuristic.
        """
        clients = build_mock_clients()
        prompt_client, embeddings_client, doc_embeddings_client, fetch_chunk = clients
        reranker = self._reranker_keeping_C_then_A()
        # Candidate pool (fetch_limit=60) >> final doc_limit (6).
        rag = DocumentRag(*clients, reranker_client=reranker)

        await rag.query(
            query="What is the return policy?", doc_limit=6, fetch_limit=60,
        )

        # Over-fetch: the embeddings store is queried with the fetch_limit
        # budget (60 // 2 concept-vectors = 30 per concept), NOT the doc_limit
        # budget (6 // 2 = 3). This is the bug guard.
        q_limit = doc_embeddings_client.query.call_args.kwargs["limit"]
        assert q_limit == 30

        # Narrow: the rerank keeps the final doc_limit (6), not fetch_limit.
        assert reranker.calls[0]["limit"] == 6

    @pytest.mark.asyncio
    async def test_default_fetch_limit_derives_overfetch_from_doc_limit(self):
        """
        With no fetch_limit passed to query(), the candidate pool falls back to
        the OVERFETCH_FACTOR x doc_limit heuristic, so over-fetch scales with
        doc_limit and reranking keeps its recall benefit out of the box.
        """
        clients = build_mock_clients()
        prompt_client, embeddings_client, doc_embeddings_client, fetch_chunk = clients
        reranker = self._reranker_keeping_C_then_A()
        # No fetch_limit -> heuristic default.
        rag = DocumentRag(*clients, reranker_client=reranker)

        await rag.query(query="What is the return policy?", doc_limit=20)

        # fetch = 3 x 20 = 60 -> 60 // 2 concept-vectors = 30 per concept.
        q_limit = doc_embeddings_client.query.call_args.kwargs["limit"]
        assert q_limit == 30
        # Rerank narrows to the final doc_limit (20).
        assert reranker.calls[0]["limit"] == 20

    @pytest.mark.asyncio
    async def test_fetch_limit_floored_at_doc_limit(self):
        """
        A fetch_limit below doc_limit is floored up to doc_limit: retrieval must
        never fetch fewer candidates than the rerank is asked to keep, else the
        prompt could not be filled.
        """
        clients = build_mock_clients()
        prompt_client, embeddings_client, doc_embeddings_client, fetch_chunk = clients
        reranker = self._reranker_keeping_C_then_A()
        rag = DocumentRag(*clients, reranker_client=reranker)

        await rag.query(
            query="What is the return policy?", doc_limit=10, fetch_limit=4,
        )

        # fetch = max(4, 10) = 10 -> 10 // 2 concept-vectors = 5 per concept.
        q_limit = doc_embeddings_client.query.call_args.kwargs["limit"]
        assert q_limit == 5
        assert reranker.calls[0]["limit"] == 10

    @pytest.mark.asyncio
    async def test_chunk_selection_event_emitted(self):
        clients = build_mock_clients()
        reranker = self._reranker_keeping_C_then_A()
        rag = DocumentRag(*clients, reranker_client=reranker)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is the return policy?",
            explain_callback=explain_callback,
        )

        # Now 5 stages: question, grounding, exploration, focus, synthesis.
        assert len(events) == 5
        ordered_types = [
            TG_DOC_RAG_QUESTION, TG_GROUNDING, TG_EXPLORATION,
            TG_FOCUS, TG_SYNTHESIS,
        ]
        for i, expected in enumerate(ordered_types):
            assert has_type(events[i]["triples"], events[i]["explain_id"], expected)

    @pytest.mark.asyncio
    async def test_chunk_selection_carries_scores_and_chunk_refs(self):
        clients = build_mock_clients()
        reranker = self._reranker_keeping_C_then_A()
        rag = DocumentRag(*clients, reranker_client=reranker)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is the return policy?",
            explain_callback=explain_callback,
        )

        focus_event = events[3]
        foc_uri = focus_event["explain_id"]
        triples = focus_event["triples"]

        # focus is derived from exploration
        exp_uri = events[2]["explain_id"]
        assert derived_from(triples, foc_uri) == exp_uri

        # Two ChunkSelection sub-entities, linked from focus.
        sel_links = find_triples(triples, TG_SELECTED_CHUNK, foc_uri)
        assert len(sel_links) == 2

        # Each selection has a ChunkSelection type, a chunk document ref and a score.
        chunk_refs = set()
        scores = set()
        for link in sel_links:
            sel_uri = link.o.iri
            assert has_type(triples, sel_uri, TG_CHUNK_SELECTION)
            doc_ref = find_triple(triples, TG_DOCUMENT, sel_uri)
            assert doc_ref is not None
            chunk_refs.add(doc_ref.o.iri)
            score_t = find_triple(triples, TG_SCORE, sel_uri)
            assert score_t is not None
            scores.add(score_t.o.value)

        # Surviving chunks are C and A (B dropped), with the reranker scores.
        assert chunk_refs == {CHUNK_C, CHUNK_A}
        assert scores == {"0.95", "0.42"}

    @pytest.mark.asyncio
    async def test_all_focus_triples_in_retrieval_graph(self):
        clients = build_mock_clients()
        reranker = self._reranker_keeping_C_then_A()
        rag = DocumentRag(*clients, reranker_client=reranker)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is the return policy?",
            explain_callback=explain_callback,
        )

        for t in events[3]["triples"]:
            assert t.g == "urn:graph:retrieval"

    @pytest.mark.asyncio
    async def test_synthesis_derives_from_focus_when_reranking(self):
        """
        When reranking runs, synthesis must derive from the focus node (the
        reranked chunks actually fed to the LLM), mirroring GraphRAG - not from
        exploration, which would leave focus as a dangling branch and
        misrepresent what fed the answer.
        """
        clients = build_mock_clients()
        reranker = self._reranker_keeping_C_then_A()
        rag = DocumentRag(*clients, reranker_client=reranker)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is the return policy?",
            doc_limit=2,
            explain_callback=explain_callback,
        )

        # events: question, grounding, exploration, focus, synthesis
        foc_uri = events[3]["explain_id"]
        syn_event = events[4]
        assert derived_from(syn_event["triples"], syn_event["explain_id"]) == foc_uri

    @pytest.mark.asyncio
    async def test_empty_docs_skips_reranker(self):
        """If retrieval returns no chunks, the reranker is never called."""
        clients = build_mock_clients()
        prompt_client, embeddings_client, doc_embeddings_client, fetch_chunk = clients
        doc_embeddings_client.query.return_value = []  # no matches

        reranker = self._reranker_keeping_C_then_A()
        rag = DocumentRag(*clients, reranker_client=reranker)

        await rag.query(query="What is the return policy?")

        assert reranker.calls == []

# ---------------------------------------------------------------------------
# 3. Diversity selection: optional MMR after cross-encoder scoring
# ---------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_diversity_mode_scores_full_candidate_pool_before_selecting(self):
        """
        With diversity selection enabled, the cross-encoder should score the full
        fetched candidate pool before MMR narrows it down to doc_limit.
        """
        clients = build_mock_clients()
        reranker = StubReranker([
            RerankerResult(document_id="0", query_id="0", score=1.00),
            RerankerResult(document_id="1", query_id="0", score=0.95),
            RerankerResult(document_id="2", query_id="0", score=0.90),
        ])
        rag = DocumentRag(
            *clients,
            reranker_client=reranker,
            rerank_diversity_mode="mmr",
        )

        await rag.query(query="What is the return policy?", doc_limit=2)

        assert reranker.calls[0]["limit"] == len(ORDERED_CONTENT)

        call = rag.prompt_client.document_prompt.call_args
        passed_docs = call.kwargs["documents"]
        assert len(passed_docs) == 2


    @pytest.mark.asyncio
    async def test_diversity_mode_selects_less_redundant_context_set(self):
        """
        MMR should use cross-encoder scores as relevance while penalizing redundant
        chunks, so a slightly lower-scored but less redundant chunk can be selected.
        """
        clients = build_mock_clients()
        prompt_client, embeddings_client, doc_embeddings_client, fetch_chunk = clients

        duplicate_a = "apple banana fruit return policy"
        duplicate_b = "apple banana fruit return policy duplicate"
        diverse_c = "engine motor vehicle warranty"

        async def mock_fetch(chunk_id):
            return {
                CHUNK_A: duplicate_a,
                CHUNK_B: duplicate_b,
                CHUNK_C: diverse_c,
            }[chunk_id]

        fetch_chunk.side_effect = mock_fetch

        reranker = StubReranker([
            RerankerResult(document_id="0", query_id="0", score=1.00),
            RerankerResult(document_id="1", query_id="0", score=0.95),
            RerankerResult(document_id="2", query_id="0", score=0.90),
        ])
        rag = DocumentRag(
            *clients,
            reranker_client=reranker,
            rerank_diversity_mode="mmr",
            rerank_diversity_lambda=0.2,
        )

        await rag.query(query="What is the return policy?", doc_limit=2)

        call = rag.prompt_client.document_prompt.call_args
        passed_docs = call.kwargs["documents"]

        assert passed_docs == [duplicate_a, diverse_c]