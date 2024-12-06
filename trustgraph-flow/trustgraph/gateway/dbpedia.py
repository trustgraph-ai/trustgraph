
from .. schema import LookupRequest, LookupResponse
from .. schema import dbpedia_lookup_request_queue
from .. schema import dbpedia_lookup_response_queue

from . endpoint import ServiceEndpoint

class DbpediaEndpoint(ServiceEndpoint):
    def __init__(self, pulsar_host, timeout, auth):

        super(DbpediaEndpoint, self).__init__(
            pulsar_host=pulsar_host,
            request_queue=dbpedia_lookup_request_queue,
            response_queue=dbpedia_lookup_response_queue,
            request_schema=LookupRequest,
            response_schema=LookupResponse,
            endpoint_path="/api/v1/dbpedia",
            timeout=timeout,
            auth=auth,
        )

    def to_request(self, body):
        return LookupRequest(
            term=body["term"],
            kind=body.get("kind", None),
        )

    def from_response(self, message):
        return { "text": message.text }

