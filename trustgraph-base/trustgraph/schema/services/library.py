from dataclasses import dataclass, field
from ..core.primitives import Triple, Error
from ..core.topic import topic
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

# get-document-content
#   -> (document_id)
#   <- (content)
#   <- (error)

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
class LibrarianRequest:
    # add-document, remove-document, update-document, get-document-metadata,
    # get-document-content, add-processing, remove-processing, list-documents,
    # list-processing
    operation: str = ""

    # add-document, remove-document, update-document, get-document-metadata,
    # get-document-content
    document_id: str = ""

    # add-processing, remove-processing
    processing_id: str = ""

    # add-document, update-document
    document_metadata: DocumentMetadata | None = None

    # add-processing
    processing_metadata: ProcessingMetadata | None = None

    # add-document
    content: bytes = b""

    # list-documents, list-processing
    user: str = ""

    # list-documents?, list-processing?
    collection: str = ""

    #
    criteria: list[Criteria] = field(default_factory=list)

@dataclass
class LibrarianResponse:
    error: Error | None = None
    document_metadata: DocumentMetadata | None = None
    content: bytes = b""
    document_metadatas: list[DocumentMetadata] = field(default_factory=list)
    processing_metadatas: list[ProcessingMetadata] = field(default_factory=list)

# FIXME: Is this right?  Using persistence on librarian so that
# message chunking works

librarian_request_queue = topic(
    'librarian', qos='q1', namespace='request'
)
librarian_response_queue = topic(
    'librarian', qos='q1', namespace='response',
)
