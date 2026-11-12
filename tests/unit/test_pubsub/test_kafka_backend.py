"""
Unit tests for AsyncKafkaBackend (#944).
"""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from trustgraph.base.async_kafka_backend import (
    AsyncKafkaBackend,
    AsyncKafkaConsumer,
    AsyncKafkaMessage,
    LONG_RETENTION_MS,
    SHORT_RETENTION_MS,
)


class TestAsyncKafkaBackend(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.backend = AsyncKafkaBackend(bootstrap_servers="localhost:9092")

    def test_parse_topic_and_retention(self):
        name, cls, durable = self.backend._parse_topic("flow:tg:text-completion")
        assert name == "tg.flow.text-completion"
        assert cls == "flow"
        assert durable is True
        assert self.backend._retention_ms(cls) == LONG_RETENTION_MS

        name, cls, durable = self.backend._parse_topic("request:tg:config:ws1")
        assert name == "tg.request.config.ws1"
        assert cls == "request"
        assert durable is False
        assert self.backend._retention_ms(cls) == SHORT_RETENTION_MS

    @patch("trustgraph.base.async_kafka_backend.AIOKafkaAdminClient")
    async def test_topic_exists_checks_error_code(self, mock_admin_cls):
        admin = AsyncMock()
        mock_admin_cls.return_value = admin

        # error_code=3 (UnknownTopicOrPartitionError) in describe_topics payload
        admin.describe_topics.return_value = [
            {"error_code": 3, "topic": "tg.response.config", "partitions": []}
        ]
        assert await self.backend.topic_exists("response:tg:config") is False

        # error_code=0 means the topic exists
        admin.describe_topics.return_value = [
            {"error_code": 0, "topic": "tg.response.config", "partitions": [0]}
        ]
        assert await self.backend.topic_exists("response:tg:config") is True

    @patch("trustgraph.base.async_kafka_backend.AIOKafkaConsumer")
    async def test_create_consumer_ensures_topic_and_waits_for_assignment(
        self, mock_consumer_cls,
    ):
        self.backend.ensure_topic = AsyncMock()
        consumer_instance = AsyncMock()
        assignments = [set(), {("tg.request.config", 0)}]
        consumer_instance.assignment = MagicMock(
            side_effect=lambda: assignments.pop(0) if len(assignments) > 1 else assignments[0]
        )
        mock_consumer_cls.return_value = consumer_instance

        await self.backend.create_consumer(
            topic="request:tg:config",
            subscription="config-svc",
            schema=dict,
        )

        self.backend.ensure_topic.assert_awaited_once_with("request:tg:config")
        _, kwargs = mock_consumer_cls.call_args
        assert kwargs["group_id"] == "config-svc"
        assert kwargs["auto_offset_reset"] == "earliest"
        consumer_instance.start.assert_awaited_once()

    @patch("trustgraph.base.async_kafka_backend.OffsetAndMetadata")
    @patch("trustgraph.base.async_kafka_backend.TopicPartition")
    async def test_acknowledge_and_negative_acknowledge_offsets(
        self, mock_tp, mock_om,
    ):
        mock_tp.side_effect = lambda t, p: (t, p)
        mock_om.side_effect = lambda o, m: (o, m)

        raw_consumer = MagicMock()
        raw_consumer.commit = AsyncMock()
        raw_consumer.seek = MagicMock()

        consumer = AsyncKafkaConsumer(raw_consumer, dict)
        raw_msg = SimpleNamespace(
            topic="tg.flow.input",
            partition=0,
            offset=41,
            value=b"{}",
            headers=[],
        )
        wrapped = AsyncKafkaMessage(raw_msg, dict)

        await consumer.acknowledge(wrapped)
        raw_consumer.commit.assert_awaited_once_with(
            {("tg.flow.input", 0): (42, "")}
        )

        await consumer.negative_acknowledge(wrapped)
        raw_consumer.seek.assert_called_once_with(("tg.flow.input", 0), 41)
