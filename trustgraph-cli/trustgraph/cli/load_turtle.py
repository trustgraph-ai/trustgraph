"""
Loads triples into the knowledge graph from Turtle files.
"""

import argparse
import os
import time
import rdflib
from typing import Iterator

from trustgraph.api import Api, Triple
from trustgraph.log_level import LogLevel

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")
default_collection = 'default'

class Loader:

    def __init__(
            self,
            files,
            flow,
            collection,
            document_id,
            url=default_url,
            token=None, workspace="default",
    ):
        self.files = files
        self.flow = flow
        self.workspace = workspace
        self.collection = collection
        self.document_id = document_id
        self.url = url
        self.token = token

    def load_triples_from_file(self, file) -> Iterator[Triple]:
        """Generator that yields Triple objects from a Turtle file"""

        g = rdflib.Graph()
        g.parse(file, format="turtle")

        for e in g:
            s_value = str(e[0])
            p_value = str(e[1])

            if isinstance(e[2], rdflib.term.URIRef):
                o_value = str(e[2])
            else:
                o_value = str(e[2])

            yield Triple(s=s_value, p=p_value, o=o_value)

    def run(self):
        """Load triples using Python API"""

        try:
            api = Api(url=self.url, token=self.token, workspace=self.workspace)
            bulk = api.bulk()

            print("Loading triples...")
            for file in self.files:
                print(f"  Processing {file}...")
                triples = self.load_triples_from_file(file)

                bulk.import_triples(
                    flow=self.flow,
                    triples=triples,
                    metadata={
                        "id": self.document_id,
                        "metadata": [],
                        "collection": self.collection
                    }
                )

            print("Triples loaded.")

        except Exception as e:
            print(f"Error: {e}", flush=True)
            raise

def main():

    parser = argparse.ArgumentParser(
        prog='tg-load-turtle',
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
        '-i', '--document-id',
        required=True,
        help=f'Document ID)',
    )

    parser.add_argument(
        '-f', '--flow-id',
        default="default",
        help=f'Flow ID (default: default)'
    )

    parser.add_argument(
        '-C', '--collection',
        default=default_collection,
        help=f'Collection ID (default: {default_collection})'
    )

    parser.add_argument(
        'files', nargs='+',
        help=f'Turtle files to load'
    )

    args = parser.parse_args()

    while True:

        try:
            loader = Loader(
                document_id=args.document_id,
                url=args.api_url,
                token=args.token,
                flow=args.flow_id,
                files=args.files,
                collection=args.collection,
                workspace=args.workspace,
            )

            loader.run()

            print("File loaded.")
            break

        except Exception as e:

            print("Exception:", e, flush=True)
            print("Will retry...", flush=True)

        time.sleep(10)

if __name__ == "__main__":
    main()
