"""
Invokes the document decoder service. Sends a document ID to docling
for conversion and returns the decoded sections as librarian references.
"""

import argparse
import os
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def run(url, flow_id, document_id, mode, token=None, workspace="default"):

    api = Api(url=url, token=token, workspace=workspace)
    socket = api.socket()
    flow = socket.flow(flow_id)

    try:
        sections = flow.document_decode(
            document_id=document_id,
            mode=mode,
        )

        print(f"Decoded {len(sections)} section(s):")
        for s in sections:
            page_info = f" (page {s['page']})" if s['page'] else ""
            print(
                f"  {s['section_type']}{page_info}: "
                f"{s['document_id']}"
            )

    finally:
        socket.close()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-document-decode',
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
        '-m', '--mode',
        default='page',
        choices=['page', 'hybrid'],
        help='Decoding mode (default: page)',
    )

    parser.add_argument(
        'document_id',
        help='Librarian document ID to decode',
    )

    args = parser.parse_args()

    try:

        run(
            url=args.url,
            flow_id=args.flow_id,
            document_id=args.document_id,
            mode=args.mode,
            token=args.token,
            workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
