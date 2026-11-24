
import json
import logging

from . common import ActionHandler, HandlerError

logger = logging.getLogger(__name__)


class McpToolHandler(ActionHandler):

    inputs = {
        "tool-name": {"artifact-type": "TextBlobArtifact"},
        "parameters": {
            "artifact-type": "TextBlobArtifact", "optional": True,
        },
    }
    outputs = {
        "result": {
            "artifact-type": [
                "TextBlobArtifact", "CompositeArtifact",
            ],
        },
    }

    async def execute(self, inputs, flow):

        tool_name = inputs["tool-name"]["text"]
        parameters = {}
        if "parameters" in inputs:
            parameters = json.loads(inputs["parameters"]["text"])

        logger.info(f"MCP tool invocation: {tool_name}")

        client = flow("mcp-tool-request")

        try:
            result = await client.invoke(
                name=tool_name, parameters=parameters, timeout=300,
            )
        except TimeoutError:
            raise HandlerError(
                f"MCP tool '{tool_name}' timed out: "
                f"is the MCP tool service running?"
            )
        except Exception as e:
            raise HandlerError(
                f"MCP tool '{tool_name}' failed: {e}"
            ) from e

        if isinstance(result, str):
            return {
                "result": {
                    "artifact-type": "TextBlobArtifact",
                    "artifact": {"text": result},
                }
            }

        return {
            "result": {
                "artifact-type": "CompositeArtifact",
                "artifact": result,
            }
        }
