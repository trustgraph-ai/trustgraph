"""
Tests for the retrieval-mode dispatch in DocumentRag (issue: hybrid
BM25 + vector retrieval).

Covered behaviours:

  1. Default: retrieval_mode="vector" never touches the keyword client and
     produces the same chunks as before — the sparse path is strictly opt-in.
  2. keyword: only the keyword index is queried (no vector-store query, no
     embedding of concepts); chunk order follows the BM25 ranking.
  3. hybrid: both paths run and are fused by weighted RRF on chunk_id; a
     keyword-path failure degrades to vector-only instead of failing the
     query.
  4. Constructing with keyword/hybrid but no keyword client is an error.

Pure orchestration tests: all subsidiary clients are stubs.
"""

import pytest
from unittest.mock import AsyncMock

from trustgraph.retrieval.document_rag.document_rag import (
    DocumentRag, rrf_fuse, RRF_K,
)
from trustgraph.base import PromptResult
from trustgraph.schema import ChunkMatch


CONTENT = {
    "v1": "vector chunk one",
    "v2": "vector chunk two",
    "k1": "keyword chunk one",
    "both": "chunk found by both paths",
}


def build_clients(vector_ids, keyword_ids):
    prompt_client = AsyncMock()
    embeddings_client = AsyncMock()
    doc_embeddings_client = AsyncMock()
    kw_index_client = AsyncMock()
    fetch_chunk = AsyncMock()

    async def mock_prompt(template_id, variables=None, **kwargs):
        if template_id == "extract-concepts":
            return PromptResult(response_type="text", text="concept")
        return PromptResult(response_type="text", text="")

    prompt_client.prompt.side_effect = mock_prompt
    prompt_client.document_prompt.return_value = PromptResult(
        response_type="text", text="answer",
    )

    embeddings_client.embed.return_value = [[0.1, 0.2]]

    doc_embeddings_client.query.return_value = [
        ChunkMatch(chunk_id=c) for c in vector_ids
    ]
    kw_index_client.query.return_value = [
        ChunkMatch(chunk_id=c, score=1.0) for c in keyword_ids
    ]

    fetch_chunk.side_effect = lambda chunk_id: CONTENT[chunk_id]

    return (
        prompt_client, embeddings_client, doc_embeddings_client,
        kw_index_client, fetch_chunk,
    )


def build_rag(vector_ids, keyword_ids, **kwargs):
    prompt, embeddings, doc_embeddings, kw, fetch = build_clients(
        vector_ids, keyword_ids,
    )
    rag = DocumentRag(
        prompt_client=prompt,
        embeddings_client=embeddings,
        doc_embeddings_client=doc_embeddings,
        fetch_chunk=fetch,
        kw_index_client=kw,
        **kwargs,
    )
    return rag, doc_embeddings, kw, embeddings, prompt


# ---------------------------------------------------------------------------
# rrf_fuse
# ---------------------------------------------------------------------------

class TestRrfFuse:

    def test_chunk_in_both_lists_outranks_single_list_leaders(self):
        a = ChunkMatch("a")
        b = ChunkMatch("b")
        both = ChunkMatch("both")
        fused = rrf_fuse([[a, both], [both, b]], [1.0, 1.0], 10)
        assert [m.chunk_id for m in fused][0] == "both"
        assert {m.chunk_id for m in fused} == {"a", "b", "both"}

    def test_weights_bias_the_fusion(self):
        a, b = ChunkMatch("a"), ChunkMatch("b")
        fused = rrf_fuse([[a], [b]], [1.0, 10.0], 10)
        assert [m.chunk_id for m in fused] == ["b", "a"]

    def test_limit_truncates(self):
        matches = [ChunkMatch(f"c{i}") for i in range(5)]
        assert len(rrf_fuse([matches], [1.0], 2)) == 2

    def test_cross_list_accumulation_beats_single_top_rank(self):
        # b sums 1/(K+2) + 1/(K+3) across two lists, beating the single
        # 1/(K+1) that a gets — the accumulation property that
        # distinguishes RRF from a best-rank merge.
        a, b, x, y = (ChunkMatch(c) for c in "abxy")
        fused = rrf_fuse([[a, b], [x, y, b]], [1.0, 1.0], 10)
        assert fused[0].chunk_id == "b"
        assert 1 / (RRF_K + 2) + 1 / (RRF_K + 3) > 1 / (RRF_K + 1)

    def test_empty_chunk_ids_are_skipped(self):
        fused = rrf_fuse([[ChunkMatch(""), ChunkMatch("a")]], [1.0], 10)
        assert [m.chunk_id for m in fused] == ["a"]


# ---------------------------------------------------------------------------
# Mode dispatch through DocumentRag.query()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vector_mode_never_touches_keyword_client():
    rag, doc_embeddings, kw, _, prompt = build_rag(
        ["v1", "v2"], ["k1"], retrieval_mode="vector",
    )
    await rag.query("question")

    kw.query.assert_not_called()
    doc_embeddings.query.assert_called()
    docs = prompt.document_prompt.call_args.kwargs["documents"]
    assert docs == [CONTENT["v1"], CONTENT["v2"]]


@pytest.mark.asyncio
async def test_default_mode_is_vector_with_no_keyword_client():
    prompt, embeddings, doc_embeddings, _, fetch = build_clients(
        ["v1"], [],
    )
    rag = DocumentRag(
        prompt_client=prompt,
        embeddings_client=embeddings,
        doc_embeddings_client=doc_embeddings,
        fetch_chunk=fetch,
    )
    await rag.query("question")
    docs = prompt.document_prompt.call_args.kwargs["documents"]
    assert docs == [CONTENT["v1"]]


@pytest.mark.asyncio
async def test_keyword_mode_skips_vector_store_and_embeddings():
    rag, doc_embeddings, kw, embeddings, prompt = build_rag(
        ["v1", "v2"], ["k1", "both"], retrieval_mode="keyword",
    )
    await rag.query("what does clause 7.3.2 say")

    doc_embeddings.query.assert_not_called()
    embeddings.embed.assert_not_called()
    # No dense path -> no concept-extraction LLM call either
    prompt.prompt.assert_not_called()
    # The sparse path searches the raw query text, not extracted concepts
    assert kw.query.call_args.kwargs["query"] == "what does clause 7.3.2 say"
    docs = prompt.document_prompt.call_args.kwargs["documents"]
    assert docs == [CONTENT["k1"], CONTENT["both"]]


@pytest.mark.asyncio
async def test_hybrid_mode_fuses_both_paths():
    # both appears in both rankings, so RRF must put it first
    rag, doc_embeddings, kw, _, prompt = build_rag(
        ["v1", "both"], ["both", "k1"], retrieval_mode="hybrid",
    )
    await rag.query("question")

    doc_embeddings.query.assert_called()
    kw.query.assert_called()
    docs = prompt.document_prompt.call_args.kwargs["documents"]
    assert docs[0] == CONTENT["both"]
    assert set(docs) == {CONTENT["both"], CONTENT["v1"], CONTENT["k1"]}


@pytest.mark.asyncio
async def test_hybrid_degrades_to_vector_when_keyword_path_fails():
    rag, doc_embeddings, kw, _, prompt = build_rag(
        ["v1", "v2"], [], retrieval_mode="hybrid",
    )
    kw.query.side_effect = RuntimeError("keyword index down")

    await rag.query("question")

    docs = prompt.document_prompt.call_args.kwargs["documents"]
    assert docs == [CONTENT["v1"], CONTENT["v2"]]


def test_non_vector_mode_without_client_is_an_error():
    prompt, embeddings, doc_embeddings, _, fetch = build_clients([], [])
    for mode in ("keyword", "hybrid"):
        with pytest.raises(ValueError):
            DocumentRag(
                prompt_client=prompt,
                embeddings_client=embeddings,
                doc_embeddings_client=doc_embeddings,
                fetch_chunk=fetch,
                retrieval_mode=mode,
            )
