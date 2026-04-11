---
layout: default
title: "شرح عمل الوكيل: تسجيل المصدر"
parent: "Arabic (Beta)"
---

# شرح عمل الوكيل: تسجيل المصدر

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## نظرة عامة

أضف تسجيل المصدر إلى حلقة الوكيل في React حتى يمكن تتبع جلسات الوكيل وتصحيحها باستخدام نفس البنية التحتية للشرح كما هو الحال في GraphRAG.

**قرارات التصميم:**
الكتابة إلى `urn:graph:retrieval` (رسم بياني للشرح العام)
سلسلة اعتماد خطية في الوقت الحالي (تحليل N → تم اشتقاقه من → تحليل N-1)
الأدوات هي صناديق سوداء (تسجيل الإدخال/الإخراج فقط)
دعم الرسم البياني الموجه غير المتصل (DAG) مؤجل للتكرار المستقبلي

## أنواع الكيانات

يستخدم كل من GraphRAG والوكيل PROV-O كعلم الوجود الأساسي مع أنواع فرعية خاصة بـ TrustGraph:

### أنواع GraphRAG
| الكيان | نوع PROV-O | أنواع TG | الوصف |
|--------|-------------|----------|-------------|
| سؤال | `prov:Activity` | `tg:Question`, `tg:GraphRagQuestion` | استعلام المستخدم |
| استكشاف | `prov:Entity` | `tg:Exploration` | الحواف المستردة من الرسم البياني المعرفي |
| تركيز | `prov:Entity` | `tg:Focus` | الحواف المحددة مع الاستدلال |
| توليف | `prov:Entity` | `tg:Synthesis` | الإجابة النهائية |

### أنواع الوكيل
| الكيان | نوع PROV-O | أنواع TG | الوصف |
|--------|-------------|----------|-------------|
| سؤال | `prov:Activity` | `tg:Question`, `tg:AgentQuestion` | استعلام المستخدم |
| تحليل | `prov:Entity` | `tg:Analysis` | كل دورة تفكير/فعل/ملاحظة |
| استنتاج | `prov:Entity` | `tg:Conclusion` | الإجابة النهائية |

### أنواع RAG للوثائق
| الكيان | نوع PROV-O | أنواع TG | الوصف |
|--------|-------------|----------|-------------|
| سؤال | `prov:Activity` | `tg:Question`, `tg:DocRagQuestion` | استعلام المستخدم |
| استكشاف | `prov:Entity` | `tg:Exploration` | أجزاء مستردة من مستودع المستندات |
| توليف | `prov:Entity` | `tg:Synthesis` | الإجابة النهائية |

**ملاحظة:** يستخدم RAG للوثائق مجموعة فرعية من أنواع GraphRAG (لا توجد خطوة "تركيز" نظرًا لعدم وجود مرحلة اختيار/استدلال للحواف).

### أنواع فرعية للأسئلة

تشترك جميع كيانات "سؤال" في `tg:Question` كنوع أساسي ولكنها تحتوي على نوع فرعي محدد لتحديد آلية الاسترداد:

| النوع الفرعي | نمط URI | الآلية |
|---------|-------------|-----------|
| `tg:GraphRagQuestion` | `urn:trustgraph:question:{uuid}` | RAG للرسم البياني المعرفي |
| `tg:DocRagQuestion` | `urn:trustgraph:docrag:{uuid}` | RAG للوثائق/الأجزاء |
| `tg:AgentQuestion` | `urn:trustgraph:agent:{uuid}` | وكيل ReAct |

يتيح ذلك الاستعلام عن جميع الأسئلة عبر `tg:Question` مع التصفية حسب آلية معينة عبر النوع الفرعي.

## نموذج المصدر

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

### نموذج تتبع أصل المستندات (Document RAG Provenance Model)

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

## التغييرات المطلوبة

### 1. تغييرات المخطط

**الملف:** `trustgraph-base/trustgraph/schema/services/agent.py`

أضف الحقول `session_id` و `collection` إلى `AgentRequest`:
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

**الملف:** `trustgraph-base/trustgraph/messaging/translators/agent.py`

تحديث المترجم للتعامل مع `session_id` و `collection` في كل من `to_pulsar()` و `from_pulsar()`.

### 2. إضافة مُنتج الشفافية إلى خدمة الوكيل

**الملف:** `trustgraph-flow/trustgraph/agent/react/service.py`

تسجيل مُنتج "الشفافية" (بنفس النمط مثل GraphRAG):
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

### 3. توليد الثلاثيات المتعلقة بالأصل.

**الملف:** `trustgraph-base/trustgraph/provenance/agent.py`

إنشاء دوال مساعدة (مشابهة لدوال `question_triples` و `exploration_triples`، إلخ في GraphRAG):
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

### 4. تعريفات الأنواع

**الملف:** `trustgraph-base/trustgraph/provenance/namespaces.py`

أضف أنواع الكيانات الخاصة بالتفسير والعبارات الخاصة بالوكيل:
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

## الملفات التي تم تعديلها

| الملف | التغيير |
|------|--------|
| `trustgraph-base/trustgraph/schema/services/agent.py` | إضافة session_id و collection إلى AgentRequest |
| `trustgraph-base/trustgraph/messaging/translators/agent.py` | تحديث المترجم للحقول الجديدة |
| `trustgraph-base/trustgraph/provenance/namespaces.py` | إضافة أنواع الكيانات، وعبارات الوكيل، وأنواع Document RAG |
| `trustgraph-base/trustgraph/provenance/triples.py` | إضافة أنواع TG إلى أدوات بناء الثلاثيات GraphRAG، وإضافة أدوات بناء الثلاثيات Document RAG |
| `trustgraph-base/trustgraph/provenance/uris.py` | إضافة مولدات URI لـ Document RAG |
| `trustgraph-base/trustgraph/provenance/__init__.py` | تصدير الأنواع والعبارات الجديدة ووظائف Document RAG |
| `trustgraph-base/trustgraph/schema/services/retrieval.py` | إضافة explain_id و explain_graph إلى DocumentRagResponse |
| `trustgraph-base/trustgraph/messaging/translators/retrieval.py` | تحديث DocumentRagResponseTranslator للحقول الخاصة بالقدرة على الشرح |
| `trustgraph-flow/trustgraph/agent/react/service.py` | إضافة منطق الإنتاج والتسجيل الخاص بالقدرة على الشرح |
| `trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py` | إضافة استدعاء رد (callback) خاص بالقدرة على الشرح وإصدار ثلاثيات المصدر |
| `trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` | إضافة مُنتج القدرة على الشرح وربطه بالاستدعاء الردي |
| `trustgraph-cli/trustgraph/cli/show_explain_trace.py` | معالجة أنواع تتبع الوكيل |
| `trustgraph-cli/trustgraph/cli/list_explain_traces.py` | عرض جلسات الوكيل جنبًا إلى جنب مع GraphRAG |

## الملفات التي تم إنشاؤها

| الملف | الغرض |
|------|---------|
| `trustgraph-base/trustgraph/provenance/agent.py` | مولدات ثلاثيات خاصة بالوكيل |

## تحديثات واجهة سطر الأوامر (CLI)

**الكشف:** كل من GraphRAG والأسئلة الخاصة بالوكيل لهما نوع `tg:Question`. يتم التمييز بينهما بواسطة:
1. نمط URI: `urn:trustgraph:agent:` مقابل `urn:trustgraph:question:`
2. الكيانات المشتقة: `tg:Analysis` (الوكيل) مقابل `tg:Exploration` (GraphRAG)

**`list_explain_traces.py`:**
يعرض عمود النوع (الوكيل مقابل GraphRAG)

**`show_explain_trace.py`:**
يكتشف تلقائيًا نوع التتبع
يعرض عرض الوكيل: سؤال → خطوة(ات) تحليل → استنتاج

## التوافق مع الإصدارات السابقة

`session_id` افتراضيًا إلى `""` - تعمل الطلبات القديمة، ولكن لن تحتوي على معلومات المصدر |
`collection` افتراضيًا إلى `"default"` - حل بديل معقول |
تتعامل واجهة سطر الأوامر (CLI) بأمان مع كلا نوعي التتبع |

## التحقق

```bash
# Run an agent query
tg-invoke-agent -q "What is the capital of France?"

# List traces (should show agent sessions with Type column)
tg-list-explain-traces -U trustgraph -C default

# Show agent trace
tg-show-explain-trace "urn:trustgraph:agent:xxx"
```

## الأعمال المستقبلية (ليست جزءًا من هذا التعديل)

تبعيات الرسم البياني الموجه (عندما يعتمد التحليل N على نتائج تحليلات سابقة متعددة)
ربط المصادر الخاص بالأدوات (KnowledgeQuery ← تتبع GraphRAG الخاص به)
إرسال المصادر بشكل مستمر (إرسال البيانات أثناء العمل، وليس دفعة واحدة في النهاية)
