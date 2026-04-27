from dataclasses import dataclass, field
from datetime import datetime

from ..core.primitives import Error
from ..core.topic import queue

############################################################################

# Collection management operations

# Collection metadata operations (for librarian service)

@dataclass
class CollectionMetadata:
    """Collection metadata record"""
    collection: str = ""
    name: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)

############################################################################

@dataclass
class CollectionManagementRequest:
    """Request for collection management operations.

    Collection-management is a global (non-flow-scoped) service, so the
    workspace has to travel on the wire — it's the isolation boundary
    for which workspace's collections the request operates on.
    """
    operation: str = ""  # e.g., "delete-collection"

    # Workspace the collection belongs to.
    workspace: str = ""

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

collection_request_queue = queue('collection', cls='request')
collection_response_queue = queue('collection', cls='response')

