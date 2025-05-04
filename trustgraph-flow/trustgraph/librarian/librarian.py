
from .. schema import LibrarianRequest, LibrarianResponse, Error, Triple
from .. knowledge import hash
from .. exceptions import RequestError
from . table_store import TableStore
from . blob_store import BlobStore
import base64

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

        if request.document_metadata.kind not in (
                "text/plain", "application/pdf"
        ):
            raise RequestError(
                "Invalid document kind: " + request.document_metadata.kind
            )

        print("Existence test...")
        if await self.table_store.document_exists(
                request.document_metadata.user,
                request.document_metadata.id
        ):
            raise RuntimeError("Document already exists")

        # Create object ID for blob
        object_id = uuid.uuid4()

        print("OID", object_id)
        print(request.content)
        print("CONT", base64.b64decode(request.content))


        print("Add blob...")

        await self.blob_store.add(
            object_id, base64.b64decode(request.content),
            request.document_metadata.kind
        )

        print("Add table...")

        await self.table_store.add_document(
            request.document_metadata, object_id
        )

        print("Add complete", flush=True)

        return LibrarianResponse(
            error = None,
            document_metadata = None,
            content = None,
            document_metadatas = None,
            processing_metadatas = None,
        )

    async def remove_document(self, request):

        print("REMOVING...")

        if not await self.table_store.document_exists(
                request.user,
                request.document_id,
        ):
            raise RuntimeError("Document does not exist")

        object_id = await self.table_store.get_document_object_id(
            request.user,
            request.document_id
        )

        # Remove blob...
        await self.blob_store.remove(object_id)

        # Remove doc table row
        await self.table_store.remove_document(
            request.user,
            request.document_id
        )

        print("Remove complete", flush=True)

        return LibrarianResponse(
            error = None,
            document_metadata = None,
            content = None,
            document_metadatas = None,
            processing_metadatas = None,
        )

    async def update_document(self, request):

        print("UPDATING...")

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

    async def get_document_metadata(self, request):

        print("GET DOC...")

        doc = await self.table_store.get_document(
            request.user,
            request.document_id
        )

        print("Get complete", flush=True)

        return LibrarianResponse(
            error = None,
            document_metadata = doc,
            content = None,
            document_metadatas = None,
            processing_metadatas = None,
        )

    async def get_document_content(self, request):

        print("GET DOC CONTENT...")

        object_id = await self.table_store.get_document_object_id(
            request.user,
            request.document_id
        )

        print("Now", object_id)

        content = await self.blob_store.get(
            object_id
        )

        print("Get complete", flush=True)

        return LibrarianResponse(
            error = None,
            document_metadata = None,
            content = base64.b64encode(content),
            document_metadatas = None,
            processing_metadatas = None,
        )

    async def add_processing(self, request):
        raise RuntimeError("Not implemented")

        # if document.kind == "application/pdf":
        #     await self.load_document(document)
        # elif document.kind == "text/plain":
        #     await self.load_text(document)

    async def remove_processing(self, request):
        raise RuntimeError("Not implemented")

    async def list_documents(self, request):

        docs = await self.table_store.list_documents(request.user)

        print(docs)

        return LibrarianResponse(
            error = None,
            document_metadata = None,
            content = None,
            document_metadatas = docs,
            processing_metadatas = None,
        )

    async def list_processing(self, request):

        procs = await self.table_store.list_processing(request.user)

        print(procs)

        return LibrarianResponse(
            error = None,
            document_metadata = None,
            content = None,
            document_metadatas = None,
            processing_metadatas = procs,
        )

