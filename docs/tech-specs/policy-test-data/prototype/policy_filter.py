"""
Prototype: incremental policy-filtered retrieval.

Demonstrates the production retrieval pattern at small scale:
1. Query returns triples in small batches
2. Extract candidate nodes from each batch
3. Parse policies to discover what node properties they need
4. Hydrate each node by fetching those properties via the adapter
5. Build a tiny evaluation graph (node properties + user context)
6. Run each policy's SPARQL target against the evaluation graph
7. Filter nodes that match, report determinations

Run from the repo root:
    python docs/tech-specs/policy-test-data/prototype/policy_filter.py
"""

from pathlib import Path
from rdflib import Graph, URIRef, Literal, BNode, Namespace
from rdflib.namespace import RDF, RDFS, XSD
import re

DATA_DIR = Path(__file__).resolve().parent.parent

# Namespaces
BPO = Namespace("http://bletchleypark.gov.uk/ontology/")
BP = Namespace("http://bletchleypark.gov.uk/data/")
SH = Namespace("http://www.w3.org/ns/shacl#")
TG_POL = Namespace("https://trustgraph.ai/ontology/policy/")
TG_UC = Namespace("https://trustgraph.ai/ontology/user-context/")


# -----------------------------------------------------------------
# Graph adapter — mirrors TriplesClient.query(s, p, o, g)
# -----------------------------------------------------------------

class GraphAdapter:
    """Triple pattern query interface backed by rdflib Graphs."""

    def __init__(self):
        self.graphs = {}
        self.query_count = 0

    def load(self, name, path, fmt="turtle"):
        g = Graph()
        g.parse(path, format=fmt)
        self.graphs[name] = g

    def query(self, s=None, p=None, o=None, g=""):
        """Query a specific graph by triple pattern.
        g="" is the default graph, g=None searches all."""
        self.query_count += 1
        results = []

        if g is None:
            targets = self.graphs.values()
        else:
            target = self.graphs.get(g)
            if target is None:
                return []
            targets = [target]

        for graph in targets:
            for t in graph.triples((s, p, o)):
                results.append(t)

        return results


# -----------------------------------------------------------------
# Policy loader — extracts policies from the policy graph
# -----------------------------------------------------------------

class Policy:
    def __init__(self, uri, label, determination, order, sparql_select):
        self.uri = uri
        self.label = label
        self.determination = determination
        self.order = order
        self.sparql_select = sparql_select


def load_policies(adapter):
    """Load policies from urn:graph:policy, sorted by sh:order."""
    policies = []

    shapes = adapter.query(p=RDF.type, o=SH.NodeShape, g="urn:graph:policy")

    for shape_uri, _, _ in shapes:
        # Get label
        labels = adapter.query(s=shape_uri, p=RDFS.label, g="urn:graph:policy")
        label = str(labels[0][2]) if labels else str(shape_uri)

        # Get determination
        dets = adapter.query(
            s=shape_uri, p=TG_POL.producesDetermination, g="urn:graph:policy"
        )
        determination = str(dets[0][2]).split("/")[-1] if dets else "Unknown"

        # Get order
        orders = adapter.query(s=shape_uri, p=SH.order, g="urn:graph:policy")
        order = int(orders[0][2]) if orders else 99

        # Get SPARQL target — follow the blank node chain
        targets = adapter.query(s=shape_uri, p=SH.target, g="urn:graph:policy")
        sparql_select = None
        for _, _, target_node in targets:
            selects = adapter.query(
                s=target_node, p=SH.select, g="urn:graph:policy"
            )
            if selects:
                sparql_select = str(selects[0][2])
                break

        if sparql_select:
            policies.append(Policy(
                uri=shape_uri, label=label,
                determination=determination, order=order,
                sparql_select=sparql_select,
            ))

    policies.sort(key=lambda p: p.order)
    return policies


# -----------------------------------------------------------------
# Policy property analysis — what does a policy need to know
# about a node?
# -----------------------------------------------------------------

def extract_node_predicates(sparql_select):
    """Parse a SPARQL SELECT to find predicates used on ?this.

    Looks for patterns like:
        ?this bpo:classification ...
        ?this bpo:section ...
        ?this a bpo:SomeType .
    """
    predicates = set()

    # Match ?this <predicate> or ?this prefix:local
    # Full IRIs
    for m in re.finditer(r'\?this\s+<([^>]+)>', sparql_select):
        predicates.add(URIRef(m.group(1)))

    # Prefixed names — we need to expand them
    prefix_map = {
        "bpo:": str(BPO),
        "bp:": str(BP),
        "rdf:": str(RDF),
        "rdfs:": str(RDFS),
        "tg-pol:": str(TG_POL),
        "tg-uc:": str(TG_UC),
    }

    for m in re.finditer(r'\?this\s+([\w-]+:\w+)', sparql_select):
        prefixed = m.group(1)
        for prefix, ns in prefix_map.items():
            if prefixed.startswith(prefix):
                local = prefixed[len(prefix):]
                predicates.add(URIRef(ns + local))
                break

    # Handle "?this a ..." (rdf:type)
    if re.search(r'\?this\s+a\s+', sparql_select):
        predicates.add(RDF.type)

    return predicates


# -----------------------------------------------------------------
# Node hydration — fetch what the policy needs
# -----------------------------------------------------------------

def hydrate_node(node_uri, predicates, adapter):
    """Fetch specific properties of a node from the default graph."""
    triples = []
    for pred in predicates:
        results = adapter.query(s=node_uri, p=pred, g="")
        triples.extend(results)
    return triples


# -----------------------------------------------------------------
# User context as triples
# -----------------------------------------------------------------

def margaret_context_graph():
    """Build Margaret's user context as an rdflib Graph."""
    g = Graph()

    ctx = URIRef(f"{BP}usr_margaret_wilson")
    g.add((ctx, RDF.type, TG_UC.UserContext))
    g.add((ctx, TG_UC.organisationalUnit, BP.Hut_3))

    assignment = BNode()
    g.add((ctx, TG_UC.hasAssignment, assignment))
    g.add((assignment, TG_UC.resource, BP.Hut_3))
    g.add((assignment, TG_UC.scope, Literal("IntelligenceAnalysis")))
    g.add((assignment, TG_UC.status, Literal("Active")))

    qualifiers = BNode()
    g.add((assignment, TG_UC.qualifiers, qualifiers))
    g.add((qualifiers, TG_UC.classification, Literal("Secret")))

    return g


# -----------------------------------------------------------------
# Policy evaluation
# -----------------------------------------------------------------

def evaluate_policy(policy, node_uri, node_triples, context_graph):
    """Run a policy's SPARQL target against a mini evaluation graph.

    Returns True if the node is a focus node (policy applies).
    """
    eval_graph = Graph()

    # Add node properties
    for s, p, o in node_triples:
        eval_graph.add((s, p, o))

    # Add user context
    for s, p, o in context_graph:
        eval_graph.add((s, p, o))

    # Bind prefixes so the SPARQL can use them
    eval_graph.bind("bpo", BPO)
    eval_graph.bind("bp", BP)
    eval_graph.bind("tg-uc", TG_UC)
    eval_graph.bind("tg-pol", TG_POL)
    eval_graph.bind("rdf", RDF)
    eval_graph.bind("rdfs", RDFS)
    eval_graph.bind("xsd", XSD)

    try:
        results = list(eval_graph.query(policy.sparql_select))
        # Check if our node is in the results
        for row in results:
            if row[0] == node_uri:
                return True
    except Exception as e:
        print(f"    SPARQL error in {policy.label}: {e}")

    return False


# -----------------------------------------------------------------
# Main retrieval flow
# -----------------------------------------------------------------

BATCH_SIZE = 3

def main():
    # Load graphs
    adapter = GraphAdapter()
    adapter.load("", DATA_DIR / "bletchley-graph.ttl")
    adapter.load("urn:graph:policy", DATA_DIR / "bletchley-policies.ttl")
    print(f"Default graph: {len(adapter.graphs[''])} triples")
    print(f"Policy graph:  {len(adapter.graphs['urn:graph:policy'])} triples")

    # Load policies
    policies = load_policies(adapter)
    print(f"\nLoaded {len(policies)} policies (by precedence):")
    for p in policies:
        print(f"  [{p.order}] {p.label} -> {p.determination}")

    # Analyse what properties each policy needs
    all_predicates = set()
    for p in policies:
        preds = extract_node_predicates(p.sparql_select)
        print(f"\n  {p.label} needs: {[str(pr).split('/')[-1] for pr in preds]}")
        all_predicates |= preds

    print(f"\nUnion of all required predicates: "
          f"{[str(pr).split('/')[-1] for pr in all_predicates]}")

    # Build user context
    context_graph = margaret_context_graph()
    print(f"\nUser: Margaret (Hut 3 analyst, Secret clearance)")
    print(f"Context graph: {len(context_graph)} triples")

    # Step 1: Retrieve all IntelligenceReport nodes
    print(f"\n{'='*60}")
    print(f"QUERY: ?x a bpo:IntelligenceReport")
    print(f"{'='*60}")

    all_results = adapter.query(p=RDF.type, o=BPO.IntelligenceReport, g="")
    candidate_nodes = [s for s, p, o in all_results]
    print(f"\nFound {len(candidate_nodes)} candidate nodes")

    # Step 2: Process in batches
    allowed = []
    filtered = []
    violations = []

    batch_num = 0
    for i in range(0, len(candidate_nodes), BATCH_SIZE):
        batch = candidate_nodes[i:i + BATCH_SIZE]
        batch_num += 1
        print(f"\n--- Batch {batch_num} ({len(batch)} nodes) ---")

        for node_uri in batch:
            # Get label for display
            labels = adapter.query(s=node_uri, p=RDFS.label, g="")
            label = str(labels[0][2]) if labels else str(node_uri)

            # Hydrate: fetch properties the policies need
            node_triples = hydrate_node(node_uri, all_predicates, adapter)

            # Evaluate each policy in precedence order
            determination = "Allowed"
            triggered_policy = None

            for policy in policies:
                if evaluate_policy(policy, node_uri, node_triples,
                                   context_graph):
                    determination = policy.determination
                    triggered_policy = policy.label
                    break  # Highest-precedence policy wins

            if determination == "Violation":
                violations.append((label, triggered_policy))
                marker = "!! VIOLATION"
            elif determination == "Filtered":
                filtered.append((label, triggered_policy))
                marker = "-- FILTERED"
            else:
                allowed.append(label)
                marker = "** ALLOWED"

            print(f"  {marker}: {label}")
            if triggered_policy:
                print(f"           policy: {triggered_policy}")

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY — Margaret (Hut 3 analyst)")
    print(f"{'='*60}")
    print(f"\nAllowed ({len(allowed)}):")
    for label in allowed:
        print(f"  + {label}")
    print(f"\nFiltered ({len(filtered)}):")
    for label, policy in filtered:
        print(f"  - {label}")
        print(f"    reason: {policy}")
    print(f"\nViolations ({len(violations)}):")
    for label, policy in violations:
        print(f"  ! {label}")
        print(f"    reason: {policy}")

    print(f"\nAdapter query count: {adapter.query_count}")

if __name__ == "__main__":
    main()
