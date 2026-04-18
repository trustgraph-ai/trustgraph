"""
Unloads a knowledge core from a flow.
"""

import argparse
import os
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")
default_flow = "default"

def unload_kg_core(url, id, flow, token=None, workspace="default"):

    api = Api(url, token=token, workspace=workspace).knowledge()

    api.unload_kg_core(id=id, flow=flow)

def main():

    parser = argparse.ArgumentParser(
        prog='tg-unload-kg-core',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
    )

    parser.add_argument(
        '-t', '--token',
        default=default_token,
        help='Authentication token (default: $TRUSTGRAPH_TOKEN)',
    )

    parser.add_argument(
        '-w', '--workspace',
        default=default_workspace,
        help=f'Workspace (default: {default_workspace})',
    )

    parser.add_argument(
        '--id', '--identifier',
        required=True,
        help=f'Knowledge core ID',
    )

    parser.add_argument(
        '-f', '--flow-id',
        default=default_flow,
        help=f'Flow ID (default: {default_flow})',
    )

    args = parser.parse_args()

    try:

        unload_kg_core(
            url=args.api_url,
            id=args.id,
            flow=args.flow_id,
            token=args.token,
            workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
