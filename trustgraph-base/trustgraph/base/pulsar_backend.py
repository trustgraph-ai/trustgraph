"""
Pulsar backend implementation for pub/sub abstraction.

This module provides a Pulsar-specific implementation of the backend interfaces,
handling topic mapping, serialization, and Pulsar client management.
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

from .backend import PubSubBackend, BackendProducer, BackendConsumer, Message
from .serialization import dataclass_to_dict, dict_to_dataclass

logger = logging.getLogger(__name__)


class PulsarMessage:
    """Wrapper for Pulsar messages to match Message protocol."""

    def __init__(self, pulsar_msg, schema_cls):
        self._msg = pulsar_msg
        self._schema_cls = schema_cls
        self._value = None

    def value(self) -> Any:
        """Deserialize and return the message value as a dataclass."""
        if self._value is None:
            # Get JSON string from Pulsar message
            json_data = self._msg.data().decode('utf-8')
            data_dict = json.loads(json_data)
            # Convert to dataclass
            self._value = dict_to_dataclass(data_dict, self._schema_cls)
        return self._value

    def properties(self) -> dict:
        """Return message properties."""
        return self._msg.properties()


class PulsarBackendProducer:
    """Pulsar-specific producer implementation."""

    def __init__(self, pulsar_producer, schema_cls):
        self._producer = pulsar_producer
        self._schema_cls = schema_cls

    def send(self, message: Any, properties: dict = {}) -> None:
        """Send a dataclass message."""
        # Convert dataclass to dict, excluding None values
        data_dict = dataclass_to_dict(message)
        # Serialize to JSON
        json_data = json.dumps(data_dict)
        # Send via Pulsar
        self._producer.send(json_data.encode('utf-8'), properties=properties)

    def flush(self) -> None:
        """Flush buffered messages."""
        self._producer.flush()

    def close(self) -> None:
        """Close the producer."""
        self._producer.close()


class PulsarBackendConsumer:
    """Pulsar-specific consumer implementation."""

    def __init__(self, pulsar_consumer, schema_cls):
        self._consumer = pulsar_consumer
        self._schema_cls = schema_cls

    def ensure_connected(self) -> None:
        """No-op for Pulsar.

        PulsarBackend.create_consumer() calls client.subscribe() which is
        synchronous and returns a fully-subscribed consumer, so the
        consumer is already ready by the time this object is constructed.
        Defined for parity with the BackendConsumer protocol used by
        Subscriber.start()'s readiness barrier."""
        pass

    def receive(self, timeout_millis: int = 2000) -> Message:
        """Receive a message. Raises TimeoutError if no message available."""
        try:
            pulsar_msg = self._consumer.receive(timeout_millis=timeout_millis)
        except _pulsar.Timeout:
            raise TimeoutError("No message received within timeout")
        return PulsarMessage(pulsar_msg, self._schema_cls)

    def acknowledge(self, message: Message) -> None:
        """Acknowledge a message."""
        if isinstance(message, PulsarMessage):
            self._consumer.acknowledge(message._msg)

    def negative_acknowledge(self, message: Message) -> None:
        """Negative acknowledge a message."""
        if isinstance(message, PulsarMessage):
            self._consumer.negative_acknowledge(message._msg)

    def unsubscribe(self) -> None:
        """Unsubscribe from the topic."""
        self._consumer.unsubscribe()

    def close(self) -> None:
        """Close the consumer."""
        self._consumer.close()


class PulsarBackend:
    """
    Pulsar backend implementation.

    Handles topic mapping, client management, and creation of Pulsar-specific
    producers and consumers.
    """

    def __init__(
        self, host: str, api_key: str = None, listener: str = None,
        admin_url: str = None,
    ):
        """
        Initialize Pulsar backend.

        Args:
            host: Pulsar broker URL (e.g., pulsar://localhost:6650)
            api_key: Optional API key for authentication
            listener: Optional listener name for multi-homed setups
            admin_url: Pulsar admin REST API URL (e.g., http://pulsar:8080)
        """
        self.host = host
        self.api_key = api_key
        self.listener = listener
        self.admin_url = admin_url

        # Create Pulsar client
        client_args = {'service_url': host}

        if listener:
            client_args['listener_name'] = listener

        if api_key:
            client_args['authentication'] = pulsar.AuthenticationToken(api_key)

        client_args['logger'] = pulsar.ConsoleLogger(
            _pulsar.LoggerLevel.Error
        )

        self.client = pulsar.Client(**client_args)
        logger.info(f"Pulsar client connected to {host}")

    def map_topic(self, queue_id: str) -> str:
        """
        Map queue identifier to Pulsar URI.

        Format: class:topicspace:topic
        Example: flow:tg:text-completion-request -> persistent://tg/flow/text-completion-request

        Args:
            queue_id: Queue identifier string or already-formatted Pulsar URI

        Returns:
            Pulsar topic URI
        """
        # If already a Pulsar URI, return as-is
        if '://' in queue_id:
            return queue_id

        parts = queue_id.split(':', 2)
        if len(parts) != 3:
            raise ValueError(
                f"Invalid queue format: {queue_id}, "
                f"expected class:topicspace:topic"
            )

        cls, topicspace, topic = parts

        # Map class to Pulsar persistence and namespace
        if cls == 'flow':
            persistence = 'persistent'
        elif cls in ('request', 'response'):
            persistence = 'non-persistent'
        elif cls == 'notify':
            persistence = 'non-persistent'
        else:
            raise ValueError(
                f"Invalid queue class: {cls}, "
                f"expected flow, request, response, or notify"
            )

        return f"{persistence}://{topicspace}/{cls}/{topic}"

    def create_producer(self, topic: str, schema: type, **options) -> BackendProducer:
        """
        Create a Pulsar producer.

        Args:
            topic: Generic topic format (qos/tenant/namespace/queue)
            schema: Dataclass type for messages
            **options: Backend-specific options (e.g., chunking_enabled)

        Returns:
            PulsarBackendProducer instance
        """
        pulsar_topic = self.map_topic(topic)

        producer_args = {
            'topic': pulsar_topic,
            'schema': pulsar.schema.BytesSchema(),  # We handle serialization ourselves
        }

        # Add optional parameters
        if 'chunking_enabled' in options:
            producer_args['chunking_enabled'] = options['chunking_enabled']

        pulsar_producer = self.client.create_producer(**producer_args)
        logger.debug(f"Created producer for topic: {pulsar_topic}")

        return PulsarBackendProducer(pulsar_producer, schema)

    def create_consumer(
        self,
        topic: str,
        subscription: str,
        schema: type,
        initial_position: str = 'latest',
        **options
    ) -> BackendConsumer:
        """
        Create a Pulsar consumer.

        Consumer type is derived from the topic's class prefix:
          - flow/request: Shared (competing consumers)
          - response/notify: Exclusive (per-subscriber)

        Args:
            topic: Queue identifier in class:topicspace:topic format
            subscription: Subscription name
            schema: Dataclass type for messages
            initial_position: 'earliest' or 'latest'
            **options: Backend-specific options

        Returns:
            PulsarBackendConsumer instance
        """
        pulsar_topic = self.map_topic(topic)

        # Extract class from topic for consumer type mapping
        cls = topic.split(':', 1)[0] if ':' in topic else 'flow'

        # Map initial position
        if initial_position == 'earliest':
            pos = pulsar.InitialPosition.Earliest
        else:
            pos = pulsar.InitialPosition.Latest

        # Map consumer type from class
        if cls in ('response', 'notify'):
            ctype = pulsar.ConsumerType.Exclusive
        else:
            ctype = pulsar.ConsumerType.Shared

        consumer_args = {
            'topic': pulsar_topic,
            'subscription_name': subscription,
            'schema': pulsar.schema.BytesSchema(),  # We handle deserialization ourselves
            'initial_position': pos,
            'consumer_type': ctype,
        }

        pulsar_consumer = self.client.subscribe(**consumer_args)
        logger.debug(f"Created consumer for topic: {pulsar_topic}, subscription: {subscription}")

        return PulsarBackendConsumer(pulsar_consumer, schema)

    def _admin_api_path(self, pulsar_uri: str) -> str:
        """
        Convert a Pulsar topic URI to an admin REST API path.

        persistent://tg/flow/triples-store:default:explain-flow
        -> /admin/v2/persistent/tg/flow/triples-store%3Adefault%3Aexplain-flow
        """
        scheme, rest = pulsar_uri.split('://', 1)
        tenant, namespace, topic = rest.split('/', 2)
        encoded_topic = urllib.parse.quote(topic, safe='')
        return f"/admin/v2/{scheme}/{tenant}/{namespace}/{encoded_topic}"

    def _admin_request(self, method, path):
        """
        Make a synchronous admin REST API request.

        Returns parsed JSON for GET, None for DELETE/PUT.
        Raises urllib.error.HTTPError for non-404 errors.
        404 is treated as success (idempotent deletion).
        """
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
        """
        Delete a persistent topic and all its subscriptions.

        Subscriptions must be removed first — Pulsar rejects topic
        deletion while subscriptions exist.  Force-deletes each
        subscription to disconnect any lingering consumers.
        """
        pulsar_uri = self.map_topic(topic)

        if pulsar_uri.startswith('non-persistent://'):
            return

        api_path = self._admin_api_path(pulsar_uri)

        try:
            subs = self._admin_request('GET', f"{api_path}/subscriptions")
        except Exception as e:
            logger.warning(f"Failed to list subscriptions for {topic}: {e}")
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
                    logger.info(
                        f"Deleted subscription {sub} from {topic}"
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
        """Check topic existence via admin API."""
        pulsar_uri = self.map_topic(topic)

        if pulsar_uri.startswith('non-persistent://'):
            return False

        api_path = self._admin_api_path(pulsar_uri)

        try:
            result = self._admin_request('GET', f"{api_path}/stats")
            return result is not None
        except Exception:
            return False

    async def create_topic(self, topic: str) -> None:
        """No-op — Pulsar auto-creates topics on first use."""
        pass

    async def delete_topic(self, topic: str) -> None:
        """
        Delete a persistent topic and all its subscriptions via
        the admin REST API.

        Called by the flow controller during deliberate flow deletion.
        Non-persistent topics are skipped. Idempotent.
        """
        if not self.admin_url:
            logger.warning(
                f"Cannot delete topic {topic}: "
                f"no admin URL configured"
            )
            return

        await asyncio.to_thread(self._delete_topic_sync, topic)

    async def topic_exists(self, topic: str) -> bool:
        """Check whether a persistent topic exists via the admin API."""
        if not self.admin_url:
            return True

        return await asyncio.to_thread(self._topic_exists_sync, topic)

    async def ensure_topic(self, topic: str) -> None:
        """No-op — Pulsar auto-creates topics on first use."""
        pass

    def close(self) -> None:
        """Close the Pulsar client."""
        self.client.close()
        logger.info("Pulsar client closed")
