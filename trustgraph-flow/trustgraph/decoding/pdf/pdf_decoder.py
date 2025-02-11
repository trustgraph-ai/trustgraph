
"""
Simple decoder, accepts PDF documents on input, outputs pages from the
PDF document as text as separate output objects.
"""

import tempfile
import base64
from langchain_community.document_loaders import PyPDFLoader

from ... schema import Document, TextDocument, Metadata
from ... schema import document_ingest_queue, text_ingest_queue
from ... log_level import LogLevel
from ... base import ConsumerProducer

module = ".".join(__name__.split(".")[1:-1])

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

        print("PDF inited")

    async def handle(self, msg):

        print("PDF message received")

        v = msg.value()

        print(f"Decoding {v.metadata.id}...", flush=True)

        with tempfile.NamedTemporaryFile(delete_on_close=False) as fp:

            fp.write(base64.b64decode(v.data))
            fp.close()

            with open(fp.name, mode='rb') as f:

                loader = PyPDFLoader(fp.name)
                pages = loader.load()

                for ix, page in enumerate(pages):

                    r = TextDocument(
                        metadata=v.metadata,
                        text=page.page_content.encode("utf-8"),
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

