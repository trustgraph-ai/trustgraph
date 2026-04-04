# اقتراح إعادة هيكلة دليل المخطط

## المشاكل الحالية

1.  **هيكل مسطح** - وجود جميع المخططات في مجلد واحد يجعل من الصعب فهم العلاقات
2.  **مزيج من المعايير** - أنواع أساسية، كائنات مجال، وعقود واجهة برمجة تطبيقات كلها مدمجة معًا
3.  **أسماء غير واضحة** - الملفات مثل "object.py"، "types.py"، "topic.py" لا تشير بوضوح إلى الغرض منها
4.  **لا يوجد تباين واضح** - من الصعب معرفة ما يعتمد على ماذا

## الهيكل المقترح

```
trustgraph-base/trustgraph/schema/
├── __init__.py
├── core/              # أنواع أساسية أولية مستخدمة في كل مكان
│   ├── __init__.py
│   ├── primitives.py  # Error, Value, Triple, Field, RowSchema
│   ├── metadata.py    # سجل البيانات الوصفية
│   └── topic.py       # أدوات الموضوع
│
├── knowledge/         # نماذج مجال المعرفة واستخراجها
│   ├── __init__.py
│   ├── graph.py       # EntityContext, EntityEmbeddings, Triples
│   ├── document.py    # Document, TextDocument, Chunk
│   ├── knowledge.py   # أنواع استخراج المعرفة
│   ├── embeddings.py  # جميع أنواع الاستعلامات المتعلقة بالاستعلام (تم نقلها من ملفات متعددة)
│   └── nlp.py         # أنواع Definition, Topic, Relationship, Fact
│
└── services/          # عقود طلب/استجابة الخدمة
    ├── __init__.py
    ├── llm.py         # TextCompletion, Embeddings, Tool requests/responses
    ├── retrieval.py   # GraphRAG, DocumentRAG queries/responses
    ├── query.py       # GraphEmbeddingsRequest/Response, DocumentEmbeddingsRequest/Response
    ├── agent.py       # Agent requests/responses
    ├── flow.py        # Flow requests/responses
    ├── prompt.py      # طلبات/استجابات خدمة Prompt
    ├── config.py      # خدمة التكوين
    ├── library.py     # خدمة المكتبة
    └── lookup.py      # خدمة البحث
```

## التغييرات الرئيسية

1.  **تنظيم هرمي** - فصل واضح بين الأنواع الأساسية، نماذج المعرفة، وعقود الخدمة
2.  **أسماء أفضل**:
    -   `types.py` → `core/primitives.py` (الغرض أكثر وضوحًا)
    -   `object.py` → تقسيم بين الملفات المناسبة بناءً على المحتوى الفعلي
    -   `documents.py` → `knowledge/document.py` (فردي، متسق)
    -   `models.py` → `services/llm.py` (نوع النماذج أكثر وضوحًا)
    -   `prompt.py` → تقسيم: أجزاء الخدمة إلى `services/prompt.py`، أنواع البيانات إلى `knowledge/nlp.py`

3.  **تجميع منطقي**:
    -   جميع أنواع الاستعلامات مجمعة في `knowledge/embeddings.py`
    -   جميع العقود المتعلقة بالخدمة LLM في `services/llm.py`
    -   فصل واضح لزوجات الطلب/الاستجابة في دليل الخدمة
    -   تجميع أنواع استخراج المعرفة مع نماذج المعرفة الأخرى

4.  **وضوح الاعتماد**:
    -   الأنواع الأساسية ليس لها تبعيات
    -   تعتمد نماذج المعرفة فقط على الأساس
    -   يمكن أن تعتمد عقود الخدمة على كل من الأساس ونماذج المعرفة

## فوائد الهجرة

1.  **سهولة التنقل** - يمكن للمطورين العثور بسرعة على ما يحتاجون إليه
2.  **تحسين الوحدات** - حدود واضحة بين مختلف المعايير
3.  **استيراد أبسط** - مسارات استيراد أكثر بديهية
4.  **قابلية التوسع** - من السهل إضافة أنواع معرف أو خدمات جديدة دون تضييق

## أمثلة على تغييرات الاستيراد

```python
# قبل
from trustgraph.schema import Error, Triple, GraphEmbeddings, TextCompletionRequest

# بعد
from trustgraph.schema.core import Error, Triple
from trustgraph.schema.knowledge import GraphEmbeddings
from trustgraph.schema.services import TextCompletionRequest
```

## ملاحظات التنفيذ

1.  الحفاظ على التوافق مع الإصدارات السابقة عن طريق الحفاظ على الاستيرادات في `__init__.py` الجذر
2.  نقل الملفات تدريجيًا، مع تحديث الاستيرادات حسب الحاجة
3.  ضع في اعتبارك إضافة `legacy.py` الذي يستورد كل شيء لفاصل زمني الانتقال
4.  تحديث الوثائق لتعكس الهيكل الجديد

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"id": "1", "content": "Examination of the current schema directory structure", "status": "completed", "priority": "high"}, {"id": "2", "content": "Analyze schema files and their purposes", "status": "completed", "priority": "high"}, {"id": "3", "content": "Propose improved naming and structure", "status": "completed", "priority": "high"}]