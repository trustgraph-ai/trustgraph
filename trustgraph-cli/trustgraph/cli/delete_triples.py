"""
Delete triples from a named graph by pattern or explicit list.

Pattern mode (default): specify -s, -p, -o to match triples for deletion.
Omitted fields act as wildcards.

Examples:
  tg-delete-triples -g urn:graph:source -s "http://example.org/entity"
  tg-delete-triples -g urn:graph:source -p "http://www.w3.org/2000/01/rdf-schema#label"
  tg-delete-triples -g urn:graph:source -s "http://example.org/entity" -p "http://example.org/name"
"""

import argparse
import os
import sys
from trustgraph.api import Api
from . query_graph import build_term

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_collection = 'default'
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")


def main():

    parser = argparse.ArgumentParser(
        prog='tg-delete-triples',
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
        '-s', '--subject',
        help='Subject filter (auto-detected as IRI or literal)',
    )

    parser.add_argument(
        '-p', '--predicate',
        help='Predicate filter (auto-detected as IRI)',
    )

    parser.add_argument(
        '-o', '--object',
        dest='obj',
        help='Object filter (IRI or literal)',
    )

    args = parser.parse_args()

    if not args.subject and not args.predicate and not args.obj:
        parser.error("At least one of -s, -p, -o must be specified for pattern deletion")

    try:
        socket = Api(args.api_url, token=args.token, workspace=args.workspace).socket()
        flow = socket.flow(args.flow_id)

        request_kwargs = {
            "operation": "delete",
            "collection": args.collection,
            "named-graph": args.named_graph,
        }

        s_term = build_term(args.subject) if args.subject else None
        p_term = build_term(args.predicate) if args.predicate else None
        o_term = build_term(args.obj) if args.obj else None

        try:
            result = flow.triples_query(
                s=s_term,
                p=p_term,
                o=o_term,
                **request_kwargs,
            )
        finally:
            socket.close()

        if isinstance(result, dict) and "error" in result:
            err = result["error"]
            print(f"Error: {err.get('message', err)}", file=sys.stderr)
            sys.exit(1)

        print("Delete operation completed")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
