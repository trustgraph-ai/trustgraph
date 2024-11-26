
from . defs import *

def Value(value, is_uri):
    if is_uri:
        return Uri(value)
    else:
        return Literal(value)

def Triple(s, p, o):
    return {
        "s": s, "p": p, "o": o,
    }

class PublicationEvent:
    def __init__(
            self, id, organization=None, name=None, description=None,
            start_date=None, end_date=None,
    ):
        self.id = id
        self.organization = organization
        self.name = name
        self.description = description
        self.start_date = start_date
        self.end_date = end_date

    def emit(self, emit):

        emit(Triple(
            s=Value(value=self.id, is_uri=True),
            p=Value(value=IS_A, is_uri=True),
            o=Value(value=PUBLICATION_EVENT, is_uri=True)))

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

        if self.organization:

            emit(Triple(
                s=Value(value=self.id, is_uri=True),
                p=Value(value=PUBLISHED_BY, is_uri=True),
                o=Value(value=self.organization.id, is_uri=True)
            ))

            self.organization.emit(emit)

        if self.start_date:

            emit(Triple(
                s=Value(value=self.id, is_uri=True),
                p=Value(value=START_DATE, is_uri=True),
                o=Value(value=self.start_date, is_uri=False)
            ))

        if self.end_date:

            emit(Triple(
                s=Value(value=self.id, is_uri=True),
                p=Value(value=END_DATE, is_uri=True),
                o=Value(value=self.end_date, is_uri=False)))
