"""
Async Pulsar backend implementation.

Uses receive_async() for zero-thread message receiving. The only
operations that use threads are the initial client.subscribe() and
client.create_producer() calls, which are wrapped in
asyncio.to_thread and release the thread immediately after.
"""

import pulsar
import _pulsar
import asyncio
import json
import logging
import urllib.request
import urllib.error
import urllib.parse
from typing import Any

from .async_backend import AsyncPubSubBackend, AsyncBackendProducer
from .async_backend import AsyncBackendConsumer, Message
from .serialization import dataclass_to_dict, dict_to_dataclass

logger = logging.getLogger(__name__)


class PulsarMessage:
    """Wrapper for Pulsar messages to match Message protocol."""

    def __init__(self, pulsar_msg, schema_cls):
        self._msg = pulsar_msg
        self._schema_cls = schema_cls
        self._value = None

    def value(self) -> Any:
        if self._value is None:
            json_data = self._msg.data().decode('utf-8')
            data_dict = json.loads(json_data)
            self._value = dict_to_dataclass(data_dict, self._schema_cls)
        return self._value

    def properties(self) -> dict:
        return self._msg.properties()


class AsyncPulsarProducer:
    """Async Pulsar producer. send() uses asyncio.to_thread."""

    def __init__(self, pulsar_producer, schema_cls):
        self._producer = pulsar_producer
        self._schema_cls = schema_cls

    async def send(self, message: Any, properties: dict = {}) -> None:
        data_dict = dataclass_to_dict(message)
        json_data = json.dumps(data_dict)
        await asyncio.to_thread(
            self._producer.send,
            json_data.encode('utf-8'),
            properties,
        )

    async def close(self) -> None:
        await asyncio.to_thread(self._producer.flush)
        self._producer.close()


class AsyncPulsarConsumer:
    """Async Pulsar consumer. Uses receive_async() for zero-thread
    message receiving."""

    def __init__(self, pulsar_consumer, schema_cls):
        self._consumer = pulsar_consumer
        self._schema_cls = schema_cls

    async def receive(self) -> Message:
        pulsar_msg = await self._consumer.receive_async()
        return PulsarMessage(pulsar_msg, self._schema_cls)

    async def acknowledge(self, message: Message) -> None:
        if isinstance(message, PulsarMessage):
            self._consumer.acknowledge(message._msg)

    async def negative_acknowledge(self, message: Message) -> None:
        if isinstance(message, PulsarMessage):
            self._consumer.negative_acknowledge(message._msg)

    async def close(self) -> None:
        try:
            self._consumer.unsubscribe()
        except Exception:
            pass
        self._consumer.close()


class AsyncPulsarBackend:
    """Async Pulsar pub/sub backend.

    Zero OS threads for receiving. client.subscribe() and
    client.create_producer() are wrapped in asyncio.to_thread for
    the initial setup call.
    """

    def __init__(
        self, host: str, api_key: str = None, listener: str = None,
        admin_url: str = None,
    ):
        self.host = host
        self.api_key = api_key
        self.listener = listener
        self.admin_url = admin_url

        client_args = {'service_url': host}

        if listener:
            client_args['listener_name'] = listener

        if api_key:
            client_args['authentication'] = pulsar.AuthenticationToken(api_key)

        client_args['logger'] = pulsar.ConsoleLogger(
            _pulsar.LoggerLevel.Error
        )

        self.client = pulsar.Client(**client_args)
        logger.info(f"Async Pulsar client connected to {host}")

    def _map_topic(self, queue_id: str) -> str:
        if '://' in queue_id:
            return queue_id

        parts = queue_id.split(':', 2)
        if len(parts) != 3:
            raise ValueError(
                f"Invalid queue format: {queue_id}, "
                f"expected class:topicspace:topic"
            )

        cls, topicspace, topic = parts

        if cls == 'flow':
            persistence = 'persistent'
        elif cls in ('request', 'response', 'notify'):
            persistence = 'non-persistent'
        else:
            raise ValueError(
                f"Invalid queue class: {cls}, "
                f"expected flow, request, response, or notify"
            )

        return f"{persistence}://{topicspace}/{cls}/{topic}"

    def _consumer_type(self, topic: str):
        cls = topic.split(':', 1)[0] if ':' in topic else 'flow'
        if cls in ('response', 'notify'):
            return pulsar.ConsumerType.Exclusive
        return pulsar.ConsumerType.Shared

    async def create_consumer(
        self, topic: str, subscription: str, schema: type,
        initial_position: str = 'latest', **options,
    ) -> AsyncBackendConsumer:
        pulsar_topic = self._map_topic(topic)

        if initial_position == 'earliest':
            pos = pulsar.InitialPosition.Earliest
        else:
            pos = pulsar.InitialPosition.Latest

        ctype = self._consumer_type(topic)

        consumer_args = {
            'topic': pulsar_topic,
            'subscription_name': subscription,
            'schema': pulsar.schema.BytesSchema(),
            'initial_position': pos,
            'consumer_type': ctype,
        }

        pulsar_consumer = await asyncio.to_thread(
            self.client.subscribe, **consumer_args,
        )
        logger.debug(
            f"Created async consumer: {pulsar_topic}, "
            f"subscription: {subscription}"
        )

        return AsyncPulsarConsumer(pulsar_consumer, schema)

    async def create_producer(
        self, topic: str, schema: type, **options,
    ) -> AsyncBackendProducer:
        pulsar_topic = self._map_topic(topic)

        producer_args = {
            'topic': pulsar_topic,
            'schema': pulsar.schema.BytesSchema(),
        }

        if 'chunking_enabled' in options:
            producer_args['chunking_enabled'] = options['chunking_enabled']

        pulsar_producer = await asyncio.to_thread(
            self.client.create_producer, **producer_args,
        )
        logger.debug(f"Created async producer: {pulsar_topic}")

        return AsyncPulsarProducer(pulsar_producer, schema)

    def _admin_api_path(self, pulsar_uri: str) -> str:
        scheme, rest = pulsar_uri.split('://', 1)
        tenant, namespace, topic = rest.split('/', 2)
        encoded_topic = urllib.parse.quote(topic, safe='')
        return f"/admin/v2/{scheme}/{tenant}/{namespace}/{encoded_topic}"

    def _admin_request(self, method, path):
        url = f"{self.admin_url}{path}"
        req = urllib.request.Request(url, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                if method == 'GET':
                    return json.loads(resp.read().decode('utf-8'))
                return None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise

    def _delete_topic_sync(self, topic: str):
        pulsar_uri = self._map_topic(topic)
        if pulsar_uri.startswith('non-persistent://'):
            return
        api_path = self._admin_api_path(pulsar_uri)
        try:
            subs = self._admin_request('GET', f"{api_path}/subscriptions")
        except Exception as e:
            logger.warning(
                f"Failed to list subscriptions for {topic}: {e}"
            )
            return
        if subs:
            for sub in subs:
                encoded_sub = urllib.parse.quote(sub, safe='')
                try:
                    self._admin_request(
                        'DELETE',
                        f"{api_path}/subscription/{encoded_sub}"
                        f"?force=true"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to delete subscription {sub} "
                        f"from {topic}: {e}"
                    )
        try:
            self._admin_request('DELETE', api_path)
            logger.info(f"Deleted topic: {topic}")
        except Exception as e:
            logger.warning(f"Failed to delete topic {topic}: {e}")

    def _topic_exists_sync(self, topic: str) -> bool:
        pulsar_uri = self._map_topic(topic)
        if pulsar_uri.startswith('non-persistent://'):
            return False
        api_path = self._admin_api_path(pulsar_uri)
        try:
            result = self._admin_request('GET', f"{api_path}/stats")
            return result is not None
        except Exception:
            return False

    async def create_topic(self, topic: str) -> None:
        pass

    async def delete_topic(self, topic: str) -> None:
        if not self.admin_url:
            logger.warning(
                f"Cannot delete topic {topic}: no admin URL configured"
            )
            return
        await asyncio.to_thread(self._delete_topic_sync, topic)

    async def topic_exists(self, topic: str) -> bool:
        if not self.admin_url:
            return True
        return await asyncio.to_thread(self._topic_exists_sync, topic)

    async def ensure_topic(self, topic: str) -> None:
        pass

    async def close(self) -> None:
        self.client.close()
        logger.info("Async Pulsar client closed")
