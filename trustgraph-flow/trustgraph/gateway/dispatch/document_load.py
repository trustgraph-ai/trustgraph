
import base64
import logging

from ... schema import Document, Metadata
from ... messaging import TranslatorRegistry

from . sender import ServiceSender

# Module logger
logger = logging.getLogger(__name__)

class DocumentLoad(ServiceSender):
    def __init__(self, backend, queue):

        super(DocumentLoad, self).__init__(
            backend = backend,
            queue = queue,
            schema = Document,
        )

        self.translator = TranslatorRegistry.get_request_translator("document")

    def to_request(self, body):
        logger.info("Document received")
        return self.translator.to_pulsar(body)

