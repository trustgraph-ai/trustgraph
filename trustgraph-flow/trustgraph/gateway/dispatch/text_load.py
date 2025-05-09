
import base64

from ... schema import TextDocument, Metadata

from . sender import ServiceSender
from . serialize import to_subgraph

class TextLoad(ServiceSender):
    def __init__(self, pulsar_client, queue):

        super(TextLoad, self).__init__(
            pulsar_client = pulsar_client,
            queue = queue,
            schema = TextDocument,
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

