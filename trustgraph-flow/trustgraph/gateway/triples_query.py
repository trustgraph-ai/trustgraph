
from .. schema import TriplesQueryRequest, TriplesQueryResponse, Triples
from .. schema import triples_request_queue
from .. schema import triples_response_queue

from . endpoint import ServiceEndpoint
from . requestor import ServiceRequestor
from . serialize import to_value, serialize_subgraph

class TriplesQueryRequestor(ServiceRequestor):
    def __init__(self, pulsar_host, timeout, auth, pulsar_api_key=None):

        super(TriplesQueryRequestor, self).__init__(
            pulsar_host=pulsar_host,
            pulsar_api_key=pulsar_api_key,
            request_queue=triples_request_queue,
            response_queue=triples_response_queue,
            request_schema=TriplesQueryRequest,
            response_schema=TriplesQueryResponse,
            timeout=timeout,
        )

    def to_request(self, body):

        if "s" in body:
            s = to_value(body["s"])
        else:
            s = None

        if "p" in body:
            p = to_value(body["p"])
        else:
            p = None

        if "o" in body:
            o = to_value(body["o"])
        else:
            o = None

        limit = int(body.get("limit", 10000))

        return TriplesQueryRequest(
            s = s, p = p, o = o,
            limit = limit,
            user = body.get("user", "trustgraph"),
            collection = body.get("collection", "default"),
        )

    def from_response(self, message):
        print(message)
        return {
            "response": serialize_subgraph(message.triples)
        }, True

