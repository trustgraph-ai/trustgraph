"""
Set collection metadata (creates if doesn't exist)
"""

import argparse
import os
import tabulate
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_user = "trustgraph"

def set_collection(url, user, collection, name, description, tags):

    api = Api(url).collection()

    result = api.update_collection(
        user=user,
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
        table.append(("Updated", result.updated_at))

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
        '-U', '--user',
        default=default_user,
        help=f'User ID (default: {default_user})'
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

    args = parser.parse_args()

    try:

        set_collection(
            url = args.api_url,
            user = args.user,
            collection = args.collection,
            name = args.name,
            description = args.description,
            tags = args.tags
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()