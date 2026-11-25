"""
Show added and removed triples between two graph versions.

Examples:
  tg-diff-graph -g urn:graph:source --v1 1 --v2 3
  tg-diff-graph -g urn:graph:source --v1 2 --v2 5 --format json
"""

import argparse
import json
import os
import sys
from trustgraph.api import Api
from . query_graph import format_term

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_collection = 'default'
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")


def print_triples(label, triples, output_format):
    if not triples:
        return

    if output_format == "json":
        print(json.dumps({label: triples}, indent=2))
        return

    print(f"\n{label} ({len(triples)}):")
    for triple in triples:
        s = format_term(triple.get("s", {}))
        p = format_term(triple.get("p", {}))
        o = format_term(triple.get("o", {}))
        prefix = "+" if label == "Added" else "-"
        print(f"  {prefix} {s} {p} {o}")


def main():

    parser = argparse.ArgumentParser(
        prog='tg-diff-graph',
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-f', '--flow-id',
        default="default",
        help='Flow ID (default: default)',
    )

    parser.add_argument(
        '-C', '--collection',
        default=default_collection,
        help=f'Collection (default: {default_collection})',
    )

    parser.add_argument(
        '-t', '--token',
        default=default_token,
        help='Auth token (default: $TRUSTGRAPH_TOKEN)',
    )

    parser.add_argument(
        '-w', '--workspace',
        default=default_workspace,
        help=f'Workspace (default: {default_workspace})',
    )

    parser.add_argument(
        '-g', '--named-graph',
        default='',
        help='Named graph IRI (default: empty = default graph)',
    )

    parser.add_argument(
        '--v1',
        type=int,
        required=True,
        help='First version (older)',
    )

    parser.add_argument(
        '--v2',
        type=int,
        required=True,
        help='Second version (newer)',
    )

    parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)',
    )

    args = parser.parse_args()

    try:
        socket = Api(args.api_url, token=args.token, workspace=args.workspace).socket()
        flow = socket.flow(args.flow_id)

        try:
            result = flow.triples_query(
                operation="diff",
                collection=args.collection,
                **{
                    "named-graph": args.named_graph,
                    "v1": args.v1,
                    "v2": args.v2,
                },
            )
        finally:
            socket.close()

        if isinstance(result, dict) and "error" in result:
            err = result["error"]
            print(f"Error: {err.get('message', err)}", file=sys.stderr)
            sys.exit(1)

        added = result.get("added", []) if isinstance(result, dict) else []
        removed = result.get("removed", []) if isinstance(result, dict) else []

        if args.format == "json":
            print(json.dumps({"added": added, "removed": removed}, indent=2))
        else:
            if not added and not removed:
                print(f"No changes between v{args.v1} and v{args.v2}")
            else:
                print_triples("Added", added, args.format)
                print_triples("Removed", removed, args.format)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
