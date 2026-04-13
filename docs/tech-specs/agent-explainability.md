# Agent Explainability: Provenance Recording

## Status

Implemented

## Overview

Agent sessions are traced and debugged using the same explainability infrastructure as GraphRAG and Document RAG. Provenance is written to `urn:graph:retrieval` and delivered inline on the explain stream.

The canonical vocabulary for all predicates and types is published as an OWL ontology at `specs/ontology/trustgraph.ttl`.

## Entity Types

All services use PROV-O as the base ontology with TrustGraph-specific subtypes.

### GraphRAG Types
| Entity | TG Types | Description |
|--------|----------|-------------|
| Question | `tg:Question`, `tg:GraphRagQuestion` | The user's query |
| Grounding | `tg:Grounding` | Concept extraction from query |
| Exploration | `tg:Exploration` | Edges retrieved from knowledge graph |
| Focus | `tg:Focus` | Selected edges with reasoning |
| Synthesis | `tg:Synthesis`, `tg:Answer` | Final answer |

### Document RAG Types
| Entity | TG Types | Description |
|--------|----------|-------------|
| Question | `tg:Question`, `tg:DocRagQuestion` | The user's query |
| Grounding | `tg:Grounding` | Concept extraction from query |
| Exploration | `tg:Exploration` | Chunks retrieved from document store |
| Synthesis | `tg:Synthesis`, `tg:Answer` | Final answer |

### Agent Types (React)
| Entity | TG Types | Description |
|--------|----------|-------------|
| Question | `tg:Question`, `tg:AgentQuestion` | The user's query (session start) |
| PatternDecision | `tg:PatternDecision` | Meta-router routing decision |
| Analysis | `tg:Analysis`, `tg:ToolUse` | One think/act cycle |
| Thought | `tg:Reflection`, `tg:Thought` | Agent reasoning (sub-entity of Analysis) |
| Observation | `tg:Reflection`, `tg:Observation` | Tool result (standalone entity) |
| Conclusion | `tg:Conclusion`, `tg:Answer` | Final answer |

### Agent Types (Orchestrator — Plan)
| Entity | TG Types | Description |
|--------|----------|-------------|
| Plan | `tg:Plan` | Structured plan of steps |
| StepResult | `tg:StepResult`, `tg:Answer` | Result from executing one plan step |
| Synthesis | `tg:Synthesis`, `tg:Answer` | Final synthesised answer |

### Agent Types (Orchestrator — Supervisor)
| Entity | TG Types | Description |
|--------|----------|-------------|
| Decomposition | `tg:Decomposition` | Question decomposed into sub-goals |
| Finding | `tg:Finding`, `tg:Answer` | Result from a sub-agent |
| Synthesis | `tg:Synthesis`, `tg:Answer` | Final synthesised answer |

### Mixin Types
| Type | Description |
|------|-------------|
| `tg:Answer` | Unifying type for terminal answers (Synthesis, Conclusion, Finding, StepResult) |
| `tg:Reflection` | Unifying type for intermediate commentary (Thought, Observation) |
| `tg:ToolUse` | Applied to Analysis when a tool is invoked |
| `tg:Error` | Applied to Observation events where a failure occurred (tool error or LLM parse error) |

### Question Subtypes

| Subtype | URI Pattern | Mechanism |
|---------|-------------|-----------|
| `tg:GraphRagQuestion` | `urn:trustgraph:question:{uuid}` | Knowledge graph RAG |
| `tg:DocRagQuestion` | `urn:trustgraph:docrag:{uuid}` | Document/chunk RAG |
| `tg:AgentQuestion` | `urn:trustgraph:agent:session:{uuid}` | Agent orchestrator |

## Provenance Chains

All chains use `prov:wasDerivedFrom` links. Each entity is a `prov:Entity`.

### GraphRAG

```
Question → Grounding → Exploration → Focus → Synthesis
```

### Document RAG

```
Question → Grounding → Exploration → Synthesis
```

### Agent React

```
Question → PatternDecision → Analysis(1) → Observation(1) → Analysis(2) → ... → Conclusion
```

The PatternDecision entity records which execution pattern the meta-router selected. It is only emitted on the first iteration when routing occurs.

Thought sub-entities derive from their parent Analysis. Observation entities derive from their parent Analysis (or from a sub-trace entity if the tool produced its own explainability, e.g. a GraphRAG query).

### Agent Plan-then-Execute

```
Question → PatternDecision → Plan → StepResult(0) → StepResult(1) → ... → Synthesis
```

### Agent Supervisor

```
Question → PatternDecision → Decomposition → [fan-out sub-agents]
                                           → Finding(0) → Finding(1) → ... → Synthesis
```

Each sub-agent runs its own session with `wasDerivedFrom` linking back to the parent's Decomposition. Findings derive from their sub-agent's Conclusion.

## Predicates

### Session / Question
| Predicate | Type | Description |
|-----------|------|-------------|
| `tg:query` | string | The user's query text |
| `prov:startedAtTime` | string | ISO timestamp |

### Pattern Decision
| Predicate | Type | Description |
|-----------|------|-------------|
| `tg:pattern` | string | Selected pattern (react, plan-then-execute, supervisor) |
| `tg:taskType` | string | Identified task type (general, research, etc.) |

### Analysis (Iteration)
| Predicate | Type | Description |
|-----------|------|-------------|
| `tg:action` | string | Tool name selected by the agent |
| `tg:arguments` | string | JSON-encoded arguments |
| `tg:thought` | IRI | Link to Thought sub-entity |
| `tg:toolCandidate` | string | Tool name available to the LLM (one per candidate) |
| `tg:stepNumber` | integer | 1-based iteration counter |
| `tg:llmDurationMs` | integer | LLM call duration in milliseconds |
| `tg:inToken` | integer | Input token count |
| `tg:outToken` | integer | Output token count |
| `tg:llmModel` | string | Model identifier |

### Observation
| Predicate | Type | Description |
|-----------|------|-------------|
| `tg:document` | IRI | Librarian document reference |
| `tg:toolDurationMs` | integer | Tool execution time in milliseconds |
| `tg:toolError` | string | Error message (tool failure or LLM parse error) |

When `tg:toolError` is present, the Observation also carries the `tg:Error` mixin type.

### Conclusion / Synthesis
| Predicate | Type | Description |
|-----------|------|-------------|
| `tg:document` | IRI | Librarian document reference |
| `tg:terminationReason` | string | Why the loop stopped |
| `tg:inToken` | integer | Input token count (synthesis LLM call) |
| `tg:outToken` | integer | Output token count |
| `tg:llmModel` | string | Model identifier |

Termination reason values:
- `final-answer` -- LLM produced a confident answer (react)
- `plan-complete` -- all plan steps executed (plan-then-execute)
- `subagents-complete` -- all sub-agents reported back (supervisor)

### Decomposition
| Predicate | Type | Description |
|-----------|------|-------------|
| `tg:subagentGoal` | string | Goal assigned to a sub-agent (one per goal) |
| `tg:inToken` | integer | Input token count |
| `tg:outToken` | integer | Output token count |

### Plan
| Predicate | Type | Description |
|-----------|------|-------------|
| `tg:planStep` | string | Goal for a plan step (one per step) |
| `tg:inToken` | integer | Input token count |
| `tg:outToken` | integer | Output token count |

### Token Counts on RAG Events

Grounding, Focus, and Synthesis events on GraphRAG and Document RAG also carry `tg:inToken`, `tg:outToken`, and `tg:llmModel` for the LLM calls associated with that step.

## Error Handling

Tool execution errors and LLM parse errors are captured as Observation events rather than crashing the agent:

- The error message is recorded on `tg:toolError`
- The Observation carries the `tg:Error` mixin type
- The error text becomes the observation content, visible to the LLM on the next iteration
- The provenance chain is preserved (Observation derives from Analysis)
- The agent gets another iteration to retry or choose a different approach

## Vocabulary Reference

The full OWL ontology covering all classes and predicates is at `specs/ontology/trustgraph.ttl`.

## Verification

```bash
# Run an agent query with explainability
tg-invoke-agent -q "What is quantum computing?" -x

# Run with token usage
tg-invoke-agent -q "What is quantum computing?" --show-usage

# GraphRAG with explainability
tg-invoke-graph-rag -q "Tell me about AI" -x

# Document RAG with explainability
tg-invoke-document-rag -q "Summarize the findings" -x
```
