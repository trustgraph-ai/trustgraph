"""
Invokes the field-extraction service. Sends text and field
instructions to a span-extraction model and returns extracted spans.
"""

import argparse
import json
import os
import sys
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def query(url, flow_id, state, fields, token=None, workspace="default"):

    api = Api(url=url, token=token, workspace=workspace)
    socket = api.socket()
    flow = socket.flow(flow_id)

    try:
        result = flow.field_extraction(state=state, fields=fields)

        error = result.get("error")
        if error:
            print(
                f"Error: [{error.get('type', 'unknown')}] "
                f"{error.get('message', 'Unknown error')}",
                file=sys.stderr,
            )
            sys.exit(1)

        model = result.get("model", "")
        if model:
            print(f"Model: {model}")

        answers = result.get("answers", {})
        for name, spans in answers.items():
            print(f"\n{name}:")
            for span in spans:
                print(f"  {span}")

    finally:
        socket.close()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-field-extract',
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
        '-s', '--state',
        required=True,
        help='State as JSON string or @filename',
    )

    parser.add_argument(
        '-F', '--fields',
        required=True,
        help='Fields specification as JSON string or @filename',
    )

    args = parser.parse_args()

    try:

        def load_json(value):
            if value.startswith("@"):
                path = value[1:]
                if path == "-":
                    return json.load(sys.stdin)
                with open(path) as f:
                    return json.load(f)
            return json.loads(value)

        state = load_json(args.state)
        fields = load_json(args.fields)

        query(
            url=args.url,
            flow_id=args.flow_id,
            state=state,
            fields=fields,
            token=args.token,
            workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
