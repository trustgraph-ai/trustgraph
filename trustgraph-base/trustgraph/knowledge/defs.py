
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

class Triple:
    def __init__(self, s, p, o):
        self.s, self.p, self.o = s, p, o

class Uri(str):
    def is_uri(self): return True
    def is_literal(self): return False

class Literal(str):
    def is_uri(self): return False
    def is_literal(self): return True

