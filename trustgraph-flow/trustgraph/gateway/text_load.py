
import base64

from .. schema import TextDocument, Metadata
from .. schema import text_ingest_queue

from . sender import ServiceSender
from . serialize import to_subgraph

class TextLoadSender(ServiceSender):
    def __init__(self, pulsar_host, pulsar_api_key=None):

        super(TextLoadSender, self).__init__(
            pulsar_host=pulsar_host,
            pulsar_api_key=pulsar_api_key,
            request_queue=text_ingest_queue,
            request_schema=TextDocument,
        )

    def to_request(self, body):

        if "metadata" in body:
            metadata = to_subgraph(body["metadata"])
        else:
            metadata = []

        if "charset" in body:
            charset = body["charset"]
        else:
            charset = "utf-8"

        # Text is base64 encoded
        text = base64.b64decode(body["text"]).decode(charset)

        print("Text document received")

        return TextDocument(
            metadata=Metadata(
                id=body.get("id"),
                metadata=metadata,
                user=body.get("user", "trustgraph"),
                collection=body.get("collection", "default"),
            ),
            text=text,
        )

