"""
Lists loaded ontologies and their status, showing state (loading/ready/error),
class and property counts, and embedding progress.
"""

import argparse
import json
import os
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def query(url, flow_id, token=None, workspace="default", as_json=False):

    api = Api(url=url, token=token, workspace=workspace)
    socket = api.socket()
    flow = socket.flow(flow_id)

    try:
        result = flow.ontology_list()
        ontologies = result.get("ontologies", [])

        if as_json:
            print(json.dumps(ontologies, indent=2))
            return

        if not ontologies:
            print("No ontologies loaded.")
            return

        for o in ontologies:
            print(f"{o['ontology-id']}:")
            print(f"  State: {o['state']}")
            print(f"  Classes: {o['classes-total']}")
            print(f"  Properties: {o['properties-total']}")
            total = o['classes-total'] + o['properties-total']
            print(f"  Embedded: {o['elements-embedded']}/{total}")
            if o.get("error-message"):
                print(f"  Error: {o['error-message']}")

    finally:
        socket.close()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-list-ontologies',
        description=__doc__,
    )

    parser.add_argument(
        '-u', '--url',
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
        '-f', '--flow-id',
        default="default",
        help=f'Flow ID (default: default)'
    )

    parser.add_argument(
        '-j', '--json',
        action='store_true',
        default=False,
        help='Output as JSON',
    )

    args = parser.parse_args()

    try:

        query(
            url=args.url,
            flow_id=args.flow_id,
            token=args.token,
            workspace=args.workspace,
            as_json=args.json,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
