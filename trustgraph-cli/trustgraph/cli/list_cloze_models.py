"""
Lists cloze model instances in the current workspace, showing their
state (ready/training), labels, accuracy, and dataset sizes.
"""

import argparse
import json
import os
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def query(url, flow_id, token=None, workspace="default", as_json=False):

    api = Api(url=url, token=token, workspace=workspace)
    socket = api.socket()
    flow = socket.flow(flow_id)

    try:
        result = flow.cloze_list_models()
        models = result.get("models", [])

        if as_json:
            print(json.dumps(models, indent=2))
            return

        if not models:
            print("No cloze models found.")
            return

        for m in models:
            print(f"{m['name']}:")
            print(f"  State: {m['state']}")
            if m.get("labels"):
                print(f"  Labels: {', '.join(m['labels'])}")
            if m.get("accuracy") is not None:
                print(f"  Accuracy: {m['accuracy']:.1%}")
            if m.get("train_size") is not None:
                print(f"  Train/Test: {m['train_size']}/{m.get('test_size', 0)}")

    finally:
        socket.close()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-list-cloze-models',
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
        '-j', '--json',
        action='store_true',
        default=False,
        help='Output as JSON',
    )

    args = parser.parse_args()

    try:

        query(
            url=args.url,
            flow_id=args.flow_id,
            token=args.token,
            workspace=args.workspace,
            as_json=args.json,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
