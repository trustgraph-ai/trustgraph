
import os
import logging

logger = logging.getLogger(__name__)

# Default connection settings from environment
DEFAULT_PULSAR_HOST = os.getenv("PULSAR_HOST", 'pulsar://pulsar:6650')
DEFAULT_PULSAR_API_KEY = os.getenv("PULSAR_API_KEY", None)


def get_pubsub(**config):
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
    else:
        raise ValueError(f"Unknown pub/sub backend: {backend_type}")


STANDALONE_PULSAR_HOST = 'pulsar://localhost:6650'


def add_pubsub_args(parser, standalone=False):
    """Add pub/sub CLI arguments to an argument parser.

    Args:
        parser: argparse.ArgumentParser
        standalone: If True, default host is localhost (for CLI tools
                    that run outside containers)
    """
    host = STANDALONE_PULSAR_HOST if standalone else DEFAULT_PULSAR_HOST
    listener_default = 'localhost' if standalone else None

    parser.add_argument(
        '--pubsub-backend',
        default=os.getenv('PUBSUB_BACKEND', 'pulsar'),
        help='Pub/sub backend (default: pulsar, env: PUBSUB_BACKEND)',
    )

    parser.add_argument(
        '-p', '--pulsar-host',
        default=host,
        help=f'Pulsar host (default: {host})',
    )

    parser.add_argument(
        '--pulsar-api-key',
        default=DEFAULT_PULSAR_API_KEY,
        help='Pulsar API key',
    )

    parser.add_argument(
        '--pulsar-listener',
        default=listener_default,
        help=f'Pulsar listener (default: {listener_default or "none"})',
    )
