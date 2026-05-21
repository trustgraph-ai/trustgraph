"""
SPARQL algebra evaluator.

Recursively evaluates an rdflib SPARQL algebra tree by issuing triple
pattern queries via TriplesClient (streaming) and performing in-memory
joins, filters, and projections.

Handlers are async generators that yield solutions incrementally.
Blocking operators (joins, sort, group, distinct) materialise their
upstream into a list at the boundary, then yield results.
"""

import logging
from collections import defaultdict

from rdflib.term import Variable, URIRef, Literal, BNode
from rdflib.plugins.sparql.parserutils import CompValue

from ... schema import Term, Triple, IRI, LITERAL, BLANK
from ... knowledge import Uri
from ... knowledge import Literal as KgLiteral
from . parser import rdflib_term_to_term
from . solutions import (
    hash_join, left_join, minus, union, project, distinct,
    order_by, slice_solutions, _term_key,
)
from . expressions import evaluate_expression, _effective_boolean

logger = logging.getLogger(__name__)


class EvaluationError(Exception):
    """Raised when SPARQL evaluation fails."""
    pass


async def evaluate(node, triples_client, collection, limit=10000):
    """
    Evaluate a SPARQL algebra node.

    Yields solutions (dicts mapping variable names to Term values)
    incrementally as an async generator.
    """
    if not isinstance(node, CompValue):
        logger.warning(f"Expected CompValue, got {type(node)}: {node}")
        yield {}
        return

    name = node.name
    handler = _HANDLERS.get(name)

    if handler is None:
        logger.warning(f"Unsupported algebra node: {name}")
        yield {}
        return

    async for sol in handler(node, triples_client, collection, limit):
        yield sol


async def materialise(node, triples_client, collection, limit=10000):
    """Collect all solutions from evaluate() into a list."""
    return [sol async for sol in evaluate(node, triples_client, collection, limit)]


# --- Node handlers (async generators) ---

async def _eval_select_query(node, tc, collection, limit):
    async for sol in evaluate(node.p, tc, collection, limit):
        yield sol


async def _eval_project(node, tc, collection, limit):
    variables = [str(v) for v in node.PV]
    async for sol in evaluate(node.p, tc, collection, limit):
        yield {v: sol[v] for v in variables if v in sol}


async def _eval_bgp(node, tc, collection, limit):
    """
    Evaluate a Basic Graph Pattern.

    Patterns are ordered by selectivity and evaluated sequentially.
    For the final pattern, results stream directly from the triple store.
    """
    triples = node.triples
    if not triples:
        yield {}
        return

    def selectivity(pattern):
        return sum(1 for t in pattern if not isinstance(t, Variable))

    sorted_patterns = sorted(
        enumerate(triples), key=lambda x: -selectivity(x[1])
    )

    # For all patterns except the last, we must materialise intermediate
    # solutions because each pattern depends on bindings from prior ones.
    # The last pattern streams directly.
    solutions = [{}]

    for pattern_idx, (_, pattern) in enumerate(sorted_patterns):
        s_tmpl, p_tmpl, o_tmpl = pattern
        is_last = (pattern_idx == len(sorted_patterns) - 1)

        if is_last:
            # Stream the final pattern — yield as triples arrive
            count = 0
            for sol in solutions:
                s_val = _resolve_term(s_tmpl, sol)
                p_val = _resolve_term(p_tmpl, sol)
                o_val = _resolve_term(o_tmpl, sol)

                async for triple in tc.query_gen(
                    s=s_val, p=p_val, o=o_val,
                    limit=limit, collection=collection,
                ):
                    binding = dict(sol)
                    if isinstance(s_tmpl, Variable):
                        binding[str(s_tmpl)] = _to_term(triple.s)
                    if isinstance(p_tmpl, Variable):
                        binding[str(p_tmpl)] = _to_term(triple.p)
                    if isinstance(o_tmpl, Variable):
                        binding[str(o_tmpl)] = _to_term(triple.o)
                    yield binding
                    count += 1
                    if count >= limit:
                        return
        else:
            # Materialise intermediate patterns
            new_solutions = []
            for sol in solutions:
                s_val = _resolve_term(s_tmpl, sol)
                p_val = _resolve_term(p_tmpl, sol)
                o_val = _resolve_term(o_tmpl, sol)

                async for triple in tc.query_gen(
                    s=s_val, p=p_val, o=o_val,
                    limit=limit, collection=collection,
                ):
                    binding = dict(sol)
                    if isinstance(s_tmpl, Variable):
                        binding[str(s_tmpl)] = _to_term(triple.s)
                    if isinstance(p_tmpl, Variable):
                        binding[str(p_tmpl)] = _to_term(triple.p)
                    if isinstance(o_tmpl, Variable):
                        binding[str(o_tmpl)] = _to_term(triple.o)
                    new_solutions.append(binding)

            solutions = new_solutions
            if not solutions:
                return


# --- Blocking operators: materialise upstream, then yield ---

def _is_small_node(node):
    """Check if a node is likely to produce a small number of solutions."""
    if not isinstance(node, CompValue):
        return False
    if node.name in ("values", "ToMultiSet"):
        return True
    if node.name == "Extend" and hasattr(node, "p"):
        return _is_small_node(node.p)
    return False


async def _eval_join(node, tc, collection, limit):
    # Bind join: if one side is small (e.g. VALUES), materialise it and
    # substitute its bindings into the other side's evaluation.  This
    # turns wildcard BGP queries into selective ones.
    if _is_small_node(node.p1):
        yield_from = _bind_join(node.p1, node.p2, tc, collection, limit)
    elif _is_small_node(node.p2):
        yield_from = _bind_join(node.p2, node.p1, tc, collection, limit)
    else:
        yield_from = _hash_join(node, tc, collection, limit)

    async for sol in yield_from:
        yield sol


async def _hash_join(node, tc, collection, limit):
    left = await materialise(node.p1, tc, collection, limit)
    right = await materialise(node.p2, tc, collection, limit)
    for sol in hash_join(left, right)[:limit]:
        yield sol


async def _bind_join(small_node, big_node, tc, collection, limit):
    """Iterate over the small side and inject bindings into the big side."""
    small_sols = await materialise(small_node, tc, collection, limit)

    count = 0
    for binding in small_sols:
        async for sol in _evaluate_with_bindings(
            big_node, binding, tc, collection, limit
        ):
            yield sol
            count += 1
            if count >= limit:
                return


def _merge_compatible(left, right):
    """Merge two solutions if compatible (shared vars have equal values)."""
    merged = dict(left)
    for k, v in right.items():
        if k in merged:
            if _term_key(merged[k]) != _term_key(v):
                return None
        else:
            merged[k] = v
    return merged


async def _evaluate_with_bindings(node, bindings, tc, collection, limit):
    """Evaluate a node with pre-seeded variable bindings.

    For BGP nodes, the bindings are injected so _resolve_term sees them,
    turning wildcard queries into selective ones.  For other node types,
    evaluate normally and merge/filter against the bindings.
    """
    if isinstance(node, CompValue) and node.name == "BGP":
        async for sol in _eval_bgp_with_bindings(
            node, bindings, tc, collection, limit
        ):
            yield sol
    else:
        async for sol in evaluate(node, tc, collection, limit):
            merged = _merge_compatible(bindings, sol)
            if merged is not None:
                yield merged


async def _eval_bgp_with_bindings(node, bindings, tc, collection, limit):
    """Evaluate a BGP with pre-seeded bindings so variables resolve to terms."""
    triples = node.triples
    if not triples:
        yield dict(bindings)
        return

    def selectivity(pattern):
        score = 0
        for t in pattern:
            if not isinstance(t, Variable):
                score += 1
            elif str(t) in bindings:
                score += 1
        return score

    sorted_patterns = sorted(
        enumerate(triples), key=lambda x: -selectivity(x[1])
    )

    solutions = [dict(bindings)]

    for pattern_idx, (_, pattern) in enumerate(sorted_patterns):
        s_tmpl, p_tmpl, o_tmpl = pattern
        is_last = (pattern_idx == len(sorted_patterns) - 1)

        if is_last:
            count = 0
            for sol in solutions:
                s_val = _resolve_term(s_tmpl, sol)
                p_val = _resolve_term(p_tmpl, sol)
                o_val = _resolve_term(o_tmpl, sol)

                async for triple in tc.query_gen(
                    s=s_val, p=p_val, o=o_val,
                    limit=limit, collection=collection,
                ):
                    binding = dict(sol)
                    if isinstance(s_tmpl, Variable):
                        binding[str(s_tmpl)] = _to_term(triple.s)
                    if isinstance(p_tmpl, Variable):
                        binding[str(p_tmpl)] = _to_term(triple.p)
                    if isinstance(o_tmpl, Variable):
                        binding[str(o_tmpl)] = _to_term(triple.o)
                    yield binding
                    count += 1
                    if count >= limit:
                        return
        else:
            new_solutions = []
            for sol in solutions:
                s_val = _resolve_term(s_tmpl, sol)
                p_val = _resolve_term(p_tmpl, sol)
                o_val = _resolve_term(o_tmpl, sol)

                async for triple in tc.query_gen(
                    s=s_val, p=p_val, o=o_val,
                    limit=limit, collection=collection,
                ):
                    binding = dict(sol)
                    if isinstance(s_tmpl, Variable):
                        binding[str(s_tmpl)] = _to_term(triple.s)
                    if isinstance(p_tmpl, Variable):
                        binding[str(p_tmpl)] = _to_term(triple.p)
                    if isinstance(o_tmpl, Variable):
                        binding[str(o_tmpl)] = _to_term(triple.o)
                    new_solutions.append(binding)

            solutions = new_solutions
            if not solutions:
                return


async def _eval_left_join(node, tc, collection, limit):
    # Buffer right side for hash index; stream left through probe
    left_sols = await materialise(node.p1, tc, collection, limit)
    right_sols = await materialise(node.p2, tc, collection, limit)

    filter_fn = None
    if hasattr(node, "expr") and node.expr is not None:
        expr = node.expr
        if not (isinstance(expr, CompValue) and expr.name == "TrueFilter"):
            filter_fn = lambda sol: _effective_boolean(
                evaluate_expression(expr, sol)
            )

    for sol in left_join(left_sols, right_sols, filter_fn)[:limit]:
        yield sol


async def _eval_minus(node, tc, collection, limit):
    left = await materialise(node.p1, tc, collection, limit)
    right = await materialise(node.p2, tc, collection, limit)
    for sol in minus(left, right):
        yield sol


async def _eval_distinct(node, tc, collection, limit):
    seen = set()
    async for sol in evaluate(node.p, tc, collection, limit):
        key = tuple(sorted(
            (k, _term_key(v)) for k, v in sol.items()
        ))
        if key not in seen:
            seen.add(key)
            yield sol


async def _eval_reduced(node, tc, collection, limit):
    async for sol in _eval_distinct(node, tc, collection, limit):
        yield sol


async def _eval_order_by(node, tc, collection, limit):
    solutions = await materialise(node.p, tc, collection, limit)

    key_fns = []
    for cond in node.expr:
        if isinstance(cond, CompValue) and cond.name == "OrderCondition":
            ascending = cond.order != "DESC"
            expr = cond.expr
            key_fns.append((
                lambda sol, e=expr: evaluate_expression(e, sol),
                ascending,
            ))
        else:
            key_fns.append((
                lambda sol, e=cond: evaluate_expression(e, sol),
                True,
            ))

    for sol in order_by(solutions, key_fns):
        yield sol


# --- Streamable operators ---

async def _eval_slice(node, tc, collection, limit):
    offset = node.start or 0
    length = node.length
    skipped = 0
    emitted = 0

    async for sol in evaluate(node.p, tc, collection, limit):
        if skipped < offset:
            skipped += 1
            continue
        yield sol
        emitted += 1
        if length is not None and emitted >= length:
            return


async def _eval_union(node, tc, collection, limit):
    async for sol in evaluate(node.p1, tc, collection, limit):
        yield sol
    async for sol in evaluate(node.p2, tc, collection, limit):
        yield sol


async def _check_exists(graph_node, sol, tc, collection, limit):
    """Evaluate an EXISTS graph pattern against a solution."""
    async for r in evaluate(graph_node, tc, collection, limit):
        shared = set(sol.keys()) & set(r.keys())
        if all(
            _term_key(sol[v]) == _term_key(r[v])
            for v in shared
            if sol.get(v) is not None and r.get(v) is not None
        ):
            return True
    return False


async def _pre_eval_exists(expr, sol, tc, collection, limit, cache):
    """Walk an expression tree, pre-evaluate EXISTS/NOT EXISTS, cache results."""
    if not isinstance(expr, CompValue):
        return
    if expr.name in ("Builtin_EXISTS", "Builtin_NOTEXISTS"):
        key = id(expr.graph), id(sol)
        if key not in cache:
            cache[key] = await _check_exists(
                expr.graph, sol, tc, collection, limit
            )
        return
    for attr in ("expr", "other", "arg", "arg1", "arg2", "arg3"):
        child = getattr(expr, attr, None)
        if child is None:
            continue
        if isinstance(child, CompValue):
            await _pre_eval_exists(child, sol, tc, collection, limit, cache)
        elif isinstance(child, (list, tuple)):
            for item in child:
                if isinstance(item, CompValue):
                    await _pre_eval_exists(
                        item, sol, tc, collection, limit, cache
                    )


async def _eval_filter(node, tc, collection, limit):
    expr = node.expr
    exists_cache = {}

    def exists_cb(graph_node, sol):
        key = id(graph_node), id(sol)
        return exists_cache.get(key, False)

    async for sol in evaluate(node.p, tc, collection, limit):
        await _pre_eval_exists(expr, sol, tc, collection, limit, exists_cache)
        if _effective_boolean(evaluate_expression(expr, sol, exists_cb=exists_cb)):
            yield sol


async def _eval_extend(node, tc, collection, limit):
    var_name = str(node.var)
    expr = node.expr
    exists_cache = {}

    def exists_cb(graph_node, sol):
        key = id(graph_node), id(sol)
        return exists_cache.get(key, False)

    async for sol in evaluate(node.p, tc, collection, limit):
        await _pre_eval_exists(expr, sol, tc, collection, limit, exists_cache)
        val = evaluate_expression(expr, sol, exists_cb=exists_cb)
        new_sol = dict(sol)
        if isinstance(val, Term):
            new_sol[var_name] = val
        elif isinstance(val, (int, float)):
            new_sol[var_name] = Term(type=LITERAL, value=str(val))
        elif isinstance(val, str):
            new_sol[var_name] = Term(type=LITERAL, value=val)
        elif isinstance(val, bool):
            new_sol[var_name] = Term(
                type=LITERAL, value=str(val).lower(),
                datatype="http://www.w3.org/2001/XMLSchema#boolean"
            )
        elif val is not None:
            new_sol[var_name] = Term(type=LITERAL, value=str(val))
        yield new_sol


# --- Aggregation (blocking) ---

async def _eval_group(node, tc, collection, limit):
    solutions = await materialise(node.p, tc, collection, limit)

    group_exprs = []
    if hasattr(node, "expr") and node.expr:
        for expr in node.expr:
            if isinstance(expr, CompValue) and expr.name == "GroupAs":
                group_exprs.append((expr.expr, str(expr.var) if hasattr(expr, "var") and expr.var else None))
            elif isinstance(expr, Variable):
                group_exprs.append((expr, str(expr)))
            else:
                group_exprs.append((expr, None))

    groups = defaultdict(list)
    for sol in solutions:
        key_parts = []
        for expr, _ in group_exprs:
            val = evaluate_expression(expr, sol)
            key_parts.append(_term_key(val) if isinstance(val, Term) else val)
        groups[tuple(key_parts)].append(sol)

    if not group_exprs:
        groups[()].extend(solutions)

    for key, group_sols in groups.items():
        sol = {}
        if group_sols:
            for (expr, var_name), k in zip(group_exprs, key):
                if var_name and group_sols:
                    sol[var_name] = evaluate_expression(expr, group_sols[0])
        sol["__group__"] = group_sols
        yield sol


async def _eval_aggregate_join(node, tc, collection, limit):
    async for sol in evaluate(node.p, tc, collection, limit):
        group = sol.get("__group__", [sol])
        new_sol = {k: v for k, v in sol.items() if k != "__group__"}

        if hasattr(node, "A") and node.A:
            for agg in node.A:
                var_name = str(agg.res)
                agg_val = _compute_aggregate(agg, group)
                new_sol[var_name] = agg_val

        yield new_sol


async def _eval_graph(node, tc, collection, limit):
    term = node.term

    if isinstance(term, URIRef):
        logger.info(f"GRAPH <{term}> clause - graph filtering not yet wired")
    elif isinstance(term, Variable):
        logger.info(f"GRAPH ?{term} clause - variable graph not yet wired")

    async for sol in evaluate(node.p, tc, collection, limit):
        yield sol


async def _eval_values(node, tc, collection, limit):
    # rdflib has two representations for VALUES:
    # 1. var=[Variable...], value=[[val, ...], ...] — positional
    # 2. var=None, res=[{Variable: val, ...}, ...] — dict-based
    if hasattr(node, "res") and node.res:
        for row in node.res:
            sol = {}
            for var, val in row.items():
                if val is not None and str(val) != "UNDEF":
                    sol[str(var)] = rdflib_term_to_term(val)
            yield sol
        return

    if not node.var or not node.value:
        yield {}
        return
    variables = [str(v) for v in node.var]
    for row in node.value:
        sol = {}
        for var_name, val in zip(variables, row):
            if val is not None and str(val) != "UNDEF":
                sol[var_name] = rdflib_term_to_term(val)
        yield sol


async def _eval_to_multiset(node, tc, collection, limit):
    async for sol in evaluate(node.p, tc, collection, limit):
        yield sol


# --- Aggregate computation ---

def _compute_aggregate(agg, group):
    """Compute a single aggregate function over a group of solutions."""
    agg_name = agg.name if hasattr(agg, "name") else ""

    expr = agg.vars if hasattr(agg, "vars") else None

    if agg_name == "Aggregate_Count":
        if hasattr(agg, "distinct") and agg.distinct:
            vals = set()
            for sol in group:
                if expr:
                    val = evaluate_expression(expr, sol)
                    if val is not None:
                        vals.add(_term_key(val) if isinstance(val, Term) else val)
                else:
                    vals.add(id(sol))
            return Term(type=LITERAL, value=str(len(vals)),
                       datatype="http://www.w3.org/2001/XMLSchema#integer")
        return Term(type=LITERAL, value=str(len(group)),
                   datatype="http://www.w3.org/2001/XMLSchema#integer")

    if agg_name == "Aggregate_Sum":
        total = 0
        for sol in group:
            val = evaluate_expression(expr, sol) if expr else None
            num = _try_numeric(val)
            if num is not None:
                total += num
        return Term(type=LITERAL, value=str(total),
                   datatype="http://www.w3.org/2001/XMLSchema#decimal")

    if agg_name == "Aggregate_Avg":
        total = 0
        count = 0
        for sol in group:
            val = evaluate_expression(expr, sol) if expr else None
            num = _try_numeric(val)
            if num is not None:
                total += num
                count += 1
        avg = total / count if count > 0 else 0
        return Term(type=LITERAL, value=str(avg),
                   datatype="http://www.w3.org/2001/XMLSchema#decimal")

    if agg_name == "Aggregate_Min":
        min_val = None
        for sol in group:
            val = evaluate_expression(expr, sol) if expr else None
            if val is not None:
                cmp = _term_key(val) if isinstance(val, Term) else val
                if min_val is None or cmp < min_val[0]:
                    min_val = (cmp, val)
        if min_val:
            val = min_val[1]
            if isinstance(val, Term):
                return val
            return Term(type=LITERAL, value=str(val))
        return None

    if agg_name == "Aggregate_Max":
        max_val = None
        for sol in group:
            val = evaluate_expression(expr, sol) if expr else None
            if val is not None:
                cmp = _term_key(val) if isinstance(val, Term) else val
                if max_val is None or cmp > max_val[0]:
                    max_val = (cmp, val)
        if max_val:
            val = max_val[1]
            if isinstance(val, Term):
                return val
            return Term(type=LITERAL, value=str(val))
        return None

    if agg_name == "Aggregate_GroupConcat":
        separator = agg.separator if hasattr(agg, "separator") else " "
        vals = []
        for sol in group:
            val = evaluate_expression(expr, sol) if expr else None
            if val is not None:
                if isinstance(val, Term):
                    vals.append(val.value if val.type == LITERAL else val.iri)
                else:
                    vals.append(str(val))
        return Term(type=LITERAL, value=separator.join(vals))

    if agg_name == "Aggregate_Sample":
        if group:
            val = evaluate_expression(expr, group[0]) if expr else None
            if isinstance(val, Term):
                return val
            if val is not None:
                return Term(type=LITERAL, value=str(val))
        return None

    logger.warning(f"Unsupported aggregate: {agg_name}")
    return None


# --- Helper functions ---

def _to_term(val):
    """
    Convert a value to a schema Term. Handles Uri and Literal from the
    knowledge module (returned by TriplesClient) as well as plain strings.
    """
    if val is None:
        return None
    if isinstance(val, Term):
        return val
    if isinstance(val, Uri):
        return Term(type=IRI, iri=str(val))
    if isinstance(val, KgLiteral):
        return Term(type=LITERAL, value=str(val))
    if isinstance(val, str):
        if val.startswith("http://") or val.startswith("https://") or val.startswith("urn:"):
            return Term(type=IRI, iri=val)
        return Term(type=LITERAL, value=val)
    return Term(type=LITERAL, value=str(val))


def _resolve_term(tmpl, solution):
    """
    Resolve a triple pattern term. If it's a variable and bound in the
    solution, return the bound Term. Otherwise return None (wildcard)
    for variables, or convert concrete terms.
    """
    if isinstance(tmpl, Variable):
        name = str(tmpl)
        if name in solution:
            return solution[name]
        return None
    else:
        return rdflib_term_to_term(tmpl)


async def _query_pattern(tc, s, p, o, collection, limit):
    """
    Issue a streaming triple pattern query via TriplesClient.

    Returns a list of Triple-like objects with s, p, o attributes.
    """
    results = await tc.query(
        s=s, p=p, o=o,
        limit=limit,
        collection=collection,
    )
    return results


def _try_numeric(val):
    """Try to convert a value to a number, return None on failure."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return val
    if isinstance(val, Term) and val.type == LITERAL:
        try:
            if "." in val.value:
                return float(val.value)
            return int(val.value)
        except (ValueError, TypeError):
            return None
    return None


# --- Handler registry ---

_HANDLERS = {
    "SelectQuery": _eval_select_query,
    "Project": _eval_project,
    "BGP": _eval_bgp,
    "Join": _eval_join,
    "LeftJoin": _eval_left_join,
    "Union": _eval_union,
    "Minus": _eval_minus,
    "Filter": _eval_filter,
    "Distinct": _eval_distinct,
    "Reduced": _eval_reduced,
    "OrderBy": _eval_order_by,
    "Slice": _eval_slice,
    "Extend": _eval_extend,
    "Group": _eval_group,
    "AggregateJoin": _eval_aggregate_join,
    "Graph": _eval_graph,
    "values": _eval_values,
    "ToMultiSet": _eval_to_multiset,
}
