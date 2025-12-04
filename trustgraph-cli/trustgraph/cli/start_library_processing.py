"""
Submits a library document for processing
"""

import argparse
import os
import tabulate
from trustgraph.api import Api, ConfigKey
import json

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_user = "trustgraph"

def start_processing(
        url, user, document_id, id, flow, collection, tags, token=None
):

    api = Api(url, token=token).library()

    if tags:
        tags = tags.split(",")
    else:
        tags = []

    api.start_processing(
        id = id,
        document_id = document_id,
        flow = flow,
        user = user,
        collection = collection,
        tags = tags
    )

def main():

    parser = argparse.ArgumentParser(
        prog='tg-start-library-processing',
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
        '-i', '--flow-id',
        default="default",
        help=f'Flow ID (default: default)',
    )

    parser.add_argument(
        '-d', '--document-id',
        required=True,
        help=f'Document ID',
    )

    parser.add_argument(
        '--id', '--processing-id',
        required=True,
        help=f'Processing ID',
    )

    parser.add_argument(
        '--collection',
        default='default',
        help=f'Collection (default: default)'
    )

    parser.add_argument(
        '--tags',
        help=f'Tags, command separated'
    )

    args = parser.parse_args()

    try:

        start_processing(
            url = args.api_url,
            user = args.user,
            document_id = args.document_id,
            id = args.id,
            flow = args.flow_id,
            collection = args.collection,
            tags = args.tags,
            token = args.token,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()