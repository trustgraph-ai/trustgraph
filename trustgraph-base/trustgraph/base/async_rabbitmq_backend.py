"""
Async RabbitMQ backend implementation.

Uses aio-pika for fully async AMQP operations. Each logical topic
maps to a fanout exchange, matching the sync RabbitMQ backend's
topology:

    class:topicspace:topic  →  exchange  topicspace.class.topic

Producers publish to the exchange with an empty routing key.
Consumers declare and bind their own queues:

  - flow / request: named durable/non-durable queue (competing consumers)
  - response / notify: anonymous exclusive auto-delete queue (per-subscriber)
"""

import asyncio
import json
import logging
from typing import Any

import aio_pika

from .async_backend import AsyncPubSubBackend, AsyncBackendProducer
from .async_backend import AsyncBackendConsumer, Message
from .serialization import dataclass_to_dict, dict_to_dataclass

logger = logging.getLogger(__name__)


class AsyncRabbitMQMessage:
    """Wrapper for aio-pika messages to match Message protocol."""

    def __init__(self, message: aio_pika.IncomingMessage, schema_cls):
        self._msg = message
        self._schema_cls = schema_cls
        self._value = None

    def value(self) -> Any:
        if self._value is None:
            data_dict = json.loads(self._msg.body.decode('utf-8'))
            self._value = dict_to_dataclass(data_dict, self._schema_cls)
        return self._value

    def properties(self) -> dict:
        return dict(self._msg.headers or {})


class AsyncRabbitMQProducer:
    """Async RabbitMQ producer publishing to a fanout exchange."""

    def __init__(self, channel, exchange, durable):
        self._channel = channel
        self._exchange = exchange
        self._durable = durable

    async def send(self, message: Any, properties: dict = {}) -> None:
        data_dict = dataclass_to_dict(message)
        json_data = json.dumps(data_dict)

        amqp_message = aio_pika.Message(
            body=json_data.encode('utf-8'),
            delivery_mode=(
                aio_pika.DeliveryMode.PERSISTENT
                if self._durable
                else aio_pika.DeliveryMode.NOT_PERSISTENT
            ),
            content_type='application/json',
            headers=properties if properties else None,
        )

        await self._exchange.publish(amqp_message, routing_key='')

    async def close(self) -> None:
        try:
            await self._channel.close()
        except BaseException:
            pass


class AsyncRabbitMQConsumer:
    """Async RabbitMQ consumer using aio-pika push-based consumption."""

    def __init__(self, channel, queue, schema_cls, consumer_tag):
        self._channel = channel
        self._queue = queue
        self._schema_cls = schema_cls
        self._consumer_tag = consumer_tag
        self._incoming = asyncio.Queue()

    async def _on_message(self, message: aio_pika.IncomingMessage):
        await self._incoming.put(message)

    async def receive(self) -> Message:
        msg = await self._incoming.get()
        return AsyncRabbitMQMessage(msg, self._schema_cls)

    async def acknowledge(self, message: Message) -> None:
        if isinstance(message, AsyncRabbitMQMessage):
            await message._msg.ack()

    async def negative_acknowledge(self, message: Message) -> None:
        if isinstance(message, AsyncRabbitMQMessage):
            await message._msg.nack(requeue=True)

    async def close(self) -> None:
        try:
            await self._queue.cancel(self._consumer_tag)
        except BaseException:
            pass
        try:
            await self._channel.close()
        except BaseException:
            pass


class AsyncRabbitMQBackend:
    """Async RabbitMQ pub/sub backend using aio-pika.

    Fully async — zero OS threads for receiving, sending, and
    consumer/producer lifecycle.
    """

    def __init__(
        self, host='localhost', port=5672, username='guest',
        password='guest', vhost='/',
    ):
        self._url = f"amqp://{username}:{password}@{host}:{port}/{vhost}"
        self._connection = None
        self._host = host
        self._port = port
        logger.info(
            f"Async RabbitMQ backend: {host}:{port} vhost={vhost}"
        )

    async def _ensure_connection(self):
        if self._connection is None or self._connection.is_closed:
            self._connection = await aio_pika.connect_robust(self._url)
            logger.info(
                f"Async RabbitMQ connected to "
                f"{self._host}:{self._port}"
            )
        return self._connection

    def _parse_topic(self, topic_id: str) -> tuple[str, str, bool]:
        """Parse topic identifier into exchange name, class, durability.

        Format: class:topicspace:topic
        Returns: (exchange_name, class, durable)
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

    async def create_producer(
        self, topic: str, schema: type, **options,
    ) -> AsyncBackendProducer:
        exchange_name, cls, durable = self._parse_topic(topic)

        connection = await self._ensure_connection()
        channel = await connection.channel()

        exchange = await channel.declare_exchange(
            exchange_name,
            aio_pika.ExchangeType.FANOUT,
            durable=True,
        )

        logger.debug(f"Created async producer: exchange={exchange_name}")

        return AsyncRabbitMQProducer(channel, exchange, durable)

    async def create_consumer(
        self, topic: str, subscription: str, schema: type,
        initial_position: str = 'latest', **options,
    ) -> AsyncBackendConsumer:
        exchange_name, cls, durable = self._parse_topic(topic)

        connection = await self._ensure_connection()
        channel = await connection.channel()

        exchange = await channel.declare_exchange(
            exchange_name,
            aio_pika.ExchangeType.FANOUT,
            durable=True,
        )

        await channel.set_qos(prefetch_count=1)

        if cls in ('response', 'notify'):
            queue = await channel.declare_queue(
                '',
                durable=False,
                exclusive=True,
                auto_delete=True,
            )
        else:
            queue_name = f"{exchange_name}.{subscription}"
            queue = await channel.declare_queue(
                queue_name,
                durable=durable,
                exclusive=False,
                auto_delete=False,
            )

        await queue.bind(exchange)

        consumer = AsyncRabbitMQConsumer(
            channel, queue, schema, consumer_tag=None,
        )

        consumer_tag = await queue.consume(consumer._on_message)
        consumer._consumer_tag = consumer_tag

        logger.debug(
            f"Created async consumer: exchange={exchange_name}, "
            f"queue={queue.name or '(anonymous)'}, cls={cls}"
        )

        return consumer

    async def create_topic(self, topic: str) -> None:
        exchange_name, cls, durable = self._parse_topic(topic)

        if cls in ('response', 'notify'):
            return

        connection = await self._ensure_connection()
        channel = await connection.channel()
        try:
            await channel.declare_exchange(
                exchange_name,
                aio_pika.ExchangeType.FANOUT,
                durable=True,
            )
            logger.info(
                f"Created topic (exchange): {exchange_name}"
            )
        finally:
            await channel.close()

    async def delete_topic(self, topic: str) -> None:
        exchange_name, cls, durable = self._parse_topic(topic)

        connection = await self._ensure_connection()
        channel = await connection.channel()
        try:
            await channel.exchange_delete(exchange_name)
            logger.info(
                f"Deleted topic (exchange): {exchange_name}"
            )
        except BaseException as e:
            logger.debug(
                f"Exchange delete for {exchange_name}: {e}"
            )
        finally:
            try:
                await channel.close()
            except BaseException:
                pass

    async def topic_exists(self, topic: str) -> bool:
        exchange_name, cls, durable = self._parse_topic(topic)

        if cls in ('response', 'notify'):
            return False

        connection = await self._ensure_connection()
        channel = await connection.channel()
        try:
            await channel.declare_exchange(
                exchange_name, passive=True,
            )
            return True
        except aio_pika.exceptions.ChannelNotFoundEntity:
            return False
        except BaseException:
            return False
        finally:
            try:
                await channel.close()
            except BaseException:
                pass

    async def ensure_topic(self, topic: str) -> None:
        if not await self.topic_exists(topic):
            await self.create_topic(topic)

    async def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            try:
                await self._connection.close()
            except BaseException:
                pass
        self._connection = None
        logger.info("Async RabbitMQ client closed")
