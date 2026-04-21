from dataclasses import dataclass

@dataclass
class Metadata:
    # Source identifier
    id: str = ""

    # Root document identifier (set by librarian, preserved through pipeline)
    root: str = ""

    # Collection the message belongs to.  Workspace is NOT carried on the
    # message — consumers derive it from flow.workspace (the flow the
    # message arrived on), which is the trusted isolation boundary.
    collection: str = ""
