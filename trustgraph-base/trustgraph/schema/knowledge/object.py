from pulsar.schema import Record, String, Map, Double, Array

from ..core.metadata import Metadata
from ..core.topic import topic

############################################################################

# Extracted object from text processing

class ExtractedObject(Record):
    metadata = Metadata()
    schema_name = String()  # Which schema this object belongs to
    values = Array(Map(String()))  # Array of objects, each object is field name -> value
    confidence = Double()
    source_span = String()  # Text span where object was found

############################################################################