
from dataclasses import dataclass, field

from .core.metadata import Metadata
from .core.primitives import Triple, Error
from .core.topic import queue

############################################################################

# PDF docs etc.
@dataclass
class Document:
    metadata: Metadata | None = None
    data: bytes = b""
    # For large document streaming: if document_id is set, the receiver should
    # fetch content from librarian instead of using inline data
    document_id: str = ""

############################################################################

# Text documents / text from PDF

@dataclass
class TextDocument:
    metadata: Metadata | None = None
    text: bytes = b""
    # For large document streaming: if document_id is set, the receiver should
    # fetch content from librarian instead of using inline text
    document_id: str = ""

############################################################################

# Chunks of text

@dataclass
class Chunk:
    metadata: Metadata | None = None
    chunk: bytes = b""
    # For provenance: document_id of this chunk in librarian
    # Post-chunker optimization: both document_id AND chunk content are included
    # so downstream processors have the ID for provenance and content to work with
    document_id: str = ""
    attributes: dict[str, str | list[str]] = field(default_factory=dict)

############################################################################

# NLP extraction data types

@dataclass
class Definition:
    name: str = ""
    definition: str = ""

@dataclass
class Topic:
    name: str = ""
    definition: str = ""

@dataclass
class Relationship:
    s: str = ""
    p: str = ""
    o: str = ""
    o_entity: bool = False

@dataclass
class Fact:
    s: str = ""
    p: str = ""
    o: str = ""

############################################################################

# Knowledge core

@dataclass
class LibraryMetadata:
    id: str = ""
    kind: str = ""
    title: str = ""
    parent_id: str = ""
    document_type: str = ""
    comments: str = ""
    tags: list[str] = field(default_factory=list)

@dataclass
class LibraryBlob:
    id: str = ""
    data: bytes = b""

@dataclass
class KnowledgeRequest:
    # get-kg-core, delete-kg-core, list-kg-cores, put-kg-core
    # load-kg-core, unload-kg-core
    operation: str = ""

    # get-kg-core, list-kg-cores, delete-kg-core, put-kg-core,
    # load-kg-core, unload-kg-core
    id: str = ""

    # load-kg-core
    flow: str = ""

    # load-kg-core
    collection: str = ""

    # put-kg-core
    triples: "Triples | None" = None
    graph_embeddings: "GraphEmbeddings | None" = None

    # put-de-core
    document_embeddings: "DocumentEmbeddings | None" = None

    # put-kg-core (source material)
    library_metadata: LibraryMetadata | None = None
    library_blob: LibraryBlob | None = None

@dataclass
class KnowledgeResponse:
    error: Error | None = None
    ids: list[str] | None = None
    eos: bool = False     # Indicates end of knowledge core stream
    triples: "Triples | None" = None
    graph_embeddings: "GraphEmbeddings | None" = None
    document_embeddings: "DocumentEmbeddings | None" = None
    library_metadata: LibraryMetadata | None = None
    library_blob: LibraryBlob | None = None

knowledge_request_queue = queue('knowledge', cls='request')
knowledge_response_queue = queue('knowledge', cls='response')

############################################################################

# Librarian service

@dataclass
class DocumentMetadata:
    id: str = ""
    time: int = 0
    kind: str = ""
    title: str = ""
    comments: str = ""
    metadata: list[Triple] = field(default_factory=list)
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

############################################################################
