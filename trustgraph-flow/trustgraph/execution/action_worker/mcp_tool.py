
import logging

from . common import HandlerError, get_param, parse_param_json

logger = logging.getLogger(__name__)


class McpToolHandler:

    async def execute(self, params, input_artifacts, flow):

        tool_name = get_param(params, "tool-name")
        parameters = parse_param_json(
            params, "parameters", expected_type=dict,
        ) or {}

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
            return "TextBlobArtifact", {"text": result}

        return "CompositeArtifact", result
