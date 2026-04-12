"""
SPARQL FILTER expression evaluator.

Evaluates rdflib algebra expression nodes against a solution (variable
binding) to produce a value or boolean result.
"""

import re
import logging
import operator

from rdflib.term import Variable, URIRef, Literal, BNode
from rdflib.plugins.sparql.parserutils import CompValue

from ... schema import Term, IRI, LITERAL, BLANK
from . parser import rdflib_term_to_term

logger = logging.getLogger(__name__)


class ExpressionError(Exception):
    """Raised when a SPARQL expression cannot be evaluated."""
    pass


def evaluate_expression(expr, solution):
    """
    Evaluate a SPARQL expression against a solution binding.

    Args:
        expr: rdflib algebra expression node
        solution: dict mapping variable names to Term values

    Returns:
        The result value (Term, bool, number, string, or None)
    """
    if expr is None:
        return True

    # rdflib Variable
    if isinstance(expr, Variable):
        name = str(expr)
        return solution.get(name)

    # rdflib concrete terms
    if isinstance(expr, URIRef):
        return Term(type=IRI, iri=str(expr))

    if isinstance(expr, Literal):
        return rdflib_term_to_term(expr)

    if isinstance(expr, BNode):
        return Term(type=BLANK, id=str(expr))

    # Boolean constants
    if isinstance(expr, bool):
        return expr

    # Numeric constants
    if isinstance(expr, (int, float)):
        return expr

    # String constants
    if isinstance(expr, str):
        return expr

    # CompValue nodes from rdflib algebra
    if isinstance(expr, CompValue):
        return _evaluate_comp_value(expr, solution)

    # List/tuple (e.g. function arguments)
    if isinstance(expr, (list, tuple)):
        return [evaluate_expression(e, solution) for e in expr]

    logger.warning(f"Unknown expression type: {type(expr)}: {expr}")
    return None


def _evaluate_comp_value(node, solution):
    """Evaluate a CompValue expression node."""
    name = node.name

    # Relational expressions: =, !=, <, >, <=, >=
    if name == "RelationalExpression":
        return _eval_relational(node, solution)

    # Conditional AND / OR
    if name == "ConditionalAndExpression":
        return _eval_conditional_and(node, solution)

    if name == "ConditionalOrExpression":
        return _eval_conditional_or(node, solution)

    # Unary NOT
    if name == "UnaryNot":
        val = evaluate_expression(node.expr, solution)
        return not _effective_boolean(val)

    # Unary plus/minus
    if name == "UnaryPlus":
        return _to_numeric(evaluate_expression(node.expr, solution))

    if name == "UnaryMinus":
        val = _to_numeric(evaluate_expression(node.expr, solution))
        return -val if val is not None else None

    # Arithmetic
    if name == "AdditiveExpression":
        return _eval_additive(node, solution)

    if name == "MultiplicativeExpression":
        return _eval_multiplicative(node, solution)

    # SPARQL built-in functions
    if name.startswith("Builtin_"):
        return _eval_builtin(name, node, solution)

    # Function call
    if name == "Function":
        return _eval_function(node, solution)

    # Exists / NotExists
    if name == "Builtin_EXISTS":
        # EXISTS requires graph pattern evaluation - not handled here
        logger.warning("EXISTS not supported in filter expressions")
        return True

    if name == "Builtin_NOTEXISTS":
        logger.warning("NOT EXISTS not supported in filter expressions")
        return True

    # TrueFilter (used with OPTIONAL)
    if name == "TrueFilter":
        return True

    # IN / NOT IN
    if name == "Builtin_IN":
        return _eval_in(node, solution)

    if name == "Builtin_NOTIN":
        return not _eval_in(node, solution)

    logger.warning(f"Unknown CompValue expression: {name}")
    return None


def _eval_relational(node, solution):
    """Evaluate a relational expression (=, !=, <, >, <=, >=)."""
    left = evaluate_expression(node.expr, solution)
    right = evaluate_expression(node.other, solution)
    op = node.op

    if left is None or right is None:
        return False

    left_cmp = _comparable_value(left)
    right_cmp = _comparable_value(right)

    ops = {
        "=": operator.eq, "==": operator.eq,
        "!=": operator.ne,
        "<": operator.lt,
        ">": operator.gt,
        "<=": operator.le,
        ">=": operator.ge,
    }

    op_fn = ops.get(str(op))
    if op_fn is None:
        logger.warning(f"Unknown relational operator: {op}")
        return False

    try:
        return op_fn(left_cmp, right_cmp)
    except TypeError:
        return False


def _eval_conditional_and(node, solution):
    """Evaluate AND expression."""
    result = _effective_boolean(evaluate_expression(node.expr, solution))
    if not result:
        return False
    for other in node.other:
        result = _effective_boolean(evaluate_expression(other, solution))
        if not result:
            return False
    return True


def _eval_conditional_or(node, solution):
    """Evaluate OR expression."""
    result = _effective_boolean(evaluate_expression(node.expr, solution))
    if result:
        return True
    for other in node.other:
        result = _effective_boolean(evaluate_expression(other, solution))
        if result:
            return True
    return False


def _eval_additive(node, solution):
    """Evaluate additive expression (a + b - c ...)."""
    result = _to_numeric(evaluate_expression(node.expr, solution))
    if result is None:
        return None
    for op, operand in zip(node.op, node.other):
        val = _to_numeric(evaluate_expression(operand, solution))
        if val is None:
            return None
        if str(op) == "+":
            result = result + val
        elif str(op) == "-":
            result = result - val
    return result


def _eval_multiplicative(node, solution):
    """Evaluate multiplicative expression (a * b / c ...)."""
    result = _to_numeric(evaluate_expression(node.expr, solution))
    if result is None:
        return None
    for op, operand in zip(node.op, node.other):
        val = _to_numeric(evaluate_expression(operand, solution))
        if val is None:
            return None
        if str(op) == "*":
            result = result * val
        elif str(op) == "/":
            if val == 0:
                return None
            result = result / val
    return result


def _eval_builtin(name, node, solution):
    """Evaluate SPARQL built-in functions."""
    builtin = name[len("Builtin_"):]

    if builtin == "BOUND":
        var_name = str(node.arg)
        return var_name in solution and solution[var_name] is not None

    if builtin == "isIRI" or builtin == "isURI":
        val = evaluate_expression(node.arg, solution)
        return isinstance(val, Term) and val.type == IRI

    if builtin == "isLITERAL":
        val = evaluate_expression(node.arg, solution)
        return isinstance(val, Term) and val.type == LITERAL

    if builtin == "isBLANK":
        val = evaluate_expression(node.arg, solution)
        return isinstance(val, Term) and val.type == BLANK

    if builtin == "STR":
        val = evaluate_expression(node.arg, solution)
        return Term(type=LITERAL, value=_to_string(val))

    if builtin == "LANG":
        val = evaluate_expression(node.arg, solution)
        if isinstance(val, Term) and val.type == LITERAL:
            return Term(type=LITERAL, value=val.language or "")
        return Term(type=LITERAL, value="")

    if builtin == "DATATYPE":
        val = evaluate_expression(node.arg, solution)
        if isinstance(val, Term) and val.type == LITERAL and val.datatype:
            return Term(type=IRI, iri=val.datatype)
        return Term(type=IRI, iri="http://www.w3.org/2001/XMLSchema#string")

    if builtin == "REGEX":
        text = _to_string(evaluate_expression(node.text, solution))
        pattern = _to_string(evaluate_expression(node.pattern, solution))
        flags_str = ""
        if hasattr(node, "flags") and node.flags is not None:
            flags_str = _to_string(evaluate_expression(node.flags, solution))

        re_flags = 0
        if "i" in flags_str:
            re_flags |= re.IGNORECASE
        if "m" in flags_str:
            re_flags |= re.MULTILINE
        if "s" in flags_str:
            re_flags |= re.DOTALL

        try:
            return bool(re.search(pattern, text, re_flags))
        except re.error:
            return False

    if builtin == "STRLEN":
        val = _to_string(evaluate_expression(node.arg, solution))
        return len(val)

    if builtin == "UCASE":
        val = _to_string(evaluate_expression(node.arg, solution))
        return Term(type=LITERAL, value=val.upper())

    if builtin == "LCASE":
        val = _to_string(evaluate_expression(node.arg, solution))
        return Term(type=LITERAL, value=val.lower())

    if builtin == "CONTAINS":
        string = _to_string(evaluate_expression(node.arg1, solution))
        pattern = _to_string(evaluate_expression(node.arg2, solution))
        return pattern in string

    if builtin == "STRSTARTS":
        string = _to_string(evaluate_expression(node.arg1, solution))
        prefix = _to_string(evaluate_expression(node.arg2, solution))
        return string.startswith(prefix)

    if builtin == "STRENDS":
        string = _to_string(evaluate_expression(node.arg1, solution))
        suffix = _to_string(evaluate_expression(node.arg2, solution))
        return string.endswith(suffix)

    if builtin == "CONCAT":
        args = [_to_string(evaluate_expression(a, solution)) for a in node.arg]
        return Term(type=LITERAL, value="".join(args))

    if builtin == "IF":
        cond = _effective_boolean(evaluate_expression(node.arg1, solution))
        if cond:
            return evaluate_expression(node.arg2, solution)
        else:
            return evaluate_expression(node.arg3, solution)

    if builtin == "COALESCE":
        for arg in node.arg:
            val = evaluate_expression(arg, solution)
            if val is not None:
                return val
        return None

    if builtin == "sameTerm":
        left = evaluate_expression(node.arg1, solution)
        right = evaluate_expression(node.arg2, solution)
        if not isinstance(left, Term) or not isinstance(right, Term):
            return False
        from . solutions import _term_key
        return _term_key(left) == _term_key(right)

    logger.warning(f"Unsupported built-in function: {builtin}")
    return None


def _eval_function(node, solution):
    """Evaluate a SPARQL function call."""
    # Cast functions (xsd:integer, xsd:string, etc.)
    iri = str(node.iri) if hasattr(node, "iri") else ""
    args = [evaluate_expression(a, solution) for a in node.expr]

    xsd = "http://www.w3.org/2001/XMLSchema#"
    if iri == xsd + "integer":
        try:
            return int(_to_numeric(args[0]))
        except (TypeError, ValueError):
            return None
    elif iri == xsd + "decimal" or iri == xsd + "double" or iri == xsd + "float":
        try:
            return float(_to_numeric(args[0]))
        except (TypeError, ValueError):
            return None
    elif iri == xsd + "string":
        return Term(type=LITERAL, value=_to_string(args[0]))
    elif iri == xsd + "boolean":
        return _effective_boolean(args[0])

    logger.warning(f"Unsupported function: {iri}")
    return None


def _eval_in(node, solution):
    """Evaluate IN expression."""
    val = evaluate_expression(node.expr, solution)
    for item in node.other:
        other = evaluate_expression(item, solution)
        if _comparable_value(val) == _comparable_value(other):
            return True
    return False


# --- Value conversion helpers ---

def _effective_boolean(val):
    """Convert a value to its effective boolean value (EBV)."""
    if isinstance(val, bool):
        return val
    if val is None:
        return False
    if isinstance(val, (int, float)):
        return val != 0
    if isinstance(val, str):
        return len(val) > 0
    if isinstance(val, Term):
        if val.type == LITERAL:
            v = val.value
            if val.datatype == "http://www.w3.org/2001/XMLSchema#boolean":
                return v.lower() in ("true", "1")
            if val.datatype in (
                "http://www.w3.org/2001/XMLSchema#integer",
                "http://www.w3.org/2001/XMLSchema#decimal",
                "http://www.w3.org/2001/XMLSchema#double",
                "http://www.w3.org/2001/XMLSchema#float",
            ):
                try:
                    return float(v) != 0
                except ValueError:
                    return False
            return len(v) > 0
        return True
    return bool(val)


def _to_string(val):
    """Convert a value to a string."""
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, Term):
        if val.type == IRI:
            return val.iri
        elif val.type == LITERAL:
            return val.value
        elif val.type == BLANK:
            return val.id
    return str(val)


def _to_numeric(val):
    """Convert a value to a number."""
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
    if isinstance(val, str):
        try:
            if "." in val:
                return float(val)
            return int(val)
        except (ValueError, TypeError):
            return None
    return None


def _comparable_value(val):
    """
    Convert a value to a form suitable for comparison.
    Returns a tuple (type, value) for consistent ordering.
    """
    if val is None:
        return (0, "")
    if isinstance(val, bool):
        return (1, val)
    if isinstance(val, (int, float)):
        return (2, val)
    if isinstance(val, str):
        return (3, val)
    if isinstance(val, Term):
        if val.type == IRI:
            return (4, val.iri)
        elif val.type == LITERAL:
            # Try numeric comparison for numeric types
            num = _to_numeric(val)
            if num is not None:
                return (2, num)
            return (3, val.value)
        elif val.type == BLANK:
            return (5, val.id)
    return (6, str(val))
