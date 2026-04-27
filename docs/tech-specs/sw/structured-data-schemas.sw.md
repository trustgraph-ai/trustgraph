---
layout: default
title: "Mfano wa Data, Mbadala ya Pulsar"
parent: "Swahili (Beta)"
---

# Mfano wa Data, Mbadala ya Pulsar

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Maelezo

Kulingana na toleo la `STRUCTURED_DATA.md`, hati hii inatoa mabadiliko muhimu ya mfano wa Pulsar na mabadiliko, ili kupendeza uwezo wa data iliyoundwa katika TrustGraph.

## Mabadiliko muhimu ya mfano

### 1. Uboreshaji wa mfano
#### Maelezo ya shamba
Sasa, kwenye `Field` class katika `core/primitives.py`, lazima ipate mali zaidi:

```python
class Field(Record):
    name = String()
    type = String()  # int, string, long, bool, float, double, timestamp
    size = Integer()
    primary = Boolean()
    description = String()
    # MAELEZO MPYA:
    required = Boolean()  # Mara kama shamba ni muhimu
    enum_values = Array(String())  # Kwa miundo ya shamba
    indexed = Boolean()  # Mara kama shamba linahitajika
```

### 2. Mfano mpya wa Maarifa

#### 2.1 Utumaji Data Iliyoundwa
Faili mpya: `knowledge/structured.py`

```python
from pulsar.schema import Record, String, Bytes, Map
from ..core.metadata import Metadata

class StructuredDataSubmission(Record):
    metadata = Metadata()
    format = String()  # "json", "csv", "xml"
    schema_name = String()  # Mara kama mfano katika faili
    data = Bytes()  # Data iliyoundwa
    options = Map(String())  # Chaguzi maalum kwa format
```

### 3. Mfano mpya wa Huduma

#### 3.1 Huduma ya NLP hadi Sarani ya Data
Faili mpya: `services/nlp_query.py`

```python
from pulsar.schema import Record, String, Array, Map, Integer, Double
from ..core.primitives import Error

class NLPToStructuredQueryRequest(Record):
    natural_language_query = String()
    max_results = Integer()
    context_hints = Map(String())  # Mara kama mawasiliano kwa utengenezaji wa sarani

class NLPToStructuredQueryResponse(Record):
    error = Error()
    graphql_query = String()  # Sarani GraphQL iliyoundwa
    variables = Map(String())  # Chaguzi GraphQL
    detected_schemas = Array(String())  # Miundo ambazo sarani huangalia
    confidence = Double()
```

#### 3.2 Sarani ya Data
Faili mpya: `services/structured_query.py`

```python
from pulsar.schema import Record, String, Map, Array
from ..core.primitives import Error

class StructuredQueryRequest(Record):
    query = String()  # Sarani GraphQL
    variables = Map(String())  # Chaguzi GraphQL
    operation_name = String()  # Mara kama jina la operesheni kwa hati za mfululizo

class StructuredQueryResponse(Record):
    error = Error()
    data = String()  # Data iliyoundwa kwa JSON
    errors = Array(String())  # Mara kama ada GraphQL
```

#### 2.2 Pato la Uteuzi wa Madhara
Faili mpya: `knowledge/object.py`

```python
from pulsar.schema import Record, String, Map, Double
from ..core.metadata import Metadata

class ExtractedObject(Record):
    metadata = Metadata()
    schema_name = String()  # Mara kama mfano
    values = Map(String())  # Jina la shamba -> thamani
    confidence = Double()
    source_span = String()  # Mara kama kitanzi
```

### 4. Mfano wa Maarifa

#### 4.1 Uboreshaji wa Embedings
Badilisha `knowledge/embeddings.py` ili kusaidia uhifadhi wa madhara iliyoundwa:

```python
class StructuredObjectEmbedding(Record):
    metadata = Metadata()
    vectors = Array(Array(Double()))
    schema_name = String()
    object_id = String()  # Thamani muhimu
    field_embeddings = Map(Array(Double()))  # Embedings kwa kila shamba
```

## Vitu vya Uunganishi

### Uunganishi wa Mzunguko

Mifano itatumika na moduli mpya za mzunguko:
- `trustgraph-flow/trustgraph/decoding/structured` - Inatumia StructuredDataSubmission
- `trustgraph-flow/trustgraph/query/nlp_query/cassandra` - Inatumia mifano za sarani
- `trustgraph-flow/trustgraph/query/objects/cassandra` - Inatumia mifano za sarani
- `trustgraph-flow/trustgraph/extract/object/row/` - Inatumia Chunk, inatoa ExtractedObject
- `trustgraph-flow/trustgraph/storage/objects/cassandra` - Inatumia mfano wa Rows
- `trustgraph-flow/trustgraph/embeddings/object_embeddings/qdrant` - Inatumia mifano za embedings
