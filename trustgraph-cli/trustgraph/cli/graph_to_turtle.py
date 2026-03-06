"""
Connects to the graph query service and dumps all graph edges in Turtle
format with RDF-star support for quoted triples.
"""

import rdflib
import io
import sys
import argparse
import os

from trustgraph.api import Api, Uri
from trustgraph.knowledge import QuotedTriple

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_user = 'trustgraph'
default_collection = 'default'


def value_to_rdflib(val):
    """Convert a TrustGraph value to an rdflib term."""
    if isinstance(val, Uri):
        # Skip malformed URLs with spaces
        if " " in val:
            return None
        return rdflib.term.URIRef(val)
    elif isinstance(val, QuotedTriple):
        # RDF-star quoted triple
        s_term = value_to_rdflib(val.s)
        p_term = value_to_rdflib(val.p)
        o_term = value_to_rdflib(val.o)
        if s_term is None or p_term is None or o_term is None:
            return None
        # rdflib 6.x+ supports Triple as a term type
        try:
            return rdflib.term.Triple((s_term, p_term, o_term))
        except AttributeError:
            # Fallback for older rdflib versions - represent as string
            return rdflib.term.Literal(f"<<{val.s} {val.p} {val.o}>>")
    else:
        return rdflib.term.Literal(str(val))


def show_graph(url, flow_id, user, collection):

    api = Api(url).flow().id(flow_id)

    rows = api.triples_query(
        s=None, p=None, o=None,
        user=user, collection=collection,
        limit=10_000)

    g = rdflib.Graph()

    for row in rows:

        sv = rdflib.term.URIRef(row.s)
        pv = rdflib.term.URIRef(row.p)
        ov = value_to_rdflib(row.o)

        if ov is None:
            continue

        g.add((sv, pv, ov))

    g.serialize(destination="output.ttl", format="turtle")

    buf = io.BytesIO()

    g.serialize(destination=buf, format="turtle")

    sys.stdout.write(buf.getvalue().decode("utf-8"))


def main():

    parser = argparse.ArgumentParser(
        prog='tg-graph-to-turtle',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-f', '--flow-id',
        default="default",
        help=f'Flow ID (default: default)'
    )

    parser.add_argument(
        '-U', '--user',
        default=default_user,
        help=f'User ID (default: {default_user})'
    )

    parser.add_argument(
        '-C', '--collection',
        default=default_collection,
        help=f'Collection ID (default: {default_collection})'
    )

    args = parser.parse_args()

    try:

        show_graph(
            url = args.api_url,
            flow_id = args.flow_id,
            user = args.user,
            collection = args.collection,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()