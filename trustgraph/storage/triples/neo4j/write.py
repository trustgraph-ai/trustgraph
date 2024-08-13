
"""
Graph writer.  Input is graph edge.  Writes edges to Cassandra graph.
"""

import pulsar
import base64
import os
import argparse
import time

from neo4j import GraphDatabase

from .... schema import Triple
from .... schema import triples_store_queue
from .... log_level import LogLevel
from .... base import Consumer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = triples_store_queue
default_subscriber = module

default_graph_host = 'bolt://localhost:7687'
default_username = 'neo4j'
default_password = 'password'

class Processor(Consumer):

    def __init__(self, **params):
        
        input_queue = params.get("input_queue", default_input_queue)
        subscriber = params.get("subscriber", default_subscriber)
        graph_host = params.get("graph_host", default_graph_host)
        username = params.get("username", default_username)
        password = params.get("passowrd", default_password)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "subscriber": subscriber,
                "input_schema": Triple,
                "graph_host": graph_host,
            }
        )

        self.db = "neo4j"

        self.io = GraphDatabase.driver(graph_host, auth=(username, password))

    def create_node(self, uri):

        print("Create node", uri)

        summary = self.io.execute_query(
            "MERGE (n:Node {uri: $uri})",
            uri=uri,
            database_=self.db,
        ).summary

        print("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=summary.counters.nodes_created,
            time=summary.result_available_after
        ))

    def create_literal(self, value):

        print("Create literal", value)

        summary = self.io.execute_query(
            "MERGE (n:Literal {value: $value})",
            value=value,
            database_=self.db,
        ).summary

        print("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=summary.counters.nodes_created,
            time=summary.result_available_after
        ))

    def relate_node(self, src, uri, dest):

        print("Create node rel", src, uri, dest)

        summary = self.io.execute_query(
            "MATCH (src:Node {uri: $src}) "
            "MATCH (dest:Node {uri: $dest}) "
            "MERGE (src)-[:Rel {uri: $uri}]->(dest)",
            src=src, dest=dest, uri=uri,
            database_=self.db,
        ).summary

        print("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=summary.counters.nodes_created,
            time=summary.result_available_after
        ))

    def relate_literal(self, src, uri, dest):

        print("Create literal rel", src, uri, dest)

        summary = self.io.execute_query(
            "MATCH (src:Node {uri: $src}) "
            "MATCH (dest:Literal {value: $dest}) "
            "MERGE (src)-[:Rel {uri: $uri}]->(dest)",
            src=src, dest=dest, uri=uri,
            database_=self.db,
        ).summary

        print("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=summary.counters.nodes_created,
            time=summary.result_available_after
        ))
    def handle(self, msg):

        v = msg.value()

        self.create_node(v.s.value)

        if v.o.is_uri:
            self.create_node(v.o.value)
            self.relate_node(v.s.value, v.p.value, v.o.value)
        else:
            self.create_literal(v.o.value)
            self.relate_literal(v.s.value, v.p.value, v.o.value)

    @staticmethod
    def add_args(parser):

        Consumer.add_args(
            parser, default_input_queue, default_subscriber,
        )

        parser.add_argument(
            '-g', '--graph_host',
            default=default_graph_host,
            help=f'Graph host (default: {default_graph_host})'
        )

        parser.add_argument(
            '--username',
            default=default_username,
            help=f'Neo4j username (default: {default_username})'
        )

        parser.add_argument(
            '--password',
            default=default_password,
            help=f'Neo4j password (default: {default_password})'
        )

def run():

    Processor.start(module, __doc__)

