from dataclasses import dataclass, field
from datetime import datetime

from ..core.primitives import Error
from ..core.topic import topic

############################################################################

# Collection management operations

# Collection metadata operations (for librarian service)

@dataclass
class CollectionMetadata:
    """Collection metadata record"""
    user: str = ""
    collection: str = ""
    name: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)

############################################################################

@dataclass
class CollectionManagementRequest:
    """Request for collection management operations"""
    operation: str = ""  # e.g., "delete-collection"

    # For 'list-collections'
    user: str = ""
    collection: str = ""
    timestamp: str = ""  # ISO timestamp
    name: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)

    # For list
    tag_filter: list[str] = field(default_factory=list)  # Optional filter by tags
    limit: int = 0

@dataclass
class CollectionManagementResponse:
    """Response for collection management operations"""
    error: Error | None = None  # Only populated if there's an error
    timestamp: str = ""  # ISO timestamp
    collections: list[CollectionMetadata] = field(default_factory=list)


############################################################################

# Topics

collection_request_queue = topic(
    'collection', qos='q0', namespace='request'
)
collection_response_queue = topic(
    'collection', qos='q0', namespace='response'
)

