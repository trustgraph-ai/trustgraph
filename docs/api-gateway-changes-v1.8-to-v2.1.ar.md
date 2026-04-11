---
layout: default
title: "تغييرات في واجهة برمجة التطبيقات: v1.8 إلى v2.1"
parent: "Arabic (Beta)"
---

# تغييرات في واجهة برمجة التطبيقات: v1.8 إلى v2.1

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## ملخص

حصلت واجهة برمجة التطبيقات على مُسِير خدمات WebSocket الجديدة لإرسال استعلامات "التضمين"، ونقطة نهاية REST الجديدة للتدفق لمحتوى المستند، وتم إجراء تغيير كبير في تنسيق الكود من "القيمة" إلى "الحد". تم إعادة تسمية خدمة "الكائنات" إلى "الصفوف".

---

## مُسِير خدمات WebSocket الجديدة

هذه هي خدمات طلب/استجابة جديدة متاحة من خلال مُضاعِف WebSocket في `/api/v1/socket` (محدد على مستوى التدفق):

| مفتاح الخدمة | الوصف |
|---|---|
| `document-embeddings` | استعلام عن أجزاء المستند بناءً على التشابه النصي. يستخدم الطلب/الاستجابة مخططات `DocumentEmbeddingsRequest`/`DocumentEmbeddingsResponse`. |
| `row-embeddings` | استعلام عن صفوف البيانات المنظمة بناءً على التشابه النصي في الحقول المفهرسة. يستخدم الطلب/الاستجابة مخططات `RowEmbeddingsRequest`/`RowEmbeddingsResponse`. |

تضاف إلى مُسِير "graph-embeddings" الحالي (الذي كان موجودًا بالفعل في v1.8 ولكنه قد تم تحديثه).

### قائمة كاملة بمُسِير خدمات تدفق WebSocket (v2.1)

خدمات طلب/استجابة (عبر `/api/v1/flow/{flow}/service/{kind}` أو مُضاعِف WebSocket):

- `agent`, `text-completion`, `prompt`, `mcp-tool`
- `graph-rag`, `document-rag`
- `embeddings`, `graph-embeddings`, `document-embeddings`
- `triples`, `rows`, `nlp-query`, `structured-query`, `structured-diag`
- `row-embeddings`

---

## نقطة نهاية REST الجديدة

| الطريقة | المسار | الوصف |
|---|---|---|
| `GET` | `/api/v1/document-stream` | تدفق محتوى المستند من المكتبة كبيانات خام. معلمات الاستعلام: `user` (مطلوب)، `document-id` (مطلوب)، `chunk-size` (اختياري، القيمة الافتراضية 1 ميجابايت). يُرجع محتوى المستند بتنسيق نقل متقطع، مع فك ترميزه من base64 داخليًا. |

---

## إعادة تسمية الخدمة: "objects" إلى "rows"

| v1.8 | v2.1 | الملاحظات |
|---|---|---|
| `objects_query.py` / `ObjectsQueryRequestor` | `rows_query.py` / `RowsQueryRequestor` | تغير المخطط من `ObjectsQueryRequest`/`ObjectsQueryResponse` إلى `RowsQueryRequest`/`RowsQueryResponse`. |
| `objects_import.py` / `ObjectsImport` | `rows_import.py` / `RowsImport` | مُسِير الاستيراد للبيانات المنظمة. |

تغير مفتاح خدمة WebSocket من `"objects"` إلى `"rows"`, وتغير مفتاح مُسِير الاستيراد بشكل مشابه من `"objects"` إلى `"rows"`.

---

## تغيير تنسيق الكود: Value إلى Term

تم إعادة كتابة طبقة التسلسل (serialize.py) لاستخدام النوع الجديد "Term" بدلاً من النوع القديم "Value".

### التنسيق القديم (v1.8 — Value)

```json
{"v": "http://example.org/entity", "e": true}
```

- `v`: القيمة (سلسلة)
- `e`: علامة منطقية تشير إلى ما إذا كانت القيمة عبارة عن URI

### التنسيق الجديد (v2.1 — Term)

IRIs:
```json
{"t": "i", "i": "http://example.org/entity"}
```

Literals:
```json
{"t": "l", "v": "some text", "d": "datatype-uri", "l": "en"}
```

Quoted triples (RDF-star):
```json
{"t": "r", "r": {"s": {...}, "p": {...}, "o": {...}}}
```

- `t`: مُحدد النوع — `"i"` (URI)، `"l"` (حرف)، `"r"` (ثلاثي مُقتبس)، `"b"` (عقدة فارغة)
- الآن يتم تفويض التسلسل إلى `TermTranslator` و `TripleTranslator` من `trustgraph.messaging.translators.primitives`

### تغييرات التسلسل الأخرى

| الحقل | v1.8 | v2.1 |
|---|---|---|
| البيانات الوصفية | `metadata.metadata` (البريد الفرعي) | `metadata.root` (قيمة بسيطة) |
| كيان تضمينات الرسم البياني | `entity.vectors` (مجموع) | `entity.vector` (مفرد) |
| جزء تضمين المستند | `chunk.vectors` + `chunk.chunk` (النص) | `chunk.vector` + `chunk.chunk_id` (مرجع المعرّف) |

---

## تغييرات في الكسر

- **تنسيق الكود Value إلى Term**: يجب على جميع العملاء الذين يرسلون/يستقبلون ثلاثيات أو سياقات الكائنات أو التضمينات من خلال واجهة برمجة التطبيقات تحديثها إلى التنسيق الجديد Term.
- **إعادة تسمية "objects" إلى "rows"**: تغير مفتاح خدمة WebSocket ومفتاح الاستيراد.
- **تغيير حقل البيانات الوصفية**: تم استبدال `metadata.metadata` (مجموعة فرعية مُسلسلة) بـ `metadata.root` (قيمة بسيطة).
- **تغييرات حقول التضمين**: أصبح `vectors` (مجموع) هو `vector` (مفرد)، وتستخدم تضمينات المستند الآن `chunk_id` بدلاً من النص المضمن.
- **نقطة نهاية جديدة `/api/v1/document-stream`**: إضافية، وليست مُفسرة.
