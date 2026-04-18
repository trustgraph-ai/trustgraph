"""
Set collection metadata (creates if doesn't exist)
"""

import argparse
import os
import tabulate
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def set_collection(url, collection, name, description, tags, token=None, workspace="default"):

    api = Api(url, token=token, workspace=workspace).collection()

    result = api.update_collection(
        collection=collection,
        name=name,
        description=description,
        tags=tags
    )

    if result:
        print(f"Collection '{collection}' set successfully.")

        table = []
        table.append(("Collection", result.collection))
        table.append(("Name", result.name))
        table.append(("Description", result.description))
        table.append(("Tags", ", ".join(result.tags)))

        print(tabulate.tabulate(
            table,
            tablefmt="pretty",
            stralign="left",
            maxcolwidths=[None, 67],
        ))
    else:
        print(f"Failed to set collection '{collection}'.")

def main():

    parser = argparse.ArgumentParser(
        prog='tg-set-collection',
        description=__doc__,
    )

    parser.add_argument(
        'collection',
        help='Collection ID to set'
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-n', '--name',
        help='Collection name'
    )

    parser.add_argument(
        '-d', '--description',
        help='Collection description'
    )

    parser.add_argument(
        '-t', '--tag',
        action='append',
        dest='tags',
        help='Collection tags (can be specified multiple times)'
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

        set_collection(
            url = args.api_url,
            collection = args.collection,
            name = args.name,
            description = args.description,
            tags = args.tags,
            token = args.token,
            workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
