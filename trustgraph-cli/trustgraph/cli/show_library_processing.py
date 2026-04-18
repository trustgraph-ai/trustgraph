"""
"""

import argparse
import os
import tabulate
from trustgraph.api import Api

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def show_procs(url, token=None, workspace="default"):

    api = Api(url, token=token, workspace=workspace).library()

    procs = api.get_processings()

    if len(procs) == 0:
        print("No processing objects.")
        return

    for proc in procs:

        table = []
        table.append(("id", proc.id))
        table.append(("document-id", proc.document_id))
        table.append(("time", proc.time))
        table.append(("flow", proc.flow))
        table.append(("collection", proc.collection))
        table.append(("tags", ", ".join(proc.tags)))

        print(tabulate.tabulate(
            table,
            tablefmt="pretty",
            stralign="left",
            maxcolwidths=[None, 50],
        ))
        print()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-show-library-processing',
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

    args = parser.parse_args()

    try:

        show_procs(
            url=args.api_url,
            token=args.token,
            workspace=args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()
