"""
Connects to the graph query service and dumps all graph edges.
Uses streaming mode for lower time-to-first-result and reduced memory overhead.
"""

import argparse
import os
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_user = 'trustgraph'
default_collection = 'default'
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)

def show_graph(url, flow_id, user, collection, limit, batch_size, token=None):

    socket = Api(url, token=token).socket()
    flow = socket.flow(flow_id)

    try:
        for batch in flow.triples_query_stream(
            user=user,
            collection=collection,
            s=None, p=None, o=None,
            limit=limit,
            batch_size=batch_size,
        ):
            for triple in batch:
                s = triple.get("s", {})
                p = triple.get("p", {})
                o = triple.get("o", {})
                # Format terms for display
                s_str = s.get("v", s.get("i", str(s)))
                p_str = p.get("v", p.get("i", str(p)))
                o_str = o.get("v", o.get("i", str(o)))
                print(s_str, p_str, o_str)
    finally:
        socket.close()

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

    parser.add_argument(
        '-l', '--limit',
        type=int,
        default=10000,
        help='Maximum number of triples to return (default: 10000)',
    )

    parser.add_argument(
        '-b', '--batch-size',
        type=int,
        default=20,
        help='Triples per streaming batch (default: 20)',
    )

    args = parser.parse_args()

    try:

        show_graph(
            url = args.api_url,
            flow_id = args.flow_id,
            user = args.user,
            collection = args.collection,
            limit = args.limit,
            batch_size = args.batch_size,
            token = args.token,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()