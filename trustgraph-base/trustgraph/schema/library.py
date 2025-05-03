
from pulsar.schema import Record, Bytes, String, Array, Long
from . types import Triple
from . topic import topic
from . types import Error
from . metadata import Metadata
from . documents import Document, TextDocument

# add
#   -> (id, document)
#   <- ()
#   <- (error)

# list
#   -> (user, collection?)
#   <- (info)
#   <- (error)

# add(Metadata, Bytes) : error?
# copy(id, user, collection)
# move(id, user, collection)
# delete(id)
# get(id) : Bytes
# reindex(id)
# list(user, collection) : id[]
# info(id[]) : DocumentInfo[]
# search(<key,op,value>[]) : id[]

class DocumentPackage(Record):
    id = String()
    flow = String()
    document = Bytes()
    kind = String()
    user = String()
    collection = String()
    title = String()
    comments = String()
    time = Long()
    metadata = Array(Triple())

class DocumentInfo(Record):
    id = String()
    flow = String()
    kind = String()
    user = String()
    collection = String()
    title = String()
    comments = String()
    time = Long()
    metadata = Array(Triple())

class Criteria(Record):
    key = String()
    value = String()
    operator = String()

class LibrarianRequest(Record):
    operation = String()
    id = String()
    flow = String()
    document = DocumentPackage()
    user = String()
    collection = String()
    criteria = Array(Criteria())

class LibrarianResponse(Record):
    error = Error()
    document = DocumentPackage()
    info = Array(DocumentInfo())

librarian_request_queue = topic(
    'librarian', kind='non-persistent', namespace='request'
)
librarian_response_queue = topic(
    'librarian', kind='non-persistent', namespace='response',
)

