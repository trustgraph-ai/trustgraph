from dataclasses import dataclass

@dataclass
class Metadata:
    # Source identifier
    id: str = ""

    # Root document identifier (set by librarian, preserved through pipeline)
    root: str = ""

    # Collection management
    user: str = ""
    collection: str = ""
