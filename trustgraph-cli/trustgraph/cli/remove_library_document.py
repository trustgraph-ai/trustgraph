"""
Remove a document from the library
"""

import argparse
import os
import uuid

from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_user = 'trustgraph'
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)


def remove_doc(url, user, id, token=None):

    api = Api(url, token=token).library()

    api.remove_document(user=user, id=id)

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
        '-U', '--user',
        default=default_user,
        help=f'User ID (default: {default_user})'
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

    args = parser.parse_args()

    try:

        remove_doc(args.url, args.user, args.identifier, token=args.token)

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()