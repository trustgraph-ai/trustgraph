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


def format_select(response, output_format):
    """Format SELECT query results."""
    variables = response.get("variables", [])
    bindings = response.get("bindings", [])

    if not bindings:
        return "No results."

    if output_format == "json":
        rows = []
        for binding in bindings:
            row = {}
            for var, val in zip(variables, binding.get("values", [])):
                if val is None:
                    row[var] = None
                elif val.get("t") == "i":
                    row[var] = val.get("i", "")
                elif val.get("t") == "l":
                    row[var] = val.get("v", "")
                else:
                    row[var] = val.get("v", val.get("i", ""))
            rows.append(row)
        return json.dumps(rows, indent=2)

    # Table format
    col_widths = [len(v) for v in variables]
    rows = []
    for binding in bindings:
        row = []
        for i, val in enumerate(binding.get("values", [])):
            if val is None:
                cell = ""
            elif val.get("t") == "i":
                cell = val.get("i", "")
            elif val.get("t") == "l":
                cell = val.get("v", "")
            else:
                cell = val.get("v", val.get("i", ""))
            row.append(cell)
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(cell))
        rows.append(row)

    # Build table
    header = " | ".join(
        v.ljust(col_widths[i]) for i, v in enumerate(variables)
    )
    separator = "-+-".join("-" * w for w in col_widths)
    lines = [header, separator]
    for row in rows:
        line = " | ".join(
            cell.ljust(col_widths[i]) if i < len(col_widths) else cell
            for i, cell in enumerate(row)
        )
        lines.append(line)
    return "\n".join(lines)


def format_triples(response, output_format):
    """Format CONSTRUCT/DESCRIBE results."""
    triples = response.get("triples", [])

    if not triples:
        return "No triples."

    if output_format == "json":
        return json.dumps(triples, indent=2)

    lines = []
    for t in triples:
        s = _term_str(t.get("s"))
        p = _term_str(t.get("p"))
        o = _term_str(t.get("o"))
        lines.append(f"{s} {p} {o} .")
    return "\n".join(lines)


def _term_str(val):
    """Convert a wire-format term to a display string."""
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
                 output_format):

    api = Api(url=url, token=token).flow().id(flow_id)

    resp = api.sparql_query(
        query=query,
        user=user,
        collection=collection,
        limit=limit,
    )

    query_type = resp.get("query-type", "select")

    if query_type == "select":
        print(format_select(resp, output_format))
    elif query_type == "ask":
        print("true" if resp.get("ask-result") else "false")
    elif query_type in ("construct", "describe"):
        print(format_triples(resp, output_format))
    else:
        print(json.dumps(resp, indent=2))


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
            output_format=args.format,
        )

    except Exception as e:
        print(f"Exception: {e}", flush=True, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
