
import base64

from ... schema import LibrarianRequest, LibrarianResponse
from ... schema import librarian_request_queue
from ... schema import librarian_response_queue

from . requestor import ServiceRequestor
from . serialize import serialize_document_metadata
from . serialize import serialize_processing_metadata
from . serialize import to_document_metadata, to_processing_metadata
from . serialize import to_criteria

class LibrarianRequestor(ServiceRequestor):
    def __init__(self, pulsar_client, consumer, subscriber, timeout=120):

        super(LibrarianRequestor, self).__init__(
            pulsar_client=pulsar_client,
            consumer_name = consumer,
            subscription = subscriber,
            request_queue=librarian_request_queue,
            response_queue=librarian_response_queue,
            request_schema=LibrarianRequest,
            response_schema=LibrarianResponse,
            timeout=timeout,
        )

    def to_request(self, body):

        # Content gets base64 decoded & encoded again.  It at least makes
        # sure payload is valid base64.

        if "document-metadata" in body:
            dm = to_document_metadata(body["document-metadata"])
        else:
            dm = None

        if "processing-metadata" in body:
            pm = to_processing_metadata(body["processing-metadata"])
        else:
            pm = None

        if "criteria" in body:
            criteria = to_criteria(body["criteria"])
        else:
            criteria = None

        if "content" in body:
            content = base64.b64decode(body["content"].encode("utf-8"))
            content = base64.b64encode(content).decode("utf-8")
        else:
            content = None

        return LibrarianRequest(
            operation = body.get("operation", None),
            document_id = body.get("document-id", None),
            processing_id = body.get("processing-id", None),
            document_metadata = dm,
            processing_metadata = pm,
            content = content,
            user = body.get("user", None),
            collection = body.get("collection", None),
            criteria = criteria,
        )

    def from_response(self, message):

        print(message)

        response = {}

        if message.document_metadata:
            response["document-metadata"] = serialize_document_metadata(
                message.document_metadata
            )

        if message.content:
            response["content"] = message.content

        if message.document_metadatas != None:
            response["document-metadatas"] = [
                serialize_document_metadata(v)
                for v in message.document_metadatas
            ]

        if message.processing_metadatas != None:
            response["processing-metadatas"] = [
                serialize_processing_metadata(v)
                for v in message.processing_metadatas
            ]
        
        return response, True

