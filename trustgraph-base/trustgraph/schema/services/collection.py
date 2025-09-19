from pulsar.schema import Record, String, Integer, Array
from datetime import datetime

from ..core.primitives import Error
from ..core.topic import topic

############################################################################

# Collection management operations

# Collection metadata operations (for librarian service)

class CollectionMetadata(Record):
    """Collection metadata record"""
    user = String()
    collection = String()
    name = String()
    description = String()
    tags = Array(String())
    created_at = String()  # ISO timestamp
    updated_at = String()  # ISO timestamp

############################################################################

class CollectionManagementRequest(Record):
    """Request for collection management operations"""
    operation = String()  # e.g., "delete-collection"

    # For 'list-collections'
    user = String()
    collection = String()
    timestamp = String()  # ISO timestamp
    name = String()
    description = String()
    tags = Array(String())
    created_at = String()  # ISO timestamp
    updated_at = String()  # ISO timestamp

    # For list
    tag_filter = Array(String())  # Optional filter by tags
    limit = Integer()

class CollectionManagementResponse(Record):
    """Response for collection management operations"""
    error = Error()  # Only populated if there's an error
    timestamp = String()  # ISO timestamp
    collections = Array(CollectionMetadata())


############################################################################

# Topics

collection_request_queue = topic(
    'collection', kind='non-persistent', namespace='request'
)
collection_response_queue = topic(
    'collection', kind='non-persistent', namespace='response'
)
