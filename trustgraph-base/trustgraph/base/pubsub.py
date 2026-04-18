from __future__ import annotations

import os
import logging
from argparse import ArgumentParser
from typing import Any

logger = logging.getLogger(__name__)

# Default connection settings from environment
DEFAULT_PULSAR_HOST = os.getenv("PULSAR_HOST", 'pulsar://pulsar:6650')
DEFAULT_PULSAR_API_KEY = os.getenv("PULSAR_API_KEY", None)

DEFAULT_RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", 'rabbitmq')
DEFAULT_RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", '5672'))
DEFAULT_RABBITMQ_USERNAME = os.getenv("RABBITMQ_USERNAME", 'guest')
DEFAULT_RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", 'guest')
DEFAULT_RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", '/')

DEFAULT_KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", 'kafka:9092')
DEFAULT_KAFKA_PROTOCOL = os.getenv("KAFKA_SECURITY_PROTOCOL", 'PLAINTEXT')
DEFAULT_KAFKA_SASL_MECHANISM = os.getenv("KAFKA_SASL_MECHANISM", None)
DEFAULT_KAFKA_SASL_USERNAME = os.getenv("KAFKA_SASL_USERNAME", None)
DEFAULT_KAFKA_SASL_PASSWORD = os.getenv("KAFKA_SASL_PASSWORD", None)


def get_pubsub(**config: Any) -> Any:
    """
    Factory function to create a pub/sub backend based on configuration.

    Args:
        config: Configuration dictionary from command-line args.
                Key 'pubsub_backend' selects the backend (default: 'pulsar').

    Returns:
        Backend instance implementing the PubSubBackend protocol.
    """
    backend_type = config.get('pubsub_backend', 'pulsar')

    if backend_type == 'pulsar':
        from .pulsar_backend import PulsarBackend
        return PulsarBackend(
            host=config.get('pulsar_host', DEFAULT_PULSAR_HOST),
            api_key=config.get('pulsar_api_key', DEFAULT_PULSAR_API_KEY),
            listener=config.get('pulsar_listener'),
        )
    elif backend_type == 'rabbitmq':
        from .rabbitmq_backend import RabbitMQBackend
        return RabbitMQBackend(
            host=config.get('rabbitmq_host', DEFAULT_RABBITMQ_HOST),
            port=config.get('rabbitmq_port', DEFAULT_RABBITMQ_PORT),
            username=config.get('rabbitmq_username', DEFAULT_RABBITMQ_USERNAME),
            password=config.get('rabbitmq_password', DEFAULT_RABBITMQ_PASSWORD),
            vhost=config.get('rabbitmq_vhost', DEFAULT_RABBITMQ_VHOST),
        )
    elif backend_type == 'kafka':
        from .kafka_backend import KafkaBackend
        return KafkaBackend(
            bootstrap_servers=config.get(
                'kafka_bootstrap_servers', DEFAULT_KAFKA_BOOTSTRAP,
            ),
            security_protocol=config.get(
                'kafka_security_protocol', DEFAULT_KAFKA_PROTOCOL,
            ),
            sasl_mechanism=config.get(
                'kafka_sasl_mechanism', DEFAULT_KAFKA_SASL_MECHANISM,
            ),
            sasl_username=config.get(
                'kafka_sasl_username', DEFAULT_KAFKA_SASL_USERNAME,
            ),
            sasl_password=config.get(
                'kafka_sasl_password', DEFAULT_KAFKA_SASL_PASSWORD,
            ),
        )
    else:
        raise ValueError(f"Unknown pub/sub backend: {backend_type}")


STANDALONE_PULSAR_HOST = 'pulsar://localhost:6650'


def add_pubsub_args(parser: ArgumentParser, standalone: bool = False) -> None:
    """Add pub/sub CLI arguments to an argument parser.

    Args:
        parser: argparse.ArgumentParser
        standalone: If True, default host is localhost (for CLI tools
                    that run outside containers)
    """
    pulsar_host = STANDALONE_PULSAR_HOST if standalone else DEFAULT_PULSAR_HOST
    pulsar_listener = 'localhost' if standalone else None
    rabbitmq_host = 'localhost' if standalone else DEFAULT_RABBITMQ_HOST
    kafka_bootstrap = 'localhost:9092' if standalone else DEFAULT_KAFKA_BOOTSTRAP

    parser.add_argument(
        '--pubsub-backend',
        default=os.getenv('PUBSUB_BACKEND', 'pulsar'),
        help='Pub/sub backend (default: pulsar, env: PUBSUB_BACKEND)',
    )

    # Pulsar options
    parser.add_argument(
        '-p', '--pulsar-host',
        default=pulsar_host,
        help=f'Pulsar host (default: {pulsar_host})',
    )

    parser.add_argument(
        '--pulsar-api-key',
        default=DEFAULT_PULSAR_API_KEY,
        help='Pulsar API key',
    )

    parser.add_argument(
        '--pulsar-listener',
        default=pulsar_listener,
        help=f'Pulsar listener (default: {pulsar_listener or "none"})',
    )

    # RabbitMQ options
    parser.add_argument(
        '--rabbitmq-host',
        default=rabbitmq_host,
        help=f'RabbitMQ host (default: {rabbitmq_host})',
    )

    parser.add_argument(
        '--rabbitmq-port',
        type=int,
        default=DEFAULT_RABBITMQ_PORT,
        help=f'RabbitMQ port (default: {DEFAULT_RABBITMQ_PORT})',
    )

    parser.add_argument(
        '--rabbitmq-username',
        default=DEFAULT_RABBITMQ_USERNAME,
        help='RabbitMQ username',
    )

    parser.add_argument(
        '--rabbitmq-password',
        default=DEFAULT_RABBITMQ_PASSWORD,
        help='RabbitMQ password',
    )

    parser.add_argument(
        '--rabbitmq-vhost',
        default=DEFAULT_RABBITMQ_VHOST,
        help=f'RabbitMQ vhost (default: {DEFAULT_RABBITMQ_VHOST})',
    )

    # Kafka options
    parser.add_argument(
        '--kafka-bootstrap-servers',
        default=kafka_bootstrap,
        help=f'Kafka bootstrap servers (default: {kafka_bootstrap})',
    )

    parser.add_argument(
        '--kafka-security-protocol',
        default=DEFAULT_KAFKA_PROTOCOL,
        help=f'Kafka security protocol (default: {DEFAULT_KAFKA_PROTOCOL})',
    )

    parser.add_argument(
        '--kafka-sasl-mechanism',
        default=DEFAULT_KAFKA_SASL_MECHANISM,
        help='Kafka SASL mechanism',
    )

    parser.add_argument(
        '--kafka-sasl-username',
        default=DEFAULT_KAFKA_SASL_USERNAME,
        help='Kafka SASL username',
    )

    parser.add_argument(
        '--kafka-sasl-password',
        default=DEFAULT_KAFKA_SASL_PASSWORD,
        help='Kafka SASL password',
    )
