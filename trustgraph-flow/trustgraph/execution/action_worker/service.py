"""
Action worker service.  Single service that dispatches step execution
to capability handlers.  Built-in handlers wrap existing TrustGraph
services.  Future: MCP tool and tool service delegation.
"""

import logging

from ... schema import ActionRequest, ActionResponse, Error
from ... base import (
    ActionService,
    GraphRagClientSpec,
    TextCompletionClientSpec,
    PromptClientSpec,
)

from . handlers import BUILTIN_HANDLERS, HandlerError

logger = logging.getLogger(__name__)

default_ident = "action"


class Processor(ActionService):

    def __init__(self, **params):

        super(Processor, self).__init__(**params)

        self.register_specification(
            GraphRagClientSpec(
                request_name="graph-rag-request",
                response_name="graph-rag-response",
            )
        )

        self.register_specification(
            TextCompletionClientSpec(
                request_name="text-completion-request",
                response_name="text-completion-response",
            )
        )

        self.register_specification(
            PromptClientSpec(
                request_name="prompt-request",
                response_name="prompt-response",
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
