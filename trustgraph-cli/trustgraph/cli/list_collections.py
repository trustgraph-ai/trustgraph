"""
List collections for a user
"""

import argparse
import os
import tabulate
from trustgraph.api import Api
import json

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_user = "trustgraph"

def list_collections(url, user, tag_filter):

    api = Api(url).collection()

    collections = api.list_collections(user=user, tag_filter=tag_filter)

    if len(collections) == 0:
        print("No collections.")
        return

    table = []
    for collection in collections:
        table.append([
            collection.collection,
            collection.name,
            collection.description,
            ", ".join(collection.tags),
            collection.created_at,
            collection.updated_at
        ])

    headers = ["Collection", "Name", "Description", "Tags", "Created", "Updated"]

    print(tabulate.tabulate(
        table,
        headers=headers,
        tablefmt="pretty",
        stralign="left",
        maxcolwidths=[20, 30, 50, 30, 19, 19],
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
        '-U', '--user',
        default=default_user,
        help=f'User ID (default: {default_user})'
    )

    parser.add_argument(
        '-t', '--tag-filter',
        action='append',
        help='Filter by tags (can be specified multiple times)'
    )

    args = parser.parse_args()

    try:

        list_collections(
            url = args.api_url,
            user = args.user,
            tag_filter = args.tag_filter
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()