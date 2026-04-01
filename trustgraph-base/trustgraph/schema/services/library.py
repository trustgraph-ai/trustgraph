from dataclasses import dataclass, field
from ..core.primitives import Triple, Error
from ..core.topic import queue
from ..core.metadata import Metadata
# Note: Document imports will be updated after knowledge schemas are converted

# add-document
#   -> (document_id, document_metadata, content)
#   <- ()
#   <- (error)

# remove-document
#   -> (document_id)
#   <- ()
#   <- (error)

# update-document
#   -> (document_id, document_metadata)
#   <- ()
#   <- (error)

# get-document-metadata
#   -> (document_id)
#   <- (document_metadata)
#   <- (error)

# get-document-content [DEPRECATED — use stream-document instead]
#   -> (document_id)
#   <- (content)
#   <- (error)
#   NOTE: Returns entire document in a single message. Fails for documents
#   exceeding the broker's max message size. Use stream-document which
#   returns content in chunks.

# add-processing
#   -> (processing_id, processing_metadata)
#   <- ()
#   <- (error)

# remove-processing
#   -> (processing_id)
#   <- ()
#   <- (error)

# list-documents
#   -> (user, collection?)
#   <- (document_metadata[])
#   <- (error)

# list-processing
#   -> (user, collection?)
#   <- (processing_metadata[])
#   <- (error)

# begin-upload
#   -> (document_metadata, total_size, chunk_size)
#   <- (upload_id, chunk_size, total_chunks)
#   <- (error)

# upload-chunk
#   -> (upload_id, chunk_index, content)
#   <- (upload_id, chunk_index, chunks_received, total_chunks, bytes_received, total_bytes)
#   <- (error)

# complete-upload
#   -> (upload_id)
#   <- (document_id, object_id)
#   <- (error)

# abort-upload
#   -> (upload_id)
#   <- ()
#   <- (error)

# get-upload-status
#   -> (upload_id)
#   <- (upload_id, state, chunks_received, missing_chunks, total_chunks, bytes_received, total_bytes)
#   <- (error)

# list-uploads
#   -> (user)
#   <- (uploads[])
#   <- (error)

@dataclass
class DocumentMetadata:
    id: str = ""
    time: int = 0
    kind: str = ""
    title: str = ""
    comments: str = ""
    metadata: list[Triple] = field(default_factory=list)
    user: str = ""
    tags: list[str] = field(default_factory=list)
    # Child document support
    parent_id: str = ""  # Empty for top-level docs, set for children
    # Document type vocabulary:
    #   "source" - original uploaded document
    #   "page" - page extracted from source (e.g., PDF page)
    #   "chunk" - text chunk derived from page or source
    #   "extracted" - legacy value, kept for backwards compatibility
    document_type: str = "source"

@dataclass
class ProcessingMetadata:
    id: str = ""
    document_id: str = ""
    time: int = 0
    flow: str = ""
    user: str = ""
    collection: str = ""
    tags: list[str] = field(default_factory=list)

@dataclass
class Criteria:
    key: str = ""
    value: str = ""
    operator: str = ""

@dataclass
class UploadProgress:
    """Progress information for chunked uploads."""
    upload_id: str = ""
    chunks_received: int = 0
    total_chunks: int = 0
    bytes_received: int = 0
    total_bytes: int = 0

@dataclass
class UploadSession:
    """Information about an in-progress upload."""
    upload_id: str = ""
    document_id: str = ""
    document_metadata_json: str = ""  # JSON-encoded DocumentMetadata
    total_size: int = 0
    chunk_size: int = 0
    total_chunks: int = 0
    chunks_received: int = 0
    created_at: str = ""

@dataclass
class LibrarianRequest:
    # add-document, remove-document, update-document, get-document-metadata,
    # get-document-content, add-processing, remove-processing, list-documents,
    # list-processing, begin-upload, upload-chunk, complete-upload, abort-upload,
    # get-upload-status, list-uploads
    operation: str = ""

    # add-document, remove-document, update-document, get-document-metadata,
    # get-document-content
    document_id: str = ""

    # add-processing, remove-processing
    processing_id: str = ""

    # add-document, update-document, begin-upload
    document_metadata: DocumentMetadata | None = None

    # add-processing
    processing_metadata: ProcessingMetadata | None = None

    # add-document, upload-chunk
    content: bytes = b""

    # list-documents, list-processing, list-uploads
    user: str = ""

    # list-documents?, list-processing?
    collection: str = ""

    #
    criteria: list[Criteria] = field(default_factory=list)

    # begin-upload
    total_size: int = 0
    chunk_size: int = 0

    # upload-chunk, complete-upload, abort-upload, get-upload-status
    upload_id: str = ""

    # upload-chunk, stream-document
    chunk_index: int = 0

    # list-documents - whether to include child documents (default False)
    include_children: bool = False

@dataclass
class LibrarianResponse:
    error: Error | None = None
    document_metadata: DocumentMetadata | None = None
    content: bytes = b""
    document_metadatas: list[DocumentMetadata] = field(default_factory=list)
    processing_metadatas: list[ProcessingMetadata] = field(default_factory=list)

    # begin-upload response
    upload_id: str = ""
    chunk_size: int = 0
    total_chunks: int = 0

    # upload-chunk response
    chunk_index: int = 0
    chunks_received: int = 0
    bytes_received: int = 0
    total_bytes: int = 0

    # complete-upload response
    document_id: str = ""
    object_id: str = ""

    # get-upload-status response
    upload_state: str = ""  # "in-progress", "completed", "expired"
    received_chunks: list[int] = field(default_factory=list)
    missing_chunks: list[int] = field(default_factory=list)

    # list-uploads response
    upload_sessions: list[UploadSession] = field(default_factory=list)

    # Protocol flag: True if this is the final response for a request.
    # Default True since most operations are single request/response.
    # Only stream-document sets False for intermediate chunks.
    is_final: bool = True

# FIXME: Is this right?  Using persistence on librarian so that
# message chunking works

librarian_request_queue = queue('librarian', cls='request')
librarian_response_queue = queue('librarian', cls='response')
