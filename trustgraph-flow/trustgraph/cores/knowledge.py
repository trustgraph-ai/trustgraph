
from .. schema import KnowledgeResponse, Error
from .. knowledge import hash
from .. exceptions import RequestError
from .. tables.knowledge import KnowledgeTableStore
import base64

import uuid

class KnowledgeManager:

    def __init__(
            self, cassandra_host, cassandra_user, cassandra_password,
            keyspace,
    ):

        self.table_store = KnowledgeTableStore(
            cassandra_host, cassandra_user, cassandra_password, keyspace
        )

    async def delete_kg_core(self, request, respond):

        print("Deleting core...", flush=True)

        await self.table_store.delete_kg_core(
            request.user, request.id
        )

        await respond(
            KnowledgeResponse(
                error = None,
                ids = None,
                eos = False,
                triples = None,
                graph_embeddings = None,
            )
        )

    async def get_kg_core(self, request, respond):

        print("Get core...", flush=True)

        async def publish_triples(t):
            await respond(
                KnowledgeResponse(
                    error = None,
                    ids = None,
                    eos = False,
                    triples = t,
                    graph_embeddings = None,
                )
            )

        # Remove doc table row
        await self.table_store.get_triples(
            request.user,
            request.id,
            publish_triples,
        )

        async def publish_ge(g):
            await respond(
                KnowledgeResponse(
                    error = None,
                    ids = None,
                    eos = False,
                    triples = None,
                    graph_embeddings = g,
                )
            )

        # Remove doc table row
        await self.table_store.get_graph_embeddings(
            request.user,
            request.id,
            publish_ge,
        )

        print("Get complete", flush=True)

        await respond(
            KnowledgeResponse(
                error = None,
                ids = None,
                eos = True,
                triples = None,
                graph_embeddings = None,
            )
        )

    async def list_kg_cores(self, request, respond):

        ids = await self.table_store.list_kg_cores(request.user)

        await respond(
            KnowledgeResponse(
                error = None,
                ids = ids,
                eos = False,
                triples = None,
                graph_embeddings = None
            )
        )

    async def put_kg_core(self, request, respond):

        if request.triples:
            await self.table_store.add_triples(request.triples)

        if request.graph_embeddings:
            await self.table_store.add_graph_embeddings(
                request.graph_embeddings
            )

        await respond(
            KnowledgeResponse(
                error = None,
                ids = None,
                eos = False,
                triples = None,
                graph_embeddings = None
            )
        )

