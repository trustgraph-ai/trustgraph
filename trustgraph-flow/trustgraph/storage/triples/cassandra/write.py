
"""
Graph writer.  Input is graph edge.  Writes edges to Cassandra graph.
"""

import pulsar
import base64
import os
import argparse
import time

from .... direct.cassandra import TrustGraph
from .... schema import Triples
from .... schema import triples_store_queue
from .... log_level import LogLevel
from .... base import Consumer

module = "triples-write"

default_input_queue = triples_store_queue
default_subscriber = module
default_graph_host='localhost'

class Processor(Consumer):

    def __init__(self, **params):
        
        input_queue = params.get("input_queue", default_input_queue)
        subscriber = params.get("subscriber", default_subscriber)
        graph_host = params.get("graph_host", default_graph_host)
        graph_username = params.get("graph_username", None)
        graph_password = params.get("graph_password", None)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "subscriber": subscriber,
                "input_schema": Triples,
                "graph_host": graph_host,
                "graph_username": graph_username,
                "graph_password": graph_password,
            }
        )
        
        self.graph_host = [graph_host]
        self.username = graph_username
        self.password = graph_password
        self.table = None

    async def handle(self, msg):

        v = msg.value()

        table = (v.metadata.user, v.metadata.collection)

        if self.table is None or self.table != table:

            self.tg = None

            try:
                if self.username and self.password:
                    self.tg = TrustGraph(
                        hosts=self.graph_host,
                        keyspace=v.metadata.user, table=v.metadata.collection,
                        username=self.username, password=self.password
                    )
                else:
                    self.tg = TrustGraph(
                        hosts=self.graph_host,
                        keyspace=v.metadata.user, table=v.metadata.collection,
                    )
            except Exception as e:
                print("Exception", e, flush=True)
                time.sleep(1)
                raise e

            self.table = table

        for t in v.triples:
            self.tg.insert(
                t.s.value,
                t.p.value,
                t.o.value
            )

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
        
        parser.add_argument(
            '--graph-username',
            default=None,
            help=f'Cassandra username'
        )
        
        parser.add_argument(
            '--graph-password',
            default=None,
            help=f'Cassandra password'
        )

def run():

    Processor.launch(module, __doc__)

