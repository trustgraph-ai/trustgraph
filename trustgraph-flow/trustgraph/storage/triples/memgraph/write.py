
"""
Graph writer.  Input is graph edge.  Writes edges to Memgraph.
"""

import pulsar
import base64
import os
import argparse
import time

from neo4j import GraphDatabase

from .... schema import Triples
from .... schema import triples_store_queue
from .... log_level import LogLevel
from .... base import Consumer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = triples_store_queue
default_subscriber = module

default_graph_host = 'bolt://memgraph:7687'
default_username = 'memgraph'
default_password = 'password'
default_database = 'memgraph'

class Processor(Consumer):

    def __init__(self, **params):
        
        input_queue = params.get("input_queue", default_input_queue)
        subscriber = params.get("subscriber", default_subscriber)
        graph_host = params.get("graph_host", default_graph_host)
        username = params.get("username", default_username)
        password = params.get("password", default_password)
        database = params.get("database", default_database)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "subscriber": subscriber,
                "input_schema": Triples,
                "graph_host": graph_host,
            }
        )

        self.db = database

        self.io = GraphDatabase.driver(graph_host, auth=(username, password))

        with self.io.session(database=self.db) as session:
            self.create_indexes(session)

    def create_indexes(self, session):

        print("Create indexes...", flush=True)

        try:
            session.run(
                "CREATE INDEX ON :Node",
            )
        except Exception as e:
            print(e, flush=True)
            # Maybe index already exists
            print("Index create failure ignored", flush=True)

        try:
            session.run(
                "CREATE INDEX ON :Node(uri)"
            )
        except Exception as e:
            print(e, flush=True)
            # Maybe index already exists
            print("Index create failure ignored", flush=True)

        try:
            session.run(
                "CREATE INDEX ON :Literal",
            )
        except Exception as e:
            print(e, flush=True)
            # Maybe index already exists
            print("Index create failure ignored", flush=True)

        try:
            session.run(
                "CREATE INDEX ON :Literal(value)"
            )
        except Exception as e:
            print(e, flush=True)
            # Maybe index already exists
            print("Index create failure ignored", flush=True)

        print("Index creation done", flush=True)

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

    def create_triple(self, tx, t):

        # Create new s node with given uri, if not exists
        result = tx.run(
            "MERGE (n:Node {uri: $uri})",
            uri=t.s.value
        )

        if t.o.is_uri:

            # Create new o node with given uri, if not exists
            result = tx.run(
                "MERGE (n:Node {uri: $uri})",
                uri=t.o.value
            )

            result = tx.run(
                "MATCH (src:Node {uri: $src}) "
                "MATCH (dest:Node {uri: $dest}) "
                "MERGE (src)-[:Rel {uri: $uri}]->(dest)",
                src=t.s.value, dest=t.o.value, uri=t.p.value,
            )

        else:
        
            # Create new o literal with given uri, if not exists
            result = tx.run(
                "MERGE (n:Literal {value: $value})",
                value=t.o.value
            )

            result = tx.run(
                "MATCH (src:Node {uri: $src}) "
                "MATCH (dest:Literal {value: $dest}) "
                "MERGE (src)-[:Rel {uri: $uri}]->(dest)",
                src=t.s.value, dest=t.o.value, uri=t.p.value,
            )
        
    def handle(self, msg):

        v = msg.value()

        for t in v.triples:

            # self.create_node(t.s.value)

            # if t.o.is_uri:
            #     self.create_node(t.o.value)
            #     self.relate_node(t.s.value, t.p.value, t.o.value)
            # else:
            #     self.create_literal(t.o.value)
            #     self.relate_literal(t.s.value, t.p.value, t.o.value)

            with self.io.session(database=self.db) as session:
                session.execute_write(self.create_triple, t)

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
            help=f'Memgraph username (default: {default_username})'
        )

        parser.add_argument(
            '--password',
            default=default_password,
            help=f'Memgraph password (default: {default_password})'
        )

        parser.add_argument(
            '--database',
            default=default_database,
            help=f'Memgraph database (default: {default_database})'
        )

def run():

    Processor.start(module, __doc__)

