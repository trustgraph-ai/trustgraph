
import logging

from . common import ActionHandler, HandlerError

logger = logging.getLogger(__name__)


class DocumentDecodeHandler(ActionHandler):

    inputs = {
        "document-id": {"artifact-type": "TextBlobArtifact"},
        "mode": {"artifact-type": "TextBlobArtifact", "optional": True},
    }
    outputs = {
        "sections": {"artifact-type": "DocumentSectionsArtifact"},
    }

    async def execute(self, inputs, flow):

        document_id = inputs["document-id"]["text"]
        mode = inputs["mode"]["text"] if "mode" in inputs else "page"

        logger.info(
            f"Document decode: {document_id} (mode={mode})"
        )

        decoder = flow("document-decode-request")

        try:
            sections = await decoder.decode(
                document_id=document_id,
                mode=mode,
                timeout=600,
            )
        except Exception as e:
            raise HandlerError(
                f"Document decode failed: {e}"
            ) from e

        return {
            "sections": {
                "document_id": document_id,
                "sections": [
                    {
                        "document_id": s.document_id,
                        "page": s.page,
                        "section_type": s.section_type,
                    }
                    for s in sections
                ],
            }
        }
