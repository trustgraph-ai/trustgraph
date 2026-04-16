---
layout: default
title: "TrustGraph Agent Orchestration — Technical Specification"
parent: "Tech Specs"
---

# TrustGraph Agent Orchestration — Technical Specification

## Overview

This specification describes the extension of TrustGraph's agent architecture
from a single ReACT execution pattern to a multi-pattern orchestration
model. The existing Pulsar-based self-queuing loop is pattern-agnostic — the
same infrastructure supports ReACT, Plan-then-Execute, Supervisor/Subagent
fan-out, and other execution strategies without changes to the message
transport. The extension adds a routing layer that selects the appropriate
pattern for each task, a set of pattern implementations that share common
iteration infrastructure, and a fan-out/fan-in mechanism for multi-agent
coordination.

The central design principle is that
**trust and explainability are structural properties of the architecture**,
achieved by constraining LLM decisions to
graph-defined option sets and recording those constraints in the execution
trace.

---

## Background

### Existing Architecture

The current agent manager is built on the ReACT pattern (Reasoning + Acting)
with these properties:

- **Self-queuing loop**: Each iteration emits a new Pulsar message carrying
  the accumulated history. The agent manager picks this up and runs the next
  iteration.
- **Stateless agent manager**: No in-process state. All state lives in the
  message payload.
- **Natural parallelism**: Multiple independent agent requests are handled
  concurrently across Pulsar consumers.
- **Durability**: Crash recovery is inherent — the message survives process
  failure.
- **Real-time feedback**: Streaming thought, action, observation and answer
  chunks are emitted as iterations complete.
- **Tool calling and MCP invocation**: Tool calls into knowledge graphs,
  external services, and MCP-connected systems.
- **Decision traces written to the knowledge graph**: Every iteration records
  PROV-O triples — session, analysis, and conclusion entities — forming the
  basis of explainability.

### Current Message Flow

```
AgentRequest arrives (question, history=[], state, group, session_id)
        │
        ▼
    Filter tools by group/state
        │
        ▼
    AgentManager.react() → LLM call → parse → Action or Final
        │                                          │
        │ [Action]                                 │ [Final]
        ▼                                          ▼
    Execute tool, capture observation          Emit conclusion triples
    Emit iteration triples                     Send AgentResponse
    Append to history                          (end_of_dialog=True)
    Emit new AgentRequest → "next" topic
        │
        └── (picked up again by consumer, loop continues)
```

The key insight is that this loop structure is not ReACT-specific. The
plumbing — receive message, do work, emit next message — is the same
regardless of what the "work" step does. The payload and the pattern logic
define the behaviour; the infrastructure remains constant.

### Current Limitations

- Only one execution pattern (ReACT) is available regardless of task
  characteristics.
- No mechanism for one agent to spawn and coordinate subagents.
- Pattern selection is implicit — every task gets the same treatment.
- The provenance model assumes a linear iteration chain (analysis N derives
  from analysis N-1), with no support for parallel branches.

---

## Design Goals

- **Pattern-agnostic iteration infrastructure**: The self-queuing loop, tool
  filtering, provenance emission, and streaming feedback should be shared
  across all patterns.
- **Graph-constrained pattern selection**: The LLM selects patterns from a
  graph-defined set, not from unconstrained reasoning. This makes the
  selection auditable and explainable.
- **Genuinely parallel fan-out**: Subagent tasks execute concurrently on the
  Pulsar queue, not sequentially in a single process.
- **Stateless coordination**: Fan-in uses the knowledge graph as coordination
  substrate. The agent manager remains stateless.
- **Additive change**: The existing ReACT flow continues to work
  unchanged. New patterns are added alongside it, not in place of it.

---

## Patterns

### ReACT as One Pattern Among Many

ReACT is one point in a wider space of agent execution strategies:

| Pattern | Structure | Strengths |
|---|---|---|
| **ReACT** | Interleaved reasoning and action | Adaptive, good for open-ended tasks |
| **Plan-then-Execute** | Decompose into a step DAG, then execute | More predictable, auditable plan |
| **Reflexion** | ReACT + self-critique after each action | Agents improve within the episode |
| **Supervisor/Subagent** | One agent orchestrates others | Parallel decomposition, synthesis |
| **Debate/Ensemble** | Multiple agents reason independently | Diverse perspectives, reconciliation |
| **LLM-as-router** | No reasoning loop, pure dispatch | Fast classification and routing |

Not all of these need to be implemented at once. The architecture should
support them; the initial implementation delivers ReACT (already exists),
Plan-then-Execute, and Supervisor/Subagent.

### Pattern Storage

Patterns are stored as configuration items via the config API. They are
finite in number, mechanically well-defined, have enumerable properties,
and change slowly. Each pattern is a JSON object stored under the
`agent-pattern` config type.

```json
Config type: "agent-pattern"
Config key:  "react"
Value: {
    "name": "react",
    "description": "ReACT — Reasoning + Acting",
    "when_to_use": "Adaptive, good for open-ended tasks"
}
```

These are written at deployment time and change rarely. If the architecture
later benefits from graph-based pattern storage (e.g. for richer ontological
relationships), the config items can be migrated to graph nodes — the
meta-router's selection logic is the same regardless of backend.

---

## Task Types

### What a Task Type Represents

A **task type** characterises the problem domain — what the agent is being
asked to accomplish, and how a domain expert would frame it analytically.

- Carries domain-specific methodology (e.g. "intelligence analysis always
  applies structured analytic techniques")
- Pre-populates initial reasoning context via a framing prompt
- Constrains which patterns are valid for this class of problem
- Can define domain-specific termination criteria

### Identification

Task types are identified from plain-text task descriptions by the
LLM. Building a formal ontology over task descriptions is premature — natural
language is too varied and context-dependent. The LLM reads the description;
the graph provides the structure downstream.

### Task Type Storage

Task types are stored as configuration items via the config API under the
`agent-task-type` config type. Each task type is a JSON object that
references valid patterns by name.

```json
Config type: "agent-task-type"
Config key:  "risk-assessment"
Value: {
    "name": "risk-assessment",
    "description": "Due Diligence / Risk Assessment",
    "framing_prompt": "Analyse across financial, reputational, legal and operational dimensions using structured analytic techniques.",
    "valid_patterns": ["supervisor", "plan-then-execute", "react"],
    "when_to_use": "Multi-dimensional analysis requiring structured assessment"
}
```

The `valid_patterns` list defines the constrained decision space — the LLM
can only select patterns that the task type's configuration says are valid.
This is the many-to-many relationship between task types and patterns,
expressed as configuration rather than graph edges.

### Selection Flow

```
Task Description (plain text, from AgentRequest.question)
        │
        │  [LLM interprets, constrained by available task types from config]
        ▼
Task Type (config item — domain framing and methodology)
        │
        │  [config lookup — valid_patterns list]
        ▼
Pattern Candidates (config items)
        │
        │  [LLM selects within constrained set,
        │   informed by task description signals:
        │   complexity, urgency, scope]
        ▼
Selected Pattern
```

The task description may carry modulating signals (complexity, urgency, scope)
that influence which pattern is selected within the constrained set. But the
raw description never directly selects a pattern — it always passes through
the task type layer first.

---

## Explainability Through Constrained Decision Spaces

A central principle of TrustGraph's explainability architecture is that
**explainability comes from constrained decision spaces**.

When a decision is made from an unconstrained space — a raw LLM call with no
guardrails — the reasoning is opaque even if the LLM produces a rationale,
because that rationale is post-hoc and unverifiable.

When a decision is made from a **constrained set defined in configuration**,
you can always answer:
- What valid options were available
- What criteria narrowed the set
- What signal made the final selection within that set

This principle already governs the existing decision trace architecture and
extends naturally to pattern selection. The routing decision — which task type
and which pattern — is itself recorded as a provenance node, making the first
decision in the execution trace auditable.

**Trust becomes a structural property of the architecture, not a claimed
property of the model.**

---

## Orchestration Architecture

### The Meta-Router

The meta-router is the entry point for all agent requests. It runs as a
pre-processing step before the pattern-specific iteration loop begins. Its
job is to determine the task type and select the execution pattern.

**When it runs**: On receipt of an `AgentRequest` with empty history (i.e. a
new task, not a continuation). Requests with non-empty history are already
mid-iteration and bypass the meta-router.

**What it does**:

1. Lists all available task types from the config API
   (`config.list("agent-task-type")`).
2. Presents these to the LLM alongside the task description. The LLM
   identifies which task type applies (or "general" as a fallback).
3. Reads the selected task type's configuration to get the `valid_patterns`
   list.
4. Loads the candidate pattern definitions from config and presents them to
   the LLM. The LLM selects one, influenced by signals in the task
   description (complexity, number of independent dimensions, urgency).
5. Records the routing decision as a provenance node (see Provenance Model
   below).
6. Populates the `AgentRequest` with the selected pattern, task type framing
   prompt, and any pattern-specific configuration, then emits it onto the
   queue.

**Where it lives**: The meta-router is a phase within the agent-orchestrator,
not a separate service. The agent-orchestrator is a new executable that
uses the same service identity as the existing agent-manager-react, making
it a drop-in replacement on the same Pulsar queues. It includes the full
ReACT implementation alongside the new orchestration patterns. The
distinction between "route" and "iterate" is determined by whether the
request already has a pattern set.

### Pattern Dispatch

Once the meta-router has annotated the request with a pattern, the agent
manager dispatches to the appropriate pattern implementation. This is a
straightforward branch on the pattern field:

```
request arrives
    │
    ├── history is empty → meta-router → annotate with pattern → re-emit
    │
    └── history is non-empty (or pattern is set)
            │
            ├── pattern = "react"              → ReACT iteration
            ├── pattern = "plan-then-execute"   → PtE iteration
            ├── pattern = "supervisor"          → Supervisor iteration
            └── (no pattern)                    → ReACT iteration (default)
```

Each pattern implementation follows the same contract: receive a request, do
one iteration of work, then either emit a "next" message (continue) or emit a
response (done). The self-queuing loop doesn't change.

### Pattern Implementations

#### ReACT (Existing)

No changes. The existing `AgentManager.react()` path continues to work
as-is.

#### Plan-then-Execute

Two-phase pattern:

**Planning phase** (first iteration):
- LLM receives the question plus task type framing.
- Produces a structured plan: an ordered list of steps, each with a goal,
  expected tool, and dependencies on prior steps.
- The plan is recorded in the history as a special "plan" step.
- Emits a "next" message to begin execution.

**Execution phase** (subsequent iterations):
- Reads the plan from history.
- Identifies the next unexecuted step.
- Executes that step (tool call + observation), similar to a single ReACT
  action.
- Records the result against the plan step.
- If all steps complete, synthesises a final answer.
- If a step fails or produces unexpected results, the LLM can revise the
  remaining plan (bounded re-planning, not a full restart).

The plan lives in the history, so it travels with the message. No external
state is needed.

#### Supervisor/Subagent

The supervisor pattern introduces fan-out and fan-in. This is the most
architecturally significant addition.

**Supervisor planning iteration**:
- LLM receives the question plus task type framing.
- Decomposes the task into independent subagent goals.
- For each subagent, emits a new `AgentRequest` with:
  - A focused question (the subagent's specific goal)
  - A shared correlation ID tying it to the parent task
  - The subagent's own pattern (typically ReACT, but could be anything)
  - Relevant context sliced from the parent request

**Subagent execution**:
- Each subagent request is picked up by an agent manager instance and runs its
  own independent iteration loop.
- Subagents are ordinary agent executions — they self-queue, use tools, emit
  provenance, stream feedback.
- When a subagent reaches a Final answer, it writes a completion record to the
  knowledge graph under the shared correlation ID.

**Fan-in and synthesis**:
- An aggregator detects when all sibling subagents for a correlation ID have
  completed.
- It emits a synthesis request to the supervisor carrying the correlation ID.
- The supervisor queries the graph for subagent results, reasons across them,
  and decides whether to emit a final answer or iterate again.

**Supervisor re-iteration**:
- After synthesis, the supervisor may determine that the results are
  incomplete, contradictory, or reveal gaps requiring further investigation.
- Rather than emitting a final answer, it can fan out again with new or
  refined subagent goals under a new correlation ID. This is the same
  self-queuing loop — the supervisor emits new subagent requests and stops,
  the aggregator detects completion, and synthesis runs again.
- The supervisor's iteration count (planning + synthesis rounds) is bounded
  to prevent unbounded looping.

This is detailed further in the Fan-Out / Fan-In section below.

---

## Message Schema Evolution

### Shared Schema Principle

The `AgentRequest` and `AgentResponse` schemas are the shared contract
between the agent-manager (existing ReACT execution) and the
agent-orchestrator (meta-routing, supervisor, plan-then-execute). Both
services consume from the same *agent request* topic using the same
schema. Any schema changes must be reflected in both — the schema is
the integration point, not the service implementation.

This means the orchestrator does not introduce separate message types for
its own use. Subagent requests, synthesis triggers, and meta-router
outputs are all `AgentRequest` messages with different field values. The
agent-manager ignores orchestration fields it doesn't use.

### New Fields

The `AgentRequest` schema needs new fields to carry orchestration
metadata.

```python
@dataclass
class AgentRequest:
    # Existing fields (unchanged)
    question: str = ""
    state: str = ""
    group: list[str] | None = None
    history: list[AgentStep] = field(default_factory=list)
    user: str = ""
    collection: str = "default"
    streaming: bool = False
    session_id: str = ""

    # New orchestration fields
    conversation_id: str = ""               # Optional caller-generated ID grouping related requests
    pattern: str = ""                       # "react", "plan-then-execute", "supervisor", ""
    task_type: str = ""                     # Identified task type name
    framing: str = ""                       # Task type framing prompt injected into LLM context
    correlation_id: str = ""                # Shared ID linking subagents to parent
    parent_session_id: str = ""             # Parent's session_id (for subagents)
    subagent_goal: str = ""                 # Focused goal for this subagent
    expected_siblings: int = 0              # How many sibling subagents exist
```

The `AgentStep` schema also extends to accommodate non-ReACT iteration types:

```python
@dataclass
class AgentStep:
    # Existing fields (unchanged)
    thought: str = ""
    action: str = ""
    arguments: dict[str, str] = field(default_factory=dict)
    observation: str = ""
    user: str = ""

    # New fields
    step_type: str = ""                     # "react", "plan", "execute", "supervise", "synthesise"
    plan: list[PlanStep] | None = None      # For plan-then-execute: the structured plan
    subagent_results: dict | None = None    # For supervisor: collected subagent outputs
```

The `PlanStep` structure for Plan-then-Execute:

```python
@dataclass
class PlanStep:
    goal: str = ""                          # What this step should accomplish
    tool_hint: str = ""                     # Suggested tool (advisory, not binding)
    depends_on: list[int] = field(default_factory=list)  # Indices of prerequisite steps
    status: str = "pending"                 # "pending", "complete", "failed", "revised"
    result: str = ""                        # Observation from execution
```

---

## Fan-Out and Fan-In

### Why This Matters

Fan-out is the mechanism that makes multi-agent coordination genuinely
parallel rather than simulated. With Pulsar, emitting multiple messages means
multiple consumers can pick them up concurrently. This is not threading or
async simulation — it is real distributed parallelism across agent manager
instances.

### Fan-Out: Supervisor Emits Subagent Requests

When a supervisor iteration decides to decompose a task, it:

1. Generates a **correlation ID** — a UUID that groups the sibling subagents.
2. For each subagent, constructs a new `AgentRequest`:
   - `question` = the subagent's focused goal (from `subagent_goal`)
   - `correlation_id` = the shared correlation ID
   - `parent_session_id` = the supervisor's session_id
   - `pattern` = typically "react", but the supervisor can specify any pattern
   - `session_id` = a new unique ID for this subagent's own provenance chain
   - `expected_siblings` = total number of sibling subagents
   - `history` = empty (fresh start, but framing context inherited)
   - `group`, `user`, `collection` = inherited from parent
3. Emits each subagent request onto the agent request topic.
4. Records the fan-out decision in the provenance graph (see below).

The supervisor then **stops**. It does not wait. It does not poll. It has
emitted its messages and its iteration is complete. The graph and the
aggregator handle the rest.

### Fan-In: Graph-Based Completion Detection

When a subagent reaches its Final answer, it writes a **completion node** to
the knowledge graph:

```
Completion node:
    rdf:type                  tg:SubagentCompletion
    tg:correlationId          <shared correlation ID>
    tg:subagentSessionId      <this subagent's session_id>
    tg:parentSessionId        <supervisor's session_id>
    tg:subagentGoal           <what this subagent was asked to do>
    tg:result                 → <document URI in librarian>
    prov:wasGeneratedBy       → <this subagent's conclusion entity>
```

The **aggregator** is a component that watches for completion nodes. When it
detects that all expected siblings for a correlation ID have written
completion nodes, it:

1. Collects all sibling results from the graph and librarian.
2. Constructs a **synthesis request** — a new `AgentRequest` addressed to the supervisor flow:
   - `session_id` = the original supervisor's session_id
   - `pattern` = "supervisor"
   - `step_type` = "synthesise" (carried in history)
   - `subagent_results` = the collected findings
   - `history` = the supervisor's history up to the fan-out point, plus the synthesis step
3. Emits this onto the agent request topic.

The supervisor picks this up, reasons across the aggregated findings, and
produces its final answer.

### Aggregator Design

The aggregator is event-driven, consistent with TrustGraph's Pulsar-based
architecture. Polling would be an anti-pattern in a system where all
coordination is message-driven.

**Mechanism**: The aggregator is a Pulsar consumer on the explainability
topic. Subagent completion nodes are emitted as triples on this topic as
part of the existing provenance flow. When the aggregator receives a
`tg:SubagentCompletion` triple, it:

1. Extracts the `tg:correlationId` from the completion node.
2. Queries the graph to count how many siblings for that correlation ID
   have completed.
3. If all `expected_siblings` are present, triggers fan-in immediately —
   collects results and emits the synthesis request.

**State**: The aggregator is stateless in the same sense as the agent
manager — it holds no essential in-memory state. The graph is the source
of truth for completion counts. If the aggregator restarts, it can
re-process unacknowledged completion messages from Pulsar and re-check the
graph. No coordination state is lost.

**Consistency**: Because the completion check queries the graph rather than
relying on an in-memory counter, the aggregator is tolerant of duplicate
messages, out-of-order delivery, and restarts. The graph query is
idempotent — asking "are all siblings complete?" gives the same answer
regardless of how many times or in what order the events arrive.

### Timeout and Failure

- **Subagent timeout**: The aggregator records the timestamp of the first
  sibling completion (from the graph). A periodic timeout check (the one
  concession to polling — but over local state, not the graph) detects
  stalled correlation IDs. If `expected_siblings` completions are not
  reached within a configurable timeout, the aggregator emits a partial
  synthesis request with whatever results are available, flagging the
  incomplete subagents.
- **Subagent failure**: If a subagent errors out, it writes an error
  completion node (with `tg:status = "error"` and an error message). The
  aggregator treats this as a completion — the supervisor receives the error
  in its synthesis input and can reason about partial results.
- **Supervisor iteration limit**: The supervisor's own iteration count
  (planning + synthesis) is bounded by `max_iterations` just like any other
  pattern.

---

## Provenance Model Extensions

### Routing Decision

The meta-router's task type and pattern selection is recorded as the first
provenance node in the session:

```
Routing node:
    rdf:type                  prov:Entity, tg:RoutingDecision
    prov:wasGeneratedBy       → session (Question) activity
    tg:taskType               → TaskType node URI
    tg:selectedPattern        → Pattern node URI
    tg:candidatePatterns      → [Pattern node URIs]  (what was available)
    tg:routingRationale       → document URI in librarian (LLM's reasoning)
```

This captures the constrained decision space: what candidates existed, which
was selected, and why. The candidates are graph-derived; the rationale is
LLM-generated but verifiable against the candidates.

### Fan-Out Provenance

When a supervisor fans out, the provenance records the decomposition:

```
FanOut node:
    rdf:type                  prov:Entity, tg:FanOut
    prov:wasDerivedFrom       → supervisor's routing or planning iteration
    tg:correlationId          <correlation ID>
    tg:subagentGoals          → [document URIs for each subagent goal]
    tg:expectedSiblings       <count>
```

Each subagent's provenance chain is independent (its own session, iterations,
conclusion) but linked back to the parent via:

```
Subagent session:
    rdf:type                  prov:Activity, tg:Question, tg:AgentQuestion
    tg:parentCorrelationId    <correlation ID>
    tg:parentSessionId        <supervisor session URI>
```

### Fan-In Provenance

The synthesis step links back to all subagent conclusions:

```
Synthesis node:
    rdf:type                  prov:Entity, tg:Synthesis
    prov:wasDerivedFrom       → [all subagent Conclusion entities]
    tg:correlationId          <correlation ID>
```

This creates a DAG in the provenance graph: the supervisor's routing fans out
to N parallel subagent chains, which fan back in to a synthesis node. The
entire multi-agent execution is traceable from a single correlation ID.

### URI Scheme

Extending the existing `urn:trustgraph:agent:{session_id}` pattern:

| Entity | URI Pattern |
|---|---|
| Session (existing) | `urn:trustgraph:agent:{session_id}` |
| Iteration (existing) | `urn:trustgraph:agent:{session_id}/i{n}` |
| Conclusion (existing) | `urn:trustgraph:agent:{session_id}/answer` |
| Routing decision | `urn:trustgraph:agent:{session_id}/routing` |
| Fan-out record | `urn:trustgraph:agent:{session_id}/fanout/{correlation_id}` |
| Subagent completion | `urn:trustgraph:agent:{session_id}/completion` |

---

## Storage Responsibilities

Pattern and task type definitions live in the config API. Runtime state and
provenance live in the knowledge graph. The division is:

| Role | Storage | When Written | Content |
|---|---|---|---|
| Pattern definitions | Config API | At design time | Pattern properties, descriptions |
| Task type definitions | Config API | At design time | Domain framing, valid pattern lists |
| Routing decision trace | Knowledge graph | At request arrival | Why this task type and pattern were selected |
| Iteration decision trace | Knowledge graph | During execution | Each think/act/observe cycle, per existing model |
| Fan-out coordination | Knowledge graph | During fan-out | Subagent goals, correlation ID, expected count |
| Subagent completion | Knowledge graph | During fan-in | Per-subagent results under shared correlation ID |
| Execution audit trail | Knowledge graph | Post-execution | Full multi-agent reasoning trace as a DAG |

The config API holds the definitions that constrain decisions. The knowledge
graph holds the runtime decisions and their provenance. The fan-in
coordination state is part of the provenance automatically — subagent
completion nodes are both coordination signals and audit trail entries.

---

## Worked Example: Partner Risk Assessment

**Request**: "Assess the risk profile of Company X as a potential partner"

**1. Request arrives** on the *agent request* topic with empty history.
The agent manager picks it up.

**2. Meta-router**:
- Queries config API, finds task types: *Risk Assessment*, *Research*,
  *Summarisation*, *General*.
- LLM identifies *Risk Assessment*. Framing prompt loaded: "analyse across
  financial, reputational, legal and operational dimensions using structured
  analytic techniques."
- Valid patterns for *Risk Assessment*: [*Supervisor/Subagent*,
  *Plan-then-Execute*, *ReACT*].
- LLM selects *Supervisor/Subagent* — task has four independent investigative
  dimensions, well-suited to parallel decomposition.
- Routing decision written to graph. Request re-emitted on the
  *agent request* topic with `pattern="supervisor"`, framing populated.

**3. Supervisor iteration** (picked up from *agent request* topic):
- LLM receives question + framing. Reasons that four independent investigative
  threads are required.
- Generates correlation ID `corr-abc123`.
- Emits four subagent requests on the *agent request* topic:
  - Financial analysis (pattern="react", subagent_goal="Analyse financial
    health and stability of Company X")
  - Legal analysis (pattern="react", subagent_goal="Review regulatory filings,
    sanctions, and legal exposure for Company X")
  - Reputational analysis (pattern="react", subagent_goal="Analyse news
    sentiment and public reputation of Company X")
  - Operational analysis (pattern="react", subagent_goal="Assess supply chain
    dependencies and operational risks for Company X")
- Fan-out node written to graph.

**4. Four subagents run in parallel** (each picked up from the *agent
request* topic by agent manager instances), each as an independent ReACT
loop:
- Financial — queries financial data services and knowledge graph
  relationships
- Legal — searches regulatory filings and sanctions lists
- Reputational — searches news, analyses sentiment
- Operational — queries supply chain databases

Each self-queues its iterations on the *agent request* topic. Each writes
its own decision trace to the graph as it progresses. Each completes
independently.

**5. Fan-in**:
- Each subagent writes a `tg:SubagentCompletion` node to the graph on
  completion, emitted on the *explainability* topic. The completion node
  references the subagent's result document in the librarian.
- Aggregator (consuming the *explainability* topic) sees each completion
  event. It queries the graph for the fan-out node to get the expected
  sibling count, then checks how many completions exist for
  `corr-abc123`.
- When all four siblings are complete, the aggregator emits a synthesis
  request on the *agent request* topic with the correlation ID. It does
  not fetch or bundle subagent results — the supervisor will query the
  graph for those.

**6. Supervisor synthesis** (picked up from *agent request* topic):
- Receives the synthesis trigger carrying the correlation ID.
- Queries the graph for `tg:SubagentCompletion` nodes under
  `corr-abc123`, retrieving each subagent's goal and result document
  reference.
- Fetches the result documents from the librarian.
- Reasons across all four dimensions, produces a structured risk
  assessment with confidence scores.
- Emits final answer on the *agent response* topic and writes conclusion
  provenance to the graph.

**7. Response delivered** — the supervisor's synthesis streams on the
*agent response* topic as the LLM generates it, with `end_of_dialog`
on the final chunk. The collated answer is saved to the librarian and
referenced from conclusion provenance in the graph. The graph now holds
a complete, human-readable trace of the entire multi-agent execution —
from pattern selection through four parallel investigations to final
synthesis.

---

## Class Hierarchy

The agent-orchestrator executable (`agent-orchestrator`) uses the same
service identity as agent-manager-react, making it a drop-in replacement.
The pattern dispatch model suggests a class hierarchy where shared iteration
infrastructure lives in a base class and pattern-specific logic is in
subclasses:

```
AgentService (base — Pulsar consumer/producer specs, request handling)
    │
    └── Processor (agent-orchestrator service)
            │
            ├── MetaRouter        — task type identification, pattern selection
            │
            ├── PatternBase       — shared: tool filtering, provenance, streaming, history
            │   ├── ReactPattern          — existing ReACT logic (extract from current AgentManager)
            │   ├── PlanThenExecutePattern — plan phase + execute phase
            │   └── SupervisorPattern     — fan-out, synthesis
            │
            └── Aggregator        — fan-in completion detection
```

`PatternBase` captures what is currently spread across `Processor` and
`AgentManager`: tool filtering, LLM invocation, provenance triple emission,
streaming callbacks, history management. The pattern subclasses implement only
the decision logic specific to their execution strategy — what to do with the
LLM output, when to terminate, whether to fan out.

This refactoring is not strictly necessary for the first iteration — the
meta-router and pattern dispatch could be added as branches within the
existing `Processor.agent_request()` method. But the class hierarchy clarifies
where shared vs. pattern-specific logic lives and will prevent duplication as
more patterns are added.

---

## Configuration

### Config API Seeding

Pattern and task type definitions are stored via the config API and need to
be seeded at deployment time. This is analogous to how flow blueprints and
parameter types are loaded — a bootstrap step that writes the initial
configuration.

The initial seed includes:

**Patterns** (config type `agent-pattern`):
- `react` — interleaved reasoning and action
- `plan-then-execute` — structured plan followed by step execution
- `supervisor` — decomposition, fan-out to subagents, synthesis

**Task types** (config type `agent-task-type`, initial set, expected to grow):
- `general` — no specific domain framing, all patterns valid
- `research` — open-ended investigation, valid patterns: react, plan-then-execute
- `risk-assessment` — multi-dimensional analysis, valid patterns: supervisor,
  plan-then-execute, react
- `summarisation` — condense information, valid patterns: react

The seed data is configuration, not code. It can be extended via the config
API (or the configuration UI) without redeploying the agent manager.

### Migration Path

The config API provides a practical starting point. If richer ontological
relationships between patterns, task types, and domain knowledge become
valuable, the definitions can be migrated to graph storage. The meta-router's
selection logic queries an abstract set of task types and patterns — the
storage backend is an implementation detail.

### Fallback Behaviour

If the config contains no patterns or task types:
- Task type defaults to `general`.
- Pattern defaults to `react`.
- The system degrades gracefully to existing behaviour.

---

## Design Decisions

| Decision | Resolution | Rationale |
|---|---|---|
| Task type identification | LLM interprets from plain text | Natural language too varied to formalise prematurely |
| Pattern/task type storage | Config API initially, graph later if needed | Avoids graph model complexity upfront; config API already has UI support; migration path is straightforward |
| Meta-router location | Phase within agent manager, not separate service | Avoids an extra network hop; routing is fast |
| Fan-in mechanism | Event-driven via explainability topic | Consistent with Pulsar-based architecture; graph query for completion count is idempotent and restart-safe |
| Aggregator deployment | Separate lightweight process | Decoupled from agent manager lifecycle |
| Subagent pattern selection | Supervisor specifies per-subagent | Supervisor has task context to make this choice |
| Plan storage | In message history | No external state needed; plan travels with message |
| Default pattern | Empty pattern field → ReACT | Sensible default when meta-router is not configured |

---

## Streaming Protocol

### Current Model

The existing agent response schema has two levels:

- **`end_of_message`** — marks the end of a complete thought, observation,
  or answer. Chunks belonging to the same message arrive sequentially.
- **`end_of_dialog`** — marks the end of the entire agent execution. No
  more messages will follow.

This works because the current system produces messages serially — one
thought at a time, one agent at a time.

### Fan-Out Breaks Serial Assumptions

With supervisor/subagent fan-out, multiple subagents stream chunks
concurrently on the same *agent response* topic. The caller receives
interleaved chunks from different sources and needs to demultiplex them.

### Resolution: Message ID

Each chunk carries a `message_id` — a per-message UUID generated when
the agent begins streaming a new thought, observation, or answer. The
caller groups chunks by `message_id` and assembles each message
independently.

```
Response chunk fields:
    message_id          UUID for this message (groups chunks)
    session_id          Which agent session produced this chunk
    message_type          "thought" | "observation" | "answer" | ...
    content             The chunk text
    end_of_message      True on the final chunk of this message
    end_of_dialog       True on the final message of the entire execution
```

A single subagent emits multiple messages (thought, observation, thought,
answer), each with a distinct `message_id`. The `session_id` identifies
which subagent the message belongs to. The caller can display, group, or
filter by either.

### Provenance Trigger

`end_of_message` is the trigger for provenance storage. When a complete
message has been assembled from its chunks:

1. The collated text is saved to the librarian as a single document.
2. A provenance node is written to the graph referencing the document URI.

This follows the pattern established by GraphRAG, where streaming synthesis
chunks are delivered live but the stored provenance references the collated
answer text. Streaming is for the caller; provenance needs complete messages.

---

## Open Questions

- **Re-planning depth** (resolved): Runtime parameter on the
  agent-orchestrator executable, default 2. Bounds how many times
  Plan-then-Execute can revise its plan before forcing termination.
- **Nested fan-out** (phase B): A subagent can itself be a supervisor
  that fans out further. The architecture supports this — correlation IDs
  are independent and the aggregator is stateless. The protocols and
  message schema should not preclude nested fan-out, but implementation
  is deferred. Depth limits will need to be enforced to prevent runaway
  decomposition.
- **Task type evolution** (resolved): Manually curated for now. See
  Future Directions below for automated discovery.
- **Cost attribution** (deferred): Costs are measured at the
  text-completion queue level as they are today. Per-request attribution
  across subagents is not yet implemented and is not a blocker for
  orchestration.
- **Conversation ID** (resolved): An optional `conversation_id` field on
  `AgentRequest`, generated by the caller. When present, all objects
  created during the execution (provenance nodes, librarian documents,
  subagent completion records) are tagged with the conversation ID. This
  enables querying all interactions in a conversation with a single
  lookup, and provides the foundation for conversation-scoped memory.
  No explicit open/close — the first request with a new conversation ID
  implicitly starts the conversation. Omit for one-shot queries.
- **Tool scoping per subagent** (resolved): Subagents inherit the
  parent's tool group by default. The supervisor can optionally override
  the group per subagent to constrain capabilities (e.g. financial
  subagent gets only financial tools). The `group` field on
  `AgentRequest` already supports this — the supervisor just sets it
  when constructing subagent requests.

---

## Future Directions

### Automated Task Type Discovery

Task types are manually curated in the initial implementation. However,
the architecture is well-suited to automated discovery because all agent
requests and their execution traces flow through Pulsar topics. A
learning service could consume these messages and analyse patterns in
how tasks are framed, which patterns are selected, and how successfully
they execute. Over time, it could propose new task types based on
clusters of similar requests that don't map well to existing types, or
suggest refinements to framing prompts based on which framings lead to
better outcomes. This service would write proposed task types to the
config API for human review — automated discovery, manual approval. The
agent-orchestrator does not need to change; it always reads task types
from config regardless of how they got there.
