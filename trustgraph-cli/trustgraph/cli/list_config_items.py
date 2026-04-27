"""
Lists configuration items for a specified type
"""

import argparse
import os
import json
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def list_config_items(url, config_type, format_type, token=None,
                      workspace="default"):

    api = Api(url, token=token, workspace=workspace).config()

    keys = api.list(config_type)

    if format_type == "json":
        print(json.dumps(keys))
    else:
        for key in keys:
            print(key)

def main():

    parser = argparse.ArgumentParser(
        prog='tg-list-config-items',
        description=__doc__,
    )

    parser.add_argument(
        '--type',
        required=True,
        help='Configuration type to list',
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

    parser.add_argument(
        '-w', '--workspace',
        default=default_workspace,
        help=f'Workspace (default: {default_workspace})',
    )

    args = parser.parse_args()

    try:

        list_config_items(
            url=args.api_url,
            config_type=args.type,
            format_type=args.format,
            token=args.token,
            workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()