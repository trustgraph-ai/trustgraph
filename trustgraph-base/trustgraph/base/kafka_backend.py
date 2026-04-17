"""
Kafka backend implementation for pub/sub abstraction.

Each logical topic maps to a Kafka topic.  The topic name encodes
the full identity:

    class:topicspace:topic  ->  topicspace.class.topic

Producers publish to the topic directly.
Consumers use consumer groups for competing-consumer semantics:

  - flow / request: named consumer group (competing consumers)
  - response / notify: unique consumer group per instance, filtering
    messages by correlation ID (all subscribers see all messages)

The flow service manages topic lifecycle via AdminClient.

Architecture:
  Producer  -->  [Kafka topic]  -->  Consumer Group A  --> Consumer
                                -->  Consumer Group A  --> Consumer
                                -->  Consumer Group B  --> Consumer (response)
"""

import asyncio
import json
import logging
import uuid
from typing import Any

from confluent_kafka import (
    Producer as KafkaProducer,
    Consumer as KafkaConsumer,
    TopicPartition,
    KafkaError,
    KafkaException,
)
from confluent_kafka.admin import AdminClient, NewTopic

from .backend import PubSubBackend, BackendProducer, BackendConsumer, Message
from .serialization import dataclass_to_dict, dict_to_dataclass

logger = logging.getLogger(__name__)

# Retention defaults (milliseconds)
LONG_RETENTION_MS = 7 * 24 * 60 * 60 * 1000   # 7 days
SHORT_RETENTION_MS = 300 * 1000                 # 5 minutes


class KafkaMessage:
    """Wrapper for Kafka messages to match Message protocol."""

    def __init__(self, msg, schema_cls):
        self._msg = msg
        self._schema_cls = schema_cls
        self._value = None

    def value(self) -> Any:
        """Deserialize and return the message value as a dataclass."""
        if self._value is None:
            data_dict = json.loads(self._msg.value().decode('utf-8'))
            self._value = dict_to_dataclass(data_dict, self._schema_cls)
        return self._value

    def properties(self) -> dict:
        """Return message properties from Kafka headers."""
        headers = self._msg.headers() or []
        return {
            k: v.decode('utf-8') if isinstance(v, bytes) else v
            for k, v in headers
        }


class KafkaBackendProducer:
    """Publishes messages to a Kafka topic.

    confluent-kafka Producer is thread-safe, so a single instance
    can be shared across threads.
    """

    def __init__(self, bootstrap_servers, topic_name, durable):
        self._topic_name = topic_name
        self._durable = durable
        self._producer = KafkaProducer({
            'bootstrap.servers': bootstrap_servers,
            'acks': 'all' if durable else '1',
        })

    def send(self, message: Any, properties: dict = {}) -> None:
        data_dict = dataclass_to_dict(message)
        json_data = json.dumps(data_dict).encode('utf-8')

        headers = [
            (k, str(v).encode('utf-8'))
            for k, v in properties.items()
        ] if properties else None

        self._producer.produce(
            topic=self._topic_name,
            value=json_data,
            headers=headers,
        )
        self._producer.flush()

    def flush(self) -> None:
        self._producer.flush()

    def close(self) -> None:
        self._producer.flush()


class KafkaBackendConsumer:
    """Consumes from a Kafka topic using a consumer group.

    Uses confluent-kafka Consumer.poll() for message delivery.
    Not thread-safe — each instance must be used from a single thread,
    which matches the ThreadPoolExecutor pattern in consumer.py.
    """

    def __init__(self, bootstrap_servers, topic_name, group_id,
                 schema_cls, auto_offset_reset='latest'):
        self._bootstrap_servers = bootstrap_servers
        self._topic_name = topic_name
        self._group_id = group_id
        self._schema_cls = schema_cls
        self._auto_offset_reset = auto_offset_reset
        self._consumer = None

    def _connect(self):
        self._consumer = KafkaConsumer({
            'bootstrap.servers': self._bootstrap_servers,
            'group.id': self._group_id,
            'auto.offset.reset': self._auto_offset_reset,
            'enable.auto.commit': False,
        })
        self._consumer.subscribe([self._topic_name])
        logger.info(
            f"Kafka consumer connected: topic={self._topic_name}, "
            f"group={self._group_id}"
        )

    def _is_alive(self):
        return self._consumer is not None

    def ensure_connected(self) -> None:
        """Eagerly connect and subscribe.

        For response/notify consumers this must be called before the
        corresponding request is published, so that the consumer is
        assigned a partition and will see the response message.
        """
        if not self._is_alive():
            self._connect()

            # Force a partition assignment by polling briefly.
            # Without this, the consumer may not be assigned partitions
            # until the first real poll(), creating a race where the
            # request is sent before assignment completes.
            self._consumer.poll(timeout=1.0)

    def receive(self, timeout_millis: int = 2000) -> Message:
        """Receive a message. Raises TimeoutError if none available."""
        if not self._is_alive():
            self._connect()

        timeout_seconds = timeout_millis / 1000.0
        msg = self._consumer.poll(timeout=timeout_seconds)

        if msg is None:
            raise TimeoutError("No message received within timeout")

        if msg.error():
            error = msg.error()
            if error.code() == KafkaError._PARTITION_EOF:
                raise TimeoutError("End of partition reached")
            raise KafkaException(error)

        return KafkaMessage(msg, self._schema_cls)

    def acknowledge(self, message: Message) -> None:
        """Commit the message's offset (next offset to read)."""
        if isinstance(message, KafkaMessage) and message._msg:
            tp = TopicPartition(
                message._msg.topic(),
                message._msg.partition(),
                message._msg.offset() + 1,
            )
            self._consumer.commit(offsets=[tp], asynchronous=False)

    def negative_acknowledge(self, message: Message) -> None:
        """Seek back to the message's offset for redelivery."""
        if isinstance(message, KafkaMessage) and message._msg:
            tp = TopicPartition(
                message._msg.topic(),
                message._msg.partition(),
                message._msg.offset(),
            )
            self._consumer.seek(tp)

    def unsubscribe(self) -> None:
        if self._consumer:
            try:
                self._consumer.unsubscribe()
            except Exception:
                pass

    def close(self) -> None:
        if self._consumer:
            try:
                self._consumer.close()
            except Exception:
                pass
            self._consumer = None


class KafkaBackend:
    """Kafka pub/sub backend using one topic per logical topic."""

    def __init__(self, bootstrap_servers='localhost:9092',
                 security_protocol='PLAINTEXT',
                 sasl_mechanism=None,
                 sasl_username=None,
                 sasl_password=None):
        self._bootstrap_servers = bootstrap_servers

        # AdminClient config
        self._admin_config = {
            'bootstrap.servers': bootstrap_servers,
        }

        if security_protocol != 'PLAINTEXT':
            self._admin_config['security.protocol'] = security_protocol
            if sasl_mechanism:
                self._admin_config['sasl.mechanism'] = sasl_mechanism
            if sasl_username:
                self._admin_config['sasl.username'] = sasl_username
            if sasl_password:
                self._admin_config['sasl.password'] = sasl_password

        logger.info(
            f"Kafka backend: {bootstrap_servers} "
            f"protocol={security_protocol}"
        )

    def _parse_topic(self, topic_id: str) -> tuple[str, str, bool]:
        """
        Parse topic identifier into Kafka topic name, class, and durability.

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

        topic_name = f"{topicspace}.{cls}.{topic}"

        return topic_name, cls, durable

    def _retention_ms(self, cls):
        """Return retention.ms for a topic class."""
        if cls == 'flow':
            return LONG_RETENTION_MS
        return SHORT_RETENTION_MS

    def create_producer(self, topic: str, schema: type,
                        **options) -> BackendProducer:
        topic_name, cls, durable = self._parse_topic(topic)
        logger.debug(f"Creating producer: topic={topic_name}")
        return KafkaBackendProducer(
            self._bootstrap_servers, topic_name, durable,
        )

    def create_consumer(self, topic: str, subscription: str, schema: type,
                        initial_position: str = 'latest',
                        **options) -> BackendConsumer:
        """Create a consumer subscribed to a Kafka topic.

        Behaviour is determined by the topic's class prefix:
          - flow: named consumer group, competing consumers
          - request: named consumer group, competing consumers
          - response: unique consumer group per instance
          - notify: unique consumer group per instance
        """
        topic_name, cls, durable = self._parse_topic(topic)

        if cls in ('response', 'notify'):
            # Per-subscriber: unique group so every instance sees
            # every message.  Filter by correlation ID happens at
            # the Subscriber layer above.
            group_id = f"{subscription}-{uuid.uuid4()}"
            auto_offset_reset = 'latest'
        else:
            # Shared: named group, competing consumers
            group_id = subscription
            auto_offset_reset = (
                'earliest' if initial_position == 'earliest'
                else 'latest'
            )

        logger.debug(
            f"Creating consumer: topic={topic_name}, "
            f"group={group_id}, cls={cls}"
        )

        return KafkaBackendConsumer(
            self._bootstrap_servers, topic_name, group_id,
            schema, auto_offset_reset,
        )

    def _create_topic_sync(self, topic_name, retention_ms):
        """Blocking topic creation via AdminClient."""
        admin = AdminClient(self._admin_config)
        new_topic = NewTopic(
            topic_name,
            num_partitions=1,
            replication_factor=1,
            config={
                'retention.ms': str(retention_ms),
            },
        )
        fs = admin.create_topics([new_topic])
        for name, f in fs.items():
            try:
                f.result()
                logger.info(f"Created topic: {name}")
            except KafkaException as e:
                # Topic already exists — idempotent
                if e.args[0].code() == KafkaError.TOPIC_ALREADY_EXISTS:
                    logger.debug(f"Topic already exists: {name}")
                else:
                    raise

    async def create_topic(self, topic: str) -> None:
        """Create a Kafka topic with appropriate retention."""
        topic_name, cls, durable = self._parse_topic(topic)
        retention_ms = self._retention_ms(cls)
        await asyncio.to_thread(
            self._create_topic_sync, topic_name, retention_ms,
        )

    def _delete_topic_sync(self, topic_name):
        """Blocking topic deletion via AdminClient."""
        admin = AdminClient(self._admin_config)
        fs = admin.delete_topics([topic_name])
        for name, f in fs.items():
            try:
                f.result()
                logger.info(f"Deleted topic: {name}")
            except KafkaException as e:
                # Topic doesn't exist — idempotent
                if e.args[0].code() == KafkaError.UNKNOWN_TOPIC_OR_PART:
                    logger.debug(f"Topic not found: {name}")
                else:
                    raise
            except Exception as e:
                logger.debug(f"Topic delete for {name}: {e}")

    async def delete_topic(self, topic: str) -> None:
        """Delete a Kafka topic."""
        topic_name, cls, durable = self._parse_topic(topic)
        await asyncio.to_thread(self._delete_topic_sync, topic_name)

    def _topic_exists_sync(self, topic_name):
        """Blocking topic existence check via AdminClient."""
        admin = AdminClient(self._admin_config)
        metadata = admin.list_topics(timeout=10)
        return topic_name in metadata.topics

    async def topic_exists(self, topic: str) -> bool:
        """Check whether a Kafka topic exists."""
        topic_name, cls, durable = self._parse_topic(topic)
        return await asyncio.to_thread(
            self._topic_exists_sync, topic_name,
        )

    async def ensure_topic(self, topic: str) -> None:
        """Ensure a topic exists, creating it if necessary."""
        if not await self.topic_exists(topic):
            await self.create_topic(topic)

    def close(self) -> None:
        pass
