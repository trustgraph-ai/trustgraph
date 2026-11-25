"""
Restore a named graph to a previous version.

This is non-destructive: it creates a new version containing the delta
needed to restore the graph to its state at the target version.

Examples:
  tg-revert-graph -g urn:graph:source -V 3
"""

import argparse
import os
import sys
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_collection = 'default'
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")


def main():

    parser = argparse.ArgumentParser(
        prog='tg-revert-graph',
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
        '-V', '--version',
        required=True,
        help='Target version number or name to revert to',
    )

    args = parser.parse_args()

    try:
        socket = Api(args.api_url, token=args.token, workspace=args.workspace).socket()
        flow = socket.flow(args.flow_id)

        try:
            result = flow.triples_query(
                operation="revert",
                collection=args.collection,
                **{
                    "named-graph": args.named_graph,
                    "version": args.version,
                },
            )
        finally:
            socket.close()

        if isinstance(result, dict) and "error" in result:
            err = result["error"]
            print(f"Error: {err.get('message', err)}", file=sys.stderr)
            sys.exit(1)

        new_version = result.get("version", "?") if isinstance(result, dict) else "?"
        print(
            f"Reverted {args.collection}/{args.named_graph} "
            f"to v{args.version} (now v{new_version})"
        )

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
