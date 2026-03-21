
"""
Simple decoder, accepts text documents on input, outputs chunks from the
as text as separate output objects.
"""

import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter
from prometheus_client import Histogram

from ... schema import TextDocument, Chunk, Metadata, Triples
from ... base import ChunkingService, ConsumerSpec, ProducerSpec

from ... provenance import (
    chunk_uri as make_chunk_uri, derived_entity_triples,
    set_graph, GRAPH_SOURCE,
)

# Component identification for provenance
COMPONENT_NAME = "chunker"
COMPONENT_VERSION = "1.0.0"

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

        self.register_specification(
            ProducerSpec(
                name = "triples",
                schema = Triples,
            )
        )

        logger.info("Recursive chunker initialized")

    async def on_message(self, msg, consumer, flow):

        v = msg.value()
        logger.info(f"Chunking document {v.metadata.id}...")

        # Get text content (fetches from librarian if needed)
        text = await self.get_document_text(v)

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

        texts = text_splitter.create_documents([text])

        # Get parent document ID for provenance linking
        # This could be a page URI (doc/p3) or document URI (doc) - we don't need to parse it
        parent_doc_id = v.document_id or v.metadata.id

        # Track character offset for provenance
        char_offset = 0

        for ix, chunk in enumerate(texts):
            chunk_index = ix + 1  # 1-indexed

            logger.debug(f"Created chunk of size {len(chunk.page_content)}")

            # Generate unique chunk ID
            c_uri = make_chunk_uri()
            chunk_doc_id = c_uri
            parent_uri = parent_doc_id

            chunk_content = chunk.page_content.encode("utf-8")
            chunk_length = len(chunk.page_content)

            # Save chunk to librarian as child document
            await self.save_child_document(
                doc_id=chunk_doc_id,
                parent_id=parent_doc_id,
                user=v.metadata.user,
                content=chunk_content,
                document_type="chunk",
                title=f"Chunk {chunk_index}",
            )

            # Emit provenance triples (stored in source graph for separation from core knowledge)
            prov_triples = derived_entity_triples(
                entity_uri=c_uri,
                parent_uri=parent_uri,
                component_name=COMPONENT_NAME,
                component_version=COMPONENT_VERSION,
                label=f"Chunk {chunk_index}",
                chunk_index=chunk_index,
                char_offset=char_offset,
                char_length=chunk_length,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

            await flow("triples").send(Triples(
                metadata=Metadata(
                    id=c_uri,
                    root=v.metadata.root,
                    user=v.metadata.user,
                    collection=v.metadata.collection,
                ),
                triples=set_graph(prov_triples, GRAPH_SOURCE),
            ))

            # Forward chunk ID + content (post-chunker optimization)
            r = Chunk(
                metadata=Metadata(
                    id=c_uri,
                    root=v.metadata.root,
                    user=v.metadata.user,
                    collection=v.metadata.collection,
                ),
                chunk=chunk_content,
                document_id=chunk_doc_id,
            )

            __class__.chunk_metric.labels(
                id=consumer.id, flow=consumer.flow
            ).observe(chunk_length)

            await flow("output").send(r)

            # Update character offset (approximate, doesn't account for overlap)
            char_offset += chunk_length - chunk_overlap

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
