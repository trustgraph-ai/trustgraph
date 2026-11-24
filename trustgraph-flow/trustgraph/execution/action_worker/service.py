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
    QueryFormulationClientSpec,
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

        self.register_specification(
            QueryFormulationClientSpec(
                request_name="query-formulation-request",
                response_name="query-formulation-response",
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
        params = json.loads(request.params) if request.params else {}

        remote = self.remote_actions.get(workspace, {}).get(capability)
        if remote:
            return await self._execute_remote(request, params, remote)

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

            artifacts = await self._execute_typed(
                handler, params, flow,
            )

        except HandlerError:
            raise
        except Exception as e:
            raise HandlerError(
                f"Handler {capability} failed: {e}"
            ) from e

        logger.info(
            f"Capability {capability} produced "
            f"{list(artifacts.keys())} for step {request.step_id}"
        )

        return ActionResponse(
            run_id=request.run_id,
            step_id=request.step_id,
            artifacts=json.dumps(artifacts),
        )

    def _check_artifact_type(self, name, actual, expected):
        if isinstance(expected, list):
            if actual not in expected:
                raise HandlerError(
                    f"Input '{name}': expected one of "
                    f"{expected}, got {actual}"
                )
        else:
            if actual != expected:
                raise HandlerError(
                    f"Input '{name}': expected {expected}, "
                    f"got {actual}"
                )

    async def _execute_typed(self, handler, params, flow):

        inputs = {}
        for name, decl in handler.inputs.items():
            entry = params.get(name)
            if entry is None:
                if decl.get("optional"):
                    continue
                raise HandlerError(
                    f"Missing input '{name}'"
                )
            expected = decl["artifact-type"]
            actual = entry.get("artifact-type", "")
            self._check_artifact_type(name, actual, expected)
            inputs[name] = entry["artifact"]

        result = await handler.execute(inputs, flow)

        artifacts = {}
        for name, decl in handler.outputs.items():
            data = result.get(name)
            if data is None:
                raise HandlerError(
                    f"Handler did not produce output '{name}'"
                )
            expected = decl["artifact-type"]
            if isinstance(expected, list):
                if not isinstance(data, dict) or "artifact-type" not in data:
                    raise HandlerError(
                        f"Output '{name}': polymorphic output must "
                        f"include artifact-type"
                    )
                self._check_artifact_type(name, data["artifact-type"], expected)
                artifacts[name] = data
            else:
                artifacts[name] = {
                    "artifact-type": expected,
                    "artifact": data,
                }

        return artifacts

    async def _execute_remote(self, request, params, client):

        logger.info(
            f"Executing remote action {request.capability} for "
            f"run {request.run_id} step {request.step_id}"
        )

        try:
            artifacts = await client.call(
                run_id=request.run_id,
                step_id=request.step_id,
                capability=request.capability,
                params=params,
                user_context=request.user_context,
            )
        except Exception as e:
            raise HandlerError(
                f"Remote action {request.capability} failed: {e}"
            ) from e

        logger.info(
            f"Remote action {request.capability} produced "
            f"{list(artifacts.keys())} for step {request.step_id}"
        )

        return ActionResponse(
            run_id=request.run_id,
            step_id=request.step_id,
            artifacts=json.dumps(artifacts),
        )

    @staticmethod
    def add_args(parser):
        ActionService.add_args(parser)


def run():
    Processor.launch(default_ident, __doc__)
