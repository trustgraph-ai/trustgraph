
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
    # int, string, long, bool, float, double
    type = String()
    size = Integer()
    primary = Boolean()
    description = String()

class RowSchema(Record):
    name = String()
    description = String()
    fields = Array(Field())

