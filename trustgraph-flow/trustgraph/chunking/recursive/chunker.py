
"""
Simple decoder, accepts text documents on input, outputs chunks from the
as text as separate output objects.
"""

import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter
from prometheus_client import Histogram

from ... schema import TextDocument, Chunk
from ... base import ChunkingService, ConsumerSpec, ProducerSpec

# Module logger
logger = logging.getLogger(__name__)

default_ident = "chunker"

class Processor(ChunkingService):

    def __init__(self, **params):

        id = params.get("id", default_ident)
        chunk_size = params.get("chunk_size", 2000)
        chunk_overlap = params.get("chunk_overlap", 100)
        
        super(Processor, self).__init__(
            **params | { "id": id }
        )

        # Store default values for parameter override
        self.default_chunk_size = chunk_size
        self.default_chunk_overlap = chunk_overlap

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

        self.register_specification(
            ConsumerSpec(
                name = "input",
                schema = TextDocument,
                handler = self.on_message,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "output",
                schema = Chunk,
            )
        )

        logger.info("Recursive chunker initialized")

    async def on_message(self, msg, consumer, flow):

        v = msg.value()
        logger.info(f"Chunking document {v.metadata.id}...")

        # Extract chunk parameters from flow (allows runtime override)
        chunk_size, chunk_overlap = await self.chunk_document(
            msg, consumer, flow,
            self.default_chunk_size,
            self.default_chunk_overlap
        )

        # Convert to int if they're strings (flow parameters are always strings)
        if isinstance(chunk_size, str):
            chunk_size = int(chunk_size)
        if isinstance(chunk_overlap, str):
            chunk_overlap = int(chunk_overlap)

        # Create text splitter with effective parameters
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )

        texts = text_splitter.create_documents(
            [v.text.decode("utf-8")]
        )

        for ix, chunk in enumerate(texts):

            logger.debug(f"Created chunk of size {len(chunk.page_content)}")

            r = Chunk(
                metadata=v.metadata,
                chunk=chunk.page_content.encode("utf-8"),
            )

            __class__.chunk_metric.labels(
                id=consumer.id, flow=consumer.flow
            ).observe(len(chunk.page_content))

            await flow("output").send(r)

        logger.debug("Document chunking complete")

    @staticmethod
    def add_args(parser):

        ChunkingService.add_args(parser)

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

