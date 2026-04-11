---
layout: default
title: "निष्कर्षण का स्रोत: सबग्राफ मॉडल"
parent: "Hindi (Beta)"
---

# निष्कर्षण का स्रोत: सबग्राफ मॉडल

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## समस्या

निष्कर्षण के समय का वर्तमान स्रोत जानकारी एक पूर्ण पुन: निरूपण प्रति उत्पन्न करता है
निष्कर्षित त्रिगुट: प्रत्येक ज्ञान तथ्य के लिए एक अद्वितीय `stmt_uri`, `activity_uri`, और संबंधित
<<<<<<< HEAD
PROV-O मेटाडेटा। एक ऐसे खंड को संसाधित करना जो 20 संबंधों का उत्पादन करता है, उसमें लगभग 220 स्रोत जानकारी त्रिगुट होते हैं, इसके अतिरिक्त
=======
PROV-O मेटाडेटा। एक ऐसे खंड को संसाधित करना जो 20 संबंध उत्पन्न करता है, उसमें लगभग 220 स्रोत जानकारी त्रिगुट होते हैं, इसके अतिरिक्त
>>>>>>> 82edf2d (New md files from RunPod)
लगभग 20 ज्ञान त्रिगुट - लगभग 10:1 का ओवरहेड।


यह महंगा है (भंडारण, अनुक्रमण, प्रसारण) और अर्थपूर्ण रूप से
गलत है। प्रत्येक खंड को एक एकल LLM कॉल द्वारा संसाधित किया जाता है जो सभी त्रिगुटों को एक लेनदेन में उत्पन्न करता है।
वर्तमान प्रति-त्रिगुट मॉडल 20 स्वतंत्र निष्कर्षण
घटनाओं का भ्रम पैदा करके इसे अस्पष्ट करता है।


इसके अतिरिक्त, चार निष्कर्षण प्रोसेसरों में से दो (kg-extract-ontology,
kg-extract-agent) में कोई स्रोत जानकारी नहीं है, जिससे ऑडिट
में अंतराल पैदा होते हैं।

## समाधान

प्रति-त्रिगुट पुन: निरूपण को एक **सबग्राफ मॉडल** से बदलें: एक स्रोत जानकारी
रिकॉर्ड प्रति खंड निष्कर्षण, उस खंड से उत्पन्न सभी त्रिगुटों में साझा किया जाता है।


### शब्दावली परिवर्तन

| पुराना | नया |
|-----|-----|
| `stmt_uri` (`https://trustgraph.ai/stmt/{uuid}`) | `subgraph_uri` (`https://trustgraph.ai/subgraph/{uuid}`) |
| `statement_uri()` | `subgraph_uri()` |
| `tg:reifies` (1:1, पहचान) | `tg:contains` (1:कई, समावेशन) |

### लक्षित संरचना

सभी स्रोत जानकारी त्रिगुट `urn:graph:source` नामित ग्राफ में जाते हैं।

```
# Subgraph contains each extracted triple (RDF-star quoted triples)
<subgraph> tg:contains <<s1 p1 o1>> .
<subgraph> tg:contains <<s2 p2 o2>> .
<subgraph> tg:contains <<s3 p3 o3>> .

# Derivation from source chunk
<subgraph> prov:wasDerivedFrom <chunk_uri> .
<subgraph> prov:wasGeneratedBy <activity> .

# Activity: one per chunk extraction
<activity> rdf:type          prov:Activity .
<activity> rdfs:label        "{component_name} extraction" .
<activity> prov:used         <chunk_uri> .
<activity> prov:wasAssociatedWith <agent> .
<activity> prov:startedAtTime "2026-03-13T10:00:00Z" .
<activity> tg:componentVersion "0.25.0" .
<activity> tg:llmModel       "gpt-4" .          # if available
<activity> tg:ontology        <ontology_uri> .   # if available

# Agent: stable per component
<agent> rdf:type   prov:Agent .
<agent> rdfs:label "{component_name}" .
```

### मात्रा की तुलना

<<<<<<< HEAD
एक ऐसे खंड के लिए जो N निकाले गए त्रिगुण उत्पन्न करता है:
=======
एक ऐसे खंड के लिए जो N निकाले गए त्रिगुण (ट्रिपल्स) उत्पन्न करता है:
>>>>>>> 82edf2d (New md files from RunPod)

| | पुराना (प्रति-त्रिगुण) | नया (उप-ग्राफ) |
|---|---|---|
| `tg:contains` / `tg:reifies` | N | N |
| गतिविधि त्रिगुण | ~9 x N | ~9 |
| एजेंट त्रिगुण | 2 x N | 2 |
| कथन/उप-ग्राफ मेटाडेटा | 2 x N | 2 |
| **कुल प्रामाणिकता त्रिगुण** | **~13N** | **N + 13** |
| **उदाहरण (N=20)** | **~260** | **33** |

## दायरा

### अपडेट करने के लिए प्रोसेसर (मौजूदा प्रामाणिकता, प्रति-त्रिगुण)

**kg-extract-definitions**
(`trustgraph-flow/trustgraph/extract/kg/definitions/extract.py`)

वर्तमान में, यह `statement_uri()` + `triple_provenance_triples()` को परिभाषा के प्रत्येक लूप के अंदर कॉल करता है।


परिवर्तन:
लूप से पहले `subgraph_uri()` और `activity_uri()` का निर्माण करें।
लूप के अंदर `tg:contains` त्रिकों को एकत्र करें।
लूप के बाद एक बार साझा गतिविधि/एजेंट/व्युत्पत्ति ब्लॉक उत्सर्जित करें।

**kg-extract-relationships**
(`trustgraph-flow/trustgraph/extract/kg/relationships/extract.py`)

परिभाषाओं के समान पैटर्न। समान परिवर्तन।

### उत्पत्ति जोड़ने के लिए प्रोसेसर (वर्तमान में गायब)

**kg-extract-ontology**
(`trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`)

<<<<<<< HEAD
वर्तमान में, यह बिना किसी स्रोत जानकारी के त्रिक उत्पन्न करता है। उपग्राफ स्रोत जानकारी जोड़ें।
उसी पैटर्न का उपयोग करके: प्रत्येक खंड के लिए एक उपग्राफ, प्रत्येक के लिए `tg:contains`।
निकाले गए त्रिगुट।
=======
वर्तमान में, यह बिना किसी स्रोत जानकारी के त्रिक (triples) उत्पन्न करता है। उप-ग्राफ (subgraph) की स्रोत जानकारी जोड़ें।
उसी पैटर्न का उपयोग करके: प्रत्येक खंड (chunk) के लिए एक उप-ग्राफ, प्रत्येक निकाले गए त्रिक के लिए `tg:contains`।

>>>>>>> 82edf2d (New md files from RunPod)

**kg-extract-agent**
(`trustgraph-flow/trustgraph/extract/kg/agent/extract.py`)

<<<<<<< HEAD
वर्तमान में, यह बिना किसी स्रोत जानकारी के त्रिक (triples) उत्पन्न करता है। समान पैटर्न का उपयोग करके सबग्राफ (subgraph) स्रोत जानकारी जोड़ें।


### साझा उत्पत्ति लाइब्रेरी में परिवर्तन

**`trustgraph-base/trustgraph/provenance/triples.py`**

`triple_provenance_triples()` को `subgraph_provenance_triples()` से बदलें
नया फ़ंक्शन एक एकल के बजाय निकाले गए त्रिपुलों की सूची को स्वीकार करता है
प्रत्येक ट्रिपल के लिए एक `tg:contains` उत्पन्न करता है, साझा गतिविधि/एजेंट ब्लॉक
पुराने `triple_provenance_triples()` को हटा दें
=======
वर्तमान में, यह बिना किसी स्रोत जानकारी के त्रिक (triples) उत्पन्न करता है। उप-ग्राफ (subgraph) की स्रोत जानकारी उसी पैटर्न का उपयोग करके जोड़ें।


### साझा स्रोत पुस्तकालय (Shared Provenance Library) में परिवर्तन

**`trustgraph-base/trustgraph/provenance/triples.py`**

`triple_provenance_triples()` को `subgraph_provenance_triples()` से बदलें।
नया फ़ंक्शन एक एकल त्रिक के बजाय निकाले गए त्रिकों की एक सूची स्वीकार करता है।
प्रत्येक त्रिक के लिए एक `tg:contains` उत्पन्न करता है, जो साझा गतिविधि/एजेंट ब्लॉक है।
पुराने `triple_provenance_triples()` को हटा दें।
>>>>>>> 82edf2d (New md files from RunPod)

**`trustgraph-base/trustgraph/provenance/uris.py`**

`statement_uri()` को `subgraph_uri()` से बदलें।

**`trustgraph-base/trustgraph/provenance/namespaces.py`**

`TG_REIFIES` को `TG_CONTAINS` से बदलें।

### दायरे में नहीं

<<<<<<< HEAD
**kg-extract-topics**: पुराना-शैली का प्रोसेसर, वर्तमान में उपयोग में नहीं है।
  मानक प्रक्रियाओं में।
**kg-extract-rows**: पंक्तियाँ उत्पन्न करता है, ट्रिपल नहीं, अलग उत्पत्ति मॉडल।
  मॉडल।
**क्वेरी-टाइम प्रोवेनेंस** (`urn:graph:retrieval`): एक अलग चिंता का विषय,
  पहले से ही एक अलग पैटर्न का उपयोग करता है (प्रश्न/अन्वेषण/फोकस/संश्लेषण)।
=======
**kg-extract-topics**: पुराना शैली का प्रोसेसर, वर्तमान में उपयोग में नहीं है।
  मानक प्रक्रियाओं में।
**kg-extract-rows**: पंक्तियाँ उत्पन्न करता है, ट्रिपल नहीं, अलग उत्पत्ति मॉडल।
  मॉडल।
**क्वेरी-टाइम प्रोवेनेंस** (`urn:graph:retrieval`): एक अलग विषय,
  पहले से ही एक अलग पैटर्न का उपयोग करता है (प्रश्न/अन्वेषण/ध्यान/संश्लेषण)।
>>>>>>> 82edf2d (New md files from RunPod)
**दस्तावेज़/पृष्ठ/खंड प्रोवेनेंस** (पीडीएफ डिकोडर, चंकर): पहले से ही उपयोग करता है
  `derived_entity_triples()` जो प्रति-एंटिटी है, प्रति-ट्रिपल नहीं - कोई
  अनावश्यकता समस्या नहीं।

## कार्यान्वयन संबंधी टिप्पणियाँ

### प्रोसेसर लूप का पुनर्गठन

पहले (प्रत्येक त्रिक के लिए, संबंधों में):
```python
for rel in rels:
    # ... build relationship_triple ...
    stmt_uri = statement_uri()
    prov_triples = triple_provenance_triples(
        stmt_uri=stmt_uri,
        extracted_triple=relationship_triple,
        ...
    )
    triples.extend(set_graph(prov_triples, GRAPH_SOURCE))
```

<<<<<<< HEAD
(उपग्राफ के बाद):
=======
(उप-ग्राफ के बाद):
>>>>>>> 82edf2d (New md files from RunPod)
```python
sg_uri = subgraph_uri()

for rel in rels:
    # ... build relationship_triple ...
    extracted_triples.append(relationship_triple)

prov_triples = subgraph_provenance_triples(
    subgraph_uri=sg_uri,
    extracted_triples=extracted_triples,
    chunk_uri=chunk_uri,
    component_name=default_ident,
    component_version=COMPONENT_VERSION,
    llm_model=llm_model,
    ontology_uri=ontology_uri,
)
triples.extend(set_graph(prov_triples, GRAPH_SOURCE))
```

### नया सहायक हस्ताक्षर

```python
def subgraph_provenance_triples(
    subgraph_uri: str,
    extracted_triples: List[Triple],
    chunk_uri: str,
    component_name: str,
    component_version: str,
    llm_model: Optional[str] = None,
    ontology_uri: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> List[Triple]:
    """
    Build provenance triples for a subgraph of extracted knowledge.

    Creates:
    - tg:contains link for each extracted triple (RDF-star quoted)
    - One prov:wasDerivedFrom link to source chunk
    - One activity with agent metadata
    """
```

### महत्वपूर्ण परिवर्तन

<<<<<<< HEAD
यह उत्पत्ति मॉडल में एक महत्वपूर्ण बदलाव है। उत्पत्ति (प्रोवेनेंस) का
जारी किया गया है, इसलिए माइग्रेशन की आवश्यकता नहीं है। पुराना `tg:reifies` /
`statement_uri` कोड पूरी तरह से हटाया जा सकता है।
=======
यह प्रामाणिकता मॉडल में एक महत्वपूर्ण बदलाव है। प्रामाणिकता अभी तक जारी नहीं की गई है, इसलिए किसी माइग्रेशन की आवश्यकता नहीं है। पुराना ⟦CODE_0⟧ / ⟦CODE_0⟧ कोड पूरी तरह से हटाया जा सकता है।
यह प्रामाणिकता मॉडल में एक महत्वपूर्ण बदलाव है। प्रामाणिकता अभी तक जारी नहीं की गई है, इसलिए किसी माइग्रेशन की आवश्यकता नहीं है। पुराना `tg:reifies` / `tg:reifies` कोड पूरी तरह से हटाया जा सकता है।
यह प्रामाणिकता मॉडल में एक महत्वपूर्ण बदलाव है। प्रामाणिकता अभी तक जारी नहीं की गई है, इसलिए किसी माइग्रेशन की आवश्यकता नहीं है। पुराना `statement_uri` / `statement_uri` कोड पूरी तरह से हटाया जा सकता है।
>>>>>>> 82edf2d (New md files from RunPod)
