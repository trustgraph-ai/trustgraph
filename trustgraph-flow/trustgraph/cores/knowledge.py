
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

    async def delete_kg_core(self, request):

        print("Updating doc...")

        # You can't update the document ID, user or kind.

        if not await self.table_store.document_exists(
                request.document_metadata.user,
                request.document_metadata.id
        ):
            raise RuntimeError("Document does not exist")

        await self.table_store.update_document(request.document_metadata)

        print("Update complete", flush=True)

        return LibrarianResponse(
            error = None,
            document_metadata = None,
            content = None,
            document_metadatas = None,
            processing_metadatas = None,
        )

    async def fetch_kg_core(self, request, flow):

        print("Fetch core...")

        async def publish(obj):
            print(obj)
#            await publisher.send(triples)

        # Remove doc table row
        await self.table_store.get_triples(
            request.user,
            request.id,
            publish
        )

        async def publish_ge(obj):
            print(obj)

        # Remove doc table row
        await self.table_store.get_graph_embeddings(
            request.user,
            request.id,
            publish
        )

        print("Fetch complete", flush=True)

        return KnowledgeResponse(
            error = None,
            ids = None,
            eos = True,
            triples = None,
            graph_embeddings = None,
        )

    async def list_kg_cores(self, request, flow):

        ids = await self.table_store.list_kg_cores(request.user)

        return KnowledgeResponse(
            error = None,
            ids = ids,
            eos = False,
            triples = None,
            graph_embeddings = None
        )

