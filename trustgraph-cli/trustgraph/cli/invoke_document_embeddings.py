"""
Queries document chunks by text similarity using vector embeddings.
Returns a list of matching document chunks, truncated to the specified length.
"""

import argparse
import os
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)

def truncate_chunk(chunk, max_length):
    """Truncate a chunk to max_length characters, adding ellipsis if needed."""
    if len(chunk) <= max_length:
        return chunk
    return chunk[:max_length] + "..."

def query(url, flow_id, query_text, user, collection, limit, max_chunk_length, token=None):

    # Create API client
    api = Api(url=url, token=token)
    socket = api.socket()
    flow = socket.flow(flow_id)

    try:
        # Call document embeddings query service
        result = flow.document_embeddings_query(
            text=query_text,
            user=user,
            collection=collection,
            limit=limit
        )

        chunks = result.get("chunks", [])
        for i, chunk in enumerate(chunks, 1):
            truncated = truncate_chunk(chunk, max_chunk_length)
            print(f"{i}. {truncated}")

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
        '--max-chunk-length',
        type=int,
        default=200,
        help='Truncate chunks to N characters (default: 200)',
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
            user=args.user,
            collection=args.collection,
            limit=args.limit,
            max_chunk_length=args.max_chunk_length,
            token=args.token,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
