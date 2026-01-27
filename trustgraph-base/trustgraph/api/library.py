"""
TrustGraph Document Library Management

This module provides interfaces for managing documents in the TrustGraph library,
including document storage, metadata management, and processing workflow coordination.
"""

import datetime
import time
import base64
import logging

from . types import DocumentMetadata, ProcessingMetadata, Triple
from .. knowledge import hash, Uri, Literal
from .. schema import IRI, LITERAL
from . exceptions import *

logger = logging.getLogger(__name__)


def to_value(x):
    """Convert wire format to Uri or Literal."""
    if x.get("t") == IRI:
        return Uri(x.get("i", ""))
    elif x.get("t") == LITERAL:
        return Literal(x.get("v", ""))
    # Fallback for any other type
    return Literal(x.get("v", x.get("i", "")))


def from_value(v):
    """Convert Uri or Literal to wire format."""
    if isinstance(v, Uri):
        return {"t": IRI, "i": str(v)}
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
            kind="text/plain", tags=[],
    ):
        """
        Add a document to the library.

        Stores a document with associated metadata in the library for
        retrieval and processing.

        Args:
            document: Document content as bytes
            id: Document identifier (auto-generated if None)
            metadata: Document metadata as list of Triple objects or object with emit method
            user: User/owner identifier
            title: Document title
            comments: Document description or comments
            kind: MIME type of the document (default: "text/plain")
            tags: List of tags for categorization (default: [])

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

    def get_documents(self, user):
        """
        List all documents for a user.

        Retrieves metadata for all documents owned by the specified user.

        Args:
            user: User identifier

        Returns:
            list[DocumentMetadata]: List of document metadata objects

        Raises:
            ProtocolException: If response format is invalid

        Example:
            ```python
            library = api.library()
            docs = library.get_documents(user="trustgraph")

            for doc in docs:
                print(f"{doc.id}: {doc.title} ({doc.kind})")
                print(f"  Uploaded: {doc.time}")
                print(f"  Tags: {', '.join(doc.tags)}")
            ```
        """

        input = {
            "operation": "list-documents",
            "user": user,
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
                    tags = v["tags"]
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

