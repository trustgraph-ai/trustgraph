
import logging

from . common import ActionHandler, HandlerError, format_tabular

logger = logging.getLogger(__name__)


class LlmSynthesisHandler(ActionHandler):

    inputs = {
        "data": {
            "artifact-type": "TabularArtifact",
            "optional": True,
        },
        "context": {
            "artifact-type": "TextBlobArtifact",
            "optional": True,
        },
        "goal": {
            "artifact-type": "TextBlobArtifact",
            "optional": True,
        },
        "prompt": {
            "artifact-type": "TextBlobArtifact",
            "optional": True,
        },
        "system": {
            "artifact-type": "TextBlobArtifact",
            "optional": True,
        },
        "response-format": {
            "artifact-type": "TextBlobArtifact",
            "optional": True,
        },
    }
    outputs = {
        "report": {"artifact-type": "ReportArtifact"},
    }

    async def execute(self, inputs, flow):

        if "system" in inputs:
            system = inputs["system"].get("text", "")
        else:
            system = (
                "You are an analyst. Synthesise a clear, structured "
                "report from the provided data and context."
            )

        prompt_parts = []

        if "data" in inputs:
            prompt_parts.append(
                "Data:\n" + format_tabular(inputs["data"])
            )

        if "context" in inputs:
            prompt_parts.append(
                "Context:\n" + inputs["context"].get("text", "")
            )

        if "goal" in inputs:
            prompt_parts.append(
                f"Goal: {inputs['goal'].get('text', '')}"
            )

        if "prompt" in inputs:
            prompt_parts.append(inputs["prompt"].get("text", ""))

        if not prompt_parts:
            raise HandlerError(
                "LLM synthesis requires at least one of: "
                "data, context, goal, or prompt"
            )

        full_prompt = "\n\n".join(prompt_parts)

        response_format = None
        if "response-format" in inputs:
            response_format = inputs["response-format"].get("text")

        logger.info(f"LLM synthesis: {len(full_prompt)} chars input")

        completion = flow("text-completion-request")

        result = await completion.text_completion(
            system=system,
            prompt=full_prompt,
            response_format=response_format,
            timeout=600,
        )

        return {
            "report": {
                "format": "markdown",
                "narrative": result.text or "",
            }
        }
