from pulsar.schema import Record, String

from ..core.primitives import Error
from ..core.topic import topic

############################################################################

# Storage management operations

class StorageManagementRequest(Record):
    """Request for storage management operations sent to store processors"""
    operation = String()  # e.g., "delete-collection"
    user = String()
    collection = String()

class StorageManagementResponse(Record):
    """Response from storage processors for management operations"""
    error = Error()  # Only populated if there's an error, if null success

############################################################################

# Storage management topics

# Topics for sending collection management requests to different storage types
vector_storage_management_topic = topic(
    'vector-storage-management', kind='non-persistent', namespace='request'
)

object_storage_management_topic = topic(
    'object-storage-management', kind='non-persistent', namespace='request'
)

triples_storage_management_topic = topic(
    'triples-storage-management', kind='non-persistent', namespace='request'
)

# Topic for receiving responses from storage processors
storage_management_response_topic = topic(
    'storage-management', kind='non-persistent', namespace='response'
)

############################################################################
