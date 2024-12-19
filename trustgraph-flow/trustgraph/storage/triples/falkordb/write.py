
"""
Graph writer.  Input is graph edge.  Writes edges to FalkorDB graph.
"""

import pulsar
import base64
import os
import argparse
import time

from falkordb import FalkorDB

from .... schema import Triples
from .... schema import triples_store_queue
from .... log_level import LogLevel
from .... base import Consumer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = triples_store_queue
default_subscriber = module

default_graph_url = 'falkor://falkordb:6379'
default_database = 'falkordb'

class Processor(Consumer):

    def __init__(self, **params):
        
        input_queue = params.get("input_queue", default_input_queue)
        subscriber = params.get("subscriber", default_subscriber)
        graph_url = params.get("graph_host", default_graph_url)
        database = params.get("database", default_database)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "subscriber": subscriber,
                "input_schema": Triples,
                "graph_url": graph_url,
            }
        )

        self.db = database

        self.io = FalkorDB.from_url(graph_url).select_graph(database)

    def create_node(self, uri):

        print("Create node", uri)

        res = self.io.query(
            "MERGE (n:Node {uri: $uri})",
            params={
                "uri": uri,
            },
        )

        print("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=res.nodes_created,
            time=res.run_time_ms
        ))

    def create_literal(self, value):

        print("Create literal", value)

        res = self.io.query(
            "MERGE (n:Literal {value: $value})",
            params={
                "value": value,
            },
        )

        print("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=res.nodes_created,
            time=res.run_time_ms
        ))

    def relate_node(self, src, uri, dest):

        print("Create node rel", src, uri, dest)

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

        print("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=res.nodes_created,
            time=res.run_time_ms
        ))

    def relate_literal(self, src, uri, dest):

        print("Create literal rel", src, uri, dest)

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

        print("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=res.nodes_created,
            time=res.run_time_ms
        ))

    def handle(self, msg):

        v = msg.value()

        for t in v.triples:

            self.create_node(t.s.value)

            if t.o.is_uri:
                self.create_node(t.o.value)
                self.relate_node(t.s.value, t.p.value, t.o.value)
            else:
                self.create_literal(t.o.value)
                self.relate_literal(t.s.value, t.p.value, t.o.value)

    @staticmethod
    def add_args(parser):

        Consumer.add_args(
            parser, default_input_queue, default_subscriber,
        )

        parser.add_argument(
            '-g', '--graph_host',
            default=default_graph_url,
            help=f'Graph host (default: {default_graph_url})'
        )

        parser.add_argument(
            '--database',
            default=default_database,
            help=f'FalkorDB database (default: {default_database})'
        )

def run():

    Processor.start(module, __doc__)

