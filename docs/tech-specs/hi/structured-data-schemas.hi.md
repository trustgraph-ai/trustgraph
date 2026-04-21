---
layout: default
title: "संरचित डेटा पल्सर स्कीमा परिवर्तन"
parent: "Hindi (Beta)"
---

# संरचित डेटा पल्सर स्कीमा परिवर्तन

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## अवलोकन

`STRUCTURED_DATA.md` विनिर्देश के आधार पर, यह दस्तावेज़ आवश्यक पल्सर स्कीमा परिवर्धन और संशोधन प्रस्तावित करता है ताकि ट्रस्टग्राफ में संरचित डेटा क्षमताओं का समर्थन किया जा सके।

## आवश्यक स्कीमा परिवर्तन

### 1. कोर स्कीमा संवर्द्धन

#### उन्नत फ़ील्ड परिभाषा
`core/primitives.py` में मौजूदा `Field` वर्ग में अतिरिक्त गुण होने चाहिए:

```python
class Field(Record):
    name = String()
    type = String()  # int, string, long, bool, float, double, timestamp
    size = Integer()
    primary = Boolean()
    description = String()
    # नए फ़ील्ड:
    required = Boolean()  # क्या फ़ील्ड अनिवार्य है
    enum_values = Array(String())  # एनम प्रकार के फ़ील्ड के लिए
    indexed = Boolean()  # क्या फ़ील्ड को अनुक्रमित किया जाना चाहिए
```

### 2. नई ज्ञान स्कीमा

#### 2.1 संरचित डेटा सबमिशन
नई फ़ाइल: `knowledge/structured.py`

```python
from pulsar.schema import Record, String, Bytes, Map
from ..core.metadata import Metadata

class StructuredDataSubmission(Record):
    metadata = Metadata()
    format = String()  # "json", "csv", "xml"
    schema_name = String()  # कॉन्फ़िगरेशन में स्कीमा का संदर्भ
    data = Bytes()  # संसाधित करने के लिए कच्चा डेटा
    options = Map(String())  # प्रारूप-विशिष्ट विकल्प
```

### 3. नई सेवा स्कीमा

#### 3.1 एनएलपी से संरचित क्वेरी सेवा
नई फ़ाइल: `services/nlp_query.py`

```python
from pulsar.schema import Record, String, Array, Map, Integer, Double
from ..core.primitives import Error

class NLPToStructuredQueryRequest(Record):
    natural_language_query = String()
    max_results = Integer()
    context_hints = Map(String())  # क्वेरी पीढ़ी के लिए वैकल्पिक संदर्भ

class NLPToStructuredQueryResponse(Record):
    error = Error()
    graphql_query = String()  # उत्पन्न ग्राफ़क्यूएल क्वेरी
    variables = Map(String())  # यदि कोई हो तो ग्राफ़क्यूएल चर
    detected_schemas = Array(String())  # कौन सी स्कीमा क्वेरी को लक्षित करती हैं
    confidence = Double()
```

#### 3.2 संरचित क्वेरी सेवा
नई फ़ाइल: `services/structured_query.py`

```python
from pulsar.schema import Record, String, Map, Array
from ..core.primitives import Error

class StructuredQueryRequest(Record):
    query = String()  # ग्राफ़क्यूएल क्वेरी
    variables = Map(String())  # ग्राफ़क्यूएल चर
    operation_name = String()  # मल्टी-ऑपरेशन दस्तावेजों के लिए वैकल्पिक ऑपरेशन नाम

class StructuredQueryResponse(Record):
    error = Error()
    data = String()  # JSON-एन्कोडेड ग्राफ़क्यूएल प्रतिक्रिया डेटा
    errors = Array(String())  # यदि कोई हो तो ग्राफ़क्यूएल त्रुटियां
```

#### 2.2 ऑब्जेक्ट निष्कर्षण आउटपुट
नई फ़ाइल: `knowledge/object.py`

```python
from pulsar.schema import Record, String, Map, Double
from ..core.metadata import Metadata

class ExtractedObject(Record):
    metadata = Metadata()
    schema_name = String()  # यह ऑब्जेक्ट किस स्कीमा से संबंधित है
    values = Map(String())  # फ़ील्ड नाम -> मान
    confidence = Double()
    source_span = String()  # पाठ का वह भाग जहां ऑब्जेक्ट पाया गया था
```

### 4. उन्नत ज्ञान स्कीमा

#### 4.1 ऑब्जेक्ट एम्बेडिंग संवर्द्धन
संरचित ऑब्जेक्ट एम्बेडिंग को बेहतर ढंग से समर्थन करने के लिए `knowledge/embeddings.py` को अपडेट करें:

```python
class StructuredObjectEmbedding(Record):
    metadata = Metadata()
    vectors = Array(Array(Double()))
    schema_name = String()
    object_id = String()  # प्राथमिक कुंजी मान
    field_embeddings = Map(Array(Double()))  # प्रति-फ़ील्ड एम्बेडिंग
```

## एकीकरण बिंदु

### फ्लो एकीकरण

इन स्कीमा का उपयोग नए फ्लो मॉड्यूल द्वारा किया जाएगा:
- `trustgraph-flow/trustgraph/decoding/structured` - `StructuredDataSubmission` का उपयोग करता है
- `trustgraph-flow/trustgraph/query/nlp_query/cassandra` - एनएलपी क्वेरी स्कीमा का उपयोग करता है
- `trustgraph-flow/trustgraph/query/objects/cassandra` - संरचित क्वेरी स्कीमा का उपयोग करता है
- `trustgraph-flow/trustgraph/extract/object/row/` - `Chunk` का उपभोग करता है, `ExtractedObject` उत्पन्न करता है
- `trustgraph-flow/trustgraph/storage/objects/cassandra` - `Rows` स्कीमा का उपयोग करता है
- `trustgraph-flow/trustgraph/embeddings/object_embeddings/qdrant` - ऑब्जेक्ट एम्बेडिंग स्कीमा का उपयोग करता है

## कार्यान्वयन नोट्स

1. **स्कीमा संस्करण:** भविष्य के माइग्रेशन समर्थन के लिए `RowSchema` में एक `version` फ़ील्ड जोड़ने पर विचार करें।
2. **प्रकार प्रणाली:** `Field.type` को सभी कैसेंड्रा मूल प्रकारों का समर्थन करना चाहिए।
3. **बैच ऑपरेशन:** अधिकांश सेवाओं को एकल और बैच दोनों ऑपरेशन का समर्थन करना चाहिए।
4. **त्रुटि प्रबंधन:** सभी नई सेवाओं में सुसंगत त्रुटि रिपोर्टिंग।
5. **पिछड़ा संगतता:** मौजूदा स्कीमा अपरिवर्तित रहते हैं, केवल छोटे फ़ील्ड संवर्द्धन को छोड़कर।

## अगले कदम

1. नई संरचना में स्कीमा फ़ाइलें लागू करें।
2. मौजूदा सेवाओं को नए स्कीमा प्रकारों को पहचानने के लिए अपडेट करें।
3. इन स्कीमा का उपयोग करने वाले फ्लो मॉड्यूल लागू करें।
4. नई सेवाओं के लिए गेटवे/रिवर्स-गेटवे एंडपॉइंट बनाएं।
5. स्कीमा सत्यापन के लिए यूनिट परीक्षण बनाएं।
