
"""
Stores knowledge-cores in Cassandra
"""

import json
import urllib.parse

from ... schema import Triples, GraphEmbeddings
from ... base import FlowProcessor, ConsumerSpec
from ... base.cassandra_config import add_cassandra_args, resolve_cassandra_config

from ... tables.knowledge import KnowledgeTableStore

default_ident = "kg-store"

keyspace = "knowledge"

class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")

        # Use helper to resolve configuration
        hosts, username, password, keyspace = resolve_cassandra_config(
            host=params.get("cassandra_host"),
            username=params.get("cassandra_username"),
            password=params.get("cassandra_password"),
            default_keyspace='knowledge'
        )

        super(Processor, self).__init__(
            **params | {
                "id": id,
                "cassandra_host": ','.join(hosts),
                "cassandra_username": username,
            }
        )

        self.register_specification(
            ConsumerSpec(
                name = "triples-input",
                schema = Triples,
                handler = self.on_triples
            )
        )

        self.register_specification(
            ConsumerSpec(
                name = "graph-embeddings-input",
                schema = GraphEmbeddings,
                handler = self.on_graph_embeddings
            )
        )

        self.table_store = KnowledgeTableStore(
            cassandra_host = hosts,
            cassandra_username = username,
            cassandra_password = password,
            keyspace = keyspace,
        )

    async def on_triples(self, msg, consumer, flow):

        v = msg.value()
        if v.triples:
            await self.table_store.add_triples(v)

    async def on_graph_embeddings(self, msg, consumer, flow):

        v = msg.value()
        if v.entities:
            await self.table_store.add_graph_embeddings(v)

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)
        add_cassandra_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

