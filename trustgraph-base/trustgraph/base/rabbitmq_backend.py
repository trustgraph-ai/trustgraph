"""
RabbitMQ backend implementation for pub/sub abstraction.

Each logical topic maps to its own fanout exchange.  The exchange name
encodes the full topic identity:

    class:topicspace:topic  →  exchange  topicspace.class.topic

Producers publish to the exchange with an empty routing key.
Consumers declare and bind their own queues:

  - flow / request: named durable/non-durable queue (competing consumers)
  - response / notify: anonymous exclusive auto-delete queue (per-subscriber)

The flow service manages topic lifecycle (create/delete exchanges).
Consumers manage their own queue lifecycle (declare + bind on connect).

Architecture:
  Producer  -->  [fanout exchange]  -->  [named queue]      --> Consumer
                                    -->  [named queue]      --> Consumer
                                    -->  [exclusive queue]  --> Subscriber
"""

import asyncio
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
    """Publishes messages to a fanout exchange.

    Uses thread-local connections so each thread gets its own
    connection/channel. This avoids wire corruption from concurrent
    threads writing to the same socket (pika is not thread-safe).
    """

    def __init__(self, connection_params, exchange_name, durable):
        self._connection_params = connection_params
        self._exchange_name = exchange_name
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
                exchange_type='fanout',
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
                    routing_key='',
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
    """Consumes from a queue bound to a fanout exchange.

    Uses basic_consume (push model) with messages delivered to an
    internal thread-safe queue. process_data_events() drives both
    message delivery and heartbeat processing.
    """

    def __init__(self, connection_params, exchange_name, queue_name,
                 schema_cls, durable, exclusive=False, auto_delete=False):
        self._connection_params = connection_params
        self._exchange_name = exchange_name
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

        # Declare the fanout exchange (idempotent)
        self._channel.exchange_declare(
            exchange=self._exchange_name,
            exchange_type='fanout',
            durable=True,
        )

        if self._exclusive:
            # Anonymous ephemeral queue (response/notify class).
            # Per-consumer, broker assigns the name.
            result = self._channel.queue_declare(
                queue='',
                durable=False,
                exclusive=True,
                auto_delete=True,
            )
            self._queue_name = result.method.queue
        else:
            # Named queue (flow/request class).
            # Consumer owns its queue — declare and bind here.
            self._channel.queue_declare(
                queue=self._queue_name,
                durable=self._durable,
                exclusive=False,
                auto_delete=False,
            )

        # Bind queue to the fanout exchange
        self._channel.queue_bind(
            queue=self._queue_name,
            exchange=self._exchange_name,
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

    def ensure_connected(self) -> None:
        """Eagerly declare and bind the queue.

        Without this, the queue is only declared lazily on the first
        receive() call. For request/response with ephemeral per-subscriber
        response queues that is a race: a request published before the
        response queue is bound will have its reply silently dropped by
        the broker. Subscriber.start() calls this so callers get a hard
        readiness barrier."""
        if not self._is_alive():
            self._connect()

    def receive(self, timeout_millis: int = 2000) -> Message:
        """Receive a message. Raises TimeoutError if none available.

        Loop ordering matters: check _incoming at the TOP of each
        iteration, not as the loop condition.  process_data_events
        may dispatch a message via the _on_message callback during
        the pump; we must re-check _incoming on the next iteration
        before giving up on the deadline.  The previous control
        flow (`while deadline: check; pump`) could lose a wakeup if
        the pump consumed the remainder of the window — the
        `while` check would fail before `_incoming` was re-read,
        leaving a just-dispatched message stranded until the next
        receive() call one full poll cycle later.
        """
        if not self._is_alive():
            self._connect()

        timeout_seconds = timeout_millis / 1000.0
        deadline = time.monotonic() + timeout_seconds

        while True:
            # Check if a message has been dispatched to our queue.
            # This catches both (a) messages dispatched before this
            # receive() was called and (b) messages dispatched
            # during the previous iteration's process_data_events.
            try:
                method, properties, body = self._incoming.get_nowait()
                return RabbitMQMessage(
                    method, properties, body, self._schema_cls,
                )
            except queue.Empty:
                pass

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("No message received within timeout")

            # Drive pika's I/O.  Any messages delivered during this
            # call land in _incoming via _on_message; the next
            # iteration of this loop catches them at the top.
            self._connection.process_data_events(
                time_limit=min(0.1, remaining),
            )

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
    """RabbitMQ pub/sub backend using one fanout exchange per topic."""

    def __init__(self, host='localhost', port=5672, username='guest',
                 password='guest', vhost='/'):
        self._connection_params = pika.ConnectionParameters(
            host=host,
            port=port,
            virtual_host=vhost,
            credentials=pika.PlainCredentials(username, password),
            # Heartbeats let us detect silently-dead connections
            # (broker restarts, network partitions, orphaned channels)
            # within ~2×interval.  Consumer threads drive pika's I/O
            # loop every 100ms via process_data_events() in receive(),
            # so heartbeat frames get pumped automatically.  Producers
            # reconnect lazily on the next publish if their connection
            # has been aged out by the broker.
            heartbeat=60,
            blocked_connection_timeout=300,
        )
        logger.info(f"RabbitMQ backend: {host}:{port} vhost={vhost}")

    def _parse_topic(self, topic_id: str) -> tuple[str, str, bool]:
        """
        Parse topic identifier into exchange name and durability.

        Format: class:topicspace:topic
        Returns: (exchange_name, class, durable)

        The exchange name encodes the full topic identity:
            class:topicspace:topic  →  topicspace.class.topic
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

        exchange_name = f"{topicspace}.{cls}.{topic}"

        return exchange_name, cls, durable

    def create_producer(self, topic: str, schema: type,
                        **options) -> BackendProducer:
        exchange, cls, durable = self._parse_topic(topic)
        logger.debug(
            f"Creating producer: exchange={exchange}"
        )
        return RabbitMQBackendProducer(
            self._connection_params, exchange, durable,
        )

    def create_consumer(self, topic: str, subscription: str, schema: type,
                        initial_position: str = 'latest',
                        **options) -> BackendConsumer:
        """Create a consumer with a queue bound to the topic's exchange.

        Behaviour is determined by the topic's class prefix:
          - flow: named durable queue, competing consumers (round-robin)
          - request: named non-durable queue, competing consumers
          - response: anonymous ephemeral queue, per-subscriber (auto-delete)
          - notify: anonymous ephemeral queue, per-subscriber (auto-delete)
        """
        exchange, cls, durable = self._parse_topic(topic)

        if cls in ('response', 'notify'):
            # Per-subscriber: anonymous queue, auto-deleted on disconnect
            queue_name = ''
            queue_durable = False
            exclusive = True
            auto_delete = True
        else:
            # Shared: named queue, competing consumers
            queue_name = f"{exchange}.{subscription}"
            queue_durable = durable
            exclusive = False
            auto_delete = False

        logger.debug(
            f"Creating consumer: exchange={exchange}, "
            f"queue={queue_name or '(anonymous)'}, cls={cls}"
        )

        return RabbitMQBackendConsumer(
            self._connection_params, exchange,
            queue_name, schema, queue_durable, exclusive, auto_delete,
        )

    def _create_topic_sync(self, exchange_name):
        """Blocking exchange creation — run via asyncio.to_thread."""
        connection = None
        try:
            connection = pika.BlockingConnection(self._connection_params)
            channel = connection.channel()
            channel.exchange_declare(
                exchange=exchange_name,
                exchange_type='fanout',
                durable=True,
            )
            logger.info(f"Created topic (exchange): {exchange_name}")
        finally:
            if connection and connection.is_open:
                try:
                    connection.close()
                except Exception:
                    pass

    async def create_topic(self, topic: str) -> None:
        """Create the fanout exchange for a logical topic.

        Only applies to flow and request class topics. Response and
        notify exchanges are created on demand by consumers.
        """
        exchange, cls, durable = self._parse_topic(topic)

        if cls in ('response', 'notify'):
            return

        await asyncio.to_thread(self._create_topic_sync, exchange)

    def _delete_topic_sync(self, exchange_name):
        """Blocking exchange deletion — run via asyncio.to_thread."""
        connection = None
        try:
            connection = pika.BlockingConnection(self._connection_params)
            channel = connection.channel()
            channel.exchange_delete(exchange=exchange_name)
            logger.info(f"Deleted topic (exchange): {exchange_name}")
        except Exception as e:
            # Idempotent — exchange may already be gone
            logger.debug(f"Exchange delete for {exchange_name}: {e}")
        finally:
            if connection and connection.is_open:
                try:
                    connection.close()
                except Exception:
                    pass

    async def delete_topic(self, topic: str) -> None:
        """Delete a topic's fanout exchange.

        Consumer queues lose their binding and drain naturally.
        """
        exchange, cls, durable = self._parse_topic(topic)
        await asyncio.to_thread(self._delete_topic_sync, exchange)

    def _topic_exists_sync(self, exchange_name):
        """Blocking exchange existence check — run via asyncio.to_thread.
        Uses passive=True which checks without creating."""
        connection = None
        try:
            connection = pika.BlockingConnection(self._connection_params)
            channel = connection.channel()
            channel.exchange_declare(
                exchange=exchange_name, passive=True,
            )
            return True
        except pika.exceptions.ChannelClosedByBroker:
            # 404 NOT_FOUND — exchange does not exist
            return False
        finally:
            if connection and connection.is_open:
                try:
                    connection.close()
                except Exception:
                    pass

    async def topic_exists(self, topic: str) -> bool:
        """Check whether a topic's exchange exists.

        Only applies to flow and request class topics. Response and
        notify topics are ephemeral — always returns False.
        """
        exchange, cls, durable = self._parse_topic(topic)

        if cls in ('response', 'notify'):
            return False

        return await asyncio.to_thread(
            self._topic_exists_sync, exchange
        )

    async def ensure_topic(self, topic: str) -> None:
        """Ensure a topic exists, creating it if necessary."""
        if not await self.topic_exists(topic):
            await self.create_topic(topic)

    def close(self) -> None:
        pass
