
from .. schema import LibrarianRequest, LibrarianResponse, Error, Triple
from .. schema import UploadSession
from .. knowledge import hash
from .. exceptions import RequestError
from .. tables.library import LibraryTableStore
from . blob_store import BlobStore
import base64
import json
import logging
import math
import time

import uuid

# Module logger
logger = logging.getLogger(__name__)

# Default chunk size for multipart uploads
DEFAULT_CHUNK_SIZE = 2 * 1024 * 1024  # 2MB default

class Librarian:

    def __init__(
            self,
            cassandra_host, cassandra_username, cassandra_password,
            object_store_endpoint, object_store_access_key, object_store_secret_key,
            bucket_name, keyspace, load_document,
            object_store_use_ssl=False, object_store_region=None,
            min_chunk_size=1,  # Default: no minimum (for Garage)
    ):

        self.blob_store = BlobStore(
            object_store_endpoint, object_store_access_key, object_store_secret_key, bucket_name,
            use_ssl=object_store_use_ssl, region=object_store_region,
        )

        self.table_store = LibraryTableStore(
            cassandra_host, cassandra_username, cassandra_password, keyspace
        )

        self.load_document = load_document
        self.min_chunk_size = min_chunk_size

    async def add_document(self, request, workspace):

        if not request.document_metadata.kind:
            raise RequestError("Document kind (MIME type) is required")

        if await self.table_store.document_exists(
                workspace,
                request.document_metadata.id
        ):
            raise RuntimeError("Document already exists")

        # Create object ID for blob
        object_id = uuid.uuid4()

        logger.debug("Adding blob...")

        await self.blob_store.add(
            object_id, base64.b64decode(request.content),
            request.document_metadata.kind
        )

        logger.debug("Adding to table...")

        await self.table_store.add_document(
            workspace, request.document_metadata, object_id
        )

        logger.debug("Add complete")

        return LibrarianResponse()

    async def remove_document(self, request, workspace):

        logger.debug("Removing document...")

        if not await self.table_store.document_exists(
                workspace,
                request.document_id,
        ):
            raise RuntimeError("Document does not exist")

        # First, cascade delete all child documents
        children = await self.table_store.list_children(request.document_id)
        for child in children:
            logger.debug(f"Cascade deleting child document {child.id}")
            try:
                child_object_id = await self.table_store.get_document_object_id(
                    workspace,
                    child.id
                )
                await self.blob_store.remove(child_object_id)
                await self.table_store.remove_document(workspace, child.id)
            except Exception as e:
                logger.warning(f"Failed to delete child document {child.id}: {e}")

        # Now remove the parent document
        object_id = await self.table_store.get_document_object_id(
            workspace,
            request.document_id
        )

        # Remove blob...
        await self.blob_store.remove(object_id)

        # Remove doc table row
        await self.table_store.remove_document(
            workspace,
            request.document_id
        )

        logger.debug("Remove complete")

        return LibrarianResponse()

    async def update_document(self, request, workspace):

        logger.debug("Updating document...")

        # You can't update the document ID, workspace or kind.

        if not await self.table_store.document_exists(
                workspace,
                request.document_metadata.id
        ):
            raise RuntimeError("Document does not exist")

        await self.table_store.update_document(workspace, request.document_metadata)

        logger.debug("Update complete")

        return LibrarianResponse()

    async def get_document_metadata(self, request, workspace):

        logger.debug("Getting document metadata...")

        doc = await self.table_store.get_document(
            workspace,
            request.document_id
        )

        logger.debug("Get complete")

        return LibrarianResponse(
            error = None,
            document_metadata = doc,
            content = None,
        )

    async def get_document_content(self, request, workspace):

        logger.debug("Getting document content...")

        object_id = await self.table_store.get_document_object_id(
            workspace,
            request.document_id
        )

        content = await self.blob_store.get(
            object_id
        )

        logger.debug("Get complete")

        return LibrarianResponse(
            error = None,
            document_metadata = None,
            content = base64.b64encode(content),
        )

    async def add_processing(self, request, workspace):

        logger.debug("Adding processing metadata...")

        if not request.processing_metadata.collection:
            raise RuntimeError("Collection parameter is required")

        if await self.table_store.processing_exists(
                workspace,
                request.processing_metadata.id
        ):
            raise RuntimeError("Processing already exists")

        doc = await self.table_store.get_document(
            workspace,
            request.processing_metadata.document_id
        )

        object_id = await self.table_store.get_document_object_id(
            workspace,
            request.processing_metadata.document_id
        )

        content = await self.blob_store.get(
            object_id
        )

        logger.debug("Retrieved content")

        logger.debug("Adding processing to table...")

        await self.table_store.add_processing(workspace, request.processing_metadata)

        logger.debug("Invoking document processing...")

        await self.load_document(
            document = doc,
            processing = request.processing_metadata,
            content = content,
            workspace = workspace,
        )

        logger.debug("Add complete")

        return LibrarianResponse()

    async def remove_processing(self, request, workspace):

        logger.debug("Removing processing metadata...")

        if not await self.table_store.processing_exists(
                workspace,
                request.processing_id,
        ):
            raise RuntimeError("Processing object does not exist")

        # Remove doc table row
        await self.table_store.remove_processing(
            workspace,
            request.processing_id
        )

        logger.debug("Remove complete")

        return LibrarianResponse()

    async def list_documents(self, request, workspace):

        docs = await self.table_store.list_documents(workspace)

        # Filter out child documents and answer documents by default
        include_children = getattr(request, 'include_children', False)
        if not include_children:
            docs = [
                doc for doc in docs
                if not doc.parent_id  # Only include top-level documents
                and doc.document_type != "answer"  # Exclude GraphRAG answers
            ]

        return LibrarianResponse(
            document_metadatas = docs,
        )

    async def list_processing(self, request, workspace):

        procs = await self.table_store.list_processing(workspace)

        return LibrarianResponse(
            processing_metadatas = procs,
        )

    # Chunked upload operations

    async def begin_upload(self, request, workspace):
        """
        Initialize a chunked upload session.

        Creates an S3 multipart upload and stores session state in Cassandra.
        """
        logger.info(f"Beginning chunked upload for document {request.document_metadata.id}")

        if not request.document_metadata.kind:
            raise RequestError("Document kind (MIME type) is required")

        if await self.table_store.document_exists(
                workspace,
                request.document_metadata.id
        ):
            raise RequestError("Document already exists")

        # Validate sizes
        total_size = request.total_size
        if total_size <= 0:
            raise RequestError("total_size must be positive")

        # Use provided chunk size or default
        chunk_size = request.chunk_size if request.chunk_size > 0 else DEFAULT_CHUNK_SIZE
        if chunk_size < self.min_chunk_size:
            raise RequestError(
                f"Chunk size {chunk_size} is below minimum {self.min_chunk_size}"
            )

        # Calculate total chunks
        total_chunks = math.ceil(total_size / chunk_size)

        # Generate IDs
        upload_id = str(uuid.uuid4())
        object_id = uuid.uuid4()

        # Create S3 multipart upload
        s3_upload_id = await self.blob_store.create_multipart_upload(
            object_id, request.document_metadata.kind
        )

        # Serialize document metadata for storage
        doc_meta_json = json.dumps({
            "id": request.document_metadata.id,
            "time": request.document_metadata.time,
            "kind": request.document_metadata.kind,
            "title": request.document_metadata.title,
            "comments": request.document_metadata.comments,
            "tags": request.document_metadata.tags,
        })

        # Store session in Cassandra
        await self.table_store.create_upload_session(
            upload_id=upload_id,
            workspace=workspace,
            document_id=request.document_metadata.id,
            document_metadata=doc_meta_json,
            s3_upload_id=s3_upload_id,
            object_id=object_id,
            total_size=total_size,
            chunk_size=chunk_size,
            total_chunks=total_chunks,
        )

        logger.info(f"Created upload session {upload_id} with {total_chunks} chunks")

        return LibrarianResponse(
            error=None,
            upload_id=upload_id,
            chunk_size=chunk_size,
            total_chunks=total_chunks,
        )

    async def upload_chunk(self, request, workspace):
        """
        Upload a single chunk of a document.

        Forwards the chunk to S3 and updates session state.
        """
        logger.debug(f"Uploading chunk {request.chunk_index} for upload {request.upload_id}")

        # Get session
        session = await self.table_store.get_upload_session(request.upload_id)
        if session is None:
            raise RequestError("Upload session not found or expired")

        # Validate ownership
        if session["workspace"] != workspace:
            raise RequestError("Not authorized to upload to this session")

        # Validate chunk index
        if request.chunk_index < 0 or request.chunk_index >= session["total_chunks"]:
            raise RequestError(
                f"Invalid chunk index {request.chunk_index}, "
                f"must be 0-{session['total_chunks']-1}"
            )

        # Decode content
        content = base64.b64decode(request.content)

        # Upload to S3 (part numbers are 1-indexed in S3)
        part_number = request.chunk_index + 1
        etag = await self.blob_store.upload_part(
            object_id=session["object_id"],
            upload_id=session["s3_upload_id"],
            part_number=part_number,
            data=content,
        )

        # Update session with chunk info
        await self.table_store.update_upload_session_chunk(
            upload_id=request.upload_id,
            chunk_index=request.chunk_index,
            etag=etag,
        )

        # Calculate progress
        chunks_received = session["chunks_received"]
        # Add this chunk if not already present
        if request.chunk_index not in chunks_received:
            chunks_received[request.chunk_index] = etag

        num_chunks_received = len(chunks_received) + 1  # +1 for this chunk
        bytes_received = num_chunks_received * session["chunk_size"]
        # Adjust for last chunk potentially being smaller
        if bytes_received > session["total_size"]:
            bytes_received = session["total_size"]

        logger.debug(f"Chunk {request.chunk_index} uploaded, {num_chunks_received}/{session['total_chunks']} complete")

        return LibrarianResponse(
            error=None,
            upload_id=request.upload_id,
            chunk_index=request.chunk_index,
            chunks_received=num_chunks_received,
            total_chunks=session["total_chunks"],
            bytes_received=bytes_received,
            total_bytes=session["total_size"],
        )

    async def complete_upload(self, request, workspace):
        """
        Finalize a chunked upload and create the document.

        Completes the S3 multipart upload and creates the document metadata.
        """
        logger.info(f"Completing upload {request.upload_id}")

        # Get session
        session = await self.table_store.get_upload_session(request.upload_id)
        if session is None:
            raise RequestError("Upload session not found or expired")

        # Validate ownership
        if session["workspace"] != workspace:
            raise RequestError("Not authorized to complete this upload")

        # Verify all chunks received
        chunks_received = session["chunks_received"]
        if len(chunks_received) != session["total_chunks"]:
            missing = [
                i for i in range(session["total_chunks"])
                if i not in chunks_received
            ]
            raise RequestError(
                f"Missing chunks: {missing[:10]}{'...' if len(missing) > 10 else ''}"
            )

        # Build parts list for S3 (sorted by part number)
        parts = [
            (chunk_index + 1, etag)  # S3 part numbers are 1-indexed
            for chunk_index, etag in sorted(chunks_received.items())
        ]

        # Complete S3 multipart upload
        await self.blob_store.complete_multipart_upload(
            object_id=session["object_id"],
            upload_id=session["s3_upload_id"],
            parts=parts,
        )

        # Parse document metadata from session
        doc_meta_dict = json.loads(session["document_metadata"])

        # Create DocumentMetadata object
        from .. schema import DocumentMetadata
        doc_metadata = DocumentMetadata(
            id=doc_meta_dict["id"],
            time=doc_meta_dict.get("time", int(time.time())),
            kind=doc_meta_dict["kind"],
            title=doc_meta_dict.get("title", ""),
            comments=doc_meta_dict.get("comments", ""),
            tags=doc_meta_dict.get("tags", []),
            metadata=[],  # Triples not supported in chunked upload yet
        )

        # Add document to table
        workspace = session["workspace"]
        await self.table_store.add_document(workspace, doc_metadata, session["object_id"])

        # Delete upload session
        await self.table_store.delete_upload_session(request.upload_id)

        logger.info(f"Upload {request.upload_id} completed, document {doc_metadata.id} created")

        return LibrarianResponse(
            error=None,
            document_id=doc_metadata.id,
            object_id=str(session["object_id"]),
        )

    async def abort_upload(self, request, workspace):
        """
        Cancel a chunked upload and clean up resources.
        """
        logger.info(f"Aborting upload {request.upload_id}")

        # Get session
        session = await self.table_store.get_upload_session(request.upload_id)
        if session is None:
            raise RequestError("Upload session not found or expired")

        # Validate ownership
        if session["workspace"] != workspace:
            raise RequestError("Not authorized to abort this upload")

        # Abort S3 multipart upload
        await self.blob_store.abort_multipart_upload(
            object_id=session["object_id"],
            upload_id=session["s3_upload_id"],
        )

        # Delete session from Cassandra
        await self.table_store.delete_upload_session(request.upload_id)

        logger.info(f"Upload {request.upload_id} aborted")

        return LibrarianResponse(error=None)

    async def get_upload_status(self, request, workspace):
        """
        Get the status of an in-progress upload.
        """
        logger.debug(f"Getting status for upload {request.upload_id}")

        # Get session
        session = await self.table_store.get_upload_session(request.upload_id)
        if session is None:
            return LibrarianResponse(
                error=None,
                upload_id=request.upload_id,
                upload_state="expired",
            )

        # Validate ownership
        if session["workspace"] != workspace:
            raise RequestError("Not authorized to view this upload")

        chunks_received = session["chunks_received"]
        received_list = sorted(chunks_received.keys())
        missing_list = [
            i for i in range(session["total_chunks"])
            if i not in chunks_received
        ]

        bytes_received = len(chunks_received) * session["chunk_size"]
        if bytes_received > session["total_size"]:
            bytes_received = session["total_size"]

        return LibrarianResponse(
            error=None,
            upload_id=request.upload_id,
            upload_state="in-progress",
            received_chunks=received_list,
            missing_chunks=missing_list,
            chunks_received=len(chunks_received),
            total_chunks=session["total_chunks"],
            bytes_received=bytes_received,
            total_bytes=session["total_size"],
        )

    async def list_uploads(self, request, workspace):
        """
        List all in-progress uploads for a workspace.
        """
        logger.debug(f"Listing uploads for workspace {workspace}")

        sessions = await self.table_store.list_upload_sessions(workspace)

        upload_sessions = [
            UploadSession(
                upload_id=s["upload_id"],
                document_id=s["document_id"],
                document_metadata_json=s.get("document_metadata", ""),
                total_size=s["total_size"],
                chunk_size=s["chunk_size"],
                total_chunks=s["total_chunks"],
                chunks_received=s["chunks_received"],
                created_at=str(s.get("created_at", "")),
            )
            for s in sessions
        ]

        return LibrarianResponse(
            error=None,
            upload_sessions=upload_sessions,
        )

    # Child document operations

    async def add_child_document(self, request, workspace):
        """
        Add a child document linked to a parent document.

        Child documents are typically extracted content (e.g., pages from a PDF).
        They have a parent_id pointing to the source document and document_type
        set to "extracted".
        """
        logger.info(f"Adding child document {request.document_metadata.id} "
                   f"for parent {request.document_metadata.parent_id}")

        if not request.document_metadata.parent_id:
            raise RequestError("parent_id is required for child documents")

        # Verify parent exists
        if not await self.table_store.document_exists(
                workspace,
                request.document_metadata.parent_id
        ):
            raise RequestError(
                f"Parent document {request.document_metadata.parent_id} does not exist"
            )

        if await self.table_store.document_exists(
                workspace,
                request.document_metadata.id
        ):
            raise RequestError("Document already exists")

        # Set document_type if not specified by caller
        # Valid types: "page", "chunk", or "extracted" (legacy)
        if not request.document_metadata.document_type or request.document_metadata.document_type == "source":
            request.document_metadata.document_type = "extracted"

        # Create object ID for blob
        object_id = uuid.uuid4()

        logger.debug("Adding blob...")

        await self.blob_store.add(
            object_id, base64.b64decode(request.content),
            request.document_metadata.kind
        )

        logger.debug("Adding to table...")

        await self.table_store.add_document(
            workspace, request.document_metadata, object_id
        )

        logger.debug("Add child document complete")

        return LibrarianResponse(
            error=None,
            document_id=request.document_metadata.id,
        )

    async def list_children(self, request, workspace):
        """
        List all child documents for a given parent document.
        """
        logger.debug(f"Listing children for parent {request.document_id}")

        children = await self.table_store.list_children(request.document_id)

        return LibrarianResponse(
            error=None,
            document_metadatas=children,
        )

    async def stream_document(self, request, workspace):
        """
        Stream document content in chunks.

        This is an async generator that yields document content in smaller chunks,
        allowing memory-efficient processing of large documents. Each yielded
        response includes chunk_index and total_chunks for tracking progress.
        Completion is determined by chunk_index reaching total_chunks - 1.
        """
        logger.debug(f"Streaming document {request.document_id}")

        DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1MB default

        chunk_size = request.chunk_size if request.chunk_size > 0 else DEFAULT_CHUNK_SIZE
        if chunk_size < self.min_chunk_size:
            raise RequestError(
                f"Chunk size {chunk_size} is below minimum {self.min_chunk_size}"
            )

        object_id = await self.table_store.get_document_object_id(
            workspace,
            request.document_id
        )

        # Get size via stat (no content download)
        total_size = await self.blob_store.get_size(object_id)
        total_chunks = math.ceil(total_size / chunk_size)

        # Stream all chunks
        for chunk_index in range(total_chunks):
            # Calculate byte range
            offset = chunk_index * chunk_size
            length = min(chunk_size, total_size - offset)

            # Fetch only the requested range
            chunk_content = await self.blob_store.get_range(object_id, offset, length)

            is_last = (chunk_index == total_chunks - 1)

            logger.debug(f"Streaming chunk {chunk_index + 1}/{total_chunks}, "
                        f"bytes {offset}-{offset + length} of {total_size}")

            yield LibrarianResponse(
                error=None,
                content=base64.b64encode(chunk_content),
                chunk_index=chunk_index,
                chunks_received=chunk_index + 1,
                total_chunks=total_chunks,
                bytes_received=offset + length,
                total_bytes=total_size,
                is_final=is_last,
            )
