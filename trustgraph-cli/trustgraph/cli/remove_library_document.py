"""
Remove a document from the library
"""

import argparse
import os

from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")


def remove_doc(url, id, token=None, workspace="default"):

    api = Api(url, token=token, workspace=workspace).library()

    api.remove_document(id=id)

def main():

    parser = argparse.ArgumentParser(
        prog='tg-remove-library-document',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '--identifier', '--id',
        required=True,
        help=f'Document ID'
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

    args = parser.parse_args()

    try:

        remove_doc(
            args.url, args.identifier,
            token=args.token, workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
