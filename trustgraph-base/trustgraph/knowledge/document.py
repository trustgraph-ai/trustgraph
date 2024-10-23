
from . defs import *

class DigitalDocument:
    def __init__(
            self, id, name=None, description=None, copyright_notice=None,
            copyright_holder=None, copyright_year=None, license=None,
            identifier=None,
            publication=None, url=None, keywords=[]
    ):
        self.id = id
        self.name = name
        self.description = description
        self.copyright_notice = copyright_notice
        self.copyright_holder = copyright_holder
        self.copyright_year = copyright_year
        self.license = license
        self.publication = publication
        self.url = url
        self.identifier = identifier
        self.keywords = keywords

    def emit(self, emit):

        emit(Triple(Value(self.id), Value(IS_A), Value(DIGITAL_DOCUMENT)))

        if self.name:
            emit(Triple(Value(self.id), Value(LABEL), Value(self.name)))
            emit(Triple(Value(self.id), Value(NAME), Value(self.name)))

        if self.identifier:
            emit(Triple(Value(id), Value(IDENTIFIER), Value(self.identifier)))

        if self.description:
            emit(Triple(
                Value(self.id), Value(DESCRIPTION), Value(self.description)
            ))

        if self.copyright_notice:
            emit(Triple(
                Value(self.id), Value(COPYRIGHT_NOTICE),
                Value(self.copyright_notice)
            ))

        if self.copyright_holder:
            emit(Triple(
                Value(self.id), Value(COPYRIGHT_HOLDER),
                Value(self.copyright_holder)
            ))

        if self.copyright_year:
            emit(Triple(
                Value(self.id), Value(COPYRIGHT_YEAR),
                Value(self.copyright_year)
            ))

        if self.license:
            emit(Triple(
                Value(self.id), Value(LICENSE), Value(self.license)
            ))

        if self.keywords:
            for k in self.keywords:
                emit(Triple(Value(self.id), Value(KEYWORD), Value(k)))

        if self.publication:
            emit(Triple(
                Value(self.id), Value(PUBLICATION, Value(self.publication.id))
            ))
            self.publication.emit(emit)

        if self.url:
            emit(Triple(Value(self.id), Value(URL), Value(self.url)))
