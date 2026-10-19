
"""
Centralized logging configuration for TrustGraph server-side components.

This module provides standardized logging setup across all TrustGraph services,
ensuring consistent log formats, levels, and command-line arguments.

Supports dual output to console and Loki for centralized log aggregation.
"""

import contextvars
import logging
import logging.handlers
import sys
import time
import uuid
from argparse import ArgumentParser
from queue import Queue
from typing import Any
import os

import requests


current_processor_id = contextvars.ContextVar(
    "current_processor_id", default="unknown"
)


def set_processor_id(pid):
    current_processor_id.set(pid)


class _ProcessorIdFilter(logging.Filter):

    def filter(self, record):
        pid = current_processor_id.get()
        record.processor_id = pid
        return True


LEVEL_TO_SEVERITY = {
    "CRITICAL": "critical",
    "ERROR": "error",
    "WARNING": "warning",
    "INFO": "info",
    "DEBUG": "debug",
}


class _LokiHandler(logging.Handler):

    INITIAL_BACKOFF = 60
    MAX_BACKOFF = 300
    STATUS_INTERVAL = 300

    def __init__(self, url, tags=None, auth=None):
        super().__init__()
        self.url = url
        self.tags = tags or {}
        self.auth = auth
        self.session = requests.Session()
        if auth:
            self.session.auth = auth

        self.degraded = False
        self.backoff = self.INITIAL_BACKOFF
        self.retry_at = 0
        self.dropped = 0
        self.degraded_since = 0
        self.last_status = 0

    def _push(self, record):

        labels = {
            **self.tags,
            "severity": LEVEL_TO_SEVERITY.get(
                record.levelname, "info"
            ),
            "processor": getattr(record, "processor_id", "unknown"),
        }

        ts = str(int(record.created * 1e9))
        line = self.format(record)

        payload = {
            "streams": [
                {
                    "stream": labels,
                    "values": [[ts, line]],
                }
            ]
        }

        resp = self.session.post(
            self.url,
            json=payload,
            timeout=5,
        )
        resp.raise_for_status()

    def _enter_degraded(self, now):
        self.degraded = True
        self.degraded_since = now
        self.last_status = now
        self.retry_at = now + self.backoff
        self.dropped = 1
        sys.stderr.write(
            f"Loki logging degraded, retrying in "
            f"{int(self.backoff)}s\n"
        )

    def emit(self, record):

        now = time.monotonic()

        if self.degraded:
            if now < self.retry_at:
                self.dropped += 1
                if now - self.last_status >= self.STATUS_INTERVAL:
                    self.last_status = now
                    elapsed = now - self.degraded_since
                    m, s = divmod(int(elapsed), 60)
                    sys.stderr.write(
                        f"Loki logging degraded: {self.dropped} messages "
                        f"dropped ({m}m{s:02d}s, backoff: "
                        f"{int(self.backoff)}s)\n"
                    )
                return

            try:
                self._push(record)
            except Exception:
                self.dropped += 1
                self.backoff = min(self.backoff * 2, self.MAX_BACKOFF)
                self.retry_at = now + self.backoff
                return

            elapsed = now - self.degraded_since
            m, s = divmod(int(elapsed), 60)
            sys.stderr.write(
                f"Loki logging restored (dropped {self.dropped} "
                f"messages over {m}m{s:02d}s)\n"
            )
            self.degraded = False
            self.backoff = self.INITIAL_BACKOFF
            self.dropped = 0
            self.degraded_since = 0
            self.last_status = 0
            return

        try:
            self._push(record)
        except Exception:
            self._enter_degraded(now)


def add_logging_args(parser: ArgumentParser) -> None:

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


def setup_logging(args: dict[str, Any]) -> None:

    log_level = args.get('log_level', 'INFO')
    loki_enabled = args.get('loki_enabled', True)

    handlers = [logging.StreamHandler()]

    queue_listener = None
    if loki_enabled:
        loki_url = args.get('loki_url', 'http://loki:3100/loki/api/v1/push')
        loki_username = args.get('loki_username')
        loki_password = args.get('loki_password')

        try:
            instance_id = str(uuid.uuid4())[:8]

            auth = None
            if loki_username and loki_password:
                auth = (loki_username, loki_password)

            loki_handler = _LokiHandler(
                url=loki_url,
                tags={"instance": instance_id},
                auth=auth,
            )

            log_queue = Queue(maxsize=500)
            queue_handler = logging.handlers.QueueHandler(log_queue)
            handlers.append(queue_handler)

            queue_listener = logging.handlers.QueueListener(
                log_queue,
                loki_handler,
                respect_handler_level=True,
            )
            queue_listener.start()

            logging.getLogger().loki_queue_listener = queue_listener

        except Exception as e:
            sys.stderr.write(f"WARNING: Failed to setup Loki logging: {e}\n")
            sys.stderr.write("Continuing with console-only logging\n")

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(processor_id)s - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True,
    )

    processor_filter = _ProcessorIdFilter()
    for h in handlers:
        h.addFilter(processor_filter)

    if args.get('id'):
        set_processor_id(args['id'])

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
