"""
Invoke the concept extraction service with a natural-language query.
Displays the extracted concepts.
"""

import argparse
import json
import os
import sys
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")


def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-concept-extraction',
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
        help='Flow ID (default: default)',
    )

    parser.add_argument(
        '-j', '--json',
        action='store_true',
        help='Output as JSON',
    )

    parser.add_argument(
        'query',
        nargs='?',
        help='Query text (or read from stdin)',
    )

    args = parser.parse_args()

    if args.query:
        query = args.query
    else:
        if sys.stdin.isatty():
            print("Enter query (Ctrl-D to finish):", file=sys.stderr)
        query = sys.stdin.read().strip()

    if not query:
        print("Error: no query provided", file=sys.stderr)
        sys.exit(1)

    try:

        api = Api(
            url=args.url, token=args.token, workspace=args.workspace,
        )
        socket = api.socket()

        try:
            result = socket._send_request_sync(
                "concept-extraction", args.flow_id,
                {
                    "query": query,
                },
            )
        finally:
            socket.close()

        if result.get("error"):
            err = result["error"]
            print(
                f"Error: [{err.get('type', '?')}] {err.get('message', '?')}",
                file=sys.stderr,
            )
            sys.exit(1)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            concepts = result.get("concepts", [])
            print(f"Concepts ({len(concepts)}):")
            print()
            for i, concept in enumerate(concepts, 1):
                print(f"  {i}. {concept}")

    except Exception as e:
        print("Exception:", e, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
