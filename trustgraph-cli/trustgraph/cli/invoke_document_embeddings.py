"""
Queries document chunks by text similarity using vector embeddings.
Returns a list of matching chunk IDs.
"""

import argparse
import os
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def query(url, flow_id, query_text, collection, limit, token=None, workspace="default"):

    # Create API client
    api = Api(url=url, token=token, workspace=workspace)
    socket = api.socket()
    flow = socket.flow(flow_id)

    try:
        # Call document embeddings query service
        result = flow.document_embeddings_query(
            text=query_text,
            collection=collection,
            limit=limit
        )

        chunks = result.get("chunks", [])
        if not chunks:
            print("No matching chunks found.")
        else:
            for i, chunk in enumerate(chunks, 1):
                chunk_id = chunk.get("chunk_id", "")
                score = chunk.get("score", 0.0)
                print(f"{i}. {chunk_id} (score: {score:.4f})")

    finally:
        # Clean up socket connection
        socket.close()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-document-embeddings',
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
        '-l', '--limit',
        type=int,
        default=10,
        help='Maximum number of results (default: 10)',
    )

    parser.add_argument(
        'query',
        nargs=1,
        help='Query text to search for similar document chunks',
    )

    args = parser.parse_args()

    try:

        query(
            url=args.url,
            flow_id=args.flow_id,
            query_text=args.query[0],
            collection=args.collection,
            limit=args.limit,
            token=args.token,
            workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
