
"""
Graph writer.  Input is graph edge.  Writes edges to FalkorDB graph.
"""

import pulsar
import base64
import os
import argparse
import time
import logging

from falkordb import FalkorDB

from .... base import TriplesStoreService

# Module logger
logger = logging.getLogger(__name__)

default_ident = "triples-write"

default_graph_url = 'falkor://falkordb:6379'
default_database = 'falkordb'

class Processor(TriplesStoreService):

    def __init__(self, **params):
        
        graph_url = params.get("graph_url", default_graph_url)
        database = params.get("database", default_database)

        super(Processor, self).__init__(
            **params | {
                "graph_url": graph_url,
                "database": database,
            }
        )

        self.db = database

        self.io = FalkorDB.from_url(graph_url).select_graph(database)

    def create_node(self, uri):

        logger.debug(f"Create node {uri}")

        res = self.io.query(
            "MERGE (n:Node {uri: $uri})",
            params={
                "uri": uri,
            },
        )

        logger.debug("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=res.nodes_created,
            time=res.run_time_ms
        ))

    def create_literal(self, value):

        logger.debug(f"Create literal {value}")

        res = self.io.query(
            "MERGE (n:Literal {value: $value})",
            params={
                "value": value,
            },
        )

        logger.debug("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=res.nodes_created,
            time=res.run_time_ms
        ))

    def relate_node(self, src, uri, dest):

        logger.debug(f"Create node rel {src} {uri} {dest}")

        res = self.io.query(
            "MATCH (src:Node {uri: $src}) "
            "MATCH (dest:Node {uri: $dest}) "
            "MERGE (src)-[:Rel {uri: $uri}]->(dest)",
            params={
                "src": src,
                "dest": dest,
                "uri": uri,
            },
        )

        logger.debug("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=res.nodes_created,
            time=res.run_time_ms
        ))

    def relate_literal(self, src, uri, dest):

        logger.debug(f"Create literal rel {src} {uri} {dest}")

        res = self.io.query(
            "MATCH (src:Node {uri: $src}) "
            "MATCH (dest:Literal {value: $dest}) "
            "MERGE (src)-[:Rel {uri: $uri}]->(dest)",
            params={
                "src": src,
                "dest": dest,
                "uri": uri,
            },
        )

        logger.debug("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=res.nodes_created,
            time=res.run_time_ms
        ))

    async def store_triples(self, message):

        for t in message.triples:

            self.create_node(t.s.value)

            if t.o.is_uri:
                self.create_node(t.o.value)
                self.relate_node(t.s.value, t.p.value, t.o.value)
            else:
                self.create_literal(t.o.value)
                self.relate_literal(t.s.value, t.p.value, t.o.value)

    @staticmethod
    def add_args(parser):

        TriplesStoreService.add_args(parser)

        parser.add_argument(
            '-g', '--graph-url',
            default=default_graph_url,
            help=f'Graph URL (default: {default_graph_url})'
        )

        parser.add_argument(
            '--database',
            default=default_database,
            help=f'FalkorDB database (default: {default_database})'
        )

def run():

    Processor.launch(default_ident, __doc__)

