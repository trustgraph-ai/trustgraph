"""
Query the triple store with pattern matching and configurable output formats.

Unlike tg-show-graph which dumps the entire graph, this tool enables selective
queries by specifying any combination of subject, predicate, object, and graph.

Auto-detection rules for values:
  - Starts with http://, https://, urn:, or wrapped in <> -> IRI
  - Starts with << -> quoted triple (Turtle-style)
  - Anything else -> literal

Examples:
  tg-query-graph -s "http://example.org/entity"
  tg-query-graph -p "http://www.w3.org/2000/01/rdf-schema#label"
  tg-query-graph -o "Marie Curie" --object-language en
  tg-query-graph -o "<<http://ex.org/s http://ex.org/p http://ex.org/o>>"
"""

import argparse
import json
import os
import sys
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_user = 'trustgraph'
default_collection = 'default'
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)


def parse_inline_quoted_triple(value):
    """Parse inline Turtle-style quoted triple: <<s p o>>

    Args:
        value: String in format "<<subject predicate object>>"

    Returns:
        dict: Wire-format quoted triple term, or None if parsing fails
    """
    # Strip << and >> markers
    inner = value[2:-2].strip()

    # Split on whitespace, but respect quoted strings
    # Simple approach: split and handle common cases
    parts = []
    current = ""
    in_quotes = False
    quote_char = None

    for char in inner:
        if char in ('"', "'") and not in_quotes:
            in_quotes = True
            quote_char = char
            current += char
        elif char == quote_char and in_quotes:
            in_quotes = False
            quote_char = None
            current += char
        elif char.isspace() and not in_quotes:
            if current:
                parts.append(current)
                current = ""
        else:
            current += char

    if current:
        parts.append(current)

    if len(parts) != 3:
        raise ValueError(
            f"Quoted triple must have exactly 3 parts (s p o), got {len(parts)}: {parts}"
        )

    s_val, p_val, o_val = parts

    # Build the inner triple terms
    s_term = build_term(s_val)
    p_term = build_term(p_val)
    o_term = build_term(o_val)

    return {
        "t": "t",
        "tr": {
            "s": s_term,
            "p": p_term,
            "o": o_term
        }
    }


def build_term(value, term_type=None, datatype=None, language=None):
    """Build wire-format Term dict from CLI input.

    Auto-detection rules (when term_type is None):
      - Starts with http://, https://, urn: -> IRI
      - Wrapped in <> (e.g., <http://...>) -> IRI (angle brackets stripped)
      - Starts with << and ends with >> -> quoted triple
      - Anything else -> literal

    Args:
        value: The term value
        term_type: One of 'iri', 'literal', 'triple', or None for auto-detect
        datatype: Datatype for literal objects (e.g., xsd:integer)
        language: Language tag for literal objects (e.g., en)

    Returns:
        dict: Wire-format Term dict, or None if value is None
    """
    if value is None:
        return None

    # Auto-detect type if not specified
    if term_type is None:
        if value.startswith("<<") and value.endswith(">>"):
            term_type = "triple"
        elif value.startswith("<") and value.endswith(">") and not value.startswith("<<"):
            # Angle-bracket wrapped IRI: <http://...>
            value = value[1:-1]  # Strip < and >
            term_type = "iri"
        elif value.startswith(("http://", "https://", "urn:")):
            term_type = "iri"
        else:
            term_type = "literal"

    if term_type == "iri":
        # Strip angle brackets if present
        if value.startswith("<") and value.endswith(">"):
            value = value[1:-1]
        return {"t": "i", "i": value}
    elif term_type == "literal":
        result = {"t": "l", "v": value}
        if datatype:
            result["dt"] = datatype
        if language:
            result["ln"] = language
        return result
    elif term_type == "triple":
        # Check if it's inline Turtle-style
        if value.startswith("<<") and value.endswith(">>"):
            return parse_inline_quoted_triple(value)
        else:
            # Assume it's raw JSON (legacy support)
            triple_data = json.loads(value)
            return {"t": "t", "tr": triple_data}
    else:
        raise ValueError(f"Unknown term type: {term_type}")


def build_quoted_triple_term(qt_subject, qt_subject_type,
                              qt_predicate,
                              qt_object, qt_object_type,
                              qt_object_datatype, qt_object_language):
    """Build a quoted triple term from --qt-* arguments.

    Returns:
        dict: Wire-format quoted triple term, or None if no qt args provided
    """
    # Check if any qt args were provided
    if not any([qt_subject, qt_predicate, qt_object]):
        return None

    # Subject (IRI or nested triple)
    s_term = build_term(qt_subject, term_type=qt_subject_type)

    # Predicate (always IRI)
    p_term = build_term(qt_predicate, term_type='iri')

    # Object (IRI, literal, or nested triple)
    o_term = build_term(
        qt_object,
        term_type=qt_object_type,
        datatype=qt_object_datatype,
        language=qt_object_language
    )

    return {
        "t": "t",
        "tr": {
            "s": s_term,
            "p": p_term,
            "o": o_term
        }
    }


def format_term(term_dict):
    """Format a term dict for display in space/pipe output formats.

    Handles multiple wire format styles:
    - Short form (send): {"t": "i", "i": "..."}, {"t": "l", "v": "..."}
    - Long form (receive): {"type": "i", "iri": "..."}, {"type": "l", "value": "..."}
    - Raw quoted triple: {"s": {...}, "p": {...}, "o": {...}} (no type wrapper)
    - Stringified quoted triple in IRI: {"t": "i", "i": "{\"s\":...}"} (backend quirk)

    Args:
        term_dict: Wire-format term dict

    Returns:
        str: Formatted string representation
    """
    if not term_dict:
        return ""

    # Get type - handle both short and long form
    t = term_dict.get("t") or term_dict.get("type")

    if t == "i":
        # IRI - handle both "i" and "iri" keys
        iri_value = term_dict.get("i") or term_dict.get("iri", "")
        # Check if IRI value is actually a stringified quoted triple (backend quirk)
        if iri_value.startswith('{"s":') or iri_value.startswith("{\"s\":"):
            try:
                parsed = json.loads(iri_value)
                if "s" in parsed and "p" in parsed and "o" in parsed:
                    # It's a stringified quoted triple - format it properly
                    s = format_term(parsed.get("s", {}))
                    p = format_term(parsed.get("p", {}))
                    o = format_term(parsed.get("o", {}))
                    return f"<<{s} {p} {o}>>"
            except json.JSONDecodeError:
                pass  # Not valid JSON, treat as regular IRI
        return iri_value
    elif t == "l":
        # Literal - handle both short and long form keys
        value = term_dict.get("v") or term_dict.get("value", "")
        result = f'"{value}"'
        # Language tag
        lang = term_dict.get("ln") or term_dict.get("language")
        if lang:
            result += f'@{lang}'
        else:
            # Datatype
            dt = term_dict.get("dt") or term_dict.get("datatype")
            if dt:
                result += f'^^{dt}'
        return result
    elif t == "t":
        # Quoted triple - handle both "tr" and "triple" keys
        tr = term_dict.get("tr") or term_dict.get("triple", {})
        s = format_term(tr.get("s", {}))
        p = format_term(tr.get("p", {}))
        o = format_term(tr.get("o", {}))
        return f"<<{s} {p} {o}>>"
    elif t is None and "s" in term_dict and "p" in term_dict and "o" in term_dict:
        # Raw quoted triple without type wrapper (has s, p, o keys directly)
        s = format_term(term_dict.get("s", {}))
        p = format_term(term_dict.get("p", {}))
        o = format_term(term_dict.get("o", {}))
        return f"<<{s} {p} {o}>>"

    return str(term_dict)


def output_space(triples, headers=False):
    """Output triples in space-separated format."""
    if headers:
        print("subject predicate object")
    for triple in triples:
        s = format_term(triple.get("s", {}))
        p = format_term(triple.get("p", {}))
        o = format_term(triple.get("o", {}))
        print(s, p, o)


def output_pipe(triples, headers=False):
    """Output triples in pipe-separated format."""
    if headers:
        print("subject|predicate|object")
    for triple in triples:
        s = format_term(triple.get("s", {}))
        p = format_term(triple.get("p", {}))
        o = format_term(triple.get("o", {}))
        print(f"{s}|{p}|{o}")


def output_json(triples):
    """Output triples as a JSON array."""
    print(json.dumps(triples, indent=2))


def output_jsonl(triples):
    """Output triples as JSON Lines (one object per line)."""
    for triple in triples:
        print(json.dumps(triple))


def query_graph(
    url, flow_id, user, collection, limit, batch_size,
    subject=None, predicate=None, obj=None, graph=None,
    output_format="space", headers=False, token=None
):
    """Query the triple store with pattern matching.

    Uses the API's triples_query_stream for efficient streaming delivery.
    """
    socket = Api(url, token=token).socket()
    flow = socket.flow(flow_id)

    all_triples = []

    try:
        # Use triples_query_stream - accepts Term dicts directly
        for triples in flow.triples_query_stream(
            s=subject,
            p=predicate,
            o=obj,
            g=graph,
            user=user,
            collection=collection,
            limit=limit,
            batch_size=batch_size,
        ):
            if not isinstance(triples, list):
                triples = [triples] if triples else []

            if output_format in ("json",):
                # Collect all triples for JSON array output
                all_triples.extend(triples)
            else:
                # Stream output for other formats
                if output_format == "space":
                    output_space(triples, headers=headers and not all_triples)
                elif output_format == "pipe":
                    output_pipe(triples, headers=headers and not all_triples)
                elif output_format == "jsonl":
                    output_jsonl(triples)
                # Track that we've output something (for headers logic)
                all_triples.extend([None] * len(triples))

        # Output collected JSON array
        if output_format == "json":
            output_json(all_triples)

    finally:
        socket.close()


def main():
    parser = argparse.ArgumentParser(
        prog='tg-query-graph',
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Outer triple filters
    outer_group = parser.add_argument_group('Outer triple filters')

    outer_group.add_argument(
        '-s', '--subject',
        metavar='VALUE',
        help='Subject filter (auto-detected as IRI or literal)',
    )

    outer_group.add_argument(
        '-p', '--predicate',
        metavar='VALUE',
        help='Predicate filter (auto-detected as IRI)',
    )

    outer_group.add_argument(
        '-o', '--object',
        dest='obj',
        metavar='VALUE',
        help='Object filter (IRI, literal, or <<quoted triple>>)',
    )

    outer_group.add_argument(
        '--object-type',
        choices=['iri', 'literal', 'triple'],
        metavar='TYPE',
        help='Override object type detection: iri, literal, triple',
    )

    outer_group.add_argument(
        '--object-datatype',
        metavar='DATATYPE',
        help='Datatype for literal object (e.g., xsd:integer)',
    )

    outer_group.add_argument(
        '--object-language',
        metavar='LANG',
        help='Language tag for literal object (e.g., en)',
    )

    outer_group.add_argument(
        '-g', '--graph',
        metavar='VALUE',
        help='Named graph filter',
    )

    # Quoted triple filters (alternative to inline <<s p o>> syntax)
    qt_group = parser.add_argument_group(
        'Quoted triple filters',
        'Build object as quoted triple using explicit fields (alternative to -o "<<s p o>>")'
    )

    qt_group.add_argument(
        '--qt-subject',
        metavar='VALUE',
        help='Quoted triple subject',
    )

    qt_group.add_argument(
        '--qt-subject-type',
        choices=['iri', 'triple'],
        metavar='TYPE',
        help='Override qt-subject type: iri, triple',
    )

    qt_group.add_argument(
        '--qt-predicate',
        metavar='VALUE',
        help='Quoted triple predicate (always IRI)',
    )

    qt_group.add_argument(
        '--qt-object',
        metavar='VALUE',
        help='Quoted triple object',
    )

    qt_group.add_argument(
        '--qt-object-type',
        choices=['iri', 'literal', 'triple'],
        metavar='TYPE',
        help='Override qt-object type: iri, literal, triple',
    )

    qt_group.add_argument(
        '--qt-object-datatype',
        metavar='DATATYPE',
        help='Datatype for qt-object literal',
    )

    qt_group.add_argument(
        '--qt-object-language',
        metavar='LANG',
        help='Language tag for qt-object literal',
    )

    # Standard parameters
    std_group = parser.add_argument_group('Standard parameters')

    std_group.add_argument(
        '-u', '--api-url',
        default=default_url,
        metavar='URL',
        help=f'API URL (default: {default_url})',
    )

    std_group.add_argument(
        '-f', '--flow-id',
        default="default",
        metavar='ID',
        help='Flow ID (default: default)'
    )

    std_group.add_argument(
        '-U', '--user',
        default=default_user,
        metavar='USER',
        help=f'User/keyspace (default: {default_user})'
    )

    std_group.add_argument(
        '-C', '--collection',
        default=default_collection,
        metavar='COLL',
        help=f'Collection (default: {default_collection})'
    )

    std_group.add_argument(
        '-t', '--token',
        default=default_token,
        metavar='TOKEN',
        help='Auth token (default: $TRUSTGRAPH_TOKEN)',
    )

    std_group.add_argument(
        '-l', '--limit',
        type=int,
        default=1000,
        metavar='N',
        help='Max results (default: 1000)',
    )

    std_group.add_argument(
        '-b', '--batch-size',
        type=int,
        default=20,
        metavar='N',
        help='Streaming batch size (default: 20)',
    )

    # Output options
    out_group = parser.add_argument_group('Output options')

    out_group.add_argument(
        '--format',
        choices=['space', 'pipe', 'json', 'jsonl'],
        default='space',
        metavar='FORMAT',
        help='Output format: space, pipe, json, jsonl (default: space)',
    )

    out_group.add_argument(
        '-H', '--headers',
        action='store_true',
        help='Show column headers (for space/pipe formats)',
    )

    args = parser.parse_args()

    try:
        # Build term dicts from CLI arguments
        subject_term = build_term(args.subject) if args.subject else None
        predicate_term = build_term(args.predicate) if args.predicate else None

        # Check for --qt-* args to build quoted triple as object
        qt_term = build_quoted_triple_term(
            qt_subject=args.qt_subject,
            qt_subject_type=args.qt_subject_type,
            qt_predicate=args.qt_predicate,
            qt_object=args.qt_object,
            qt_object_type=args.qt_object_type,
            qt_object_datatype=args.qt_object_datatype,
            qt_object_language=args.qt_object_language,
        )

        # Object: use --qt-* args if provided, otherwise use -o
        if qt_term is not None:
            if args.obj:
                parser.error("Cannot use both -o/--object and --qt-* arguments")
            obj_term = qt_term
        elif args.obj:
            obj_term = build_term(
                args.obj,
                term_type=args.object_type,
                datatype=args.object_datatype,
                language=args.object_language
            )
        else:
            obj_term = None

        # Graph is a plain IRI string, not a Term
        # None = all graphs, "" = default graph only, "uri" = specific graph
        graph_value = args.graph

        query_graph(
            url=args.api_url,
            flow_id=args.flow_id,
            user=args.user,
            collection=args.collection,
            limit=args.limit,
            batch_size=args.batch_size,
            subject=subject_term,
            predicate=predicate_term,
            obj=obj_term,
            graph=graph_value,
            output_format=args.format,
            headers=args.headers,
            token=args.token,
        )

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Exception: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
