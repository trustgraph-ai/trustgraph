
import uuid
import hashlib

def hash(data):

    if isinstance(data, str):
        data = data.encode("utf-8")

    # Create a SHA256 hash from the data
    id = hashlib.sha256(data).hexdigest()

    # Convert into a UUID, 64-byte hash becomes 32-byte UUID
    id = str(uuid.UUID(id[::2]))

    return id

def to_uri(pref, id):
    return f"https://trustgraph.ai/{pref}/{id}"

PREF_PUBEV = "pubev"
PREF_ORG = "org"
PREF_DOC = "doc"
