"""
Deletes a loaded ontology from the config service.
"""

import argparse
import os
import sys
from trustgraph.api import Api
from trustgraph.api.types import ConfigKey

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")


def delete_ontology(url, ontology_id, token=None, workspace="default"):
    api = Api(url, token=token, workspace=workspace).config()

    config_key = ConfigKey(type="ontology", key=ontology_id)
    api.delete([config_key])

    print(f"Ontology '{ontology_id}' deleted")


def main():

    parser = argparse.ArgumentParser(
        prog='tg-delete-ontology',
        description=__doc__,
    )

    parser.add_argument(
        '--ontology-id', '-i',
        required=True,
        help='Ontology identifier',
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

    args = parser.parse_args()

    try:

        delete_ontology(
            url=args.api_url,
            ontology_id=args.ontology_id,
            token=args.token,
            workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
