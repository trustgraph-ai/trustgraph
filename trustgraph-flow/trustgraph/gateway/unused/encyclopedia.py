
from .. schema import LookupRequest, LookupResponse
from .. schema import encyclopedia_lookup_request_queue
from .. schema import encyclopedia_lookup_response_queue

from . endpoint import ServiceEndpoint
from . requestor import ServiceRequestor

class EncyclopediaRequestor(ServiceRequestor):
    def __init__(self, pulsar_client, timeout, auth):

        super(EncyclopediaRequestor, self).__init__(
            pulsar_client=pulsar_client,
            request_queue=encyclopedia_lookup_request_queue,
            response_queue=encyclopedia_lookup_response_queue,
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
        return { "text": message.text }, True

