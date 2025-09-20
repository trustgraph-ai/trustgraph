"""
Delete a collection and all its data
"""

import argparse
import os
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_user = "trustgraph"

def delete_collection(url, user, collection, confirm):

    if not confirm:
        response = input(f"Are you sure you want to delete collection '{collection}' and all its data? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Operation cancelled.")
            return

    api = Api(url).collection()

    api.delete_collection(user=user, collection=collection)

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
        '-U', '--user',
        default=default_user,
        help=f'User ID (default: {default_user})'
    )

    parser.add_argument(
        '-y', '--yes',
        action='store_true',
        help='Skip confirmation prompt'
    )

    args = parser.parse_args()

    try:

        delete_collection(
            url = args.api_url,
            user = args.user,
            collection = args.collection,
            confirm = args.yes
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()