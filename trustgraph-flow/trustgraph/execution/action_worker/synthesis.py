
import logging

from . common import (
    HandlerError, get_param, get_input_artifact, format_tabular,
    parse_param_json,
)

logger = logging.getLogger(__name__)


class LlmSynthesisHandler:

    async def execute(self, params, input_artifacts, flow):

        system = get_param(params, "system", required=False) or (
            "You are an analyst. Synthesise a clear, structured report "
            "from the provided data and context."
        )

        prompt_parts = []

        data_artifact = get_input_artifact(
            input_artifacts, "TabularArtifact",
        )
        if data_artifact:
            prompt_parts.append(
                "Data:\n" + format_tabular(data_artifact)
            )

        context_artifact = get_input_artifact(
            input_artifacts, "TextBlobArtifact",
        )
        if context_artifact:
            prompt_parts.append(
                "Context:\n" + context_artifact.get("text", "")
            )

        goal = get_param(params, "goal", required=False)
        if goal:
            prompt_parts.append(f"Goal: {goal}")

        prompt = get_param(params, "prompt", required=False)
        if prompt:
            prompt_parts.append(prompt)

        if not prompt_parts:
            raise HandlerError(
                "LLM synthesis requires at least one input artifact "
                "or a prompt parameter"
            )

        full_prompt = "\n\n".join(prompt_parts)

        response_format = get_param(
            params, "response-format", required=False,
        ) or None
        response_schema = parse_param_json(params, "schema", dict)

        logger.info(f"LLM synthesis: {len(full_prompt)} chars input")

        completion = flow("text-completion-request")

        result = await completion.text_completion(
            system=system,
            prompt=full_prompt,
            response_format=response_format,
            schema=response_schema,
            timeout=600,
        )

        return "ReportArtifact", {
            "format": "markdown",
            "narrative": result.text or "",
        }
