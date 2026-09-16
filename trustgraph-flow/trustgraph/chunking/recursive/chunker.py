
"""
Simple decoder, accepts text documents on input, outputs chunks from the
as text as separate output objects.
"""

import logging
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
                'tg_chunk_size', 'Chunk size',
                ["processor"],
                buckets=[100, 160, 250, 400, 650, 1000, 1600,
                         2500, 4000, 6400, 10000, 16000]
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

    SEPARATORS = ["\n\n", "\n", " ", ""]

    def _recursive_split(self, text, chunk_size, chunk_overlap):
        return self._split_text(text, self.SEPARATORS, chunk_size, chunk_overlap)

    def _split_text(self, text, separators, chunk_size, chunk_overlap):
        final_chunks = []
        separator = separators[-1]
        new_separators = []

        for i, sep in enumerate(separators):
            if sep == "":
                separator = sep
                break
            if sep in text:
                separator = sep
                new_separators = separators[i + 1:]
                break

        splits = list(text) if separator == "" else text.split(separator)

        good_splits = []
        for s in splits:
            if len(s) < chunk_size:
                good_splits.append(s)
            else:
                if good_splits:
                    final_chunks.extend(
                        self._merge_splits(good_splits, separator, chunk_size, chunk_overlap)
                    )
                    good_splits = []
                if not new_separators:
                    final_chunks.append(s)
                else:
                    final_chunks.extend(
                        self._split_text(s, new_separators, chunk_size, chunk_overlap)
                    )

        if good_splits:
            final_chunks.extend(
                self._merge_splits(good_splits, separator, chunk_size, chunk_overlap)
            )

        return [c for c in final_chunks if c.strip()]

    @staticmethod
    def _merge_splits(splits, separator, chunk_size, chunk_overlap):
        chunks = []
        current = []
        total = 0

        for s in splits:
            s_len = len(s)
            sep_len = len(separator) if current else 0

            if total + s_len + sep_len > chunk_size and current:
                chunks.append(separator.join(current))
                while total > chunk_overlap and len(current) > 1:
                    dropped = current.pop(0)
                    total -= len(dropped) + len(separator)
                if total > chunk_overlap:
                    current = []
                    total = 0

            current.append(s)
            total += s_len + (len(separator) if len(current) > 1 else 0)

        if current:
            chunk = separator.join(current)
            if chunk.strip():
                chunks.append(chunk)

        return chunks

    async def on_message(self, msg, consumer, flow):

        v = msg.value()
        logger.info(f"Chunking document {v.metadata.id}...")

        # Get text content (fetches from librarian if needed)
        text = await self.get_document_text(v, flow)

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

        chunks = self._recursive_split(text, chunk_size, chunk_overlap)

        # Get parent document ID for provenance linking
        # This could be a page URI (doc/p3) or document URI (doc) - we don't need to parse it
        parent_doc_id = v.document_id or v.metadata.id

        # Track character offset for provenance
        char_offset = 0

        for ix, chunk_text in enumerate(chunks):
            chunk_index = ix + 1  # 1-indexed

            logger.debug(f"Created chunk of size {len(chunk_text)}")

            # Generate unique chunk ID
            c_uri = make_chunk_uri()
            chunk_doc_id = c_uri
            parent_uri = parent_doc_id

            chunk_content = chunk_text.encode("utf-8")
            chunk_length = len(chunk_text)

            # Save chunk to librarian as child document
            await flow.librarian.save_child_document(
                doc_id=chunk_doc_id,
                parent_id=parent_doc_id,
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
                    collection=v.metadata.collection,
                ),
                triples=set_graph(prov_triples, GRAPH_SOURCE),
            ))

            # Forward chunk ID + content (post-chunker optimization)
            r = Chunk(
                metadata=Metadata(
                    id=c_uri,
                    root=v.metadata.root,
                    collection=v.metadata.collection,
                ),
                chunk=chunk_content,
                document_id=chunk_doc_id,
            )

            __class__.chunk_metric.labels(
                processor=self.id,
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
