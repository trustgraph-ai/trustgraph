
import base64

from ... schema import TextDocument, Metadata
from .... base.messaging import TranslatorRegistry

from . sender import ServiceSender

class TextLoad(ServiceSender):
    def __init__(self, pulsar_client, queue):

        super(TextLoad, self).__init__(
            pulsar_client = pulsar_client,
            queue = queue,
            schema = TextDocument,
        )

        self.translator = TranslatorRegistry.get_request_translator("text-document")

    def to_request(self, body):
        print("Text document received")
        return self.translator.to_pulsar(body)

