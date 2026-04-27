"""
Outputs a flow blueprint definition in JSON format.
"""

import argparse
import os
import tabulate
from trustgraph.api import Api
import json

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def get_flow_blueprint(url, blueprint_name, token=None, workspace="default"):

    api = Api(url, token=token, workspace=workspace).flow()

    cls = api.get_blueprint(blueprint_name)

    print(json.dumps(cls, indent=4))

def main():

    parser = argparse.ArgumentParser(
        prog='tg-get-flow-blueprint',
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
        '-n', '--blueprint-name',
        required=True,
        help=f'Flow blueprint name',
    )

    args = parser.parse_args()

    try:

        get_flow_blueprint(
            url=args.api_url,
            blueprint_name=args.blueprint_name,
            token=args.token,
            workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
