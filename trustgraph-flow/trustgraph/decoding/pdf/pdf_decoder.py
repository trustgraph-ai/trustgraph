
"""
Simple decoder, accepts PDF documents on input, outputs pages from the
PDF document as text as separate output objects.
"""

import tempfile
import base64
from langchain_community.document_loaders import PyPDFLoader

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

        print("PDF inited", flush=True)

    async def on_message(self, msg, consumer, flow):

        print("PDF message received", flush=True)

        v = msg.value()

        print(f"Decoding {v.metadata.id}...", flush=True)

        with tempfile.NamedTemporaryFile(delete_on_close=False) as fp:

            fp.write(base64.b64decode(v.data))
            fp.close()

            with open(fp.name, mode='rb') as f:

                loader = PyPDFLoader(fp.name)
                pages = loader.load()

                for ix, page in enumerate(pages):

                    print("page", ix, flush=True)

                    r = TextDocument(
                        metadata=v.metadata,
                        text=page.page_content.encode("utf-8"),
                    )

                    await flow("output").send(r)

        print("Done.", flush=True)

    @staticmethod
    def add_args(parser):
        FlowProcessor.add_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

