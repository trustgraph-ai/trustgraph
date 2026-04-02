"""
SPARQL parser wrapping rdflib's SPARQL 1.1 parser and algebra compiler.
Parses a SPARQL query string into an algebra tree for evaluation.
"""

import logging

from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.algebra import translateQuery
from rdflib.plugins.sparql.parserutils import CompValue
from rdflib.term import Variable, URIRef, Literal, BNode

from ... schema import Term, Triple, IRI, LITERAL, BLANK

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """Raised when a SPARQL query cannot be parsed."""
    pass


class ParsedQuery:
    """Result of parsing a SPARQL query string."""

    def __init__(self, algebra, query_type, variables=None):
        self.algebra = algebra
        self.query_type = query_type        # "select", "ask", "construct", "describe"
        self.variables = variables or []    # projected variable names (SELECT)


def rdflib_term_to_term(t):
    """Convert an rdflib term (URIRef, Literal, BNode) to a schema Term."""
    if isinstance(t, URIRef):
        return Term(type=IRI, iri=str(t))
    elif isinstance(t, Literal):
        term = Term(type=LITERAL, value=str(t))
        if t.datatype:
            term.datatype = str(t.datatype)
        if t.language:
            term.language = t.language
        return term
    elif isinstance(t, BNode):
        return Term(type=BLANK, id=str(t))
    else:
        return Term(type=LITERAL, value=str(t))


def term_to_rdflib(t):
    """Convert a schema Term to an rdflib term."""
    if t.type == IRI:
        return URIRef(t.iri)
    elif t.type == LITERAL:
        kwargs = {}
        if t.datatype:
            kwargs["datatype"] = URIRef(t.datatype)
        if t.language:
            kwargs["lang"] = t.language
        return Literal(t.value, **kwargs)
    elif t.type == BLANK:
        return BNode(t.id)
    else:
        return Literal(t.value)


def parse_sparql(query_string):
    """
    Parse a SPARQL query string into a ParsedQuery.

    Args:
        query_string: SPARQL 1.1 query string

    Returns:
        ParsedQuery with algebra tree, query type, and projected variables

    Raises:
        ParseError: if the query cannot be parsed
    """
    try:
        prepared = prepareQuery(query_string)
    except Exception as e:
        raise ParseError(f"SPARQL parse error: {e}") from e

    algebra = prepared.algebra

    # Determine query type and extract variables
    query_type = _detect_query_type(algebra)
    variables = _extract_variables(algebra, query_type)

    return ParsedQuery(
        algebra=algebra,
        query_type=query_type,
        variables=variables,
    )


def _detect_query_type(algebra):
    """Detect the SPARQL query type from the algebra root."""
    name = algebra.name

    if name == "SelectQuery":
        return "select"
    elif name == "AskQuery":
        return "ask"
    elif name == "ConstructQuery":
        return "construct"
    elif name == "DescribeQuery":
        return "describe"

    # The top-level algebra node may be a modifier (Project, Slice, etc.)
    # wrapping the actual query. Check for common patterns.
    if name in ("Project", "Distinct", "Reduced", "OrderBy", "Slice"):
        return "select"

    logger.warning(f"Unknown algebra root type: {name}, assuming select")
    return "select"


def _extract_variables(algebra, query_type):
    """Extract projected variable names from the algebra."""
    if query_type != "select":
        return []

    # For SELECT queries, the Project node has PV (projected variables)
    if hasattr(algebra, "PV"):
        return [str(v) for v in algebra.PV]

    # Walk down through modifiers to find Project
    node = algebra
    while hasattr(node, "p"):
        node = node.p
        if hasattr(node, "PV"):
            return [str(v) for v in node.PV]

    # Fallback: collect all variables from the algebra
    if hasattr(algebra, "_vars"):
        return [str(v) for v in algebra._vars]

    return []
