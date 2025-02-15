
from .. schema import LibrarianRequest, LibrarianResponse, Triples
from .. schema import librarian_request_queue
from .. schema import librarian_response_queue

from . endpoint import ServiceEndpoint
from . requestor import ServiceRequestor
from . serialize import serialize_document_package, serialize_document_info
from . serialize import to_document_package, to_document_info, to_criteria

class LibrarianRequestor(ServiceRequestor):
    def __init__(self, pulsar_client, timeout, auth):

        super(LibrarianRequestor, self).__init__(
            pulsar_client=pulsar_client,
            request_queue=librarian_request_queue,
            response_queue=librarian_response_queue,
            request_schema=LibrarianRequest,
            response_schema=LibrarianResponse,
            timeout=timeout,
        )

    def to_request(self, body):

        print("TRR")
        if "document" in body:
            dp = to_document_package(body["document"])
        else:
            dp = None

        print("GOT")
        if "criteria" in body:
            criteria = to_criteria(body["criteria"])
        else:
            criteria = None

        print("ASLDKJ")

        return LibrarianRequest(
            operation = body.get("operation", None),
            id = body.get("id", None),
            document = dp,
            user = body.get("user", None),
            collection = body.get("collection", None),
            criteria = criteria,
        )

    def from_response(self, message):

        response = {}

        if message.document:
            response["document"] = serialize_document_package(message.document)

        if message.info:
            response["info"] = [
                serialize_document_info(v)
                for v in message.info
            ]
        
        return response, True

