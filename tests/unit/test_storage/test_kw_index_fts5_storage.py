"""
Unit tests for trustgraph.storage.kw_index.fts5.service — the SQLite FTS5
keyword index. Covers the MATCH-expression sanitizer (raw user text is not
valid FTS5 syntax), exact-term retrieval for the motivating cases (dotted
clause numbers, error codes, hyphenated identifiers), chunk re-ingestion
replacing rather than duplicating, (workspace, collection) scoping, and
collection deletion.
"""

import tempfile
from pathlib import Path

import pytest
from unittest.mock import AsyncMock
from unittest import IsolatedAsyncioTestCase

from trustgraph.schema import Chunk, Metadata, KeywordIndexRequest
from trustgraph.storage.kw_index.fts5.service import (
    Processor, to_match_query, _table,
)


class TestMatchQuerySanitizer:

    def test_plain_words_are_quoted_and_or_joined(self):
        assert to_match_query("return policy") == '"return" OR "policy"'

    def test_dotted_and_hyphenated_terms_survive(self):
        # Raw "7.3.2" is an FTS5 syntax error; "AURA-7" parses "-" as a
        # column filter. Quoting neutralizes both.
        assert to_match_query("clause 7.3.2 AURA-7") == (
            '"clause" OR "7.3.2" OR "AURA-7"'
        )

    def test_embedded_quotes_are_escaped(self):
        assert to_match_query('say "hello"') == '"say" OR """hello"""'

    def test_empty_and_quote_only_queries_yield_none(self):
        assert to_match_query("") is None
        assert to_match_query("   ") is None
        assert to_match_query('"') is None


def make_processor(index_path):
    # A real file, not :memory: — the service holds separate write and read
    # connections, which only share a database through the filesystem.
    processor = Processor(
        taskgroup=AsyncMock(),
        id="test-kw-index",
        index_path=index_path,
    )
    # Config-pushed collection state isn't wired in unit tests
    processor.collection_exists = lambda workspace, collection: True
    return processor


def chunk(chunk_id, text, collection="default"):
    return Chunk(
        metadata=Metadata(id="doc1", collection=collection),
        chunk=text.encode("utf-8"),
        document_id=chunk_id,
    )


CHUNKS = [
    ("c1", "Clause 7.3.2 states that indemnification obligations survive."),
    ("c2", "Clause 7.3.1 covers limitation of liability."),
    ("c3", "Error E4032 occurs when the connection pool is exhausted."),
]


class TestFts5KeywordIndex(IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.processor = make_processor(str(Path(self._tmp.name) / "kw.db"))
        for chunk_id, text in CHUNKS:
            await self.processor.index_chunk("ws", chunk("ws-" + chunk_id, text))

    async def asyncTearDown(self):
        self.processor.db.close()
        self.processor.read_db.close()
        self._tmp.cleanup()

    async def query(self, text, collection="default", limit=0):
        return await self.processor.query_keyword_index(
            "ws", KeywordIndexRequest(
                query=text, limit=limit, collection=collection,
            ),
        )

    async def test_exact_dotted_term_matches_only_its_clause(self):
        matches = await self.query("7.3.2")
        assert [m.chunk_id for m in matches] == ["ws-c1"]

    async def test_error_code_matches(self):
        matches = await self.query("E4032")
        assert [m.chunk_id for m in matches] == ["ws-c3"]

    async def test_scores_are_higher_is_better(self):
        matches = await self.query("clause indemnification")
        assert matches[0].chunk_id == "ws-c1"
        assert all(m.score > 0 for m in matches)
        # c1 matches both terms so it must outrank c2
        by_id = {m.chunk_id: m.score for m in matches}
        assert by_id["ws-c1"] > by_id["ws-c2"]

    async def test_reingesting_a_chunk_replaces_it(self):
        await self.processor.index_chunk(
            "ws", chunk("ws-c1", "Completely different content now.")
        )
        assert await self.query("indemnification 7.3.2") == []
        matches = await self.query("completely different")
        assert [m.chunk_id for m in matches] == ["ws-c1"]

    async def test_collections_are_isolated(self):
        await self.processor.index_chunk(
            "ws", chunk("other-c1", "indemnification text", collection="other")
        )
        default_ids = [m.chunk_id for m in await self.query("indemnification")]
        other_ids = [
            m.chunk_id
            for m in await self.query("indemnification", collection="other")
        ]
        assert "other-c1" not in default_ids
        assert other_ids == ["other-c1"]

    async def test_workspaces_are_isolated(self):
        matches = await self.processor.query_keyword_index(
            "someone-else", KeywordIndexRequest(
                query="indemnification", collection="default",
            ),
        )
        assert matches == []

    async def test_unindexed_collection_returns_empty_not_error(self):
        assert await self.query("anything", collection="never-written") == []

    async def test_hostile_query_text_is_inert(self):
        # FTS5 operators and SQL fragments arrive as quoted phrases
        assert await self.query('body: DROP TABLE OR NOT NEAR(') == []

    async def test_limit_is_applied(self):
        matches = await self.query("clause", limit=1)
        assert len(matches) == 1

    async def test_delete_collection_drops_the_index(self):
        await self.processor.delete_collection("ws", "default")
        assert await self.query("clause") == []

    async def test_dropped_message_when_collection_missing(self):
        self.processor.collection_exists = lambda w, c: False
        await self.processor.index_chunk(
            "ws", chunk("ws-c9", "should be dropped")
        )
        self.processor.collection_exists = lambda w, c: True
        assert await self.query("dropped") == []
