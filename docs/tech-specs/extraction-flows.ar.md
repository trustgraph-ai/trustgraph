---
layout: default
title: "تدفقات الاستخراج"
parent: "Arabic (Beta)"
---

# تدفقات الاستخراج

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

يصف هذا المستند كيفية تدفق البيانات عبر مسار الاستخراج الخاص بـ TrustGraph، بدءًا من تقديم المستندات وصولًا إلى تخزينها في مستودعات المعرفة.

## نظرة عامة

```
┌──────────┐     ┌─────────────┐     ┌─────────┐     ┌────────────────────┐
│ Librarian│────▶│ PDF Decoder │────▶│ Chunker │────▶│ Knowledge          │
│          │     │ (PDF only)  │     │         │     │ Extraction         │
│          │────────────────────────▶│         │     │                    │
└──────────┘     └─────────────┘     └─────────┘     └────────────────────┘
                                          │                    │
                                          │                    ├──▶ Triples
                                          │                    ├──▶ Entity Contexts
                                          │                    └──▶ Rows
                                          │
                                          └──▶ Document Embeddings
```

## تخزين المحتوى

### تخزين الكائنات (S3/Minio)

يتم تخزين محتوى المستندات في تخزين الكائنات المتوافق مع S3:
تنسيق المسار: `doc/{object_id}` حيث object_id هو معرف فريد عالمي (UUID)
يتم تخزين جميع أنواع المستندات هنا: المستندات المصدر، الصفحات، الأجزاء

### تخزين البيانات الوصفية (Cassandra)

يتم تخزين البيانات الوصفية للمستندات في Cassandra وتشمل:
معرف المستند، العنوان، النوع (نوع MIME)
مرجع إلى تخزين الكائنات `object_id`
مرجع إلى المستندات الفرعية (الصفحات، الأجزاء) `parent_id`
`document_type`: "source"، "page"، "chunk"، "answer"

### عتبة التضمين مقابل التدفق

نقل المحتوى يستخدم استراتيجية تعتمد على الحجم:
**أقل من 2 ميجابايت**: يتم تضمين المحتوى مباشرة في الرسالة (مشفر بـ base64).
**أكبر من أو يساوي 2 ميجابايت**: يتم إرسال `document_id` فقط؛ يقوم المعالج باسترداد البيانات عبر واجهة برمجة التطبيقات الخاصة بالمكتبة.

## المرحلة الأولى: تقديم المستند (المكتبة)

### نقطة الدخول

تدخل المستندات إلى النظام عبر عملية `add-document` الخاصة بالمكتبة:
1. يتم تحميل المحتوى إلى مساحة تخزين الكائنات.
2. يتم إنشاء سجل بيانات وصفية في Cassandra.
3. يتم إرجاع معرف المستند.

### بدء عملية الاستخراج

عملية `add-processing` تبدأ عملية الاستخراج:
تحدد `document_id`، و `flow` (معرف المسار)، و `collection` (مخزن الهدف).
تقوم عملية `load_document()` الخاصة بالمكتبة باسترداد المحتوى ونشره في قائمة انتظار الإدخال الخاصة بالتدفق.

### المخطط: المستند

```
Document
├── metadata: Metadata
│   ├── id: str              # Document identifier
│   ├── user: str            # Tenant/user ID
│   ├── collection: str      # Target collection
│   └── metadata: list[Triple]  # (largely unused, historical)
├── data: bytes              # PDF content (base64, if inline)
└── document_id: str         # Librarian reference (if streaming)
```

**التوجيه:** بناءً على الحقل `kind`:
`application/pdf` → قائمة انتظار `document-load` → وحدة فك ترميز PDF
`text/plain` → قائمة انتظار `text-load` → وحدة تقسيم

## المرحلة الثانية: وحدة فك ترميز PDF

تحويل مستندات PDF إلى صفحات نصية.

### العملية

1. استرجاع المحتوى (مضمن في `data` أو عبر `document_id` من أمين المكتبة)
2. استخراج الصفحات باستخدام PyPDF
3. لكل صفحة:
   حفظ كـ مستند فرعي في أمين المكتبة (`{doc_id}/p{page_num}`)
   إرسال ثلاثيات المصدر (الصفحة مشتقة من المستند)
   توجيه إلى وحدة التقسيم

### المخطط: TextDocument

```
TextDocument
├── metadata: Metadata
│   ├── id: str              # Page URI (e.g., https://trustgraph.ai/doc/xxx/p1)
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]
├── text: bytes              # Page text content (if inline)
└── document_id: str         # Librarian reference (e.g., "doc123/p1")
```

## المرحلة الثالثة: تقسيم النص إلى أجزاء

يقسم النص إلى أجزاء عند الحجم المحدد.

### المعلمات (قابلة للتكوين من خلال التدفق)

`chunk_size`: الحجم المستهدف للجزء الواحد بالأحرف (الافتراضي: 2000)
`chunk_overlap`: التداخل بين الأجزاء (الافتراضي: 100)

### العملية

1. استرجاع محتوى النص (مباشرة أو عبر أمين المكتبة)
2. التقسيم باستخدام مقسم الأحرف التكراري
3. لكل جزء:
   حفظ كوثيقة فرعية في أمين المكتبة (`{parent_id}/c{index}`)
   إرسال بيانات المصدر (الجزء مشتق من صفحة/مستند)
   توجيه إلى معالجات الاستخراج

### المخطط: جزء

```
Chunk
├── metadata: Metadata
│   ├── id: str              # Chunk URI
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]
├── chunk: bytes             # Chunk text content
└── document_id: str         # Librarian chunk ID (e.g., "doc123/p1/c3")
```

### التسلسل الهرمي لمعرف المستند

تقوم المستندات الفرعية بتشفير أصلها في المعرف:
المصدر: `doc123`
الصفحة: `doc123/p5`
جزء من الصفحة: `doc123/p5/c2`
جزء من النص: `doc123/c2`

## المرحلة 4: استخراج المعرفة

تتوفر أنماط استخراج متعددة، يتم اختيارها بواسطة إعدادات التدفق.

### النمط أ: GraphRAG الأساسي

معالجتان متوازيتان:

**kg-extract-definitions**
المدخلات: جزء
المخرجات: ثلاثيات (تعريفات الكيانات)، سياقات الكيانات
يستخرج: تسميات الكيانات، التعريفات

**kg-extract-relationships**
المدخلات: جزء
المخرجات: ثلاثيات (علاقات)، سياقات الكيانات
يستخرج: علاقات الفاعل-الفعل-المفعول

### النمط ب: مدفوع بالدلالات (kg-extract-ontology)

المدخلات: جزء
المخرجات: ثلاثيات، سياقات الكيانات
يستخدم دلالات مُكوّنة لتوجيه الاستخراج

### النمط ج: قائم على الوكيل (kg-extract-agent)

المدخلات: جزء
المخرجات: ثلاثيات، سياقات الكيانات
يستخدم إطار عمل الوكيل للاستخراج

### النمط د: استخراج الصفوف (kg-extract-rows)

المدخلات: جزء
المخرجات: صفوف (بيانات منظمة، وليست ثلاثيات)
يستخدم تعريف المخطط لاستخراج سجلات منظمة

### المخطط: ثلاثيات

```
Triples
├── metadata: Metadata
│   ├── id: str
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]  # (set to [] by extractors)
└── triples: list[Triple]
    └── Triple
        ├── s: Term              # Subject
        ├── p: Term              # Predicate
        ├── o: Term              # Object
        └── g: str | None        # Named graph
```

### المخطط: سياقات الكيانات

```
EntityContexts
├── metadata: Metadata
└── entities: list[EntityContext]
    └── EntityContext
        ├── entity: Term         # Entity identifier (IRI)
        ├── context: str         # Textual description for embedding
        └── chunk_id: str        # Source chunk ID (provenance)
```

### المخطط: الصفوف

```
Rows
├── metadata: Metadata
├── row_schema: RowSchema
│   ├── name: str
│   ├── description: str
│   └── fields: list[Field]
└── rows: list[dict[str, str]]   # Extracted records
```

## المرحلة الخامسة: توليد التضمينات

### تضمينات الرسم البياني

تحويل سياقات الكيانات إلى تضمينات متجهة.

**العملية:**
1. استقبال سياقات الكيانات.
2. استدعاء خدمة التضمينات مع نص السياق.
3. إخراج تضمينات الرسم البياني (ت mapping بين الكيان والمتجه).

**النموذج: تضمينات الرسم البياني**

```
GraphEmbeddings
├── metadata: Metadata
└── entities: list[EntityEmbeddings]
    └── EntityEmbeddings
        ├── entity: Term         # Entity identifier
        ├── vector: list[float]  # Embedding vector
        └── chunk_id: str        # Source chunk (provenance)
```

### تضمينات المستندات

يحول النص المقسم مباشرةً إلى تضمينات متجهة.

**العملية:**
1. استقبال الجزء
2. استدعاء خدمة التضمينات باستخدام نص الجزء
3. إخراج تضمينات المستندات

**التركيب: تضمينات المستندات**

```
DocumentEmbeddings
├── metadata: Metadata
└── chunks: list[ChunkEmbeddings]
    └── ChunkEmbeddings
        ├── chunk_id: str        # Chunk identifier
        └── vector: list[float]  # Embedding vector
```

### تضمينات الصفوف

تحويل حقول فهرس الصف إلى تضمينات متجهة.

**العملية:**
1. استقبال الصفوف
2. تضمين حقول الفهرس المحددة
3. الإخراج إلى مخزن المتجهات الصفية

## المرحلة 6: التخزين

### مخزن ثلاثي

يستقبل: ثلاثيات
التخزين: Cassandra (جداول تركز على الكيانات)
الرسوم البيانية المسماة تفصل المعرفة الأساسية عن المصادر:
  `""` (افتراضي): حقائق المعرفة الأساسية
  `urn:graph:source`: تتبع المصادر
  `urn:graph:retrieval`: إمكانية الشرح في وقت الاستعلام

### مخزن المتجهات (تضمينات الرسم البياني)

يستقبل: تضمينات الرسم البياني
التخزين: Qdrant، Milvus، أو Pinecone
مفهرس بواسطة: IRI الكيان
البيانات الوصفية: chunk_id لتتبع المصادر

### مخزن المتجهات (تضمينات المستندات)

يستقبل: تضمينات المستندات
التخزين: Qdrant، Milvus، أو Pinecone
مفهرس بواسطة: chunk_id

### مخزن الصفوف

يستقبل: صفوف
التخزين: Cassandra
هيكل الجدول الموجه بالمخطط

### مخزن المتجهات الصفية

يستقبل: تضمينات الصفوف
التخزين: قاعدة بيانات المتجهات
مفهرس بواسطة: حقول فهرس الصف

## تحليل حقول البيانات الوصفية

### الحقول المستخدمة بنشاط

| الحقل | الاستخدام |
|-------|-------|
| `metadata.id` | معرف المستند/الكتلة، التسجيل، تتبع المصادر |
| `metadata.user` | تعدد المستأجرين، توجيه التخزين |
| `metadata.collection` | اختيار المجموعة المستهدفة |
| `document_id` | مرجع أمين المكتبة، ربط تتبع المصادر |
| `chunk_id` | تتبع المصادر عبر مسار العمل |

<<<<<<< HEAD
### الحقول التي قد تكون زائدة عن الحاجة

| الحقل | الحالة |
|-------|--------|
| `metadata.metadata` | يتم تعيينه على `[]` بواسطة جميع المستخرجات؛ يتم التعامل مع بيانات وصفية على مستوى المستند الآن بواسطة أمين المكتبة في وقت الإرسال |
=======
### الحقول التي تمت إزالتها

| الحقل | الحالة |
|-------|--------|
| `metadata.metadata` | تمت إزالته من الفئة `Metadata`. يتم الآن إرسال ثلاثيات البيانات الوصفية على مستوى المستند مباشرةً بواسطة أمين المكتبة إلى مخزن الثلاثيات في وقت الإرسال، ولا يتم نقلها عبر مسار العمل. |
>>>>>>> e3bcbf73 (قائمة البيانات الوصفية (الثلاثيات) في فئة مسار العمل Metadata)

### نمط حقول البايت

جميع حقول المحتوى (`data`، `text`، `chunk`) هي `bytes` ولكن يتم فك ترميزها على الفور إلى سلاسل UTF-8 بواسطة جميع المعالجات. لا يستخدم أي معالج بايت خام.

## تكوين التدفق

يتم تعريف التدفقات خارجيًا وتقديمها إلى أمين المكتبة عبر خدمة التكوين. يحدد كل تدفق:

قوائم انتظار الإدخال (`text-load`، `document-load`)
سلسلة المعالجات
المعلمات (حجم الكتلة، طريقة الاستخراج، إلخ.)

أمثلة على أنماط التدفق:
`pdf-graphrag`: PDF → Decoder → Chunker → Definitions + Relationships → Embeddings
`text-graphrag`: Text → Chunker → Definitions + Relationships → Embeddings
`pdf-ontology`: PDF → Decoder → Chunker → Ontology Extraction → Embeddings
`text-rows`: Text → Chunker → Row Extraction → Row Store
