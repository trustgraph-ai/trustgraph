# أصل الاستخراج: نموذج الرسم البياني الفرعي

## المشكلة

حاليًا، يقوم تتبع أصل الاستخراج بإنشاء تجسيد كامل لكل ثلاثية مستخرجة:
معرف فريد `stmt_uri`، و `activity_uri`، وبيانات وصفية PROV-O مرتبطة
لكل حقيقة معرفية. يؤدي معالجة جزء واحد ينتج عنه 20 علاقة إلى إنتاج حوالي 220 ثلاثية لتتبع الأصل بالإضافة إلى
حوالي 20 ثلاثية معرفية - وهو عبء إضافي يقدر بحوالي 10:1.


هذا مكلف للغاية (من حيث التخزين والفهرسة والنقل) وغير دقيق من الناحية الدلالية.
تتم معالجة كل جزء بواسطة استدعاء واحد لنموذج اللغة الكبير (LLM) ينتج
جميع الثلاثيات الخاصة به في معاملة واحدة.
يخفي النموذج الحالي لكل ثلاثية ذلك من خلال خلق وهم بوجود 20 عملية استخراج
مستقلة.

بالإضافة إلى ذلك، لا توجد أي معلومات عن مصدرين من أصل أربعة معالجات للاستخراج (kg-extract-ontology،
kg-extract-agent)، مما يترك فجوات في مسار التدقيق.


## الحل

استبدال عملية التجسيد لكل ثلاثية بنموذج **رسم بياني فرعي**: سجل واحد للبيانات الوصفية لكل جزء مستخرج، ويتم مشاركته عبر جميع الثلاثيات الناتجة عن هذا الجزء.



### تغيير في المصطلحات

| القديم | الجديد |
|-----|-----|
| `stmt_uri` (`https://trustgraph.ai/stmt/{uuid}`) | `subgraph_uri` (`https://trustgraph.ai/subgraph/{uuid}`) |
| `statement_uri()` | `subgraph_uri()` |
| `tg:reifies` (1:1، تطابق) | `tg:contains` (1:كثير، احتواء) |

### الهيكل المستهدف

يجب أن تضاف جميع الثلاثيات المتعلقة بأصل البيانات إلى الرسم البياني المسمى `urn:graph:source`.

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

### مقارنة الحجم

لكل جزء ينتج عنه N من الثلاثيات المستخرجة:

| | القديم (لكل ثلاثية) | الجديد (الرسم البياني الفرعي) |
|---|---|---|
| `tg:contains` / `tg:reifies` | N | N |
| ثلاثيات النشاط | ~9 × N | ~9 |
| ثلاثيات الوكيل | 2 × N | 2 |
| بيانات التعريف/الرسم البياني الفرعي | 2 × N | 2 |
| **إجمالي ثلاثيات التتبع** | **~13N** | **N + 13** |
| **مثال (N=20)** | **~260** | **33** |

## النطاق

### المعالجات التي سيتم تحديثها (التتبع الحالي، لكل ثلاثية)

**kg-extract-definitions**
(`trustgraph-flow/trustgraph/extract/kg/definitions/extract.py`)

حاليًا، تستدعي `statement_uri()` + `triple_provenance_triples()` داخل
حلقة التعريف لكل عنصر.

التغييرات:
نقل إنشاء `subgraph_uri()` و `activity_uri()` قبل الحلقة
جمع ثلاثيات `tg:contains` داخل الحلقة
إخراج كتلة النشاط/الوكيل/الاشتقاق المشتركة مرة واحدة بعد الحلقة

**kg-extract-relationships**
(`trustgraph-flow/trustgraph/extract/kg/relationships/extract.py`)

نفس النمط مثل التعريفات. نفس التغييرات.

### المعالجات التي يجب إضافتها للتتبع (مفقودة حاليًا)

**kg-extract-ontology**
(`trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`)

حاليًا، يقوم بإخراج ثلاثيات بدون مصدر. أضف مصدر الرسم البياني الفرعي.
باستخدام نفس النمط: رسم بياني فرعي واحد لكل جزء، `tg:contains` لكل
ثلاثية مستخرجة.

**kg-extract-agent**
(`trustgraph-flow/trustgraph/extract/kg/agent/extract.py`)

حاليًا، يقوم بإخراج ثلاثيات بدون مصدر. أضف مصدر الرسم البياني الفرعي
باستخدام نفس النمط.

### تغييرات في مكتبة المصادر المشتركة

**`trustgraph-base/trustgraph/provenance/triples.py`**

استبدل `triple_provenance_triples()` بـ `subgraph_provenance_triples()`
تقبل الدالة الجديدة قائمة بالثلاثيات المستخرجة بدلاً من ثلاثية واحدة.
تقوم بإنشاء `tg:contains` واحد لكل ثلاثية، كتلة نشاط/وكيل مشتركة.
قم بإزالة `triple_provenance_triples()` القديم.

**`trustgraph-base/trustgraph/provenance/uris.py`**

استبدل `statement_uri()` بـ `subgraph_uri()`

**`trustgraph-base/trustgraph/provenance/namespaces.py`**

استبدل `TG_REIFIES` بـ `TG_CONTAINS`

### ليس ضمن النطاق

**kg-extract-topics**: معالج بنمط قديم، ولا يتم استخدامه حاليًا في
  العمليات القياسية.
**kg-extract-rows**: ينتج صفوفًا وليست ثلاثيات، ومن مصدر مختلف.
  نموذج.
**تتبع المصدر في وقت الاستعلام** (`urn:graph:retrieval`): مسألة منفصلة،
  تستخدم بالفعل نمطًا مختلفًا (سؤال/استكشاف/تركيز/توليف).
**أصل المستند/الصفحة/الجزء** (فك تشفير PDF، تقسيم النص): تستخدم بالفعل.
  `derived_entity_triples()` وهو خاص بكل كيان، وليس لكل ثلاثية - لا.
  مشكلة التكرار.

## ملاحظات حول التنفيذ

### إعادة هيكلة حلقة المعالج

قبل (لكل ثلاثية، في العلاقات):
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

بعد (رسم بياني فرعي):
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

### التوقيع المساعد الجديد

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

### تغيير جذري

هذا تغيير جذري في نموذج التتبع. لم يتم
تم إصدارها، لذا لا توجد حاجة إلى ترحيل. الكود القديم `tg:reifies` /
يمكن إزالة كود `statement_uri` تمامًا.
