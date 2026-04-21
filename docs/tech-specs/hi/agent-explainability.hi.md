---
layout: default
title: "एजेंट स्पष्टता: उत्पत्ति रिकॉर्डिंग"
parent: "Hindi (Beta)"
---

# एजेंट स्पष्टता: उत्पत्ति रिकॉर्डिंग

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## अवलोकन

रिएक्ट एजेंट लूप में उत्पत्ति रिकॉर्डिंग जोड़ें ताकि एजेंट सत्रों को ट्रैक और डीबग किया जा सके, जो कि ग्राफआरएजी के समान स्पष्टता बुनियादी ढांचे का उपयोग करके किया जा सके।

**डिजाइन निर्णय:**
`urn:graph:retrieval` (सामान्य स्पष्टता ग्राफ) में लिखें
फिलहाल रैखिक निर्भरता श्रृंखला (विश्लेषण N → wasDerivedFrom → विश्लेषण N-1)
उपकरण अपार ब्लैक बॉक्स हैं (केवल इनपुट/आउटपुट रिकॉर्ड करें)
डीएजी समर्थन भविष्य के पुनरावृत्ति के लिए स्थगित है

## इकाई प्रकार

ग्राफआरएजी और एजेंट दोनों ही ट्रस्टग्राफ-विशिष्ट उपप्रकारों के साथ पीआरओवी-ओ को आधार ऑन्टोलॉजी के रूप में उपयोग करते हैं:

### ग्राफआरएजी प्रकार
| इकाई | पीआरओवी-ओ प्रकार | टीजी प्रकार | विवरण |
|--------|-------------|----------|-------------|
| प्रश्न | `prov:Activity` | `tg:Question`, `tg:GraphRagQuestion` | उपयोगकर्ता का प्रश्न |
| अन्वेषण | `prov:Entity` | `tg:Exploration` | ज्ञान ग्राफ से प्राप्त किनारे |
| फोकस | `prov:Entity` | `tg:Focus` | तर्क के साथ चयनित किनारे |
| संश्लेषण | `prov:Entity` | `tg:Synthesis` | अंतिम उत्तर |

### एजेंट प्रकार
| इकाई | पीआरओवी-ओ प्रकार | टीजी प्रकार | विवरण |
|--------|-------------|----------|-------------|
| प्रश्न | `prov:Activity` | `tg:Question`, `tg:AgentQuestion` | उपयोगकर्ता का प्रश्न |
| विश्लेषण | `prov:Entity` | `tg:Analysis` | प्रत्येक सोच/कार्य/अवलोकन चक्र |
| निष्कर्ष | `prov:Entity` | `tg:Conclusion` | अंतिम उत्तर |

### दस्तावेज़ आरएजी प्रकार
| इकाई | पीआरओवी-ओ प्रकार | टीजी प्रकार | विवरण |
|--------|-------------|----------|-------------|
| प्रश्न | `prov:Activity` | `tg:Question`, `tg:DocRagQuestion` | उपयोगकर्ता का प्रश्न |
| अन्वेषण | `prov:Entity` | `tg:Exploration` | दस्तावेज़ भंडार से प्राप्त टुकड़े |
| संश्लेषण | `prov:Entity` | `tg:Synthesis` | अंतिम उत्तर |

**ध्यान दें:** दस्तावेज़ आरएजी ग्राफआरएजी के प्रकारों का एक उपसमुच्चय का उपयोग करता है (कोई फोकस चरण नहीं है क्योंकि कोई किनारा चयन/तर्क चरण नहीं है)।

### प्रश्न उपप्रकार

सभी प्रश्न इकाइयों में `tg:Question` को एक आधार प्रकार के रूप में साझा किया जाता है, लेकिन पुनर्प्राप्ति तंत्र की पहचान करने के लिए एक विशिष्ट उपप्रकार होता है:

| उपप्रकार | यूआरआई पैटर्न | तंत्र |
|---------|-------------|-----------|
| `tg:GraphRagQuestion` | `urn:trustgraph:question:{uuid}` | ज्ञान ग्राफ आरएजी |
| `tg:DocRagQuestion` | `urn:trustgraph:docrag:{uuid}` | दस्तावेज़/टुकड़ा आरएजी |
| `tg:AgentQuestion` | `urn:trustgraph:agent:{uuid}` | रीएक्ट एजेंट |

यह सभी प्रश्नों को `tg:Question` के माध्यम से क्वेरी करने की अनुमति देता है, जबकि उपप्रकार के माध्यम से विशिष्ट तंत्र द्वारा फ़िल्टर किया जा सकता है।

## उत्पत्ति मॉडल

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

### दस्तावेज़ आरएजी उत्पत्ति मॉडल

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

## आवश्यक परिवर्तन

### 1. स्कीमा परिवर्तन

**फ़ाइल:** `trustgraph-base/trustgraph/schema/services/agent.py`

`AgentRequest` में `session_id` और `collection` फ़ील्ड जोड़ें:
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

**फ़ाइल:** `trustgraph-base/trustgraph/messaging/translators/agent.py`

अनुवादक को `session_id` और `collection` को `to_pulsar()` और `from_pulsar()` दोनों में संभालने के लिए अपडेट करें।

### 2. एजेंट सेवा में "एक्सप्लेनेबिलिटी" उत्पादक जोड़ें

**फ़ाइल:** `trustgraph-flow/trustgraph/agent/react/service.py`

एक "एक्सप्लेनेबिलिटी" उत्पादक को पंजीकृत करें (ग्राफआरएजी के समान पैटर्न):
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

### 3. उत्पत्ति त्रिक निर्माण

**फ़ाइल:** `trustgraph-base/trustgraph/provenance/agent.py`

सहायक फ़ंक्शन बनाएँ (ग्राफ़आरएजी के `question_triples`, `exploration_triples`, आदि के समान):
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

### 4. प्रकार की परिभाषाएँ

**फ़ाइल:** `trustgraph-base/trustgraph/provenance/namespaces.py`

व्याख्यात्मकता इकाई प्रकार और एजेंट विधेयकों को जोड़ें:
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

## संशोधित फ़ाइलें

| फ़ाइल | परिवर्तन |
|------|--------|
| `trustgraph-base/trustgraph/schema/services/agent.py` | AgentRequest में session_id और collection जोड़ें |
| `trustgraph-base/trustgraph/messaging/translators/agent.py` | नए फ़ील्ड के लिए ट्रांसलेटर को अपडेट करें |
| `trustgraph-base/trustgraph/provenance/namespaces.py` | एंटिटी प्रकार, एजेंट प्रेडिकेट और Document RAG प्रेडिकेट जोड़ें |
| `trustgraph-base/trustgraph/provenance/triples.py` | GraphRAG ट्रिपल बिल्डरों में TG प्रकार जोड़ें, Document RAG ट्रिपल बिल्डर जोड़ें |
| `trustgraph-base/trustgraph/provenance/uris.py` | Document RAG URI जनरेटर जोड़ें |
| `trustgraph-base/trustgraph/provenance/__init__.py` | नए प्रकार, प्रेडिकेट और Document RAG फ़ंक्शन निर्यात करें |
| `trustgraph-base/trustgraph/schema/services/retrieval.py` | DocumentRagResponse में explain_id और explain_graph जोड़ें |
| `trustgraph-base/trustgraph/messaging/translators/retrieval.py` | व्याख्यात्मक फ़ील्ड के लिए DocumentRagResponseTranslator को अपडेट करें |
| `trustgraph-flow/trustgraph/agent/react/service.py` | व्याख्यात्मक उत्पादक + रिकॉर्डिंग लॉजिक जोड़ें |
| `trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py` | व्याख्यात्मक कॉलबैक जोड़ें और प्रोवेनेंस ट्रिपल उत्सर्जित करें |
| `trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` | व्याख्यात्मक उत्पादक जोड़ें और कॉलबैक को कनेक्ट करें |
| `trustgraph-cli/trustgraph/cli/show_explain_trace.py` | एजेंट ट्रेस प्रकारों को संभालें |
| `trustgraph-cli/trustgraph/cli/list_explain_traces.py` | GraphRAG के साथ एजेंट सत्रों को सूचीबद्ध करें |

## बनाई गई फ़ाइलें

| फ़ाइल | उद्देश्य |
|------|---------|
| `trustgraph-base/trustgraph/provenance/agent.py` | एजेंट-विशिष्ट ट्रिपल जनरेटर |

## CLI अपडेट

**पहचान:** GraphRAG और Agent Questions दोनों में `tg:Question` प्रकार होता है। निम्नलिखित द्वारा पहचाना जाता है:
1. URI पैटर्न: `urn:trustgraph:agent:` बनाम `urn:trustgraph:question:`
2. व्युत्पन्न एंटिटीज: `tg:Analysis` (एजेंट) बनाम `tg:Exploration` (GraphRAG)

**`list_explain_traces.py`:**
टाइप कॉलम दिखाता है (एजेंट बनाम GraphRAG)

**`show_explain_trace.py`:**
स्वचालित रूप से ट्रेस प्रकार का पता लगाता है
एजेंट रेंडरिंग दिखाता है: प्रश्न → विश्लेषण चरण(s) → निष्कर्ष

## पिछली अनुकूलता

`session_id` डिफ़ॉल्ट रूप से `""` होता है - पुराने अनुरोध काम करते हैं, लेकिन उनमें प्रोवेनेंस नहीं होगा
`collection` डिफ़ॉल्ट रूप से `"default"` होता है - उचित बैकअप
CLI दोनों ट्रेस प्रकारों को आसानी से संभालता है

## सत्यापन

```bash
# Run an agent query
tg-invoke-agent -q "What is the capital of France?"

# List traces (should show agent sessions with Type column)
tg-list-explain-traces -U trustgraph -C default

# Show agent trace
tg-show-explain-trace "urn:trustgraph:agent:xxx"
```

## भविष्य की योजनाएं (इस पुल अनुरोध में नहीं)

डीएजी निर्भरताएँ (जब विश्लेषण एन, पिछले कई विश्लेषणों के परिणामों का उपयोग करता है)
टूल-विशिष्ट उत्पत्ति लिंकिंग (नॉलेजक्वेरी → इसका ग्राफआरएजी ट्रेस)
स्ट्रीमिंग उत्पत्ति उत्सर्जन (जैसे-जैसे उत्पन्न होता है, अंत में बैच न करें)
