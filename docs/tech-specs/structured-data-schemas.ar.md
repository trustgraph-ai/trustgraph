# مخطط بيانات البنية: تغييرات مخطط Pulsar

## نظرة عامة

استنادًا إلى مواصفات `STRUCTURED_DATA.md`، تقترح هذه الوثيقة الإضافات والتعديلات اللازمة على مخطط Pulsar لدعم قدرات البيانات المنظمة في TrustGraph.

## تغييرات مخطط مطلوبة

### 1. تحسينات مخطط أساسية

#### تعريف الحقل المحسّن
تحتاج الفئة الحالية `Field` في `core/primitives.py` إلى خصائص إضافية:

```python
class Field(Record):
    name = String()
    type = String()  # int, string, long, bool, float, double, timestamp
    size = Integer()
    primary = Boolean()
    description = String()
    # حقول جديدة:
    required = Boolean()  # ما إذا كان الحقل مطلوبًا
    enum_values = Array(String())  # للحقول من نوع Enum
    indexed = Boolean()  # ما إذا كان يجب فهرسة الحقل
```

### 2. مخططات معرفة جديدة

#### 2.1 إرسال بيانات منظمة
ملف جديد: `knowledge/structured.py`

```python
from pulsar.schema import Record, String, Bytes, Map
from ..core.metadata import Metadata

class StructuredDataSubmission(Record):
    metadata = Metadata()
    format = String()  # "json", "csv", "xml"
    schema_name = String()  # مرجع إلى المخطط في التكوين
    data = Bytes()  # البيانات الخام للإدخال
    options = Map(String())  # خيارات محددة بالتنسيق
```

### 3. مخططات الخدمات الجديدة

#### 3.1 خدمة استعلام NLP إلى منظمة
ملف جديد: `services/nlp_query.py`

```python
from pulsar.schema import Record, String, Array, Map, Integer, Double
from ..core.primitives import Error

class NLPToStructuredQueryRequest(Record):
    natural_language_query = String()
    max_results = Integer()
    context_hints = Map(String())  # تلميحات سياق اختيارية لتوليد الاستعلام

class NLPToStructuredQueryResponse(Record):
    error = Error()
    graphql_query = String()  # استعلام GraphQL المُنشأ
    variables = Map(String())  # متغيرات GraphQL إذا كانت موجودة
    detected_schemas = Array(String())  # المخططات التي يستهدفها الاستعلام
    confidence = Double()
```

#### 3.2 خدمة استعلام منظمة
ملف جديد: `services/structured_query.py`

```python
from pulsar.schema import Record, String, Map, Array
from ..core.primitives import Error

class StructuredQueryRequest(Record):
    query = String()  # استعلام GraphQL
    variables = Map(String())  # متغيرات GraphQL
    operation_name = String()  # اسم العملية الاختياري للمستندات متعددة العمليات

class StructuredQueryResponse(Record):
    error = Error()
    data = String()  # بيانات استجابة GraphQL المُشفرة بتنسيق JSON
    errors = Array(String())  # أخطاء GraphQL إذا كانت موجودة
```

#### 2.2 مخرجات استخراج الكائنات
ملف جديد: `knowledge/object.py`

```python
from pulsar.schema import Record, String, Map, Double
from ..core.metadata import Metadata

class ExtractedObject(Record):
    metadata = Metadata()
    schema_name = String()  # أي مخطط ينتمي إليه هذا الكائن
    values = Map(String())  # اسم الحقل -> القيمة
    confidence = Double()
    source_span = String()  # نطاق النص الذي تم فيه العثور على الكائن
```

### 4. مخططات معرفة محسّنة

#### 4.1 تحسين تضمين الكائنات
قم بتحديث `knowledge/embeddings.py` لدعم تضمين الكائنات المنظمة بشكل أفضل:

```python
class StructuredObjectEmbedding(Record):
    metadata = Metadata()
    vectors = Array(Array(Double()))
    schema_name = String()
    object_id = String()  # قيمة المفتاح الأساسي
    field_embeddings = Map(Array(Double()))  # تضمينات الحقول
```

## نقاط التكامل

### تكامل التدفق

سيتم استخدام المخططات في وحدات تدفق جديدة:
- `trustgraph-flow/trustgraph/decoding/structured` - يستخدم StructuredDataSubmission
- `trustgraph-flow/trustgraph/query/nlp_query/cassandra` - يستخدم مخططات استعلام NLP
- `trustgraph-flow/trustgraph/query/objects/cassandra` - يستخدم مخططات استعلام منظمة
- `trustgraph-flow/trustgraph/extract/object/row/` - يستهلك Chunk، وينتج ExtractedObject
- `trustgraph-flow/trustgraph/storage/objects/cassandra` - يستخدم مخطط Rows
- `trustgraph-flow/trustgraph/embeddings/object_embeddings/qdrant` - يستخدم مخططات تضمين الكائنات

## ملاحظات التنفيذ

1. **إصدار المخطط**: ضع في اعتبارك إضافة حقل `version` إلى RowSchema لدعم الترحيل المستقبلي
2. **نظام الأنواع**: يجب أن يدعم `Field.type` جميع أنواع بيانات Cassandra الأصلية
3. **عمليات المجموعة**: يجب أن يدعم معظم الخدمات العمليات الفردية والمجمعة
4. **معالجة الأخطاء**: يجب أن يكون للإبلاغ عن الأخطاء باستمرار عبر جميع الخدمات الجديدة
5. **التوافق مع الإصدارات السابقة**: تظل المخططات الحالية دون تغيير باستثناء التحسينات الطفيفة للملفات