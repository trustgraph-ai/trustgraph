
"""
Graph writer.  Input is graph edge.  Writes edges to Neo4j graph.
"""

import pulsar
import base64
import os
import argparse
import time

from neo4j import GraphDatabase
from .... base import TriplesStoreService

default_ident = "triples-write"

default_graph_host = 'bolt://neo4j:7687'
default_username = 'neo4j'
default_password = 'password'
default_database = 'neo4j'

class Processor(TriplesStoreService):

    def __init__(self, **params):
        
        id = params.get("id", default_ident)

        graph_host = params.get("graph_host", default_graph_host)
        username = params.get("username", default_username)
        password = params.get("password", default_password)
        database = params.get("database", default_database)

        super(Processor, self).__init__(
            **params | {
                "graph_host": graph_host,
                "username": username,
                "database": database,
            }
        )

        self.db = database

        self.io = GraphDatabase.driver(graph_host, auth=(username, password))

        with self.io.session(database=self.db) as session:
            self.create_indexes(session)

    def create_indexes(self, session):

        # Race condition, index creation failure is ignored.  Right thing
        # to do if the index already exists.  Wrong thing to do if it's
        # because the store is not up yet

        # In real-world cases, Neo4j will start up quicker than Pulsar
        # and this process will restart several times until Pulsar arrives,
        # so should be safe

        print("Create indexes...", flush=True)

        try:
            session.run(
                "CREATE INDEX Node_uri FOR (n:Node) ON (n.uri)",
            )
        except Exception as e:
            print(e, flush=True)
            # Maybe index already exists
            print("Index create failure ignored", flush=True)

        try:
            session.run(
                "CREATE INDEX Literal_value FOR (n:Literal) ON (n.value)",
            )
        except Exception as e:
            print(e, flush=True)
            # Maybe index already exists
            print("Index create failure ignored", flush=True)

        try:
            session.run(
                "CREATE INDEX Rel_uri FOR ()-[r:Rel]-() ON (r.uri)",
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

        parser.add_argument(
            '--database',
            default=default_database,
            help=f'Neo4j database (default: {default_database})'
        )

def run():

    Processor.launch(default_ident, __doc__)

