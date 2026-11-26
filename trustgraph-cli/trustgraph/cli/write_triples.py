"""
Write triples to a named graph via the triples service.

Reads triples from stdin in N-Triples format (one triple per line):
  <subject> <predicate> <object> .

Examples:
  echo '<http://ex.org/s> <http://ex.org/p> "value" .' | tg-write-triples -g urn:graph:source
  cat data.nt | tg-write-triples -g urn:graph:source -C my-collection
"""

import argparse
import json
import os
import re
import sys
from trustgraph.api import Api
from . query_graph import build_term

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_collection = 'default'
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")


# N-Triples string escapes (ECHAR and UCHAR), the reverse of the escaping in
# nquads.py.
_UNESCAPE = re.compile(r"\\(?:u([0-9a-fA-F]{4})|U([0-9a-fA-F]{8})|(.))", re.DOTALL)
_ECHARS = {
    "t": "\t", "b": "\b", "n": "\n", "r": "\r", "f": "\f",
    '"': '"', "'": "'", "\\": "\\",
}


def unescape_ntriples(value):
    """Decode the backslash escapes of an N-Triples string literal."""

    def repl(m):
        code = m.group(1) or m.group(2)
        if code:
            try:
                return chr(int(code, 16))
            except (ValueError, OverflowError):
                return m.group(0)
        return _ECHARS.get(m.group(3), m.group(0))

    return _UNESCAPE.sub(repl, value)


def parse_ntriples_line(line):
    """Parse a single N-Triples line into (subject, predicate, object) term dicts.

    Handles:
      <iri> -> IRI term
      "value" -> literal term
      "value"@lang -> literal with language
      "value"^^<datatype> -> literal with datatype
    """
    line = line.strip()
    if not line or line.startswith('#'):
        return None

    if line.endswith(' .'):
        line = line[:-2].strip()
    elif line.endswith('.'):
        line = line[:-1].strip()

    parts = []
    i = 0
    while i < len(line) and len(parts) < 3:
        if line[i] == '<':
            end = line.index('>', i)
            parts.append(build_term(line[i+1:end], term_type='iri'))
            i = end + 1
        elif line[i] == '"':
            end = i + 1
            while end < len(line) and line[end] != '"':
                if line[end] == '\\':
                    end += 1
                end += 1
            value = unescape_ntriples(line[i+1:end])
            end += 1
            language = None
            datatype = None
            if end < len(line) and line[end] == '@':
                lang_start = end + 1
                lang_end = lang_start
                while lang_end < len(line) and not line[lang_end].isspace():
                    lang_end += 1
                language = line[lang_start:lang_end]
                end = lang_end
            elif end + 1 < len(line) and line[end:end+2] == '^^':
                end += 2
                if end < len(line) and line[end] == '<':
                    dt_end = line.index('>', end)
                    datatype = line[end+1:dt_end]
                    end = dt_end + 1
            parts.append(build_term(value, term_type='literal',
                                    datatype=datatype, language=language))
            i = end
        elif line[i].isspace():
            i += 1
        else:
            end = i
            while end < len(line) and not line[end].isspace():
                end += 1
            parts.append(build_term(line[i:end]))
            i = end

    if len(parts) != 3:
        return None

    return parts


def main():

    parser = argparse.ArgumentParser(
        prog='tg-write-triples',
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

    args = parser.parse_args()

    triples = []
    for line in sys.stdin:
        parsed = parse_ntriples_line(line)
        if parsed:
            s, p, o = parsed
            triples.append({"s": s, "p": p, "o": o})

    if not triples:
        print("No triples read from stdin", file=sys.stderr)
        sys.exit(1)

    try:
        socket = Api(args.api_url, token=args.token, workspace=args.workspace).socket()
        flow = socket.flow(args.flow_id)

        try:
            result = flow.triples_query(
                operation="write",
                collection=args.collection,
                **{
                    "named-graph": args.named_graph,
                    "triples": triples,
                },
            )
        finally:
            socket.close()

        if isinstance(result, dict) and "error" in result:
            err = result["error"]
            print(f"Error: {err.get('message', err)}", file=sys.stderr)
            sys.exit(1)

        print(f"Wrote {len(triples)} triples to {args.named_graph}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
