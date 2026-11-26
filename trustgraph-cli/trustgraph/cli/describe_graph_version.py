"""
Set a description on a graph version.

Examples:
  tg-describe-graph-version -g urn:graph:source -V 3 -d "Baseline after initial ingestion"
  tg-describe-graph-version -V 2 -d "Before Q4 reingestion"
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
        prog='tg-describe-graph-version',
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
        help='Version number or name to describe',
    )

    parser.add_argument(
        '-d', '--description',
        required=True,
        help='Description text for the version',
    )

    args = parser.parse_args()

    try:
        socket = Api(args.api_url, token=args.token, workspace=args.workspace).socket()
        flow = socket.flow(args.flow_id)

        try:
            result = flow.triples_query(
                operation="version-describe",
                collection=args.collection,
                **{
                    "named-graph": args.named_graph,
                    "version": args.version,
                    "description": args.description,
                },
            )
        finally:
            socket.close()

        if isinstance(result, dict) and "error" in result:
            err = result["error"]
            print(f"Error: {err.get('message', err)}", file=sys.stderr)
            sys.exit(1)

        print(
            f"Described {args.collection}/{args.named_graph} "
            f"v{args.version}: '{args.description}'"
        )

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
