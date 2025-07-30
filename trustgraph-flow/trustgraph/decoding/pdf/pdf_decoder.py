
"""
Simple decoder, accepts PDF documents on input, outputs pages from the
PDF document as text as separate output objects.
"""

import tempfile
import base64
import logging
from langchain_community.document_loaders import PyPDFLoader

from ... schema import Document, TextDocument, Metadata
from ... base import FlowProcessor, ConsumerSpec, ProducerSpec

# Module logger
logger = logging.getLogger(__name__)

default_ident = "pdf-decoder"

class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id", default_ident)

        super(Processor, self).__init__(
            **params | {
                "id": id,
            }
        )

        self.register_specification(
            ConsumerSpec(
                name = "input",
                schema = Document,
                handler = self.on_message,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "output",
                schema = TextDocument,
            )
        )

        logger.info("PDF decoder initialized")

    async def on_message(self, msg, consumer, flow):

        logger.debug("PDF message received")

        v = msg.value()

        logger.info(f"Decoding PDF {v.metadata.id}...")

        with tempfile.NamedTemporaryFile(delete_on_close=False) as fp:

            fp.write(base64.b64decode(v.data))
            fp.close()

            with open(fp.name, mode='rb') as f:

                loader = PyPDFLoader(fp.name)
                pages = loader.load()

                for ix, page in enumerate(pages):

                    logger.debug(f"Processing page {ix}")

                    r = TextDocument(
                        metadata=v.metadata,
                        text=page.page_content.encode("utf-8"),
                    )

                    await flow("output").send(r)

        logger.debug("PDF decoding complete")

    @staticmethod
    def add_args(parser):
        FlowProcessor.add_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

