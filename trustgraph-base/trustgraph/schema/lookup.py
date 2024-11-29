
from pulsar.schema import Record, String

from . types import Error, Value, Triple
from . topic import topic
from . metadata import Metadata

############################################################################

# Lookups

class LookupRequest(Record):
    kind = String()
    term = String()

class LookupResponse(Record):
    text = String()
    error = Error()

encyclopedia_lookup_request_queue = topic(
    'encyclopedia', kind='non-persistent', namespace='request'
)
encyclopedia_lookup_response_queue = topic(
    'encyclopedia', kind='non-persistent', namespace='response', 
)

dbpedia_lookup_request_queue = topic(
    'dbpedia', kind='non-persistent', namespace='request'
)
dbpedia_lookup_response_queue = topic(
    'dbpedia', kind='non-persistent', namespace='response', 
)

internet_search_request_queue = topic(
    'internet-search', kind='non-persistent', namespace='request'
)
internet_search_response_queue = topic(
    'internet-search', kind='non-persistent', namespace='response', 
)

############################################################################

