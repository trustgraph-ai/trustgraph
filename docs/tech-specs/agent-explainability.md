# Agent Explainability: Provenance Recording

## Overview

Add provenance recording to the React agent loop so agent sessions can be traced and debugged using the same explainability infrastructure as GraphRAG.

**Design Decisions:**
- Write to `urn:graph:retrieval` (generic explainability graph)
- Linear dependency chain for now (analysis N → wasDerivedFrom → analysis N-1)
- Tools are opaque black boxes (record input/output only)
- DAG support deferred to future iteration

## Entity Types

Both GraphRAG and Agent use PROV-O as the base ontology with TrustGraph-specific subtypes:

### GraphRAG Types
| Entity | PROV-O Type | TG Type | Description |
|--------|-------------|---------|-------------|
| Question | `prov:Activity` | `tg:Question` | The user's query |
| Exploration | `prov:Entity` | `tg:Exploration` | Edges retrieved from knowledge graph |
| Focus | `prov:Entity` | `tg:Focus` | Selected edges with reasoning |
| Synthesis | `prov:Entity` | `tg:Synthesis` | Final answer |

### Agent Types
| Entity | PROV-O Type | TG Type | Description |
|--------|-------------|---------|-------------|
| Question | `prov:Activity` | `tg:Question` | The user's query (same as GraphRAG) |
| Analysis | `prov:Entity` | `tg:Analysis` | Each think/act/observe cycle |
| Conclusion | `prov:Entity` | `tg:Conclusion` | Final answer |

## Provenance Model

```
Question (urn:trustgraph:agent:{uuid})
    │
    │  tg:query = "User's question"
    │  prov:startedAtTime = timestamp
    │  rdf:type = prov:Activity, tg:Question
    │
    ↓ prov:wasDerivedFrom
    │
Analysis1 (urn:trustgraph:agent:{uuid}/i1)
    │
    │  tg:thought = "I need to query the knowledge base..."
    │  tg:action = "knowledge-query"
    │  tg:arguments = {"question": "..."}
    │  tg:observation = "Result from tool..."
    │  rdf:type = prov:Entity, tg:Analysis
    │
    ↓ prov:wasDerivedFrom
    │
Analysis2 (urn:trustgraph:agent:{uuid}/i2)
    │  ...
    ↓ prov:wasDerivedFrom
    │
Conclusion (urn:trustgraph:agent:{uuid}/final)
    │
    │  tg:answer = "The final response..."
    │  rdf:type = prov:Entity, tg:Conclusion
```

## Changes Required

### 1. Schema Changes

**File:** `trustgraph-base/trustgraph/schema/services/agent.py`

Add `session_id` and `collection` fields to `AgentRequest`:
```python
@dataclass
class AgentRequest:
    question: str = ""
    state: str = ""
    group: list[str] | None = None
    history: list[AgentStep] = field(default_factory=list)
    user: str = ""
    collection: str = "default"  # NEW: Collection for provenance traces
    streaming: bool = False
    session_id: str = ""         # NEW: For provenance tracking across iterations
```

**File:** `trustgraph-base/trustgraph/messaging/translators/agent.py`

Update translator to handle `session_id` and `collection` in both `to_pulsar()` and `from_pulsar()`.

### 2. Add Explainability Producer to Agent Service

**File:** `trustgraph-flow/trustgraph/agent/react/service.py`

Register an "explainability" producer (same pattern as GraphRAG):
```python
from ... base import ProducerSpec
from ... schema import Triples

# In __init__:
self.register_specification(
    ProducerSpec(
        name = "explainability",
        schema = Triples,
    )
)
```

### 3. Provenance Triple Generation

**File:** `trustgraph-base/trustgraph/provenance/agent.py`

Create helper functions (similar to GraphRAG's `question_triples`, `exploration_triples`, etc.):
```python
def agent_session_triples(session_uri, query, timestamp):
    """Generate triples for agent Question."""
    return [
        Triple(s=session_uri, p=RDF_TYPE, o=PROV_ACTIVITY),
        Triple(s=session_uri, p=RDF_TYPE, o=TG_QUESTION),
        Triple(s=session_uri, p=TG_QUERY, o=query),
        Triple(s=session_uri, p=PROV_STARTED_AT_TIME, o=timestamp),
    ]

def agent_iteration_triples(iteration_uri, parent_uri, thought, action, arguments, observation):
    """Generate triples for one Analysis step."""
    return [
        Triple(s=iteration_uri, p=RDF_TYPE, o=PROV_ENTITY),
        Triple(s=iteration_uri, p=RDF_TYPE, o=TG_ANALYSIS),
        Triple(s=iteration_uri, p=TG_THOUGHT, o=thought),
        Triple(s=iteration_uri, p=TG_ACTION, o=action),
        Triple(s=iteration_uri, p=TG_ARGUMENTS, o=json.dumps(arguments)),
        Triple(s=iteration_uri, p=TG_OBSERVATION, o=observation),
        Triple(s=iteration_uri, p=PROV_WAS_DERIVED_FROM, o=parent_uri),
    ]

def agent_final_triples(final_uri, parent_uri, answer):
    """Generate triples for Conclusion."""
    return [
        Triple(s=final_uri, p=RDF_TYPE, o=PROV_ENTITY),
        Triple(s=final_uri, p=RDF_TYPE, o=TG_CONCLUSION),
        Triple(s=final_uri, p=TG_ANSWER, o=answer),
        Triple(s=final_uri, p=PROV_WAS_DERIVED_FROM, o=parent_uri),
    ]
```

### 4. Type Definitions

**File:** `trustgraph-base/trustgraph/provenance/namespaces.py`

Add explainability entity types and agent predicates:
```python
# Explainability entity types (used by both GraphRAG and Agent)
TG_QUESTION = TG + "Question"
TG_EXPLORATION = TG + "Exploration"
TG_FOCUS = TG + "Focus"
TG_SYNTHESIS = TG + "Synthesis"
TG_ANALYSIS = TG + "Analysis"
TG_CONCLUSION = TG + "Conclusion"

# Agent predicates
TG_THOUGHT = TG + "thought"
TG_ACTION = TG + "action"
TG_ARGUMENTS = TG + "arguments"
TG_OBSERVATION = TG + "observation"
TG_ANSWER = TG + "answer"
```

## Files Modified

| File | Change |
|------|--------|
| `trustgraph-base/trustgraph/schema/services/agent.py` | Add session_id and collection to AgentRequest |
| `trustgraph-base/trustgraph/messaging/translators/agent.py` | Update translator for new fields |
| `trustgraph-base/trustgraph/provenance/namespaces.py` | Add entity types and agent predicates |
| `trustgraph-base/trustgraph/provenance/triples.py` | Add TG types to GraphRAG triple builders |
| `trustgraph-base/trustgraph/provenance/__init__.py` | Export new types and predicates |
| `trustgraph-flow/trustgraph/agent/react/service.py` | Add explainability producer + recording logic |
| `trustgraph-cli/trustgraph/cli/show_explain_trace.py` | Handle agent trace types |
| `trustgraph-cli/trustgraph/cli/list_explain_traces.py` | List agent sessions alongside GraphRAG |

## Files Created

| File | Purpose |
|------|---------|
| `trustgraph-base/trustgraph/provenance/agent.py` | Agent-specific triple generators |

## CLI Updates

**Detection:** Both GraphRAG and Agent Questions have `tg:Question` type. Distinguished by:
1. URI pattern: `urn:trustgraph:agent:` vs `urn:trustgraph:question:`
2. Derived entities: `tg:Analysis` (agent) vs `tg:Exploration` (GraphRAG)

**`list_explain_traces.py`:**
- Shows Type column (Agent vs GraphRAG)

**`show_explain_trace.py`:**
- Auto-detects trace type
- Agent rendering shows: Question → Analysis step(s) → Conclusion

## Backwards Compatibility

- `session_id` defaults to `""` - old requests work, just won't have provenance
- `collection` defaults to `"default"` - reasonable fallback
- CLI gracefully handles both trace types

## Verification

```bash
# Run an agent query
tg-invoke-agent -q "What is the capital of France?"

# List traces (should show agent sessions with Type column)
tg-list-explain-traces -U trustgraph -C default

# Show agent trace
tg-show-explain-trace "urn:trustgraph:agent:xxx"
```

## Future Work (Not This PR)

- DAG dependencies (when analysis N uses results from multiple prior analyses)
- Tool-specific provenance linking (KnowledgeQuery → its GraphRAG trace)
- Document RAG explainability
- Streaming provenance emission (emit as we go, not batch at end)
