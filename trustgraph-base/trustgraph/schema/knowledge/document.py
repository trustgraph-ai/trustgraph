from dataclasses import dataclass

from ..core.metadata import Metadata

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

############################################################################
