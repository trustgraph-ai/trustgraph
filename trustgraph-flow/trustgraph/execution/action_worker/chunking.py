
import logging

from . common import ActionHandler, HandlerError

logger = logging.getLogger(__name__)


class ChunkHandler(ActionHandler):

    inputs = {
        "document-id": {"artifact-type": "TextBlobArtifact"},
        "chunk-size": {"artifact-type": "TextBlobArtifact", "optional": True},
        "chunk-overlap": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
    }
    outputs = {
        "chunks": {"artifact-type": "ChunksArtifact"},
    }

    async def execute(self, inputs, flow):

        document_id = inputs["document-id"]["text"]
        chunk_size = (
            int(inputs["chunk-size"]["text"])
            if "chunk-size" in inputs else 0
        )
        chunk_overlap = (
            int(inputs["chunk-overlap"]["text"])
            if "chunk-overlap" in inputs else 0
        )

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

        return {
            "chunks": {
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
        }
