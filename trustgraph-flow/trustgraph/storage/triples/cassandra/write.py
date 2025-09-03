
"""
Graph writer.  Input is graph edge.  Writes edges to Cassandra graph.
"""

import pulsar
import base64
import os
import argparse
import time
import logging

from .... direct.cassandra import TrustGraph
from .... base import TriplesStoreService
from .... base.cassandra_config import add_cassandra_args, resolve_cassandra_config

# Module logger
logger = logging.getLogger(__name__)

default_ident = "triples-write"


class Processor(TriplesStoreService):

    def __init__(self, **params):
        
        id = params.get("id", default_ident)

        # Get Cassandra parameters
        cassandra_host = params.get("cassandra_host")
        cassandra_username = params.get("cassandra_username")
        cassandra_password = params.get("cassandra_password")

        # Resolve configuration with environment variable fallback
        hosts, username, password = resolve_cassandra_config(
            host=cassandra_host,
            username=cassandra_username,
            password=cassandra_password
        )

        super(Processor, self).__init__(
            **params | {
                "cassandra_host": ','.join(hosts),
                "cassandra_username": username
            }
        )
        
        self.cassandra_host = hosts
        self.cassandra_username = username
        self.cassandra_password = password
        self.table = None

    async def store_triples(self, message):

        table = (message.metadata.user, message.metadata.collection)

        if self.table is None or self.table != table:

            self.tg = None

            try:
                if self.cassandra_username and self.cassandra_password:
                    self.tg = TrustGraph(
                        hosts=self.cassandra_host,
                        keyspace=message.metadata.user,
                        table=message.metadata.collection,
                        username=self.cassandra_username, password=self.cassandra_password
                    )
                else:
                    self.tg = TrustGraph(
                        hosts=self.cassandra_host,
                        keyspace=message.metadata.user,
                        table=message.metadata.collection,
                    )
            except Exception as e:
                logger.error(f"Exception: {e}", exc_info=True)
                time.sleep(1)
                raise e

            self.table = table

        for t in message.triples:
            self.tg.insert(
                t.s.value,
                t.p.value,
                t.o.value
            )

    @staticmethod
    def add_args(parser):

        TriplesStoreService.add_args(parser)
        add_cassandra_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

