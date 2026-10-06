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
    2. Parse each policy's sh:SPARQLTarget and sh:SPARQLRule
    3. For each candidate node in the retrieved triples:
       a. Hydrate: fetch the required predicates from the graph
       b. Build a tiny evaluation graph (node props + user context)
       c. Run each policy's SPARQL SELECT target in precedence order
       d. If the target matches, run the CONSTRUCT rule
       e. Parse sh:ValidationResult from CONSTRUCT output:
          sh:resultSeverity (determination IRI),
          sh:resultMessage (reason), tg-pol:blocks (default true)
       f. First matching policy wins — its determination applies
    4. Apply determinations: nodes with blocks=true are removed
"""

import time
import logging
from typing import Callable, Awaitable
from collections import OrderedDict

from rdflib import Graph, URIRef, Literal, BNode, Namespace, Variable
from rdflib.namespace import RDF, RDFS, XSD
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.algebra import traverse
from rdflib.plugins.sparql.parserutils import CompValue

from .. schema import Triple, Term, IRI, LITERAL, UserContext

logger = logging.getLogger(__name__)

# Well-known namespaces used in policy SPARQL
SH = Namespace("http://www.w3.org/ns/shacl#")
TG_POL = Namespace("https://trustgraph.ai/ontology/policy/")
TG_UC = Namespace("https://trustgraph.ai/ontology/user-context/")

POLICY_GRAPH = "urn:graph:policy"

QUERY_CACHE_TTL = 30
QUERY_CACHE_MAX = 256
SPARQL_CACHE_MAX = 64


class QueryCache:
    """LRU + TTL cache for triple query results."""

    def __init__(self, query_fn, ttl=QUERY_CACHE_TTL,
                 max_size=QUERY_CACHE_MAX):
        self._query_fn = query_fn
        self._ttl = ttl
        self._max_size = max_size
        self._cache = OrderedDict()

    def _make_key(self, s, p, o, collection, g):
        s_key = (s.type, s.iri, s.value) if s else None
        p_key = (p.type, p.iri, p.value) if p else None
        o_key = (o.type, o.iri, o.value) if o else None
        return (s_key, p_key, o_key, collection, g)

    async def query(self, s, p, o, collection, g=""):
        key = self._make_key(s, p, o, collection, g)
        now = time.monotonic()

        if key in self._cache:
            result, ts = self._cache[key]
            if now - ts < self._ttl:
                self._cache.move_to_end(key)
                return result
            del self._cache[key]

        result = await self._query_fn(s, p, o, collection, g)

        self._cache[key] = (result, now)
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

        return result


class SparqlCache:
    """Cache for compiled SPARQL queries."""

    def __init__(self, max_size=SPARQL_CACHE_MAX):
        self._max_size = max_size
        self._cache = OrderedDict()

    def prepare(self, query_string, initNs=None):
        key = query_string
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]

        compiled = prepareQuery(query_string, initNs=initNs or {})
        self._cache[key] = compiled
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

        return compiled


class PolicyEvaluation:
    """Result of evaluating a node against a policy."""
    def __init__(self, node_iri, policy_uri, policy_label,
                 determination, blocks=True, reason=""):
        self.node_iri = node_iri
        self.policy_uri = policy_uri
        self.policy_label = policy_label
        self.determination = determination
        self.blocks = blocks
        self.reason = reason


class LoadedPolicy:
    """A policy loaded from the policy graph."""
    def __init__(self, uri, label, order, sparql_select,
                 target_prefixes, sparql_construct, construct_prefixes):
        self.uri = uri
        self.label = label
        self.order = order
        self.sparql_select = sparql_select
        self.target_prefixes = target_prefixes
        self.sparql_construct = sparql_construct
        self.construct_prefixes = construct_prefixes


class PolicyFilter:

    def __init__(
        self,
        query_fn: Callable[..., Awaitable[list[Triple]]],
        on_evaluation: Callable[..., Awaitable[None]] | None = None,
        query_cache: QueryCache | None = None,
        sparql_cache: SparqlCache | None = None,
        policies: list | None = None,
        required_predicates: set | None = None,
    ):
        """
        Args:
            query_fn: async fn(s, p, o, collection, g) -> list[Triple]
            on_evaluation: async fn(PolicyEvaluation) -> None
                Called for every determination. No-op if None.
            query_cache: Shared QueryCache instance (created if None)
            sparql_cache: Shared SparqlCache instance (created if None)
            policies: Pre-loaded policies (loads from graph if None)
            required_predicates: Pre-computed predicates for policies
        """
        if query_cache is not None:
            self._query_cache = query_cache
            self._query_cache._query_fn = query_fn
        else:
            self._query_cache = QueryCache(query_fn)
        self.query_fn = self._query_cache.query
        self.on_evaluation = on_evaluation
        self._policies = policies
        self._required_predicates = required_predicates
        self._sparql_cache = sparql_cache or SparqlCache()

    async def load_policies(self, collection: str) -> None:
        """Load policies from the policy graph if not already loaded."""
        if self._policies is None:
            self._policies = await self._load_policies(collection)
            if self._policies:
                self._required_predicates = self._discover_predicates(
                    self._policies
                )

    def has_policies(self) -> bool:
        """True if policies have been loaded and at least one exists."""
        return bool(self._policies)

    async def apply(
        self,
        triples: list[Triple],
        collection: str,
        user_context: UserContext,
        graph=None,
    ) -> list[Triple]:
        """
        Apply policy filtering to a set of triples.

        Returns the filtered list of triples the user is permitted
        to see.
        """

        await self.load_policies(collection)

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
                node_iri, collection, context_graph, graph,
            )
            if evaluation:
                if self.on_evaluation:
                    await self.on_evaluation(evaluation)
                if evaluation.blocks:
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
        target_prefixes = {}
        for target_triple in target_results:
            target_term = target_triple.o

            target_prefixes = await self._resolve_prefixes(
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

        # Rule -> SPARQL CONSTRUCT
        rule_results = await self.query_fn(
            s, Term(type=IRI, iri=str(SH.rule)), None,
            collection, POLICY_GRAPH,
        )

        sparql_construct = None
        construct_prefixes = {}
        for rule_triple in rule_results:
            rule_term = rule_triple.o

            construct_prefixes = await self._resolve_prefixes(
                rule_term, collection,
            )

            construct_results = await self.query_fn(
                rule_term, Term(type=IRI, iri=str(SH.construct)), None,
                collection, POLICY_GRAPH,
            )
            if construct_results:
                sparql_construct = construct_results[0].o.value
                break

        if not sparql_construct:
            logger.warning(
                f"Policy {label} has no sh:SPARQLRule, skipping"
            )
            return None

        return LoadedPolicy(
            uri=shape_iri, label=label, order=order,
            sparql_select=sparql_select,
            target_prefixes=target_prefixes,
            sparql_construct=sparql_construct,
            construct_prefixes=construct_prefixes,
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
        """Discover all predicates that policies need for evaluation.

        Walks the SPARQL algebra of each policy's SELECT query to find
        every predicate reachable from ?this through chains of triple
        patterns. This ensures hydration fetches enough data for
        arbitrarily deep property traversals.

        Returns a set of (predicate_iri, position) tuples where position
        is "s" (fetch triples where the node is subject) or "o" (fetch
        triples where the node is object). This distinction matters
        because hydration must query the graph in the right direction.
        """
        all_preds = set()
        for p in policies:
            all_preds |= self._extract_node_predicates(p)
        return all_preds

    def _extract_node_predicates(self, policy):
        """Walk the SPARQL algebra to find predicates reachable from ?this.

        Uses rdflib's algebra tree (produced by prepareQuery) rather than
        regex, so it correctly handles OPTIONAL, UNION, FILTER NOT EXISTS,
        prefixed names, and the 'a' shorthand for rdf:type.

        The algorithm traces variable dependencies starting from ?this:
          1. Seed the "known" set with Variable('this')
          2. Scan all BGP triple patterns for any pattern where a known
             variable appears as subject or object
          3. Record the predicate and which position the known variable
             occupies ("s" if subject, "o" if object)
          4. Add any newly discovered variables to the known set
          5. Repeat until no new variables are found

        This captures multi-hop patterns like:
            ?this bpo:section ?section .
            ?section bpo:classification ?class .
        where both bpo:section and bpo:classification need hydrating.
        """
        prefix_header = self._build_prefix_header(policy.target_prefixes)
        full_query = f"{prefix_header}\n{policy.sparql_select}"

        compiled = self._sparql_cache.prepare(full_query)

        # Collect all BGP triple patterns from the algebra
        all_triples = []

        def collect_bgp(node):
            if isinstance(node, CompValue) and node.name == 'BGP':
                all_triples.extend(node.triples)

        traverse(compiled.algebra, visitPre=collect_bgp)

        # Trace variable dependencies outward from ?this
        known_vars = {Variable('this')}
        predicates = set()

        changed = True
        while changed:
            changed = False
            for s, p, o in all_triples:
                if not isinstance(p, URIRef):
                    continue

                if s in known_vars:
                    pred_key = (str(p), "s")
                    if pred_key not in predicates:
                        predicates.add(pred_key)
                        changed = True
                    if isinstance(o, Variable) and o not in known_vars:
                        known_vars.add(o)
                        changed = True

                if o in known_vars:
                    pred_key = (str(p), "o")
                    if pred_key not in predicates:
                        predicates.add(pred_key)
                        changed = True
                    if isinstance(s, Variable) and s not in known_vars:
                        known_vars.add(s)
                        changed = True

        return predicates

    # -----------------------------------------------------------------
    # Node hydration
    # -----------------------------------------------------------------

    async def _hydrate_node(self, node_iri, collection, graph=None):
        """Fetch policy-required properties for a node.

        Each entry in _required_predicates is a (predicate_iri, position)
        tuple. Position "s" means the candidate node is the subject, so
        we query (node, pred, ?). Position "o" means the candidate node
        is the object, so we query (?, pred, node).
        """
        hydrated = []
        node = Term(type=IRI, iri=node_iri)
        for pred_iri, position in self._required_predicates:
            p = Term(type=IRI, iri=pred_iri)
            if position == "s":
                results = await self.query_fn(
                    node, p, None, collection, graph,
                )
            else:
                results = await self.query_fn(
                    None, p, node, collection, graph,
                )
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

    async def _evaluate_node(self, node_iri, collection, context_graph,
                             graph=None):
        """Evaluate a node against all policies in precedence order.

        Returns a PolicyEvaluation if a policy triggers, or None if
        the node is allowed.
        """
        hydrated = await self._hydrate_node(node_iri, collection, graph)

        eval_graph = Graph()

        for t in hydrated:
            eval_graph.add(self._schema_triple_to_rdflib(t))

        for s, p, o in context_graph:
            eval_graph.add((s, p, o))

        node_uri = URIRef(node_iri)

        for policy in self._policies:
            for prefix, ns in policy.target_prefixes.items():
                eval_graph.bind(prefix, Namespace(ns))

            if not self._run_sparql_target(policy, node_uri, eval_graph):
                continue

            result = self._run_sparql_rule(
                policy, node_uri, eval_graph,
            )
            if result:
                return PolicyEvaluation(
                    node_iri=node_iri,
                    policy_uri=policy.uri,
                    policy_label=policy.label,
                    determination=result["determination"],
                    blocks=result["blocks"],
                    reason=result["reason"],
                )

        return None

    def _run_sparql_target(self, policy, node_uri, eval_graph):
        """Run a policy's SPARQL SELECT and check if the node matches."""
        prefix_header = self._build_prefix_header(policy.target_prefixes)
        full_query = f"{prefix_header}\n{policy.sparql_select}"

        try:
            compiled = self._sparql_cache.prepare(full_query)
            results = list(eval_graph.query(
                compiled,
                initBindings={Variable('this'): node_uri},
            ))
            return len(results) > 0
        except Exception as e:
            logger.error(
                f"SPARQL target error in policy '{policy.label}': {e}",
                exc_info=True,
            )
        return False

    def _run_sparql_rule(self, policy, node_uri, eval_graph):
        """Run a policy's CONSTRUCT rule and parse the ValidationResult.

        Returns a dict with determination (IRI), blocks (bool),
        and reason (str), or None if the CONSTRUCT produced no result.
        """
        all_prefixes = {**policy.target_prefixes, **policy.construct_prefixes}
        prefix_header = self._build_prefix_header(all_prefixes)

        for prefix, ns in all_prefixes.items():
            eval_graph.bind(prefix, Namespace(ns))

        full_query = f"{prefix_header}\n{policy.sparql_construct}"

        try:
            compiled = self._sparql_cache.prepare(full_query)
            result_graph = eval_graph.query(
                compiled,
                initBindings={Variable('this'): node_uri},
            ).graph
        except Exception as e:
            logger.error(
                f"SPARQL rule error in policy '{policy.label}': {e}",
                exc_info=True,
            )
            return None

        for result_node in result_graph.subjects(RDF.type, SH.ValidationResult):
            determination = str(policy.uri)
            blocks = True
            reason = ""

            for sev in result_graph.objects(result_node, SH.resultSeverity):
                determination = str(sev)

            for msg in result_graph.objects(result_node, SH.resultMessage):
                reason = str(msg)

            for b in result_graph.objects(result_node, TG_POL.blocks):
                if hasattr(b, 'toPython'):
                    blocks = b.toPython()
                else:
                    blocks = str(b).lower() not in ("false", "0")

            return {
                "determination": determination,
                "blocks": blocks,
                "reason": reason,
            }

        return None

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
