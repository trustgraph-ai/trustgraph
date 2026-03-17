
from dataclasses import dataclass, field

from ..core.topic import topic
from ..core.primitives import Error

############################################################################

# Prompt services, abstract the prompt generation

@dataclass
class AgentStep:
    thought: str = ""
    action: str = ""
    arguments: dict[str, str] = field(default_factory=dict)
    observation: str = ""
    user: str = ""              # User context for the step

@dataclass
class AgentRequest:
    question: str = ""
    state: str = ""
    group: list[str] | None = None
    history: list[AgentStep] = field(default_factory=list)
    user: str = ""              # User context for multi-tenancy
    collection: str = "default" # Collection for provenance traces
    streaming: bool = False     # Enable streaming response delivery (default false)
    session_id: str = ""        # For provenance tracking across iterations

@dataclass
class AgentResponse:
    # Streaming-first design
    chunk_type: str = ""        # "thought", "action", "observation", "answer", "explain", "error"
    content: str = ""           # The actual content (interpretation depends on chunk_type)
    end_of_message: bool = False   # Current chunk type (thought/action/etc.) is complete
    end_of_dialog: bool = False    # Entire agent dialog is complete

    # Explainability fields
    explain_id: str | None = None     # Provenance URI (announced as created)
    explain_graph: str | None = None  # Named graph where explain was stored

    # Legacy fields (deprecated but kept for backward compatibility)
    answer: str = ""
    error: Error | None = None
    thought: str = ""
    observation: str = ""

############################################################################

