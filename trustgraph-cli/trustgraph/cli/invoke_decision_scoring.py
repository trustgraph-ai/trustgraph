"""
Invokes the decision-scoring service. Sends state and question
specifications to a System 1 decision model and returns scored answers.
"""

import argparse
import json
import os
import sys
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def query(url, flow_id, state, questions, token=None, workspace="default"):

    api = Api(url=url, token=token, workspace=workspace)
    socket = api.socket()
    flow = socket.flow(flow_id)

    try:
        result = flow.decision_scoring(state=state, questions=questions)

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
        for name, answer in answers.items():
            print(f"\n{name}:")
            print(json.dumps(answer, indent=2))

    finally:
        socket.close()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-decision-scoring',
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
        '-q', '--questions',
        required=True,
        help='Questions specification as JSON string or @filename',
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
        questions = load_json(args.questions)

        query(
            url=args.url,
            flow_id=args.flow_id,
            state=state,
            questions=questions,
            token=args.token,
            workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
