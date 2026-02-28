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
- Segregated from main data for separate retrieval patterns
- Query-time provenance references extraction-time provenance nodes
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

### Core Fields

| Field | Description |
|-------|-------------|
| `id` | Unique identifier for this provenance node |
| `session_id` | Agent session this belongs to |
| `timestamp` | When this step occurred |
| `type` | Node type (see below) |
| `derived_from` | List of parent node IDs (DAG edges) |

### Node Types

| Type | Description | Additional Fields |
|------|-------------|-------------------|
| `retrieval` | Facts retrieved from knowledge graph | `facts`, `source_refs` |
| `tool_invocation` | Tool was called | `tool_name`, `input`, `output` |
| `reasoning` | LLM reasoning step | `prompt_summary`, `conclusion` |
| `answer` | Final answer produced | `content` |

### Example Provenance Node

```json
{
  "id": "prov-12345",
  "session_id": "session-abc",
  "timestamp": "2024-01-15T10:30:00Z",
  "type": "retrieval",
  "derived_from": [],
  "facts": [
    {"id": "fact-001", "content": "Swallow airspeed is 8.5 m/s"}
  ],
  "source_refs": ["extract-prov-789"]
}
```

```json
{
  "id": "prov-12346",
  "session_id": "session-abc",
  "timestamp": "2024-01-15T10:30:01Z",
  "type": "reasoning",
  "derived_from": ["prov-12345"],
  "prompt_summary": "Asked to determine average swallow speed",
  "conclusion": "Based on retrieved data, average speed is 8.5 m/s"
}
```

## Provenance Events

Events streamed to the client during agent execution.

### Event Structure

```json
{
  "event_type": "provenance_update",
  "session_id": "session-abc",
  "node": { ... provenance node ... }
}
```

### Integration with Agent Response

The existing `AgentResponse` streams chunks back to the client. Provenance events extend this:

**Option A: Separate provenance chunks**
Add a new `chunk_type: "provenance"` to `AgentResponse`.

**Option B: Parallel stream**
Provenance flows on a separate topic/channel alongside the main response.

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

## Open Questions

### Provenance Node Identity

How are provenance nodes identified across sessions?
- UUID per node?
- Content-addressable (hash of content)?
- Hierarchical (session-id/step-number)?

### Graph vs Tree

The provenance structure is described as a DAG:
- Can a provenance node have multiple parents? (e.g., reasoning step combines multiple facts)
- Can the same extraction-time node be referenced by multiple query-time sessions?

### Retrieval Granularity

When the agent retrieves facts:
- One provenance node per retrieval call?
- One provenance node per fact retrieved?
- Both (retrieval node with child fact nodes)?

### Storage Segregation

How is provenance segregated in the knowledge graph?
- Separate named graph?
- Prefix on node IRIs?
- Separate collection?

### Linking to Extraction Provenance

How does query-time provenance reference extraction-time provenance?
- Direct IRI reference?
- Separate linking mechanism?

### Client Protocol

How do provenance events reach the client?
- Extension to existing AgentResponse?
- Separate Pulsar topic?
- Separate field in response envelope?

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
