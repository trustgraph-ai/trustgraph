
IS_A = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'
LABEL = 'http://www.w3.org/2000/01/rdf-schema#label'

DIGITAL_DOCUMENT = 'https://schema.org/DigitalDocument'
PUBLICATION_EVENT = 'https://schema.org/PublicationEvent'
ORGANIZATION = 'https://schema.org/Organization'

NAME = 'https://schema.org/name'
DESCRIPTION = 'https://schema.org/description'
COPYRIGHT_NOTICE = 'https://schema.org/copyrightNotice'
COPYRIGHT_HOLDER = 'https://schema.org/copyrightHolder'
COPYRIGHT_YEAR = 'https://schema.org/copyrightYear'
LICENSE = 'https://schema.org/license'
PUBLICATION = 'https://schema.org/publication'
START_DATE = 'https://schema.org/startDate'
END_DATE = 'https://schema.org/endDate'
PUBLISHED_BY = 'https://schema.org/publishedBy'
DATE_PUBLISHED = 'https://schema.org/datePublished'
PUBLICATION = 'https://schema.org/publication'
DATE_PUBLISHED = 'https://schema.org/datePublished'
URL = 'https://schema.org/url'
IDENTIFIER = 'https://schema.org/identifier'
KEYWORD = 'https://schema.org/keywords'

class Uri(str):
    def is_uri(self): return True
    def is_literal(self): return False
    def is_triple(self): return False

class Literal(str):
    def is_uri(self): return False
    def is_literal(self): return True
    def is_triple(self): return False

class QuotedTriple:
    """
    RDF-star quoted triple (reification).

    Represents a triple that can be used as the object of another triple,
    enabling statements about statements.

    Example:
        # subgraph:123 tg:contains <<:Hope skos:definition "A feeling...">>
        qt = QuotedTriple(
            s=Uri("https://example.org/Hope"),
            p=Uri("http://www.w3.org/2004/02/skos/core#definition"),
            o=Literal("A feeling of expectation")
        )
    """
    def __init__(self, s, p, o):
        self.s = s  # Uri, Literal, or QuotedTriple
        self.p = p  # Uri
        self.o = o  # Uri, Literal, or QuotedTriple

    def is_uri(self): return False
    def is_literal(self): return False
    def is_triple(self): return True

    def __repr__(self):
        return f"<<{self.s} {self.p} {self.o}>>"

    def __str__(self):
        return f"<<{self.s} {self.p} {self.o}>>"

