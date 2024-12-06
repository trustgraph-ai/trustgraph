
from ... schema import LookupRequest, LookupResponse
from ... schema import internet_search_request_queue
from ... schema import internet_search_response_queue

from . endpoint import ServiceEndpoint

class InternetSearchEndpoint(ServiceEndpoint):
    def __init__(self, pulsar_host, timeout, auth):

        super(InternetSearchEndpoint, self).__init__(
            pulsar_host=pulsar_host,
            request_queue=internet_search_request_queue,
            response_queue=internet_search_response_queue,
            request_schema=LookupRequest,
            response_schema=LookupResponse,
            endpoint_path="/api/v1/internet-search",
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

