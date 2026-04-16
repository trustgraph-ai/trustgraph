"""
Pulsar backend implementation for pub/sub abstraction.

This module provides a Pulsar-specific implementation of the backend interfaces,
handling topic mapping, serialization, and Pulsar client management.
"""

import pulsar
import _pulsar
import json
import logging
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

    def __init__(self, host: str, api_key: str = None, listener: str = None):
        """
        Initialize Pulsar backend.

        Args:
            host: Pulsar broker URL (e.g., pulsar://localhost:6650)
            api_key: Optional API key for authentication
            listener: Optional listener name for multi-homed setups
        """
        self.host = host
        self.api_key = api_key
        self.listener = listener

        # Create Pulsar client
        client_args = {'service_url': host}

        if listener:
            client_args['listener_name'] = listener

        if api_key:
            client_args['authentication'] = pulsar.AuthenticationToken(api_key)

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

    async def create_queue(self, topic: str, subscription: str) -> None:
        """No-op — Pulsar auto-creates topics on first use.
        TODO: Use admin REST API for explicit persistent topic creation."""
        pass

    async def delete_queue(self, topic: str, subscription: str) -> None:
        """No-op — to be replaced with admin REST API calls.
        TODO: Delete subscription and persistent topic via admin API."""
        pass

    async def queue_exists(self, topic: str, subscription: str) -> bool:
        """Returns True — Pulsar auto-creates on subscribe.
        TODO: Use admin REST API for actual existence check."""
        return True

    async def ensure_queue(self, topic: str, subscription: str) -> None:
        """No-op — Pulsar auto-creates topics on first use.
        TODO: Use admin REST API for explicit creation."""
        pass

    def close(self) -> None:
        """Close the Pulsar client."""
        self.client.close()
        logger.info("Pulsar client closed")
