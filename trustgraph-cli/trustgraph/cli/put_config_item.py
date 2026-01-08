"""
Sets a configuration item
"""

import argparse
import os
import sys
from trustgraph.api import Api
from trustgraph.api.types import ConfigValue

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)

def put_config_item(url, config_type, key, value, token=None):

    api = Api(url, token=token).config()

    config_value = ConfigValue(type=config_type, key=key, value=value)
    api.put([config_value])

    print(f"Configuration item set: {config_type}/{key}")

def main():

    parser = argparse.ArgumentParser(
        prog='tg-put-config-item',
        description=__doc__,
    )

    parser.add_argument(
        '--type',
        required=True,
        help='Configuration type',
    )

    parser.add_argument(
        '--key',
        required=True,
        help='Configuration key',
    )

    value_group = parser.add_mutually_exclusive_group(required=True)
    value_group.add_argument(
        '--value',
        help='Configuration value',
    )

    value_group.add_argument(
        '--stdin',
        action='store_true',
        help='Read configuration value from standard input',
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-t', '--token',
        default=default_token,
        help='Authentication token (default: $TRUSTGRAPH_TOKEN)',
    )

    args = parser.parse_args()

    try:

        if args.stdin:
            value = sys.stdin.read()
        else:
            value = args.value

        put_config_item(
            url=args.api_url,
            config_type=args.type,
            key=args.key,
            value=value,
            token=args.token,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()