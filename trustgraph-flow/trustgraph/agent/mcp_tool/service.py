
"""
MCP tool-calling service, calls an external MCP tool.  Input is
name + parameters, output is the response, either a string or an object.
"""

from ... base import ToolService

from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

default_ident = "mcp-tool"

class Service(ToolService):

    def __init__(self, **params):

        super(Service, self).__init__(
            **params
        )

    async def invoke_tool(self, name, parameters):

        try:
            print(name)
            print(parameters)
            # Connect to a streamable HTTP server
            async with streamablehttp_client("http://mcp-server:8000/mcp/") as (
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
                        name,
                        parameters
                    )

                    print(result)

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

