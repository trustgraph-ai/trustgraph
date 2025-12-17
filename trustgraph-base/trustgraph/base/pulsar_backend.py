"""
Pulsar backend implementation for pub/sub abstraction.

This module provides a Pulsar-specific implementation of the backend interfaces,
handling topic mapping, serialization, and Pulsar client management.
"""

import pulsar
import _pulsar
import json
import logging
from dataclasses import asdict, is_dataclass
from typing import Any

from .backend import PubSubBackend, BackendProducer, BackendConsumer, Message

logger = logging.getLogger(__name__)


def dataclass_to_dict(obj: Any) -> dict:
    """
    Recursively convert a dataclass to a dictionary, handling None values.

    None values are excluded from the dictionary (not serialized).
    """
    if obj is None:
        return None

    if is_dataclass(obj):
        result = {}
        for key, value in asdict(obj).items():
            if value is not None:
                if is_dataclass(value):
                    result[key] = dataclass_to_dict(value)
                elif isinstance(value, list):
                    result[key] = [dataclass_to_dict(item) if is_dataclass(item) else item for item in value]
                elif isinstance(value, dict):
                    result[key] = {k: dataclass_to_dict(v) if is_dataclass(v) else v for k, v in value.items()}
                else:
                    result[key] = value
        return result
    return obj


def dict_to_dataclass(data: dict, cls: type) -> Any:
    """
    Convert a dictionary back to a dataclass instance.

    Handles nested dataclasses and missing fields.
    """
    if data is None:
        return None

    if not is_dataclass(cls):
        return data

    # Get field types from the dataclass
    field_types = {f.name: f.type for f in cls.__dataclass_fields__.values()}
    kwargs = {}

    for key, value in data.items():
        if key in field_types:
            field_type = field_types[key]

            # Handle Optional types (type | None)
            if hasattr(field_type, '__args__'):
                # Get the non-None type from Union
                actual_type = next((t for t in field_type.__args__ if t is not type(None)), field_type)
            else:
                actual_type = field_type

            # Recursively convert nested dataclasses
            if is_dataclass(actual_type) and isinstance(value, dict):
                kwargs[key] = dict_to_dataclass(value, actual_type)
            elif hasattr(actual_type, '__origin__'):
                # Handle generic types like list[T] or dict[K, V]
                if actual_type.__origin__ == list:
                    item_type = actual_type.__args__[0] if actual_type.__args__ else None
                    if item_type and is_dataclass(item_type):
                        kwargs[key] = [dict_to_dataclass(item, item_type) for item in value]
                    else:
                        kwargs[key] = value
                else:
                    kwargs[key] = value
            else:
                kwargs[key] = value

    return cls(**kwargs)


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

    def receive(self, timeout_millis: int = 2000) -> Message:
        """Receive a message."""
        pulsar_msg = self._consumer.receive(timeout_millis=timeout_millis)
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

    def map_topic(self, generic_topic: str) -> str:
        """
        Map generic topic format to Pulsar URI.

        Format: qos/tenant/namespace/queue
        Example: q1/tg/flow/my-queue -> persistent://tg/flow/my-queue

        Args:
            generic_topic: Generic topic string

        Returns:
            Pulsar topic URI
        """
        parts = generic_topic.split('/', 3)
        if len(parts) != 4:
            raise ValueError(f"Invalid topic format: {generic_topic}, expected qos/tenant/namespace/queue")

        qos, tenant, namespace, queue = parts

        # Map QoS to persistence
        if qos == 'q0':
            persistence = 'non-persistent'
        elif qos in ['q1', 'q2']:
            persistence = 'persistent'
        else:
            raise ValueError(f"Invalid QoS level: {qos}, expected q0, q1, or q2")

        return f"{persistence}://{tenant}/{namespace}/{queue}"

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
        consumer_type: str = 'shared',
        **options
    ) -> BackendConsumer:
        """
        Create a Pulsar consumer.

        Args:
            topic: Generic topic format (qos/tenant/namespace/queue)
            subscription: Subscription name
            schema: Dataclass type for messages
            initial_position: 'earliest' or 'latest'
            consumer_type: 'shared', 'exclusive', or 'failover'
            **options: Backend-specific options

        Returns:
            PulsarBackendConsumer instance
        """
        pulsar_topic = self.map_topic(topic)

        # Map initial position
        if initial_position == 'earliest':
            pos = pulsar.InitialPosition.Earliest
        else:
            pos = pulsar.InitialPosition.Latest

        # Map consumer type
        if consumer_type == 'exclusive':
            ctype = pulsar.ConsumerType.Exclusive
        elif consumer_type == 'failover':
            ctype = pulsar.ConsumerType.Failover
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

    def close(self) -> None:
        """Close the Pulsar client."""
        self.client.close()
        logger.info("Pulsar client closed")
