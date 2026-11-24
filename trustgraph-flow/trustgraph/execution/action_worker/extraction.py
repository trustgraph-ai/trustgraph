
import logging

from . common import ActionHandler, HandlerError, schema_term_to_dict

logger = logging.getLogger(__name__)


class ExtractionHandler(ActionHandler):

    inputs = {
        "text": {"artifact-type": "TextBlobArtifact", "optional": True},
        "document-id": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
    }
    outputs = {
        "extraction": {"artifact-type": "ExtractionArtifact"},
    }

    def __init__(self, flow_name):
        self.flow_name = flow_name

    async def execute(self, inputs, flow):

        text = inputs["text"]["text"] if "text" in inputs else ""
        document_id = (
            inputs["document-id"]["text"]
            if "document-id" in inputs else ""
        )

        if not text and not document_id:
            raise HandlerError(
                "Either 'text' or 'document-id' must be provided"
            )

        logger.info(
            f"Extraction via {self.flow_name}: "
            f"{len(text)} chars, doc={document_id}"
        )

        extractor = flow(self.flow_name)

        try:
            result = await extractor.extract(
                text=text,
                document_id=document_id,
                timeout=300,
            )
        except TimeoutError:
            raise HandlerError(
                f"Extraction via {self.flow_name} timed out: "
                f"is the extraction service running?"
            )
        except Exception as e:
            raise HandlerError(
                f"Extraction failed: {e}"
            ) from e

        def encode_triple(t):
            return {
                "s": schema_term_to_dict(t.s),
                "p": schema_term_to_dict(t.p),
                "o": schema_term_to_dict(t.o),
            }

        def encode_entity_context(ec):
            d = {
                "entity": schema_term_to_dict(ec.entity),
                "context": ec.context,
            }
            if ec.chunk_id:
                d["chunk_id"] = ec.chunk_id
            return d

        return {
            "extraction": {
                "triples": [
                    encode_triple(t) for t in result.triples
                ],
                "entity_contexts": [
                    encode_entity_context(ec)
                    for ec in result.entity_contexts
                ],
                "provenance_triples": [
                    encode_triple(t)
                    for t in result.provenance_triples
                ],
            }
        }
