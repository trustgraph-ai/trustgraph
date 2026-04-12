"""
Solution sequence operations for SPARQL evaluation.

A solution is a dict mapping variable names (str) to Term values.
A solution sequence is a list of solutions.
"""

import logging
from collections import defaultdict

from ... schema import Term, IRI, LITERAL, BLANK

logger = logging.getLogger(__name__)


def _term_key(term):
    """Create a hashable key from a Term for join/distinct operations."""
    if term is None:
        return None
    if term.type == IRI:
        return ("i", term.iri)
    elif term.type == LITERAL:
        return ("l", term.value, term.datatype, term.language)
    elif term.type == BLANK:
        return ("b", term.id)
    else:
        return ("?", str(term))


def _solution_key(solution, variables):
    """Create a hashable key from a solution for the given variables."""
    return tuple(_term_key(solution.get(v)) for v in variables)


def _terms_equal(a, b):
    """Check if two Terms are equal."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return _term_key(a) == _term_key(b)


def _compatible(sol_a, sol_b):
    """Check if two solutions are compatible (agree on shared variables)."""
    shared = set(sol_a.keys()) & set(sol_b.keys())
    return all(_terms_equal(sol_a[v], sol_b[v]) for v in shared)


def _merge(sol_a, sol_b):
    """Merge two compatible solutions into one."""
    result = dict(sol_a)
    result.update(sol_b)
    return result


def hash_join(left, right):
    """
    Inner join two solution sequences on shared variables.
    Uses hash join for efficiency.
    """
    if not left or not right:
        return []

    left_vars = set()
    for sol in left:
        left_vars.update(sol.keys())

    right_vars = set()
    for sol in right:
        right_vars.update(sol.keys())

    shared = sorted(left_vars & right_vars)

    if not shared:
        # Cross product
        return [_merge(l, r) for l in left for r in right]

    # Build hash table on the smaller side
    if len(left) <= len(right):
        index = defaultdict(list)
        for sol in left:
            key = _solution_key(sol, shared)
            index[key].append(sol)

        results = []
        for sol_r in right:
            key = _solution_key(sol_r, shared)
            for sol_l in index.get(key, []):
                results.append(_merge(sol_l, sol_r))
        return results
    else:
        index = defaultdict(list)
        for sol in right:
            key = _solution_key(sol, shared)
            index[key].append(sol)

        results = []
        for sol_l in left:
            key = _solution_key(sol_l, shared)
            for sol_r in index.get(key, []):
                results.append(_merge(sol_l, sol_r))
        return results


def left_join(left, right, filter_fn=None):
    """
    Left outer join (OPTIONAL semantics).
    Every left solution is preserved. If it joins with right solutions
    (and passes the optional filter), the merged solutions are included.
    Otherwise the original left solution is kept.
    """
    if not left:
        return []

    if not right:
        return list(left)

    right_vars = set()
    for sol in right:
        right_vars.update(sol.keys())

    left_vars = set()
    for sol in left:
        left_vars.update(sol.keys())

    shared = sorted(left_vars & right_vars)

    # Build hash table on right side
    index = defaultdict(list)
    for sol in right:
        key = _solution_key(sol, shared) if shared else ()
        index[key].append(sol)

    results = []
    for sol_l in left:
        key = _solution_key(sol_l, shared) if shared else ()
        matches = index.get(key, [])

        matched = False
        for sol_r in matches:
            merged = _merge(sol_l, sol_r)
            if filter_fn is None or filter_fn(merged):
                results.append(merged)
                matched = True

        if not matched:
            results.append(dict(sol_l))

    return results


def union(left, right):
    """Union two solution sequences (concatenation)."""
    return list(left) + list(right)


def project(solutions, variables):
    """Keep only the specified variables in each solution."""
    return [
        {v: sol[v] for v in variables if v in sol}
        for sol in solutions
    ]


def distinct(solutions):
    """Remove duplicate solutions."""
    seen = set()
    results = []
    for sol in solutions:
        key = tuple(sorted(
            (k, _term_key(v)) for k, v in sol.items()
        ))
        if key not in seen:
            seen.add(key)
            results.append(sol)
    return results


def order_by(solutions, key_fns):
    """
    Sort solutions by the given key functions.

    key_fns is a list of (fn, ascending) tuples where fn extracts
    a comparable value from a solution.
    """
    if not key_fns:
        return solutions

    def sort_key(sol):
        keys = []
        for fn, ascending in key_fns:
            val = fn(sol)
            # Convert to comparable form
            if val is None:
                comparable = ("", "")
            elif isinstance(val, Term):
                comparable = _term_key(val)
            else:
                comparable = ("v", str(val))
            keys.append(comparable)
        return keys

    # Handle ascending/descending
    # For simplicity, sort ascending then reverse individual keys
    # This works for single sort keys; for multiple mixed keys we
    # need a wrapper
    result = sorted(solutions, key=sort_key)

    # If any key is descending, we need a more complex approach.
    # Check if all are same direction for the simple case.
    if key_fns and all(not asc for _, asc in key_fns):
        result.reverse()
    elif key_fns and not all(asc for _, asc in key_fns):
        # Mixed ascending/descending - use negation wrapper
        result = _mixed_sort(solutions, key_fns)

    return result


def _mixed_sort(solutions, key_fns):
    """Sort with mixed ascending/descending keys."""
    import functools

    def compare(a, b):
        for fn, ascending in key_fns:
            va = fn(a)
            vb = fn(b)
            ka = _term_key(va) if isinstance(va, Term) else ("v", str(va)) if va is not None else ("", "")
            kb = _term_key(vb) if isinstance(vb, Term) else ("v", str(vb)) if vb is not None else ("", "")

            if ka < kb:
                return -1 if ascending else 1
            elif ka > kb:
                return 1 if ascending else -1

        return 0

    return sorted(solutions, key=functools.cmp_to_key(compare))


def slice_solutions(solutions, offset=0, limit=None):
    """Apply OFFSET and LIMIT to a solution sequence."""
    if offset:
        solutions = solutions[offset:]
    if limit is not None:
        solutions = solutions[:limit]
    return solutions
