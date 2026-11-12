"""
Retrieves a loaded ontology from the config service. Can output as
JSON-LD (default) or convert to Turtle, RDF/XML, or N-Triples via rdflib.
"""

import argparse
import os
import sys
from rdflib import Graph
from trustgraph.api import Api
from trustgraph.api.types import ConfigKey

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")


def from_jsonld(jsonld, fmt):
    if fmt == "json-ld":
        return jsonld
    g = Graph()
    g.parse(data=jsonld, format="json-ld")
    return g.serialize(format=fmt)


def get_ontology(url, ontology_id, fmt, token=None, workspace="default"):
    api = Api(url, token=token, workspace=workspace).config()

    config_key = ConfigKey(type="ontology", key=ontology_id)
    values = api.get([config_key])

    if not values:
        raise Exception(
            f"Ontology not found: {ontology_id}"
        )

    jsonld = values[0].value
    print(from_jsonld(jsonld, fmt))


def main():

    parser = argparse.ArgumentParser(
        prog='tg-get-ontology',
        description=__doc__,
    )

    parser.add_argument(
        '--ontology-id', '-i',
        required=True,
        help='Ontology identifier',
    )

    parser.add_argument(
        '--format', '-f',
        choices=['json-ld', 'turtle', 'xml', 'nt'],
        default='json-ld',
        help='Output format (default: json-ld)',
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

        get_ontology(
            url=args.api_url,
            ontology_id=args.ontology_id,
            fmt=args.format,
            token=args.token,
            workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
