
import base64

from .. schema import Document, Metadata
from .. schema import document_ingest_queue

from . sender import ServiceSender
from . serialize import to_subgraph

class DocumentLoadSender(ServiceSender):
    def __init__(self, pulsar_host):

        super(DocumentLoadSender, self).__init__(
            pulsar_host=pulsar_host,
            request_queue=document_ingest_queue,
            request_schema=Document,
        )

    def to_request(self, body):

        if "metadata" in body:
            metadata = to_subgraph(body["metadata"])
        else:
            metadata = []

        # Doing a base64 decoe/encode here to make sure the
        # content is valid base64
        doc = base64.b64decode(body["data"])

        print("Document received")

        return Document(
            metadata=Metadata(
                id=body.get("id"),
                metadata=metadata,
                user=body.get("user", "trustgraph"),
                collection=body.get("collection", "default"),
            ),
            data=base64.b64encode(doc).decode("utf-8")
        )

