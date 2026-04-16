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
