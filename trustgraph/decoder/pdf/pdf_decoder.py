
"""
Simple decoder, accepts PDF documents on input, outputs pages from the
PDF document as text as separate output objects.
"""

from langchain_community.document_loaders import PyPDFLoader

from ... schema import Document, TextDocument, Source
from ... log_level import LogLevel
from ... base import ConsumerProducer

default_input_queue = 'document-load'
default_output_queue = 'text-doc-load'
default_subscriber = 'pdf-decoder'

class Processor(ConsumerProducer):

    def __init__(
            self,
            pulsar_host=None,
            input_queue=default_input_queue,
            output_queue=default_output_queue,
            subscriber=default_subscriber,
            log_level=LogLevel.INFO,
    ):

        super(Processor, self).__init__(
            pulsar_host=pulsar_host,
            log_level=log_level,
            input_queue=input_queue,
            output_queue=output_queue,
            subscriber=subscriber,
            input_schema=Document,
            output_schema=TextDocument,
        )

        print("PDF inited")

    def handle(self, msg):

        print("PDF message received")

        v = msg.value()

        print(f"Decoding {v.source.id}...", flush=True)

        with tempfile.NamedTemporaryFile(delete_on_close=False) as fp:

            fp.write(base64.b64decode(v.data))
            fp.close()

            with open(fp.name, mode='rb') as f:

                loader = PyPDFLoader(fp.name)
                pages = loader.load()

                for ix, page in enumerate(pages):

                    id = v.source.id + "-p" + str(ix)
                    r = TextDocument(
                        source=Source(
                            source=v.source.source,
                            title=v.source.title,
                            id=id,
                        ),
                        text=page.page_content.encode("utf-8"),
                    )

                    self.send(r)

        print("Done.", flush=True)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

def run():

    Processor.start("pdf-decoder", __doc__)

