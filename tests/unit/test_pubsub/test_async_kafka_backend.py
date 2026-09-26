"""Tests for Kafka consumer startup readiness."""

import asyncio

import pytest

from trustgraph.base.async_kafka_backend import (
    AsyncKafkaBackend,
    _wait_for_consumer_assignment,
)


class FakeConsumer:
    def __init__(self, assignments=()):
        self.assignments = list(assignments)
        self.positioned = []
        self.started = False
        self.stopped = False

    async def start(self):
        self.started = True

    async def stop(self):
        self.stopped = True

    def assignment(self):
        if not self.assignments:
            return set()
        return self.assignments.pop(0)

    async def position(self, partition):
        self.positioned.append(partition)
        return 0


@pytest.mark.asyncio
async def test_wait_for_consumer_assignment_initializes_partition_positions(
    monkeypatch,
):
    consumer = FakeConsumer([set(), {"partition-0", "partition-1"}])

    async def no_delay(_delay):
        return None

    monkeypatch.setattr(asyncio, "sleep", no_delay)

    await _wait_for_consumer_assignment(consumer)

    assert set(consumer.positioned) == {"partition-0", "partition-1"}


@pytest.mark.asyncio
async def test_create_consumer_stops_half_started_consumer_on_assignment_timeout(
    monkeypatch,
):
    consumer = FakeConsumer()

    monkeypatch.setattr(
        "trustgraph.base.async_kafka_backend.AIOKafkaConsumer",
        lambda *args, **kwargs: consumer,
    )

    async def time_out(_consumer):
        raise asyncio.TimeoutError

    monkeypatch.setattr(
        "trustgraph.base.async_kafka_backend._wait_for_consumer_assignment",
        time_out,
    )

    backend = AsyncKafkaBackend()

    with pytest.raises(
        RuntimeError,
        match="Timed out waiting for Kafka partition assignment",
    ):
        await backend.create_consumer(
            "flow:test:requests",
            "workers",
            dict,
        )

    assert consumer.started
    assert consumer.stopped
