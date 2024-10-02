
from pulsar.schema import Record, String

class Metadata(Record):
    source = String()
    id = String()
    title = String()
    user = String()
    collection = String()

