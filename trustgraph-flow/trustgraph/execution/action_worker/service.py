"""
Action worker service.  Single service that dispatches step execution
to capability handlers.  Built-in handlers wrap existing TrustGraph
services.  Future: MCP tool and tool service delegation.
"""

import logging

from ... schema import ActionRequest, ActionResponse, Error
from ... base import (
    ActionService,
    ConceptExtractionClientSpec,
    KnowledgeRetrievalClientSpec,
    GraphRagClientSpec,
    DocumentRagClientSpec,
    EmbeddingsClientSpec,
    GraphEmbeddingsClientSpec,
    TriplesClientSpec,
    SparqlClientSpec,
    RerankerClientSpec,
    TextCompletionClientSpec,
    ClozeClientSpec,
    DecisionScoringClientSpec,
    FieldExtractionClientSpec,
    DocumentDecoderClientSpec,
)

from . handlers import BUILTIN_HANDLERS, HandlerError

logger = logging.getLogger(__name__)

default_ident = "action"


class Processor(ActionService):

    def __init__(self, **params):

        super(Processor, self).__init__(**params)

        self.register_specification(
            ConceptExtractionClientSpec(
                request_name="concept-extraction-request",
                response_name="concept-extraction-response",
            )
        )

        self.register_specification(
            KnowledgeRetrievalClientSpec(
                request_name="knowledge-retrieval-request",
                response_name="knowledge-retrieval-response",
            )
        )

        self.register_specification(
            GraphRagClientSpec(
                request_name="graph-rag-request",
                response_name="graph-rag-response",
            )
        )

        self.register_specification(
            EmbeddingsClientSpec(
                request_name="embeddings-request",
                response_name="embeddings-response",
            )
        )

        self.register_specification(
            GraphEmbeddingsClientSpec(
                request_name="graph-embeddings-request",
                response_name="graph-embeddings-response",
            )
        )

        self.register_specification(
            TriplesClientSpec(
                request_name="triples-request",
                response_name="triples-response",
            )
        )

        self.register_specification(
            RerankerClientSpec(
                request_name="reranker-request",
                response_name="reranker-response",
            )
        )

        self.register_specification(
            TextCompletionClientSpec(
                request_name="text-completion-request",
                response_name="text-completion-response",
            )
        )

        self.register_specification(
            DocumentRagClientSpec(
                request_name="document-rag-request",
                response_name="document-rag-response",
            )
        )

        self.register_specification(
            SparqlClientSpec(
                request_name="sparql-request",
                response_name="sparql-response",
            )
        )

        self.register_specification(
            ClozeClientSpec(
                request_name="cloze-request",
                response_name="cloze-response",
            )
        )

        self.register_specification(
            DecisionScoringClientSpec(
                request_name="decision-scoring-request",
                response_name="decision-scoring-response",
            )
        )

        self.register_specification(
            FieldExtractionClientSpec(
                request_name="field-extraction-request",
                response_name="field-extraction-response",
            )
        )

        self.register_specification(
            DocumentDecoderClientSpec(
                request_name="document-decode-request",
                response_name="document-decode-response",
            )
        )

        self.handlers = dict(BUILTIN_HANDLERS)

    async def execute(self, workspace, request, flow):

        capability = request.capability

        handler = self.handlers.get(capability)
        if handler is None:
            raise HandlerError(
                f"Unknown capability: {capability}"
            )

        logger.info(
            f"Executing {capability} for "
            f"run {request.run_id} step {request.step_id}"
        )

        try:
            artifact_type, artifact = await handler.execute(
                request.params,
                request.input_artifacts,
                flow,
            )
        except HandlerError:
            raise
        except Exception as e:
            raise HandlerError(
                f"Handler {capability} failed: {e}"
            ) from e

        logger.info(
            f"Capability {capability} produced {artifact_type} "
            f"for step {request.step_id}"
        )

        return ActionResponse(
            run_id=request.run_id,
            step_id=request.step_id,
            artifact_type=artifact_type,
            artifact=artifact,
        )

    @staticmethod
    def add_args(parser):
        ActionService.add_args(parser)


def run():
    Processor.launch(default_ident, __doc__)
