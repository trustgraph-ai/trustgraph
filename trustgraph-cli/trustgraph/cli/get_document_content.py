"""
Gets document content from the library by document ID.
"""

import argparse
import os
import sys
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_user = "trustgraph"

def get_content(url, user, document_id, output_file, token=None):

    api = Api(url, token=token).library()

    content = api.get_document_content(user=user, id=document_id)

    if output_file:
        with open(output_file, 'wb') as f:
            f.write(content)
        print(f"Written {len(content)} bytes to {output_file}")
    else:
        # Write to stdout
        # Try to decode as text, fall back to binary info
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
        '-U', '--user',
        default=default_user,
        help=f'User ID (default: {default_user})'
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
            user=args.user,
            document_id=args.document_id,
            output_file=args.output,
            token=args.token,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
