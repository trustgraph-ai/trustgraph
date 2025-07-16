
"""
MCP tool-calling service, calls an external MCP tool.  Input is
name + parameters, output is the response, either a string or an object.
"""

import json
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

from ... base import ToolService

default_ident = "mcp-tool"

class Service(ToolService):

    def __init__(self, **params):

        super(Service, self).__init__(
            **params
        )

        self.register_config_handler(self.on_mcp_config)

        self.mcp_services = {}

    async def on_mcp_config(self, config, version):

        print("Got config version", version)

        if "mcp" not in config: return

        self.mcp_services = {
            k: json.loads(v)
            for k, v in config["mcp"].items()
        }

    async def invoke_tool(self, name, parameters):

        try:

            if name not in self.mcp_services:
                raise RuntimeError(f"MCP service {name} not known")

            if "url" not in self.mcp_services[name]:
                raise RuntimeError(f"MCP service {name} URL not defined")

            url = self.mcp_services[name]["url"]

            if "remote-name" in self.mcp_services[name]:
                remote_name = self.mcp_services[name]["remote-name"]
            else:
                remote_name = name

            print("Invoking", remote_name, "at", url, flush=True)

            # Connect to a streamable HTTP server
            async with streamablehttp_client(url) as (
                    read_stream,
                    write_stream,
                    _,
            ):

                # Create a session using the client streams
                async with ClientSession(read_stream, write_stream) as session:

                    # Initialize the connection
                    await session.initialize()

                    # Call a tool
                    result = await session.call_tool(
                        remote_name,
                        parameters
                    )

                    if result.structuredContent:
                        return result.structuredContent
                    elif hasattr(result, "content"):
                            return "".join([
                                x.text
                                for x in result.content
                            ])
                    else:
                        return "No content"

        except BaseExceptionGroup as e:

            for child in e.exceptions:
                print(child)

            raise e.exceptions[0]

        except Exception as e:

            print(e)
            raise e
            
    @staticmethod
    def add_args(parser):

        ToolService.add_args(parser)

def run():
    Service.launch(default_ident, __doc__)

