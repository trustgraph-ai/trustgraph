---
layout: default
title: "مواصفات سطر الأوامر لـ 'Explainability CLI'"
parent: "Arabic (Beta)"
---

# مواصفات سطر الأوامر لـ "Explainability CLI"

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## الحالة

مُقترح

## نظرة عامة

تصف هذه المواصفة أدوات سطر الأوامر لتصحيح الأخطاء واستكشاف بيانات الشرح في TrustGraph. تسمح هذه الأدوات للمستخدمين بتتبع كيفية استخلاص الإجابات وتصحيح سلسلة الأصل من الحواف إلى المستندات المصدر.

ثلاث أدوات سطر أوامر:

1. **`tg-show-document-hierarchy`** - عرض تسلسل المستند → الصفحة → الجزء → الحافة
2. **`tg-list-explain-traces`** - سرد جميع جلسات GraphRAG مع الأسئلة
3. **`tg-show-explain-trace`** - عرض مسار الشرح الكامل لجلسة

## الأهداف

- **تصحيح الأخطاء**: تمكين المطورين من فحص نتائج معالجة المستندات
- **قابلية التدقيق**: تتبع أي حقيقة مستخرجة إلى مستندها المصدر
- **الشفافية**: إظهار بالضبط كيف اشتق GraphRAG إجابة
- **سهولة الاستخدام**: واجهة سطر أوامر بسيطة مع قيم افتراضية معقولة

## الخلفية

يحتوي TrustGraph على نظامين لتعقب:

1. **تعقب وقت الاستخراج** (انظر `extraction-time-provenance.md`): يسجل علاقات المستند → الصفحة → الجزء → الحافة أثناء الاستيعاب. يتم تخزينها في رسم بياني يسمى `urn:graph:source` باستخدام `prov:wasDerivedFrom`.

2. **شرح قابل للتفسير في وقت الاستعلام** (انظر `query-time-explainability.md`): يسجل سلسلة السؤال → الاستكشاف → التركيز → التجميع أثناء استعلامات GraphRAG. يتم تخزينها في رسم بياني يسمى `urn:graph:retrieval`.

القيود الحالية:
- لا توجد طريقة سهلة لتصور تسلسل المستند بعد المعالجة
- يجب الاستعلام يدويًا عن المثلثات لعرض بيانات الشرح
- لا يوجد عرض موحد لجلسة GraphRAG

## التصميم الفني

### الأداة 1: tg-show-document-hierarchy

**الغرض**: إعطاء معرف المستند، والتحرك وعرض جميع الكيانات المشتقة.

**الاستخدام**:
```bash
tg-show-document-hierarchy "urn:trustgraph:doc:abc123"
tg-show-document-hierarchy --show-content --max-content 500 "urn:trustgraph:doc:abc123"
```

**الوسائط**:
| الوسيط | الوصف |
|---|---|
| `document_id` | URI للمستند (موضعي) |
| `-u/--api-url` | عنوان URL لـ Gateway |
| `-t/--token` | رمز المصادقة |
| `-U/--user` | معرف المستخدم |
| `-C/--collection` | المجموعة |
| `--show-content` | تضم محتوى Blob/المستند |
| `--max-content` | أقصى عدد من الأحرف في Blob (افتراضي: 200) |
| `--format` | الإخراج: `tree` (افتراضي)، `json` |

**التنفيذ**:
1. استعلام عن المثلثات: `?child prov:wasDerivedFrom <document_id>` في `urn:graph:source`
2. استعلام بشكل متكرر عن الأطفال لكل نتيجة
3. بناء بنية الشجرة: المستند → الصفحات → الأجزاء
4. إذا كان `--show-content`، فقم باسترداد المحتوى من واجهة برمجة التطبيقات الخاصة بالمكتبة
5. عرض كشجرة مسطحة أو JSON

**مثال على الإخراج**:
```
المستند: urn:trustgraph:doc:abc123
  العنوان: "Sample PDF"
  النوع: application/pdf

  └── الصفحة 1: urn:trustgraph:doc:abc123/p1
      ├── الجزء 0: urn:trustgraph:doc:abc123/p1/c0
          المحتوى: "The quick brown fox..." [مقتطف]
      └── الجزء 1: urn:trustgraph:doc:abc123/p1/c1
          المحتوى: "Machine learning is..." [مقتطف]
```

### الأداة 2: tg-list-explain-traces

**الغرض**: سرد جميع جلسات GraphRAG (الأسئلة) في مجموعة.

**الاستخدام**:
```bash
tg-list-explain-traces
tg-list-explain-traces --limit 20 --format json
```

**الوسائط**:
| الوسيط | الوصف |
|---|---|
| `-u/--api-url` | عنوان URL لـ Gateway |
| `-t/--token` | رمز المصادقة |
| `-U/--user` | معرف المستخدم |
| `-C/--collection` | المجموعة |
| `--limit` | أقصى عدد من النتائج (افتراضي: 50) |
| `--format` | الإخراج: `table` (افتراضي)، `json` |

**التنفيذ**:
1. استعلام: `?session tg:query ?text` في `urn:graph:retrieval`
2. استعلام عن الطوابع الزمنية: `?session prov:startedAtTime ?time`
3. عرض كجدول

**مثال على الإخراج**:
```
معرف الجلسة                                 | السؤال                        | الوقت
----------------------------------------------|--------------------------------|---------------------
urn:trustgraph:question:abc123                | What was the War on Terror?    | 2024-01-15 10:30:00
urn:trustgraph:question:def456                | Who founded OpenAI?            | 2024-01-15 09:15:00
```

### الأداة 3: tg-show-explain-trace

**الغرض**: عرض مسار الشرح الكامل لجلسة GraphRAG.

**الاستخدام**:
```bash
tg-show-explain-trace "urn:trustgraph:question:abc123"
tg-show-explain-trace --max-answer 1000 --show-provenance "urn:trustgraph:question:abc123"
```

**الوسائط**:
| الوسيط | الوصف |
|---|---|
| `question_id` | معرف السؤال (موضعي) |
| `-u/--api-url` | عنوان URL لـ Gateway |
| `-t/--token` | رمز المصادقة |
| `-U/--user` | معرف المستخدم |
| `-C/--collection` | المجموعة |
| `--max-answer` | أقصى عدد من الأحرف للإجابة (افتراضي: 500) |
| `--show-provenance` | تتبع الحواف إلى المستندات المصدر |
| `--format` | الإخراج: `text` (افتراضي)، `json` |

**التنفيذ**:
1. الحصول على نص السؤال من البُعد `tg:query`
2. العثور على الاستكشاف: `?exp prov:wasGeneratedBy <question_id>`
3. العثور على التركيز: `?focus prov:wasDerivedFrom <exploration_id>`
4. الحصول على الحواف المحددة: `<focus_id> tg:selectedEdge ?edge`
5. لكل حافة، الحصول على `tg:edge` (سلسلة RDF) و `tg:reasoning`
6. العثور على التجميع: `?synth prov:wasDerivedFrom <focus_id>`
7. الحصول على الإجابة من `tg:document` عبر واجهة برمجة التطبيقات
8. إذا كان `--show-provenance`، فقم بتتبع الحواف إلى المستندات المصدر

**مثال على الإخراج**:
```
=== جلسة GraphRAG: urn:trustgraph:question:abc123 ===

السؤال: What was the War on Terror?
الوقت: 2024-01-15 10:30:00

الإجابة: [إجابة]

مسار الشرح:
- السؤال: What was the War on Terror?
  - استخراج: [ملف]
  - تجميع: [إطار عمل]
  - استجابة: [إجابة]
- السؤال: What was the War on Terror?
  - استخراج: [ملف]
  - تجميع: [إطار عمل]
  - استجابة: [إجابة]
```

## المراجع

- شرح قابل للتفسير: `docs/tech-specs/query-time-explainability.md`
- تتبع وقت الاستخراج: `docs/tech-specs/extraction-time-provenance.md`
- مثال سطر الأوامر: `trustgraph-cli/trustgraph/cli/invoke_graph_rag.py`
