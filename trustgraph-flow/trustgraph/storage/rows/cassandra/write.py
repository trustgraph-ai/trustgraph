
"""
Graph writer.  Input is graph edge.  Writes edges to Cassandra graph.
"""

raise RuntimeError("This code is no longer in use")

import pulsar
import base64
import os
import argparse
import time
import logging
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from ssl import SSLContext, PROTOCOL_TLSv1_2

from .... schema import Rows
from .... log_level import LogLevel
from .... base import Consumer
from .... base.cassandra_config import add_cassandra_args, resolve_cassandra_config

# Module logger
logger = logging.getLogger(__name__)

module = "rows-write"
ssl_context = SSLContext(PROTOCOL_TLSv1_2)

default_input_queue = "rows-store"  # Default queue name
default_subscriber = module

class Processor(Consumer):

    def __init__(self, **params):
        
        input_queue = params.get("input_queue", default_input_queue)
        subscriber = params.get("subscriber", default_subscriber)
        
        # Use new parameter names, fall back to old for compatibility
        cassandra_host = params.get("cassandra_host", params.get("graph_host"))
        cassandra_username = params.get("cassandra_username", params.get("graph_username"))
        cassandra_password = params.get("cassandra_password", params.get("graph_password"))
        
        # Resolve configuration with environment variable fallback
        hosts, username, password = resolve_cassandra_config(
            host=cassandra_host,
            username=cassandra_username,
            password=cassandra_password
        )

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "subscriber": subscriber,
                "input_schema": Rows,
                "cassandra_host": ','.join(hosts),
                "cassandra_username": username,
                "cassandra_password": password,
            }
        )
        
        if username and password:
            auth_provider = PlainTextAuthProvider(username=username, password=password)
            self.cluster = Cluster(hosts, auth_provider=auth_provider, ssl_context=ssl_context)
        else:
            self.cluster = Cluster(hosts)
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

    async def handle(self, msg):

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

            logger.error(f"Exception: {str(e)}", exc_info=True)

            # If there's an error make sure to do table creation etc.
            self.tables.remove(name)

            raise e

    @staticmethod
    def add_args(parser):

        Consumer.add_args(
            parser, default_input_queue, default_subscriber,
        )
        add_cassandra_args(parser)

def run():

    Processor.launch(module, __doc__)

