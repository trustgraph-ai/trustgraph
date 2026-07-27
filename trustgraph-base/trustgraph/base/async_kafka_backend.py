"""
Async Kafka backend implementation.

Uses aiokafka for fully async Kafka operations. Each logical topic
maps to a Kafka topic, matching the sync Kafka backend's topology:

    class:topicspace:topic  →  topicspace.class.topic

Producers publish to the topic directly.
Consumers use consumer groups for competing-consumer semantics:

  - flow / request: named consumer group (competing consumers)
  - response / notify: unique consumer group per instance, filtering
    messages by correlation ID (all subscribers see all messages)
"""

import asyncio
import json
import logging
import uuid
from typing import Any

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import TopicAlreadyExistsError, UnknownTopicOrPartitionError

from .async_backend import AsyncPubSubBackend, AsyncBackendProducer
from .async_backend import AsyncBackendConsumer, Message
from .serialization import dataclass_to_dict, dict_to_dataclass

logger = logging.getLogger(__name__)

LONG_RETENTION_MS = 7 * 24 * 60 * 60 * 1000   # 7 days
SHORT_RETENTION_MS = 300 * 1000                 # 5 minutes


class AsyncKafkaMessage:
    """Wrapper for aiokafka messages to match Message protocol."""

    def __init__(self, msg, schema_cls):
        self._msg = msg
        self._schema_cls = schema_cls
        self._value = None

    def value(self) -> Any:
        if self._value is None:
            data_dict = json.loads(self._msg.value.decode('utf-8'))
            self._value = dict_to_dataclass(data_dict, self._schema_cls)
        return self._value

    def properties(self) -> dict:
        headers = self._msg.headers or []
        return {
            k: v.decode('utf-8') if isinstance(v, bytes) else v
            for k, v in headers
        }


class AsyncKafkaProducer:
    """Async Kafka producer using aiokafka."""

    def __init__(self, producer, topic_name):
        self._producer = producer
        self._topic_name = topic_name

    async def send(self, message: Any, properties: dict = {}) -> None:
        data_dict = dataclass_to_dict(message)
        json_data = json.dumps(data_dict).encode('utf-8')

        headers = [
            (k, str(v).encode('utf-8'))
            for k, v in properties.items()
        ] if properties else None

        await self._producer.send_and_wait(
            self._topic_name,
            value=json_data,
            headers=headers,
        )

    async def close(self) -> None:
        try:
            await self._producer.stop()
        except BaseException:
            pass


class AsyncKafkaConsumer:
    """Async Kafka consumer using aiokafka."""

    def __init__(self, consumer, schema_cls):
        self._consumer = consumer
        self._schema_cls = schema_cls

    async def receive(self) -> Message:
        msg = await self._consumer.__anext__()
        return AsyncKafkaMessage(msg, self._schema_cls)

    async def acknowledge(self, message: Message) -> None:
        if isinstance(message, AsyncKafkaMessage):
            await self._consumer.commit()

    async def negative_acknowledge(self, message: Message) -> None:
        pass

    async def close(self) -> None:
        try:
            await self._consumer.stop()
        except BaseException:
            pass


class AsyncKafkaBackend:
    """Async Kafka pub/sub backend using aiokafka.

    Fully async — zero OS threads for receiving, sending, and
    consumer/producer lifecycle.
    """

    def __init__(
        self, bootstrap_servers='localhost:9092',
        security_protocol='PLAINTEXT',
        sasl_mechanism=None,
        sasl_username=None,
        sasl_password=None,
    ):
        self._bootstrap_servers = bootstrap_servers
        self._security_protocol = security_protocol
        self._sasl_mechanism = sasl_mechanism
        self._sasl_username = sasl_username
        self._sasl_password = sasl_password

        self.max_consumer_concurrency = 1

        logger.info(
            f"Async Kafka backend: {bootstrap_servers} "
            f"protocol={security_protocol}"
        )

    def _client_kwargs(self):
        kwargs = {
            'bootstrap_servers': self._bootstrap_servers,
            'security_protocol': self._security_protocol,
        }
        if self._sasl_mechanism:
            kwargs['sasl_mechanism'] = self._sasl_mechanism
        if self._sasl_username:
            kwargs['sasl_plain_username'] = self._sasl_username
        if self._sasl_password:
            kwargs['sasl_plain_password'] = self._sasl_password
        return kwargs

    def _parse_topic(self, topic_id: str) -> tuple[str, str, bool]:
        """Parse topic identifier into Kafka topic name, class, durability.

        Format: class:topicspace:topic
        Returns: (topic_name, class, durable)
        """
        if ':' not in topic_id:
            return f'tg.flow.{topic_id}', 'flow', True

        parts = topic_id.split(':', 2)
        if len(parts) != 3:
            raise ValueError(
                f"Invalid topic format: {topic_id}, "
                f"expected class:topicspace:topic"
            )

        cls, topicspace, topic = parts

        if cls == 'flow':
            durable = True
        elif cls in ('request', 'response', 'notify'):
            durable = False
        else:
            raise ValueError(
                f"Invalid topic class: {cls}, "
                f"expected flow, request, response, or notify"
            )

        topic_name = f"{topicspace}.{cls}.{topic}".replace(':', '.')

        return topic_name, cls, durable

    def _retention_ms(self, cls):
        if cls == 'flow':
            return LONG_RETENTION_MS
        return SHORT_RETENTION_MS

    async def create_producer(
        self, topic: str, schema: type, **options,
    ) -> AsyncBackendProducer:
        topic_name, cls, durable = self._parse_topic(topic)

        producer = AIOKafkaProducer(
            **self._client_kwargs(),
            acks='all' if durable else 1,
            max_request_size=10485760,
        )
        await producer.start()

        logger.debug(f"Created async producer: topic={topic_name}")

        return AsyncKafkaProducer(producer, topic_name)

    async def create_consumer(
        self, topic: str, subscription: str, schema: type,
        initial_position: str = 'latest', **options,
    ) -> AsyncBackendConsumer:
        topic_name, cls, durable = self._parse_topic(topic)

        if cls in ('response', 'notify'):
            group_id = f"{subscription}-{uuid.uuid4()}"
            auto_offset_reset = 'earliest'
        else:
            group_id = subscription
            auto_offset_reset = (
                'earliest' if initial_position == 'earliest'
                else 'latest'
            )

        consumer = AIOKafkaConsumer(
            topic_name,
            **self._client_kwargs(),
            group_id=group_id,
            auto_offset_reset=auto_offset_reset,
            enable_auto_commit=False,
            max_partition_fetch_bytes=10485760,
            session_timeout_ms=6000,
            heartbeat_interval_ms=1000,
        )
        await consumer.start()

        logger.debug(
            f"Created async consumer: topic={topic_name}, "
            f"group={group_id}, cls={cls}"
        )

        return AsyncKafkaConsumer(consumer, schema)

    async def create_topic(self, topic: str) -> None:
        topic_name, cls, durable = self._parse_topic(topic)
        retention_ms = self._retention_ms(cls)

        admin = AIOKafkaAdminClient(**self._client_kwargs())
        try:
            await admin.start()
            new_topic = NewTopic(
                topic_name,
                num_partitions=1,
                replication_factor=1,
                topic_configs={
                    'retention.ms': str(retention_ms),
                },
            )
            await admin.create_topics([new_topic])
            logger.info(f"Created topic: {topic_name}")
        except TopicAlreadyExistsError:
            logger.debug(f"Topic already exists: {topic_name}")
        finally:
            await admin.close()

    async def delete_topic(self, topic: str) -> None:
        topic_name, cls, durable = self._parse_topic(topic)

        admin = AIOKafkaAdminClient(**self._client_kwargs())
        try:
            await admin.start()
            await admin.delete_topics([topic_name])
            logger.info(f"Deleted topic: {topic_name}")
        except UnknownTopicOrPartitionError:
            logger.debug(f"Topic not found: {topic_name}")
        except BaseException as e:
            logger.debug(f"Topic delete for {topic_name}: {e}")
        finally:
            try:
                await admin.close()
            except BaseException:
                pass

    async def topic_exists(self, topic: str) -> bool:
        topic_name, cls, durable = self._parse_topic(topic)

        admin = AIOKafkaAdminClient(**self._client_kwargs())
        try:
            await admin.start()
            metadata = await admin.describe_topics([topic_name])
            return len(metadata) > 0
        except UnknownTopicOrPartitionError:
            return False
        except BaseException:
            return False
        finally:
            try:
                await admin.close()
            except BaseException:
                pass

    async def ensure_topic(self, topic: str) -> None:
        if not await self.topic_exists(topic):
            await self.create_topic(topic)

    async def close(self) -> None:
        logger.info("Async Kafka backend closed")
