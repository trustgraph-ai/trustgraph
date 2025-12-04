"""
Uses the DocumentRAG service to answer a question
"""

import argparse
import os
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_user = 'trustgraph'
default_collection = 'default'
default_doc_limit = 10

def question(url, flow_id, question, user, collection, doc_limit, streaming=True, token=None):

    # Create API client
    api = Api(url=url, token=token)

    if streaming:
        # Use socket client for streaming
        socket = api.socket()
        flow = socket.flow(flow_id)

        try:
            response = flow.document_rag(
                question=question,
                user=user,
                collection=collection,
                doc_limit=doc_limit,
                streaming=True
            )

            # Stream output
            for chunk in response:
                print(chunk, end="", flush=True)
            print()  # Final newline

        finally:
            socket.close()
    else:
        # Use REST API for non-streaming
        flow = api.flow().id(flow_id)
        resp = flow.document_rag(
            question=question,
            user=user,
            collection=collection,
            doc_limit=doc_limit,
        )
        print(resp)

def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-document-rag',
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
        '-q', '--question',
        required=True,
        help=f'Question to answer',
    )

    parser.add_argument(
        '-U', '--user',
        default=default_user,
        help=f'User ID (default: {default_user})'
    )

    parser.add_argument(
        '-C', '--collection',
        default=default_collection,
        help=f'Collection ID (default: {default_collection})'
    )

    parser.add_argument(
        '-d', '--doc-limit',
        type=int,
        default=default_doc_limit,
        help=f'Document limit (default: {default_doc_limit})'
    )

    parser.add_argument(
        '--no-streaming',
        action='store_true',
        help='Disable streaming (use non-streaming mode)'
    )

    args = parser.parse_args()

    try:

        question(
            url=args.url,
            flow_id=args.flow_id,
            question=args.question,
            user=args.user,
            collection=args.collection,
            doc_limit=args.doc_limit,
            streaming=not args.no_streaming,
            token=args.token,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
