"""
Prototype: run all five Bletchley Park personas through
policy-filtered retrieval of the full graph.

Run from the repo root:
    python docs/tech-specs/policy-test-data/prototype/policy_filter_all_personas.py
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
# Graph adapter
# -----------------------------------------------------------------

class GraphAdapter:
    def __init__(self):
        self.graphs = {}
        self.query_count = 0

    def load(self, name, path, fmt="turtle"):
        g = Graph()
        g.parse(path, format=fmt)
        self.graphs[name] = g

    def query(self, s=None, p=None, o=None, g=""):
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
# Policy loader
# -----------------------------------------------------------------

class Policy:
    def __init__(self, uri, label, determination, order, sparql_select,
                 prefixes):
        self.uri = uri
        self.label = label
        self.determination = determination
        self.order = order
        self.sparql_select = sparql_select
        self.prefixes = prefixes


def resolve_prefixes(sparql_component, adapter):
    """Resolve sh:prefixes -> sh:declare chain from the policy graph."""
    prefixes = {}
    prefix_refs = adapter.query(
        s=sparql_component, p=SH.prefixes, g="urn:graph:policy"
    )
    for _, _, prefix_resource in prefix_refs:
        declarations = adapter.query(
            s=prefix_resource, p=SH.declare, g="urn:graph:policy"
        )
        for _, _, decl_node in declarations:
            prefix_results = adapter.query(
                s=decl_node, p=SH.prefix, g="urn:graph:policy"
            )
            ns_results = adapter.query(
                s=decl_node, p=SH.namespace, g="urn:graph:policy"
            )
            if prefix_results and ns_results:
                p_name = str(prefix_results[0][2])
                ns_iri = str(ns_results[0][2])
                prefixes[p_name] = ns_iri
    return prefixes


def build_prefix_header(prefixes):
    """Build a SPARQL PREFIX header string from a prefix dict."""
    lines = []
    for prefix, ns in sorted(prefixes.items()):
        lines.append(f"PREFIX {prefix}: <{ns}>")
    return "\n".join(lines)


def load_policies(adapter):
    policies = []
    shapes = adapter.query(p=RDF.type, o=SH.NodeShape, g="urn:graph:policy")
    for shape_uri, _, _ in shapes:
        labels = adapter.query(s=shape_uri, p=RDFS.label, g="urn:graph:policy")
        label = str(labels[0][2]) if labels else str(shape_uri)
        dets = adapter.query(
            s=shape_uri, p=TG_POL.producesDetermination, g="urn:graph:policy"
        )
        determination = str(dets[0][2]).split("/")[-1] if dets else "Unknown"
        orders = adapter.query(s=shape_uri, p=SH.order, g="urn:graph:policy")
        order = int(orders[0][2]) if orders else 99
        targets = adapter.query(s=shape_uri, p=SH.target, g="urn:graph:policy")
        sparql_select = None
        prefixes = {}
        for _, _, target_node in targets:
            prefixes = resolve_prefixes(target_node, adapter)
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
                sparql_select=sparql_select, prefixes=prefixes,
            ))
    policies.sort(key=lambda p: p.order)
    return policies


# -----------------------------------------------------------------
# Policy property analysis
# -----------------------------------------------------------------

def extract_node_predicates(policy):
    predicates = set()
    sparql_select = policy.sparql_select
    for m in re.finditer(r'\?this\s+<([^>]+)>', sparql_select):
        predicates.add(URIRef(m.group(1)))
    for m in re.finditer(r'\?this\s+([\w-]+:\w+)', sparql_select):
        prefixed = m.group(1)
        colon = prefixed.index(":")
        prefix = prefixed[:colon]
        local = prefixed[colon + 1:]
        if prefix in policy.prefixes:
            predicates.add(URIRef(policy.prefixes[prefix] + local))
    if re.search(r'\?this\s+a\s+', sparql_select):
        predicates.add(RDF.type)
    return predicates


# -----------------------------------------------------------------
# Node hydration
# -----------------------------------------------------------------

def hydrate_node(node_uri, predicates, adapter):
    triples = []
    for pred in predicates:
        results = adapter.query(s=node_uri, p=pred, g="")
        triples.extend(results)
    return triples


# -----------------------------------------------------------------
# User contexts
# -----------------------------------------------------------------

def build_context(user_id, org_units, assignments=None,
                  override_authorities=None):
    """Build a user context graph.

    assignments: list of dicts with keys:
        resource, scope, status, classification
    override_authorities: list of dicts with keys:
        policy_area, condition
    """
    g = Graph()
    ctx = URIRef(user_id)
    g.add((ctx, RDF.type, TG_UC.UserContext))

    for ou in org_units:
        g.add((ctx, TG_UC.organisationalUnit, URIRef(ou)))

    for a in (assignments or []):
        assignment = BNode()
        g.add((ctx, TG_UC.hasAssignment, assignment))
        g.add((assignment, TG_UC.resource, URIRef(a["resource"])))
        g.add((assignment, TG_UC.scope, Literal(a["scope"])))
        g.add((assignment, TG_UC.status, Literal(a.get("status", "Active"))))
        if "classification" in a:
            qualifiers = BNode()
            g.add((assignment, TG_UC.qualifiers, qualifiers))
            g.add((qualifiers, TG_UC.classification,
                   Literal(a["classification"])))

    for oa in (override_authorities or []):
        override = BNode()
        g.add((ctx, TG_UC.hasOverrideAuthority, override))
        g.add((override, TG_UC.policyArea, Literal(oa["policy_area"])))

    return g


PERSONAS = [
    {
        "name": "Alan",
        "description": "Hut 8 cryptanalyst, Most Secret clearance",
        "context": lambda: build_context(
            f"{BP}usr_alan_turing",
            [f"{BP}Hut_8"],
            assignments=[{
                "resource": f"{BP}Hut_8",
                "scope": "Cryptanalysis",
                "classification": "MostSecret",
            }],
        ),
    },
    {
        "name": "Dorothy",
        "description": "Bombe operator, Hut 11, Secret clearance",
        "context": lambda: build_context(
            f"{BP}usr_dorothy_jenkins",
            [f"{BP}Hut_11"],
            assignments=[{
                "resource": f"{BP}Hut_11",
                "scope": "MachineOperations",
                "classification": "Secret",
            }],
        ),
    },
    {
        "name": "Cdr Bradshaw",
        "description": "Admiralty liaison, scoped to Hut 4",
        "context": lambda: build_context(
            f"{BP}usr_cdr_bradshaw",
            [f"{BP}Admiralty"],
            assignments=[{
                "resource": f"{BP}Hut_4",
                "scope": "Liaison",
                "classification": "Secret",
            }],
        ),
    },
    {
        "name": "Travis",
        "description": "Director, Ultra clearance, full override",
        "context": lambda: build_context(
            f"{BP}usr_travis",
            [f"{BP}Directorate"],
            assignments=[{
                "resource": f"{BP}GC_CS",
                "scope": "DirectorOversight",
                "classification": "Ultra",
            }],
            override_authorities=[{
                "policy_area": "UltraDissemination",
            }],
        ),
    },
]


# -----------------------------------------------------------------
# Policy evaluation
# -----------------------------------------------------------------

def evaluate_policy(policy, node_uri, node_triples, context_graph):
    eval_graph = Graph()
    for s, p, o in node_triples:
        eval_graph.add((s, p, o))
    for s, p, o in context_graph:
        eval_graph.add((s, p, o))
    for prefix, ns in policy.prefixes.items():
        eval_graph.bind(prefix, Namespace(ns))
    prefix_header = build_prefix_header(policy.prefixes)
    full_query = f"{prefix_header}\n{policy.sparql_select}"
    try:
        results = list(eval_graph.query(full_query))
        for row in results:
            if row[0] == node_uri:
                return True
    except Exception as e:
        print(f"    SPARQL error in {policy.label}: {e}")
    return False


# -----------------------------------------------------------------
# Run one persona
# -----------------------------------------------------------------

BATCH_SIZE = 3

def run_persona(persona, candidate_nodes, policies, all_predicates, adapter):
    name = persona["name"]
    desc = persona["description"]
    context_graph = persona["context"]()

    print(f"\n{'#'*60}")
    print(f"# {name} — {desc}")
    print(f"{'#'*60}")

    allowed = []
    filtered = []
    violations = []

    batch_num = 0
    for i in range(0, len(candidate_nodes), BATCH_SIZE):
        batch = candidate_nodes[i:i + BATCH_SIZE]
        batch_num += 1

        for node_uri in batch:
            labels = adapter.query(s=node_uri, p=RDFS.label, g="")
            label = str(labels[0][2]) if labels else str(node_uri)

            node_triples = hydrate_node(node_uri, all_predicates, adapter)

            determination = "Allowed"
            triggered_policy = None

            for policy in policies:
                if evaluate_policy(policy, node_uri, node_triples,
                                   context_graph):
                    determination = policy.determination
                    triggered_policy = policy.label
                    break

            if determination == "Violation":
                violations.append((label, triggered_policy))
            elif determination == "Filtered":
                filtered.append((label, triggered_policy))
            else:
                allowed.append(label)

    # Summary only — skip per-batch output for readability
    print(f"\nAllowed ({len(allowed)}):")
    for label in allowed:
        print(f"  + {label}")
    print(f"\nFiltered ({len(filtered)}):")
    for label, policy in filtered:
        print(f"  - {label}  [{policy}]")
    print(f"\nViolations ({len(violations)}):")
    for label, policy in violations:
        print(f"  ! {label}  [{policy}]")


# -----------------------------------------------------------------
# Main
# -----------------------------------------------------------------

def main():
    adapter = GraphAdapter()
    adapter.load("", DATA_DIR / "bletchley-graph.ttl")
    adapter.load("urn:graph:policy", DATA_DIR / "bletchley-policies.ttl")

    policies = load_policies(adapter)
    print(f"Policies ({len(policies)}):")
    for p in policies:
        print(f"  [{p.order}] {p.label} -> {p.determination}")

    all_predicates = set()
    for p in policies:
        all_predicates |= extract_node_predicates(p)

    # Get all candidate nodes
    all_subjects = set()
    for s, p, o in adapter.query(s=None, p=None, o=None, g=""):
        if isinstance(s, URIRef):
            all_subjects.add(s)
    candidate_nodes = sorted(all_subjects)
    print(f"\n{len(candidate_nodes)} candidate nodes in default graph")

    for persona in PERSONAS:
        run_persona(persona, candidate_nodes, policies,
                    all_predicates, adapter)

    print(f"\nTotal adapter query count: {adapter.query_count}")

if __name__ == "__main__":
    main()
