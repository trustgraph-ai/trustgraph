"""
Invoke the knowledge retrieval service.  Retrieves a ranked subgraph
from a query, concepts, or entity URIs.

By default, extracts concepts from the query string using the
concept extraction service, then retrieves matching edges.
Use -c to provide concepts directly, or -e to provide entity URIs.
"""

import argparse
import json
import os
import sys
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")


def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-knowledge-retrieval',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-t', '--token',
        default=default_token,
        help='Authentication token (default: $TRUSTGRAPH_TOKEN)',
    )

    parser.add_argument(
        '-w', '--workspace',
        default=default_workspace,
        help=f'Workspace (default: {default_workspace})',
    )

    parser.add_argument(
        '-f', '--flow-id',
        default="default",
        help='Flow ID (default: default)',
    )

    parser.add_argument(
        '-j', '--json',
        action='store_true',
        help='Output as JSON',
    )

    parser.add_argument(
        '-T', '--turtle',
        action='store_true',
        help='Output as Turtle RDF',
    )

    parser.add_argument(
        '-L', '--jsonld',
        action='store_true',
        help='Output as JSON-LD',
    )

    parser.add_argument(
        '-c', '--concept',
        action='append',
        dest='concepts',
        default=[],
        help='Concept to search for, skips extraction (repeatable)',
    )

    parser.add_argument(
        '-e', '--entity',
        action='append',
        dest='entities',
        default=[],
        help='Entity URI to traverse from, skips embedding (repeatable)',
    )

    parser.add_argument(
        '--entity-limit',
        type=int, default=50,
        help='Max entities from embedding search (default: 50)',
    )

    parser.add_argument(
        '--edge-limit',
        type=int, default=25,
        help='Max edges returned (default: 25)',
    )

    parser.add_argument(
        '--max-hops',
        type=int, default=2,
        help='Max traversal hops (default: 2)',
    )

    parser.add_argument(
        'query',
        nargs='?',
        help='Query text (extracts concepts automatically)',
    )

    args = parser.parse_args()

    if not args.query and not args.concepts and not args.entities:
        print(
            "Error: provide a query, --concept, or --entity",
            file=sys.stderr,
        )
        sys.exit(1)

    try:

        api = Api(
            url=args.url, token=args.token, workspace=args.workspace,
        )
        socket = api.socket()

        try:

            concepts = list(args.concepts)

            # If a query is provided and no explicit concepts/entities,
            # call concept extraction first
            if args.query and not concepts and not args.entities:
                print(
                    f"Extracting concepts from query...",
                    file=sys.stderr,
                )
                ce_result = socket._send_request_sync(
                    "concept-extraction", args.flow_id,
                    {"query": args.query},
                )
                if ce_result.get("error"):
                    err = ce_result["error"]
                    print(
                        f"Error: [{err.get('type', '?')}] "
                        f"{err.get('message', '?')}",
                        file=sys.stderr,
                    )
                    sys.exit(1)

                concepts = ce_result.get("concepts", [])
                print(
                    f"Concepts: {', '.join(concepts)}",
                    file=sys.stderr,
                )

            request = {}
            if concepts:
                request["concepts"] = concepts
            if args.entities:
                request["entities"] = args.entities
            if args.entity_limit != 50:
                request["entity-limit"] = args.entity_limit
            if args.edge_limit != 25:
                request["edge-limit"] = args.edge_limit
            if args.max_hops != 2:
                request["max-path-length"] = args.max_hops

            result = socket._send_request_sync(
                "knowledge-retrieval", args.flow_id,
                request,
            )

        finally:
            socket.close()

        if result.get("error"):
            err = result["error"]
            print(
                f"Error: [{err.get('type', '?')}] {err.get('message', '?')}",
                file=sys.stderr,
            )
            sys.exit(1)

        if args.json:
            print(json.dumps(result, indent=2))
        elif args.turtle or args.jsonld:
            from rdflib import Graph, URIRef, Literal, Namespace
            g = Graph()
            edges = result.get("edges", [])
            for e in edges:
                s_val = e.get("s", "")
                p_val = e.get("p", "")
                o_val = e.get("o", "")
                s = URIRef(s_val) if s_val.startswith(("http://", "https://", "urn:")) else Literal(s_val)
                p = URIRef(p_val) if p_val.startswith(("http://", "https://", "urn:")) else URIRef(f"urn:predicate:{p_val}")
                o = URIRef(o_val) if o_val.startswith(("http://", "https://", "urn:")) else Literal(o_val)
                g.add((s, p, o))
            fmt = "json-ld" if args.jsonld else "turtle"
            print(g.serialize(format=fmt))
        else:
            edges = result.get("edges", [])
            seeds = result.get("seed-entities", [])
            concepts = result.get("concepts", [])

            print(f"Concepts: {', '.join(concepts)}")
            print(f"Seed entities: {len(seeds)}")
            print(f"Edges: {len(edges)}")
            print()

            for i, e in enumerate(edges, 1):
                s_label = e.get("s-label", e.get("s", "?"))
                p_label = e.get("p-label", e.get("p", "?"))
                o_label = e.get("o-label", e.get("o", "?"))
                score = e.get("score", 0)
                concept = e.get("concept", "")

                print(f"  {i:3d}. [{score:.4f}] {s_label}")
                print(f"       -- {p_label} -->")
                print(f"       {o_label}")
                if concept:
                    print(f"       (concept: {concept})")
                print()

    except Exception as e:
        print("Exception:", e, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
