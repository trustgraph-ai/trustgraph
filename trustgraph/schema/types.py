
from pulsar.schema import Record, String, Boolean

class Error(Record):
    type = String()
    message = String()

class Value(Record):
    value = String()
    is_uri = Boolean()
    type = String()


