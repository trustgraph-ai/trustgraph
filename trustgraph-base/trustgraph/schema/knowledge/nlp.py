from dataclasses import dataclass


############################################################################

# NLP extraction data types

@dataclass
class Definition:
    name: str = ""
    definition: str = ""

@dataclass
class Topic:
    name: str = ""
    definition: str = ""

@dataclass
class Relationship:
    s: str = ""
    p: str = ""
    o: str = ""
    o_entity: bool = False

@dataclass
class Fact:
    s: str = ""
    p: str = ""
    o: str = ""
