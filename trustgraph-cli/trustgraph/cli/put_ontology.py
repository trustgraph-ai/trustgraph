"""
Loads an ontology from a file into the ontology config. Supports Turtle,
RDF/XML, N-Triples, and JSON-LD input formats — non-JSON-LD formats are
converted automatically via rdflib. Ontologies can also be fetched from
the ohi.dev ontology catalog with --ohi.
"""

import argparse
import hashlib
import os
import sys
from ohi import CatalogClient
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

# ohi.dev artifact formats we can load, in order of preference
OHI_FORMAT_MAP = {
    "owl-turtle": "turtle",
    "owl-rdfxml": "xml",
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


def fetch_ohi_artifact(client, publication):
    for ohi_fmt, fmt in OHI_FORMAT_MAP.items():
        for artifact in publication.artifacts:
            if artifact.format == ohi_fmt:
                data = client.get(artifact.url)
                if hashlib.sha256(data).hexdigest() != artifact.sha256:
                    raise ValueError(f"Checksum mismatch for {artifact.url}")
                return data, fmt
    raise ValueError(
        f"No OWL Turtle or RDF/XML artifact in {publication.base_url}"
    )


def fetch_from_ohi(reference, include_dependencies=False):
    client = CatalogClient()
    publication = client.inspect(reference)

    publications = [publication]
    if include_dependencies:
        publications += [
            client.inspect(dep.base_url) for dep in publication.dependencies
        ]

    # Dependencies are merged into one graph, as the ontology service
    # does not follow owl:imports
    g = Graph()
    for pub in publications:
        data, fmt = fetch_ohi_artifact(client, pub)
        g.parse(data=data, format=fmt)
        print(f"Fetched {pub.namespace}/{pub.name}@{pub.version} from ohi.dev")

    return g.serialize(format="turtle")


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
        '--ohi',
        metavar='REFERENCE',
        help='Fetch the ontology from the ohi.dev catalog instead of a file, '
             'e.g. w3c/prov-o@2013 (omit @version for the latest release)',
    )

    parser.add_argument(
        '--include-dependencies',
        action='store_true',
        help='With --ohi, also fetch the ontologies it depends on and '
             'merge them into one ontology',
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

    if args.ohi and (args.file or args.format):
        parser.error("--ohi cannot be used with a file or --format")

    if args.include_dependencies and not args.ohi:
        parser.error("--include-dependencies requires --ohi")

    try:

        if args.ohi:
            data = fetch_from_ohi(args.ohi, args.include_dependencies)
            fmt = "turtle"
        elif args.file:
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
