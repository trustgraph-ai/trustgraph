
from ... schema import LookupRequest, LookupResponse
from ... schema import encyclopedia_lookup_request_queue
from ... schema import encyclopedia_lookup_response_queue

from . endpoint import ServiceEndpoint

class EncyclopediaEndpoint(ServiceEndpoint):
    def __init__(self, pulsar_host, timeout):

        super(EncyclopediaEndpoint, self).__init__(
            pulsar_host=pulsar_host,
            request_queue=encyclopedia_lookup_request_queue,
            response_queue=encyclopedia_lookup_response_queue,
            request_schema=LookupRequest,
            response_schema=LookupResponse,
            endpoint_path="/api/v1/encyclopedia",
            timeout=timeout,
        )

    def to_request(self, body):
        return LookupRequest(
            term=body["term"],
            kind=body.get("kind", None),
        )

    def from_response(self, message):
        return { "text": message.text }

