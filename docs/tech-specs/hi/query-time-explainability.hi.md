---
layout: default
title: "क्वेरी-टाइम एक्सप्लेनेबिलिटी (Query-Time Explainability)"
parent: "Hindi (Beta)"
---

# क्वेरी-टाइम एक्सप्लेनेबिलिटी (Query-Time Explainability)

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## स्थिति (Status)

कार्यान्वित (Implemented)

## अवलोकन (Overview)

यह विनिर्देश बताता है कि GraphRAG क्वेरी निष्पादन के दौरान एक्सप्लेनेबिलिटी डेटा को कैसे रिकॉर्ड और संचारित करता है। इसका लक्ष्य पूर्ण पता लगाने की क्षमता है: अंतिम उत्तर से लेकर चयनित किनारों तक और फिर स्रोत दस्तावेजों तक।

क्वेरी-टाइम एक्सप्लेनेबिलिटी यह कैप्चर करती है कि GraphRAG पाइपलाइन तर्क के दौरान क्या करती है। यह निष्कर्षण-समय के प्रमाण से जुड़ा है, जो रिकॉर्ड करता है कि ज्ञान ग्राफ तथ्यों की उत्पत्ति कहाँ से हुई।

## शब्दावली (Terminology)

| शब्द | परिभाषा |
|------|------------|
| **एक्सप्लेनेबिलिटी (Explainability)** | यह रिकॉर्ड है कि एक परिणाम कैसे प्राप्त किया गया |
| **सेशन (Session)** | एक एकल GraphRAG क्वेरी निष्पादन |
| **एज सिलेक्शन (Edge Selection)** | तर्क के साथ प्रासंगिक किनारों का LLM-संचालित चयन |
| **प्रूवेनेंस चेन (Provenance Chain)** | किनारे → चंक → पृष्ठ → दस्तावेज़ से पथ |

## आर्किटेक्चर (Architecture)

### एक्सप्लेनेबिलिटी फ्लो (Explainability Flow)

```
GraphRAG Query
    │
    ├─► Session Activity
    │       └─► Query text, timestamp
    │
    ├─► Retrieval Entity
    │       └─► All edges retrieved from subgraph
    │
    ├─► Selection Entity
    │       └─► Selected edges with LLM reasoning
    │           └─► Each edge links to extraction provenance
    │
    └─► Answer Entity
            └─► Reference to synthesized response (in librarian)
```

### दो-चरणीय ग्राफआरएजी पाइपलाइन

1. **एज चयन**: एलएलएम सबग्राफ से प्रासंगिक किनारों का चयन करता है, प्रत्येक के लिए तर्क प्रदान करता है।
2. **संश्लेषण**: एलएलएम केवल चयनित किनारों से उत्तर उत्पन्न करता है।

यह अलगाव व्याख्यात्मकता को सक्षम बनाता है - हमें ठीक से पता है कि किन किनारों ने योगदान दिया।

### भंडारण

व्याख्यात्मकता ट्रिपल कॉन्फ़िगर करने योग्य संग्रह में संग्रहीत हैं (डिफ़ॉल्ट: `explainability`)।
यह स्रोत संबंधों के लिए प्रोवी-ओ ऑन्टोलॉजी का उपयोग करता है।
किनारे संदर्भों के लिए आरडीएफ-स्टार रीफिकेशन।
उत्तर सामग्री लाइब्रेरियन सेवा में संग्रहीत है (इनलाइन नहीं - बहुत बड़ा)।

### वास्तविक समय स्ट्रीमिंग

व्याख्यात्मकता घटनाएँ क्लाइंट को क्वेरी निष्पादित होने के दौरान स्ट्रीम की जाती हैं:

1. सत्र बनाया गया → घटना उत्सर्जित।
2. किनारे पुनर्प्राप्त किए गए → घटना उत्सर्जित।
3. तर्क के साथ किनारे चुने गए → घटना उत्सर्जित।
4. उत्तर संश्लेषित → घटना उत्सर्जित।

क्लाइंट को `explain_id` और `explain_collection` प्राप्त होते हैं ताकि पूर्ण विवरण प्राप्त किए जा सकें।

## यूआरआई संरचना

सभी यूआरआई `urn:trustgraph:` नेमस्पेस का उपयोग करते हैं जिसमें यूयूआईडी शामिल हैं:

| इकाई | यूआरआई पैटर्न |
|--------|-------------|
| सत्र | `urn:trustgraph:session:{uuid}` |
| पुनर्प्राप्ति | `urn:trustgraph:prov:retrieval:{uuid}` |
| चयन | `urn:trustgraph:prov:selection:{uuid}` |
| उत्तर | `urn:trustgraph:prov:answer:{uuid}` |
| किनारे का चयन | `urn:trustgraph:prov:edge:{uuid}:{index}` |

## आरडीएफ मॉडल (प्रोवी-ओ)

### सत्र गतिविधि

```turtle
<session-uri> a prov:Activity ;
    rdfs:label "GraphRAG query session" ;
    prov:startedAtTime "2024-01-15T10:30:00Z" ;
    tg:query "What was the War on Terror?" .
```

### पुनर्प्राप्ति इकाई

```turtle
<retrieval-uri> a prov:Entity ;
    rdfs:label "Retrieved edges" ;
    prov:wasGeneratedBy <session-uri> ;
    tg:edgeCount 50 .
```

### चयन इकाई

```turtle
<selection-uri> a prov:Entity ;
    rdfs:label "Selected edges" ;
    prov:wasDerivedFrom <retrieval-uri> ;
    tg:selectedEdge <edge-sel-0> ;
    tg:selectedEdge <edge-sel-1> .

<edge-sel-0> tg:edge << <s> <p> <o> >> ;
    tg:reasoning "This edge establishes the key relationship..." .
```

### उत्तर इकाई

```turtle
<answer-uri> a prov:Entity ;
    rdfs:label "GraphRAG answer" ;
    prov:wasDerivedFrom <selection-uri> ;
    tg:document <urn:trustgraph:answer:{uuid}> .
```

`tg:document` संदर्भ लाइब्रेरियन सेवा में संग्रहीत उत्तर को दर्शाता है।

## नेमस्पेस स्थिरांक

`trustgraph-base/trustgraph/provenance/namespaces.py` में परिभाषित:

| स्थिरांक | यूआरआई |
|----------|-----|
| `TG_QUERY` | `https://trustgraph.ai/ns/query` |
| `TG_EDGE_COUNT` | `https://trustgraph.ai/ns/edgeCount` |
| `TG_SELECTED_EDGE` | `https://trustgraph.ai/ns/selectedEdge` |
| `TG_EDGE` | `https://trustgraph.ai/ns/edge` |
| `TG_REASONING` | `https://trustgraph.ai/ns/reasoning` |
| `TG_CONTENT` | `https://trustgraph.ai/ns/content` |
| `TG_DOCUMENT` | `https://trustgraph.ai/ns/document` |

## GraphRagResponse स्कीमा

```python
@dataclass
class GraphRagResponse:
    error: Error | None = None
    response: str = ""
    end_of_stream: bool = False
    explain_id: str | None = None
    explain_collection: str | None = None
    message_type: str = ""  # "chunk" or "explain"
    end_of_session: bool = False
```

### संदेश प्रकार

| संदेश_प्रकार | उद्देश्य |
|--------------|---------|
| `chunk` | प्रतिक्रिया पाठ (स्ट्रीमिंग या अंतिम) |
| `explain` | आईआरआई संदर्भ के साथ व्याख्यात्मक घटना |

### सत्र जीवनचक्र

1. कई `explain` संदेश (सत्र, पुनर्प्राप्ति, चयन, उत्तर)
2. कई `chunk` संदेश (स्ट्रीमिंग प्रतिक्रिया)
3. `end_of_session=True` के साथ अंतिम `chunk`

## एज चयन प्रारूप

एलएलएम चयनित किनारों के साथ JSONL लौटाता है:

```jsonl
{"id": "edge-hash-1", "reasoning": "This edge shows the key relationship..."}
{"id": "edge-hash-2", "reasoning": "Provides supporting evidence..."}
```

`id`, `(labeled_s, labeled_p, labeled_o)` का एक हैश है, जिसकी गणना `edge_id()` द्वारा की जाती है।

## यूआरआई का संरक्षण

### समस्या

GraphRAG, एलएलएम को समझने योग्य लेबल प्रदर्शित करता है, लेकिन स्पष्टीकरण के लिए मूल यूआरआई की आवश्यकता होती है ताकि स्रोत का पता लगाया जा सके।

### समाधान

`get_labelgraph()` दोनों लौटाता है:
`labeled_edges`: एलएलएम के लिए `(label_s, label_p, label_o)` की सूची
`uri_map`: एक डिक्शनरी जो `edge_id(labels)` को `(uri_s, uri_p, uri_o)` से जोड़ती है।

जब व्याख्यात्मक डेटा संग्रहीत किया जाता है, तो `uri_map` से यूआरआई का उपयोग किया जाता है।

## उत्पत्ति अनुरेखण

### किनारे से स्रोत तक

चयनित किनारों को मूल दस्तावेजों तक वापस ट्रेस किया जा सकता है:

1. समाहित उपग्राफ के लिए क्वेरी करें: `?subgraph tg:contains <<s p o>>`
2. मूल दस्तावेज़ तक `prov:wasDerivedFrom` श्रृंखला का पालन करें
3. श्रृंखला में प्रत्येक चरण: खंड → पृष्ठ → दस्तावेज़

### कैसेंड्रा उद्धृत त्रिक समर्थन

कैसेंड्रा क्वेरी सेवा उद्धृत त्रिकों के मिलान का समर्थन करती है:

```python
# In get_term_value():
elif term.type == TRIPLE:
    return serialize_triple(term.triple)
```

यह इस तरह के प्रश्नों को सक्षम करता है:
```
?subgraph tg:contains <<http://example.org/s http://example.org/p "value">>
```

## कमांड लाइन इंटरफेस (CLI) का उपयोग

```bash
tg-invoke-graph-rag --explainable -q "What was the War on Terror?"
```

### आउटपुट प्रारूप

```
[session] urn:trustgraph:session:abc123

[retrieval] urn:trustgraph:prov:retrieval:abc123

[selection] urn:trustgraph:prov:selection:abc123
    Selected 12 edge(s)
      Edge: (Guantanamo, definition, A detention facility...)
        Reason: Directly connects Guantanamo to the War on Terror
        Source: Chunk 1 → Page 2 → Beyond the Vigilant State

[answer] urn:trustgraph:prov:answer:abc123

Based on the provided knowledge statements...
```

### विशेषताएं

क्वेरी के दौरान वास्तविक समय में व्याख्यात्मक घटनाएं।
`rdfs:label` के माध्यम से एज घटकों के लिए लेबल समाधान।
`prov:wasDerivedFrom` के माध्यम से स्रोत श्रृंखला का पता लगाना।
बार-बार क्वेरी से बचने के लिए लेबल कैशिंग।

## कार्यान्वित फाइलें

| फ़ाइल | उद्देश्य |
|------|---------|
| `trustgraph-base/trustgraph/provenance/uris.py` | यूआरआई जनरेटर |
| `trustgraph-base/trustgraph/provenance/namespaces.py` | आरडीएफ नेमस्पेस स्थिरांक |
| `trustgraph-base/trustgraph/provenance/triples.py` | ट्रिपल बिल्डर |
| `trustgraph-base/trustgraph/schema/services/retrieval.py` | GraphRagResponse स्कीमा |
| `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py` | यूआरआई संरक्षण के साथ मुख्य GraphRAG |
| `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` | लाइब्रेरियन एकीकरण के साथ सेवा |
| `trustgraph-flow/trustgraph/query/triples/cassandra/service.py` | उद्धृत ट्रिपल क्वेरी समर्थन |
| `trustgraph-cli/trustgraph/cli/invoke_graph_rag.py` | व्याख्यात्मक प्रदर्शन के साथ सीएलआई |

## संदर्भ

PROV-O (डब्ल्यू3सी प्रोवेनेंस ऑन्टोलॉजी): https://www.w3.org/TR/prov-o/
RDF-star: https://w3c.github.io/rdf-star/
निष्कर्षण-समय प्रोवेनेंस: `docs/tech-specs/extraction-time-provenance.md`
