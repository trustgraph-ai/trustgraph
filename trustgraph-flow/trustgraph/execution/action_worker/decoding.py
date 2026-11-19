
import logging

from . common import HandlerError, get_param

logger = logging.getLogger(__name__)


class DocumentDecodeHandler:

    async def execute(self, params, input_artifacts, flow):

        document_id = get_param(params, "document-id")
        mode = get_param(params, "mode", required=False) or "page"

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

        return "DocumentSectionsArtifact", {
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
