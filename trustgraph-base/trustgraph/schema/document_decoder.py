
from dataclasses import dataclass

from .core.primitives import Error
from .core.topic import queue

############################################################################

# Document decoder service (request/response interface to docling)

@dataclass
class DocumentDecoderRequest:
    document_id: str = ""
    mode: str = "page"           # "page" or "hybrid"

@dataclass
class DocumentDecoderResponse:
    error: Error | None = None
    document_id: str = ""        # librarian URI for this section
    page: int = 0
    section_type: str = "text"   # "text", "image", "table" (future)
    end_of_stream: bool = False

############################################################################

# Queue definitions

document_decoder_request_queue = queue('document-decoder', cls='request')
document_decoder_response_queue = queue('document-decoder', cls='response')
