from dataclasses import dataclass

@dataclass
class Metadata:
    # Source identifier
    id: str = ""

    # Collection management
    user: str = ""
    collection: str = ""
