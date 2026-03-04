from dataclasses import dataclass

from ..core.metadata import Metadata
from ..core.topic import topic

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

############################################################################
