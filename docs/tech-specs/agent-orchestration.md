# TrustGraph Agent Orchestration — Design Context Document

## Background

TrustGraph has an existing **Agent Manager** component built on the **ReACT pattern** (Reasoning + Acting). The current implementation has a notable architectural characteristic: it uses **Apache Pulsar pub/sub** as the loop mechanism. Rather than running an in-process iteration loop, each agent iteration emits a new message onto its own input queue. The full conversation and tool-call history travels with each message, making the agent manager effectively stateless.

This document captures a design exploration into extending that architecture toward a broader **multi-pattern agent orchestration model**.

---

## Existing Architecture — Key Properties

- **Self-queuing loop**: Each ReACT iteration emits a new Pulsar message carrying the accumulated history. The agent manager picks this up and runs the next iteration.
- **Stateless agent manager**: No in-process state. All state lives in the message payload.
- **Natural parallelism**: Multiple independent agent requests are handled concurrently across Pulsar consumers, giving fair, parallel access to the agent manager.
- **Durability**: Crash recovery is inherent — the message survives process failure.
- **Real-time feedback**: Progress and explainable feedback can be emitted continuously as iterations complete.
- **Tool calling and MCP invocation**: The agent manager already supports tool calls into knowledge graphs, external services, and MCP-connected systems.
- **Decision traces written to the knowledge graph**: Every significant decision is recorded in the graph, forming the basis of TrustGraph's explainability architecture.

---

## The Core Insight: ReACT as One Pattern Among Many

ReACT is one point in a wider space of agent execution strategies. Other patterns include:

- **Plan-then-Execute** — decompose the task upfront into a DAG of steps, then execute. Less adaptive but more predictable.
- **ReACT** — interleaved reasoning and action. Adaptive, good for open-ended tasks.
- **Reflexion** — adds a self-critique step after each action; agents improve within the episode.
- **Supervisor/Subagent** — one agent orchestrates others, delegating subtasks and synthesising results.
- **Debate/Ensemble** — multiple agents reason independently, outputs reconciled.
- **LLM-as-router** — no reasoning loop, pure classification and dispatch.

The key architectural observation is that **the Pulsar self-queuing loop is pattern-agnostic**. The plumbing doesn't care whether an iteration is a ReACT step, a planning step, or a supervisor dispatching to subagents. The *payload* and the *pattern logic* define the behaviour; the infrastructure remains constant.

---

## Proposed Extension: Multi-Pattern Orchestration

### Task Type

A **task type** characterises the *problem domain* — what the agent is being asked to accomplish, and how a domain expert would frame it analytically.

- Carries domain-specific methodology (e.g. "intelligence analysis always applies structured analytic techniques")
- Pre-populates initial reasoning context
- Constrains which patterns are valid for this class of problem
- Can define domain-specific termination criteria

Task types are initially identified from plain-text task descriptions by the LLM. Building a formal ontology over task descriptions is deferred — natural language is too varied and context-dependent to formalise prematurely. The LLM reads the description; the graph provides the structure downstream.

### Pattern

A **pattern** characterises the *execution strategy* — the mechanical structure of how planning and iteration take place.

- How iterations are structured
- How decisions are made at each step
- Termination conditions
- Whether fan-out to subagents occurs
- How history accumulates

Patterns are well-suited to graph representation because they are finite in number, mechanically well-defined, have enumerable properties and relationships, and change slowly over time.

### Relationship Between Task Type and Pattern

The relationship is **many-to-many with a clear hierarchy**:

```
Task Description (plain text)
        ↓  [LLM interprets]
Task Type (graph node — domain framing and methodology)
        ↓  [graph query — constrains valid patterns]
Pattern Candidates (graph nodes)
        ↓  [LLM selects within constrained set, informed by task description signals]
Selected Pattern
```

The task description may carry modulating signals (complexity, urgency, scope) that influence which pattern is selected *within* the constrained set. But the raw description never directly selects a pattern — it always passes through the task type layer first.

---

## Explainability Through Constrained Decision Spaces

A central principle of TrustGraph's explainability architecture is that **explainability comes from constrained decision spaces**.

When a decision is made from an unconstrained space — a raw LLM call with no guardrails — the reasoning is opaque even if the LLM produces a rationale, because that rationale is post-hoc and unverifiable.

When a decision is made from a **graph-defined constrained set**, you can always answer:
- What valid options were available
- What criteria narrowed the set
- What signal made the final selection within that set

The LLM makes a **supervised choice within a known decision space**. This is auditable in a way that unconstrained LLM reasoning is not.

This principle already governs the existing decision trace architecture and extends naturally to pattern selection. **Trust becomes a structural property of the architecture, not a claimed property of the model.**

---

## The Knowledge Graph as Connective Tissue

The knowledge graph plays multiple roles simultaneously:

| Role | When Written | Content |
|---|---|---|
| Pattern ontology | At design time | Pattern nodes, properties, valid task-type mappings |
| Task type ontology | At design time | Task type nodes, domain framing, pattern constraints |
| Decision trace | During execution | Why this task type and pattern were selected |
| In-progress state | During execution | Current iteration state, subagent status |
| Fan-in coordination | During fan-out | Subagent completion nodes under shared correlation ID |
| Execution audit trail | Post-execution | Full multi-agent reasoning trace |

These are not separate mechanisms — they are all nodes and edges written at different points in the execution lifecycle on the same substrate. The fan-in coordination state *is* part of the explanation automatically.

---

## Multi-Agent Fan-Out and Fan-In

With the Pulsar architecture, fan-out is **genuinely parallel**, not simulated.

**Fan-out**: A supervisor iteration emits multiple messages onto the queue — one per subagent. Each carries:
- A focused subagent goal
- A shared **correlation ID** tying it to the parent task
- The relevant slice of history

Subagents are picked up concurrently by agent manager instances. Each runs its own independent iteration loop (ReACT or otherwise) on the queue.

**Fan-in**: As each subagent completes, it writes a completion node to the graph under the shared correlation ID. An aggregator monitors for all sibling completions, then emits a synthesis message back to the supervisor flow.

The graph is the natural coordination substrate for fan-in — querying "how many siblings have completed for correlation ID X" is structurally identical to querying the decision trace. The same mechanism serves both purposes. The agent manager itself remains stateless.

---

## Worked Example: Partner Risk Assessment

**Request**: "Assess the risk profile of Company X as a potential partner"

1. **Request arrives** on the Pulsar input topic with a new task ID and empty history.

2. **Meta-router queries the graph**: Task type matched as *Due Diligence / Risk Assessment*. Domain framing applied: analyse across financial, reputational, legal and operational dimensions. Pattern selected: *Supervisor/Subagent fanout*. Selection written to graph as first decision trace node.

3. **Supervisor iteration**: LLM receives request plus task type framing. Reasons that four independent investigative threads are required. Emits four messages onto the queue with a shared correlation ID.

4. **Four subagents run in parallel**, each as an independent ReACT loop:
   - Financial — queries financial data services and knowledge graph relationships
   - Legal — searches regulatory filings and sanctions lists
   - Reputational — searches news, analyses sentiment
   - Operational — queries supply chain databases

   Each writes its own decision trace to the graph as it progresses.

5. **Fan-in**: Each subagent writes a completion node to the graph. Aggregator detects all four siblings complete and emits a synthesis message to the supervisor.

6. **Supervisor synthesis**: Receives aggregated findings, reasons across dimensions, produces a structured risk assessment with confidence score.

7. **Response delivered**. The graph now holds a complete, human-readable trace of the entire multi-agent execution — from pattern selection through to final synthesis.

---

## Design Decisions and Deferred Questions

| Decision | Resolution |
|---|---|
| Task descriptions | Plain text initially; LLM interprets naturally |
| Pattern representation | Graph ontology from the start |
| Task type representation | Graph ontology; may grow incrementally from usage evidence |
| Fan-in coordination state | Written to knowledge graph under correlation ID |
| Pattern selection mechanism | Graph constrains valid set; LLM selects within it |
| Explainability mechanism | Constrained decision spaces recorded at each step |

---

## Summary

TrustGraph's existing Pulsar-based self-queuing architecture is a strong foundation for multi-pattern agent orchestration. The loop mechanism is pattern-agnostic. The knowledge graph already serves as the explainability and state substrate. Extending to multiple patterns, task types, and multi-agent fan-out is largely additive — the same mechanisms, applied more broadly. The central architectural principle is that trust and explainability are structural properties, achieved by constraining LLM decision-making to graph-defined spaces and recording those constraints in the execution trace.


