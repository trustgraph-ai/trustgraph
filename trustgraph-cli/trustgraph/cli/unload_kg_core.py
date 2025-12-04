"""
Starts a load operation on a knowledge core which is already stored by
the knowledge manager.  You could load a core with tg-put-kg-core and then
run this utility.
"""

import argparse
import os
import tabulate
from trustgraph.api import Api
import json

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_flow = "default"
default_collection = "default"

def unload_kg_core(url, user, id, flow, token=None):

    api = Api(url, token=token).knowledge()

    class_names = api.unload_kg_core(user = user, id = id, flow=flow)

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
        '-U', '--user',
        default="trustgraph",
        help='API URL (default: trustgraph)',
    )

    parser.add_argument(
        '--id', '--identifier',
        required=True,
        help=f'Knowledge core ID',
    )

    parser.add_argument(
        '-f', '--flow-id',
        default=default_flow,
        help=f'Flow ID (default: {default_flow}',
    )

    args = parser.parse_args()

    try:

        unload_kg_core(
            url=args.api_url,
            user=args.user,
            id=args.id,
            flow=args.flow_id,
            token=args.token,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
