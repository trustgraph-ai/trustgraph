
import logging

from . common import HandlerError, get_param, get_param_int

logger = logging.getLogger(__name__)


class ChunkHandler:

    async def execute(self, params, input_artifacts, flow):

        document_id = get_param(params, "document-id")
        chunk_size = get_param_int(params, "chunk-size", 0)
        chunk_overlap = get_param_int(params, "chunk-overlap", 0)

        logger.info(
            f"Chunk: {document_id} "
            f"(size={chunk_size}, overlap={chunk_overlap})"
        )

        chunker = flow("chunker-request")

        try:
            chunks = await chunker.chunk(
                document_id=document_id,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                timeout=300,
            )
        except Exception as e:
            raise HandlerError(
                f"Chunking failed: {e}"
            ) from e

        return "ChunksArtifact", {
            "document_id": document_id,
            "chunks": [
                {
                    "document_id": c.document_id,
                    "index": c.index,
                    "char_offset": c.char_offset,
                    "char_length": c.char_length,
                }
                for c in chunks
            ],
        }
