"""
Deletes a configuration item
"""

import argparse
import os
from trustgraph.api import Api
from trustgraph.api.types import ConfigKey

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')

def delete_config_item(url, config_type, key):

    api = Api(url).config()

    config_key = ConfigKey(type=config_type, key=key)
    api.delete([config_key])

    print(f"Configuration item deleted: {config_type}/{key}")

def main():

    parser = argparse.ArgumentParser(
        prog='tg-delete-config-item',
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
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    args = parser.parse_args()

    try:

        delete_config_item(
            url=args.api_url,
            config_type=args.type,
            key=args.key,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()