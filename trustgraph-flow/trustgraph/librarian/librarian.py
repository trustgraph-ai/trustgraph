
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

    async def add_document(self, request):

        print(request)

        if request.document_metadata.kind not in (
                "text/plain", "application/pdf"
        ):
            raise RequestError(
                "Invalid document kind: " + request.document_metadata.kind
            )

        # Create object ID for blob
        object_id = uuid.uuid4()

        print("HERE")
        self.blob_store.add(object_id, request.content,
                            request.document_metadata.kind)

        self.table_store.add_document(request.document_metadata, object_id)
        print("HERE2")

        # if document.kind == "application/pdf":
        #     await self.load_document(document)
        # elif document.kind == "text/plain":
        #     await self.load_text(document)

        print("Add complete", flush=True)

        return LibrarianResponse(
            error = None,
            document_metadata = None,
            content = None,
            document_metadatas = None,
            processing_metadatas = None,
        )

    async def remove_document(self, request):
        raise RuntimeError("Not implemented")

    async def update_document(self, request):
        raise RuntimeError("Not implemented")

    async def get_document_metadata(self, request):
        raise RuntimeError("Not implemented")

    async def get_document_content(self, request):
        raise RuntimeError("Not implemented")

    async def add_processing(self, request):
        raise RuntimeError("Not implemented")

    async def remove_processing(self, request):
        raise RuntimeError("Not implemented")

    async def list_documents(self, request):
        raise RuntimeError("Not implemented")

    async def list_processing(self, request):
        raise RuntimeError("Not implemented")

    async def list(self, user, collection):

        raise RuntimeError("Not implemented")



        print("list")

        info = self.table_store.list(user, collection)

        print(">>", info)

        return LibrarianResponse(
            error = None,
            document = None,
            info = info,
        )

