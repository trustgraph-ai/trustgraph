
from pulsar.schema import Record, String, Boolean, Array, Integer

class Error(Record):
    type = String()
    message = String()

class Value(Record):
    value = String()
    is_uri = Boolean()
    type = String()

class Triple(Record):
    s = Value()
    p = Value()
    o = Value()

class Field(Record):
    name = String()
    # int, string, long, bool, float, double, timestamp
    type = String()
    size = Integer()
    primary = Boolean()
    description = String()
    # NEW FIELDS for structured data:
    required = Boolean()  # Whether field is required
    enum_values = Array(String())  # For enum type fields
    indexed = Boolean()  # Whether field should be indexed

class RowSchema(Record):
    name = String()
    description = String()
    fields = Array(Field())

