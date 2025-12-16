
import os
import pulsar
import _pulsar
import uuid
from pulsar.schema import JsonSchema
import logging

from .. log_level import LogLevel
from .pulsar_backend import PulsarBackend

logger = logging.getLogger(__name__)


def get_pubsub(**config):
    """
    Factory function to create a pub/sub backend based on configuration.

    Args:
        config: Configuration dictionary from command-line args
                Must include 'pubsub_backend' key

    Returns:
        Backend instance (PulsarBackend, MQTTBackend, etc.)

    Example:
        backend = get_pubsub(
            pubsub_backend='pulsar',
            pulsar_host='pulsar://localhost:6650'
        )
    """
    backend_type = config.get('pubsub_backend', 'pulsar')

    if backend_type == 'pulsar':
        return PulsarBackend(
            host=config.get('pulsar_host', PulsarClient.default_pulsar_host),
            api_key=config.get('pulsar_api_key', PulsarClient.default_pulsar_api_key),
            listener=config.get('pulsar_listener'),
        )
    elif backend_type == 'mqtt':
        # TODO: Implement MQTT backend
        raise NotImplementedError("MQTT backend not yet implemented")
    else:
        raise ValueError(f"Unknown pub/sub backend: {backend_type}")


class PulsarClient:

    default_pulsar_host = os.getenv("PULSAR_HOST", 'pulsar://pulsar:6650')
    default_pulsar_api_key = os.getenv("PULSAR_API_KEY", None)

    def __init__(self, **params):

        self.client = None

        pulsar_host = params.get("pulsar_host", self.default_pulsar_host)
        pulsar_listener = params.get("pulsar_listener", None)
        pulsar_api_key = params.get(
            "pulsar_api_key",
            self.default_pulsar_api_key
        )
        # Hard-code Pulsar logging to ERROR level to minimize noise

        self.pulsar_host = pulsar_host
        self.pulsar_api_key = pulsar_api_key

        if pulsar_api_key:
            auth = pulsar.AuthenticationToken(pulsar_api_key)
            self.client = pulsar.Client(
                pulsar_host,
                authentication=auth,
                logger=pulsar.ConsoleLogger(_pulsar.LoggerLevel.Error)
            )
        else:
            self.client = pulsar.Client(
                pulsar_host,
                listener_name=pulsar_listener,
                logger=pulsar.ConsoleLogger(_pulsar.LoggerLevel.Error)
            )

        self.pulsar_listener = pulsar_listener

    def close(self):
        self.client.close()

    def __del__(self):

        if hasattr(self, "client"):
            if self.client:
                self.client.close()

    @staticmethod
    def add_args(parser):

        parser.add_argument(
            '-p', '--pulsar-host',
            default=__class__.default_pulsar_host,
            help=f'Pulsar host (default: {__class__.default_pulsar_host})',
        )
        
        parser.add_argument(
            '--pulsar-api-key',
            default=__class__.default_pulsar_api_key,
            help=f'Pulsar API key',
        )

        parser.add_argument(
            '--pulsar-listener',
            help=f'Pulsar listener (default: none)',
        )
