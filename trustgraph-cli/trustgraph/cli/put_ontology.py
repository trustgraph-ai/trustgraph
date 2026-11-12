"""
Loads an ontology from a file into the ontology config. Supports Turtle,
RDF/XML, N-Triples, and JSON-LD input formats — non-JSON-LD formats are
converted automatically via rdflib.
"""

import argparse
import os
import sys
from rdflib import Graph
from trustgraph.api import Api
from trustgraph.api.types import ConfigValue

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

FORMAT_MAP = {
    ".ttl": "turtle",
    ".turtle": "turtle",
    ".rdf": "xml",
    ".owl": "xml",
    ".xml": "xml",
    ".nt": "nt",
    ".ntriples": "nt",
    ".jsonld": "json-ld",
    ".json": "json-ld",
}


def detect_format(filename):
    ext = os.path.splitext(filename)[1].lower()
    fmt = FORMAT_MAP.get(ext)
    if fmt is None:
        raise ValueError(
            f"Cannot detect format from extension '{ext}'. "
            f"Use --format to specify one of: turtle, xml, nt, json-ld"
        )
    return fmt


def to_jsonld(data, fmt):
    if fmt == "json-ld":
        return data
    g = Graph()
    g.parse(data=data, format=fmt)
    return g.serialize(format="json-ld")


def put_ontology(url, ontology_id, data, fmt, token=None,
                 workspace="default"):
    jsonld = to_jsonld(data, fmt)

    api = Api(url, token=token, workspace=workspace).config()

    config_value = ConfigValue(type="ontology", key=ontology_id, value=jsonld)
    api.put([config_value])

    print(f"Ontology '{ontology_id}' loaded ({fmt} → json-ld)")


def main():

    parser = argparse.ArgumentParser(
        prog='tg-put-ontology',
        description=__doc__,
    )

    parser.add_argument(
        'file',
        nargs='?',
        help='Ontology file to load (omit to read from stdin)',
    )

    parser.add_argument(
        '--ontology-id', '-i',
        required=True,
        help='Ontology identifier',
    )

    parser.add_argument(
        '--format', '-f',
        choices=['turtle', 'xml', 'nt', 'json-ld'],
        default=None,
        help='Input format (default: auto-detect from file extension)',
    )

    parser.add_argument(
        '-u', '--api-url',
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

    args = parser.parse_args()

    try:

        if args.file:
            with open(args.file, 'r') as f:
                data = f.read()
            fmt = args.format or detect_format(args.file)
        else:
            data = sys.stdin.read()
            if args.format is None:
                parser.error(
                    "--format is required when reading from stdin"
                )
            fmt = args.format

        put_ontology(
            url=args.api_url,
            ontology_id=args.ontology_id,
            data=data,
            fmt=fmt,
            token=args.token,
            workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
