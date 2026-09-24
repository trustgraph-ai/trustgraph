
from dataclasses import dataclass, field

from .core.primitives import Error, Triple

############################################################################

# Agent

@dataclass
class PlanStep:
    goal: str = ""
    tool_hint: str = ""                   # Suggested tool for this step
    depends_on: list[int] = field(default_factory=list)  # Indices of prerequisite steps
    status: str = "pending"               # pending, running, completed, failed
    result: str = ""                      # Result of step execution

@dataclass
class AgentStep:
    thought: str = ""
    action: str = ""
    arguments: dict[str, str] = field(default_factory=dict)
    observation: str = ""
    step_type: str = ""         # "react", "plan", "execute", "decompose", "synthesise"
    plan: list[PlanStep] = field(default_factory=list)      # Plan steps (for plan-then-execute)
    subagent_results: dict[str, str] = field(default_factory=dict)  # Subagent results keyed by goal

@dataclass
class AgentRequest:
    question: str = ""
    state: str = ""
    group: list[str] | None = None
    history: list[AgentStep] = field(default_factory=list)
    collection: str = "default" # Collection for provenance traces
    streaming: bool = False     # Enable streaming response delivery (default false)
    session_id: str = ""        # For provenance tracking across iterations

    # Orchestration fields
    conversation_id: str = ""   # Groups related requests into a conversation
    pattern: str = ""           # Selected pattern: "react", "plan-then-execute", "supervisor"
    task_type: str = ""         # Task type from config: "general", "research", etc.
    framing: str = ""           # Domain framing text injected into prompts
    correlation_id: str = ""    # Links fan-out subagents to parent for fan-in
    parent_session_id: str = "" # Session ID of the supervisor that spawned this subagent
    subagent_goal: str = ""     # Specific goal for a subagent (set by supervisor)
    expected_siblings: int = 0  # Number of sibling subagents in this fan-out

@dataclass
class AgentResponse:
    # Streaming-first design
    message_type: str = ""     # "thought", "action", "observation", "answer", "explain", "error"
    content: str = ""           # The actual content (interpretation depends on message_type)
    end_of_message: bool = False   # Current chunk type (thought/action/etc.) is complete
    end_of_dialog: bool = False    # Entire agent dialog is complete

    # Explainability fields
    explain_id: str | None = None     # Root URI for this explain step
    explain_graph: str | None = None  # Named graph (e.g., urn:graph:retrieval)
    explain_triples: list[Triple] = field(default_factory=list)  # Provenance triples for this step

    # Orchestration fields
    message_id: str = ""              # Unique ID for this response message

    error: Error | None = None

    # Token usage (populated on end_of_dialog message)
    in_token: int | None = None
    out_token: int | None = None
    model: str | None = None

############################################################################

# Tool service

@dataclass
class ToolServiceRequest:
    """Request to a dynamically configured tool service."""
    # Config values (collection, etc.) as JSON
    config: str = ""
    # Arguments from LLM as JSON
    arguments: str = ""

@dataclass
class ToolServiceResponse:
    """Response from a tool service."""
    error: Error | None = None
    # Response text (the observation)
    response: str = ""
    # End of stream marker for streaming responses
    end_of_stream: bool = False

############################################################################

# Passthrough

@dataclass
class PassthroughRequest:
    payload: dict = field(default_factory=dict)

@dataclass
class PassthroughResponse:
    payload: dict = field(default_factory=dict)
    error: Error | None = None
    is_final: bool = True

############################################################################
