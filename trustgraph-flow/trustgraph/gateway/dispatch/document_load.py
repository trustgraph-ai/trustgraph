
import base64

from ... schema import Document, Metadata
from .... base.messaging import TranslatorRegistry

from . sender import ServiceSender

class DocumentLoad(ServiceSender):
    def __init__(self, pulsar_client, queue):

        super(DocumentLoad, self).__init__(
            pulsar_client = pulsar_client,
            queue = queue,
            schema = Document,
        )

        self.translator = TranslatorRegistry.get_request_translator("document")

    def to_request(self, body):
        print("Document received")
        return self.translator.to_pulsar(body)

