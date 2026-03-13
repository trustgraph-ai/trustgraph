"""
Tests for MessageDispatcher semaphore-based concurrency enforcement.

Verifies that the dispatcher limits concurrent message processing to
max_workers via asyncio.Semaphore.
"""

import asyncio

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from trustgraph.rev_gateway.dispatcher import MessageDispatcher


class TestSemaphoreEnforcement:

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrent_processing(self):
        """Only max_workers messages should be processed concurrently."""
        max_workers = 2
        dispatcher = MessageDispatcher(max_workers=max_workers)

        concurrent_count = 0
        max_concurrent = 0
        processing_event = asyncio.Event()

        async def slow_process(message):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.05)
            concurrent_count -= 1
            return {"id": message.get("id"), "response": {"ok": True}}

        dispatcher._process_message = slow_process

        # Launch more tasks than max_workers
        messages = [
            {"id": f"msg-{i}", "service": "test", "request": {}}
            for i in range(5)
        ]

        tasks = [
            asyncio.create_task(dispatcher.handle_message(m))
            for m in messages
        ]

        await asyncio.gather(*tasks)

        # At no point should more than max_workers have been active
        assert max_concurrent <= max_workers

    @pytest.mark.asyncio
    async def test_semaphore_value_matches_max_workers(self):
        for n in [1, 5, 20]:
            dispatcher = MessageDispatcher(max_workers=n)
            assert dispatcher.semaphore._value == n

    @pytest.mark.asyncio
    async def test_active_tasks_tracked(self):
        """Active tasks should be added/removed during processing."""
        dispatcher = MessageDispatcher(max_workers=5)

        task_was_tracked = False

        original_process = dispatcher._process_message

        async def tracking_process(message):
            nonlocal task_was_tracked
            # During processing, our task should be in active_tasks
            if len(dispatcher.active_tasks) > 0:
                task_was_tracked = True
            return {"id": message.get("id"), "response": {"ok": True}}

        dispatcher._process_message = tracking_process

        await dispatcher.handle_message(
            {"id": "test", "service": "test", "request": {}}
        )

        assert task_was_tracked
        # After completion, task should be discarded
        assert len(dispatcher.active_tasks) == 0

    @pytest.mark.asyncio
    async def test_semaphore_released_on_error(self):
        """Semaphore should be released even if processing raises."""
        dispatcher = MessageDispatcher(max_workers=2)

        async def failing_process(message):
            raise RuntimeError("process failed")

        dispatcher._process_message = failing_process

        # Should not deadlock — semaphore must be released on error
        with pytest.raises(RuntimeError):
            await dispatcher.handle_message(
                {"id": "test", "service": "test", "request": {}}
            )

        # Semaphore should be back at max
        assert dispatcher.semaphore._value == 2

    @pytest.mark.asyncio
    async def test_single_worker_serializes_processing(self):
        """With max_workers=1, messages are processed one at a time."""
        dispatcher = MessageDispatcher(max_workers=1)

        order = []

        async def ordered_process(message):
            msg_id = message["id"]
            order.append(f"start-{msg_id}")
            await asyncio.sleep(0.02)
            order.append(f"end-{msg_id}")
            return {"id": msg_id, "response": {"ok": True}}

        dispatcher._process_message = ordered_process

        messages = [{"id": str(i), "service": "t", "request": {}} for i in range(3)]
        tasks = [asyncio.create_task(dispatcher.handle_message(m)) for m in messages]
        await asyncio.gather(*tasks)

        # With semaphore=1, each message should complete before next starts
        # Check that no two "start" entries appear without an intervening "end"
        active = 0
        max_active = 0
        for event in order:
            if event.startswith("start"):
                active += 1
                max_active = max(max_active, active)
            elif event.startswith("end"):
                active -= 1

        assert max_active == 1
