
from . defs import *

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

        emit(Triple(Value(self.id), Value(IS_A), Value(PUBLICATION_EVENT)))

        if self.name:
            emit(Triple(Value(self.id), Value(LABEL), Value(self.name)))
            emit(Triple(Value(self.id), Value(NAME), Value(self.name)))

        if self.description:
            emit(Triple(
                Value(self.id), Value(DESCRIPTION), Value(self.description)
            ))

        if self.organization:
            emit(Triple(
                Value(self.id), Value(PUBLISHED_BY),
                Value(self.organization.id)
            ))
            self.organization.emit(emit)

        if self.start_date:
            emit(Triple(
                Value(self.id), Value(START_DATE), Value(self.start_date)
            ))

        if self.end_date:
            emit(Triple(Value(self.id), Value(END_DATE), Value(self.end_date)))

