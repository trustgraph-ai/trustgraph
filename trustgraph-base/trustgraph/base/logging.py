
"""
Centralized logging configuration for TrustGraph server-side components.

This module provides standardized logging setup across all TrustGraph services,
ensuring consistent log formats, levels, and command-line arguments.

Supports dual output to console and Loki for centralized log aggregation.
"""

import contextvars
import logging
import logging.handlers
from queue import Queue
import os


# The current processor id for this task context.  Read by
# _ProcessorIdFilter to stamp every LogRecord with its owning
# processor, and read by logging_loki's emitter via record.tags
# to label log lines in Loki.  ContextVar so asyncio subtasks
# inherit their parent supervisor's processor id automatically.
current_processor_id = contextvars.ContextVar(
    "current_processor_id", default="unknown"
)


def set_processor_id(pid):
    """Set the processor id for the current task context.

    All subsequent log records emitted from this task — and any
    asyncio tasks spawned from it — will be tagged with this id
    in the console format and in Loki labels.
    """
    current_processor_id.set(pid)


class _ProcessorIdFilter(logging.Filter):
    """Stamps every LogRecord with processor_id from the contextvar.

    Attaches two fields to each record:
        record.processor_id — used by the console format string
        record.tags         — merged into Loki labels by logging_loki's
                              emitter (it reads record.tags and combines
                              with the handler's static tags)
    """

    def filter(self, record):
        pid = current_processor_id.get()
        record.processor_id = pid
        existing = getattr(record, "tags", None) or {}
        record.tags = {**existing, "processor": pid}
        return True


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

        try:
            from logging_loki import LokiHandler

            # Create Loki handler with optional authentication.  The
            # processor label is NOT baked in here — it's stamped onto
            # each record by _ProcessorIdFilter reading the task-local
            # contextvar, and logging_loki's emitter reads record.tags
            # to build per-record Loki labels.
            loki_handler_kwargs = {
                'url': loki_url,
                'version': "1",
            }

            if loki_username and loki_password:
                loki_handler_kwargs['auth'] = (loki_username, loki_password)

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

    # Configure logging with all handlers.  The processor id comes
    # from _ProcessorIdFilter (via contextvar) and is injected into
    # each record as record.processor_id.  The format string reads
    # that attribute on every emit.
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(processor_id)s - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True  # Force reconfiguration if already configured
    )

    # Attach the processor-id filter to every handler so all records
    # passing through any sink get stamped (console, queue→loki,
    # future handlers).  Filters on handlers run regardless of which
    # logger originated the record, so logs from pika, cassandra,
    # processor code, etc. all pass through it.
    processor_filter = _ProcessorIdFilter()
    for h in handlers:
        h.addFilter(processor_filter)

    # Seed the contextvar from --id if one was supplied.  In group
    # mode --id isn't present; the processor_group supervisor sets
    # it per task.  In standalone mode AsyncProcessor.launch provides
    # it via argparse default.
    if args.get('id'):
        set_processor_id(args['id'])

    # Silence noisy third-party library loggers.  These emit INFO-level
    # chatter (connection churn, channel open/close, driver warnings) that
    # drowns the useful signal and can't be attributed to a specific
    # processor anyway.  WARNING and above still propagate.
    for noisy in (
        'pika',
        'cassandra',
        'urllib3',
        'urllib3.connectionpool',
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {log_level}")
    if loki_enabled and queue_listener:
        logger.info(f"Loki logging enabled: {loki_url}")
    elif loki_enabled:
        logger.warning("Loki logging requested but not available")
