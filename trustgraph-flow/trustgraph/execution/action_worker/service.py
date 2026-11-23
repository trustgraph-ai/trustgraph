"""
Action worker service.  Single service that dispatches step execution
to capability handlers.  Built-in handlers wrap existing TrustGraph
services including MCP tool delegation and remote action services.
"""

import json
import logging

from ... schema import ActionRequest, ActionResponse, Error
from ... base import (
    ActionService,
    RemoteActionClient,
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
    ChunkerClientSpec,
    ExtractionClientSpec,
    ToolClientSpec,
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
                optional=Exception,
            )
        )

        self.register_specification(
            KnowledgeRetrievalClientSpec(
                request_name="knowledge-retrieval-request",
                response_name="knowledge-retrieval-response",
                optional=Exception,
            )
        )

        self.register_specification(
            GraphRagClientSpec(
                request_name="graph-rag-request",
                response_name="graph-rag-response",
                optional=Exception,
            )
        )

        self.register_specification(
            EmbeddingsClientSpec(
                request_name="embeddings-request",
                response_name="embeddings-response",
                optional=Exception,
            )
        )

        self.register_specification(
            GraphEmbeddingsClientSpec(
                request_name="graph-embeddings-request",
                response_name="graph-embeddings-response",
                optional=Exception,
            )
        )

        self.register_specification(
            TriplesClientSpec(
                request_name="triples-request",
                response_name="triples-response",
                optional=Exception,
            )
        )

        self.register_specification(
            RerankerClientSpec(
                request_name="reranker-request",
                response_name="reranker-response",
                optional=Exception,
            )
        )

        self.register_specification(
            TextCompletionClientSpec(
                request_name="text-completion-request",
                response_name="text-completion-response",
                optional=Exception,
            )
        )

        self.register_specification(
            DocumentRagClientSpec(
                request_name="document-rag-request",
                response_name="document-rag-response",
                optional=Exception,
            )
        )

        self.register_specification(
            SparqlClientSpec(
                request_name="sparql-request",
                response_name="sparql-response",
                optional=Exception,
            )
        )

        self.register_specification(
            ClozeClientSpec(
                request_name="cloze-request",
                response_name="cloze-response",
                optional=Exception,
            )
        )

        self.register_specification(
            DecisionScoringClientSpec(
                request_name="decision-scoring-request",
                response_name="decision-scoring-response",
                optional=Exception,
            )
        )

        self.register_specification(
            FieldExtractionClientSpec(
                request_name="field-extraction-request",
                response_name="field-extraction-response",
                optional=Exception,
            )
        )

        self.register_specification(
            DocumentDecoderClientSpec(
                request_name="document-decode-request",
                response_name="document-decode-response",
                optional=Exception,
            )
        )

        self.register_specification(
            ChunkerClientSpec(
                request_name="chunker-request",
                response_name="chunker-response",
                optional=Exception,
            )
        )

        self.register_specification(
            ExtractionClientSpec(
                request_name="extract-definitions-request",
                response_name="extract-definitions-response",
                optional=Exception,
            )
        )

        self.register_specification(
            ExtractionClientSpec(
                request_name="extract-relationships-request",
                response_name="extract-relationships-response",
                optional=Exception,
            )
        )

        self.register_specification(
            ExtractionClientSpec(
                request_name="extract-ontology-request",
                response_name="extract-ontology-response",
                optional=Exception,
            )
        )

        self.register_specification(
            ToolClientSpec(
                request_name="mcp-tool-request",
                response_name="mcp-tool-response",
                optional=Exception,
            )
        )

        self.handlers = dict(BUILTIN_HANDLERS)

        self.remote_actions = {}

        self.register_config_handler(
            self.on_remote_action_config,
            types=["remote-action"],
        )

    async def on_remote_action_config(self, workspace, config, version):

        logger.info(
            f"Loading remote action config for workspace {workspace} "
            f"(version {version})"
        )

        old_clients = self.remote_actions.get(workspace, {})
        for client in old_clients.values():
            await client.close()

        remote_config = config.get("remote-action", {})
        clients = {}

        for capability, raw in remote_config.items():
            try:
                desc = json.loads(raw)
                request_topic = desc["request-topic"]
                response_topic = desc["response-topic"]

                clients[capability] = RemoteActionClient(
                    backend=self.async_backend,
                    request_topic=request_topic,
                    response_topic=response_topic,
                )

                logger.info(
                    f"Registered remote action '{capability}' "
                    f"({request_topic})"
                )
            except Exception as e:
                logger.error(
                    f"Failed to configure remote action "
                    f"'{capability}': {e}"
                )

        self.remote_actions[workspace] = clients

        logger.info(
            f"Action worker has {len(clients)} remote actions "
            f"for workspace {workspace}"
        )

    async def execute(self, workspace, request, flow):

        capability = request.capability

        remote = self.remote_actions.get(workspace, {}).get(capability)
        if remote:
            return await self._execute_remote(request, remote)

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

    async def _execute_remote(self, request, client):

        logger.info(
            f"Executing remote action {request.capability} for "
            f"run {request.run_id} step {request.step_id}"
        )

        try:
            artifact_type, artifact = await client.call(
                run_id=request.run_id,
                step_id=request.step_id,
                capability=request.capability,
                params=request.params,
                input_artifacts=request.input_artifacts,
                user_context=request.user_context,
            )
        except Exception as e:
            raise HandlerError(
                f"Remote action {request.capability} failed: {e}"
            ) from e

        logger.info(
            f"Remote action {request.capability} produced "
            f"{artifact_type} for step {request.step_id}"
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
