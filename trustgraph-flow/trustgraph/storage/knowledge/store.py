
"""
Stores knowledge-cores in Cassandra
"""

import json
import urllib.parse

from ... schema import Triples, GraphEmbeddings
from ... base import FlowProcessor, ConsumerSpec

from ... tables.knowledge import KnowledgeTableStore

default_ident = "kg-store"

default_cassandra_host = "cassandra"
keyspace = "knowledge"

class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")

        cassandra_host = params.get("cassandra_host", default_cassandra_host)
        cassandra_user = params.get("cassandra_user")
        cassandra_password = params.get("cassandra_password")

        super(Processor, self).__init__(
            **params | {
                "id": id,
                "cassandra_host": cassandra_host,
                "cassandra_user": cassandra_user,
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
            cassandra_host = cassandra_host.split(","),
            cassandra_user = cassandra_user,
            cassandra_password = cassandra_password,
            keyspace = keyspace,
        )

    async def on_triples(self, msg, consumer, flow):

        v = msg.value()
        await self.table_store.add_triples(v)

    async def on_graph_embeddings(self, msg, consumer, flow):

        v = msg.value()
        await self.table_store.add_graph_embeddings(v)

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

