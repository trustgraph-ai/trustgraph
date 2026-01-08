"""
"""

import argparse
import os
import tabulate
from trustgraph.api import Api, ConfigKey
import json

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_user = "trustgraph"
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)

def show_procs(url, user, token=None):

    api = Api(url, token=token).library()

    procs = api.get_processings(user = user)

    if len(procs) == 0:
        print("No processing objects.")
        return

    for proc in procs:

        table = []
        table.append(("id", proc.id))
        table.append(("document-id", proc.document_id))
        table.append(("time", proc.time))
        table.append(("flow", proc.flow))
        table.append(("collection", proc.collection))
        table.append(("tags", ", ".join(proc.tags)))

        print(tabulate.tabulate(
            table,
            tablefmt="pretty",
            stralign="left",
            maxcolwidths=[None, 50],
        ))
        print()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-show-library-processing',
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
        '-t', '--token',
        default=default_token,
        help='Authentication token (default: $TRUSTGRAPH_TOKEN)',
    )

    args = parser.parse_args()

    try:

        show_procs(
            url = args.api_url, user = args.user, token = args.token
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()