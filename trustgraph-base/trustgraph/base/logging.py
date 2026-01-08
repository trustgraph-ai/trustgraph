
"""
Centralized logging configuration for TrustGraph server-side components.

This module provides standardized logging setup across all TrustGraph services,
ensuring consistent log formats, levels, and command-line arguments.

Supports dual output to console and Loki for centralized log aggregation.
"""

import logging
import logging.handlers
from queue import Queue
import os


def add_logging_args(parser):
    """
    Add standard logging arguments to an argument parser.

    Args:
        parser: argparse.ArgumentParser instance to add arguments to
    """
    parser.add_argument(
        '-l', '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Log level (default: INFO)'
    )

    parser.add_argument(
        '--loki-enabled',
        action='store_true',
        default=True,
        help='Enable Loki logging (default: True)'
    )

    parser.add_argument(
        '--no-loki-enabled',
        dest='loki_enabled',
        action='store_false',
        help='Disable Loki logging'
    )

    parser.add_argument(
        '--loki-url',
        default=os.getenv('LOKI_URL', 'http://loki:3100/loki/api/v1/push'),
        help='Loki push URL (default: http://loki:3100/loki/api/v1/push)'
    )

    parser.add_argument(
        '--loki-username',
        default=os.getenv('LOKI_USERNAME', None),
        help='Loki username for authentication (optional)'
    )

    parser.add_argument(
        '--loki-password',
        default=os.getenv('LOKI_PASSWORD', None),
        help='Loki password for authentication (optional)'
    )


def setup_logging(args):
    """
    Configure logging from parsed command-line arguments.

    Sets up logging with a standardized format and output to stdout.
    Optionally enables Loki integration for centralized log aggregation.

    This should be called early in application startup, before any
    logging calls are made.

    Args:
        args: Dictionary of parsed arguments (typically from vars(args))
              Must contain 'log_level' key, optional Loki configuration
    """
    log_level = args.get('log_level', 'INFO')
    loki_enabled = args.get('loki_enabled', True)

    # Build list of handlers starting with console
    handlers = [logging.StreamHandler()]

    # Add Loki handler if enabled
    queue_listener = None
    if loki_enabled:
        loki_url = args.get('loki_url', 'http://loki:3100/loki/api/v1/push')
        loki_username = args.get('loki_username')
        loki_password = args.get('loki_password')
        processor_id = args.get('id')  # Processor identity (e.g., "config-svc", "text-completion")

        try:
            from logging_loki import LokiHandler

            # Create Loki handler with optional authentication and processor label
            loki_handler_kwargs = {
                'url': loki_url,
                'version': "1",
            }

            if loki_username and loki_password:
                loki_handler_kwargs['auth'] = (loki_username, loki_password)

            # Add processor label if available (for consistency with Prometheus metrics)
            if processor_id:
                loki_handler_kwargs['tags'] = {'processor': processor_id}

            loki_handler = LokiHandler(**loki_handler_kwargs)

            # Wrap in QueueHandler for non-blocking operation
            log_queue = Queue(maxsize=500)
            queue_handler = logging.handlers.QueueHandler(log_queue)
            handlers.append(queue_handler)

            # Start QueueListener in background thread
            queue_listener = logging.handlers.QueueListener(
                log_queue,
                loki_handler,
                respect_handler_level=True
            )
            queue_listener.start()

            # Store listener reference for potential cleanup
            # (attached to root logger for access if needed)
            logging.getLogger().loki_queue_listener = queue_listener

        except ImportError:
            # Graceful degradation if python-logging-loki not installed
            print("WARNING: python-logging-loki not installed, Loki logging disabled")
            print("Install with: pip install python-logging-loki")
        except Exception as e:
            # Graceful degradation if Loki connection fails
            print(f"WARNING: Failed to setup Loki logging: {e}")
            print("Continuing with console-only logging")

    # Get processor ID for log formatting (use 'unknown' if not available)
    processor_id = args.get('id', 'unknown')

    # Configure logging with all handlers
    # Use processor ID as the primary identifier in logs
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=f'%(asctime)s - {processor_id} - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True  # Force reconfiguration if already configured
    )

    # Prevent recursive logging from Loki's HTTP client
    if loki_enabled and queue_listener:
        # Disable urllib3 logging to prevent infinite loop
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {log_level}")
    if loki_enabled and queue_listener:
        logger.info(f"Loki logging enabled: {loki_url}")
    elif loki_enabled:
        logger.warning("Loki logging requested but not available")
