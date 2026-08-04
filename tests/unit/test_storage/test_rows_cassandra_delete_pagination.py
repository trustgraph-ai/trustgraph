"""Pagination regression tests for the Cassandra row-storage delete paths.

Same defect class as issue #1066, found while auditing the other `async_execute` callers
as that issue suggests. `delete_collection` and `delete_collection_schema` discover the
partitions to delete with `async_execute`, which materialises only the FIRST result page.
Both then delete the `row_partitions` manifest rows for the collection — so a truncated
discovery does not merely leave rows behind, it removes the index that would let anything
find them again.

Method-binding onto a MagicMock follows the existing style in
tests/unit/test_storage/test_rows_cassandra_storage.py, which avoids standing up the whole
flow-processor framework. No production function is patched: the fake session models both
halves of the driver contract, so a reverted fix genuinely fails these tests.
"""

import asyncio
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from trustgraph.storage.rows.cassandra.write import Processor


def _partition(i):
    return SimpleNamespace(schema_name=f'schema{i}', index_name=f'index{i}')


# Three pages of partitions; a truncating discovery sees only the first two.
PAGES = [
    [_partition(1), _partition(2)],
    [_partition(3), _partition(4)],
    [_partition(5), _partition(6)],
]
TOTAL_PARTITIONS = sum(len(p) for p in PAGES)


class FakePagedResultSet:
    def __init__(self, pages):
        self._pages = [list(p) for p in pages]
        self._index = 0

    @property
    def current_rows(self):
        return self._pages[self._index]

    @property
    def has_more_pages(self):
        return self._index < len(self._pages) - 1

    def fetch_next_page(self):
        if not self.has_more_pages:
            raise AssertionError("fetch_next_page() with no further pages")
        self._index += 1

    def __iter__(self):
        for page in self._pages:
            for row in page:
                yield row


class FakeResponseFuture:
    """execute_async(): materialises only the first page, like the driver."""

    def __init__(self, first_page):
        self._first_page = list(first_page)

    def add_callbacks(self, on_result, on_error):
        on_result(self._first_page)


def _processor(pages):
    """A MagicMock processor with the real delete methods bound onto it."""
    session = MagicMock()
    session.execute.return_value = FakePagedResultSet(pages)
    session.execute_async.side_effect = (
        lambda *a, **k: FakeResponseFuture(pages[0] if pages else [])
    )

    proc = MagicMock()
    proc.session = session
    proc.known_keyspaces = {'ws'}          # skip the keyspace-existence probe
    proc._setup_lock = asyncio.Lock()
    proc.connect_cassandra = lambda: None
    proc.sanitize_name = Processor.sanitize_name.__get__(proc, Processor)
    proc.delete_collection = Processor.delete_collection.__get__(proc, Processor)
    proc.delete_collection_schema = (
        Processor.delete_collection_schema.__get__(proc, Processor)
    )
    return proc, session


def _deleted_index_names(session):
    """index_name values passed to the per-partition row deletes."""
    names = []
    for call in session.execute_async.call_args_list:
        args = call.args
        if len(args) >= 2 and isinstance(args[1], (tuple, list)):
            params = args[1]
            if len(params) == 3:
                names.append(params[2])
    return names


async def test_delete_collection_deletes_partitions_from_every_page():
    """#1066 class: all discovered partitions must be deleted, not just the first page."""
    proc, session = _processor(PAGES)

    await proc.delete_collection('ws', 'c1')

    deleted = _deleted_index_names(session)
    assert len(deleted) == TOTAL_PARTITIONS, (
        f"deleted {len(deleted)} of {TOTAL_PARTITIONS} partitions — partitions beyond "
        f"the first page were left behind, and the row_partitions manifest is removed "
        f"afterwards, so they become unreachable"
    )
    assert set(deleted) == {f'index{i}' for i in range(1, 7)}


async def test_delete_collection_drains_the_result_set():
    proc, session = _processor(PAGES)
    await proc.delete_collection('ws', 'c1')
    assert session.execute.return_value.has_more_pages is False, \
        "partition discovery did not reach the last page"


async def test_delete_collection_single_page_unchanged():
    """A collection whose partitions fit in one page behaves as before."""
    proc, session = _processor([PAGES[0]])
    await proc.delete_collection('ws', 'c1')
    assert len(_deleted_index_names(session)) == 2


async def test_delete_collection_schema_deletes_partitions_from_every_page():
    """Same defect in the per-schema delete path."""
    proc, session = _processor(PAGES)

    await proc.delete_collection_schema('ws', 'c1', 'schema1')

    deleted = _deleted_index_names(session)
    assert len(deleted) == TOTAL_PARTITIONS, (
        f"deleted {len(deleted)} of {TOTAL_PARTITIONS} partitions in "
        f"delete_collection_schema"
    )


async def test_delete_collection_schema_drains_the_result_set():
    proc, session = _processor(PAGES)
    await proc.delete_collection_schema('ws', 'c1', 'schema1')
    assert session.execute.return_value.has_more_pages is False
