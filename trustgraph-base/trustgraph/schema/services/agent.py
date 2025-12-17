
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
    streaming: bool = False     # NEW: Enable streaming response delivery (default false)

@dataclass
class AgentResponse:
    # Streaming-first design
    chunk_type: str = ""        # "thought", "action", "observation", "answer", "error"
    content: str = ""           # The actual content (interpretation depends on chunk_type)
    end_of_message: bool = False   # Current chunk type (thought/action/etc.) is complete
    end_of_dialog: bool = False    # Entire agent dialog is complete

    # Legacy fields (deprecated but kept for backward compatibility)
    answer: str = ""
    error: Error | None = None
    thought: str = ""
    observation: str = ""

############################################################################

