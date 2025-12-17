"""
Backend abstraction interfaces for pub/sub systems.

This module defines Protocol classes that all pub/sub backends must implement,
allowing TrustGraph to work with different messaging systems (Pulsar, MQTT, Kafka, etc.)
"""

from typing import Protocol, Any, runtime_checkable


@runtime_checkable
class Message(Protocol):
    """Protocol for a received message."""

    def value(self) -> Any:
        """
        Get the deserialized message content.

        Returns:
            Dataclass instance representing the message
        """
        ...

    def properties(self) -> dict:
        """
        Get message properties/metadata.

        Returns:
            Dictionary of message properties
        """
        ...


@runtime_checkable
class BackendProducer(Protocol):
    """Protocol for backend-specific producer."""

    def send(self, message: Any, properties: dict = {}) -> None:
        """
        Send a message (dataclass instance) with optional properties.

        Args:
            message: Dataclass instance to send
            properties: Optional metadata properties
        """
        ...

    def flush(self) -> None:
        """Flush any buffered messages."""
        ...

    def close(self) -> None:
        """Close the producer."""
        ...


@runtime_checkable
class BackendConsumer(Protocol):
    """Protocol for backend-specific consumer."""

    def receive(self, timeout_millis: int = 2000) -> Message:
        """
        Receive a message from the topic.

        Args:
            timeout_millis: Timeout in milliseconds

        Returns:
            Message object

        Raises:
            TimeoutError: If no message received within timeout
        """
        ...

    def acknowledge(self, message: Message) -> None:
        """
        Acknowledge successful processing of a message.

        Args:
            message: The message to acknowledge
        """
        ...

    def negative_acknowledge(self, message: Message) -> None:
        """
        Negative acknowledge - triggers redelivery.

        Args:
            message: The message to negatively acknowledge
        """
        ...

    def unsubscribe(self) -> None:
        """Unsubscribe from the topic."""
        ...

    def close(self) -> None:
        """Close the consumer."""
        ...


@runtime_checkable
class PubSubBackend(Protocol):
    """Protocol defining the interface all pub/sub backends must implement."""

    def create_producer(self, topic: str, schema: type, **options) -> BackendProducer:
        """
        Create a producer for a topic.

        Args:
            topic: Generic topic format (qos/tenant/namespace/queue)
            schema: Dataclass type for messages
            **options: Backend-specific options (e.g., chunking_enabled)

        Returns:
            Backend-specific producer instance
        """
        ...

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
        Create a consumer for a topic.

        Args:
            topic: Generic topic format (qos/tenant/namespace/queue)
            subscription: Subscription/consumer group name
            schema: Dataclass type for messages
            initial_position: 'earliest' or 'latest' (some backends may ignore)
            consumer_type: 'shared', 'exclusive', 'failover' (some backends may ignore)
            **options: Backend-specific options

        Returns:
            Backend-specific consumer instance
        """
        ...

    def close(self) -> None:
        """Close the backend connection."""
        ...
