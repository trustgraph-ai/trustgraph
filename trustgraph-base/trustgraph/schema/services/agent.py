
from dataclasses import dataclass, field
from typing import Optional

from ..core.topic import topic
from ..core.primitives import Error

############################################################################

# Prompt services, abstract the prompt generation

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
    user: str = ""              # User context for the step
    step_type: str = ""         # "react", "plan", "execute", "decompose", "synthesise"
    plan: list[PlanStep] = field(default_factory=list)      # Plan steps (for plan-then-execute)
    subagent_results: dict[str, str] = field(default_factory=dict)  # Subagent results keyed by goal

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
    chunk_type: str = ""        # "thought", "action", "observation", "answer", "explain", "error"
    content: str = ""           # The actual content (interpretation depends on chunk_type)
    end_of_message: bool = False   # Current chunk type (thought/action/etc.) is complete
    end_of_dialog: bool = False    # Entire agent dialog is complete

    # Explainability fields
    explain_id: str | None = None     # Provenance URI (announced as created)
    explain_graph: str | None = None  # Named graph where explain was stored

    # Orchestration fields
    message_id: str = ""              # Unique ID for this response message

    error: Error | None = None

############################################################################

