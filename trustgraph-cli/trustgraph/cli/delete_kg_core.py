"""
Deletes a flow class
"""

import argparse
import os
import tabulate
from trustgraph.api import Api
import json

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')

def delete_kg_core(url, user, id):

    api = Api(url).knowledge()

    class_names = api.delete_kg_core(user = user, id = id)

def main():

    parser = argparse.ArgumentParser(
        prog='tg-delete-kg-core',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-U', '--user',
        default="trustgraph",
        help='API URL (default: trustgraph)',
    )

    parser.add_argument(
        '--id', '--identifier',
        required=True,
        help=f'Knowledge core ID',
    )

    args = parser.parse_args()

    try:

        delete_kg_core(
            url=args.api_url,
            user=args.user,
            id=args.id,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
