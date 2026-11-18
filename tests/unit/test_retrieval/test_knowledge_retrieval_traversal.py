"""
Tests for knowledge retrieval traversal engine.

Covers: LRU cache, concurrent batch triple queries, direction tracking,
direction-aware reranker text, label resolution, language filtering,
and hop-and-filter graph traversal.
"""

import asyncio
import time

import pytest
from unittest.mock import MagicMock, AsyncMock

from trustgraph.retrieval.knowledge_retrieval.traversal import (
    TraversalEngine, LRUCacheWithTTL, FROM_S, FROM_P, FROM_O,
)


LABEL = "http://www.w3.org/2000/01/rdf-schema#label"


def _make_engine(
    triples_client=None,
    reranker_client=None,
    embeddings_client=None,
    graph_embeddings_client=None,
    collection="test-collection",
    entity_limit=50,
    triple_limit=30,
    max_path_length=2,
    edge_limit=25,
    max_reranker_input=350,
    languages=None,
    graph=None,
):
    return TraversalEngine(
        embeddings_client=embeddings_client or AsyncMock(),
        graph_embeddings_client=graph_embeddings_client or AsyncMock(),
        triples_client=triples_client or AsyncMock(),
        reranker_client=reranker_client or AsyncMock(),
        collection=collection,
        entity_limit=entity_limit,
        triple_limit=triple_limit,
        max_path_length=max_path_length,
        edge_limit=edge_limit,
        max_reranker_input=max_reranker_input,
        languages=languages,
        graph=graph,
    )


def _make_triple(s, p, o):
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


def _make_direction_engine(reranker_results=None, labels=None):
    triples_client = AsyncMock()
    reranker_client = AsyncMock()

    if labels:
        async def label_query(s=None, p=None, o=None, limit=1, **kwargs):
            if p == LABEL and s in labels:
                return [MagicMock(o=labels[s])]
            return []
        triples_client.query.side_effect = label_query
    else:
        triples_client.query.return_value = []

    if reranker_results is not None:
        reranker_client.rerank.return_value = reranker_results
    else:
        reranker_client.rerank.return_value = []

    engine = TraversalEngine(
        embeddings_client=AsyncMock(),
        graph_embeddings_client=AsyncMock(),
        triples_client=triples_client,
        reranker_client=reranker_client,
        collection="test",
        max_path_length=1,
        edge_limit=25,
    )

    return engine, triples_client, reranker_client


class TestLRUCacheWithTTL:

    def test_put_and_get(self):
        cache = LRUCacheWithTTL(max_size=10, ttl=60)
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_returns_none(self):
        cache = LRUCacheWithTTL()
        assert cache.get("nonexistent") is None

    def test_max_size_eviction(self):
        cache = LRUCacheWithTTL(max_size=2, ttl=60)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_lru_order(self):
        cache = LRUCacheWithTTL(max_size=2, ttl=60)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")
        cache.put("c", 3)
        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3

    def test_ttl_expiration(self):
        cache = LRUCacheWithTTL(max_size=10, ttl=0)
        cache.put("key", "value")
        time.sleep(0.01)
        assert cache.get("key") is None

    def test_update_existing_key(self):
        cache = LRUCacheWithTTL(max_size=10, ttl=60)
        cache.put("key", "v1")
        cache.put("key", "v2")
        assert cache.get("key") == "v2"


class TestBatchTripleQueries:

    @pytest.mark.asyncio
    async def test_three_queries_per_entity(self):
        client = AsyncMock()
        client.query_stream = AsyncMock(return_value=[])
        engine = _make_engine(triples_client=client)

        await engine.execute_batch_triple_queries(["entity-1"], limit_per_entity=10)

        assert client.query_stream.call_count == 3

    @pytest.mark.asyncio
    async def test_multiple_entities_multiply_queries(self):
        client = AsyncMock()
        client.query_stream = AsyncMock(return_value=[])
        engine = _make_engine(triples_client=client)

        await engine.execute_batch_triple_queries(
            ["e1", "e2", "e3"], limit_per_entity=10,
        )

        assert client.query_stream.call_count == 9

    @pytest.mark.asyncio
    async def test_queries_executed_concurrently(self):
        concurrent_count = 0
        max_concurrent = 0

        async def tracking_query(**kwargs):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.02)
            concurrent_count -= 1
            return []

        client = AsyncMock()
        client.query_stream = tracking_query
        engine = _make_engine(triples_client=client)

        await engine.execute_batch_triple_queries(
            ["e1", "e2", "e3"], limit_per_entity=5,
        )

        assert max_concurrent == 9

    @pytest.mark.asyncio
    async def test_results_aggregated(self):
        triple_a = _make_triple("a", "p", "b")
        triple_b = _make_triple("c", "p", "d")
        call_count = 0

        async def alternating_results(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                return [triple_a]
            return [triple_b]

        client = AsyncMock()
        client.query_stream = alternating_results
        engine = _make_engine(triples_client=client)

        result = await engine.execute_batch_triple_queries(
            ["e1"], limit_per_entity=10,
        )

        assert len(result) == 3
        for triple, direction in result:
            assert direction in (FROM_S, FROM_P, FROM_O)

    @pytest.mark.asyncio
    async def test_exception_in_one_query_does_not_block_others(self):
        good_triple = _make_triple("a", "p", "b")
        call_count = 0

        async def mixed_results(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("query failed")
            return [good_triple]

        client = AsyncMock()
        client.query_stream = mixed_results
        engine = _make_engine(triples_client=client)

        result = await engine.execute_batch_triple_queries(
            ["e1"], limit_per_entity=10,
        )

        assert len(result) == 2
        for triple, direction in result:
            assert direction in (FROM_S, FROM_P, FROM_O)

    @pytest.mark.asyncio
    async def test_none_results_filtered(self):
        call_count = 0

        async def sometimes_none(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None
            return [_make_triple("a", "p", "b")]

        client = AsyncMock()
        client.query_stream = sometimes_none
        engine = _make_engine(triples_client=client)

        result = await engine.execute_batch_triple_queries(
            ["e1"], limit_per_entity=10,
        )

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_empty_entities_no_queries(self):
        client = AsyncMock()
        client.query_stream = AsyncMock(return_value=[])
        engine = _make_engine(triples_client=client)

        result = await engine.execute_batch_triple_queries(
            [], limit_per_entity=10,
        )

        assert result == []
        client.query_stream.assert_not_called()

    @pytest.mark.asyncio
    async def test_query_params_correct(self):
        client = AsyncMock()
        client.query_stream = AsyncMock(return_value=[])
        engine = _make_engine(triples_client=client)

        await engine.execute_batch_triple_queries(
            ["ent-1"], limit_per_entity=15,
        )

        calls = client.query_stream.call_args_list
        assert len(calls) == 3

        assert calls[0].kwargs["s"] == "ent-1"
        assert calls[0].kwargs["p"] is None
        assert calls[0].kwargs["o"] is None
        assert calls[0].kwargs["limit"] == 15
        assert calls[0].kwargs["collection"] == "test-collection"
        assert calls[0].kwargs["batch_size"] == 20

        assert calls[1].kwargs["s"] is None
        assert calls[1].kwargs["p"] == "ent-1"
        assert calls[1].kwargs["o"] is None

        assert calls[2].kwargs["s"] is None
        assert calls[2].kwargs["p"] is None
        assert calls[2].kwargs["o"] == "ent-1"

    @pytest.mark.asyncio
    async def test_directions_assigned_correctly(self):
        triple = _make_triple("s", "p", "o")
        call_count = 0

        async def one_triple_each(**kwargs):
            nonlocal call_count
            call_count += 1
            return [triple]

        client = AsyncMock()
        client.query_stream = one_triple_each
        engine = _make_engine(triples_client=client)

        result = await engine.execute_batch_triple_queries(
            ["e1"], limit_per_entity=10,
        )

        assert len(result) == 3
        assert result[0][1] == FROM_S
        assert result[1][1] == FROM_P
        assert result[2][1] == FROM_O

    @pytest.mark.asyncio
    async def test_directions_correct_for_multiple_entities(self):
        triple = _make_triple("s", "p", "o")
        client = AsyncMock()
        client.query_stream = AsyncMock(return_value=[triple])
        engine = _make_engine(triples_client=client)

        result = await engine.execute_batch_triple_queries(
            ["e1", "e2"], limit_per_entity=10,
        )

        assert len(result) == 6
        expected = [FROM_S, FROM_P, FROM_O, FROM_S, FROM_P, FROM_O]
        for (_, direction), exp in zip(result, expected):
            assert direction == exp

    @pytest.mark.asyncio
    async def test_direction_preserved_with_multiple_triples(self):
        t1 = _make_triple("a", "p1", "b")
        t2 = _make_triple("a", "p2", "c")
        call_count = 0

        async def multi_results(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [t1, t2]
            return []

        client = AsyncMock()
        client.query_stream = multi_results
        engine = _make_engine(triples_client=client)

        result = await engine.execute_batch_triple_queries(
            ["e1"], limit_per_entity=10,
        )

        assert len(result) == 2
        assert result[0] == (t1, FROM_S)
        assert result[1] == (t2, FROM_S)

    @pytest.mark.asyncio
    async def test_workspace_never_passed(self):
        client = AsyncMock()
        client.query_stream = AsyncMock(return_value=[])
        engine = _make_engine(triples_client=client)

        await engine.execute_batch_triple_queries(
            ["e1"], limit_per_entity=10,
        )

        for c in client.query_stream.call_args_list:
            assert "workspace" not in c.kwargs


class TestDirectionTracking:

    @pytest.mark.asyncio
    async def test_from_s_direction(self):
        triple = _make_triple("ent1", "pred", "obj")
        client = AsyncMock()

        async def query_stream(s=None, p=None, o=None, **kwargs):
            if s is not None:
                return [triple]
            return []

        client.query_stream.side_effect = query_stream
        engine = _make_engine(triples_client=client)

        result = await engine.execute_batch_triple_queries(["ent1"], 10)

        from_s = [(t, d) for t, d in result if d == FROM_S]
        assert len(from_s) == 1
        assert from_s[0][0] is triple

    @pytest.mark.asyncio
    async def test_from_o_direction(self):
        triple = _make_triple("subj", "pred", "ent1")
        client = AsyncMock()

        async def query_stream(s=None, p=None, o=None, **kwargs):
            if o is not None:
                return [triple]
            return []

        client.query_stream.side_effect = query_stream
        engine = _make_engine(triples_client=client)

        result = await engine.execute_batch_triple_queries(["ent1"], 10)

        from_o = [(t, d) for t, d in result if d == FROM_O]
        assert len(from_o) == 1
        assert from_o[0][0] is triple

    @pytest.mark.asyncio
    async def test_from_p_direction(self):
        triple = _make_triple("subj", "ent1", "obj")
        client = AsyncMock()

        async def query_stream(s=None, p=None, o=None, **kwargs):
            if p is not None:
                return [triple]
            return []

        client.query_stream.side_effect = query_stream
        engine = _make_engine(triples_client=client)

        result = await engine.execute_batch_triple_queries(["ent1"], 10)

        from_p = [(t, d) for t, d in result if d == FROM_P]
        assert len(from_p) == 1
        assert from_p[0][0] is triple


class TestDirectionAwareRerankerText:

    @pytest.mark.asyncio
    async def test_from_s_uses_predicate_object(self):
        triple = _make_triple(
            "http://ex/entity-A", "http://ex/likes", "http://ex/entity-B",
        )
        labels = {
            "http://ex/entity-A": "Alice",
            "http://ex/likes": "likes",
            "http://ex/entity-B": "Bob",
        }
        engine, tc, rc = _make_direction_engine(
            reranker_results=[_reranker_result(0)], labels=labels,
        )

        async def query_stream(s=None, p=None, o=None, **kwargs):
            if s is not None:
                return [triple]
            return []

        tc.query_stream.side_effect = query_stream

        await engine.hop_and_filter(
            seed_entities=["http://ex/entity-A"], concepts=["likes"],
        )

        documents = rc.rerank.call_args.kwargs["documents"]
        assert len(documents) == 1
        assert documents[0]["text"] == "likes Bob"

    @pytest.mark.asyncio
    async def test_from_o_uses_subject_predicate(self):
        triple = _make_triple(
            "http://ex/entity-A", "http://ex/likes", "http://ex/entity-B",
        )
        labels = {
            "http://ex/entity-A": "Alice",
            "http://ex/likes": "likes",
            "http://ex/entity-B": "Bob",
        }
        engine, tc, rc = _make_direction_engine(
            reranker_results=[_reranker_result(0)], labels=labels,
        )

        async def query_stream(s=None, p=None, o=None, **kwargs):
            if o is not None:
                return [triple]
            return []

        tc.query_stream.side_effect = query_stream

        await engine.hop_and_filter(
            seed_entities=["http://ex/entity-B"], concepts=["likes"],
        )

        documents = rc.rerank.call_args.kwargs["documents"]
        assert len(documents) == 1
        assert documents[0]["text"] == "Alice likes"

    @pytest.mark.asyncio
    async def test_from_p_uses_subject_object(self):
        triple = _make_triple(
            "http://ex/entity-A", "http://ex/likes", "http://ex/entity-B",
        )
        labels = {
            "http://ex/entity-A": "Alice",
            "http://ex/likes": "likes",
            "http://ex/entity-B": "Bob",
        }
        engine, tc, rc = _make_direction_engine(
            reranker_results=[_reranker_result(0)], labels=labels,
        )

        async def query_stream(s=None, p=None, o=None, **kwargs):
            if p is not None:
                return [triple]
            return []

        tc.query_stream.side_effect = query_stream

        await engine.hop_and_filter(
            seed_entities=["http://ex/likes"], concepts=["entity"],
        )

        documents = rc.rerank.call_args.kwargs["documents"]
        assert len(documents) == 1
        assert documents[0]["text"] == "Alice Bob"

    @pytest.mark.asyncio
    async def test_mixed_directions_produce_different_text(self):
        triple_from_s = _make_triple(
            "http://ex/seed", "http://ex/rel", "http://ex/target",
        )
        triple_from_o = _make_triple(
            "http://ex/other", "http://ex/ref", "http://ex/seed",
        )
        labels = {
            "http://ex/seed": "Seed",
            "http://ex/rel": "relates to",
            "http://ex/target": "Target",
            "http://ex/other": "Other",
            "http://ex/ref": "references",
        }

        engine, tc, rc = _make_direction_engine(
            reranker_results=[_reranker_result(0), _reranker_result(1)],
            labels=labels,
        )

        async def query_stream(s=None, p=None, o=None, **kwargs):
            if s == "http://ex/seed":
                return [triple_from_s]
            if o == "http://ex/seed":
                return [triple_from_o]
            return []

        tc.query_stream.side_effect = query_stream

        await engine.hop_and_filter(
            seed_entities=["http://ex/seed"], concepts=["test"],
        )

        documents = rc.rerank.call_args.kwargs["documents"]
        texts = {d["text"] for d in documents}
        assert "relates to Target" in texts
        assert "Other references" in texts

    @pytest.mark.asyncio
    async def test_labels_applied_to_direction_text(self):
        triple = _make_triple(
            "http://ex/entity-A", "http://ex/likes", "http://ex/entity-B",
        )
        engine, tc, rc = _make_direction_engine(
            reranker_results=[_reranker_result(0)],
        )

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

        tc.query_stream.side_effect = query_stream
        tc.query.side_effect = label_query

        await engine.hop_and_filter(
            seed_entities=["http://ex/entity-A"], concepts=["friendship"],
        )

        documents = rc.rerank.call_args.kwargs["documents"]
        assert len(documents) == 1
        assert documents[0]["text"] == "likes Bob"

    @pytest.mark.asyncio
    async def test_no_duplicate_text_from_shared_object(self):
        triple_a = _make_triple(
            "http://ex/cpu-A", "http://ex/hasCategory", "http://ex/Processors",
        )
        triple_b = _make_triple(
            "http://ex/cpu-B", "http://ex/hasCategory", "http://ex/Processors",
        )
        labels = {
            "http://ex/cpu-A": "CPU Alpha",
            "http://ex/cpu-B": "CPU Beta",
            "http://ex/hasCategory": "has category",
            "http://ex/Processors": "Processors",
        }

        engine, tc, rc = _make_direction_engine(
            reranker_results=[_reranker_result(0), _reranker_result(1)],
            labels=labels,
        )

        async def query_stream(s=None, p=None, o=None, **kwargs):
            if o == "http://ex/Processors":
                return [triple_a, triple_b]
            return []

        tc.query_stream.side_effect = query_stream

        await engine.hop_and_filter(
            seed_entities=["http://ex/Processors"], concepts=["CPUs"],
        )

        documents = rc.rerank.call_args.kwargs["documents"]
        texts = [d["text"] for d in documents]
        assert len(texts) == 2
        assert texts[0] != texts[1]
        assert "CPU Alpha" in texts[0]
        assert "CPU Beta" in texts[1]


class TestMaybeLabel:

    @pytest.mark.asyncio
    async def test_cached_label_returned(self):
        engine = _make_engine(collection="test_collection")
        engine.label_cache.put("test_collection:entity1", "Entity One Label")

        result = await engine.maybe_label("entity1")

        assert result == "Entity One Label"

    @pytest.mark.asyncio
    async def test_label_lookup_from_triples(self):
        triples_client = AsyncMock()
        mock_triple = MagicMock()
        mock_triple.o = "Human Readable Label"
        triples_client.query.return_value = [mock_triple]

        engine = _make_engine(
            triples_client=triples_client, collection="test_collection",
        )

        result = await engine.maybe_label("http://example.com/entity")

        triples_client.query.assert_called_once_with(
            s="http://example.com/entity",
            p=LABEL, o=None, limit=1,
            collection="test_collection", g="",
        )
        assert result == "Human Readable Label"
        assert engine.label_cache.get(
            "test_collection:http://example.com/entity"
        ) == "Human Readable Label"

    @pytest.mark.asyncio
    async def test_no_label_falls_back_to_local_name(self):
        triples_client = AsyncMock()
        triples_client.query.return_value = []

        engine = _make_engine(
            triples_client=triples_client, collection="test_collection",
        )

        result = await engine.maybe_label("http://example.com/MyEntity")

        assert result == "MyEntity"
        assert engine.label_cache.get(
            "test_collection:http://example.com/MyEntity"
        ) == "MyEntity"

    @pytest.mark.asyncio
    async def test_workspace_never_passed(self):
        triples_client = AsyncMock()
        triples_client.query.return_value = [MagicMock(o="Label")]

        engine = _make_engine(
            triples_client=triples_client, collection="test_collection",
        )

        await engine.maybe_label("http://example.com/entity")

        for c in triples_client.query.call_args_list:
            assert "workspace" not in c.kwargs


class TestLanguageFiltering:

    def _make_triple(self, s_lang=None, o_lang=None,
                     s_is_iri=False, o_is_iri=False):
        triple = MagicMock()

        if s_is_iri:
            triple.s = MagicMock(spec=[])
        else:
            triple.s = MagicMock()
            triple.s.language = s_lang
            triple.s.value = "some value"

        if o_is_iri:
            triple.o = MagicMock(spec=[])
        else:
            triple.o = MagicMock()
            triple.o.language = o_lang
            triple.o.value = "some value"

        return triple

    def test_no_filter_passes_everything(self):
        engine = _make_engine(languages=[])
        assert engine._matches_language(self._make_triple(o_lang="de")) is True

    def test_matching_language_passes(self):
        engine = _make_engine(languages=["en"])
        assert engine._matches_language(self._make_triple(o_lang="en")) is True

    def test_non_matching_language_rejected(self):
        engine = _make_engine(languages=["en"])
        assert engine._matches_language(self._make_triple(o_lang="de")) is False

    def test_empty_string_matches_no_language_tag(self):
        engine = _make_engine(languages=[""])
        assert engine._matches_language(self._make_triple(o_lang=None)) is True

    def test_multiple_languages(self):
        engine = _make_engine(languages=["en", "fr"])
        assert engine._matches_language(self._make_triple(o_lang="en")) is True
        assert engine._matches_language(self._make_triple(o_lang="fr")) is True
        assert engine._matches_language(self._make_triple(o_lang="de")) is False

    def test_iri_only_triple_passes_through(self):
        engine = _make_engine(languages=["en"])
        triple = self._make_triple(s_is_iri=True, o_is_iri=True)
        assert engine._matches_language(triple) is True

    def test_mixed_iri_and_matching_literal(self):
        engine = _make_engine(languages=["en"])
        triple = self._make_triple(s_is_iri=True, o_lang="en")
        assert engine._matches_language(triple) is True

    def test_mixed_iri_and_non_matching_literal(self):
        engine = _make_engine(languages=["en"])
        triple = self._make_triple(s_is_iri=True, o_lang="de")
        assert engine._matches_language(triple) is False


class TestHopAndFilter:

    @pytest.mark.asyncio
    async def test_basic_functionality(self):
        triples_client = AsyncMock()
        reranker_client = AsyncMock()

        mock_triple = _make_triple("entity1", "predicate1", "object1")
        triples_client.query_stream.return_value = [mock_triple]
        triples_client.query.return_value = []

        reranker_client.rerank.return_value = [
            _reranker_result(0, score=0.95),
        ]

        engine = _make_engine(
            triples_client=triples_client,
            reranker_client=reranker_client,
            triple_limit=10, edge_limit=25,
        )

        edges = await engine.hop_and_filter(["entity1"], ["test concept"])

        assert len(edges) == 1
        assert edges[0]["s"] == "entity1"
        assert edges[0]["p"] == "predicate1"
        assert edges[0]["o"] == "object1"
        assert edges[0]["score"] == 0.95
        assert edges[0]["concept"] == "test concept"

        reranker_client.rerank.assert_called_once()
        assert reranker_client.rerank.call_args.kwargs["limit"] == 25

    @pytest.mark.asyncio
    async def test_empty_frontier_returns_empty(self):
        engine = _make_engine()

        edges = await engine.hop_and_filter([], ["concept"])

        assert edges == []

    @pytest.mark.asyncio
    async def test_schema_predicates_filtered(self):
        triples_client = AsyncMock()
        reranker_client = AsyncMock()

        label_triple = _make_triple(
            "entity1",
            "http://www.w3.org/2000/01/rdf-schema#label",
            "Entity One",
        )
        triples_client.query_stream.return_value = [label_triple]
        triples_client.query.return_value = []

        engine = _make_engine(
            triples_client=triples_client,
            reranker_client=reranker_client,
            triple_limit=10,
        )

        edges = await engine.hop_and_filter(["entity1"], ["concept"])

        assert edges == []
        reranker_client.rerank.assert_not_called()
