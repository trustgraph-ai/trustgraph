
"""
MCP tool-calling service, calls an external MCP tool.  Input is
name + parameters, output is the response, either a string or an object.
"""

import json
import logging
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.shared._httpx_utils import create_mcp_http_client

from ... base import ToolService

try:
    from mcp.client.streamable_http import streamable_http_client
    _MCP_USES_CALLER_HTTP_CLIENT = True
except ImportError:
    from mcp.client.streamable_http import (
        streamablehttp_client as streamable_http_client,
    )
    _MCP_USES_CALLER_HTTP_CLIENT = False

# Module logger
logger = logging.getLogger(__name__)

default_ident = "mcp-tool"


@asynccontextmanager
async def connect_streamable_http(url, headers):
    """Yield the read/write streams across MCP's two HTTP client APIs."""
    if _MCP_USES_CALLER_HTTP_CLIENT:
        async with create_mcp_http_client(headers=headers) as http_client:
            async with streamable_http_client(
                url,
                http_client=http_client,
            ) as streams:
                yield streams[:2]
    else:
        async with streamable_http_client(
            url,
            headers=headers,
        ) as streams:
            yield streams[:2]


class Service(ToolService):

    def __init__(self, **params):

        super(Service, self).__init__(
            **params
        )

        self.register_config_handler(self.on_mcp_config, types=["mcp"])

        # Per-workspace MCP service registries
        self.mcp_services = {}

    async def on_mcp_config(self, workspace, config, version):

        logger.info(
            f"Got config version {version} for workspace {workspace}"
        )

        if "mcp" not in config:
            self.mcp_services[workspace] = {}
            return

        self.mcp_services[workspace] = {
            k: json.loads(v)
            for k, v in config["mcp"].items()
        }

    async def invoke_tool(self, workspace, name, parameters):

        try:

            ws_services = self.mcp_services.get(workspace, {})

            if name not in ws_services:
                raise RuntimeError(
                    f"MCP service {name} not known in workspace "
                    f"{workspace}"
                )

            if "url" not in ws_services[name]:
                raise RuntimeError(f"MCP service {name} URL not defined")

            url = ws_services[name]["url"]

            if "remote-name" in ws_services[name]:
                remote_name = ws_services[name]["remote-name"]
            else:
                remote_name = name

            # Build headers with optional bearer token
            headers = {}
            token = ws_services[name].get("auth-token")
            if token:
                headers["Authorization"] = f"Bearer {token}"

            logger.info(f"Invoking {remote_name} at {url}")

            async with connect_streamable_http(
                url,
                headers,
            ) as (read_stream, write_stream):

                # Create a session using the client streams
                async with ClientSession(
                    read_stream,
                    write_stream,
                ) as session:

                    # Initialize the connection
                    await session.initialize()

                    # Call a tool
                    result = await session.call_tool(
                        remote_name,
                        parameters
                    )

                    structured_content = getattr(
                        result,
                        "structured_content",
                        None,
                    )
                    if structured_content is None:
                        structured_content = getattr(
                            result,
                            "structuredContent",
                            None,
                        )

                    if structured_content:
                        return structured_content
                    elif hasattr(result, "content"):
                        return "".join([
                            x.text
                            for x in result.content
                        ])
                    else:
                        return "No content"

        except BaseExceptionGroup as e:

            for child in e.exceptions:
                logger.debug(f"Child: {child}")

            raise e.exceptions[0]

        except Exception as e:

            logger.error(f"Error invoking MCP tool: {e}", exc_info=True)
            raise e
            
    @staticmethod
    def add_args(parser):

        ToolService.add_args(parser)

def run():
    Service.launch(default_ident, __doc__)

