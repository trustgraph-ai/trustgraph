
import logging

from . common import HandlerError, get_param, schema_term_to_dict

logger = logging.getLogger(__name__)


class ExtractionHandler:

    def __init__(self, flow_name):
        self.flow_name = flow_name

    async def execute(self, params, input_artifacts, flow):

        text = get_param(params, "text", required=False) or ""
        document_id = get_param(params, "document-id", required=False) or ""

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

        return "ExtractionArtifact", {
            "triples": [encode_triple(t) for t in result.triples],
            "entity_contexts": [
                encode_entity_context(ec)
                for ec in result.entity_contexts
            ],
            "provenance_triples": [
                encode_triple(t) for t in result.provenance_triples
            ],
        }
