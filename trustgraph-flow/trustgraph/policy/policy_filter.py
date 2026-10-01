"""
Policy filter for post-query filtering of graph results.

Takes a set of triples and a UserContext, evaluates SHACL-AF policy
rules, and returns only the triples the user is permitted to see.

The filter is transport-agnostic: it receives a query_fn callback
for fetching data from the graph. This allows it to be used
inside the triples query service (direct store access) or inside
GraphRAG (via triples client).

query_fn signature:
    async query_fn(s, p, o, collection, g) -> list[Triple]
    where s, p, o are Term | None

Policy evaluation flow:
    1. Load SHACL-AF NodeShape policies from urn:graph:policy
    2. Parse each policy's sh:SPARQLTarget to discover what
       predicates are used against ?this (the candidate node)
    3. For each candidate node in the retrieved triples:
       a. Hydrate: fetch the required predicates from the graph
       b. Build a tiny evaluation graph (node props + user context)
       c. Run each policy's SPARQL SELECT in precedence order
       d. First matching policy wins — its determination applies
    4. Apply determinations: Notify passes through (with event),
       Filtered and Violation remove the node's triples
"""

import re
import logging
from typing import Callable, Awaitable

from rdflib import Graph, URIRef, Literal, BNode, Namespace
from rdflib.namespace import RDF, RDFS, XSD

from .. schema import Triple, Term, IRI, LITERAL, UserContext

logger = logging.getLogger(__name__)

# Well-known namespaces used in policy SPARQL
SH = Namespace("http://www.w3.org/ns/shacl#")
TG_POL = Namespace("https://trustgraph.ai/ontology/policy/")
TG_UC = Namespace("https://trustgraph.ai/ontology/user-context/")

POLICY_GRAPH = "urn:graph:policy"


class PolicyEvaluation:
    """Result of evaluating a node against a policy."""
    def __init__(self, node_iri, policy_uri, policy_label, determination):
        self.node_iri = node_iri
        self.policy_uri = policy_uri
        self.policy_label = policy_label
        self.determination = determination


class LoadedPolicy:
    """A policy loaded from the policy graph."""
    def __init__(self, uri, label, determination, order, sparql_select,
                 prefixes):
        self.uri = uri
        self.label = label
        self.determination = determination
        self.order = order
        self.sparql_select = sparql_select
        self.prefixes = prefixes


class PolicyFilter:

    def __init__(
        self,
        query_fn: Callable[..., Awaitable[list[Triple]]],
        on_evaluation: Callable[..., Awaitable[None]] | None = None,
    ):
        """
        Args:
            query_fn: async fn(s, p, o, collection, g) -> list[Triple]
            on_evaluation: async fn(PolicyEvaluation) -> None
                Called for every determination (Notify, Filtered,
                or Violation). No-op if None.
        """
        self.query_fn = query_fn
        self.on_evaluation = on_evaluation
        self._policies = None
        self._required_predicates = None

    async def apply(
        self,
        triples: list[Triple],
        collection: str,
        user_context: UserContext,
    ) -> list[Triple]:
        """
        Apply policy filtering to a set of triples.

        Returns the filtered list of triples the user is permitted
        to see.
        """

        if self._policies is None:
            self._policies = await self._load_policies(collection)
            if not self._policies:
                return triples
            self._required_predicates = self._discover_predicates(
                self._policies
            )

        if not self._policies:
            return triples

        context_graph = self._build_context_graph(user_context)

        candidate_iris = set()
        for t in triples:
            if t.s and t.s.type == IRI:
                candidate_iris.add(t.s.iri)
            if t.o and t.o.type == IRI:
                candidate_iris.add(t.o.iri)

        blocked_iris = set()
        for node_iri in candidate_iris:
            evaluation = await self._evaluate_node(
                node_iri, collection, context_graph,
            )
            if evaluation:
                if self.on_evaluation:
                    await self.on_evaluation(evaluation)
                if evaluation.determination != "Notify":
                    blocked_iris.add(node_iri)

        if not blocked_iris:
            return triples

        return [
            t for t in triples
            if not self._triple_blocked(t, blocked_iris)
        ]

    def _triple_blocked(self, triple, blocked_iris):
        if triple.s and triple.s.type == IRI:
            if triple.s.iri in blocked_iris:
                return True
        return False

    # -----------------------------------------------------------------
    # Policy loading
    # -----------------------------------------------------------------

    async def _load_policies(self, collection):
        """Load SHACL-AF NodeShape policies from urn:graph:policy."""

        sh_type = Term(type=IRI, iri=str(RDF.type))
        sh_node_shape = Term(type=IRI, iri=str(SH.NodeShape))

        shapes = await self.query_fn(
            None, sh_type, sh_node_shape, collection, POLICY_GRAPH,
        )

        policies = []
        for shape_triple in shapes:
            policy = await self._load_one_policy(
                shape_triple.s, collection,
            )
            if policy:
                policies.append(policy)

        policies.sort(key=lambda p: p.order)

        return policies

    async def _load_one_policy(self, shape_term, collection):
        """Load a single policy shape from the policy graph."""

        shape_iri = shape_term.iri if shape_term.type == IRI else None
        if not shape_iri:
            return None

        s = Term(type=IRI, iri=shape_iri)

        # Label
        label_results = await self.query_fn(
            s, Term(type=IRI, iri=str(RDFS.label)), None,
            collection, POLICY_GRAPH,
        )
        label = (
            label_results[0].o.value if label_results else shape_iri
        )

        # Determination
        det_results = await self.query_fn(
            s, Term(type=IRI, iri=str(TG_POL.producesDetermination)), None,
            collection, POLICY_GRAPH,
        )
        determination = "Unknown"
        if det_results:
            det_iri = det_results[0].o.iri if det_results[0].o.type == IRI else ""
            determination = det_iri.split("/")[-1]

        # Order
        order_results = await self.query_fn(
            s, Term(type=IRI, iri=str(SH.order)), None,
            collection, POLICY_GRAPH,
        )
        order = 99
        if order_results:
            try:
                order = int(order_results[0].o.value)
            except (ValueError, AttributeError):
                pass

        # Target -> SPARQL SELECT
        target_results = await self.query_fn(
            s, Term(type=IRI, iri=str(SH.target)), None,
            collection, POLICY_GRAPH,
        )

        sparql_select = None
        prefixes = {}
        for target_triple in target_results:
            target_term = target_triple.o

            # Resolve sh:prefixes -> sh:declare chain
            prefixes = await self._resolve_prefixes(
                target_term, collection,
            )

            select_results = await self.query_fn(
                target_term, Term(type=IRI, iri=str(SH.select)), None,
                collection, POLICY_GRAPH,
            )
            if select_results:
                sparql_select = select_results[0].o.value
                break

        if not sparql_select:
            logger.warning(
                f"Policy {label} has no sh:SPARQLTarget, skipping"
            )
            return None

        return LoadedPolicy(
            uri=shape_iri, label=label, determination=determination,
            order=order, sparql_select=sparql_select, prefixes=prefixes,
        )

    # -----------------------------------------------------------------
    # sh:prefixes / sh:declare resolution
    # -----------------------------------------------------------------

    async def _resolve_prefixes(self, sparql_component_term, collection):
        """Resolve sh:prefixes -> sh:declare chains from the policy graph.

        Follows the SHACL-AF standard:
            ?component sh:prefixes ?prefixResource .
            ?prefixResource sh:declare ?decl .
            ?decl sh:prefix "bpo" .
            ?decl sh:namespace "http://..."^^xsd:anyURI .

        Returns a dict of {prefix: namespace_iri}.
        """
        prefixes = {}

        prefix_refs = await self.query_fn(
            sparql_component_term,
            Term(type=IRI, iri=str(SH.prefixes)),
            None, collection, POLICY_GRAPH,
        )

        for prefix_ref_triple in prefix_refs:
            prefix_resource = prefix_ref_triple.o

            declarations = await self.query_fn(
                prefix_resource,
                Term(type=IRI, iri=str(SH.declare)),
                None, collection, POLICY_GRAPH,
            )

            for decl_triple in declarations:
                decl_node = decl_triple.o

                prefix_results = await self.query_fn(
                    decl_node,
                    Term(type=IRI, iri=str(SH.prefix)),
                    None, collection, POLICY_GRAPH,
                )
                ns_results = await self.query_fn(
                    decl_node,
                    Term(type=IRI, iri=str(SH.namespace)),
                    None, collection, POLICY_GRAPH,
                )

                if prefix_results and ns_results:
                    p_name = prefix_results[0].o.value
                    ns_term = ns_results[0].o
                    ns_iri = self._extract_term_value(ns_term)
                    if p_name and ns_iri:
                        prefixes[p_name] = ns_iri

        return prefixes

    def _extract_term_value(self, term):
        """Extract the string value from a Term, checking both value and iri.

        sh:namespace values are typed xsd:anyURI which may be stored
        as either a literal (value) or an IRI depending on the backend.
        """
        if term is None:
            return None
        if term.value:
            return term.value
        if term.iri:
            return term.iri
        return None

    def _build_prefix_header(self, prefixes):
        """Build a SPARQL PREFIX header string from a prefix dict."""
        lines = []
        for prefix, ns in sorted(prefixes.items()):
            lines.append(f"PREFIX {prefix}: <{ns}>")
        return "\n".join(lines)

    # -----------------------------------------------------------------
    # Predicate discovery
    # -----------------------------------------------------------------

    def _discover_predicates(self, policies):
        """Discover the union of predicates all policies need from ?this."""
        all_preds = set()
        for p in policies:
            all_preds |= self._extract_node_predicates(p)
        return all_preds

    def _extract_node_predicates(self, policy):
        """Parse SPARQL to find predicates used on ?this."""
        predicates = set()
        sparql_select = policy.sparql_select

        for m in re.finditer(r'\?this\s+<([^>]+)>', sparql_select):
            predicates.add(m.group(1))

        for m in re.finditer(r'\?this\s+([\w-]+:\w+)', sparql_select):
            prefixed = m.group(1)
            colon = prefixed.index(":")
            prefix = prefixed[:colon]
            local = prefixed[colon + 1:]
            if prefix in policy.prefixes:
                predicates.add(policy.prefixes[prefix] + local)

        if re.search(r'\?this\s+a\s+', sparql_select):
            predicates.add(str(RDF.type))

        return predicates

    # -----------------------------------------------------------------
    # Node hydration
    # -----------------------------------------------------------------

    async def _hydrate_node(self, node_iri, collection):
        """Fetch policy-required properties for a node."""
        hydrated = []
        s = Term(type=IRI, iri=node_iri)
        for pred_iri in self._required_predicates:
            p = Term(type=IRI, iri=pred_iri)
            results = await self.query_fn(s, p, None, collection, "")
            hydrated.extend(results)
        return hydrated

    # -----------------------------------------------------------------
    # User context -> rdflib Graph
    # -----------------------------------------------------------------

    def _build_context_graph(self, user_context):
        """Convert a UserContext dataclass to an rdflib Graph."""
        g = Graph()

        if not user_context.user_id:
            return g

        ctx = URIRef(user_context.user_id)
        g.add((ctx, RDF.type, TG_UC.UserContext))

        for ou in user_context.organisational_units:
            g.add((ctx, TG_UC.organisationalUnit, URIRef(ou)))

        for role in user_context.roles:
            g.add((ctx, TG_UC.role, URIRef(role)))

        for a in user_context.assignments:
            assignment = BNode()
            g.add((ctx, TG_UC.hasAssignment, assignment))
            if a.resource:
                g.add((assignment, TG_UC.resource, URIRef(a.resource)))
            if a.scope:
                g.add((assignment, TG_UC.scope, Literal(a.scope)))
            if a.status:
                g.add((assignment, TG_UC.status, Literal(a.status)))
            if a.qualifiers:
                qualifiers = BNode()
                g.add((assignment, TG_UC.qualifiers, qualifiers))
                for k, v in a.qualifiers.items():
                    g.add((qualifiers, TG_UC[k], Literal(v)))

        for e in user_context.entitlements:
            entitlement = BNode()
            g.add((ctx, TG_UC.hasEntitlement, entitlement))
            if e.resource_scope:
                g.add((entitlement, TG_UC.resourceScope,
                       Literal(e.resource_scope)))
            if e.access_level:
                g.add((entitlement, TG_UC.accessLevel,
                       Literal(e.access_level)))

        for oa in user_context.override_authorities:
            override = BNode()
            g.add((ctx, TG_UC.hasOverrideAuthority, override))
            if oa.policy_area:
                g.add((override, TG_UC.policyArea,
                       Literal(oa.policy_area)))
            if oa.condition:
                g.add((override, TG_UC.condition,
                       Literal(oa.condition)))

        if user_context.delegation:
            delegation = BNode()
            g.add((ctx, TG_UC.hasDelegation, delegation))
            if user_context.delegation.delegator_id:
                g.add((delegation, TG_UC.delegatorId,
                       URIRef(user_context.delegation.delegator_id)))
            if user_context.delegation.scope:
                g.add((delegation, TG_UC.scope,
                       Literal(user_context.delegation.scope)))

        return g

    # -----------------------------------------------------------------
    # Policy evaluation
    # -----------------------------------------------------------------

    async def _evaluate_node(self, node_iri, collection, context_graph):
        """Evaluate a node against all policies in precedence order.

        Returns a PolicyEvaluation if a policy triggers, or None if
        the node is allowed.
        """
        hydrated = await self._hydrate_node(node_iri, collection)

        eval_graph = Graph()

        for t in hydrated:
            eval_graph.add(self._schema_triple_to_rdflib(t))

        for s, p, o in context_graph:
            eval_graph.add((s, p, o))

        for policy in self._policies:
            # Bind this policy's resolved prefixes
            for prefix, ns in policy.prefixes.items():
                eval_graph.bind(prefix, Namespace(ns))

            if self._run_sparql_target(
                policy, URIRef(node_iri), eval_graph,
            ):
                return PolicyEvaluation(
                    node_iri=node_iri,
                    policy_uri=policy.uri,
                    policy_label=policy.label,
                    determination=policy.determination,
                )

        return None

    def _run_sparql_target(self, policy, node_uri, eval_graph):
        """Run a policy's SPARQL SELECT and check if the node matches.

        Prepends PREFIX declarations resolved from sh:prefixes/sh:declare
        so the SPARQL engine can resolve prefixed names.
        """
        prefix_header = self._build_prefix_header(policy.prefixes)
        full_query = f"{prefix_header}\n{policy.sparql_select}"

        try:
            results = list(eval_graph.query(full_query))
            for row in results:
                if row[0] == node_uri:
                    return True
        except Exception as e:
            logger.error(
                f"SPARQL error in policy '{policy.label}': {e}",
                exc_info=True,
            )
        return False

    def _schema_triple_to_rdflib(self, t):
        """Convert a schema Triple to an rdflib (s, p, o) tuple."""
        s = self._term_to_rdflib(t.s)
        p = self._term_to_rdflib(t.p)
        o = self._term_to_rdflib(t.o)
        return (s, p, o)

    def _term_to_rdflib(self, term):
        """Convert a schema Term to an rdflib term."""
        if term is None:
            return None
        if term.type == IRI:
            return URIRef(term.iri)
        if term.type == LITERAL:
            return Literal(term.value)
        return Literal(str(term.value or term.iri))
