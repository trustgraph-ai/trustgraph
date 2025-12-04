"""
Connects to the graph query service and dumps all graph edges.
"""

import argparse
import os
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_user = 'trustgraph'
default_collection = 'default'
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)

def show_graph(url, flow_id, user, collection, token=None):

    api = Api(url, token=token).flow().id(flow_id)

    rows = api.triples_query(
        user=user, collection=collection,
        s=None, p=None, o=None, limit=10_000,
    )

    for row in rows:
        print(row.s, row.p, row.o)

def main():

    parser = argparse.ArgumentParser(
        prog='tg-show-graph',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-f', '--flow-id',
        default="default",
        help=f'Flow ID (default: default)'
    )

    parser.add_argument(
        '-U', '--user',
        default=default_user,
        help=f'User ID (default: {default_user})'
    )

    parser.add_argument(
        '-C', '--collection',
        default=default_collection,
        help=f'Collection ID (default: {default_collection})'
    )

    parser.add_argument(
        '-t', '--token',
        default=default_token,
        help='Authentication token (default: $TRUSTGRAPH_TOKEN)',
    )

    args = parser.parse_args()

    try:

        show_graph(
            url = args.api_url,
            flow_id = args.flow_id,
            user = args.user,
            collection = args.collection,
            token = args.token,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()