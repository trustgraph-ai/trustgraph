
from pulsar.schema import Record, Bytes, String, Array, Long
from . types import Triple
from . topic import topic
from . types import Error
from . metadata import Metadata
from . documents import Document, TextDocument

# add-document
#   -> (document_id, document_metadata, content)
#   <- ()
#   <- (error)

# remove-document
#   -> (document_id)
#   <- ()
#   <- (error)

# update-document
#   -> (document_id, document_metadata)
#   <- ()
#   <- (error)

# get-document-metadata
#   -> (document_id)
#   <- (document_metadata)
#   <- (error)

# get-document-content
#   -> (document_id)
#   <- (content)
#   <- (error)

# add-processing
#   -> (processing_id, processing_metadata)
#   <- ()
#   <- (error)

# remove-processing
#   -> (processing_id)
#   <- ()
#   <- (error)

# list-documents
#   -> (user, collection?)
#   <- (document_metadata[])
#   <- (error)

# list-processing
#   -> (user, collection?)
#   <- (processing_metadata[])
#   <- (error)

# OLD:
# add(Metadata, Bytes) : error?
# copy(id, user, collection)
# move(id, user, collection)
# delete(id)
# get(id) : Bytes
# reindex(id)
# list(user, collection) : id[]
# info(id[]) : DocumentInfo[]
# search(<key,op,value>[]) : id[]

class DocumentMetadata(Record):
#    id = String()
    time = Long()
    kind = String()
    title = String()
    comments = String()
    metadata = Array(Triple())
    tags = Array(String())

class ProcessingMetadata(Record):
    document_id = String()
    time = Long()
    flow = String()
    user = String()
    collection = String()
    tags = Array(String())

class Criteria(Record):
    key = String()
    value = String()
    operator = String()

class LibrarianRequest(Record):

    # add-document, remove-document, update-document, get-document-metadata,
    # get-document-content, add-processing, remove-processing, list-documents,
    # list-processing
    operation = String()

    user = String()

    # add-document, remove-document, update-document, get-document-metadata,
    # get-document-content
    document_id = String()

    # add-processing, remove-processing
    processing_id = String()

    # add-document, update-document
    document_metadata = DocumentMetadata()

    # add-processing
    processing_metadata = ProcessingMetadata()

    # add-document
    content = Bytes()

    # list-documents, list-processing
    user = String()

    # list-documents?, list-processing?
    collection = String()

    # 
    criteria = Array(Criteria())

class LibrarianResponse(Record):
    error = Error()
    document_metadata = DocumentMetadata()
    content = Bytes()
    document_metadatas = Array(DocumentMetadata())
    processing_metadatas = Array(ProcessingMetadata())

librarian_request_queue = topic(
    'librarian', kind='non-persistent', namespace='request'
)
librarian_response_queue = topic(
    'librarian', kind='non-persistent', namespace='response',
)

