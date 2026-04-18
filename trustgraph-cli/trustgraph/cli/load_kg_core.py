"""
Starts a load operation on a knowledge core which is already stored by
the knowledge manager.  You could load a core with tg-put-kg-core and then
run this utility.
"""

import argparse
import os
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")
default_flow = "default"
default_collection = "default"

def load_kg_core(url, id, flow, collection, token=None, workspace="default"):

    api = Api(url, token=token, workspace=workspace).knowledge()

    api.load_kg_core(id=id, flow=flow, collection=collection)

def main():

    parser = argparse.ArgumentParser(
        prog='tg-load-kg-core',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--api-url',
        default=default_url,
        help=f'API URL (default: {default_url})',
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

    parser.add_argument(
        '-C', '--collection',
        default=default_collection,
        help=f'Collection ID (default: {default_collection})',
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

    args = parser.parse_args()

    try:

        load_kg_core(
            url=args.api_url,
            id=args.id,
            flow=args.flow_id,
            collection=args.collection,
            token=args.token,
            workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
