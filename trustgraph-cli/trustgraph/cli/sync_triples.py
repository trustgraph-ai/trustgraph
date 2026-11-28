"""
Sync triples to a named graph via diff-load.

Reads triples from one or more RDF files (Turtle by default), partitions
them by subject, and sends chunked sync requests.  Only triples that
differ from the current graph state are written.

Modes:
  sync      (default) Insert new triples, delete absent triples.
            The graph at the current version will exactly match the input.
  additive  Insert new triples only; existing triples are left alone.

Examples:
  tg-sync-triples -g urn:graph:source data.ttl
  tg-sync-triples -g urn:graph:source --format nt data.nt
  tg-sync-triples -g urn:graph:source --mode additive data.ttl
  tg-sync-triples -g urn:graph:source a.ttl b.ttl
"""

import argparse
import os
import sys
import rdflib
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_collection = 'default'
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

FORMAT_CHOICES = ['turtle', 'nt', 'xml', 'n3', 'json-ld', 'trig']


def rdflib_term_to_wire(term):
    if isinstance(term, rdflib.term.URIRef):
        return {"t": "i", "i": str(term)}
    elif isinstance(term, rdflib.term.Literal):
        result = {"t": "l", "v": str(term)}
        if term.datatype:
            result["dt"] = str(term.datatype)
        if term.language:
            result["ln"] = str(term.language)
        return result
    else:
        raise ValueError(f"Unsupported RDF term type: {type(term)}")


def load_triples_from_file(path, fmt):
    g = rdflib.Graph()
    if path == "-":
        g.parse(sys.stdin, format=fmt)
    else:
        g.parse(path, format=fmt)

    triples = []
    for s, p, o in g:
        triples.append({
            "s": rdflib_term_to_wire(s),
            "p": rdflib_term_to_wire(p),
            "o": rdflib_term_to_wire(o),
        })
    return triples


def chunk_by_subject(triples, chunk_size):
    """Partition triples into chunks at subject boundaries.

    Returns list of (s_start, s_end, chunk_triples) where s_start is
    inclusive, s_end is exclusive, and None means unbounded.
    """
    if not triples:
        return [(None, None, [])]

    triples.sort(key=lambda t: t["s"]["i"])

    subjects = []
    seen = set()
    for t in triples:
        s = t["s"]["i"]
        if s not in seen:
            seen.add(s)
            subjects.append(s)

    chunks = []
    i = 0

    while i < len(subjects):
        boundary_start = subjects[i]
        boundary_end_idx = min(i + chunk_size, len(subjects))
        boundary_end = subjects[boundary_end_idx] if boundary_end_idx < len(subjects) else None

        chunk_triples = [
            t for t in triples
            if t["s"]["i"] >= boundary_start
            and (boundary_end is None or t["s"]["i"] < boundary_end)
        ]

        s_start = None if i == 0 else boundary_start
        s_end = boundary_end

        chunks.append((s_start, s_end, chunk_triples))
        i = boundary_end_idx

    if chunks and chunks[0][0] is not None:
        chunks.insert(0, (None, chunks[0][0], []))

    return chunks


def main():

    parser = argparse.ArgumentParser(
        prog='tg-sync-triples',
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
        required=True,
        help='Named graph IRI',
    )

    parser.add_argument(
        '--mode',
        choices=['sync', 'additive'],
        default='sync',
        help='Sync mode (default: sync)',
    )

    parser.add_argument(
        '--chunk-size',
        type=int,
        default=500,
        help='Distinct subjects per chunk (default: 500)',
    )

    parser.add_argument(
        '-F', '--format',
        choices=FORMAT_CHOICES,
        default='turtle',
        help='RDF format (default: turtle)',
    )

    parser.add_argument(
        'files', nargs='*', default=['-'],
        help='RDF files to load (default: stdin)',
    )

    args = parser.parse_args()

    triples = []
    for path in args.files:
        try:
            loaded = load_triples_from_file(path, args.format)
            if path != "-":
                print(f"Parsed {len(loaded)} triples from {path}",
                      file=sys.stderr)
            triples.extend(loaded)
        except Exception as e:
            print(f"Error parsing {path}: {e}", file=sys.stderr)
            sys.exit(1)

    if not triples:
        print("No triples loaded", file=sys.stderr)
        sys.exit(1)

    chunks = chunk_by_subject(triples, args.chunk_size)
    is_sync = args.mode == "sync"

    try:
        socket = Api(args.api_url, token=args.token, workspace=args.workspace).socket()
        flow = socket.flow(args.flow_id)

        total_inserted = 0
        total_deleted = 0

        try:
            for i, (s_start, s_end, chunk_triples) in enumerate(chunks):
                result = flow.triples_query(
                    operation="sync-triples",
                    collection=args.collection,
                    sync=is_sync,
                    **{
                        "named-graph": args.named_graph,
                        "triples": chunk_triples,
                        "s-start": s_start,
                        "s-end": s_end,
                    },
                )

                if isinstance(result, dict) and "error" in result:
                    err = result["error"]
                    print(
                        f"Error on chunk {i+1}/{len(chunks)}: "
                        f"{err.get('message', err)}",
                        file=sys.stderr,
                    )
                    sys.exit(1)

                print(
                    f"Chunk {i+1}/{len(chunks)}: "
                    f"{len(chunk_triples)} triples "
                    f"[{s_start or '*'}..{s_end or '*'})",
                    file=sys.stderr,
                )

        finally:
            socket.close()

        print(
            f"Sync complete: {len(triples)} input triples, "
            f"{len(chunks)} chunks, mode={args.mode}"
        )

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
