from pulsar.schema import Record, String, Boolean

from ..core.topic import topic

############################################################################

# NLP extraction data types

class Definition(Record):
    name = String()
    definition = String()

class Topic(Record):
    name = String()
    definition = String()

class Relationship(Record):
    s = String()
    p = String()
    o = String()
    o_entity = Boolean()

class Fact(Record):
    s = String()
    p = String()
    o = String()