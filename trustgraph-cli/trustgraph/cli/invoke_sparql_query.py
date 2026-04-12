"""
Execute a SPARQL query against the TrustGraph knowledge graph.
"""

import argparse
import os
import json
import sys
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_user = 'trustgraph'
default_collection = 'default'


def _term_cell(val):
    """Extract display string from a wire-format term."""
    if val is None:
        return ""
    t = val.get("t", "")
    if t == "i":
        return val.get("i", "")
    elif t == "l":
        return val.get("v", "")
    return val.get("v", val.get("i", ""))


def _term_str(val):
    """Convert a wire-format term to a Turtle-style display string."""
    if val is None:
        return "?"
    t = val.get("t", "")
    if t == "i":
        return f"<{val.get('i', '')}>"
    elif t == "l":
        v = val.get("v", "")
        dt = val.get("d", "")
        lang = val.get("l", "")
        if lang:
            return f'"{v}"@{lang}'
        elif dt:
            return f'"{v}"^^<{dt}>'
        return f'"{v}"'
    return str(val)


def sparql_query(url, token, flow_id, query, user, collection, limit,
                 batch_size, output_format):

    socket = Api(url=url, token=token).socket()
    flow = socket.flow(flow_id)

    variables = None
    all_rows = []

    try:

        for response in flow.sparql_query_stream(
            query=query,
            user=user,
            collection=collection,
            limit=limit,
            batch_size=batch_size,
        ):
            query_type = response.get("query-type", "select")

            # ASK queries - just print and return
            if query_type == "ask":
                print("true" if response.get("ask-result") else "false")
                return

            # CONSTRUCT/DESCRIBE - print triples
            if query_type in ("construct", "describe"):
                triples = response.get("triples", [])
                if not triples:
                    print("No triples.")
                elif output_format == "json":
                    print(json.dumps(triples, indent=2))
                else:
                    for t in triples:
                        s = _term_str(t.get("s"))
                        p = _term_str(t.get("p"))
                        o = _term_str(t.get("o"))
                        print(f"{s} {p} {o} .")
                return

            # SELECT - accumulate bindings across batches
            if variables is None:
                variables = response.get("variables", [])

            bindings = response.get("bindings", [])
            for binding in bindings:
                values = binding.get("values", [])
                all_rows.append([_term_cell(v) for v in values])

        # Output SELECT results
        if variables is None:
            print("No results.")
            return

        if not all_rows:
            print("No results.")
            return

        if output_format == "json":
            rows = []
            for row in all_rows:
                rows.append({
                    var: cell for var, cell in zip(variables, row)
                })
            print(json.dumps(rows, indent=2))
        else:
            # Table format
            col_widths = [len(v) for v in variables]
            for row in all_rows:
                for i, cell in enumerate(row):
                    if i < len(col_widths):
                        col_widths[i] = max(col_widths[i], len(cell))

            header = " | ".join(
                v.ljust(col_widths[i]) for i, v in enumerate(variables)
            )
            separator = "-+-".join("-" * w for w in col_widths)
            print(header)
            print(separator)
            for row in all_rows:
                line = " | ".join(
                    cell.ljust(col_widths[i]) if i < len(col_widths) else cell
                    for i, cell in enumerate(row)
                )
                print(line)

    finally:
        socket.close()


def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-sparql-query',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-t', '--token',
        default=os.getenv("TRUSTGRAPH_TOKEN"),
        help='API bearer token (default: TRUSTGRAPH_TOKEN env var)',
    )

    parser.add_argument(
        '-f', '--flow-id',
        default="default",
        help='Flow ID (default: default)',
    )

    parser.add_argument(
        '-q', '--query',
        help='SPARQL query string',
    )

    parser.add_argument(
        '-i', '--input',
        help='Read SPARQL query from file (use - for stdin)',
    )

    parser.add_argument(
        '-U', '--user',
        default=default_user,
        help=f'User ID (default: {default_user})',
    )

    parser.add_argument(
        '-C', '--collection',
        default=default_collection,
        help=f'Collection ID (default: {default_collection})',
    )

    parser.add_argument(
        '-l', '--limit',
        type=int,
        default=10000,
        help='Result limit (default: 10000)',
    )

    parser.add_argument(
        '-b', '--batch-size',
        type=int,
        default=20,
        help='Streaming batch size (default: 20)',
    )

    parser.add_argument(
        '--format',
        choices=['table', 'json'],
        default='table',
        help='Output format (default: table)',
    )

    args = parser.parse_args()

    # Get query from argument or file
    query = args.query
    if not query and args.input:
        if args.input == '-':
            query = sys.stdin.read()
        else:
            with open(args.input) as f:
                query = f.read()

    if not query:
        parser.error("Either -q/--query or -i/--input is required")

    try:

        sparql_query(
            url=args.url,
            token=args.token,
            flow_id=args.flow_id,
            query=query,
            user=args.user,
            collection=args.collection,
            limit=args.limit,
            batch_size=args.batch_size,
            output_format=args.format,
        )

    except Exception as e:
        print(f"Exception: {e}", flush=True, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
