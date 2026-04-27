"""
Queries row data by text similarity using vector embeddings on indexed fields.
Returns matching rows with their index values and similarity scores.
"""

import argparse
import os
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def query(url, flow_id, query_text, schema_name, collection, index_name, limit, token=None, workspace="default"):

    # Create API client
    api = Api(url=url, token=token, workspace=workspace)
    socket = api.socket()
    flow = socket.flow(flow_id)

    try:
        # Call row embeddings query service
        result = flow.row_embeddings_query(
            text=query_text,
            schema_name=schema_name,
            collection=collection,
            index_name=index_name,
            limit=limit
        )

        matches = result.get("matches", [])
        for match in matches:
            print(f"Index: {match['index_name']}")
            print(f"  Values: {match['index_value']}")
            print(f"  Text: {match['text']}")
            print(f"  Score: {match['score']:.4f}")
            print()

    finally:
        # Clean up socket connection
        socket.close()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-row-embeddings',
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
        '-w', '--workspace',
        default=default_workspace,
        help=f'Workspace (default: {default_workspace})',
    )

    parser.add_argument(
        '-f', '--flow-id',
        default="default",
        help=f'Flow ID (default: default)'
    )

    parser.add_argument(
        '-c', '--collection',
        default="default",
        help='Collection (default: default)',
    )

    parser.add_argument(
        '-s', '--schema-name',
        required=True,
        help='Schema name to search within (required)',
    )

    parser.add_argument(
        '-i', '--index-name',
        default=None,
        help='Index name to filter search (optional)',
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
        help='Query text to search for similar row index values',
    )

    args = parser.parse_args()

    try:

        query(
            url=args.url,
            flow_id=args.flow_id,
            query_text=args.query[0],
            schema_name=args.schema_name,
            collection=args.collection,
            index_name=args.index_name,
            limit=args.limit,
            token=args.token,
            workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
