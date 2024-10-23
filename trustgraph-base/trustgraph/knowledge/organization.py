
from . defs import *
from .. schema import Triple, Value

class Organization:
    def __init__(self, id, name=None, description=None):
        self.id = id
        self.name = name
        self.description = description

    def emit(self, emit):

        emit(Triple(Value(self.id), Value(IS_A), Value(ORGANIZATION)))

        if self.name:
            emit(Triple(Value(self.id), Value(LABEL), Value(self.name)))
            emit(Triple(Value(self.id), Value(NAME), Value(self.name)))

        if self.description:
            emit(Triple(
                Value(self.id), Value(DESCRIPTION), Value(self.description)
            ))
