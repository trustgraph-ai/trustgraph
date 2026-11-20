
from dataclasses import dataclass

from .core.primitives import Error
from .core.topic import queue

############################################################################

# Chunker service (request/response interface)

@dataclass
class ChunkerRequest:
    document_id: str = ""
    chunk_size: int = 0        # 0 = use service default
    chunk_overlap: int = 0     # 0 = use service default

@dataclass
class ChunkerResponse:
    error: Error | None = None
    document_id: str = ""      # librarian URI for this chunk
    index: int = 0             # 1-indexed chunk number
    char_offset: int = 0
    char_length: int = 0
    end_of_stream: bool = False

############################################################################

# Queue definitions

chunker_request_queue = queue('chunker', cls='request')
chunker_response_queue = queue('chunker', cls='response')
