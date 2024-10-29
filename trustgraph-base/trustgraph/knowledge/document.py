
from . defs import *
from .. schema import Triple, Value

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

        emit(Triple(
            s=Value(value=self.id, is_uri=True),
            p=Value(value=IS_A, is_uri=True),
            o=Value(value=DIGITAL_DOCUMENT, is_uri=True)
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

        if self.identifier:

            emit(Triple(
                s=Value(value=id, is_uri=True),
                p=Value(value=IDENTIFIER, is_uri=True),
                o=Value(value=self.identifier, is_uri=False)
            ))

        if self.description:

            emit(Triple(
                s=Value(value=self.id, is_uri=True),
                p=Value(value=DESCRIPTION, is_uri=True),
                o=Value(value=self.description, is_uri=False)
            ))

        if self.copyright_notice:

            emit(Triple(
                s=Value(value=self.id, is_uri=True),
                p=Value(value=COPYRIGHT_NOTICE, is_uri=True),
                o=Value(value=self.copyright_notice, is_uri=False)
            ))

        if self.copyright_holder:

            emit(Triple(
                s=Value(value=self.id, is_uri=True),
                p=Value(value=COPYRIGHT_HOLDER, is_uri=True),
                o=Value(value=self.copyright_holder, is_uri=False)
            ))

        if self.copyright_year:

            emit(Triple(
                s=Value(value=self.id, is_uri=True),
                p=Value(value=COPYRIGHT_YEAR, is_uri=True),
                o=Value(value=self.copyright_year, is_uri=False)
            ))

        if self.license:

            emit(Triple(
                s=Value(value=self.id, is_uri=True),
                p=Value(value=LICENSE, is_uri=True),
                o=Value(value=self.license, is_uri=False)
            ))

        if self.keywords:
            for k in self.keywords:
                emit(Triple(
                    s=Value(value=self.id, is_uri=True),
                    p=Value(value=KEYWORD, is_uri=True),
                    o=Value(value=k, is_uri=False)
                ))

        if self.publication:

            emit(Triple(
                s=Value(value=self.id, is_uri=True),
                p=Value(value=PUBLICATION, is_uri=True),
                o=Value(value=self.publication.id, is_uri=True)
            ))

            self.publication.emit(emit)

        if self.url:

            emit(Triple(
                s=Value(value=self.id, is_uri=True),
                p=Value(value=URL, is_uri=True),
                o=Value(value=self.url, is_uri=True)
            ))
