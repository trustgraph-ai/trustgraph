"""
Uses the GraphRAG service to answer a question
"""

import argparse
import os
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_user = 'trustgraph'
default_collection = 'default'
default_entity_limit = 50
default_triple_limit = 30
default_max_subgraph_size = 150
default_max_path_length = 2

def question(
        url, flow_id, question, user, collection, entity_limit, triple_limit,
        max_subgraph_size, max_path_length, streaming=True, token=None
):

    # Create API client
    api = Api(url=url, token=token)

    if streaming:
        # Use socket client for streaming
        socket = api.socket()
        flow = socket.flow(flow_id)

        try:
            response = flow.graph_rag(
                query=question,
                user=user,
                collection=collection,
                entity_limit=entity_limit,
                triple_limit=triple_limit,
                max_subgraph_size=max_subgraph_size,
                max_path_length=max_path_length,
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
        resp = flow.graph_rag(
            query=question,
            user=user,
            collection=collection,
            entity_limit=entity_limit,
            triple_limit=triple_limit,
            max_subgraph_size=max_subgraph_size,
            max_path_length=max_path_length
        )
        print(resp)

def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-graph-rag',
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
        '-e', '--entity-limit',
        type=int,
        default=default_entity_limit,
        help=f'Entity limit (default: {default_entity_limit})'
    )

    parser.add_argument(
        '--triple-limit',
        type=int,
        default=default_triple_limit,
        help=f'Triple limit (default: {default_triple_limit})'
    )

    parser.add_argument(
        '-s', '--max-subgraph-size',
        type=int,
        default=default_max_subgraph_size,
        help=f'Max subgraph size (default: {default_max_subgraph_size})'
    )

    parser.add_argument(
        '-p', '--max-path-length',
        type=int,
        default=default_max_path_length,
        help=f'Max path length (default: {default_max_path_length})'
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
            entity_limit=args.entity_limit,
            triple_limit=args.triple_limit,
            max_subgraph_size=args.max_subgraph_size,
            max_path_length=args.max_path_length,
            streaming=not args.no_streaming,
            token=args.token,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
