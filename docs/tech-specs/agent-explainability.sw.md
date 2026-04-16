---
layout: default
title: "Ufafanuzi wa Mwakala: Urekodaji wa Asili"
parent: "Swahili (Beta)"
---

# Ufafanuzi wa Mwakala: Urekodaji wa Asili

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Muhtasari

Ongeza urekodaji wa asili kwenye mzunguko wa wakala wa React ili vipindi vya wakala viweze kufuatiliwa na kurekebishwa kwa kutumia miundomino sawa ya ufafanuzi kama GraphRAG.

**Maamuzi ya Ubunifu:**
- Andika kwenye `urn:graph:retrieval` (picha ya ufafanuzi ya jumla)
- Mnyororo wa utegemezi wa mstari kwa sasa (uchambuzi N → ilitokana na → uchambuzi N-1)
- Zana ni masanduku meusi (rekodi tu ingizo/patto)
- Usaidizi wa DAG umeahirishwa hadi toleo la baadaye

## Aina za Vitambulisho

GraphRAG na Agent hutumia PROV-O kama ontolojia ya msingi na aina za ziada maalum za TrustGraph:

### Aina za GraphRAG
| Vitambulisho | Aina ya PROV-O | Aina za TG | Maelezo |
|--------|-------------|----------|-------------|
| Swali | `prov:Activity` | `tg:Question`, `tg:GraphRagQuestion` | Uliza wa mtumiaji |
| Uchunguzi | `prov:Entity` | `tg:Exploration` | Edges iliyopatikana kutoka kwenye grafu ya maarifa |
| Lengo | `prov:Entity` | `tg:Focus` | Edges iliyochaguliwa na hoja |
| Muunganisho | `prov:Entity` | `tg:Synthesis` | Jibu la mwisho |

### Aina za Wakala
| Vitambulisho | Aina ya PROV-O | Aina za TG | Maelezo |
|--------|-------------|----------|-------------|
| Swali | `prov:Activity` | `tg:Question`, `tg:AgentQuestion` | Uliza wa mtumiaji |
| Uchambuzi | `prov:Entity` | `tg:Analysis` | Kila mzunguko wa kufikiria/kutenda/kuona |
| Hitimisho | `prov:Entity` | `tg:Conclusion` | Jibu la mwisho |

### Aina za RAG za Hati
| Vitambulisho | Aina ya PROV-O | Aina za TG | Maelezo |
|--------|-------------|----------|-------------|
| Swali | `prov:Activity` | `tg:Question`, `tg:DocRagQuestion` | Uliza wa mtumiaji |
| Uchunguzi | `prov:Entity` | `tg:Exploration` | Sehemu zilizopatikana kutoka kwenye duka la hati |
| Muunganisho | `prov:Entity` | `tg:Synthesis` | Jibu la mwisho |

**Kumbuka:** RAG ya Hati hutumia sehemu ya aina za GraphRAG (hakuna hatua ya Lengo kwa sababu hakuna awamu ya uteuzi/hoja ya edge).

### Aina za Ndogo za Swali

Aina zote za Swali hushiriki `tg:Question` kama aina ya msingi lakini zina aina maalum ili kutambua utaratibu wa urejesho:

| Aina | Mfumo wa URI | Utaratibu |
|---------|-------------|-----------|
| `tg:GraphRagQuestion` | `urn:trustgraph:question:{uuid}` | RAG ya grafu ya maarifa |
| `tg:DocRagQuestion` | `urn:trustgraph:docrag:{uuid}` | RAG ya hati/sehemu |
| `tg:AgentQuestion` | `urn:trustgraph:agent:{uuid}` | Wakala wa ReAct |

Hii inaruhusu kuuliza maswali yote kupitia `tg:Question` huku ikiwezesha kuchujwa kwa utaratibu maalum kupitia aina.

## Mfumo wa Asili

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

### Mfumo wa Asili ya Hati ya RAG

```
Question (urn:trustgraph:docrag:{uuid})
    │
    │  tg:query = "User's question"
    │  prov:startedAtTime = timestamp
    │  rdf:type = prov:Activity, tg:Question
    │
    ↓ prov:wasGeneratedBy
    │
Exploration (urn:trustgraph:docrag:{uuid}/exploration)
    │
    │  tg:chunkCount = 5
    │  tg:selectedChunk = "chunk-id-1"
    │  tg:selectedChunk = "chunk-id-2"
    │  ...
    │  rdf:type = prov:Entity, tg:Exploration
    │
    ↓ prov:wasDerivedFrom
    │
Synthesis (urn:trustgraph:docrag:{uuid}/synthesis)
    │
    │  tg:content = "The synthesized answer..."
    │  rdf:type = prov:Entity, tg:Synthesis
```

## Mabadiliko Yanayohitajika

### 1. Mabadiliko ya Muundo

**Faili:** `trustgraph-base/trustgraph/schema/services/agent.py`

Ongeza sehemu za `session_id` na `collection` kwenye `AgentRequest`:
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

**Faidio:** `trustgraph-base/trustgraph/messaging/translators/agent.py`

Sasisha mtafsiri ili kushughulikia `session_id` na `collection` katika `to_pulsar()` na `from_pulsar()`.

### 2. Ongeza Mzalishaji wa Ufafanuzi kwa Huduma ya Wakala

**Faidio:** `trustgraph-flow/trustgraph/agent/react/service.py`

Sajili "mzalishaji wa ufafanuzi" (mfumo sawa na GraphRAG):
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

### 3. Uzalishaji wa Mfumo wa Asili

**Faili:** `trustgraph-base/trustgraph/provenance/agent.py`

Unda kazi za msaada (kama zile za GraphRAG, kama `question_triples`, `exploration_triples`, n.k.):
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

### 4. Ufafanuzi wa Aina

**Faili:** `trustgraph-base/trustgraph/provenance/namespaces.py`

Ongeza aina za vitu vya uelewaji na sentensi za wakala:
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

## Faili Yaliyobadilishwa

| Faili | Mabadiliko |
|------|--------|
| `trustgraph-base/trustgraph/schema/services/agent.py` | Ongeza `session_id` na `collection` kwenye `AgentRequest` |
| `trustgraph-base/trustgraph/messaging/translators/agent.py` | Sasisha `translator` kwa ajili ya sehemu mpya |
| `trustgraph-base/trustgraph/provenance/namespaces.py` | Ongeza aina za `entity`, `agent predicates`, na `Document RAG predicates` |
| `trustgraph-base/trustgraph/provenance/triples.py` | Ongeza aina za `TG` kwenye `GraphRAG triple builders`, ongeza `Document RAG triple builders` |
| `trustgraph-base/trustgraph/provenance/uris.py` | Ongeza `Document RAG URI generators` |
| `trustgraph-base/trustgraph/provenance/__init__.py` | Export aina mpya, `predicates`, na `Document RAG functions` |
| `trustgraph-base/trustgraph/schema/services/retrieval.py` | Ongeza `explain_id` na `explain_graph` kwenye `DocumentRagResponse` |
| `trustgraph-base/trustgraph/messaging/translators/retrieval.py` | Sasisha `DocumentRagResponseTranslator` kwa ajili ya sehemu za `explainability` |
| `trustgraph-flow/trustgraph/agent/react/service.py` | Ongeza mzalishaji wa `explainability` + mantiki ya kurekodi |
| `trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py` | Ongeza `explainability callback` na toa `provenance triples` |
| `trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` | Ongeza mzalishaji wa `explainability` na uunganishe `callback` |
| `trustgraph-cli/trustgraph/cli/show_explain_trace.py` | Shirikisha aina za `agent trace` |
| `trustgraph-cli/trustgraph/cli/list_explain_traces.py` | Orodha `agent sessions` pamoja na `GraphRAG` |

## Faili Zilizoundwa

| Faili | Madhumuni |
|------|---------|
| `trustgraph-base/trustgraph/provenance/agent.py` | Wazalishaji wa `triple` maalum kwa `agent` |

## Mabadiliko ya CLI

**Kugundua:** Maswali ya `GraphRAG` na `Agent` yana aina ya `tg:Question`. Hutofautishwa na:
1. Mfumo wa `URI`: `urn:trustgraph:agent:` dhidi ya `urn:trustgraph:question:`
2. Vipengele vilivyotokana: `tg:Analysis` (`agent`) dhidi ya `tg:Exploration` (`GraphRAG`)

**`list_explain_traces.py`:**
- Inaonyesha safu ya Aina (Agent vs GraphRAG)

**`show_explain_trace.py`:**
- Hugundua kiotomatiki aina ya `trace`
- Uonyesho wa `agent` unaonyesha: Swali → Hatua za uchambuzi → Hitimisho

## Utangamano na Mifumo ya Zamani

- `session_id` huenda kwa `""` - maombi ya zamani hufanya kazi, lakini hayata na `provenance`
- `collection` huenda kwa `"default"` - `fallback` inayofaa
- CLI hushughulikia aina zote za `trace` kwa utulivu

## Uthibitisho

```bash
# Run an agent query
tg-invoke-agent -q "What is the capital of France?"

# List traces (should show agent sessions with Type column)
tg-list-explain-traces -U trustgraph -C default

# Show agent trace
tg-show-explain-trace "urn:trustgraph:agent:xxx"
```

## Kazi Zinazotarajiwa (Sio Katika Mradi Huyu)

- Utendakazi wa utegemezi wa DAG (wakati uchambuzi N hutumia matokeo kutoka kwa uchambuzi kadhaa uliopita)
- Uunganisho wa utambulisho wa zana maalum (KnowledgeQuery → faili yake ya GraphRAG)
- Utumaji wa utambulisho wa mtiririko (tumia kwa wakati, sio kwa wingi mwisho)
