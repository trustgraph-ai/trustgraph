from .. schema import LibrarianRequest, LibrarianResponse, Error, Triple
from .. knowledge import hash
from .. exceptions import RequestError
from . table_store import TableStore
from . blob_store import BlobStore

import uuid

class Librarian:

    def __init__(
            self,
            cassandra_host, cassandra_user, cassandra_password,
            minio_host, minio_access_key, minio_secret_key,
            bucket_name, keyspace, load_document, load_text,
    ):

        self.blob_store = BlobStore(
            minio_host, minio_access_key, minio_secret_key, bucket_name
        )

        self.table_store = TableStore(
            cassandra_host, cassandra_user, cassandra_password, keyspace
        )

        self.load_document = load_document
        self.load_text = load_text

    async def add(self, document):

        if document.kind not in (
                "text/plain", "application/pdf"
        ):
            raise RequestError("Invalid document kind: " + document.kind)

        # Create object ID as a hash of the document
        object_id = uuid.UUID(hash(document.document))

        self.blob_store.add(object_id, document.document, document.kind)

        self.table_store.add(object_id, document)

        if document.kind == "application/pdf":
            await self.load_document(document)
        elif document.kind == "text/plain":
            await self.load_text(document)

        print("Add complete", flush=True)

        return LibrarianResponse(
            error = None,
            document = None,
            info = None,
        )

    async def list(self, user, collection):

        print("list")

        info = self.table_store.list(user, collection)

        print(">>", info)

        return LibrarianResponse(
            error = None,
            document = None,
            info = info,
        )

    def handle_triples(self, m):
        self.table_store.add_triples(m)

    def handle_graph_embeddings(self, m):
        self.table_store.add_graph_embeddings(m)

    def handle_document_embeddings(self, m):
        self.table_store.add_document_embeddings(m)
        

    def handle_triples(self, m):
        self.table_store.add_triples(m)

    def handle_graph_embeddings(self, m):
        self.table_store.add_graph_embeddings(m)

    def handle_document_embeddings(self, m):
        self.table_store.add_document_embeddings(m)

