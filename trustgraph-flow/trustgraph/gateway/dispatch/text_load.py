
import base64
import logging

from ... schema import TextDocument, Metadata
from ... messaging import TranslatorRegistry

from . sender import ServiceSender

# Module logger
logger = logging.getLogger(__name__)

class TextLoad(ServiceSender):
    def __init__(self, backend, queue):

        super(TextLoad, self).__init__(
            backend = backend,
            queue = queue,
            schema = TextDocument,
        )

        self.translator = TranslatorRegistry.get_request_translator("text-document")

    def to_request(self, body):
        logger.info("Text document received")
        return self.translator.to_pulsar(body)

