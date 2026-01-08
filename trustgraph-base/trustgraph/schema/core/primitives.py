
from dataclasses import dataclass, field

@dataclass
class Error:
    type: str = ""
    message: str = ""

@dataclass
class Value:
    value: str = ""
    is_uri: bool = False
    type: str = ""

@dataclass
class Triple:
    s: Value | None = None
    p: Value | None = None
    o: Value | None = None

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

