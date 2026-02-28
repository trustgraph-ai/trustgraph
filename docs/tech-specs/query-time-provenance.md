# Query-Time Provenance: Agent Explainability

## Status

Draft - Gathering Requirements

## Overview

This specification defines how the agent framework records and communicates provenance during query execution. The goal is full explainability: tracing how a result was obtained, from final answer back through reasoning steps to source data.

Query-time provenance captures the "inference layer" - what the agent did during reasoning. It connects to extraction-time provenance (source layer) which records where facts came from originally.

## Terminology

| Term | Definition |
|------|------------|
| **Provenance** | The record of how a result was derived |
| **Provenance Node** | A single step or artifact in the provenance DAG |
| **Provenance DAG** | Directed Acyclic Graph of provenance relationships |
| **Query-time Provenance** | Provenance generated during agent reasoning |
| **Extraction-time Provenance** | Provenance from data ingestion (source metadata) - separate spec |

## Architecture

### Two Provenance Contexts

1. **Extraction-time** (out of scope for this spec):
   - Generated when data is ingested (PDF extraction, web scraping, etc.)
   - Records: source URL, extraction method, timestamps, funding, authorship
   - Already partially implemented via source metadata in knowledge graph
   - See: `docs/tech-specs/extraction-time-provenance.md` (notes)

2. **Query-time** (this spec):
   - Generated during agent reasoning
   - Records: tool invocations, retrieval results, LLM reasoning, final conclusions
   - Links to extraction-time provenance for retrieved facts

### Provenance Flow

```
Agent Session
    │
    ├─► Tool: Knowledge Query
    │       │
    │       ├─► Retrieved Fact A ──► [link to extraction provenance]
    │       └─► Retrieved Fact B ──► [link to extraction provenance]
    │
    ├─► LLM Reasoning Step
    │       │
    │       └─► "Combined A and B to conclude X"
    │
    └─► Final Answer
            │
            └─► Derived from reasoning step above
```

### Storage

- Provenance stored in knowledge graph infrastructure
- Segregated in a **separate collection** for distinct retrieval patterns
- Query-time provenance references extraction-time provenance nodes via IRIs
- Persists beyond agent session (reusable, auditable)

### Real-Time Streaming

Provenance events stream back to the client as the agent works:

1. Agent invokes tool
2. Tool generates provenance data
3. Provenance stored in graph
4. Provenance event sent to client
5. UX builds provenance visualization incrementally

## Provenance Node Structure

Each provenance node represents a step in the reasoning process.

### Node Identity

Provenance nodes are identified by IRIs containing UUIDs, consistent with the RDF-style knowledge graph:

```
urn:trustgraph:prov:550e8400-e29b-41d4-a716-446655440000
```

### Core Fields

| Field | Description |
|-------|-------------|
| `id` | IRI with UUID (e.g., `urn:trustgraph:prov:{uuid}`) |
| `session_id` | Agent session this belongs to |
| `timestamp` | When this step occurred |
| `type` | Node type (see below) |
| `derived_from` | List of parent node IRIs (DAG edges) |

### Node Types

| Type | Description | Additional Fields |
|------|-------------|-------------------|
| `retrieval` | Facts retrieved from knowledge graph | `facts`, `source_refs` |
| `tool_invocation` | Tool was called | `tool_name`, `input`, `output` |
| `reasoning` | LLM reasoning step | `prompt_summary`, `conclusion` |
| `answer` | Final answer produced | `content` |

### Example Provenance Nodes

```json
{
  "id": "urn:trustgraph:prov:550e8400-e29b-41d4-a716-446655440001",
  "session_id": "urn:trustgraph:session:7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "timestamp": "2024-01-15T10:30:00Z",
  "type": "retrieval",
  "derived_from": [],
  "facts": [
    {
      "id": "urn:trustgraph:fact:9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "content": "Swallow airspeed is 8.5 m/s"
    }
  ],
  "source_refs": ["urn:trustgraph:extract:1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed"]
}
```

```json
{
  "id": "urn:trustgraph:prov:550e8400-e29b-41d4-a716-446655440002",
  "session_id": "urn:trustgraph:session:7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "timestamp": "2024-01-15T10:30:01Z",
  "type": "reasoning",
  "derived_from": ["urn:trustgraph:prov:550e8400-e29b-41d4-a716-446655440001"],
  "prompt_summary": "Asked to determine average swallow speed",
  "conclusion": "Based on retrieved data, average speed is 8.5 m/s"
}
```

## Provenance Events

Events streamed to the client during agent execution.

### Design: Lightweight Reference Events

Provenance events are lightweight - they reference provenance nodes by IRI rather than embedding full provenance data. This keeps the stream efficient while allowing the client to fetch full details if needed.

A single agent step may create or modify multiple provenance objects. The event references all of them.

### Event Structure

```json
{
  "provenance_refs": [
    "urn:trustgraph:prov:550e8400-e29b-41d4-a716-446655440001",
    "urn:trustgraph:prov:550e8400-e29b-41d4-a716-446655440002"
  ]
}
```

### Integration with Agent Response

Provenance events extend `AgentResponse` with a new `chunk_type: "provenance"`:

```json
{
  "chunk_type": "provenance",
  "content": "",
  "provenance_refs": ["urn:trustgraph:prov:..."],
  "end_of_message": false
}
```

This allows provenance updates to flow alongside existing chunk types (`thought`, `observation`, `answer`, `error`).

## Tool Provenance Reporting

Tools report provenance as part of their execution.

### Minimum Reporting (all tools)

Every tool can report at minimum:
- Tool name
- Input arguments
- Output result

### Enhanced Reporting (tools that can describe more)

Tools that understand their internals can report:
- What sources were consulted
- What reasoning/transformation was applied
- Confidence scores
- Links to extraction-time provenance

### Graceful Degradation

Tools that can't provide detailed provenance still participate:
```json
{
  "type": "tool_invocation",
  "tool_name": "calculator",
  "input": {"expression": "8 + 5"},
  "output": "13",
  "detail_level": "basic"
}
```

## Design Decisions

### Provenance Node Identity: IRIs with UUIDs

Provenance nodes use IRIs containing UUIDs, consistent with the RDF-style knowledge graph:
- Format: `urn:trustgraph:prov:{uuid}`
- Globally unique, persistent across sessions
- Can be dereferenced to retrieve full node data

### Storage Segregation: Separate Collection

Provenance is stored in a separate collection within the knowledge graph infrastructure. This allows:
- Distinct retrieval patterns for provenance vs. data
- Independent scaling/retention policies
- Clear separation of concerns

### Client Protocol: Extended AgentResponse

Provenance events extend `AgentResponse` with `chunk_type: "provenance"`. Events are lightweight, containing only IRI references to provenance nodes created/modified in the step.

### Retrieval Granularity: Flexible, Multiple Objects Per Step

A single agent step can create multiple provenance objects. The provenance event references all objects created or modified. This handles cases like:
- Retrieval returning multiple facts (each gets a provenance node)
- Tool invocation creating both an invocation node and result nodes

### Graph Structure: True DAG

The provenance structure is a DAG (not a tree):
- A provenance node can have multiple parents (e.g., reasoning combines facts A and B)
- Extraction-time nodes can be referenced by multiple query-time sessions
- Enables proper modeling of how conclusions derive from multiple sources

### Linking to Extraction Provenance: Direct IRI Reference

Query-time provenance references extraction-time provenance via direct IRI links in the `source_refs` field. No separate linking mechanism needed.

## Open Questions

### Provenance Retrieval API

Base layer uses the existing knowledge graph API to query the provenance collection. A higher-level service may be added to provide convenience methods. Details TBD during implementation.

### Provenance Node Granularity

Placeholder to explore: What level of detail should different node types capture?
- Should `reasoning` nodes include the full LLM prompt, or just a summary?
- How much of tool input/output to store?
- Trade-offs between completeness and storage/performance

### Provenance Retention

TBD - retention policy to be determined:
- Indefinitely?
- Tied to session retention?
- Configurable per collection?

## Implementation Considerations

### Files Likely Affected

| Area | Changes |
|------|---------|
| Agent service | Generate provenance events |
| Tool implementations | Report provenance data |
| Agent response schema | Add provenance event type |
| Knowledge graph | Provenance storage/retrieval |

### Backward Compatibility

- Existing agent clients continue to work (provenance is additive)
- Tools that don't report provenance still function

## References

- PROV-O (PROV-Ontology): W3C standard for provenance modeling
- Current agent implementation: `trustgraph-flow/trustgraph/agent/react/`
- Agent schemas: `trustgraph-base/trustgraph/schema/services/agent.py`
- Extraction-time provenance notes: `docs/tech-specs/extraction-time-provenance.md`
