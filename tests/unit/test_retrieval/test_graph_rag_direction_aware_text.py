"""
Tests for direction-aware reranker text in GraphRAG hop-and-filter.

The reranker document text varies by traversal direction:
- From S (subject is the frontier entity): text = "{p} {o}"
- From O (object is the frontier entity): text = "{s} {p}"
- From P (predicate is the frontier entity): text = "{s} {o}"
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from trustgraph.retrieval.graph_rag.graph_rag import Query, LRUCacheWithTTL
from trustgraph.schema import Term, IRI, LITERAL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_rag(reranker_results=None):
    """Create a mock GraphRag with all clients stubbed."""
    rag = MagicMock()
    rag.label_cache = LRUCacheWithTTL()
    rag.triples_client = AsyncMock()
    rag.reranker_client = AsyncMock()

    # Label lookups return empty (fall back to URI)
    rag.triples_client.query.return_value = []

    if reranker_results is not None:
        rag.reranker_client.rerank.return_value = reranker_results
    else:
        rag.reranker_client.rerank.return_value = []

    return rag


def _make_query(rag, max_path_length=1, edge_limit=25):
    return Query(
        rag=rag,
        collection="test",
        verbose=False,
        entity_limit=50,
        triple_limit=30,
        max_subgraph_size=1000,
        max_path_length=max_path_length,
        edge_limit=edge_limit,
    )


def _make_schema_triple(s, p, o):
    """Create a mock triple matching the schema interface."""
    t = MagicMock()
    t.s = s
    t.p = p
    t.o = o
    return t


def _reranker_result(document_id, query_id="0", score=0.9):
    r = MagicMock()
    r.document_id = str(document_id)
    r.query_id = str(query_id)
    r.score = score
    return r


# ---------------------------------------------------------------------------
# Tests: execute_batch_triple_queries direction tracking
# ---------------------------------------------------------------------------

class TestDirectionTracking:

    @pytest.mark.asyncio
    async def test_from_s_direction(self):
        """Triples from s=entity queries are tagged FROM_S."""
        triple = _make_schema_triple("ent1", "pred", "obj")
        rag = _make_rag()

        async def query_stream(s=None, p=None, o=None, **kwargs):
            if s is not None:
                return [triple]
            return []

        rag.triples_client.query_stream.side_effect = query_stream
        q = _make_query(rag)

        result = await q.execute_batch_triple_queries(["ent1"], 10)

        from_s = [(t, d) for t, d in result if d == Query.FROM_S]
        assert len(from_s) == 1
        assert from_s[0][0] is triple

    @pytest.mark.asyncio
    async def test_from_o_direction(self):
        """Triples from o=entity queries are tagged FROM_O."""
        triple = _make_schema_triple("subj", "pred", "ent1")
        rag = _make_rag()

        async def query_stream(s=None, p=None, o=None, **kwargs):
            if o is not None:
                return [triple]
            return []

        rag.triples_client.query_stream.side_effect = query_stream
        q = _make_query(rag)

        result = await q.execute_batch_triple_queries(["ent1"], 10)

        from_o = [(t, d) for t, d in result if d == Query.FROM_O]
        assert len(from_o) == 1
        assert from_o[0][0] is triple

    @pytest.mark.asyncio
    async def test_from_p_direction(self):
        """Triples from p=entity queries are tagged FROM_P."""
        triple = _make_schema_triple("subj", "ent1", "obj")
        rag = _make_rag()

        async def query_stream(s=None, p=None, o=None, **kwargs):
            if p is not None:
                return [triple]
            return []

        rag.triples_client.query_stream.side_effect = query_stream
        q = _make_query(rag)

        result = await q.execute_batch_triple_queries(["ent1"], 10)

        from_p = [(t, d) for t, d in result if d == Query.FROM_P]
        assert len(from_p) == 1
        assert from_p[0][0] is triple


# ---------------------------------------------------------------------------
# Tests: hop_and_filter reranker document text
# ---------------------------------------------------------------------------

class TestDirectionAwareRerankerText:

    @pytest.mark.asyncio
    async def test_from_s_uses_predicate_object(self):
        """From-S traversal: reranker text should be '{p} {o}'."""
        triple = _make_schema_triple(
            "http://ex/entity-A",
            "http://ex/likes",
            "http://ex/entity-B",
        )
        reranker_result = _reranker_result(0)
        rag = _make_rag(reranker_results=[reranker_result])

        async def query_stream(s=None, p=None, o=None, **kwargs):
            if s is not None:
                return [triple]
            return []

        rag.triples_client.query_stream.side_effect = query_stream

        q = _make_query(rag, max_path_length=1, edge_limit=10)

        await q.hop_and_filter(
            seed_entities=["http://ex/entity-A"],
            concepts=["likes"],
        )

        call_args = rag.reranker_client.rerank.call_args
        documents = call_args.kwargs["documents"]
        # Text should be "{p} {o}" — the URIs since no labels found
        assert len(documents) == 1
        assert documents[0]["text"] == "http://ex/likes http://ex/entity-B"

    @pytest.mark.asyncio
    async def test_from_o_uses_subject_predicate(self):
        """From-O traversal: reranker text should be '{s} {p}'."""
        triple = _make_schema_triple(
            "http://ex/entity-A",
            "http://ex/likes",
            "http://ex/entity-B",
        )
        reranker_result = _reranker_result(0)
        rag = _make_rag(reranker_results=[reranker_result])

        async def query_stream(s=None, p=None, o=None, **kwargs):
            if o is not None:
                return [triple]
            return []

        rag.triples_client.query_stream.side_effect = query_stream

        q = _make_query(rag, max_path_length=1, edge_limit=10)

        await q.hop_and_filter(
            seed_entities=["http://ex/entity-B"],
            concepts=["likes"],
        )

        call_args = rag.reranker_client.rerank.call_args
        documents = call_args.kwargs["documents"]
        assert len(documents) == 1
        assert documents[0]["text"] == "http://ex/entity-A http://ex/likes"

    @pytest.mark.asyncio
    async def test_from_p_uses_subject_object(self):
        """From-P traversal: reranker text should be '{s} {o}'."""
        triple = _make_schema_triple(
            "http://ex/entity-A",
            "http://ex/likes",
            "http://ex/entity-B",
        )
        reranker_result = _reranker_result(0)
        rag = _make_rag(reranker_results=[reranker_result])

        async def query_stream(s=None, p=None, o=None, **kwargs):
            if p is not None:
                return [triple]
            return []

        rag.triples_client.query_stream.side_effect = query_stream

        q = _make_query(rag, max_path_length=1, edge_limit=10)

        await q.hop_and_filter(
            seed_entities=["http://ex/likes"],
            concepts=["entity"],
        )

        call_args = rag.reranker_client.rerank.call_args
        documents = call_args.kwargs["documents"]
        assert len(documents) == 1
        assert documents[0]["text"] == "http://ex/entity-A http://ex/entity-B"

    @pytest.mark.asyncio
    async def test_mixed_directions_produce_different_text(self):
        """Edges from different directions use different text formats."""
        triple_from_s = _make_schema_triple(
            "http://ex/seed", "http://ex/rel", "http://ex/target",
        )
        triple_from_o = _make_schema_triple(
            "http://ex/other", "http://ex/ref", "http://ex/seed",
        )

        rag = _make_rag(reranker_results=[
            _reranker_result(0), _reranker_result(1),
        ])

        async def query_stream(s=None, p=None, o=None, **kwargs):
            if s == "http://ex/seed":
                return [triple_from_s]
            if o == "http://ex/seed":
                return [triple_from_o]
            return []

        rag.triples_client.query_stream.side_effect = query_stream

        q = _make_query(rag, max_path_length=1, edge_limit=10)

        await q.hop_and_filter(
            seed_entities=["http://ex/seed"],
            concepts=["test"],
        )

        call_args = rag.reranker_client.rerank.call_args
        documents = call_args.kwargs["documents"]
        texts = {d["text"] for d in documents}

        # From S: "{p} {o}" = "http://ex/rel http://ex/target"
        assert "http://ex/rel http://ex/target" in texts
        # From O: "{s} {p}" = "http://ex/other http://ex/ref"
        assert "http://ex/other http://ex/ref" in texts

    @pytest.mark.asyncio
    async def test_labels_applied_to_direction_text(self):
        """Labels should be resolved and used in the direction-aware text."""
        triple = _make_schema_triple(
            "http://ex/entity-A",
            "http://ex/likes",
            "http://ex/entity-B",
        )
        reranker_result = _reranker_result(0)
        rag = _make_rag(reranker_results=[reranker_result])

        LABEL = "http://www.w3.org/2000/01/rdf-schema#label"

        async def query_stream(s=None, p=None, o=None, **kwargs):
            if s is not None and p is None:
                return [triple]
            return []

        async def label_query(s=None, p=None, o=None, limit=1, **kwargs):
            if p == LABEL:
                labels = {
                    "http://ex/entity-A": "Alice",
                    "http://ex/likes": "likes",
                    "http://ex/entity-B": "Bob",
                }
                if s in labels:
                    return [MagicMock(o=labels[s])]
            return []

        rag.triples_client.query_stream.side_effect = query_stream
        rag.triples_client.query.side_effect = label_query

        q = _make_query(rag, max_path_length=1, edge_limit=10)

        await q.hop_and_filter(
            seed_entities=["http://ex/entity-A"],
            concepts=["friendship"],
        )

        call_args = rag.reranker_client.rerank.call_args
        documents = call_args.kwargs["documents"]
        assert len(documents) == 1
        # From S with labels: "{p_label} {o_label}"
        assert documents[0]["text"] == "likes Bob"

    @pytest.mark.asyncio
    async def test_no_duplicate_text_from_shared_object(self):
        """Multiple edges sharing an object should produce distinct texts."""
        triple_a = _make_schema_triple(
            "http://ex/cpu-A", "http://ex/hasCategory", "http://ex/Processors",
        )
        triple_b = _make_schema_triple(
            "http://ex/cpu-B", "http://ex/hasCategory", "http://ex/Processors",
        )

        rag = _make_rag(reranker_results=[
            _reranker_result(0), _reranker_result(1),
        ])

        async def query_stream(s=None, p=None, o=None, **kwargs):
            if o == "http://ex/Processors":
                return [triple_a, triple_b]
            return []

        rag.triples_client.query_stream.side_effect = query_stream

        q = _make_query(rag, max_path_length=1, edge_limit=10)

        await q.hop_and_filter(
            seed_entities=["http://ex/Processors"],
            concepts=["CPUs"],
        )

        call_args = rag.reranker_client.rerank.call_args
        documents = call_args.kwargs["documents"]
        texts = [d["text"] for d in documents]

        assert len(texts) == 2
        # From O: "{s} {p}" — subjects differ, so texts differ
        assert texts[0] != texts[1]
        assert "http://ex/cpu-A" in texts[0]
        assert "http://ex/cpu-B" in texts[1]
