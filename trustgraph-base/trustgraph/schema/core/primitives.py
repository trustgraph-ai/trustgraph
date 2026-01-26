from __future__ import annotations

from dataclasses import dataclass, field

# Term type constants
IRI = "i"      # IRI/URI node
BLANK = "b"    # Blank node
LITERAL = "l"  # Literal value
TRIPLE = "t"   # Quoted triple (RDF-star)


@dataclass
class Error:
    type: str = ""
    message: str = ""


@dataclass
class Term:
    """
    RDF Term - can represent an IRI, blank node, literal, or quoted triple.

    The 'type' field determines which other fields are relevant:
    - IRI: use 'iri' field
    - BLANK: use 'id' field
    - LITERAL: use 'value', 'datatype', 'language' fields
    - TRIPLE: use 'triple' field
    """
    type: str = ""  # One of: IRI, BLANK, LITERAL, TRIPLE

    # For IRI terms (type == IRI)
    iri: str = ""

    # For blank nodes (type == BLANK)
    id: str = ""

    # For literals (type == LITERAL)
    value: str = ""
    datatype: str = ""   # XSD datatype URI (mutually exclusive with language)
    language: str = ""   # Language tag (mutually exclusive with datatype)

    # For quoted triples (type == TRIPLE)
    triple: Triple | None = None


@dataclass
class Triple:
    """
    RDF Triple / Quad.

    The optional 'g' field specifies the named graph (None = default graph).
    """
    s: Term | None = None    # Subject
    p: Term | None = None    # Predicate
    o: Term | None = None    # Object
    g: str | None = None     # Graph name (IRI), None = default graph

@dataclass
class Field:
    name: str = ""
    # int, string, long, bool, float, double, timestamp
    type: str = ""
    size: int = 0
    primary: bool = False
    description: str = ""
    # NEW FIELDS for structured data:
    required: bool = False  # Whether field is required
    enum_values: list[str] = field(default_factory=list)  # For enum type fields
    indexed: bool = False  # Whether field should be indexed

@dataclass
class RowSchema:
    name: str = ""
    description: str = ""
    fields: list[Field] = field(default_factory=list)

