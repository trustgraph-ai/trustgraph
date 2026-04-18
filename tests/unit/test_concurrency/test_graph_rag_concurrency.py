"""
Tests for Graph RAG concurrent query execution.

Covers: execute_batch_triple_queries concurrent task spawning,
exception handling in gather, and result aggregation.
"""

import asyncio

import pytest
from unittest.mock import MagicMock, AsyncMock

from trustgraph.retrieval.graph_rag.graph_rag import Query, LRUCacheWithTTL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_query(
    triples_client=None,
    entity_limit=50,
    triple_limit=30,
    max_subgraph_size=1000,
    max_path_length=2,
):
    """Create a Query object with mocked rag dependencies."""
    rag = MagicMock()
    rag.triples_client = triples_client or AsyncMock()
    rag.label_cache = LRUCacheWithTTL()

    query = Query(
        rag=rag,
        collection="test-collection",
        verbose=False,
        entity_limit=entity_limit,
        triple_limit=triple_limit,
        max_subgraph_size=max_subgraph_size,
        max_path_length=max_path_length,
    )
    return query


def _make_triple(s, p, o):
    """Create a simple mock triple."""
    t = MagicMock()
    t.s = s
    t.p = p
    t.o = o
    return t


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBatchTripleQueries:

    @pytest.mark.asyncio
    async def test_three_queries_per_entity(self):
        """Each entity should generate 3 concurrent queries (s, p, o positions)."""
        client = AsyncMock()
        client.query_stream = AsyncMock(return_value=[])
        query = _make_query(triples_client=client)

        entities = ["entity-1"]
        await query.execute_batch_triple_queries(entities, limit_per_entity=10)

        assert client.query_stream.call_count == 3

    @pytest.mark.asyncio
    async def test_multiple_entities_multiply_queries(self):
        """N entities should produce N*3 concurrent queries."""
        client = AsyncMock()
        client.query_stream = AsyncMock(return_value=[])
        query = _make_query(triples_client=client)

        entities = ["e1", "e2", "e3"]
        await query.execute_batch_triple_queries(entities, limit_per_entity=10)

        assert client.query_stream.call_count == 9  # 3 * 3

    @pytest.mark.asyncio
    async def test_queries_executed_concurrently(self):
        """All queries should run concurrently via asyncio.gather."""
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
        query = _make_query(triples_client=client)

        entities = ["e1", "e2", "e3"]
        await query.execute_batch_triple_queries(entities, limit_per_entity=5)

        # All 9 queries should have run concurrently
        assert max_concurrent == 9

    @pytest.mark.asyncio
    async def test_results_aggregated(self):
        """Results from all queries should be combined into a single list."""
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
        query = _make_query(triples_client=client)

        result = await query.execute_batch_triple_queries(
            ["e1"], limit_per_entity=10
        )

        # 3 queries, alternating results
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_exception_in_one_query_does_not_block_others(self):
        """If one query raises, other results are still collected."""
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
        query = _make_query(triples_client=client)

        result = await query.execute_batch_triple_queries(
            ["e1"], limit_per_entity=10
        )

        # 3 queries: 2 succeed, 1 fails → 2 triples
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_none_results_filtered(self):
        """None results from queries should be filtered out."""
        call_count = 0

        async def sometimes_none(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None
            return [_make_triple("a", "p", "b")]

        client = AsyncMock()
        client.query_stream = sometimes_none
        query = _make_query(triples_client=client)

        result = await query.execute_batch_triple_queries(
            ["e1"], limit_per_entity=10
        )

        # 3 queries: 1 returns None, 2 return triples
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_empty_entities_no_queries(self):
        """Empty entity list should produce no queries."""
        client = AsyncMock()
        client.query_stream = AsyncMock(return_value=[])
        query = _make_query(triples_client=client)

        result = await query.execute_batch_triple_queries([], limit_per_entity=10)

        assert result == []
        client.query_stream.assert_not_called()

    @pytest.mark.asyncio
    async def test_query_params_correct(self):
        """Each query should use correct s/p/o positions and params."""
        client = AsyncMock()
        client.query_stream = AsyncMock(return_value=[])
        query = _make_query(triples_client=client)

        entities = ["ent-1"]
        await query.execute_batch_triple_queries(entities, limit_per_entity=15)

        calls = client.query_stream.call_args_list
        assert len(calls) == 3

        # First call: s=entity, p=None, o=None
        assert calls[0].kwargs["s"] == "ent-1"
        assert calls[0].kwargs["p"] is None
        assert calls[0].kwargs["o"] is None
        assert calls[0].kwargs["limit"] == 15
        assert calls[0].kwargs["collection"] == "test-collection"
        assert calls[0].kwargs["batch_size"] == 20

        # Second call: s=None, p=entity, o=None
        assert calls[1].kwargs["s"] is None
        assert calls[1].kwargs["p"] == "ent-1"
        assert calls[1].kwargs["o"] is None

        # Third call: s=None, p=None, o=entity
        assert calls[2].kwargs["s"] is None
        assert calls[2].kwargs["p"] is None
        assert calls[2].kwargs["o"] == "ent-1"


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
        cache.put("c", 3)  # Should evict "a"
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_lru_order(self):
        cache = LRUCacheWithTTL(max_size=2, ttl=60)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")  # Access "a" — now "b" is LRU
        cache.put("c", 3)  # Should evict "b"
        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3

    def test_ttl_expiration(self):
        cache = LRUCacheWithTTL(max_size=10, ttl=0)  # TTL=0 means instant expiry
        cache.put("key", "value")
        # With TTL=0, any time check > 0 means expired
        import time
        time.sleep(0.01)
        assert cache.get("key") is None

    def test_update_existing_key(self):
        cache = LRUCacheWithTTL(max_size=10, ttl=60)
        cache.put("key", "v1")
        cache.put("key", "v2")
        assert cache.get("key") == "v2"
