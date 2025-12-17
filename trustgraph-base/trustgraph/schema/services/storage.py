from dataclasses import dataclass

from ..core.primitives import Error
from ..core.topic import topic

############################################################################

# Storage management operations

@dataclass
class StorageManagementRequest:
    """Request for storage management operations sent to store processors"""
    operation: str = ""  # e.g., "delete-collection"
    user: str = ""
    collection: str = ""

@dataclass
class StorageManagementResponse:
    """Response from storage processors for management operations"""
    error: Error | None = None  # Only populated if there's an error, if null success

############################################################################

# Storage management topics

# Topics for sending collection management requests to different storage types
vector_storage_management_topic = topic(
    'vector-storage-management', qos='q0', namespace='request'
)

object_storage_management_topic = topic(
    'object-storage-management', qos='q0', namespace='request'
)

triples_storage_management_topic = topic(
    'triples-storage-management', qos='q0', namespace='request'
)

# Topic for receiving responses from storage processors
storage_management_response_topic = topic(
    'storage-management', qos='q0', namespace='response'
)

############################################################################

