"""
Shows knowledge cores
"""

import argparse
import os
import tabulate
from trustgraph.api import Api, ConfigKey
import json

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')

def show_cores(url, user):

    api = Api(url).knowledge()

    ids = api.list_kg_cores()

    if len(ids) == 0:
        print("No knowledge cores.")

    for id in ids:
        print(id)

def main():

    parser = argparse.ArgumentParser(
        prog='tg-show-flows',
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

    args = parser.parse_args()

    try:

        show_cores(
            url=args.api_url, user=args.user
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()