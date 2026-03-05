"""
TrustGraph Document Library Management

This module provides interfaces for managing documents in the TrustGraph library,
including document storage, metadata management, and processing workflow coordination.
"""

import datetime
import math
import time
import base64
import logging

from . types import DocumentMetadata, ProcessingMetadata, Triple
from .. knowledge import hash, Uri, Literal, QuotedTriple
from .. schema import IRI, LITERAL, TRIPLE
from . exceptions import *

logger = logging.getLogger(__name__)

# Threshold for switching to chunked upload (2MB)
# Lower threshold provides progress feedback and resumability on slower connections
CHUNKED_UPLOAD_THRESHOLD = 2 * 1024 * 1024

# Default chunk size (5MB - S3 multipart minimum)
DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024


def to_value(x):
    """Convert wire format to Uri, Literal, or QuotedTriple."""
    if x.get("t") == IRI:
        return Uri(x.get("i", ""))
    elif x.get("t") == LITERAL:
        return Literal(x.get("v", ""))
    elif x.get("t") == TRIPLE:
        # Parse the nested triple from JSON or structured data
        triple_data = x.get("v", "")
        if isinstance(triple_data, str):
            import json
            try:
                triple_data = json.loads(triple_data)
            except json.JSONDecodeError:
                return Literal(triple_data)
        if isinstance(triple_data, dict):
            return QuotedTriple(
                s=to_value(triple_data.get("s", {})),
                p=to_value(triple_data.get("p", {})),
                o=to_value(triple_data.get("o", {})),
            )
        return Literal(str(triple_data))
    # Fallback for any other type
    return Literal(x.get("v", x.get("i", "")))


def from_value(v):
    """Convert Uri, Literal, or QuotedTriple to wire format."""
    if isinstance(v, Uri):
        return {"t": IRI, "i": str(v)}
    elif isinstance(v, QuotedTriple):
        import json
        return {
            "t": TRIPLE,
            "v": json.dumps({
                "s": from_value(v.s),
                "p": from_value(v.p),
                "o": from_value(v.o),
            })
        }
    else:
        return {"t": LITERAL, "v": str(v)}

class Library:
    """
    Document library management client.

    Provides methods for managing documents in the TrustGraph library, including
    adding, retrieving, updating, and removing documents, as well as managing
    document processing workflows.
    """

    def __init__(self, api):
        """
        Initialize Library client.

        Args:
            api: Parent Api instance for making requests
        """
        self.api = api

    def request(self, request):
        """
        Make a library-scoped API request.

        Args:
            request: Request payload dictionary

        Returns:
            dict: Response object
        """
        return self.api.request(f"librarian", request)

    def add_document(
            self, document, id, metadata, user, title, comments,
            kind="text/plain", tags=[], on_progress=None,
    ):
        """
        Add a document to the library.

        Stores a document with associated metadata in the library for
        retrieval and processing. For large documents (> 10MB), automatically
        uses chunked upload for better reliability and progress tracking.

        Args:
            document: Document content as bytes
            id: Document identifier (auto-generated if None)
            metadata: Document metadata as list of Triple objects or object with emit method
            user: User/owner identifier
            title: Document title
            comments: Document description or comments
            kind: MIME type of the document (default: "text/plain")
            tags: List of tags for categorization (default: [])
            on_progress: Optional callback(bytes_sent, total_bytes) for progress updates

        Returns:
            dict: Response from the add operation

        Raises:
            RuntimeError: If metadata is provided without an id

        Example:
            ```python
            library = api.library()

            # Add a PDF document
            with open("research.pdf", "rb") as f:
                library.add_document(
                    document=f.read(),
                    id="research-001",
                    metadata=[],
                    user="trustgraph",
                    title="Research Paper",
                    comments="Key findings in quantum computing",
                    kind="application/pdf",
                    tags=["research", "physics"]
                )

            # Add a large document with progress tracking
            def progress(sent, total):
                print(f"Uploaded {sent}/{total} bytes ({100*sent//total}%)")

            with open("large_document.pdf", "rb") as f:
                library.add_document(
                    document=f.read(),
                    id="large-doc-001",
                    metadata=[],
                    user="trustgraph",
                    title="Large Document",
                    comments="A very large document",
                    kind="application/pdf",
                    on_progress=progress
                )
            ```
        """

        if id is None:

            if metadata is not None:

                # Situation makes no sense.  What can the metadata possibly
                # mean if the caller doesn't know the document ID.
                # Metadata should relate to the document by ID
                raise RuntimeError("Can't specify metadata without id")

            id = hash(document)

        if not title: title = ""
        if not comments: comments = ""

        # Check if we should use chunked upload
        if len(document) >= CHUNKED_UPLOAD_THRESHOLD:
            return self._add_document_chunked(
                document=document,
                id=id,
                metadata=metadata,
                user=user,
                title=title,
                comments=comments,
                kind=kind,
                tags=tags,
                on_progress=on_progress,
            )

        # Small document: use single operation (existing behavior)
        triples = []

        def emit(t):
            triples.append(t)

        if metadata:
            if isinstance(metadata, list):
                triples = [
                    {
                        "s": from_value(t.s),
                        "p": from_value(t.p),
                        "o": from_value(t.o),
                    }
                    for t in metadata
                ]
            elif hasattr(metadata, "emit"):
                metadata.emit(
                    lambda t: triples.append({
                        "s": from_value(t["s"]),
                        "p": from_value(t["p"]),
                        "o": from_value(t["o"]),
                    })
                )
            else:
                raise RuntimeError("metadata should be a list of Triples or have an emit method")

        input = {
            "operation": "add-document",
            "document-metadata": {
                "id": id,
                "time": int(time.time()),
                "kind": kind,
                "title": title,
                "comments": comments,
                "metadata": triples,
                "user": user,
                "tags": tags
            },
            "content": base64.b64encode(document).decode("utf-8"),
        }

        return self.request(input)

    def _add_document_chunked(
            self, document, id, metadata, user, title, comments,
            kind, tags, on_progress=None,
    ):
        """
        Add a large document using chunked upload.

        Internal method that handles multipart upload for large documents.
        """
        total_size = len(document)
        chunk_size = DEFAULT_CHUNK_SIZE

        logger.info(f"Starting chunked upload for document {id} ({total_size} bytes)")

        # Begin upload session
        begin_request = {
            "operation": "begin-upload",
            "document-metadata": {
                "id": id,
                "time": int(time.time()),
                "kind": kind,
                "title": title,
                "comments": comments,
                "user": user,
                "tags": tags,
            },
            "total-size": total_size,
            "chunk-size": chunk_size,
        }

        begin_response = self.request(begin_request)

        upload_id = begin_response.get("upload-id")
        if not upload_id:
            raise RuntimeError("Failed to begin upload: no upload_id returned")

        actual_chunk_size = begin_response.get("chunk-size", chunk_size)
        total_chunks = begin_response.get("total-chunks", math.ceil(total_size / actual_chunk_size))

        logger.info(f"Upload session {upload_id} created, {total_chunks} chunks")

        try:
            # Upload chunks
            bytes_sent = 0
            for chunk_index in range(total_chunks):
                start = chunk_index * actual_chunk_size
                end = min(start + actual_chunk_size, total_size)
                chunk_data = document[start:end]

                chunk_request = {
                    "operation": "upload-chunk",
                    "upload-id": upload_id,
                    "chunk-index": chunk_index,
                    "content": base64.b64encode(chunk_data).decode("utf-8"),
                    "user": user,
                }

                chunk_response = self.request(chunk_request)

                bytes_sent = end

                # Call progress callback if provided
                if on_progress:
                    on_progress(bytes_sent, total_size)

                logger.debug(f"Chunk {chunk_index + 1}/{total_chunks} uploaded")

            # Complete upload
            complete_request = {
                "operation": "complete-upload",
                "upload-id": upload_id,
                "user": user,
            }

            complete_response = self.request(complete_request)

            logger.info(f"Chunked upload completed for document {id}")

            return complete_response

        except Exception as e:
            # Try to abort on failure
            logger.error(f"Chunked upload failed: {e}")
            try:
                abort_request = {
                    "operation": "abort-upload",
                    "upload-id": upload_id,
                    "user": user,
                }
                self.request(abort_request)
                logger.info(f"Aborted failed upload {upload_id}")
            except Exception as abort_error:
                logger.warning(f"Failed to abort upload: {abort_error}")
            raise

    def get_documents(self, user, include_children=False):
        """
        List all documents for a user.

        Retrieves metadata for all documents owned by the specified user.
        By default, only returns top-level documents (not child/extracted documents).

        Args:
            user: User identifier
            include_children: If True, also include child documents (default: False)

        Returns:
            list[DocumentMetadata]: List of document metadata objects

        Raises:
            ProtocolException: If response format is invalid

        Example:
            ```python
            library = api.library()

            # Get only top-level documents
            docs = library.get_documents(user="trustgraph")

            for doc in docs:
                print(f"{doc.id}: {doc.title} ({doc.kind})")
                print(f"  Uploaded: {doc.time}")
                print(f"  Tags: {', '.join(doc.tags)}")

            # Get all documents including extracted pages
            all_docs = library.get_documents(user="trustgraph", include_children=True)
            ```
        """

        input = {
            "operation": "list-documents",
            "user": user,
            "include-children": include_children,
        }

        object = self.request(input)

        try:
            return [
                DocumentMetadata(
                    id = v["id"],
                    time = datetime.datetime.fromtimestamp(v["time"]),
                    kind = v["kind"],
                    title = v["title"],
                    comments = v.get("comments", ""),
                    metadata = [
                        Triple(
                            s = to_value(w["s"]),
                            p = to_value(w["p"]),
                            o = to_value(w["o"])
                        )
                        for w in v["metadata"]
                    ],
                    user = v["user"],
                    tags = v["tags"],
                    parent_id = v.get("parent-id", ""),
                    document_type = v.get("document-type", "source"),
                )
                for v in object["document-metadatas"]
            ]
        except Exception as e:
            logger.error("Failed to parse document list response", exc_info=True)
            raise ProtocolException(f"Response not formatted correctly")

    def get_document(self, user, id):
        """
        Get metadata for a specific document.

        Retrieves the metadata for a single document by ID.

        Args:
            user: User identifier
            id: Document identifier

        Returns:
            DocumentMetadata: Document metadata object

        Raises:
            ProtocolException: If response format is invalid

        Example:
            ```python
            library = api.library()
            doc = library.get_document(user="trustgraph", id="doc-123")
            print(f"Title: {doc.title}")
            print(f"Comments: {doc.comments}")
            ```
        """

        input = {
            "operation": "get-document",
            "user": user,
            "document-id": id,
        }

        object = self.request(input)
        doc = object["document-metadata"]

        try:
            return DocumentMetadata(
                id = doc["id"],
                time = datetime.datetime.fromtimestamp(doc["time"]),
                kind = doc["kind"],
                title = doc["title"],
                comments = doc.get("comments", ""),
                metadata = [
                    Triple(
                        s = to_value(w["s"]),
                        p = to_value(w["p"]),
                        o = to_value(w["o"])
                    )
                    for w in doc["metadata"]
                ],
                user = doc["user"],
                tags = doc["tags"],
                parent_id = doc.get("parent-id", ""),
                document_type = doc.get("document-type", "source"),
            )
        except Exception as e:
            logger.error("Failed to parse document response", exc_info=True)
            raise ProtocolException(f"Response not formatted correctly")

    def update_document(self, user, id, metadata):
        """
        Update document metadata.

        Updates the metadata for an existing document in the library.

        Args:
            user: User identifier
            id: Document identifier
            metadata: Updated DocumentMetadata object

        Returns:
            DocumentMetadata: Updated document metadata

        Raises:
            ProtocolException: If response format is invalid

        Example:
            ```python
            library = api.library()

            # Get existing document
            doc = library.get_document(user="trustgraph", id="doc-123")

            # Update metadata
            doc.title = "Updated Title"
            doc.comments = "Updated description"
            doc.tags.append("reviewed")

            # Save changes
            updated_doc = library.update_document(
                user="trustgraph",
                id="doc-123",
                metadata=doc
            )
            ```
        """

        input = {
            "operation": "update-document",
            "document-metadata": {
                "user": user,
                "document-id": id,
                "time": metadata.time,
                "title": metadata.title,
                "comments": metadata.comments,
                "metadata": [
                    {
                        "s": from_value(t["s"]),
                        "p": from_value(t["p"]),
                        "o": from_value(t["o"]),
                    }
                    for t in metadata.metadata
                ],
                "tags": metadata.tags,
            }
        }

        object = self.request(input)
        doc = object["document-metadata"]

        try:
            DocumentMetadata(
                id = doc["id"],
                time = datetime.datetime.fromtimestamp(doc["time"]),
                kind = doc["kind"],
                title = doc["title"],
                comments = doc.get("comments", ""),
                metadata = [
                    Triple(
                        s = to_value(w["s"]),
                        p = to_value(w["p"]),
                        o = to_value(w["o"])
                    )
                    for w in doc["metadata"]
                ],
                user = doc["user"],
                tags = doc["tags"]
            )
        except Exception as e:
            logger.error("Failed to parse document update response", exc_info=True)
            raise ProtocolException(f"Response not formatted correctly")

    def remove_document(self, user, id):
        """
        Remove a document from the library.

        Deletes a document and its metadata from the library.

        Args:
            user: User identifier
            id: Document identifier to remove

        Returns:
            dict: Empty response object

        Example:
            ```python
            library = api.library()
            library.remove_document(user="trustgraph", id="doc-123")
            ```
        """

        input = {
            "operation": "remove-document",
            "user": user,
            "document-id": id,
        }

        object = self.request(input)

        return {}

    def start_processing(
            self, id, document_id, flow="default",
            user="trustgraph", collection="default", tags=[],
    ):
        """
        Start a document processing workflow.

        Initiates processing of a document through a specified flow, tracking
        the processing job with metadata.

        Args:
            id: Unique processing job identifier
            document_id: ID of the document to process
            flow: Flow instance to use for processing (default: "default")
            user: User identifier (default: "trustgraph")
            collection: Target collection for processed data (default: "default")
            tags: List of tags for the processing job (default: [])

        Returns:
            dict: Empty response object

        Example:
            ```python
            library = api.library()

            # Start processing a document
            library.start_processing(
                id="proc-001",
                document_id="doc-123",
                flow="default",
                user="trustgraph",
                collection="research",
                tags=["automated", "extract"]
            )
            ```
        """

        input = {
            "operation": "add-processing",
            "processing-metadata": {
                "id": id,
                "document-id": document_id,
                "time": int(time.time()),
                "flow": flow,
                "user": user,
                "collection": collection,
                "tags": tags,
            }
        }

        object = self.request(input)

        return {}

    def stop_processing(
            self, id, user="trustgraph",
    ):
        """
        Stop a running document processing job.

        Terminates an active document processing workflow and removes its metadata.

        Args:
            id: Processing job identifier to stop
            user: User identifier (default: "trustgraph")

        Returns:
            dict: Empty response object

        Example:
            ```python
            library = api.library()
            library.stop_processing(id="proc-001", user="trustgraph")
            ```
        """

        input = {
            "operation": "remove-processing",
            "processing-id": id,
            "user": user,
        }

        object = self.request(input)

        return {}

    def get_processings(self, user="trustgraph"):
        """
        List all active document processing jobs.

        Retrieves metadata for all currently running document processing workflows
        for the specified user.

        Args:
            user: User identifier (default: "trustgraph")

        Returns:
            list[ProcessingMetadata]: List of processing job metadata objects

        Raises:
            ProtocolException: If response format is invalid

        Example:
            ```python
            library = api.library()
            jobs = library.get_processings(user="trustgraph")

            for job in jobs:
                print(f"Job {job.id}:")
                print(f"  Document: {job.document_id}")
                print(f"  Flow: {job.flow}")
                print(f"  Collection: {job.collection}")
                print(f"  Started: {job.time}")
            ```
        """

        input = {
            "operation": "list-processing",
            "user": user,
        }

        object = self.request(input)

        try:
            return [
                ProcessingMetadata(
                    id = v["id"],
                    document_id = v["document-id"],
                    time = datetime.datetime.fromtimestamp(v["time"]),
                    flow = v["flow"],
                    user = v["user"],
                    collection = v["collection"],
                    tags = v["tags"],
                )
                for v in object["processing-metadatas"]
            ]
        except Exception as e:
            logger.error("Failed to parse processing list response", exc_info=True)
            raise ProtocolException(f"Response not formatted correctly")

    # Chunked upload management methods

    def get_pending_uploads(self, user):
        """
        List all pending (in-progress) uploads for a user.

        Retrieves information about chunked uploads that have been started
        but not yet completed.

        Args:
            user: User identifier

        Returns:
            list[dict]: List of pending upload information

        Example:
            ```python
            library = api.library()
            pending = library.get_pending_uploads(user="trustgraph")

            for upload in pending:
                print(f"Upload {upload['upload_id']}:")
                print(f"  Document: {upload['document_id']}")
                print(f"  Progress: {upload['chunks_received']}/{upload['total_chunks']}")
            ```
        """
        input = {
            "operation": "list-uploads",
            "user": user,
        }

        response = self.request(input)

        return response.get("upload-sessions", [])

    def get_upload_status(self, upload_id, user):
        """
        Get the status of a specific upload.

        Retrieves detailed status information about a chunked upload,
        including which chunks have been received and which are missing.

        Args:
            upload_id: Upload session identifier
            user: User identifier

        Returns:
            dict: Upload status information including:
                - upload_id: The upload session ID
                - state: "in-progress", "completed", or "expired"
                - chunks_received: Number of chunks received
                - total_chunks: Total number of chunks expected
                - received_chunks: List of received chunk indices
                - missing_chunks: List of missing chunk indices
                - bytes_received: Total bytes received
                - total_bytes: Total expected bytes

        Example:
            ```python
            library = api.library()
            status = library.get_upload_status(
                upload_id="abc-123",
                user="trustgraph"
            )

            if status['state'] == 'in-progress':
                print(f"Missing chunks: {status['missing_chunks']}")
            ```
        """
        input = {
            "operation": "get-upload-status",
            "upload-id": upload_id,
            "user": user,
        }

        return self.request(input)

    def abort_upload(self, upload_id, user):
        """
        Abort an in-progress upload.

        Cancels a chunked upload and cleans up any uploaded chunks.

        Args:
            upload_id: Upload session identifier
            user: User identifier

        Returns:
            dict: Empty response on success

        Example:
            ```python
            library = api.library()
            library.abort_upload(upload_id="abc-123", user="trustgraph")
            ```
        """
        input = {
            "operation": "abort-upload",
            "upload-id": upload_id,
            "user": user,
        }

        return self.request(input)

    def resume_upload(self, upload_id, document, user, on_progress=None):
        """
        Resume an interrupted upload.

        Continues a chunked upload that was previously interrupted,
        uploading only the missing chunks.

        Args:
            upload_id: Upload session identifier to resume
            document: Complete document content as bytes
            user: User identifier
            on_progress: Optional callback(bytes_sent, total_bytes) for progress updates

        Returns:
            dict: Response from completing the upload

        Example:
            ```python
            library = api.library()

            # Check what's missing
            status = library.get_upload_status(
                upload_id="abc-123",
                user="trustgraph"
            )

            if status['state'] == 'in-progress':
                # Resume with the same document
                with open("large_document.pdf", "rb") as f:
                    library.resume_upload(
                        upload_id="abc-123",
                        document=f.read(),
                        user="trustgraph"
                    )
            ```
        """
        # Get current status
        status = self.get_upload_status(upload_id, user)

        if status.get("upload-state") == "expired":
            raise RuntimeError("Upload session has expired, please start a new upload")

        if status.get("upload-state") == "completed":
            return {"message": "Upload already completed"}

        missing_chunks = status.get("missing-chunks", [])
        total_chunks = status.get("total-chunks", 0)
        total_bytes = status.get("total-bytes", len(document))
        chunk_size = total_bytes // total_chunks if total_chunks > 0 else DEFAULT_CHUNK_SIZE

        logger.info(f"Resuming upload {upload_id}, {len(missing_chunks)} chunks remaining")

        # Upload missing chunks
        for chunk_index in missing_chunks:
            start = chunk_index * chunk_size
            end = min(start + chunk_size, len(document))
            chunk_data = document[start:end]

            chunk_request = {
                "operation": "upload-chunk",
                "upload-id": upload_id,
                "chunk-index": chunk_index,
                "content": base64.b64encode(chunk_data).decode("utf-8"),
                "user": user,
            }

            self.request(chunk_request)

            if on_progress:
                # Estimate progress including previously uploaded chunks
                uploaded = total_chunks - len(missing_chunks) + missing_chunks.index(chunk_index) + 1
                bytes_sent = min(uploaded * chunk_size, total_bytes)
                on_progress(bytes_sent, total_bytes)

            logger.debug(f"Resumed chunk {chunk_index}")

        # Complete upload
        complete_request = {
            "operation": "complete-upload",
            "upload-id": upload_id,
            "user": user,
        }

        return self.request(complete_request)

    # Child document methods

    def add_child_document(
            self, document, id, parent_id, user, title, comments,
            kind="text/plain", tags=[], metadata=None,
    ):
        """
        Add a child document linked to a parent document.

        Child documents are typically extracted content (e.g., pages from a PDF).
        They are automatically marked with document_type="extracted" and linked
        to their parent via parent_id.

        Args:
            document: Document content as bytes
            id: Document identifier (auto-generated if None)
            parent_id: Parent document identifier (required)
            user: User/owner identifier
            title: Document title
            comments: Document description or comments
            kind: MIME type of the document (default: "text/plain")
            tags: List of tags for categorization (default: [])
            metadata: Optional metadata as list of Triple objects

        Returns:
            dict: Response from the add operation

        Raises:
            RuntimeError: If parent_id is not provided

        Example:
            ```python
            library = api.library()

            # Add extracted page from a PDF
            library.add_child_document(
                document=page_text.encode('utf-8'),
                id="doc-123-page-1",
                parent_id="doc-123",
                user="trustgraph",
                title="Page 1 of Research Paper",
                comments="First page extracted from PDF",
                kind="text/plain",
                tags=["extracted", "page"]
            )
            ```
        """
        if not parent_id:
            raise RuntimeError("parent_id is required for child documents")

        if id is None:
            id = hash(document)

        if not title:
            title = ""
        if not comments:
            comments = ""

        triples = []
        if metadata:
            if isinstance(metadata, list):
                triples = [
                    {
                        "s": from_value(t.s),
                        "p": from_value(t.p),
                        "o": from_value(t.o),
                    }
                    for t in metadata
                ]

        input = {
            "operation": "add-child-document",
            "document-metadata": {
                "id": id,
                "time": int(time.time()),
                "kind": kind,
                "title": title,
                "comments": comments,
                "metadata": triples,
                "user": user,
                "tags": tags,
                "parent-id": parent_id,
                "document-type": "extracted",
            },
            "content": base64.b64encode(document).decode("utf-8"),
        }

        return self.request(input)

    def list_children(self, document_id, user):
        """
        List all child documents for a given parent document.

        Args:
            document_id: Parent document identifier
            user: User identifier

        Returns:
            list[DocumentMetadata]: List of child document metadata objects

        Example:
            ```python
            library = api.library()
            children = library.list_children(
                document_id="doc-123",
                user="trustgraph"
            )

            for child in children:
                print(f"{child.id}: {child.title}")
            ```
        """
        input = {
            "operation": "list-children",
            "document-id": document_id,
            "user": user,
        }

        response = self.request(input)

        try:
            return [
                DocumentMetadata(
                    id=v["id"],
                    time=datetime.datetime.fromtimestamp(v["time"]),
                    kind=v["kind"],
                    title=v["title"],
                    comments=v.get("comments", ""),
                    metadata=[
                        Triple(
                            s=to_value(w["s"]),
                            p=to_value(w["p"]),
                            o=to_value(w["o"])
                        )
                        for w in v.get("metadata", [])
                    ],
                    user=v["user"],
                    tags=v.get("tags", []),
                    parent_id=v.get("parent-id", ""),
                    document_type=v.get("document-type", "source"),
                )
                for v in response.get("document-metadatas", [])
            ]
        except Exception as e:
            logger.error("Failed to parse children response", exc_info=True)
            raise ProtocolException("Response not formatted correctly")

    def get_document_content(self, user, id):
        """
        Get the content of a document.

        Retrieves the full content of a document as bytes.

        Args:
            user: User identifier
            id: Document identifier

        Returns:
            bytes: Document content

        Example:
            ```python
            library = api.library()
            content = library.get_document_content(
                user="trustgraph",
                id="doc-123"
            )

            # Write to file
            with open("output.pdf", "wb") as f:
                f.write(content)
            ```
        """
        input = {
            "operation": "get-document-content",
            "user": user,
            "document-id": id,
        }

        response = self.request(input)
        content_b64 = response.get("content", "")

        return base64.b64decode(content_b64)

    def stream_document_to_file(self, user, id, file_path, chunk_size=1024*1024, on_progress=None):
        """
        Stream document content to a file.

        Downloads document content in chunks and writes directly to a file,
        enabling memory-efficient handling of large documents.

        Args:
            user: User identifier
            id: Document identifier
            file_path: Path to write the document content
            chunk_size: Size of each chunk to download (default 1MB)
            on_progress: Optional callback(bytes_received, total_bytes) for progress updates

        Returns:
            int: Total bytes written

        Example:
            ```python
            library = api.library()

            def progress(received, total):
                print(f"Downloaded {received}/{total} bytes")

            library.stream_document_to_file(
                user="trustgraph",
                id="large-doc-123",
                file_path="/tmp/document.pdf",
                on_progress=progress
            )
            ```
        """
        chunk_index = 0
        total_bytes_written = 0
        total_bytes = None

        with open(file_path, "wb") as f:
            while True:
                input = {
                    "operation": "stream-document",
                    "user": user,
                    "document-id": id,
                    "chunk-index": chunk_index,
                    "chunk-size": chunk_size,
                }

                response = self.request(input)

                content_b64 = response.get("content", "")
                chunk_data = base64.b64decode(content_b64)

                if not chunk_data:
                    break

                f.write(chunk_data)
                total_bytes_written += len(chunk_data)

                total_chunks = response.get("total-chunks", 1)
                total_bytes = response.get("total-bytes", total_bytes_written)

                if on_progress:
                    on_progress(total_bytes_written, total_bytes)

                # Check if we've received all chunks
                if chunk_index >= total_chunks - 1:
                    break

                chunk_index += 1

        return total_bytes_written

