"""
Connects to the graph query service and dumps all graph edges in Turtle
format with RDF-star support for quoted triples.
Uses streaming mode for lower time-to-first-processing.
"""

import rdflib
import io
import sys
import argparse
import os

from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_user = 'trustgraph'
default_collection = 'default'
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)


def term_to_rdflib(term):
    """Convert a wire-format term to an rdflib term."""
    if term is None:
        return None

    t = term.get("t", "")

    if t == "i":  # IRI
        iri = term.get("i", "")
        # Skip malformed URLs with spaces
        if " " in iri:
            return None
        return rdflib.term.URIRef(iri)
    elif t == "l":  # Literal
        value = term.get("v", "")
        datatype = term.get("d")
        language = term.get("l")
        if language:
            return rdflib.term.Literal(value, lang=language)
        elif datatype:
            return rdflib.term.Literal(value, datatype=rdflib.term.URIRef(datatype))
        else:
            return rdflib.term.Literal(value)
    elif t == "r":  # Quoted triple (RDF-star)
        triple = term.get("r", {})
        s_term = term_to_rdflib(triple.get("s"))
        p_term = term_to_rdflib(triple.get("p"))
        o_term = term_to_rdflib(triple.get("o"))
        if s_term is None or p_term is None or o_term is None:
            return None
        try:
            return rdflib.term.Triple((s_term, p_term, o_term))
        except AttributeError:
            # Fallback for older rdflib versions
            return rdflib.term.Literal(f"<<{s_term} {p_term} {o_term}>>")
    else:
        # Fallback
        return rdflib.term.Literal(str(term))


def show_graph(url, flow_id, user, collection, limit, batch_size, token=None):

    socket = Api(url, token=token).socket()
    flow = socket.flow(flow_id)

    g = rdflib.Graph()

    try:
        for batch in flow.triples_query_stream(
            s=None, p=None, o=None,
            user=user, collection=collection,
            limit=limit,
            batch_size=batch_size,
        ):
            for triple in batch:
                sv = term_to_rdflib(triple.get("s"))
                pv = term_to_rdflib(triple.get("p"))
                ov = term_to_rdflib(triple.get("o"))

                if sv is None or pv is None or ov is None:
                    continue

                g.add((sv, pv, ov))
    finally:
        socket.close()

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

    parser.add_argument(
        '-t', '--token',
        default=default_token,
        help='Authentication token (default: $TRUSTGRAPH_TOKEN)',
    )

    parser.add_argument(
        '-l', '--limit',
        type=int,
        default=10000,
        help='Maximum number of triples to return (default: 10000)',
    )

    parser.add_argument(
        '-b', '--batch-size',
        type=int,
        default=20,
        help='Triples per streaming batch (default: 20)',
    )

    args = parser.parse_args()

    try:

        show_graph(
            url = args.api_url,
            flow_id = args.flow_id,
            user = args.user,
            collection = args.collection,
            limit = args.limit,
            batch_size = args.batch_size,
            token = args.token,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()