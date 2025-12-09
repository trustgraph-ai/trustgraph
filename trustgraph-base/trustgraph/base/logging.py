
"""
Centralized logging configuration for TrustGraph server-side components.

This module provides standardized logging setup across all TrustGraph services,
ensuring consistent log formats, levels, and command-line arguments.
"""

import logging


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


def setup_logging(args):
    """
    Configure logging from parsed command-line arguments.

    Sets up logging with a standardized format and output to stdout.
    This should be called early in application startup, before any
    logging calls are made.

    Args:
        args: Dictionary of parsed arguments (typically from vars(args))
              Must contain 'log_level' key
    """
    log_level = args.get('log_level', 'INFO')

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {log_level}")
