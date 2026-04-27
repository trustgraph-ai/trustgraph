"""
Stops a processing flow.
"""

import argparse
import os
import tabulate
from trustgraph.api import Api
import json

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def stop_flow(url, flow_id, token=None, workspace="default"):

    api = Api(url, token=token, workspace=workspace).flow()

    api.stop(id = flow_id)

def main():

    parser = argparse.ArgumentParser(
        prog='tg-stop-flow',
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
        '-i', '--flow-id',
        required=True,
        help=f'Flow ID',
    )

    args = parser.parse_args()

    try:

        stop_flow(
            url=args.api_url,
            flow_id=args.flow_id,
            token=args.token,
            workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()