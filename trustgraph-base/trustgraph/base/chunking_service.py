"""
Base chunking service that provides parameter specification functionality
for chunk-size and chunk-overlap parameters, and librarian client for
fetching large document content.

Supports both flow mode (on_message) and request/response mode
(on_chunk_request) for on-demand chunking via the gateway.
"""

import asyncio
import logging

from .flow_processor import FlowProcessor
from .parameter_spec import ParameterSpec
from .librarian_spec import LibrarianSpec
from .consumer_spec import ConsumerSpec
from .producer_spec import ProducerSpec

from .. schema import ChunkerRequest, ChunkerResponse, Error

from .. provenance import chunk_uri as make_chunk_uri

logger = logging.getLogger(__name__)


class ChunkingService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id", "chunker")

        super(ChunkingService, self).__init__(**params)

        self.register_specification(
            ParameterSpec(name="chunk-size")
        )

        self.register_specification(
            ParameterSpec(name="chunk-overlap")
        )

        self.register_specification(
            LibrarianSpec()
        )

        self.register_specification(
            ConsumerSpec(
                name="request",
                schema=ChunkerRequest,
                handler=self.on_chunk_request,
            )
        )

        self.register_specification(
            ProducerSpec(
                name="response",
                schema=ChunkerResponse,
            )
        )

    def split_text(self, text, chunk_size, chunk_overlap):
        raise NotImplementedError

    async def get_document_text(self, doc, flow):
        if doc.document_id and not doc.text:
            logger.info(f"Fetching document {doc.document_id} from librarian...")
            text = await flow.librarian.fetch_document_text(
                document_id=doc.document_id,
            )
            logger.info(f"Fetched {len(text)} characters from librarian")
            return text
        else:
            return doc.text.decode("utf-8")

    async def chunk_document(self, msg, consumer, flow, default_chunk_size, default_chunk_overlap):

        chunk_size = default_chunk_size
        chunk_overlap = default_chunk_overlap

        try:
            cs = flow("chunk-size")
            if cs is not None:
                chunk_size = int(cs)
        except Exception as e:
            logger.warning(f"Could not parse chunk-size parameter: {e}")

        try:
            co = flow("chunk-overlap")
            if co is not None:
                chunk_overlap = int(co)
        except Exception as e:
            logger.warning(f"Could not parse chunk-overlap parameter: {e}")

        return chunk_size, chunk_overlap

    async def on_chunk_request(self, msg, consumer, flow):

        id = msg.properties()["id"]

        try:

            v = msg.value()
            document_id = v.document_id
            chunk_size = v.chunk_size or self.default_chunk_size
            chunk_overlap = v.chunk_overlap or self.default_chunk_overlap

            logger.info(
                f"Chunk request {id}: document={document_id} "
                f"size={chunk_size} overlap={chunk_overlap}"
            )

            text = await flow.librarian.fetch_document_text(
                document_id=document_id,
            )

            logger.info(
                f"Chunk request {id}: fetched {len(text)} characters"
            )

            loop = asyncio.get_event_loop()
            chunks = await loop.run_in_executor(
                None,
                lambda: self.split_text(text, chunk_size, chunk_overlap),
            )

            char_offset = 0

            for ix, chunk_text in enumerate(chunks):
                chunk_index = ix + 1

                if not chunk_text or not chunk_text.strip():
                    continue

                c_uri = make_chunk_uri()
                chunk_content = chunk_text.encode("utf-8")
                chunk_length = len(chunk_text)

                await flow.librarian.save_child_document(
                    doc_id=c_uri,
                    parent_id=document_id,
                    content=chunk_content,
                    document_type="chunk",
                    title=f"Chunk {chunk_index}",
                )

                await flow("response").send(
                    ChunkerResponse(
                        document_id=c_uri,
                        index=chunk_index,
                        char_offset=char_offset,
                        char_length=chunk_length,
                    ),
                    properties={"id": id},
                )

                char_offset += chunk_length

            await flow("response").send(
                ChunkerResponse(end_of_stream=True),
                properties={"id": id},
            )

            logger.info(f"Chunk request {id}: complete")

        except Exception as e:

            logger.error(
                f"Chunk request {id} failed: {type(e).__name__}: {e}",
                exc_info=True,
            )

            await flow("response").send(
                ChunkerResponse(
                    error=Error(
                        type="chunker-error",
                        message=str(e),
                    ),
                    end_of_stream=True,
                ),
                properties={"id": id},
            )
