"""
Show version history for a named graph.

Lists all versions with timestamps and symbolic labels, newest first.

Examples:
  tg-list-graph-versions -g urn:graph:source
  tg-list-graph-versions -g urn:graph:source --format json
"""

import argparse
import json
import os
import sys
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_collection = 'default'
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")


def main():

    parser = argparse.ArgumentParser(
        prog='tg-list-graph-versions',
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
                operation="version-list",
                collection=args.collection,
                **{"named-graph": args.named_graph},
            )
        finally:
            socket.close()

        if isinstance(result, dict) and "error" in result:
            err = result["error"]
            print(f"Error: {err.get('message', err)}", file=sys.stderr)
            sys.exit(1)

        version_log = result.get("version-log", []) if isinstance(result, dict) else []

        if args.format == "json":
            print(json.dumps(version_log, indent=2))
        else:
            if not version_log:
                print("No versions found")
            else:
                for entry in version_log:
                    v = entry.get("version", "?")
                    created = entry.get("created-at", "")
                    names = entry.get("names", [])
                    desc = entry.get("description", "")

                    parts = [f"v{v}"]
                    if created:
                        parts.append(f"  {created}")
                    if names:
                        parts.append(f"  [{', '.join(names)}]")
                    if desc:
                        parts.append(f"  {desc}")
                    print("".join(parts))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
