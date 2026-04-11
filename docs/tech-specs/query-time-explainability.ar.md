# الشرح في وقت الاستعلام

## الحالة

تم التنفيذ

## نظرة عامة

يصف هذا المواصفات كيفية تسجيل GraphRAG وتوصيل بيانات الشرح أثناء تنفيذ الاستعلام. الهدف هو التتبع الكامل: من الإجابة النهائية إلى الحواف المحددة ثم إلى المستندات المصدر.

يمثل الشرح في وقت الاستعلام ما قام به مسار عمل GraphRAG أثناء عملية الاستدلال. وهو مرتبط ببيانات المصدر التي تم تسجيلها في وقت الاستخراج، والتي تسجل أصل حقائق الرسم البياني المعرفي.

## المصطلحات

| المصطلح | التعريف |
|------|------------|
| **الشرح** | سجل لكيفية اشتقاق نتيجة |
| **الجلسة** | تنفيذ استعلام GraphRAG واحد |
| **اختيار الحواف** | اختيار الحواف ذات الصلة المدفوع بالنماذج اللغوية الكبيرة مع الاستدلال |
| **سلسلة المصدر** | مسار من الحافة → الجزء → الصفحة → المستند |

## البنية

### تدفق الشرح

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

### خط أنابيب GraphRAG ثنائي المراحل

1. **اختيار الحواف**: يقوم نموذج اللغة الكبيرة (LLM) باختيار الحواف ذات الصلة من الرسم البياني الفرعي، مع تقديم مبررات لكل حافة.
2. **التوليف**: يقوم نموذج اللغة الكبيرة (LLM) بإنشاء الإجابة من الحواف المحددة فقط.

هذا الفصل يمكّن من إمكانية التفسير - نحن نعرف بالضبط أي الحواف ساهمت.

### التخزين

يتم تخزين ثلاثيات إمكانية التفسير في مجموعة قابلة للتكوين (افتراضي: `explainability`).
يستخدم علم الوجود PROV-O للعلاقات المتعلقة بالأصل.
إعادة تمثيل RDF-star للمراجع إلى الحواف.
يتم تخزين محتوى الإجابة في خدمة "المكتبار" (وليس مضمنًا - كبير جدًا).

### البث في الوقت الفعلي

يتم بث أحداث إمكانية التفسير إلى العميل أثناء تنفيذ الاستعلام:

1. تم إنشاء جلسة → تم إرسال حدث.
2. تم استرداد الحواف → تم إرسال حدث.
3. تم تحديد الحواف مع التبرير → تم إرسال حدث.
4. تم توليف الإجابة → تم إرسال حدث.

يتلقى العميل `explain_id` و `explain_collection` لاسترداد التفاصيل الكاملة.

## هيكل URI

تستخدم جميع عناوين URI مساحة الاسم `urn:trustgraph:` مع معرفات UUID:

| الكيان | نمط URI |
|--------|-------------|
| الجلسة | `urn:trustgraph:session:{uuid}` |
| الاسترداد | `urn:trustgraph:prov:retrieval:{uuid}` |
| التحديد | `urn:trustgraph:prov:selection:{uuid}` |
| الإجابة | `urn:trustgraph:prov:answer:{uuid}` |
| تحديد الحواف | `urn:trustgraph:prov:edge:{uuid}:{index}` |

## نموذج RDF (PROV-O)

### نشاط الجلسة

```turtle
<session-uri> a prov:Activity ;
    rdfs:label "GraphRAG query session" ;
    prov:startedAtTime "2024-01-15T10:30:00Z" ;
    tg:query "What was the War on Terror?" .
```

### الكيان الخاص بالاسترجاع

```turtle
<retrieval-uri> a prov:Entity ;
    rdfs:label "Retrieved edges" ;
    prov:wasGeneratedBy <session-uri> ;
    tg:edgeCount 50 .
```

### الكيان المحدد

```turtle
<selection-uri> a prov:Entity ;
    rdfs:label "Selected edges" ;
    prov:wasDerivedFrom <retrieval-uri> ;
    tg:selectedEdge <edge-sel-0> ;
    tg:selectedEdge <edge-sel-1> .

<edge-sel-0> tg:edge << <s> <p> <o> >> ;
    tg:reasoning "This edge establishes the key relationship..." .
```

### إجابة الكيان

```turtle
<answer-uri> a prov:Entity ;
    rdfs:label "GraphRAG answer" ;
    prov:wasDerivedFrom <selection-uri> ;
    tg:document <urn:trustgraph:answer:{uuid}> .
```

يشير الرمز `tg:document` إلى الإجابة المخزنة في خدمة أمين المكتبة.

## ثوابت مساحة الاسم

معرفة في `trustgraph-base/trustgraph/provenance/namespaces.py`:

| الثابت | عنوان URI |
|----------|-----|
| `TG_QUERY` | `https://trustgraph.ai/ns/query` |
| `TG_EDGE_COUNT` | `https://trustgraph.ai/ns/edgeCount` |
| `TG_SELECTED_EDGE` | `https://trustgraph.ai/ns/selectedEdge` |
| `TG_EDGE` | `https://trustgraph.ai/ns/edge` |
| `TG_REASONING` | `https://trustgraph.ai/ns/reasoning` |
| `TG_CONTENT` | `https://trustgraph.ai/ns/content` |
| `TG_DOCUMENT` | `https://trustgraph.ai/ns/document` |

## مخطط GraphRagResponse

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

### أنواع الرسائل

| نوع الرسالة | الغرض |
|--------------|---------|
| `chunk` | نص الاستجابة (متدفق أو نهائي) |
| `explain` | حدث قابل للتفسير مع مرجع IRI |

### دورة حياة الجلسة

1. رسائل `explain` متعددة (جلسة، استرجاع، اختيار، إجابة)
2. رسائل `chunk` متعددة (استجابة متدفقة)
3. رسالة `chunk` نهائية مع `end_of_session=True`

## تنسيق اختيار الحافة

يقوم نموذج اللغة الكبيرة بإرجاع JSONL مع الحواف المحددة:

```jsonl
{"id": "edge-hash-1", "reasoning": "This edge shows the key relationship..."}
{"id": "edge-hash-2", "reasoning": "Provides supporting evidence..."}
```

الرمز `id` هو تجزئة لـ `(labeled_s, labeled_p, labeled_o)` تم حسابه بواسطة `edge_id()`.

## الحفاظ على عنوان URI

### المشكلة

يعرض GraphRAG تسميات قابلة للقراءة للبشر لنظام LLM، ولكن الشفافية تتطلب عناوين URI أصلية لتتبع الأصل.

### الحل

`get_labelgraph()` يُرجع كلاً من:
`labeled_edges`: قائمة بـ `(label_s, label_p, label_o)` لنظام LLM
`uri_map`: قاموس يربط بين `edge_id(labels)` و `(uri_s, uri_p, uri_o)`

عند تخزين بيانات الشفافية، تُستخدم عناوين URI من `uri_map`.

## تتبع الأصل

### من الحافة إلى المصدر

يمكن تتبع الحواف المحددة إلى المستندات المصدر:

1. الاستعلام عن الرسم البياني الفرعي الذي يحتوي عليها: `?subgraph tg:contains <<s p o>>`
2. تتبع سلسلة `prov:wasDerivedFrom` إلى المستند الجذر
3. كل خطوة في السلسلة: جزء → صفحة → مستند

### دعم ثلاثيات Cassandra المقتبسة

يدعم خدمة استعلام Cassandra مطابقة ثلاثيات مقتبسة:

```python
# In get_term_value():
elif term.type == TRIPLE:
    return serialize_triple(term.triple)
```

هذا يتيح إجراء استعلامات مثل:
```
?subgraph tg:contains <<http://example.org/s http://example.org/p "value">>
```

## استخدام واجهة سطر الأوامر

```bash
tg-invoke-graph-rag --explainable -q "What was the War on Terror?"
```

### تنسيق الإخراج

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

### الميزات

أحداث تفسيرية في الوقت الفعلي أثناء الاستعلام.
حل التسميات للمكونات الطرفية عبر `rdfs:label`.
تتبع سلسلة المصدر عبر `prov:wasDerivedFrom`.
تخزين مؤقت للتسميات لتجنب الاستعلامات المتكررة.

## الملفات المنفذة

| الملف | الغرض |
|------|---------|
| `trustgraph-base/trustgraph/provenance/uris.py` | مولدات URI |
| `trustgraph-base/trustgraph/provenance/namespaces.py` | ثوابت مساحة الاسم RDF |
| `trustgraph-base/trustgraph/provenance/triples.py` | أدوات بناء الثلاثيات |
| `trustgraph-base/trustgraph/schema/services/retrieval.py` | مخطط GraphRagResponse |
| `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py` | GraphRAG الأساسي مع الحفاظ على URI |
| `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` | خدمة مع تكامل أمين المكتبة |
| `trustgraph-flow/trustgraph/query/triples/cassandra/service.py` | دعم الاستعلام عن الثلاثيات المقتبسة |
| `trustgraph-cli/trustgraph/cli/invoke_graph_rag.py` | واجهة سطر أوامر مع عرض التفسير |

## المراجع

PROV-O (علم الوجود W3C): https://www.w3.org/TR/prov-o/
RDF-star: https://w3c.github.io/rdf-star/
علم الوجود في وقت الاستخراج: `docs/tech-specs/extraction-time-provenance.md`
