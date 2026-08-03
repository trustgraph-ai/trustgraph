from ... schema import PassthroughRequest, PassthroughResponse

from . requestor import ServiceRequestor


class PassthroughRequestor(ServiceRequestor):
    def __init__(
            self, backend, request_queue, response_queue, timeout,
            consumer, subscriber,
    ):

        super(PassthroughRequestor, self).__init__(
            backend=backend,
            request_queue=request_queue,
            response_queue=response_queue,
            request_schema=PassthroughRequest,
            response_schema=PassthroughResponse,
            subscription=subscriber,
            consumer_name=consumer,
            timeout=timeout,
        )

    def to_request(self, body):
        return PassthroughRequest(payload=body)

    def from_response(self, message):
        return message.payload, message.is_final
