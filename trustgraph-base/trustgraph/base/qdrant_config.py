
import os
import argparse
from typing import Optional, Any, Tuple


def get_qdrant_defaults() -> dict:
    return {
        'url': os.getenv('QDRANT_URL', 'http://localhost:6333'),
        'api_key': os.getenv('QDRANT_API_KEY'),
        'replication_factor': int(os.getenv('QDRANT_REPLICATION_FACTOR', '1')),
        'shard_number': int(os.getenv('QDRANT_SHARD_NUMBER', '1')),
    }


def add_qdrant_args(parser: argparse.ArgumentParser) -> None:
    defaults = get_qdrant_defaults()

    url_help = f"Qdrant URL (default: {defaults['url']})"
    if 'QDRANT_URL' in os.environ:
        url_help += " [from QDRANT_URL]"

    api_key_help = "Qdrant API key"
    if defaults['api_key']:
        api_key_help += " (default: <set>)"
        if 'QDRANT_API_KEY' in os.environ:
            api_key_help += " [from QDRANT_API_KEY]"

    replication_help = f"Qdrant collection replication factor (default: {defaults['replication_factor']})"
    if 'QDRANT_REPLICATION_FACTOR' in os.environ:
        replication_help += " [from QDRANT_REPLICATION_FACTOR]"

    shard_help = f"Qdrant collection shard number (default: {defaults['shard_number']})"
    if 'QDRANT_SHARD_NUMBER' in os.environ:
        shard_help += " [from QDRANT_SHARD_NUMBER]"

    parser.add_argument(
        '--store-uri',
        default=defaults['url'],
        help=url_help,
    )

    parser.add_argument(
        '--api-key',
        default=defaults['api_key'],
        help=api_key_help,
    )

    parser.add_argument(
        '--qdrant-replication-factor',
        type=int,
        default=defaults['replication_factor'],
        help=replication_help,
    )

    parser.add_argument(
        '--qdrant-shard-number',
        type=int,
        default=defaults['shard_number'],
        help=shard_help,
    )


def resolve_qdrant_config(
    args: Optional[Any] = None,
    url: Optional[str] = None,
    api_key: Optional[str] = None,
    replication_factor: Optional[int] = None,
    shard_number: Optional[int] = None,
) -> Tuple[str, Optional[str], int, int]:
    if args is not None:
        url = url or getattr(args, 'store_uri', None)
        api_key = api_key or getattr(args, 'api_key', None)
        replication_factor = replication_factor or getattr(
            args, 'qdrant_replication_factor', None
        )
        shard_number = shard_number or getattr(
            args, 'qdrant_shard_number', None
        )

    defaults = get_qdrant_defaults()
    url = url or defaults['url']
    api_key = api_key or defaults['api_key']
    replication_factor = replication_factor or defaults['replication_factor']
    shard_number = shard_number or defaults['shard_number']

    return url, api_key, replication_factor, shard_number
