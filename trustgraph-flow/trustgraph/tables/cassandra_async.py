"""
Async wrapper for cassandra-driver sessions.

The cassandra driver exposes a callback-based async API via
session.execute_async, returning a ResponseFuture that fires
on_result / on_error from the driver's own worker thread.
This module bridges that into an awaitable interface.

Usage:
    from ..tables.cassandra_async import async_execute

    rows = await async_execute(self.cassandra, stmt, (param1, param2))
    for row in rows:
        ...

Notes:
    - Rows are materialised into a list inside the driver callback
      thread before the future is resolved, so subsequent iteration
      in the caller never triggers a sync page-fetch on the asyncio
      loop.  This is safe for single-page results (the common case
      in this codebase); if a query needs pagination, handle it
      explicitly.
    - Callbacks fire on a driver worker thread; call_soon_threadsafe
      is used to hand the result back to the asyncio loop.
    - Errors from the driver are re-raised in the awaiting coroutine.
"""

import asyncio

from cassandra.query import SimpleStatement


async def async_execute(session, query, parameters=None):
    """Execute a CQL statement asynchronously.

    Args:
        session: cassandra.cluster.Session (self.cassandra)
        query: statement string or PreparedStatement
        parameters: tuple/list of bind params, or None

    Returns:
        A list of rows (materialised from the first result page).
    """

    loop = asyncio.get_running_loop()
    fut = loop.create_future()

    def on_result(rows):
        # Materialise on the driver thread so the loop thread
        # never touches a lazy iterator that might trigger
        # further sync I/O.
        try:
            materialised = list(rows) if rows is not None else []
        except Exception as e:
            loop.call_soon_threadsafe(
                _set_exception_if_pending, fut, e
            )
            return
        loop.call_soon_threadsafe(
            _set_result_if_pending, fut, materialised
        )

    def on_error(exc):
        loop.call_soon_threadsafe(
            _set_exception_if_pending, fut, exc
        )

    rf = session.execute_async(query, parameters)
    rf.add_callbacks(on_result, on_error)
    return await fut


def _set_result_if_pending(fut, result):
    if not fut.done():
        fut.set_result(result)


def _set_exception_if_pending(fut, exc):
    if not fut.done():
        fut.set_exception(exc)


async def async_execute_paged(session, query, parameters=None, fetch_size=5000):
    """Execute a CQL query with page-by-page iteration.

    Uses synchronous session.execute() inside run_in_executor so that
    the driver's ResultSet paging works correctly without materialising
    the entire result set in memory.

    Returns all pages as a list of lists.
    """
    loop = asyncio.get_running_loop()

    if isinstance(query, str):
        stmt = SimpleStatement(query, fetch_size=fetch_size)
    else:
        stmt = query
        stmt.fetch_size = fetch_size

    def _fetch_all_pages():
        pages = []
        result_set = session.execute(stmt, parameters)
        while True:
            pages.append(list(result_set.current_rows))
            if result_set.has_more_pages:
                result_set.fetch_next_page()
            else:
                break
        return pages

    return await loop.run_in_executor(
        None, _fetch_all_pages
    )


async def async_scan(
    session, query, parameters=None, row_filter=None,
    limit=None, fetch_size=5000,
):
    """Scan a CQL query page-by-page, applying a filter and limit.

    Only matching rows accumulate in memory.  Each page is discarded
    after processing, so peak memory is bounded by fetch_size plus
    the number of matching rows (capped by limit).

    Args:
        session: cassandra.cluster.Session
        query: CQL statement string
        parameters: bind params
        row_filter: callable(row) -> bool, or None to accept all
        limit: max results to return, or None for unlimited
        fetch_size: rows per Cassandra page fetch

    Returns:
        List of matching rows.
    """
    loop = asyncio.get_running_loop()

    if isinstance(query, str):
        stmt = SimpleStatement(query, fetch_size=fetch_size)
    else:
        stmt = query
        stmt.fetch_size = fetch_size

    def _scan():
        results = []
        result_set = session.execute(stmt, parameters)
        while True:
            for row in result_set.current_rows:
                if row_filter is None or row_filter(row):
                    results.append(row)
                    if limit and len(results) >= limit:
                        return results
            if result_set.has_more_pages:
                result_set.fetch_next_page()
            else:
                break
        return results

    return await loop.run_in_executor(None, _scan)
