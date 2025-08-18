from pulsar.schema import Record, Bytes

from ..core.metadata import Metadata
from ..core.topic import topic

############################################################################

# PDF docs etc.
class Document(Record):
    metadata = Metadata()
    data = Bytes()

############################################################################

# Text documents / text from PDF

class TextDocument(Record):
    metadata = Metadata()
    text = Bytes()

############################################################################

# Chunks of text

class Chunk(Record):
    metadata = Metadata()
    chunk = Bytes()

############################################################################