
"""
Simple decoder, accepts text documents on input, outputs chunks from the
as text as separate output objects.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from prometheus_client import Histogram

from ... schema import TextDocument, Chunk, Metadata
from ... schema import text_ingest_queue, chunk_ingest_queue
from ... log_level import LogLevel
from ... base import FlowProcessor

default_ident = "chunker"

class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id", default_ident)
        chunk_size = params.get("chunk_size", 2000)
        chunk_overlap = params.get("chunk_overlap", 100)
        
        super(Processor, self).__init__(
            **params | { "id": id }
        )

        if not hasattr(__class__, "chunk_metric"):
            __class__.chunk_metric = Histogram(
                'chunk_size', 'Chunk size',
                ["id", "flow"],
                buckets=[100, 160, 250, 400, 650, 1000, 1600,
                         2500, 4000, 6400, 10000, 16000]
            )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )

        self.register_consumer(
            name = "input",
            schema = TextDocument,
            handler = self.on_message,
        )

        self.register_producer(
            name = "output",
            schema = Chunk,
        )

        print("Chunker initialised", flush=True)

    async def on_message(self, msg, consumer, flow):

        v = msg.value()
        print(f"Chunking {v.metadata.id}...", flush=True)

        texts = self.text_splitter.create_documents(
            [v.text.decode("utf-8")]
        )

        for ix, chunk in enumerate(texts):

            print("Chunk", len(chunk.page_content), flush=True)

            r = Chunk(
                metadata=v.metadata,
                chunk=chunk.page_content.encode("utf-8"),
            )

            __class__.chunk_metric.labels(
                id=consumer.id, flow=consumer.flow
            ).observe(len(chunk.page_content))

            await flow.producer["output"].send(r)

        print("Done.", flush=True)

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

        parser.add_argument(
            '-z', '--chunk-size',
            type=int,
            default=2000,
            help=f'Chunk size (default: 2000)'
        )

        parser.add_argument(
            '-v', '--chunk-overlap',
            type=int,
            default=100,
            help=f'Chunk overlap (default: 100)'
        )

def run():

    Processor.launch(default_ident, __doc__)

