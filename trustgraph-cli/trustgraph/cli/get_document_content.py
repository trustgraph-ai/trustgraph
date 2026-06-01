"""
Gets document content from the library by document ID.
"""

import argparse
import os
import sys
import requests

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def get_content(url, document_id, output_file, token=None, workspace="default"):

    stream_url = url.rstrip("/") + "/api/v1/document-stream"

    params = {
        "document-id": document_id,
        "workspace": workspace,
    }

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.get(stream_url, params=params, headers=headers, stream=True)
    resp.raise_for_status()

    if output_file:
        total = 0
        with open(output_file, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
                total += len(chunk)
        print(f"Written {total} bytes to {output_file}")
    else:
        content = resp.content
        try:
            text = content.decode('utf-8')
            print(text)
        except UnicodeDecodeError:
            print(f"Binary content: {len(content)} bytes", file=sys.stderr)
            sys.stdout.buffer.write(content)

def main():

    parser = argparse.ArgumentParser(
        prog='tg-get-document-content',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--api-url',
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
        '-o', '--output',
        default=None,
        help='Output file (default: stdout)'
    )

    parser.add_argument(
        'document_id',
        help='Document ID (IRI) to retrieve',
    )

    args = parser.parse_args()

    try:

        get_content(
            url=args.api_url,
            document_id=args.document_id,
            output_file=args.output,
            token=args.token,
            workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
