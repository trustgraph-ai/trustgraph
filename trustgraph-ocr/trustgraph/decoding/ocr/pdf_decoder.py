
"""
Simple decoder, accepts PDF documents on input, outputs pages from the
PDF document as text as separate output objects.
"""

import tempfile
import base64
import pytesseract
from pdf2image import convert_from_bytes

from ... schema import Document, TextDocument, Metadata
from ... base import FlowProcessor, ConsumerSpec, ProducerSpec

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

        print("PDF OCR inited")

    async def on_message(self, msg, consumer, flow):

        print("PDF message received", flush=True)

        v = msg.value()

        print(f"Decoding {v.metadata.id}...", flush=True)

        blob = base64.b64decode(v.data)

        pages = convert_from_bytes(blob)

        for ix, page in enumerate(pages):

            try:
                text = pytesseract.image_to_string(page, lang='eng')
            except Exception as e:
                print(f"Page did not OCR: {e}")
                continue

            r = TextDocument(
                metadata=v.metadata,
                text=text.encode("utf-8"),
            )

            await flow("output").send(r)

        print("Done.", flush=True)

    @staticmethod
    def add_args(parser):
        FlowProcessor.add_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

