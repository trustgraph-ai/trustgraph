"""
Loads triples and entity contexts into the knowledge graph.
"""

import argparse
import os
import time
import rdflib
from typing import Iterator, Tuple

from trustgraph.api import Api, Triple
from trustgraph.api.types import Uri, Literal
from trustgraph.log_level import LogLevel

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8888/')
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")
default_collection = 'default'

class KnowledgeLoader:

    def __init__(
            self,
            files,
            flow,
            collection,
            document_id,
            url=default_url,
            token=None, workspace="default",
            graph="",
            format="turtle",
    ):
        self.files = files
        self.flow = flow
        self.collection = collection
        self.document_id = document_id
        self.url = url
        self.token = token
        self.workspace = workspace
        self.graph = graph
        self.format = format

    def _make_triple(self, s, p, o, graph=""):
        s_value = Uri(str(s))
        p_value = Uri(str(p))

        if isinstance(o, rdflib.term.Literal):
            o_value = Literal(
                str(o),
                datatype=str(o.datatype) if o.datatype else None,
                language=str(o.language) if o.language else None,
            )
        else:
            o_value = Uri(str(o))

        return Triple(s=s_value, p=p_value, o=o_value, g=graph)

    def load_triples_from_file(self, file) -> Iterator[Triple]:
        """Generator that yields Triple objects from a data file."""

        if self.format == "trig":
            ds = rdflib.Dataset()
            ds.parse(file, format="trig")
            for s, p, o, g in ds.quads((None, None, None, None)):
                graph_id = g.identifier if hasattr(g, 'identifier') else g
                graph = str(graph_id) if graph_id else ""
                if graph == "urn:x-rdflib:default":
                    graph = ""
                yield self._make_triple(s, p, o, graph)
        else:
            g = rdflib.Graph()
            g.parse(file, format="turtle")
            for s, p, o in g:
                yield self._make_triple(s, p, o, self.graph)

    def load_entity_contexts_from_file(self, file) -> Iterator[Tuple[str, str]]:
        """Generator that yields (entity, context) tuples from a data file."""

        if self.format == "trig":
            ds = rdflib.Dataset()
            ds.parse(file, format="trig")
            for s, p, o, _g in ds.quads((None, None, None, None)):
                if isinstance(o, rdflib.term.URIRef):
                    continue
                yield (str(s), str(o))
        else:
            g = rdflib.Graph()
            g.parse(file, format="turtle")
            for s, p, o in g:
                if isinstance(o, rdflib.term.URIRef):
                    continue
                yield (str(s), str(o))

    def run(self):
        """Load triples and entity contexts using Python API"""

        try:
            api = Api(url=self.url, token=self.token, workspace=self.workspace)
            bulk = api.bulk()

            print("Loading triples...")
            total_triples = 0
            for file in self.files:
                print(f"  Processing {file}...")
                count = 0

                def counting_triples():
                    nonlocal count
                    for triple in self.load_triples_from_file(file):
                        count += 1
                        yield triple

                bulk.import_triples(
                    flow=self.flow,
                    triples=counting_triples(),
                    metadata={
                        "id": self.document_id,
                        "metadata": [],
                        "collection": self.collection
                    }
                )
                print(f"    Loaded {count} triples")
                total_triples += count

            print(f"Triples loaded. Total: {total_triples}")

            print("Loading entity contexts...")
            total_contexts = 0
            for file in self.files:
                print(f"  Processing {file}...")
                count = 0

                def entity_context_generator():
                    nonlocal count
                    for entity, context in self.load_entity_contexts_from_file(file):
                        count += 1
                        yield {
                            "entity": {"t": "i", "i": entity},
                            "context": context
                        }

                bulk.import_entity_contexts(
                    flow=self.flow,
                    contexts=entity_context_generator(),
                    metadata={
                        "id": self.document_id,
                        "metadata": [],
                        "collection": self.collection
                    }
                )
                print(f"    Loaded {count} entity contexts")
                total_contexts += count

            print(f"Entity contexts loaded. Total: {total_contexts}")

        except Exception as e:
            print(f"Error: {e}", flush=True)
            raise

def main():

    parser = argparse.ArgumentParser(
        prog='tg-load-knowledge',
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
        '-g', '--graph',
        default="",
        help='Named graph URI (e.g. urn:graph:policy). Default: default graph'
    )

    parser.add_argument(
        '-F', '--format',
        choices=["turtle", "trig"],
        default="turtle",
        help='Input format (default: turtle)'
    )

    parser.add_argument(
        'files', nargs='+',
        help=f'Data files to load'
    )

    args = parser.parse_args()

    if args.format == "trig" and args.graph:
        parser.error("--format trig and --graph are incompatible: "
                      "named graphs come from the TriG data")

    while True:

        try:
            loader = KnowledgeLoader(
                document_id=args.document_id,
                url=args.api_url,
                token=args.token,
                flow=args.flow_id,
                files=args.files,
                collection=args.collection,
                workspace=args.workspace,
                graph=args.graph,
                format=args.format,
            )

            loader.run()

            print("Triples and entity contexts loaded.")
            break

        except Exception as e:

            print("Exception:", e, flush=True)
            print("Will retry...", flush=True)

        time.sleep(10)

if __name__ == "__main__":
    main()
