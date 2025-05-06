
from .. schema import LibrarianRequest, LibrarianResponse, Error, Triple
from .. knowledge import hash
from .. exceptions import RequestError
from .. tables.library import LibraryTableStore
from . blob_store import BlobStore
import base64

import uuid

class Librarian:

    def __init__(
            self,
            cassandra_host, cassandra_user, cassandra_password,
            minio_host, minio_access_key, minio_secret_key,
            bucket_name, keyspace, load_document,
    ):

        self.blob_store = BlobStore(
            minio_host, minio_access_key, minio_secret_key, bucket_name
        )

        self.table_store = TableStore(
            cassandra_host, cassandra_user, cassandra_password, keyspace
        )

        self.load_document = load_document

    async def add_document(self, request):

        if request.document_metadata.kind not in (
                "text/plain", "application/pdf"
        ):
            raise RequestError(
                "Invalid document kind: " + request.document_metadata.kind
            )

        if await self.table_store.document_exists(
                request.document_metadata.user,
                request.document_metadata.id
        ):
            raise RuntimeError("Document already exists")

        # Create object ID for blob
        object_id = uuid.uuid4()

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

        print("Removing doc...")

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

    async def get_document_metadata(self, request):

        print("Get doc...")

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

        print("Get doc content...")

        object_id = await self.table_store.get_document_object_id(
            request.user,
            request.document_id
        )

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

        print("Add processing")

        if await self.table_store.processing_exists(
                request.processing_metadata.user,
                request.processing_metadata.id
        ):
            raise RuntimeError("Processing already exists")

        doc = await self.table_store.get_document(
            request.processing_metadata.user,
            request.processing_metadata.document_id
        )

        object_id = await self.table_store.get_document_object_id(
            request.processing_metadata.user,
            request.processing_metadata.document_id
        )

        content = await self.blob_store.get(
            object_id
        )

        print("Got content")

        print("Add processing...")

        await self.table_store.add_processing(request.processing_metadata)

        print("Invoke document processing...")

        await self.load_document(
            document = doc,
            processing = request.processing_metadata,
            content = content,
        )

        print("Add complete", flush=True)

        return LibrarianResponse(
            error = None,
            document_metadata = None,
            content = None,
            document_metadatas = None,
            processing_metadatas = None,
        )

    async def remove_processing(self, request):

        print("Removing processing...")

        if not await self.table_store.processing_exists(
                request.user,
                request.processing_id,
        ):
            raise RuntimeError("Processing object does not exist")

        # Remove doc table row
        await self.table_store.remove_processing(
            request.user,
            request.processing_id
        )

        print("Remove complete", flush=True)

        return LibrarianResponse(
            error = None,
            document_metadata = None,
            content = None,
            document_metadatas = None,
            processing_metadatas = None,
        )

    async def list_documents(self, request):

        docs = await self.table_store.list_documents(request.user)

        return LibrarianResponse(
            error = None,
            document_metadata = None,
            content = None,
            document_metadatas = docs,
            processing_metadatas = None,
        )

    async def list_processing(self, request):

        procs = await self.table_store.list_processing(request.user)

        return LibrarianResponse(
            error = None,
            document_metadata = None,
            content = None,
            document_metadatas = None,
            processing_metadatas = procs,
        )

