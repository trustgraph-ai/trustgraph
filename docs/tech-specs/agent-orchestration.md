# TrustGraph Agent Orchestration — Technical Specification

## Overview

This specification describes the extension of TrustGraph's agent architecture from a single ReACT execution pattern to a multi-pattern orchestration model. The existing Pulsar-based self-queuing loop is pattern-agnostic — the same infrastructure supports ReACT, Plan-then-Execute, Supervisor/Subagent fan-out, and other execution strategies without changes to the message transport. The extension adds a routing layer that selects the appropriate pattern for each task, a set of pattern implementations that share common iteration infrastructure, and a fan-out/fan-in mechanism for multi-agent coordination.

The central design principle is that **trust and explainability are structural properties of the architecture**, achieved by constraining LLM decisions to graph-defined option sets and recording those constraints in the execution trace.

---

## Background

### Existing Architecture

The current agent manager is built on the ReACT pattern (Reasoning + Acting) with these properties:

- **Self-queuing loop**: Each iteration emits a new Pulsar message carrying the accumulated history. The agent manager picks this up and runs the next iteration.
- **Stateless agent manager**: No in-process state. All state lives in the message payload.
- **Natural parallelism**: Multiple independent agent requests are handled concurrently across Pulsar consumers.
- **Durability**: Crash recovery is inherent — the message survives process failure.
- **Real-time feedback**: Streaming thought, action, observation and answer chunks are emitted as iterations complete.
- **Tool calling and MCP invocation**: Tool calls into knowledge graphs, external services, and MCP-connected systems.
- **Decision traces written to the knowledge graph**: Every iteration records PROV-O triples — session, analysis, and conclusion entities — forming the basis of explainability.

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

The key insight is that this loop structure is not ReACT-specific. The plumbing — receive message, do work, emit next message — is the same regardless of what the "work" step does. The payload and the pattern logic define the behaviour; the infrastructure remains constant.

### Current Limitations

- Only one execution pattern (ReACT) is available regardless of task characteristics.
- No mechanism for one agent to spawn and coordinate subagents.
- Pattern selection is implicit — every task gets the same treatment.
- The provenance model assumes a linear iteration chain (analysis N derives from analysis N-1), with no support for parallel branches.

---

## Design Goals

- **Pattern-agnostic iteration infrastructure**: The self-queuing loop, tool filtering, provenance emission, and streaming feedback should be shared across all patterns.
- **Graph-constrained pattern selection**: The LLM selects patterns from a graph-defined set, not from unconstrained reasoning. This makes the selection auditable and explainable.
- **Genuinely parallel fan-out**: Subagent tasks execute concurrently on the Pulsar queue, not sequentially in a single process.
- **Stateless coordination**: Fan-in uses the knowledge graph as coordination substrate. The agent manager remains stateless.
- **Additive change**: The existing ReACT flow continues to work unchanged. New patterns are added alongside it, not in place of it.

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

Not all of these need to be implemented at once. The architecture should support them; the initial implementation delivers ReACT (already exists), Plan-then-Execute, and Supervisor/Subagent.

### Pattern Representation in the Graph

Patterns are well-suited to graph representation: they are finite in number, mechanically well-defined, have enumerable properties, and change slowly. Each pattern is a node in the knowledge graph with properties that describe its execution behaviour.

```
Pattern node:
    rdf:type              tg:AgentPattern
    tg:patternName        "react" | "plan-then-execute" | "supervisor" | ...
    tg:supportsStreaming   true | false
    tg:supportsFanOut      true | false
    tg:maxIterations       <default iteration limit>
    rdfs:label             "ReACT — Reasoning + Acting"
    rdfs:comment           <human-readable description of when to use>
```

These nodes are written at design time and change rarely. They form part of the system ontology, not runtime state.

---

## Task Types

### What a Task Type Represents

A **task type** characterises the problem domain — what the agent is being asked to accomplish, and how a domain expert would frame it analytically.

- Carries domain-specific methodology (e.g. "intelligence analysis always applies structured analytic techniques")
- Pre-populates initial reasoning context via a framing prompt
- Constrains which patterns are valid for this class of problem
- Can define domain-specific termination criteria

### Identification

Task types are identified from plain-text task descriptions by the LLM. Building a formal ontology over task descriptions is premature — natural language is too varied and context-dependent. The LLM reads the description; the graph provides the structure downstream.

### Task Type Representation in the Graph

```
TaskType node:
    rdf:type                tg:AgentTaskType
    tg:taskTypeName         "risk-assessment" | "research" | "summarisation" | ...
    tg:framingPrompt        <domain methodology and framing instructions>
    tg:validPatterns        → [Pattern nodes]   (edge: tg:supportsPattern)
    rdfs:label              "Due Diligence / Risk Assessment"
    rdfs:comment            <when this task type applies>
```

The `tg:supportsPattern` edges define the many-to-many relationship between task types and patterns. This is the constrained decision space — the LLM can only select patterns that the graph says are valid for the identified task type.

### Selection Flow

```
Task Description (plain text, from AgentRequest.question)
        │
        │  [LLM interprets, constrained by available TaskType nodes]
        ▼
Task Type (graph node — domain framing and methodology)
        │
        │  [graph query — tg:supportsPattern edges]
        ▼
Pattern Candidates (graph nodes)
        │
        │  [LLM selects within constrained set,
        │   informed by task description signals:
        │   complexity, urgency, scope]
        ▼
Selected Pattern
```

The task description may carry modulating signals (complexity, urgency, scope) that influence which pattern is selected within the constrained set. But the raw description never directly selects a pattern — it always passes through the task type layer first.

---

## Explainability Through Constrained Decision Spaces

A central principle of TrustGraph's explainability architecture is that **explainability comes from constrained decision spaces**.

When a decision is made from an unconstrained space — a raw LLM call with no guardrails — the reasoning is opaque even if the LLM produces a rationale, because that rationale is post-hoc and unverifiable.

When a decision is made from a **graph-defined constrained set**, you can always answer:
- What valid options were available
- What criteria narrowed the set
- What signal made the final selection within that set

This principle already governs the existing decision trace architecture and extends naturally to pattern selection. The routing decision — which task type and which pattern — is itself recorded as a provenance node, making the first decision in the execution trace auditable.

**Trust becomes a structural property of the architecture, not a claimed property of the model.**

---

## Orchestration Architecture

### The Meta-Router

The meta-router is the entry point for all agent requests. It runs as a pre-processing step before the pattern-specific iteration loop begins. Its job is to determine the task type and select the execution pattern.

**When it runs**: On receipt of an `AgentRequest` with empty history (i.e. a new task, not a continuation). Requests with non-empty history are already mid-iteration and bypass the meta-router.

**What it does**:

1. Queries the graph for all available `tg:AgentTaskType` nodes.
2. Presents these to the LLM alongside the task description. The LLM identifies which task type applies (or "general" as a fallback).
3. Queries the graph for valid patterns via `tg:supportsPattern` edges from the selected task type.
4. Presents the candidate patterns to the LLM. The LLM selects one, influenced by signals in the task description (complexity, number of independent dimensions, urgency).
5. Records the routing decision as a provenance node (see Provenance Model below).
6. Populates the `AgentRequest` with the selected pattern, task type framing prompt, and any pattern-specific configuration, then emits it onto the queue.

**Where it lives**: The meta-router is a phase within the agent manager, not a separate service. It shares the same Pulsar consumer — the distinction between "route" and "iterate" is determined by whether the request has history.

### Pattern Dispatch

Once the meta-router has annotated the request with a pattern, the agent manager dispatches to the appropriate pattern implementation. This is a straightforward branch on the pattern field:

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
            └── (no pattern / legacy)           → ReACT iteration (backward compat)
```

Each pattern implementation follows the same contract: receive a request, do one iteration of work, then either emit a "next" message (continue) or emit a response (done). The self-queuing loop doesn't change.

### Pattern Implementations

#### ReACT (Existing)

No changes. The existing `AgentManager.react()` path continues to work as-is. Requests without a pattern field default to ReACT for backward compatibility.

#### Plan-then-Execute

Two-phase pattern:

**Planning phase** (first iteration):
- LLM receives the question plus task type framing.
- Produces a structured plan: an ordered list of steps, each with a goal, expected tool, and dependencies on prior steps.
- The plan is recorded in the history as a special "plan" step.
- Emits a "next" message to begin execution.

**Execution phase** (subsequent iterations):
- Reads the plan from history.
- Identifies the next unexecuted step.
- Executes that step (tool call + observation), similar to a single ReACT action.
- Records the result against the plan step.
- If all steps complete, synthesises a final answer.
- If a step fails or produces unexpected results, the LLM can revise the remaining plan (bounded re-planning, not a full restart).

The plan lives in the history, so it travels with the message. No external state is needed.

#### Supervisor/Subagent

The supervisor pattern introduces fan-out and fan-in. This is the most architecturally significant addition.

**Supervisor planning iteration**:
- LLM receives the question plus task type framing.
- Decomposes the task into independent subagent goals.
- For each subagent, emits a new `AgentRequest` with:
  - A focused question (the subagent's specific goal)
  - A shared correlation ID tying it to the parent task
  - The subagent's own pattern (typically ReACT, but could be anything)
  - Relevant context sliced from the parent request

**Subagent execution**:
- Each subagent request is picked up by an agent manager instance and runs its own independent iteration loop.
- Subagents are ordinary agent executions — they self-queue, use tools, emit provenance, stream feedback.
- When a subagent reaches a Final answer, it writes a completion record to the knowledge graph under the shared correlation ID.

**Fan-in and synthesis**:
- An aggregator detects when all sibling subagents for a correlation ID have completed.
- It collects their results and emits a synthesis message back to the supervisor flow.
- The supervisor receives the aggregated findings, reasons across them, and produces the final answer.

This is detailed further in the Fan-Out / Fan-In section below.

---

## Message Schema Evolution

The `AgentRequest` schema needs new fields to carry orchestration metadata. These are additive — existing fields retain their meaning.

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

### Backward Compatibility

Requests with `pattern=""` (or absent) default to ReACT. The meta-router only runs for new requests (empty history). Existing callers that send plain `AgentRequest` messages with just `question` and `history` continue to work without modification.

---

## Fan-Out and Fan-In

### Why This Matters

Fan-out is the mechanism that makes multi-agent coordination genuinely parallel rather than simulated. With Pulsar, emitting multiple messages means multiple consumers can pick them up concurrently. This is not threading or async simulation — it is real distributed parallelism across agent manager instances.

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

The supervisor then **stops**. It does not wait. It does not poll. It has emitted its messages and its iteration is complete. The graph and the aggregator handle the rest.

### Fan-In: Graph-Based Completion Detection

When a subagent reaches its Final answer, it writes a **completion node** to the knowledge graph:

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

The **aggregator** is a component that watches for completion nodes. When it detects that all expected siblings for a correlation ID have written completion nodes, it:

1. Collects all sibling results from the graph and librarian.
2. Constructs a **synthesis request** — a new `AgentRequest` addressed to the supervisor flow:
   - `session_id` = the original supervisor's session_id
   - `pattern` = "supervisor"
   - `step_type` = "synthesise" (carried in history)
   - `subagent_results` = the collected findings
   - `history` = the supervisor's history up to the fan-out point, plus the synthesis step
3. Emits this onto the agent request topic.

The supervisor picks this up, reasons across the aggregated findings, and produces its final answer.

### Aggregator Design

The aggregator can be implemented as:

- **A periodic graph query**: A lightweight process that polls the graph for correlation IDs with all siblings complete. Simple, stateless, tolerant of restarts.
- **A Pulsar consumer on the explainability topic**: Since completion nodes are emitted as triples on the explainability topic, the aggregator can consume these and maintain an in-memory count. Faster than polling, but requires the aggregator to be running.

The polling approach is preferred initially — it aligns with the stateless design principle and is simpler to reason about. The aggregator has no state of its own; the graph is the source of truth.

### Timeout and Failure

- **Subagent timeout**: The aggregator tracks the timestamp of the first sibling completion. If `expected_siblings` completions are not reached within a configurable timeout, it emits a partial synthesis request with whatever results are available, flagging the incomplete subagents.
- **Subagent failure**: If a subagent errors out, it writes an error completion node (with `tg:status = "error"` and an error message). The aggregator treats this as a completion — the supervisor receives the error in its synthesis input and can reason about partial results.
- **Supervisor iteration limit**: The supervisor's own iteration count (planning + synthesis) is bounded by `max_iterations` just like any other pattern.

---

## Provenance Model Extensions

### Routing Decision

The meta-router's task type and pattern selection is recorded as the first provenance node in the session:

```
Routing node:
    rdf:type                  prov:Entity, tg:RoutingDecision
    prov:wasGeneratedBy       → session (Question) activity
    tg:taskType               → TaskType node URI
    tg:selectedPattern        → Pattern node URI
    tg:candidatePatterns      → [Pattern node URIs]  (what was available)
    tg:routingRationale       → document URI in librarian (LLM's reasoning)
```

This captures the constrained decision space: what candidates existed, which was selected, and why. The candidates are graph-derived; the rationale is LLM-generated but verifiable against the candidates.

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

Each subagent's provenance chain is independent (its own session, iterations, conclusion) but linked back to the parent via:

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

This creates a DAG in the provenance graph: the supervisor's routing fans out to N parallel subagent chains, which fan back in to a synthesis node. The entire multi-agent execution is traceable from a single correlation ID.

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

## The Knowledge Graph as Connective Tissue

The knowledge graph plays multiple roles simultaneously across the execution lifecycle:

| Role | When Written | Content |
|---|---|---|
| Pattern ontology | At design time | Pattern nodes, properties, valid task-type mappings |
| Task type ontology | At design time | Task type nodes, domain framing, pattern constraints |
| Routing decision trace | At request arrival | Why this task type and pattern were selected |
| Iteration decision trace | During execution | Each think/act/observe cycle, per existing model |
| Fan-out coordination | During fan-out | Subagent goals, correlation ID, expected count |
| Subagent completion | During fan-in | Per-subagent results under shared correlation ID |
| Execution audit trail | Post-execution | Full multi-agent reasoning trace as a DAG |

These are not separate mechanisms — they are all nodes and edges written at different points in the execution lifecycle on the same substrate. The fan-in coordination state *is* part of the explanation automatically.

---

## Worked Example: Partner Risk Assessment

**Request**: "Assess the risk profile of Company X as a potential partner"

**1. Request arrives** on the Pulsar input topic with a new task ID and empty history.

**2. Meta-router**:
- Queries graph, finds TaskType nodes: *Risk Assessment*, *Research*, *Summarisation*, *General*.
- LLM identifies *Risk Assessment*. Framing prompt loaded: "analyse across financial, reputational, legal and operational dimensions using structured analytic techniques."
- Valid patterns for *Risk Assessment*: [*Supervisor/Subagent*, *Plan-then-Execute*, *ReACT*].
- LLM selects *Supervisor/Subagent* — task has four independent investigative dimensions, well-suited to parallel decomposition.
- Routing decision written to graph. Request re-emitted with `pattern="supervisor"`, framing populated.

**3. Supervisor iteration**:
- LLM receives question + framing. Reasons that four independent investigative threads are required.
- Generates correlation ID `corr-abc123`.
- Emits four `AgentRequest` messages:
  - Financial analysis (pattern="react", subagent_goal="Analyse financial health and stability of Company X")
  - Legal analysis (pattern="react", subagent_goal="Review regulatory filings, sanctions, and legal exposure for Company X")
  - Reputational analysis (pattern="react", subagent_goal="Analyse news sentiment and public reputation of Company X")
  - Operational analysis (pattern="react", subagent_goal="Assess supply chain dependencies and operational risks for Company X")
- Fan-out node written to graph.

**4. Four subagents run in parallel**, each as an independent ReACT loop:
- Financial — queries financial data services and knowledge graph relationships
- Legal — searches regulatory filings and sanctions lists
- Reputational — searches news, analyses sentiment
- Operational — queries supply chain databases

Each writes its own decision trace to the graph as it progresses. Each completes independently.

**5. Fan-in**:
- Each subagent writes a `tg:SubagentCompletion` node to the graph on completion.
- Aggregator detects all four siblings complete for `corr-abc123`.
- Collects results, emits synthesis request to supervisor.

**6. Supervisor synthesis**:
- Receives aggregated findings from all four dimensions.
- Reasons across dimensions, produces a structured risk assessment with confidence scores.
- Emits final answer and conclusion provenance.

**7. Response delivered**. The graph now holds a complete, human-readable trace of the entire multi-agent execution — from pattern selection through four parallel investigations to final synthesis.

---

## Class Hierarchy

The pattern dispatch model suggests a class hierarchy where the shared iteration infrastructure lives in a base class and pattern-specific logic is in subclasses:

```
AgentService (base — Pulsar consumer/producer specs, request handling)
    │
    └── Processor (orchestration service)
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

`PatternBase` captures what is currently spread across `Processor` and `AgentManager`: tool filtering, LLM invocation, provenance triple emission, streaming callbacks, history management. The pattern subclasses implement only the decision logic specific to their execution strategy — what to do with the LLM output, when to terminate, whether to fan out.

This refactoring is not strictly necessary for the first iteration — the meta-router and pattern dispatch could be added as branches within the existing `Processor.agent_request()` method. But the class hierarchy clarifies where shared vs. pattern-specific logic lives and will prevent duplication as more patterns are added.

---

## Configuration

### Graph Seeding

Pattern and task type nodes need to be seeded into the knowledge graph at deployment time. This is analogous to how schema definitions are loaded — a bootstrap step that writes the ontology nodes.

The initial seed includes:

**Patterns**:
- `react` — interleaved reasoning and action
- `plan-then-execute` — structured plan followed by step execution
- `supervisor` — decomposition, fan-out to subagents, synthesis

**Task types** (initial set, expected to grow):
- `general` — no specific domain framing, all patterns valid
- `research` — open-ended investigation, valid patterns: react, plan-then-execute
- `risk-assessment` — multi-dimensional analysis, valid patterns: supervisor, plan-then-execute, react
- `summarisation` — condense information, valid patterns: react

The seed data is configuration, not code. It can be extended by writing new nodes to the graph without redeploying the agent manager.

### Fallback Behaviour

If the graph is empty or unreachable during routing:
- Task type defaults to `general`.
- Pattern defaults to `react`.
- The system degrades gracefully to existing behaviour.

---

## Design Decisions

| Decision | Resolution | Rationale |
|---|---|---|
| Task type identification | LLM interprets from plain text | Natural language too varied to formalise prematurely |
| Pattern representation | Graph ontology from the start | Finite, well-defined, enables constrained selection |
| Meta-router location | Phase within agent manager, not separate service | Avoids an extra network hop; routing is fast |
| Fan-in mechanism | Graph polling (initially) | Stateless, simple, aligns with existing architecture |
| Aggregator deployment | Separate lightweight process | Decoupled from agent manager lifecycle |
| Subagent pattern selection | Supervisor specifies per-subagent | Supervisor has task context to make this choice |
| Plan storage | In message history | No external state needed; plan travels with message |
| Backward compatibility | Empty pattern field → ReACT | Existing callers work without changes |

---

## Open Questions

- **Re-planning depth**: How many times can Plan-then-Execute revise its plan before forcing termination? A fixed re-plan budget (e.g. 2 revisions) is a reasonable starting point.
- **Nested fan-out**: Can a subagent itself be a supervisor that fans out further? The architecture supports it (correlation IDs are independent), but depth limits need consideration.
- **Streaming across fan-out**: How should streaming feedback work when multiple subagents are running in parallel? Options include interleaving chunks with subagent identifiers, or only streaming the supervisor's synthesis phase.
- **Task type evolution**: Should the system learn new task types from usage evidence, or are they always manually curated? Manual curation is the safe starting point; automated discovery is a future exploration.
- **Cost attribution**: When a supervisor fans out to N subagents, each making LLM calls, how is the total cost tracked and attributed back to the original request?
