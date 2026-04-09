"""
RabbitMQ backend implementation for pub/sub abstraction.

Uses a single topic exchange per topicspace. The logical queue name
becomes the routing key. Consumer behavior is determined by the
subscription name:

- Same subscription + same topic = shared queue (competing consumers)
- Different subscriptions = separate queues (broadcast / fan-out)

This mirrors Pulsar's subscription model using idiomatic RabbitMQ.

Architecture:
  Producer  -->  [tg exchange]  --routing key-->  [named queue]  --> Consumer
                                --routing key-->  [named queue]  --> Consumer
                                --routing key-->  [exclusive q]  --> Subscriber

Uses basic_consume (push) instead of basic_get (polling) for
efficient message delivery.
"""

import json
import time
import logging
import queue
import threading
import pika
from typing import Any

from .backend import PubSubBackend, BackendProducer, BackendConsumer, Message
from .serialization import dataclass_to_dict, dict_to_dataclass

logger = logging.getLogger(__name__)


class RabbitMQMessage:
    """Wrapper for RabbitMQ messages to match Message protocol."""

    def __init__(self, method, properties, body, schema_cls):
        self._method = method
        self._properties = properties
        self._body = body
        self._schema_cls = schema_cls
        self._value = None

    def value(self) -> Any:
        """Deserialize and return the message value as a dataclass."""
        if self._value is None:
            data_dict = json.loads(self._body.decode('utf-8'))
            self._value = dict_to_dataclass(data_dict, self._schema_cls)
        return self._value

    def properties(self) -> dict:
        """Return message properties from AMQP headers."""
        headers = self._properties.headers or {}
        return dict(headers)


class RabbitMQBackendProducer:
    """Publishes messages to a topic exchange with a routing key.

    Uses thread-local connections so each thread gets its own
    connection/channel. This avoids wire corruption from concurrent
    threads writing to the same socket (pika is not thread-safe).
    """

    def __init__(self, connection_params, exchange_name, routing_key,
                 durable):
        self._connection_params = connection_params
        self._exchange_name = exchange_name
        self._routing_key = routing_key
        self._durable = durable
        self._local = threading.local()

    def _get_channel(self):
        """Get or create a thread-local connection and channel."""
        conn = getattr(self._local, 'connection', None)
        chan = getattr(self._local, 'channel', None)

        if conn is None or not conn.is_open or chan is None or not chan.is_open:
            # Close stale connection if any
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

            conn = pika.BlockingConnection(self._connection_params)
            chan = conn.channel()
            chan.exchange_declare(
                exchange=self._exchange_name,
                exchange_type='topic',
                durable=True,
            )
            self._local.connection = conn
            self._local.channel = chan

        return chan

    def send(self, message: Any, properties: dict = {}) -> None:
        data_dict = dataclass_to_dict(message)
        json_data = json.dumps(data_dict)

        amqp_properties = pika.BasicProperties(
            delivery_mode=2 if self._durable else 1,
            content_type='application/json',
            headers=properties if properties else None,
        )

        for attempt in range(2):
            try:
                channel = self._get_channel()
                channel.basic_publish(
                    exchange=self._exchange_name,
                    routing_key=self._routing_key,
                    body=json_data.encode('utf-8'),
                    properties=amqp_properties,
                )
                return
            except Exception as e:
                logger.warning(
                    f"RabbitMQ send failed (attempt {attempt + 1}): {e}"
                )
                # Force reconnect on next attempt
                self._local.connection = None
                self._local.channel = None
                if attempt == 1:
                    raise

    def flush(self) -> None:
        pass

    def close(self) -> None:
        """Close the thread-local connection if any."""
        conn = getattr(self._local, 'connection', None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._local.connection = None
            self._local.channel = None


class RabbitMQBackendConsumer:
    """Consumes from a queue bound to a topic exchange.

    Uses basic_consume (push model) with messages delivered to an
    internal thread-safe queue. process_data_events() drives both
    message delivery and heartbeat processing.
    """

    def __init__(self, connection_params, exchange_name, routing_key,
                 queue_name, schema_cls, durable, exclusive=False,
                 auto_delete=False):
        self._connection_params = connection_params
        self._exchange_name = exchange_name
        self._routing_key = routing_key
        self._queue_name = queue_name
        self._schema_cls = schema_cls
        self._durable = durable
        self._exclusive = exclusive
        self._auto_delete = auto_delete
        self._connection = None
        self._channel = None
        self._consumer_tag = None
        self._incoming = queue.Queue()

    def _connect(self):
        self._connection = pika.BlockingConnection(self._connection_params)
        self._channel = self._connection.channel()

        # Declare the topic exchange
        self._channel.exchange_declare(
            exchange=self._exchange_name,
            exchange_type='topic',
            durable=True,
        )

        # Declare the queue — anonymous if exclusive
        result = self._channel.queue_declare(
            queue=self._queue_name,
            durable=self._durable,
            exclusive=self._exclusive,
            auto_delete=self._auto_delete,
        )
        # Capture actual name (important for anonymous queues where name='')
        self._queue_name = result.method.queue

        self._channel.queue_bind(
            queue=self._queue_name,
            exchange=self._exchange_name,
            routing_key=self._routing_key,
        )

        self._channel.basic_qos(prefetch_count=1)

        # Register push-based consumer
        self._consumer_tag = self._channel.basic_consume(
            queue=self._queue_name,
            on_message_callback=self._on_message,
            auto_ack=False,
        )

    def _on_message(self, channel, method, properties, body):
        """Callback invoked by pika when a message arrives."""
        self._incoming.put((method, properties, body))

    def _is_alive(self):
        return (
            self._connection is not None
            and self._connection.is_open
            and self._channel is not None
            and self._channel.is_open
        )

    def receive(self, timeout_millis: int = 2000) -> Message:
        """Receive a message. Raises TimeoutError if none available."""
        if not self._is_alive():
            self._connect()

        timeout_seconds = timeout_millis / 1000.0
        deadline = time.monotonic() + timeout_seconds

        while time.monotonic() < deadline:
            # Check if a message was already delivered
            try:
                method, properties, body = self._incoming.get_nowait()
                return RabbitMQMessage(
                    method, properties, body, self._schema_cls,
                )
            except queue.Empty:
                pass

            # Drive pika's I/O — delivers messages and processes heartbeats
            remaining = deadline - time.monotonic()
            if remaining > 0:
                self._connection.process_data_events(
                    time_limit=min(0.1, remaining),
                )

        raise TimeoutError("No message received within timeout")

    def acknowledge(self, message: Message) -> None:
        if isinstance(message, RabbitMQMessage) and message._method:
            self._channel.basic_ack(
                delivery_tag=message._method.delivery_tag,
            )

    def negative_acknowledge(self, message: Message) -> None:
        if isinstance(message, RabbitMQMessage) and message._method:
            self._channel.basic_nack(
                delivery_tag=message._method.delivery_tag,
                requeue=True,
            )

    def unsubscribe(self) -> None:
        if self._consumer_tag and self._channel and self._channel.is_open:
            try:
                self._channel.basic_cancel(self._consumer_tag)
            except Exception:
                pass
            self._consumer_tag = None

    def close(self) -> None:
        self.unsubscribe()
        try:
            if self._channel and self._channel.is_open:
                self._channel.close()
        except Exception:
            pass
        try:
            if self._connection and self._connection.is_open:
                self._connection.close()
        except Exception:
            pass
        self._channel = None
        self._connection = None


class RabbitMQBackend:
    """RabbitMQ pub/sub backend using a topic exchange per topicspace."""

    def __init__(self, host='localhost', port=5672, username='guest',
                 password='guest', vhost='/'):
        self._connection_params = pika.ConnectionParameters(
            host=host,
            port=port,
            virtual_host=vhost,
            credentials=pika.PlainCredentials(username, password),
            heartbeat=0,
        )
        logger.info(f"RabbitMQ backend: {host}:{port} vhost={vhost}")

    def _parse_queue_id(self, queue_id: str) -> tuple[str, str, str, bool]:
        """
        Parse queue identifier into exchange, routing key, and durability.

        Format: class:topicspace:topic
        Returns: (exchange_name, routing_key, class, durable)
        """
        if ':' not in queue_id:
            return 'tg', queue_id, 'flow', False

        parts = queue_id.split(':', 2)
        if len(parts) != 3:
            raise ValueError(
                f"Invalid queue format: {queue_id}, "
                f"expected class:topicspace:topic"
            )

        cls, topicspace, topic = parts

        if cls == 'flow':
            durable = True
        elif cls in ('request', 'response', 'notify'):
            durable = False
        else:
            raise ValueError(
                f"Invalid queue class: {cls}, "
                f"expected flow, request, response, or notify"
            )

        # Exchange per topicspace, routing key includes class
        exchange_name = topicspace
        routing_key = f"{cls}.{topic}"

        return exchange_name, routing_key, cls, durable

    # Keep map_queue_name for backward compatibility with tests
    def map_queue_name(self, queue_id: str) -> tuple[str, bool]:
        exchange, routing_key, cls, durable = self._parse_queue_id(queue_id)
        return f"{exchange}.{routing_key}", durable

    def create_producer(self, topic: str, schema: type,
                        **options) -> BackendProducer:
        exchange, routing_key, cls, durable = self._parse_queue_id(topic)
        logger.debug(
            f"Creating producer: exchange={exchange}, "
            f"routing_key={routing_key}"
        )
        return RabbitMQBackendProducer(
            self._connection_params, exchange, routing_key, durable,
        )

    def create_consumer(self, topic: str, subscription: str, schema: type,
                        initial_position: str = 'latest',
                        **options) -> BackendConsumer:
        """Create a consumer with a queue bound to the topic exchange.

        Behaviour is determined by the topic's class prefix:
          - flow: named durable queue, competing consumers (round-robin)
          - request: named non-durable queue, competing consumers
          - response: anonymous ephemeral queue, per-subscriber (auto-delete)
          - notify: anonymous ephemeral queue, per-subscriber (auto-delete)
        """
        exchange, routing_key, cls, durable = self._parse_queue_id(topic)

        if cls in ('response', 'notify'):
            # Per-subscriber: anonymous queue, auto-deleted on disconnect
            queue_name = ''
            queue_durable = False
            exclusive = True
            auto_delete = True
        else:
            # Shared: named queue, competing consumers
            queue_name = f"{exchange}.{routing_key}.{subscription}"
            queue_durable = durable
            exclusive = False
            auto_delete = False

        logger.debug(
            f"Creating consumer: exchange={exchange}, "
            f"routing_key={routing_key}, queue={queue_name or '(anonymous)'}, "
            f"cls={cls}"
        )

        return RabbitMQBackendConsumer(
            self._connection_params, exchange, routing_key,
            queue_name, schema, queue_durable, exclusive, auto_delete,
        )

    def close(self) -> None:
        pass
