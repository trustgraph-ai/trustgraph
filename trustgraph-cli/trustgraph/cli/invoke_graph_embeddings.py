"""
Queries graph entities by text similarity using vector embeddings.
Returns a list of matching graph entities.
"""

import argparse
import os
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)

def query(url, flow_id, query_text, user, collection, limit, token=None):

    # Create API client
    api = Api(url=url, token=token)
    socket = api.socket()
    flow = socket.flow(flow_id)

    try:
        # Call graph embeddings query service
        result = flow.graph_embeddings_query(
            text=query_text,
            user=user,
            collection=collection,
            limit=limit
        )

        entities = result.get("entities", [])
        for entity in entities:
            print(entity)

    finally:
        # Clean up socket connection
        socket.close()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-graph-embeddings',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-t', '--token',
        default=default_token,
        help='Authentication token (default: $TRUSTGRAPH_TOKEN)',
    )

    parser.add_argument(
        '-f', '--flow-id',
        default="default",
        help=f'Flow ID (default: default)'
    )

    parser.add_argument(
        '-U', '--user',
        default="trustgraph",
        help='User/keyspace (default: trustgraph)',
    )

    parser.add_argument(
        '-c', '--collection',
        default="default",
        help='Collection (default: default)',
    )

    parser.add_argument(
        '-l', '--limit',
        type=int,
        default=10,
        help='Maximum number of results (default: 10)',
    )

    parser.add_argument(
        'query',
        nargs=1,
        help='Query text to search for similar graph entities',
    )

    args = parser.parse_args()

    try:

        query(
            url=args.url,
            flow_id=args.flow_id,
            query_text=args.query[0],
            user=args.user,
            collection=args.collection,
            limit=args.limit,
            token=args.token,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
