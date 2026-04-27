"""
List collections in a workspace
"""

import argparse
import os
import tabulate
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def list_collections(url, tag_filter, token=None, workspace="default"):

    api = Api(url, token=token, workspace=workspace).collection()

    collections = api.list_collections(tag_filter=tag_filter)

    if not collections or len(collections) == 0:
        print("No collections found.")
        return

    table = []
    for collection in collections:
        table.append([
            collection.collection,
            collection.name,
            collection.description,
            ", ".join(collection.tags)
        ])

    headers = ["Collection", "Name", "Description", "Tags"]

    print(tabulate.tabulate(
        table,
        headers=headers,
        tablefmt="pretty",
        stralign="left",
        maxcolwidths=[20, 30, 50, 30],
    ))

def main():

    parser = argparse.ArgumentParser(
        prog='tg-list-collections',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-t', '--tag-filter',
        action='append',
        help='Filter by tags (can be specified multiple times)'
    )

    parser.add_argument(
        '--token',
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

        list_collections(
            url = args.api_url,
            tag_filter = args.tag_filter,
            token = args.token,
            workspace = args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
