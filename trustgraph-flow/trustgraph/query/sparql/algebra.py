"""
SPARQL algebra evaluator.

Recursively evaluates an rdflib SPARQL algebra tree by issuing triple
pattern queries via TriplesClient (streaming) and performing in-memory
joins, filters, and projections.
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
    hash_join, left_join, union, project, distinct,
    order_by, slice_solutions, _term_key,
)
from . expressions import evaluate_expression, _effective_boolean

logger = logging.getLogger(__name__)


class EvaluationError(Exception):
    """Raised when SPARQL evaluation fails."""
    pass


async def evaluate(node, triples_client, user, collection, limit=10000):
    """
    Evaluate a SPARQL algebra node.

    Args:
        node: rdflib CompValue algebra node
        triples_client: TriplesClient instance for triple pattern queries
        user: user/keyspace identifier
        collection: collection identifier
        limit: safety limit on results

    Returns:
        list of solutions (dicts mapping variable names to Term values)
    """
    if not isinstance(node, CompValue):
        logger.warning(f"Expected CompValue, got {type(node)}: {node}")
        return [{}]

    name = node.name
    handler = _HANDLERS.get(name)

    if handler is None:
        logger.warning(f"Unsupported algebra node: {name}")
        return [{}]

    return await handler(node, triples_client, user, collection, limit)


# --- Node handlers ---

async def _eval_select_query(node, tc, user, collection, limit):
    """Evaluate a SelectQuery node."""
    return await evaluate(node.p, tc, user, collection, limit)


async def _eval_project(node, tc, user, collection, limit):
    """Evaluate a Project node (SELECT variable projection)."""
    solutions = await evaluate(node.p, tc, user, collection, limit)
    variables = [str(v) for v in node.PV]
    return project(solutions, variables)


async def _eval_bgp(node, tc, user, collection, limit):
    """
    Evaluate a Basic Graph Pattern.

    Issues streaming triple pattern queries and joins results. Patterns
    are ordered by selectivity (more bound terms first) and evaluated
    sequentially with bound-variable substitution.
    """
    triples = node.triples
    if not triples:
        return [{}]

    # Sort patterns by selectivity: more bound terms = more selective
    def selectivity(pattern):
        return sum(1 for t in pattern if not isinstance(t, Variable))

    sorted_patterns = sorted(
        enumerate(triples), key=lambda x: -selectivity(x[1])
    )

    solutions = [{}]

    for _, pattern in sorted_patterns:
        s_tmpl, p_tmpl, o_tmpl = pattern

        new_solutions = []

        for sol in solutions:
            # Substitute known bindings into the pattern
            s_val = _resolve_term(s_tmpl, sol)
            p_val = _resolve_term(p_tmpl, sol)
            o_val = _resolve_term(o_tmpl, sol)

            # Query the triples store
            results = await _query_pattern(
                tc, s_val, p_val, o_val, user, collection, limit
            )

            # Map results back to variable bindings,
            # converting Uri/Literal to Term objects
            for triple in results:
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
            break

    return solutions[:limit]


async def _eval_join(node, tc, user, collection, limit):
    """Evaluate a Join node."""
    left = await evaluate(node.p1, tc, user, collection, limit)
    right = await evaluate(node.p2, tc, user, collection, limit)
    return hash_join(left, right)[:limit]


async def _eval_left_join(node, tc, user, collection, limit):
    """Evaluate a LeftJoin node (OPTIONAL)."""
    left_sols = await evaluate(node.p1, tc, user, collection, limit)
    right_sols = await evaluate(node.p2, tc, user, collection, limit)

    filter_fn = None
    if hasattr(node, "expr") and node.expr is not None:
        expr = node.expr
        if not (isinstance(expr, CompValue) and expr.name == "TrueFilter"):
            filter_fn = lambda sol: _effective_boolean(
                evaluate_expression(expr, sol)
            )

    return left_join(left_sols, right_sols, filter_fn)[:limit]


async def _eval_union(node, tc, user, collection, limit):
    """Evaluate a Union node."""
    left = await evaluate(node.p1, tc, user, collection, limit)
    right = await evaluate(node.p2, tc, user, collection, limit)
    return union(left, right)[:limit]


async def _eval_filter(node, tc, user, collection, limit):
    """Evaluate a Filter node."""
    solutions = await evaluate(node.p, tc, user, collection, limit)
    expr = node.expr
    return [
        sol for sol in solutions
        if _effective_boolean(evaluate_expression(expr, sol))
    ]


async def _eval_distinct(node, tc, user, collection, limit):
    """Evaluate a Distinct node."""
    solutions = await evaluate(node.p, tc, user, collection, limit)
    return distinct(solutions)


async def _eval_reduced(node, tc, user, collection, limit):
    """Evaluate a Reduced node (like Distinct but implementation-defined)."""
    # Treat same as Distinct
    solutions = await evaluate(node.p, tc, user, collection, limit)
    return distinct(solutions)


async def _eval_order_by(node, tc, user, collection, limit):
    """Evaluate an OrderBy node."""
    solutions = await evaluate(node.p, tc, user, collection, limit)

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
            # Simple variable or expression
            key_fns.append((
                lambda sol, e=cond: evaluate_expression(e, sol),
                True,
            ))

    return order_by(solutions, key_fns)


async def _eval_slice(node, tc, user, collection, limit):
    """Evaluate a Slice node (LIMIT/OFFSET)."""
    # Pass tighter limit downstream if possible
    inner_limit = limit
    if node.length is not None:
        offset = node.start or 0
        inner_limit = min(limit, offset + node.length)

    solutions = await evaluate(node.p, tc, user, collection, inner_limit)
    return slice_solutions(solutions, node.start or 0, node.length)


async def _eval_extend(node, tc, user, collection, limit):
    """Evaluate an Extend node (BIND)."""
    solutions = await evaluate(node.p, tc, user, collection, limit)
    var_name = str(node.var)
    expr = node.expr

    result = []
    for sol in solutions:
        val = evaluate_expression(expr, sol)
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
        result.append(new_sol)

    return result


async def _eval_group(node, tc, user, collection, limit):
    """Evaluate a Group node (GROUP BY with aggregation)."""
    solutions = await evaluate(node.p, tc, user, collection, limit)

    # Extract grouping expressions
    group_exprs = []
    if hasattr(node, "expr") and node.expr:
        for expr in node.expr:
            if isinstance(expr, CompValue) and expr.name == "GroupAs":
                group_exprs.append((expr.expr, str(expr.var) if hasattr(expr, "var") and expr.var else None))
            elif isinstance(expr, Variable):
                group_exprs.append((expr, str(expr)))
            else:
                group_exprs.append((expr, None))

    # Group solutions
    groups = defaultdict(list)
    for sol in solutions:
        key_parts = []
        for expr, _ in group_exprs:
            val = evaluate_expression(expr, sol)
            key_parts.append(_term_key(val) if isinstance(val, Term) else val)
        groups[tuple(key_parts)].append(sol)

    if not group_exprs:
        # No GROUP BY - entire result is one group
        groups[()].extend(solutions)

    # Build grouped solutions (one per group)
    result = []
    for key, group_sols in groups.items():
        sol = {}
        # Include group key variables
        if group_sols:
            for (expr, var_name), k in zip(group_exprs, key):
                if var_name and group_sols:
                    sol[var_name] = evaluate_expression(expr, group_sols[0])
        sol["__group__"] = group_sols
        result.append(sol)

    return result


async def _eval_aggregate_join(node, tc, user, collection, limit):
    """Evaluate an AggregateJoin (aggregation functions after GROUP BY)."""
    solutions = await evaluate(node.p, tc, user, collection, limit)

    result = []
    for sol in solutions:
        group = sol.get("__group__", [sol])
        new_sol = {k: v for k, v in sol.items() if k != "__group__"}

        # Apply aggregate functions
        if hasattr(node, "A") and node.A:
            for agg in node.A:
                var_name = str(agg.res)
                agg_val = _compute_aggregate(agg, group)
                new_sol[var_name] = agg_val

        result.append(new_sol)

    return result


async def _eval_graph(node, tc, user, collection, limit):
    """Evaluate a Graph node (GRAPH clause)."""
    term = node.term

    if isinstance(term, URIRef):
        # GRAPH <uri> { ... } — fixed graph
        # We'd need to pass graph to triples queries
        # For now, evaluate inner pattern normally
        logger.info(f"GRAPH <{term}> clause - graph filtering not yet wired")
        return await evaluate(node.p, tc, user, collection, limit)
    elif isinstance(term, Variable):
        # GRAPH ?g { ... } — variable graph
        logger.info(f"GRAPH ?{term} clause - variable graph not yet wired")
        return await evaluate(node.p, tc, user, collection, limit)
    else:
        return await evaluate(node.p, tc, user, collection, limit)


async def _eval_values(node, tc, user, collection, limit):
    """Evaluate a VALUES clause (inline data)."""
    variables = [str(v) for v in node.var]
    solutions = []

    for row in node.value:
        sol = {}
        for var_name, val in zip(variables, row):
            if val is not None and str(val) != "UNDEF":
                sol[var_name] = rdflib_term_to_term(val)
        solutions.append(sol)

    return solutions


async def _eval_to_multiset(node, tc, user, collection, limit):
    """Evaluate a ToMultiSet node (subquery)."""
    return await evaluate(node.p, tc, user, collection, limit)


# --- Aggregate computation ---

def _compute_aggregate(agg, group):
    """Compute a single aggregate function over a group of solutions."""
    agg_name = agg.name if hasattr(agg, "name") else ""

    # Get the expression to aggregate
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


async def _query_pattern(tc, s, p, o, user, collection, limit):
    """
    Issue a streaming triple pattern query via TriplesClient.

    Returns a list of Triple-like objects with s, p, o attributes.
    """
    results = await tc.query(
        s=s, p=p, o=o,
        limit=limit,
        user=user,
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
