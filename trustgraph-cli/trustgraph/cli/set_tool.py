"""
Configures and registers tools in the TrustGraph system.

This script allows you to define agent tools with various types including:
- knowledge-query: Query knowledge bases  
- text-completion: Text generation
- mcp-tool: Reference to MCP (Model Context Protocol) tools
- prompt: Prompt template execution

Tools are stored in the 'tool' configuration group and can include
argument specifications for parameterized execution.

IMPORTANT: The tool 'name' is used by agents to invoke the tool and must
be a valid function identifier (use snake_case, no spaces or special chars).
The 'description' provides human-readable information about the tool.
"""

from typing import List
import argparse
import os
from trustgraph.api import Api, ConfigKey, ConfigValue
import json
import tabulate
import textwrap
import dataclasses

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')

@dataclasses.dataclass
class Argument:
    name : str
    type : str
    description : str

    @staticmethod
    def parse(s):

        parts = s.split(":")
        if len(parts) != 3:
            raise RuntimeError(
                "Arguments should be form name:type:description"
            )

        valid_types = [
            "string", "number",
        ]

        if parts[1] not in valid_types:
            raise RuntimeError(
                f"Type {parts[1]} invalid, use: " +
                ", ".join(valid_types)
            )

        return Argument(name=parts[0], type=parts[1], description=parts[2])

def set_tool(
        url : str,
        id : str,
        name : str,
        description : str,
        type : str,
        mcp_tool : str,
        collection : str,
        template : str,
        arguments : List[Argument],
):

    api = Api(url).config()

    values = api.get([
        ConfigKey(type="agent", key="tool-index")
    ])

    object = {
        "name": name,
        "description": description,
        "type": type,
    }

    if mcp_tool: object["mcp-tool"] = mcp_tool

    if collection: object["collection"] = collection

    if template: object["template"] = template

    if arguments:
        object["arguments"] = [
            {
                "name": a.name,
                "type": a.type,
                "description": a.description,
            }
            for a in arguments
        ]

    values = api.put([
        ConfigValue(
            type="tool", key=f"{id}", value=json.dumps(object)
        )
    ])

    print("Tool set.")

def main():

    parser = argparse.ArgumentParser(
        prog='tg-set-tool',
        description=__doc__,
        epilog=textwrap.dedent('''
            Valid tool types:
              knowledge-query    - Query knowledge bases
              text-completion    - Text completion/generation
              mcp-tool           - Model Control Protocol tool
              prompt             - Prompt template query
            
            Valid argument types:
              string            - String/text parameter
              number            - Numeric parameter
            
            Examples:
              %(prog)s --id weather_tool --name get_weather \\
                       --type knowledge-query \\
                       --description "Get weather information for a location" \\
                       --argument location:string:"Location to query" \\
                       --argument units:string:"Temperature units (C/F)"
              
              %(prog)s --id calc_tool --name calculate --type mcp-tool \\
                       --description "Perform mathematical calculations" \\
                       --mcp-tool calculator \\
                       --argument expression:string:"Mathematical expression"
        ''').strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '--id',
        help=f'Unique tool identifier',
    )

    parser.add_argument(
        '--name',
        help=f'Tool name used by agents to invoke this tool (use snake_case, e.g., get_weather)',
    )

    parser.add_argument(
        '--description',
        help=f'Detailed description of what the tool does',
    )

    parser.add_argument(
        '--type',
        help=f'Tool type, one of: knowledge-query, text-completion, mcp-tool, prompt',
    )

    parser.add_argument(
        '--mcp-tool',
        help=f'For MCP type: ID of MCP tool configuration (as defined by tg-set-mcp-tool)',
    )

    parser.add_argument(
        '--collection',
        help=f'For knowledge-query type: collection to query',
    )

    parser.add_argument(
        '--template',
        help=f'For prompt type: template ID to use',
    )

    parser.add_argument(
       '--argument',
       nargs="*",
       help=f'Tool arguments in the form: name:type:description (can specify multiple)',
    )

    args = parser.parse_args()

    try:

        valid_types = [
            "knowledge-query", "text-completion", "mcp-tool", "prompt"
        ]

        if args.id is None:
            raise RuntimeError("Must specify --id for tool")

        if args.name is None:
            raise RuntimeError("Must specify --name for tool")

        if args.type:
            if args.type not in valid_types:
                raise RuntimeError(
                    "Type must be one of: " + ", ".join(valid_types)
                )

        mcp_tool = args.mcp_tool

        if args.argument:
            arguments = [
                Argument.parse(a)
                for a in args.argument
            ]
        else:
            arguments = []

        set_tool(
            url=args.api_url,
            id=args.id,
            name=args.name,
            description=args.description,
            type=args.type,
            mcp_tool=mcp_tool,
            collection=args.collection,
            template=args.template,
            arguments=arguments,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()