# المواصفات الفنية للبيانات المهيكلة (الجزء 2)

## نظرة عامة

تتناول هذه المواصفات المشكلات والفجوات التي تم تحديدها أثناء التنفيذ الأولي لدمج البيانات المهيكلة في TrustGraph، كما هو موضح في `structured-data.md`.

## بيان المشكلات

### 1. عدم اتساق في التسمية: "كائن" مقابل "صف"

يستخدم التنفيذ الحالي مصطلح "كائن" في جميع أنحائه (على سبيل المثال، `ExtractedObject`، واستخراج الكائنات، وتضمينات الكائنات). هذا المصطلح عام جدًا ويسبب ارتباكًا:

مصطلح "كائن" مصطلح عام ومزدحم في البرمجيات (كائنات بايثون، كائنات JSON، إلخ).
البيانات التي يتم التعامل معها هي في الأساس بيانات جدولية - صفوف في الجداول ذات المخططات المحددة.
مصطلح "صف" يصف نموذج البيانات بشكل أكثر دقة ويتوافق مع مصطلحات قواعد البيانات.

يظهر هذا التناقض في أسماء الوحدات، وأسماء الفئات، وأنواع الرسائل، والوثائق.

### 2. قيود استعلامات تخزين الصفوف

يحتوي تنفيذ تخزين الصفوف الحالي على قيود استعلام كبيرة:

**عدم تطابق مع اللغة الطبيعية**: تواجه الاستعلامات صعوبة في التعامل مع الاختلافات في البيانات الواقعية. على سبيل المثال:
من الصعب العثور على قاعدة بيانات الشوارع التي تحتوي على `"CHESTNUT ST"` عند السؤال عن `"Chestnut Street"`.
تكسر الاختصارات، والاختلافات في الأحرف الكبيرة والصغيرة، وتغيرات التنسيق استعلامات المطابقة التامة.
يتوقع المستخدمون فهمًا دلاليًا، لكن المستودع يوفر مطابقة حرفية.

**مشكلات تطور المخطط**: يؤدي تغيير المخططات إلى حدوث مشكلات:
قد لا تتوافق البيانات الموجودة مع المخططات المحدثة.
يمكن أن تؤدي تغييرات هيكل الجدول إلى تعطيل الاستعلامات وتكامل البيانات.
لا توجد مسار ترحيل واضح لتحديثات المخطط.

### 3. مطلوب تضمينات الصفوف

بالإضافة إلى المشكلة رقم 2، يحتاج النظام إلى تضمينات متجهة لبيانات الصفوف لتمكين:

البحث الدلالي عبر البيانات المهيكلة (العثور على "شارع تشيستنوت" عندما تحتوي البيانات على "CHESTNUT ST").
مطابقة التشابه للاستعلامات الغامضة.
البحث الهجين الذي يجمع بين المرشحات المهيكلة ومطابقة التشابه الدلالي.
دعم أفضل للغة الطبيعية.

تم تحديد خدمة التضمين ولكن لم يتم تنفيذها.

### 4. استيعاب بيانات الصفوف غير مكتمل

مسار استيعاب البيانات المهيكلة ليس فعالًا بالكامل:

توجد مطالبات تشخيصية لتصنيف تنسيقات الإدخال (CSV، JSON، إلخ).
خدمة الاستيعاب التي تستخدم هذه المطالبات غير متصلة بالنظام.
لا يوجد مسار شامل لتحميل البيانات المهيكلة مسبقًا إلى مستودع الصفوف.

## الأهداف

**مرونة المخطط**: تمكين تطور المخطط دون تعطل البيانات الموجودة أو الحاجة إلى عمليات ترحيل.
**تسمية متسقة**: توحيد مصطلح "صف" في جميع أنحاء قاعدة التعليمات البرمجية.
**قابلية الاستعلام الدلالي**: دعم المطابقة الغامضة / الدلالية عبر تضمينات الصفوف.
**مسار استيعاب كامل**: توفير مسار شامل لتحميل البيانات المهيكلة.

## التصميم الفني

### مخطط تخزين صفوف موحد

أنشأ التنفيذ السابق جدول Cassandra منفصل لكل مخطط. تسبب ذلك في حدوث مشكلات عند تطور المخططات، حيث تتطلب تغييرات هيكل الجدول عمليات ترحيل.

يستخدم التصميم الجديد جدولًا موحدًا واحدًا لجميع بيانات الصفوف:

```sql
CREATE TABLE rows (
    collection text,
    schema_name text,
    index_name text,
    index_value frozen<list<text>>,
    data map<text, text>,
    source text,
    PRIMARY KEY ((collection, schema_name, index_name), index_value)
)
```

#### تعريفات الأعمدة

| العمود | النوع | الوصف |
|--------|------|-------------|
| `collection` | `text` | معرف جمع البيانات/الاستيراد (من البيانات الوصفية) |
| `schema_name` | `text` | اسم المخطط الذي يتوافق معه هذا الصف |
| `index_name` | `text` | اسم الحقل/الحقول المفهرسة، مفصولة بفاصلة للحقول المركبة |
| `index_value` | `frozen<list<text>>` | قيم الفهرس كقائمة |
| `data` | `map<text, text>` | بيانات الصف كأزواج مفتاح-قيمة |
| `source` | `text` | عنوان URI اختياري يربط بمعلومات المصدر في الرسم البياني المعرفي. السلسلة الفارغة أو NULL تشير إلى عدم وجود مصدر. |

#### معالجة الفهرس

يتم تخزين كل صف عدة مرات - مرة واحدة لكل حقل مفهرس معرف في المخطط. يتم التعامل مع حقول المفتاح الأساسي كفهرس بدون علامة خاصة، مما يوفر مرونة مستقبلية.

**مثال على الفهرس ذي الحقل الواحد:**
يحدد المخطط `email` كحقل مفهرس
`index_name = "email"`
`index_value = ['foo@bar.com']`

**مثال على الفهرس المركب:**
يحدد المخطط فهرسًا مركبًا على `region` و `status`
`index_name = "region,status"` (أسماء الحقول مرتبة ومفصولة بفاصلة)
`index_value = ['US', 'active']` (القيم بنفس ترتيب أسماء الحقول)

**مثال على المفتاح الأساسي:**
يحدد المخطط `customer_id` كمفتاح أساسي
`index_name = "customer_id"`
`index_value = ['CUST001']`

#### أنماط الاستعلام

تتبع جميع الاستعلامات نفس النمط بغض النظر عن الفهرس المستخدم:

```sql
SELECT * FROM rows
WHERE collection = 'import_2024'
  AND schema_name = 'customers'
  AND index_name = 'email'
  AND index_value = ['foo@bar.com']
```

#### المقايضات التصميمية

**المزايا:**
التغييرات في المخطط لا تتطلب تغييرات في هيكل الجدول.
البيانات الموجودة في الصفوف غير مرئية لـ Cassandra - إضافة أو إزالة الحقول تكون شفافة.
نمط استعلام متسق لجميع طرق الوصول.
لا توجد فهارس ثانوية لـ Cassandra (والتي يمكن أن تكون بطيئة على نطاق واسع).
أنواع Cassandra الأصلية في جميع أنحاء النظام (`map`، `frozen<list>`).

**المقايضات:**
تضخيم الكتابة: كل إدخال صف = N إدخالات (واحد لكل حقل مفهرس).
تكلفة تخزين إضافية بسبب تكرار بيانات الصفوف.
يتم تخزين معلومات النوع في تكوين المخطط، ويتم التحويل في طبقة التطبيق.

#### نموذج الاتساق

التصميم يقبل بعض التبسيط:

1. **لا توجد تحديثات للصفوف**: النظام مخصص للإضافة فقط. هذا يلغي مخاوف الاتساق المتعلقة بتحديث نسخ متعددة من نفس الصف.

2. **تحمل تغيير المخطط**: عند تغيير المخططات (على سبيل المثال، إضافة أو إزالة الفهارس)، تحتفظ الصفوف الموجودة بفهرستها الأصلية. لن يتمكن المستخدمون من اكتشاف الصفوف القديمة عبر الفهارس الجديدة. يمكن للمستخدمين حذف وإعادة إنشاء مخطط لضمان الاتساق إذا لزم الأمر.

### تتبع الأقسام والحذف

#### المشكلة

باستخدام مفتاح التقسيم `(collection, schema_name, index_name)`، يتطلب الحذف الفعال معرفة جميع مفاتيح التقسيم المراد حذفها. يتطلب الحذف باستخدام `collection` أو `collection + schema_name` معرفة جميع قيم `index_name` التي تحتوي على بيانات.

#### جدول تتبع الأقسام

جدول بحث ثانوي يتتبع الأقسام الموجودة:

```sql
CREATE TABLE row_partitions (
    collection text,
    schema_name text,
    index_name text,
    PRIMARY KEY ((collection), schema_name, index_name)
)
```

هذا يتيح اكتشافًا فعالًا للأقسام لعمليات الحذف.

#### سلوك كاتب الصفوف

يحتفظ كاتب الصفوف بخزن مؤقت في الذاكرة لأزواج `(collection, schema_name)` المسجلة. عند معالجة صف:

1. تحقق مما إذا كانت `(collection, schema_name)` موجودة في الذاكرة المؤقتة.
2. إذا لم تكن موجودة في الذاكرة المؤقتة (أول صف لهذه الزوج):
   ابحث في تكوين المخطط للحصول على جميع أسماء الفهارس.
   أدخل إدخالات في `row_partitions` لكل `(collection, schema_name, index_name)`.
   أضف الزوج إلى الذاكرة المؤقتة.
3. تابع بكتابة بيانات الصف.

يراقب كاتب الصفوف أيضًا أحداث تغيير تكوين المخطط. عند حدوث تغيير في المخطط، يتم مسح إدخالات الذاكرة المؤقتة ذات الصلة بحيث يؤدي الصف التالي إلى إعادة التسجيل باستخدام أسماء الفهارس المحدثة.

يضمن هذا النهج:
تتم كتابة جداول البحث مرة واحدة لكل زوج `(collection, schema_name)`، وليس لكل صف.
يعكس جدول البحث الفهارس التي كانت نشطة عند كتابة البيانات.
يتم اكتشاف تغييرات المخطط في منتصف الاستيراد بشكل صحيح.

#### عمليات الحذف

**حذف المجموعة:**
```sql
-- 1. Discover all partitions
SELECT schema_name, index_name FROM row_partitions WHERE collection = 'X';

-- 2. Delete each partition from rows table
DELETE FROM rows WHERE collection = 'X' AND schema_name = '...' AND index_name = '...';
-- (repeat for each discovered partition)

-- 3. Clean up the lookup table
DELETE FROM row_partitions WHERE collection = 'X';
```

**حذف المجموعة والمخطط:**
```sql
-- 1. Discover partitions for this schema
SELECT index_name FROM row_partitions WHERE collection = 'X' AND schema_name = 'Y';

-- 2. Delete each partition from rows table
DELETE FROM rows WHERE collection = 'X' AND schema_name = 'Y' AND index_name = '...';
-- (repeat for each discovered partition)

-- 3. Clean up the lookup table entries
DELETE FROM row_partitions WHERE collection = 'X' AND schema_name = 'Y';
```

### تضمينات الصفوف

تتيح تضمينات الصفوف المطابقة الدلالية/التقريبية على القيم المفهرسة، مما يحل مشكلة عدم تطابق اللغة الطبيعية (على سبيل المثال، العثور على "CHESTNUT ST" عند البحث عن "Chestnut Street").

#### نظرة عامة على التصميم

يتم تضمين كل قيمة مفهرسة وتخزينها في مخزن متجه (Qdrant). في وقت الاستعلام، يتم تضمين الاستعلام، ويتم العثور على المتجهات المشابهة، ويتم استخدام البيانات الوصفية المرتبطة للبحث عن الصفوف الفعلية في Cassandra.

#### هيكل مجموعة Qdrant

مجموعة Qdrant واحدة لكل مجموعة `(user, collection, schema_name, dimension)`:

**تسمية المجموعة:** `rows_{user}_{collection}_{schema_name}_{dimension}`
يتم تنظيف الأسماء (يتم استبدال الأحرف غير الأبجدية الرقمية بـ `_`، وتحويلها إلى أحرف صغيرة، وتتم إضافة بادئة رقمية بـ `r_`)
**السبب:** يتيح حذف مثيل `(user, collection, schema_name)` بشكل نظيف عن طريق حذف مجموعات Qdrant المطابقة؛ تسمح لاحقة الأبعاد لوجود نماذج تضمين مختلفة.

#### ما الذي يتم تضمينه

التمثيل النصي لقيم الفهرس:

| نوع الفهرس | مثال `index_value` | النص المراد تضمينه |
|------------|----------------------|---------------|
| حقل واحد | `['foo@bar.com']` | `"foo@bar.com"` |
| مركب | `['US', 'active']` | `"US active"` (مفصولة بمسافات) |

#### هيكل النقطة

تحتوي كل نقطة Qdrant على:

```json
{
  "id": "<uuid>",
  "vector": [0.1, 0.2, ...],
  "payload": {
    "index_name": "street_name",
    "index_value": ["CHESTNUT ST"],
    "text": "CHESTNUT ST"
  }
}
```

| حقل الحمولة | الوصف |
|---------------|-------------|
| `index_name` | الحقول المفهرسة التي يمثلها هذا التضمين. |
| `index_value` | القائمة الأصلية للقيم (للبحث في Cassandra). |
| `text` | النص الذي تم تضمينه (للتصحيح/العرض). |

ملاحظة: `user`، و `collection`، و `schema_name` مستمدة ضمنيًا من اسم مجموعة Qdrant.

#### مسار الاستعلام

1. يقوم المستخدم بالاستعلام عن "Chestnut Street" ضمن المستخدم U، والمجموعة X، والمخطط Y.
2. تضمين نص الاستعلام.
3. تحديد اسم(أسماء) مجموعة Qdrant التي تتطابق مع البادئة `rows_U_X_Y_`.
4. البحث في مجموعة(مجموعات) Qdrant المطابقة عن أقرب المتجهات.
5. الحصول على النقاط المطابقة التي تحتوي على حمولات تحتوي على `index_name` و `index_value`.
6. الاستعلام عن Cassandra:
   ```sql
   SELECT * FROM rows
   WHERE collection = 'X'
     AND schema_name = 'Y'
     AND index_name = '<from payload>'
     AND index_value = <from payload>
   ```
7. إرجاع الصفوف المطابقة.

#### اختياري: التصفية حسب اسم الفهرس.

يمكن للاستعلامات اختيارياً أن تقوم بالتصفية باستخدام `index_name` في Qdrant للبحث في حقول محددة فقط:

**"ابحث عن أي حقل يطابق 'Chestnut'"** → ابحث في جميع المتجهات في المجموعة.
**"ابحث عن 'street_name' الذي يطابق 'Chestnut'"** → قم بالتصفية حيث `payload.index_name = 'street_name'`.

#### البنية.

تتبع تضمينات الصف النمط **المكون من مرحلتين** المستخدم في GraphRAG (تضمينات الرسم البياني، تضمينات المستندات):

**المرحلة 1: حساب التضمين** (`trustgraph-flow/trustgraph/embeddings/row_embeddings/`) - تستهلك `ExtractedObject`، وتحسب التضمينات عبر خدمة التضمينات، وتُخرج `RowEmbeddings`.
**المرحلة 2: تخزين التضمين** (`trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/`) - تستهلك `RowEmbeddings`، وتكتب المتجهات إلى Qdrant.

كاتب صف Cassandra هو مستهلك متوازي منفصل:

**كاتب صف Cassandra** (`trustgraph-flow/trustgraph/storage/rows/cassandra`) - يستهلك `ExtractedObject`، ويكتب الصفوف إلى Cassandra.

تستهلك جميع الخدمات الثلاثة من نفس التدفق، مما يحافظ عليها منفصلة. هذا يسمح:
بتوسيع نطاق كتابة Cassandra بشكل مستقل عن إنشاء التضمينات وتخزين المتجهات.
يمكن تعطيل خدمات التضمين إذا لم تكن مطلوبة.
لا تؤثر الأعطال في خدمة واحدة على الخدمات الأخرى.
بنية متسقة مع مسارات GraphRAG.

#### مسار الكتابة.

**المرحلة 1 (معالج تضمينات الصف):** عند استقبال `ExtractedObject`:

1. ابحث عن المخطط للعثور على الحقول المفهرسة.
2. لكل حقل مفهرس:
   قم بإنشاء التمثيل النصي لقيمة الفهرس.
   احسب التضمين عبر خدمة التضمينات.
3. أخرج رسالة `RowEmbeddings` تحتوي على جميع المتجهات المحسوبة.

**المرحلة 2 (كتابة تضمينات الصف إلى Qdrant):** عند استقبال `RowEmbeddings`:

1. لكل تضمين في الرسالة:
   حدد مجموعة Qdrant من `(user, collection, schema_name, dimension)`.
   قم بإنشاء المجموعة إذا لزم الأمر (إنشاء كسول في الكتابة الأولى).
   قم بتحديث النقطة باستخدام المتجه والحمولة.

#### أنواع الرسائل.

```python
@dataclass
class RowIndexEmbedding:
    index_name: str              # The indexed field name(s)
    index_value: list[str]       # The field value(s)
    text: str                    # Text that was embedded
    vectors: list[list[float]]   # Computed embedding vectors

@dataclass
class RowEmbeddings:
    metadata: Metadata
    schema_name: str
    embeddings: list[RowIndexEmbedding]
```

#### دمج الحذف

يتم اكتشاف مجموعات Qdrant من خلال مطابقة البادئة مع نمط اسم المجموعة:

**حذف `(user, collection)`:**
1.  قائمة بجميع مجموعات Qdrant التي تتطابق مع البادئة `rows_{user}_{collection}_`
2.  حذف كل مجموعة مطابقة
3.  حذف أقسام صفوف Cassandra (كما هو موثق أعلاه)
4.  تنظيف إدخالات `row_partitions`

**حذف `(user, collection, schema_name)`:**
1.  قائمة بجميع مجموعات Qdrant التي تتطابق مع البادئة `rows_{user}_{collection}_{schema_name}_`
2.  حذف كل مجموعة مطابقة (يتعامل مع أبعاد متعددة)
3.  حذف أقسام صفوف Cassandra
4.  تنظيف `row_partitions`

#### مواقع الوحدات

| المرحلة | الوحدة | نقطة الدخول |
|-------|--------|-------------|
| المرحلة 1 | `trustgraph-flow/trustgraph/embeddings/row_embeddings/` | `row-embeddings` |
| المرحلة 2 | `trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/` | `row-embeddings-write-qdrant` |

### واجهة برمجة تطبيقات استعلام تضمينات الصفوف

استعلام تضمينات الصفوف هو **واجهة برمجة تطبيقات منفصلة** عن خدمة استعلام الصفوف GraphQL:

| واجهة برمجة التطبيقات | الغرض | الواجهة الخلفية |
|-----|---------|---------|
| استعلام الصفوف (GraphQL) | مطابقة دقيقة في الحقول المفهرسة | Cassandra |
| استعلام تضمينات الصفوف | مطابقة تقريبية/دلالية | Qdrant |

هذا الفصل يحافظ على الفصل بين المهام:
خدمة GraphQL تركز على الاستعلامات الدقيقة والمنظمة
واجهة برمجة تطبيقات التضمينات تتعامل مع التشابه الدلالي
سير عمل المستخدم: بحث تقريبي عبر التضمينات للعثور على المرشحين، ثم استعلام دقيق للحصول على بيانات الصف الكاملة

#### مخطط الطلب/الاستجابة

```python
@dataclass
class RowEmbeddingsRequest:
    vectors: list[list[float]]    # Query vectors (pre-computed embeddings)
    user: str = ""
    collection: str = ""
    schema_name: str = ""
    index_name: str = ""          # Optional: filter to specific index
    limit: int = 10               # Max results per vector

@dataclass
class RowIndexMatch:
    index_name: str = ""          # The matched index field(s)
    index_value: list[str] = []   # The matched value(s)
    text: str = ""                # Original text that was embedded
    score: float = 0.0            # Similarity score

@dataclass
class RowEmbeddingsResponse:
    error: Error | None = None
    matches: list[RowIndexMatch] = []
```

#### معالج الاستعلامات

الوحدة: `trustgraph-flow/trustgraph/query/row_embeddings/qdrant`

نقطة الدخول: `row-embeddings-query-qdrant`

المعالج:
1. يتلقى `RowEmbeddingsRequest` مع متجهات الاستعلام.
2. يجد مجموعة Qdrant المناسبة عن طريق مطابقة البادئة.
3. يبحث عن أقرب المتجهات مع مرشح `index_name` اختياري.
4. يُرجع `RowEmbeddingsResponse` مع معلومات الفهرس المطابقة.

#### تكامل بوابة واجهة برمجة التطبيقات (API Gateway)

تعرض البوابة استعلامات تضمينات الصفوف عبر النمط القياسي للطلب/الاستجابة:

| المكون | الموقع |
|-----------|----------|
| الموزع | `trustgraph-flow/trustgraph/gateway/dispatch/row_embeddings_query.py` |
| التسجيل | أضف `"row-embeddings"` إلى `request_response_dispatchers` في `manager.py` |

اسم واجهة التدفق: `row-embeddings`

تعريف الواجهة في مخطط التدفق:
```json
{
  "interfaces": {
    "row-embeddings": {
      "request": "non-persistent://tg/request/row-embeddings:{id}",
      "response": "non-persistent://tg/response/row-embeddings:{id}"
    }
  }
}
```

#### دعم حزمة تطوير البرمجيات (SDK) الخاصة بـ Python

توفر حزمة تطوير البرمجيات (SDK) طرقًا للاستعلام عن تضمينات الصفوف:

```python
# Flow-scoped query (preferred)
api = Api(url)
flow = api.flow().id("default")

# Query with text (SDK computes embeddings)
matches = flow.row_embeddings_query(
    text="Chestnut Street",
    collection="my_collection",
    schema_name="addresses",
    index_name="street_name",  # Optional filter
    limit=10
)

# Query with pre-computed vectors
matches = flow.row_embeddings_query(
    vectors=[[0.1, 0.2, ...]],
    collection="my_collection",
    schema_name="addresses"
)

# Each match contains:
for match in matches:
    print(match.index_name)   # e.g., "street_name"
    print(match.index_value)  # e.g., ["CHESTNUT ST"]
    print(match.text)         # e.g., "CHESTNUT ST"
    print(match.score)        # e.g., 0.95
```

#### أداة سطر الأوامر

الأمر: `tg-invoke-row-embeddings`

```bash
# Query by text (computes embedding automatically)
tg-invoke-row-embeddings \
  --text "Chestnut Street" \
  --collection my_collection \
  --schema addresses \
  --index street_name \
  --limit 10

# Query by vector file
tg-invoke-row-embeddings \
  --vectors vectors.json \
  --collection my_collection \
  --schema addresses

# Output formats
tg-invoke-row-embeddings --text "..." --format json
tg-invoke-row-embeddings --text "..." --format table
```

#### النمط النموذجي للاستخدام

عادةً ما يتم استخدام استعلام تضمينات الصفوف كجزء من تدفق بحث تقريبي إلى دقيق:

```python
# Step 1: Fuzzy search via embeddings
matches = flow.row_embeddings_query(
    text="chestnut street",
    collection="geo",
    schema_name="streets"
)

# Step 2: Exact lookup via GraphQL for full row data
for match in matches:
    query = f'''
    query {{
        streets(where: {{ {match.index_name}: {{ eq: "{match.index_value[0]}" }} }}) {{
            street_name
            city
            zip_code
        }}
    }}
    '''
    rows = flow.rows_query(query, collection="geo")
```

هذا النمط المكون من خطوتين يمكّن:
العثور على "CHESTNUT ST" عندما يبحث المستخدم عن "Chestnut Street"
استرجاع بيانات الصف بأكملها مع جميع الحقول
الجمع بين التشابه الدلالي والوصول إلى البيانات المنظمة

### استيعاب بيانات الصف

سيتم تأجيله إلى مرحلة لاحقة. سيتم تصميمه جنبًا إلى جنب مع تغييرات الاستيعاب الأخرى.

## التأثير على التنفيذ

### تحليل الحالة الحالية

يحتوي التنفيذ الحالي على مكونين رئيسيين:

| المكون | الموقع | الأسطر | الوصف |
|-----------|----------|-------|-------------|
| خدمة الاستعلام | `trustgraph-flow/trustgraph/query/objects/cassandra/service.py` | ~740 | كتلة واحدة: توليد مخطط GraphQL، تحليل المرشحات، استعلامات Cassandra، معالجة الطلبات |
| الكاتب | `trustgraph-flow/trustgraph/storage/objects/cassandra/write.py` | ~540 | إنشاء جدول لكل مخطط، فهارس ثانوية، إدراج/حذف |

**نمط الاستعلام الحالي:**
```sql
SELECT * FROM {keyspace}.o_{schema_name}
WHERE collection = 'X' AND email = 'foo@bar.com'
ALLOW FILTERING
```

**نمط استعلام جديد:**
```sql
SELECT * FROM {keyspace}.rows
WHERE collection = 'X' AND schema_name = 'customers'
  AND index_name = 'email' AND index_value = ['foo@bar.com']
```

### التغييرات الرئيسية

1. **تبسيط دلالات الاستعلام**: المخطط الجديد يدعم فقط المطابقات الدقيقة على `index_value`. مرشحات GraphQL الحالية (`gt`، `lt`، `contains`، إلخ) إما:
   تصبح تصفية لاحقة على البيانات المُرجعة (إذا كانت لا تزال مطلوبة)
   يتم إزالتها لصالح استخدام واجهة برمجة تطبيقات التضمينات للمطابقة التقريبية

2. **كود GraphQL مرتبط ارتباطًا وثيقًا**: يحتوي `service.py` الحالي على توليد أنواع Strawberry، وتحليل المرشحات، والاستعلامات الخاصة بـ Cassandra. إضافة قاعدة بيانات أخرى ستؤدي إلى تكرار حوالي 400 سطر من كود GraphQL.

### إعادة الهيكلة المقترحة

تتكون إعادة الهيكلة من جزأين:

#### 1. فصل كود GraphQL

استخراج مكونات GraphQL القابلة لإعادة الاستخدام إلى وحدة مشتركة:

```
trustgraph-flow/trustgraph/query/graphql/
├── __init__.py
├── types.py        # Filter types (IntFilter, StringFilter, FloatFilter)
├── schema.py       # Dynamic schema generation from RowSchema
└── filters.py      # Filter parsing utilities
```

هذا يتيح:
إعادة الاستخدام عبر خلفيات تخزين الصفوف المختلفة.
فصل أوضح للمسؤوليات.
اختبار منطق GraphQL بسهولة أكبر بشكل مستقل.

#### 2. تنفيذ مخطط الجدول الجديد

إعادة هيكلة التعليمات البرمجية الخاصة بـ Cassandra لاستخدام الجدول الموحد:

**الكاتب** (`trustgraph-flow/trustgraph/storage/rows/cassandra/`):
جدول `rows` واحد بدلاً من الجداول الخاصة بكل مخطط.
كتابة N من النسخ لكل صف (واحد لكل فهرس).
التسجيل في جدول `row_partitions`.
إنشاء جدول أبسط (إعداد لمرة واحدة).

**خدمة الاستعلام** (`trustgraph-flow/trustgraph/query/rows/cassandra/`):
الاستعلام عن جدول `rows` الموحد.
استخدام الوحدة النمطية GraphQL المستخرجة لإنشاء المخطط.
تبسيط معالجة المرشحات (مطابقة تامة فقط على مستوى قاعدة البيانات).

### تغيير أسماء الوحدات النمطية

كجزء من عملية تنظيف أسماء "object" → "row":

| الحالي | الجديد |
|---------|-----|
| `storage/objects/cassandra/` | `storage/rows/cassandra/` |
| `query/objects/cassandra/` | `query/rows/cassandra/` |
| `embeddings/object_embeddings/` | `embeddings/row_embeddings/` |

### وحدات نمطية جديدة

| الوحدة النمطية | الغرض |
|--------|---------|
| `trustgraph-flow/trustgraph/query/graphql/` | أدوات GraphQL مشتركة |
| `trustgraph-flow/trustgraph/query/row_embeddings/qdrant/` | واجهة برمجة تطبيقات استعلام تضمينات الصفوف |
| `trustgraph-flow/trustgraph/embeddings/row_embeddings/` | حساب تضمينات الصفوف (المرحلة 1) |
| `trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/` | تخزين تضمينات الصفوف (المرحلة 2) |

## المراجع

[مواصفات البيانات المنظمة](structured-data.md)
