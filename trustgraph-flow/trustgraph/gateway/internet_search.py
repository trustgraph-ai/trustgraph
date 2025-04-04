
from .. schema import LookupRequest, LookupResponse
from .. schema import internet_search_request_queue
from .. schema import internet_search_response_queue

from . endpoint import ServiceEndpoint
from . requestor import ServiceRequestor

class InternetSearchRequestor(ServiceRequestor):
    def __init__(self, pulsar_client, timeout, auth):

        super(InternetSearchRequestor, self).__init__(
            pulsar_client=pulsar_client,
            request_queue=internet_search_request_queue,
            response_queue=internet_search_response_queue,
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

