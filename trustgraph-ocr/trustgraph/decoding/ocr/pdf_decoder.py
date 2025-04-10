
"""
Simple decoder, accepts PDF documents on input, outputs pages from the
PDF document as text as separate output objects.
"""

import tempfile
import base64
import pytesseract
from pdf2image import convert_from_bytes

from ... schema import Document, TextDocument, Metadata
from ... schema import document_ingest_queue, text_ingest_queue
from ... log_level import LogLevel
from ... base import ConsumerProducer

module = "ocr"

default_input_queue = document_ingest_queue
default_output_queue = text_ingest_queue
default_subscriber = module

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": Document,
                "output_schema": TextDocument,
            }
        )

        print("PDF OCR inited")

    async def handle(self, msg):

        print("PDF message received")

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

            await self.send(r)

        print("Done.", flush=True)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

def run():

    Processor.launch(module, __doc__)

