"""
Loads triples and entity contexts into the knowledge graph.
"""

import asyncio
import argparse
import os
import time
import rdflib
import json
from websockets.asyncio.client import connect
from typing import List, Dict, Any

from trustgraph.log_level import LogLevel

default_url = os.getenv("TRUSTGRAPH_URL", 'ws://localhost:8088/')
default_user = 'trustgraph'
default_collection = 'default'

class KnowledgeLoader:

    def __init__(
            self,
            files,
            flow,
            user,
            collection,
            document_id,
            url = default_url,
    ):

        if not url.endswith("/"):
            url += "/"

        self.triples_url = url + f"api/v1/flow/{flow}/import/triples"
        self.entity_contexts_url = url + f"api/v1/flow/{flow}/import/entity-contexts"

        self.files = files
        self.user = user
        self.collection = collection
        self.document_id = document_id

    async def run(self):

        try:
            # Load triples first
            async with connect(self.triples_url) as ws:
                for file in self.files:
                    await self.load_triples(file, ws)

            # Then load entity contexts
            async with connect(self.entity_contexts_url) as ws:
                for file in self.files:
                    await self.load_entity_contexts(file, ws)

        except Exception as e:
            print(e, flush=True)

    async def load_triples(self, file, ws):

        g = rdflib.Graph()
        g.parse(file, format="turtle")

        def Value(value, is_uri):
            return { "v": value, "e": is_uri }

        for e in g:
            s = Value(value=str(e[0]), is_uri=True)
            p = Value(value=str(e[1]), is_uri=True)
            if type(e[2]) == rdflib.term.URIRef:
                o = Value(value=str(e[2]), is_uri=True)
            else:
                o = Value(value=str(e[2]), is_uri=False)

            req = {
                "metadata": {
                    "id": self.document_id,
                    "metadata": [],
                    "user": self.user,
                    "collection": self.collection
                },
                "triples": [
                    {
                        "s": s,
                        "p": p,
                        "o": o,
                    }
                ]
            }

            await ws.send(json.dumps(req))

    async def load_entity_contexts(self, file, ws):
        """
        Load entity contexts by extracting entities from the RDF graph
        and generating contextual descriptions based on their relationships.
        """

        g = rdflib.Graph()
        g.parse(file, format="turtle")

        for s, p, o in g:
            # If object is a URI, do nothing
            if isinstance(o, rdflib.term.URIRef):
                continue
                
            # If object is a literal, create entity context for subject with literal as context
            s_str = str(s)
            o_str = str(o)
            
            req = {
                "metadata": {
                    "id": self.document_id,
                    "metadata": [],
                    "user": self.user,
                    "collection": self.collection
                },
                "entities": [
                    {
                        "entity": {
                            "v": s_str,
                            "e": True
                        },
                        "context": o_str
                    }
                ]
            }

            await ws.send(json.dumps(req))


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
        '-U', '--user',
        default=default_user,
        help=f'User ID (default: {default_user})'
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
            loader = KnowledgeLoader(
                document_id = args.document_id,
                url = args.api_url,
                flow = args.flow_id,
                files = args.files,
                user = args.user,
                collection = args.collection,
            )

            asyncio.run(loader.run())

            print("Triples and entity contexts loaded.")
            break

        except Exception as e:

            print("Exception:", e, flush=True)
            print("Will retry...", flush=True)

        time.sleep(10)

if __name__ == "__main__":
    main()