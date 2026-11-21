"""
Invokes the chunker service. Sends a document ID to the chunker
and returns the chunk references as librarian document IDs.
"""

import argparse
import os
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def run(url, flow_id, document_id, chunk_size, chunk_overlap,
        token=None, workspace="default"):

    api = Api(url=url, token=token, workspace=workspace)
    socket = api.socket()
    flow = socket.flow(flow_id)

    try:
        chunks = flow.chunk(
            document_id=document_id,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        print(f"Created {len(chunks)} chunk(s):")
        for c in chunks:
            print(
                f"  chunk {c['index']}: {c['document_id']} "
                f"(offset={c['char_offset']}, length={c['char_length']})"
            )

    finally:
        socket.close()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-chunk',
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
        '-z', '--chunk-size',
        type=int,
        default=0,
        help='Chunk size (0 = use service default)',
    )

    parser.add_argument(
        '-v', '--chunk-overlap',
        type=int,
        default=0,
        help='Chunk overlap (0 = use service default)',
    )

    parser.add_argument(
        'document_id',
        help='Librarian document ID to chunk',
    )

    args = parser.parse_args()

    try:

        run(
            url=args.url,
            flow_id=args.flow_id,
            document_id=args.document_id,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            token=args.token,
            workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
