# مواصفات فنية لدعم التدفق في RAG

## نظرة عامة

تصف هذه المواصفات إضافة دعم التدفق إلى خدمات GraphRAG و DocumentRAG، مما يمكّن من الحصول على استجابات على شكل أجزاء (token-by-token) في الوقت الفعلي للاستعلامات المتعلقة باسترجاع المعرفة ورؤوس المستندات. هذا يوسع البنية المعمارية الحالية للتدفق، والتي تم تنفيذها بالفعل لخدمات إكمال النص، والتعليمات البرمجية، ووكلاء LLM.

## الأهداف

- **تجربة تدفق متسقة**: توفير تجربة تدفق متسقة عبر جميع خدمات TrustGraph.
- **تغييرات واجهة برمجة تطبيقات (API) قليلة**: إضافة دعم التدفق باستخدام علامة واحدة (`streaming`)، وفقًا للأنماط المتبعة.
- **التوافق مع الإصدارات السابقة**: الحفاظ على سلوك غير تدفق بشكل افتراضي.
- **استخدام البنية التحتية الحالية**: الاستفادة من تدفق PromptClient المطبق بالفعل.
- **دعم البوابة**: تمكين التدفق من خلال بوابة websocket للتطبيقات العميلة.

## الخلفية

خدمات التدفق الحالية:
- **خدمة إكمال النص للـ LLM**: المرحلة 1 - التدفق من مزودي LLM.
- **خدمة التعليمات البرمجية**: المرحلة 2 - التدفق من خلال قوالب التعليمات البرمجية.
- **خدمة الوكيل**: المراحل 3-4 - استجابات ReAct مع أجزاء فكرية/ملاحظات/إجابات متزايدة.

قيود الحالية لخدمات RAG:
- GraphRAG و DocumentRAG تدعم فقط الاستجابات المتوقفة.
- يجب على المستخدمين الانتظار حتى استلام الرد الكامل من LLM قبل رؤية أي مخرجات.
- تجربة مستخدم (UX) سيئة للاستجابات الطويلة من استعلامات الرسم البياني المعرفي أو المستندات.
- تجربة غير متسقة مقارنة بـ خدمات TrustGraph الأخرى.

تستجيب هذه المواصفات لهذه الثغرات من خلال إضافة دعم التدفق إلى GraphRAG و DocumentRAG. من خلال تمكين الاستجابات على شكل أجزاء، يمكن لـ TrustGraph:
- توفير تجربة تدفق متسقة عبر جميع أنواع الاستعلام.
- تقليل التأخير المتوقع في استعلامات RAG.
- تمكين ملاحظات تقدم أفضل للاستعلامات الطويلة الأمد.
- دعم العرض في الوقت الفعلي في تطبيقات العملاء.

## التصميم الفني

### البنية

يستفيد تنفيذ التدفق في RAG من البنية التحتية الحالية:

1.  **تدفق PromptClient** (مطبق بالفعل)
    -   يستقبل `kg_prompt()` و `document_prompt()` بالفعل معلمات `streaming` و `chunk_callback`.
    -   تستدعي هذه `prompt()` داخليًا مع دعم التدفق.
    -   لا يلزم إجراء أي تغييرات على PromptClient.

    الوحدة: `trustgraph-base/trustgraph/base/prompt_client.py`

2.  **خدمة GraphRAG** (تحتاج إلى تمرير معلمة التدفق)
    -   إضافة معلمة `streaming` إلى طريقة `query()`.
    -   تمرير علامة التدفق والوظائف المرجعية إلى `prompt_client.kg_prompt()`.
    -   يجب أن يحتوي مخطط GraphRag على حقل `streaming`.

    الوحدات:
    -   `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py`
    -   `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` (المعالجة)
    -   `trustgraph-base/trustgraph/schema/graph_rag.py` (مخطط الطلب)
    -   `trustgraph-flow/trustgraph/gateway/dispatch/graph_rag.py` (البوابة)

3.  **خدمة DocumentRAG** (تحتاج إلى تمرير معلمة التدفق)
    -   إضافة معلمة `streaming` إلى طريقة `query()`.
    -   تمرير علامة التدفق والوظائف المرجعية إلى `prompt_client.document_prompt()`.
    -   يجب أن يحتوي مخطط DocumentRag على حقل `streaming`.

    الوحدات:
    -   `trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py`
    -   `trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` (المعالجة)
    -   `trustgraph-base/trustgraph/schema/document_rag.py` (مخطط الطلب)
    -   `trustgraph-flow/trustgraph/gateway/dispatch/document_rag.py` (البوابة)

### تدفق البيانات

**غير تدفق (الحالي)**:
```
Client → Gateway → RAG Service → PromptClient.kg_prompt(streaming=False)
                                   ↓
                                Prompt Service → LLM
                                   ↓
                                رد كامل
                                   ↓
Client ← Gateway ← RAG Service ←  الرد
```

**تدفق (مقترح)**:
```
Client → Gateway → RAG Service → PromptClient.kg_prompt(streaming=True, chunk_callback=cb)
                                   ↓
                                Prompt Service → LLM (streaming)
                                   ↓
                                جزء → وظيفة مرجعية → رد RAG (جزء)
                                   ↓                       ↓
Client ← Gateway ← ────────────────────────────────── رد التدفق
```

### واجهات برمجة التطبيقات (APIs)

**تغييرات GraphRAG**:

1.  **GraphRag.query()** - إضافة معلمات التدفق
```python
async def query(
    self, query, user, collection,
    verbose=False, streaming=False, chunk_callback=None  # NEW
):
    # ... كود موجود ...

    if streaming and chunk_callback:
        resp = await self.prompt_client.kg_prompt(
            query, kg,
            streaming=True,
            chunk_callback=chunk_callback
        )
    else:
        resp = await self.prompt_client.kg_prompt(query, kg)

    return resp
```

2.  **مخطط GraphRagRequest** - إضافة حقل التدفق
```python
class GraphRagRequest(Record):
    query = String()
    user = String()
    collection = String()
    streaming = Boolean()  # NEW
```

3.  **مخطط GraphRagResponse** - إضافة حقول التدفق (اتبع نمط الوكيل)
```python
class GraphRagResponse(Record):
    response = String()
    metadata = dict
    # ... حقول أخرى ...
```

**تغييرات DocumentRAG**:
(نفس التغييرات الموضحة أعلاه)

### التغييرات في البوابة

(نفس التغييرات الموضحة أعلاه)

## خطة النقل

لا توجد حاجة لنقل:
- التدفق هو خيار، وتكون القيمة الافتراضية هي False.
- لا تزال العملاء الحالية تعمل بشكل طبيعي.
- يمكن للعملاء الجدد اختيار التدفق.

## الجدول الزمني

الوقت المقدر للتنفيذ: 4-6 ساعات
- المرحلة 1 (2 ساعات): دعم التدفق في GraphRAG
- المرحلة 2 (2 ساعات): دعم التدفق في DocumentRAG
- المرحلة 3 (1-2 ساعات): تحديثات البوابة وعلامات سطر الأوامر (CLI)
- الاختبار: تم تضمينه في كل مرحلة

## الأسئلة المفتوحة

- هل يجب إضافة دعم التدفق لخدمة NLP Query أيضًا؟
- هل نريد تدفق خطوات وسيطة (مثل "جاري استرداد الكيانات..."، "استعلام عن الرسم البياني") أم فقط مخرجات LLM؟
- هل يجب تضمين بيانات وصفية للجزء (مثل رقم الجزء، العدد الإجمالي المتوقع) في استجابات GraphRAG/DocumentRAG؟

## المراجع

- التنفيذ الحالي: `docs/tech-specs/streaming-llm-responses.md`
- تدفق PromptClient: `trustgraph-base/trustgraph/base/prompt_client.py`
- تدفق الوكيل: `trustgraph-flow/trustgraph/agent/react/agent_manager.py`