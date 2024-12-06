
from .. schema import LookupRequest, LookupResponse
from .. schema import dbpedia_lookup_request_queue
from .. schema import dbpedia_lookup_response_queue

from . endpoint import ServiceEndpoint
from . requestor import ServiceRequestor

class DbpediaRequestor(ServiceRequestor):
    def __init__(self, pulsar_host, timeout, auth):

        super(DbpediaRequestor, self).__init__(
            pulsar_host=pulsar_host,
            request_queue=dbpedia_lookup_request_queue,
            response_queue=dbpedia_lookup_response_queue,
            request_schema=LookupRequest,
            response_schema=LookupResponse,
            timeout=timeout,
        )

    def to_request(self, body):
        return LookupRequest(
            term=body["term"],
            kind=body.get("kind", None),
        )

    def from_response(self, message):
        return { "text": message.text }

class DbpediaEndpoint(ServiceEndpoint):
    def __init__(self, pulsar_host, timeout, auth):

        super(DbpediaEndpoint, self).__init__(
            endpoint_path="/api/v1/dbpedia",
            auth=auth,
            requestor = DbpediaRequestor(
                pulsar_host=pulsar_host, timeout=timeout, auth=auth
            )
        )

