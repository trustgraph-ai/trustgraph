"""
Invokes an extraction service (definitions, relationships, or ontology).
Sends text to the specified extractor and returns the extracted triples
and entity contexts.
"""

import argparse
import json
import os
import sys
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")


def format_term(t):
    if not t or not isinstance(t, dict):
        return str(t)
    typ = t.get("type", "")
    if typ == "i":
        return t.get("iri", "")
    elif typ == "l":
        return t.get("value", "")
    elif typ == "iri":
        return t.get("iri", "")
    elif typ == "literal":
        return t.get("value", "")
    return str(t)


def run(url, flow_id, kind, text, document_id,
        token=None, workspace="default"):

    api = Api(url=url, token=token, workspace=workspace)
    socket = api.socket()
    flow = socket.flow(flow_id)

    try:
        result = flow.extract(
            kind=kind,
            text=text,
            document_id=document_id,
        )

        triples = result["triples"]
        entities = result["entity_contexts"]
        prov = result["provenance_triples"]

        print(f"Extracted {len(triples)} triple(s):")
        for t in triples:
            s = format_term(t.get("s"))
            p = format_term(t.get("p"))
            o = format_term(t.get("o"))
            print(f"  ({s}, {p}, {o})")

        if entities:
            print(f"\n{len(entities)} entity context(s):")
            for ec in entities:
                entity = format_term(ec.get("entity"))
                ctx = ec.get("context", "")
                print(f"  {entity}: {ctx[:80]}...")

        print(f"\n{len(prov)} provenance triple(s)")

    finally:
        socket.close()


def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-extraction',
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
        help=f'Flow ID (default: default)'
    )

    parser.add_argument(
        '-k', '--kind',
        required=True,
        choices=['definitions', 'relationships', 'ontology'],
        help='Extraction type',
    )

    parser.add_argument(
        '-d', '--document-id',
        default="",
        help='Source document ID (for provenance)',
    )

    parser.add_argument(
        'text',
        nargs='?',
        default=None,
        help='Text to extract from (reads from stdin if not provided)',
    )

    args = parser.parse_args()

    text = args.text
    if text is None:
        if args.document_id:
            text = ""
        else:
            text = sys.stdin.read()

    try:

        run(
            url=args.url,
            flow_id=args.flow_id,
            kind=args.kind,
            text=text,
            document_id=args.document_id,
            token=args.token,
            workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
