"""
Load Bletchley Park data into separate rdflib Graphs and dump
the policy graph.

- Default graph: bletchley-graph.ttl
- Policy graph:  bletchley-policies.ttl (urn:graph:policy)

Run from the repo root:
    python docs/tech-specs/policy-test-data/prototype/load_and_dump.py
"""

from pathlib import Path
from rdflib import Graph

DATA_DIR = Path(__file__).resolve().parent.parent

def load_graphs():
    graphs = {}

    # Default graph — knowledge data
    default = Graph()
    default.parse(DATA_DIR / "bletchley-graph.ttl", format="turtle")
    graphs[""] = default

    # Policy graph
    policy = Graph()
    policy.parse(DATA_DIR / "bletchley-policies.ttl", format="turtle")
    graphs["urn:graph:policy"] = policy

    return graphs

def main():
    graphs = load_graphs()

    print(f"Default graph: {len(graphs[''])} triples")
    print(f"Policy graph:  {len(graphs['urn:graph:policy'])} triples")
    print()

    print("=== Policy graph triples ===")
    for s, p, o in sorted(graphs["urn:graph:policy"]):
        print(f"  {s}")
        print(f"    {p}")
        print(f"    {o}")
        print()

if __name__ == "__main__":
    main()
