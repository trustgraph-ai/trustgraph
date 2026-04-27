"""
Shows all loaded library documents
"""

import argparse
import os
import tabulate
from trustgraph.api import Api, ConfigKey
import json

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")

def show_docs(url, token=None, workspace="default"):

    api = Api(url, token=token, workspace=workspace).library()

    docs = api.get_documents()

    if len(docs) == 0:
        print("No documents.")
        return

    for doc in docs:

        table = []
        table.append(("id", doc.id))
        table.append(("time", doc.time))
        table.append(("title", doc.title))
        table.append(("kind", doc.kind))
        table.append(("note", doc.comments))
        table.append(("tags", ", ".join(doc.tags)))

        print(tabulate.tabulate(
            table,
            tablefmt="pretty",
            stralign="left",
            maxcolwidths=[None, 67],
        ))
        print()

def main():

    parser = argparse.ArgumentParser(
        prog='tg-show-library-documents',
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

        show_docs(
            url = args.api_url,
            token = args.token,
            workspace = args.workspace,
        )

    except Exception as e:

        print("Exception:", e, flush=True)

if __name__ == "__main__":
    main()