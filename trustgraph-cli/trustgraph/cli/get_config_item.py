"""
Gets a specific configuration item
"""

import argparse
import os
import json
from trustgraph.api import Api
from trustgraph.api.types import ConfigKey

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)

def get_config_item(url, config_type, key, format_type, token=None):

    api = Api(url, token=token).config()

    config_key = ConfigKey(type=config_type, key=key)
    values = api.get([config_key])

    if not values:
        raise Exception(f"Configuration item not found: {config_type}/{key}")

    value = values[0].value

    if format_type == "json":
        print(json.dumps(value))
    else:
        print(value)

def main():

    parser = argparse.ArgumentParser(
        prog='tg-get-config-item',
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

    parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)',
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

        get_config_item(
            url=args.api_url,
            config_type=args.type,
            key=args.key,
            format_type=args.format,
            token=args.token,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()