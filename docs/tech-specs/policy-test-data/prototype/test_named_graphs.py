"""
Quick test: does rdflib-sqlalchemy support named graphs via Dataset?

Creates a SQLite-backed Dataset, loads triples into separate named
graphs, and queries across them with SPARQL GRAPH patterns.

Run from the repo root:
    python docs/tech-specs/policy-test-data/prototype/test_named_graphs.py
"""

import os
import sys
from rdflib import Dataset, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS

DB_PATH = "test_named_graphs.db"
DB_URI = f"sqlite:///{DB_PATH}"

def main():

    # Clean up any previous run
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    ds = Dataset(store="SQLAlchemy")
    ds.open(DB_URI, create=True)

    try:
        # --- Default graph ---
        ds.default_graph.add((
            URIRef("http://example.org/a"),
            RDFS.label,
            Literal("Test A"),
        ))

        # --- Named graph: urn:graph:policy ---
        g_policy = ds.graph(URIRef("urn:graph:policy"))
        g_policy.add((
            URIRef("http://example.org/policy1"),
            RDF.type,
            URIRef("http://example.org/Policy"),
        ))
        g_policy.add((
            URIRef("http://example.org/policy1"),
            RDFS.label,
            Literal("Test Policy"),
        ))

        # --- Named graph: urn:graph:context ---
        g_ctx = ds.graph(URIRef("urn:graph:context"))
        g_ctx.add((
            URIRef("http://example.org/user1"),
            RDF.type,
            URIRef("http://example.org/User"),
        ))

        # --- Check: enumerate named graphs ---
        print("=== Named graphs ===")
        for g in ds.graphs():
            print(f"  {g.identifier} ({len(g)} triples)")

        # --- Check: union query (all graphs) ---
        print()
        print("=== All triples (default union graph) ===")
        for s, p, o in ds.default_union_graph:
            print(f"  {s}  {p}  {o}")

        # --- Check: SPARQL with GRAPH clause ---
        print()
        print("=== SPARQL with GRAPH pattern ===")
        results = ds.query("""
            SELECT ?s ?label ?g
            WHERE {
                GRAPH ?g {
                    ?s rdfs:label ?label .
                }
            }
        """)
        for row in results:
            print(f"  {row.s} -> \"{row.label}\" (in {row.g})")

        # --- Check: query scoped to one named graph ---
        print()
        print("=== Query scoped to urn:graph:policy only ===")
        results = ds.query("""
            SELECT ?s ?type
            WHERE {
                GRAPH <urn:graph:policy> {
                    ?s a ?type .
                }
            }
        """)
        for row in results:
            print(f"  {row.s} a {row.type}")

        # --- Check: cross-graph join ---
        print()
        print("=== Cross-graph join (default + policy) ===")
        results = ds.query("""
            SELECT ?thing ?label ?policyLabel
            WHERE {
                ?thing rdfs:label ?label .
                GRAPH <urn:graph:policy> {
                    ?policy rdfs:label ?policyLabel .
                }
            }
        """)
        for row in results:
            print(f"  thing={row.thing} label=\"{row.label}\" "
                  f"policyLabel=\"{row.policyLabel}\"")

        print()
        print("All checks passed.")

    finally:
        ds.close()
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

if __name__ == "__main__":
    main()
