
from .. schema import TriplesQueryRequest, TriplesQueryResponse, Triples

from . endpoint import ServiceEndpoint
from . requestor import ServiceRequestor
from . serialize import to_value, serialize_subgraph

class TriplesQueryRequestor(ServiceRequestor):
    def __init__(
            self, pulsar_client, request_queue, response_queue, timeout, auth,
            consumer, subscriber,
    ):

        super(TriplesQueryRequestor, self).__init__(
            pulsar_client=pulsar_client,
            request_queue=request_queue,
            response_queue=response_queue,
            request_schema=TriplesQueryRequest,
            response_schema=TriplesQueryResponse,
            subscription = subscriber,
            consumer_name = consumer,
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

