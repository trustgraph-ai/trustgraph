# Agent Explainability: Provenance Recording

## Overview

Add provenance recording to the React agent loop so agent sessions can be traced and debugged using the same explainability infrastructure as GraphRAG.

**Design Decisions:**
- Write to `urn:graph:retrieval` (generic explainability graph)
- Linear dependency chain for now (iteration N → wasDerivedFrom → iteration N-1)
- Tools are opaque black boxes (record input/output only)
- DAG support deferred to future iteration

## Provenance Model

```
AgentSession (urn:trustgraph:agent:{uuid})
    │
    │  tg:query = "User's question"
    │  prov:startedAtTime = timestamp
    │  rdf:type = tg:AgentSession
    │
    ↓ prov:wasGeneratedBy
    │
Iteration1 (urn:trustgraph:agent:{uuid}/i1)
    │
    │  tg:thought = "I need to query the knowledge base..."
    │  tg:action = "knowledge-query"
    │  tg:arguments = {"question": "..."}
    │  tg:observation = "Result from tool..."
    │  rdf:type = tg:AgentIteration
    │
    ↓ prov:wasDerivedFrom
    │
Iteration2 (urn:trustgraph:agent:{uuid}/i2)
    │  ...
    ↓ prov:wasDerivedFrom
    │
FinalAnswer (urn:trustgraph:agent:{uuid}/final)
    │
    │  tg:answer = "The final response..."
    │  rdf:type = tg:AgentFinal
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

**Option A:** Add to existing `trustgraph-base/trustgraph/provenance/` module
**Option B:** Create agent-specific provenance helpers in the agent module

Create helper functions (similar to GraphRAG's `question_triples`, `exploration_triples`, etc.):
```python
def agent_session_triples(session_uri, query, timestamp):
    """Generate triples for agent session start."""
    return [
        Triple(s=session_uri, p=RDF_TYPE, o=TG_AGENT_SESSION),
        Triple(s=session_uri, p=TG_QUERY, o=query),
        Triple(s=session_uri, p=PROV_STARTED_AT_TIME, o=timestamp),
    ]

def agent_iteration_triples(iteration_uri, parent_uri, thought, action, arguments, observation):
    """Generate triples for one agent iteration."""
    return [
        Triple(s=iteration_uri, p=RDF_TYPE, o=TG_AGENT_ITERATION),
        Triple(s=iteration_uri, p=TG_THOUGHT, o=thought),
        Triple(s=iteration_uri, p=TG_ACTION, o=action),
        Triple(s=iteration_uri, p=TG_ARGUMENTS, o=json.dumps(arguments)),
        Triple(s=iteration_uri, p=TG_OBSERVATION, o=observation),
        Triple(s=iteration_uri, p=PROV_WAS_DERIVED_FROM, o=parent_uri),
    ]

def agent_final_triples(final_uri, parent_uri, answer):
    """Generate triples for agent final answer."""
    return [
        Triple(s=final_uri, p=RDF_TYPE, o=TG_AGENT_FINAL),
        Triple(s=final_uri, p=TG_ANSWER, o=answer),
        Triple(s=final_uri, p=PROV_WAS_DERIVED_FROM, o=parent_uri),
    ]
```

### 4. Integration in service.py

**In `agent_request()` method:**

```python
async def agent_request(self, request, respond, next, flow):
    # Generate or retrieve session ID
    if not request.session_id:
        session_id = str(uuid.uuid4())
    else:
        session_id = request.session_id

    session_uri = f"urn:trustgraph:agent:{session_id}"
    iteration_num = len(history) + 1
    iteration_uri = f"{session_uri}/i{iteration_num}"

    # On first iteration, emit session triples
    if iteration_num == 1:
        triples = agent_session_triples(session_uri, request.question, timestamp)
        await flow("explainability").send(Triples(
            metadata=Metadata(user=request.user, collection=..., id=session_uri),
            triples=triples,
        ))

    # ... existing react() call ...

    if isinstance(act, Final):
        # Emit final answer triples
        final_uri = f"{session_uri}/final"
        parent_uri = f"{session_uri}/i{iteration_num - 1}" if iteration_num > 1 else session_uri
        triples = agent_final_triples(final_uri, parent_uri, act.final)
        await flow("explainability").send(...)
    else:
        # Emit iteration triples
        parent_uri = f"{session_uri}/i{iteration_num - 1}" if iteration_num > 1 else session_uri
        triples = agent_iteration_triples(iteration_uri, parent_uri, act.thought, act.name, act.arguments, act.observation)
        await flow("explainability").send(...)

        # Pass session_id to next iteration
        r = AgentRequest(
            ...,
            session_id=session_id,
        )
```

### 5. Predicate Definitions

**File:** `trustgraph-base/trustgraph/provenance/namespaces.py`

Add new predicates:
```python
TG_THOUGHT = TG + "thought"
TG_ACTION = TG + "action"
TG_ARGUMENTS = TG + "arguments"
TG_OBSERVATION = TG + "observation"
TG_AGENT_SESSION = TG + "AgentSession"
TG_AGENT_ITERATION = TG + "AgentIteration"
TG_AGENT_FINAL = TG + "AgentFinal"
# TG_QUERY and TG_ANSWER likely already exist
```

## Files to Modify

| File | Change |
|------|--------|
| `trustgraph-base/trustgraph/schema/services/agent.py` | Add session_id and collection to AgentRequest |
| `trustgraph-base/trustgraph/messaging/translators/agent.py` | Update translator for new fields |
| `trustgraph-base/trustgraph/provenance/namespaces.py` | Add agent predicates |
| `trustgraph-base/trustgraph/provenance/__init__.py` | Export new predicates |
| `trustgraph-flow/trustgraph/agent/react/service.py` | Add explainability producer + recording logic |
| `trustgraph-cli/trustgraph/cli/show_explain_trace.py` | Handle agent trace types |
| `trustgraph-cli/trustgraph/cli/list_explain_traces.py` | List agent sessions alongside GraphRAG |

## Files to Potentially Create

| File | Purpose |
|------|---------|
| `trustgraph-base/trustgraph/provenance/agent.py` | Agent-specific triple generators (optional, could inline in service.py) |

## CLI Updates Detail

**`list_explain_traces.py`:**
- Currently queries for `tg:query` predicate to find questions
- Agent sessions also use `tg:query`, so should work automatically
- May want to add a type indicator column (GraphRAG vs Agent)

**`show_explain_trace.py`:**
- Currently expects: question → exploration → focus → synthesis chain
- Agent traces have: session → iteration(s) → final chain
- Detection: check `rdf:type` of the root entity
  - `tg:AgentSession` → agent trace rendering
  - Otherwise → GraphRAG trace rendering (existing)
- Agent rendering shows:
  - Session info (question, time)
  - Each iteration: thought, action, args, observation
  - Final answer

## Design Decisions

1. **Collection handling:** Add `collection` field to AgentRequest. Agent receives a collection parameter for provenance traces. Tools can access other collections per their config, but decision traces stay in the invoked collection.

2. **CLI tool updates:** Update existing `tg-show-explain-trace` to detect and handle both GraphRAG and agent trace types.

## Implementation Order

0. **Tech Spec:** Write this plan to `docs/tech-specs/agent-explainability.md`
1. **Schema:** Add `session_id` and `collection` to AgentRequest + translator
2. **Predicates:** Add agent predicates to `namespaces.py`
3. **Service:** Add explainability producer to agent service
4. **Provenance:** Create/add agent triple generators
5. **Integration:** Wire up provenance recording in `agent_request()`
6. **CLI:** Update `show_explain_trace.py` to detect and render agent traces
7. **Test:** Run agent query and verify trace is recorded and viewable

## Backwards Compatibility

- `session_id` defaults to `""` - old requests work, just won't have provenance
- `collection` defaults to `"default"` - reasonable fallback
- CLI gracefully handles both trace types

## Verification

```bash
# Run an agent query
tg-invoke-agent -q "What is the capital of France?"

# Check triples were written
tg-query-graph -p "https://trustgraph.ai/ns/query" -g "urn:graph:retrieval"

# List traces (should show agent sessions)
tg-list-explain-traces -U trustgraph -C default

# Show trace (may need CLI updates for agent entity types)
tg-show-explain-trace "urn:trustgraph:agent:xxx"
```

## Future Work (Not This PR)

- DAG dependencies (when iteration N uses results from multiple prior iterations)
- Tool-specific provenance linking (KnowledgeQuery → its GraphRAG trace)
- CLI tool enhancements to better display agent traces
- Streaming provenance emission (emit as we go, not batch at end)
