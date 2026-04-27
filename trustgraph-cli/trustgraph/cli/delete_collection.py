"""
Delete a collection and all its data
"""

import argparse
import os
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")


def delete_collection(url, collection, confirm, token=None, workspace="default"):

    if not confirm:
        response = input(f"Are you sure you want to delete collection '{collection}' and all its data? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Operation cancelled.")
            return

    api = Api(url, token=token, workspace=workspace).collection()

    api.delete_collection(collection=collection)

    print(f"Collection '{collection}' deleted successfully.")

def main():

    parser = argparse.ArgumentParser(
        prog='tg-delete-collection',
        description=__doc__,
    )

    parser.add_argument(
        'collection',
        help='Collection ID to delete'
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-y', '--yes',
        action='store_true',
        help='Skip confirmation prompt'
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

        delete_collection(
            url = args.api_url,
            collection = args.collection,
            confirm = args.yes,
            token = args.token,
            workspace = args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
