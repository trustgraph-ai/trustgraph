"""
Invoke the query formulation service with a natural language question
and schema name, and display the resulting QuerySpec.
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
        prog='tg-invoke-query-formulation',
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
        '-s', '--schema-name',
        required=True,
        help='Schema name to formulate query against',
    )

    parser.add_argument(
        '-j', '--json',
        action='store_true',
        help='Output raw JSON response',
    )

    parser.add_argument(
        'question',
        nargs='?',
        help='Natural language question (or read from stdin)',
    )

    args = parser.parse_args()

    question = args.question
    if question is None:
        if sys.stdin.isatty():
            print("Enter question (Ctrl-D to finish):", file=sys.stderr)
        question = sys.stdin.read().strip()

    if not question:
        print("Error: no question provided", file=sys.stderr)
        sys.exit(1)

    try:

        api = Api(
            url=args.url, token=args.token, workspace=args.workspace,
        )
        socket = api.socket()

        try:
            result = socket._send_request_sync(
                "query-formulation", args.flow_id,
                {
                    "question": question,
                    "schema-name": args.schema_name,
                },
            )
        finally:
            socket.close()

        if result.get("error"):
            err = result["error"]
            print(
                f"Error: [{err.get('type', '?')}] "
                f"{err.get('message', '?')}",
                file=sys.stderr,
            )
            sys.exit(1)

        query_spec_str = result.get("query-spec", "")

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            try:
                spec = json.loads(query_spec_str)
                print(f"Type: {spec.get('type', '?')}")

                if spec.get("type") == "select":
                    print(f"Table: {spec.get('table', '?')}")
                    print(f"Columns: {', '.join(spec.get('columns', []))}")

                    filters = spec.get("filters", [])
                    if filters:
                        print("Filters:")
                        for f in filters:
                            print(
                                f"  {f.get('column')} "
                                f"{f.get('op')} "
                                f"{f.get('value')}"
                            )

                    order_by = spec.get("order_by", [])
                    if order_by:
                        print("Order:")
                        for o in order_by:
                            print(
                                f"  {o.get('column')} "
                                f"{o.get('direction')}"
                            )

                    limit = spec.get("limit")
                    if limit:
                        print(f"Limit: {limit}")

                elif spec.get("type") == "join":
                    print(f"Join type: {spec.get('join_type', '?')}")
                    print(f"On: {spec.get('on', [])}")
                    print()
                    print("Full spec:")
                    print(json.dumps(spec, indent=2))

                else:
                    print(json.dumps(spec, indent=2))

            except json.JSONDecodeError:
                print(query_spec_str)

    except Exception as e:
        print("Exception:", e, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
