"""
Invokes the cloze classification service. Sends a query to a trained
cloze model instance and returns the predicted label with confidence.
"""

import argparse
import os
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def query(url, flow_id, model, query_text, token=None, workspace="default"):

    api = Api(url=url, token=token, workspace=workspace)
    socket = api.socket()
    flow = socket.flow(flow_id)

    try:
        result = flow.cloze(model=model, query=query_text)
        print(f"Label: {result.get('label', '')}")
        print(f"Confidence: {result.get('confidence', 0):.2%}")

    finally:
        socket.close()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-cloze',
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
        '-m', '--model',
        required=True,
        help='Name of the trained cloze model instance',
    )

    parser.add_argument(
        'query',
        help='Query text to classify',
    )

    args = parser.parse_args()

    try:

        query(
            url=args.url,
            flow_id=args.flow_id,
            model=args.model,
            query_text=args.query,
            token=args.token,
            workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
