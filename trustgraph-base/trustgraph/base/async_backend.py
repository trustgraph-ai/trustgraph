"""
Async backend abstraction interfaces for pub/sub systems.

These protocols replace the synchronous protocols in backend.py.
All methods that perform broker I/O are async. The backend handles
its own threading internally — the application layer never creates
threads for broker operations.
"""

from typing import Protocol, Any, runtime_checkable


@runtime_checkable
class Message(Protocol):
    """Protocol for a received message."""

    def value(self) -> Any:
        """Get the deserialized message content."""
        ...

    def properties(self) -> dict:
        """Get message properties/metadata."""
        ...


@runtime_checkable
class AsyncBackendConsumer(Protocol):
    """Protocol for an async backend consumer.

    receive() is awaitable with no timeout — shutdown is signalled
    by cancelling the awaiting task. acknowledge() and
    negative_acknowledge() are async so that backends with threading
    constraints (e.g. RabbitMQ) can route ack calls internally.
    """

    async def receive(self) -> Message:
        """Await the next message.

        Does not time out. Shutdown is signalled by cancelling the
        awaiting task.
        """
        ...

    async def acknowledge(self, message: Message) -> None:
        """Acknowledge successful processing of a message."""
        ...

    async def negative_acknowledge(self, message: Message) -> None:
        """Negative acknowledge — triggers redelivery."""
        ...

    async def close(self) -> None:
        """Close the consumer and release broker resources."""
        ...


@runtime_checkable
class AsyncBackendProducer(Protocol):
    """Protocol for an async backend producer.

    send() is async so the backend can perform broker I/O without
    blocking the event loop.
    """

    async def send(self, message: Any, properties: dict = {}) -> None:
        """Send a message with optional properties."""
        ...

    async def close(self) -> None:
        """Flush pending messages and close the producer."""
        ...


@runtime_checkable
class AsyncPubSubBackend(Protocol):
    """Protocol for an async pub/sub backend.

    Factory methods are async since they perform broker roundtrips.
    """

    async def create_consumer(
        self, topic: str, subscription: str, schema: type,
        initial_position: str = 'latest', **options,
    ) -> AsyncBackendConsumer:
        """Create a consumer subscribed to a topic.

        Returns only when the subscription is active and ready to
        receive messages.
        """
        ...

    async def create_producer(
        self, topic: str, schema: type, **options,
    ) -> AsyncBackendProducer:
        """Create a producer bound to a topic.

        Returns only when the producer is ready to send.
        """
        ...

    async def create_topic(self, topic: str) -> None:
        """Create broker-side resources for a logical topic."""
        ...

    async def delete_topic(self, topic: str) -> None:
        """Delete a topic and discard any in-flight messages."""
        ...

    async def topic_exists(self, topic: str) -> bool:
        """Check whether a topic exists."""
        ...

    async def ensure_topic(self, topic: str) -> None:
        """Ensure a topic exists, creating it if necessary."""
        ...

    async def close(self) -> None:
        """Close the backend and release all resources."""
        ...
