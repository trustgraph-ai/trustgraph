from dataclasses import dataclass

from ..core.metadata import Metadata
from ..core.topic import topic

############################################################################

# PDF docs etc.
@dataclass
class Document:
    metadata: Metadata | None = None
    data: bytes = b""

############################################################################

# Text documents / text from PDF

@dataclass
class TextDocument:
    metadata: Metadata | None = None
    text: bytes = b""

############################################################################

# Chunks of text

@dataclass
class Chunk:
    metadata: Metadata | None = None
    chunk: bytes = b""

############################################################################
