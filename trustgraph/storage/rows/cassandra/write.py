
"""
Graph writer.  Input is graph edge.  Writes edges to Cassandra graph.
"""

import pulsar
import base64
import os
import argparse
import time
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider

from .... schema import Rows
from .... schema import rows_store_queue
from .... log_level import LogLevel
from .... base import Consumer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = rows_store_queue
default_subscriber = module
default_graph_host='localhost'

class Processor(Consumer):

    def __init__(self, **params):
        
        input_queue = params.get("input_queue", default_input_queue)
        subscriber = params.get("subscriber", default_subscriber)
        graph_host = params.get("graph_host", default_graph_host)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "subscriber": subscriber,
                "input_schema": Rows,
                "graph_host": graph_host,
            }
        )

        self.cluster = Cluster(graph_host.split(","))
        self.session = self.cluster.connect()

        self.tables = set()

        self.session.execute("""
        create keyspace if not exists trustgraph
            with replication = { 
                'class' : 'SimpleStrategy', 
                'replication_factor' : 1 
            };
        """);

        self.session.execute("use trustgraph");

    def handle(self, msg):

        try:

            v = msg.value()
            name = v.row_schema.name

            if name not in self.tables:

                # FIXME: SQL injection?

                pkey = []

                stmt = "create table if not exists " + name + " ( "

                for field in v.row_schema.fields:

                    stmt += field.name + " text, "

                    if field.primary:
                        pkey.append(field.name)

                stmt += "PRIMARY KEY (" + ", ".join(pkey) + "));"

                self.session.execute(stmt)

                self.tables.add(name);

            for row in v.rows:

                field_names = []
                values = []
                
                for field in v.row_schema.fields:
                    field_names.append(field.name)
                    values.append(row[field.name])

                # FIXME: SQL injection?
                stmt = (
                    "insert into " + name + " (" + ", ".join(field_names) +
                    ") values (" + ",".join(["%s"] * len(values)) + ")"
                )

                self.session.execute(stmt, values)

        except Exception as e:

            print("Exception:", str(e), flush=True)

            # If there's an error make sure to do table creation etc.
            self.tables.remove(name)

            raise e

    @staticmethod
    def add_args(parser):

        Consumer.add_args(
            parser, default_input_queue, default_subscriber,
        )

        parser.add_argument(
            '-g', '--graph-host',
            default="localhost",
            help=f'Graph host (default: localhost)'
        )

def run():

    Processor.start(module, __doc__)

