"""
Configures and registers MCP (Model Context Protocol) tools in the
TrustGraph system.

MCP tools are external services that follow the Model Context Protocol
specification. This script stores MCP tool configurations with:
- id: Unique identifier for the tool
- remote-name: Name used by the MCP server (defaults to id)
- url: MCP server endpoint URL
- auth-token: Optional bearer token for authentication

Configurations are stored in the 'mcp' configuration group and can be
referenced by agent tools using the 'mcp-tool' type.
"""

import argparse
import os
from trustgraph.api import Api, ConfigValue
import textwrap
import json

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')

def set_mcp_tool(
        url : str,
        id : str,
        remote_name : str,
        tool_url : str,
        auth_token : str = None,
):

    api = Api(url).config()

    # Build the MCP tool configuration
    config = {
        "remote-name": remote_name,
        "url": tool_url,
    }

    if auth_token:
        config["auth-token"] = auth_token

    # Store the MCP tool configuration in the 'mcp' group
    values = api.put([
        ConfigValue(
            type="mcp", key=id, value=json.dumps(config)
        )
    ])

def main():

    parser = argparse.ArgumentParser(
        prog='tg-set-mcp-tool',
        description=__doc__,
        epilog=textwrap.dedent('''
            MCP tools are configured with a name and URL. The URL should point
            to the MCP server endpoint that provides the tool functionality.
            Optionally, an auth-token can be provided for secured endpoints.

            Examples:
              %(prog)s --id weather --tool-url "http://localhost:3000/weather"
              %(prog)s --id calculator --tool-url "http://mcp-tools.example.com/calc"
              %(prog)s --id secure-tool --tool-url "https://api.example.com/mcp" \\
                --auth-token "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        ''').strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-i', '--id',
        required=True,
        help='MCP tool identifier',
    )

    parser.add_argument(
        '-r', '--remote-name',
        required=False,
        help='Remote MCP tool name (defaults to --id if not specified)',
    )

    parser.add_argument(
        '--tool-url',
        required=True,
        help='MCP tool URL endpoint',
    )

    parser.add_argument(
        '--auth-token',
        required=False,
        help='Bearer token for authentication (optional)',
    )

    args = parser.parse_args()

    try:

        if not args.id:
            raise RuntimeError("Must specify --id for MCP tool")

        if not args.tool_url:
            raise RuntimeError("Must specify --tool-url for MCP tool")

        if args.remote_name:
            remote_name = args.remote_name
        else:
            remote_name = args.id

        set_mcp_tool(
            url=args.api_url,
            id=args.id,
            remote_name=remote_name,
            tool_url=args.tool_url,
            auth_token=args.auth_token
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()