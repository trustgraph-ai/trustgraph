"""Pagination regression tests for EntityCentricKnowledgeGraph.async_delete_collection

Issue #1066: async_delete_collection read the quad manifest with async_execute, which
materialises only the FIRST result page. Deleting a collection larger than fetch_size
therefore removed only that page while logging success and dropping the collection's
config entry, leaving the bulk of the data behind and unreachable through the API.

The harness below models both halves of the driver contract faithfully rather than
stubbing the helpers out, so the tests distinguish a paging read from a single-page one:

  session.execute(stmt, params)        -> a multi-page ResultSet   (what async_scan uses)
  session.execute_async(q, params)     -> first page only, via callbacks
                                          (what async_execute uses, mirroring the driver)

No production function is patched, so a reverted fix genuinely fails these tests.
"""

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def _row(s, d='', otype='u'):
    return SimpleNamespace(d=d, s=s, p='p' + s, o='o' + s, otype=otype, dtype='', lang='')


# Three pages, two quads each. A truncating read sees only the first two rows.
PAGES = [
    [_row('s1'), _row('s2')],
    [_row('s3'), _row('s4')],
    [_row('s5'), _row('s6')],
]
TOTAL_QUADS = sum(len(p) for p in PAGES)


class FakePagedResultSet:
    """Minimal stand-in for the driver's ResultSet paging contract."""

    def __init__(self, pages):
        self._pages = [list(page) for page in pages]
        self._index = 0

    @property
    def current_rows(self):
        return self._pages[self._index]

    @property
    def has_more_pages(self):
        return self._index < len(self._pages) - 1

    def fetch_next_page(self):
        if not self.has_more_pages:
            raise AssertionError("fetch_next_page() called with no further pages")
        self._index += 1

    def __iter__(self):
        # The sync path iterates the ResultSet, which transparently spans pages.
        for page in self._pages:
            for row in page:
                yield row


class FakeResponseFuture:
    """execute_async() result: materialises only the first page, like the driver."""

    def __init__(self, first_page):
        self._first_page = list(first_page)

    def add_callbacks(self, on_result, on_error):
        on_result(self._first_page)


class RecordingBatch:
    """Records (statement, params) instead of validating driver statement types."""

    instances = []

    def __init__(self, *args, **kwargs):
        self.added = []
        RecordingBatch.instances.append(self)

    def add(self, statement, parameters=None):
        self.added.append((statement, parameters))


def _session_serving(pages):
    session = MagicMock()
    # Each prepare() must yield a DISTINCT statement, otherwise every prepared
    # statement is the same MagicMock and the assertions cannot tell the
    # entity-partition deletes apart from the collection-row deletes.
    session.prepare.side_effect = lambda *a, **k: MagicMock(name='prepared')
    session.execute.return_value = FakePagedResultSet(pages)
    session.execute_async.side_effect = (
        lambda *a, **k: FakeResponseFuture(pages[0] if pages else [])
    )
    return session


@pytest.fixture
def make_kg():
    from trustgraph.direct.cassandra_kg import EntityCentricKnowledgeGraph

    def _build(pages):
        with patch('trustgraph.direct.cassandra_kg.Cluster') as cluster_cls:
            session = _session_serving(pages)
            cluster = MagicMock()
            cluster.connect.return_value = session
            cluster_cls.return_value = cluster
            graph = EntityCentricKnowledgeGraph(hosts=['localhost'], keyspace='ks')
            # Re-arm after schema creation consumed the result set.
            session.execute.return_value = FakePagedResultSet(pages)
            return graph, session

    return _build


def _row_deletes(graph):
    return [
        params
        for batch in RecordingBatch.instances
        for stmt, params in batch.added
        if stmt is graph.delete_collection_row_stmt
    ]


async def test_async_delete_collection_deletes_every_page(make_kg):
    """#1066: every page of the quad manifest must be deleted, not just the first."""
    graph, session = make_kg(PAGES)

    RecordingBatch.instances = []
    with patch('trustgraph.direct.cassandra_kg.BatchStatement', RecordingBatch):
        await graph.async_delete_collection('c1')

    deletes = _row_deletes(graph)
    assert len(deletes) == TOTAL_QUADS, (
        f"deleted {len(deletes)} of {TOTAL_QUADS} quads — rows beyond the first page "
        f"were left behind (issue #1066)"
    )
    assert {p[2] for p in deletes} == {f's{i}' for i in range(1, 7)}


async def test_async_delete_collection_drains_the_result_set(make_kg):
    """The scan must reach the final page, so no rows are silently left behind."""
    graph, session = make_kg(PAGES)
    RecordingBatch.instances = []
    with patch('trustgraph.direct.cassandra_kg.BatchStatement', RecordingBatch):
        await graph.async_delete_collection('c1')

    assert session.execute.return_value.has_more_pages is False, \
        "result set was not drained to the last page"


async def test_async_delete_collection_single_page_unchanged(make_kg):
    """A collection that fits in one page behaves exactly as before the fix."""
    graph, session = make_kg([PAGES[0]])
    RecordingBatch.instances = []
    with patch('trustgraph.direct.cassandra_kg.BatchStatement', RecordingBatch):
        await graph.async_delete_collection('c1')

    assert len(_row_deletes(graph)) == 2


def test_sync_delete_collection_spans_pages(make_kg):
    """The sync path was already correct; pinned so the two paths stay symmetric."""
    graph, session = make_kg(PAGES)
    RecordingBatch.instances = []
    with patch('trustgraph.direct.cassandra_kg.BatchStatement', RecordingBatch):
        graph.delete_collection('c1')

    assert len(_row_deletes(graph)) == TOTAL_QUADS
