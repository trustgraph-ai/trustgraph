
from . defs import *

def Value(value, is_uri):
    return {
        "v": value, "e": is_uri,
    }

def Triple(s, p, o):
    return {
        "s": s, "p": p, "o": o,
    }

class Organization:
    def __init__(self, id, name=None, description=None):
        self.id = id
        self.name = name
        self.description = description

    def emit(self, emit):

        emit(Triple(
            s=Value(value=self.id, is_uri=True),
            p=Value(value=IS_A, is_uri=True),
            o=Value(value=ORGANIZATION, is_uri=True)
        ))

        if self.name:

            emit(Triple(
                s=Value(value=self.id, is_uri=True),
                p=Value(value=LABEL, is_uri=True),
                o=Value(value=self.name, is_uri=False)
            ))

            emit(Triple(
                s=Value(value=self.id, is_uri=True),
                p=Value(value=NAME, is_uri=True),
                o=Value(value=self.name, is_uri=False)
            ))

        if self.description:

            emit(Triple(
                s=Value(value=self.id, is_uri=True),
                p=Value(value=DESCRIPTION, is_uri=True),
                o=Value(value=self.description, is_uri=False)
            ))

