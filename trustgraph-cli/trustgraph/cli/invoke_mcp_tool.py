"""
Invokes MCP (Model Control Protocol) tools through the TrustGraph API.
Allows calling MCP tools by specifying the tool name and providing
parameters as a JSON-encoded dictionary. The tool is executed within
the context of a specified flow.
"""

import argparse
import os
import json
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')

def query(url, flow_id, name, parameters):

    api = Api(url).flow().id(flow_id)

    resp = api.mcp_tool(name=name, parameters=parameters)

    if isinstance(resp, str):
        print(resp)
    else:
        print(json.dumps(resp, indent=4))

def main():

    parser = argparse.ArgumentParser(
        prog='tg-invoke-mcp-tool',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-f', '--flow-id',
        default="default",
        help=f'Flow ID (default: default)'
    )

    parser.add_argument(
        '-n', '--name',
        metavar='tool-name',
        help=f'MCP tool name',
    )

    parser.add_argument(
        '-P', '--parameters',
        help='''Tool parameters, should be JSON-encoded dict.''',
    )

    args = parser.parse_args()


    if args.parameters:
        parameters = json.loads(args.parameters)
    else:
        parameters = {}

    try:

        query(
            url = args.url,
            flow_id = args.flow_id,
            name = args.name,
            parameters = parameters,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()