# المواصفات الفنية: إعادة هيكلة أداء قاعدة المعرفة Cassandra

**الحالة:** مسودة
**المؤلف:** مساعد
**التاريخ:** 2025-09-18

## نظرة عامة

تتناول هذه المواصفة مشكلات الأداء في تطبيق قاعدة المعرفة Cassandra TrustGraph وتقترح تحسينات لتخزين واستعلام ثلاثيات RDF.

## التنفيذ الحالي

### تصميم المخطط

يستخدم التنفيذ الحالي تصميم جدول واحد في `trustgraph-flow/trustgraph/direct/cassandra_kg.py`:

```sql
CREATE TABLE triples (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY (collection, s, p, o)
);
```

**الفهارس الثانوية:**
`triples_s` على `s` (الموضوع)
`triples_p` على `p` (المُتَعَدِّي)
`triples_o` على `o` (المفعول به)

### أنماط الاستعلام

تدعم التنفيذ الحالي 8 أنماط استعلام متميزة:

1. **get_all(collection, limit=50)** - استرجاع جميع الثلاثيات لمجموعة
   ```sql
   SELECT s, p, o FROM triples WHERE collection = ? LIMIT 50
   ```

2. **get_s(collection, s, limit=10)** - الاستعلام بناءً على الموضوع.
   ```sql
   SELECT p, o FROM triples WHERE collection = ? AND s = ? LIMIT 10
   ```

3. **get_p(collection, p, limit=10)** - الاستعلام بناءً على شرط.
   ```sql
   SELECT s, o FROM triples WHERE collection = ? AND p = ? LIMIT 10
   ```

4. **get_o(collection, o, limit=10)** - الاستعلام بناءً على الكائن.
   ```sql
   SELECT s, p FROM triples WHERE collection = ? AND o = ? LIMIT 10
   ```

5. **get_sp(collection, s, p, limit=10)** - الاستعلام بناءً على الموضوع + المسند.
   ```sql
   SELECT o FROM triples WHERE collection = ? AND s = ? AND p = ? LIMIT 10
   ```

6. **get_po(collection, p, o, limit=10)** - الاستعلام بناءً على الشرط + الكائن ⚠️
   ```sql
   SELECT s FROM triples WHERE collection = ? AND p = ? AND o = ? LIMIT 10 ALLOW FILTERING
   ```

7. **get_os(collection, o, s, limit=10)** - الاستعلام بناءً على الكائن والموضوع ⚠️
   ```sql
   SELECT p FROM triples WHERE collection = ? AND o = ? AND s = ? LIMIT 10 ALLOW FILTERING
   ```

8. **get_spo(collection, s, p, o, limit=10)** - تطابق ثلاثي دقيق.
   ```sql
   SELECT s as x FROM triples WHERE collection = ? AND s = ? AND p = ? AND o = ? LIMIT 10
   ```

### البنية التحتية الحالية

**الملف: `trustgraph-flow/trustgraph/direct/cassandra_kg.py`**
فئة `KnowledgeGraph` واحدة تتعامل مع جميع العمليات.
تجميع الاتصالات من خلال قائمة `_active_clusters` عامة.
اسم جدول ثابت: `"triples"`.
مساحة مفاتيح لكل نموذج مستخدم.
استنساخ SimpleStrategy بعامل 1.

**نقاط التكامل:**
**مسار الكتابة:** `trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`.
**مسار الاستعلام:** `trustgraph-flow/trustgraph/query/triples/cassandra/service.py`.
**مخزن المعرفة:** `trustgraph-flow/trustgraph/tables/knowledge.py`.

## المشكلات المتعلقة بالأداء التي تم تحديدها

### مشكلات على مستوى المخطط

1. **تصميم مفتاح أساسي غير فعال**
   الحالي: `PRIMARY KEY (collection, s, p, o)`.
   يؤدي إلى تجميع ضعيف لأنماط الوصول الشائعة.
   يجبر على استخدام فهرس ثانوي مكلف.

2. **إفراط في استخدام الفهرس الثانوي** ⚠️
   ثلاثة فهارس ثانوية على أعمدة ذات قيم عالية (s، p، o).
   الفهارس الثانوية في Cassandra مكلفة ولا تتوسع بشكل جيد.
   تتطلب الاستعلامات 6 و 7 `ALLOW FILTERING` مما يشير إلى نموذج بيانات ضعيف.

3. **خطر التقسيم الساخن**
   يمكن أن يؤدي مفتاح التقسيم الواحد `collection` إلى إنشاء تقسيمات ساخنة.
   ستتركز المجموعات الكبيرة على عقد فردية.
   لا توجد استراتيجية توزيع لتحقيق موازنة التحميل.

### مشكلات على مستوى الاستعلام

1. **استخدام ALLOW FILTERING** ⚠️
   يتطلب نوعان من الاستعلامات (get_po، get_os) `ALLOW FILTERING`.
   هذه الاستعلامات تفحص العديد من التقسيمات وهي مكلفة للغاية.
   يتدهور الأداء خطيًا مع حجم البيانات.

2. **أنماط وصول غير فعالة**
   لا توجد تحسينات لأنماط استعلام RDF الشائعة.
   فهارس مركبة مفقودة لتوليفات الاستعلامات المتكررة.
   لا توجد اعتبارات لأنماط اجتياز الرسم البياني.

3. **نقص في تحسين الاستعلام**
   لا يوجد تخزين مؤقت لبيانات الاستعلامات المُعدة.
   لا توجد تلميحات أو استراتيجيات لتحسين الاستعلام.
   لا توجد اعتبارات للتقسيم إلى صفحات تتجاوز LIMIT البسيطة.

## بيان المشكلة

يحتوي تطبيق قاعدة المعرفة الحالي في Cassandra على نقطتي اختناق أداء حاسمتين:

### 1. أداء استعلام get_po غير فعال

الاستعلام `get_po(collection, p, o)` غير فعال للغاية لأنه يتطلب `ALLOW FILTERING`:

```sql
SELECT s FROM triples WHERE collection = ? AND p = ? AND o = ? LIMIT 10 ALLOW FILTERING
```

**لماذا هذه مشكلة:**
`ALLOW FILTERING` تجبر Cassandra على فحص جميع الأقسام داخل المجموعة.
تتدهور الأداء بشكل خطي مع حجم البيانات.
هذا نمط استعلام RDF شائع (إيجاد الموضوعات التي لها علاقة محددة بين الفاعل والمفعول به).
يؤدي ذلك إلى زيادة كبيرة في الحمل على المجموعة مع نمو البيانات.

### 2. استراتيجية تجميع غير فعالة

المفتاح الأساسي الحالي `PRIMARY KEY (collection, s, p, o)` يوفر فوائد تجميع محدودة:

**المشاكل المتعلقة بالتجميع الحالي:**
`collection` كمفتاح قسم لا يوزع البيانات بشكل فعال.
تحتوي معظم المجموعات على بيانات متنوعة مما يجعل التجميع غير فعال.
لا توجد اعتبارات لأنماط الوصول الشائعة في استعلامات RDF.
تخلق المجموعات الكبيرة أقسامًا "ساخنة" على عقد فردية.
لا تعمل أعمدة التجميع (s، p، o) على تحسين أنماط اجتياز الرسم البياني النموذجية.

**التأثير:**
لا تستفيد الاستعلامات من قرب البيانات.
استخدام ضعيف لذاكرة التخزين المؤقت.
توزيع غير متساوٍ للحمل عبر عقد المجموعة.
اختناقات في قابلية التوسع مع نمو المجموعات.

## الحل المقترح: استراتيجية إلغاء التسوية باستخدام 4 جداول

### نظرة عامة

استبدل الجدول `triples` الواحد بأربعة جداول مصممة خصيصًا، كل منها مُحسَّن لأنماط استعلام محددة. هذا يلغي الحاجة إلى الفهارس الثانوية و ALLOW FILTERING مع توفير أداء مثالي لجميع أنواع الاستعلامات. يتيح الجدول الرابع حذف المجموعات بكفاءة على الرغم من مفاتيح الأقسام المركبة.

### تصميم المخطط الجديد

**الجدول 1: الاستعلامات المرتكزة على الموضوع (triples_s)**
```sql
CREATE TABLE triples_s (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY ((collection, s), p, o)
);
```
**تحسينات:** get_s، get_sp، get_os
**مفتاح التقسيم:** (collection, s) - توزيع أفضل من مجرد استخدام collection وحده.
**التجميع:** (p, o) - يتيح عمليات بحث فعالة عن المحددات/الكائنات لكيان معين.

**الجدول 2: استعلامات المحدد-الكائن (triples_p)**
```sql
CREATE TABLE triples_p (
    collection text,
    p text,
    o text,
    s text,
    PRIMARY KEY ((collection, p), o, s)
);
```
**تحسين:** get_p, get_po (يزيل الحاجة إلى ALLOW FILTERING!)
**مفتاح التقسيم:** (collection, p) - وصول مباشر عبر الشرط.
**التجميع:** (o, s) - تصفح فعال للكائنات والموضوعات.

**الجدول 3: الاستعلامات المرتكزة على الكائنات (triples_o)**
```sql
CREATE TABLE triples_o (
    collection text,
    o text,
    s text,
    p text,
    PRIMARY KEY ((collection, o), s, p)
);
```
**التحسينات:** get_o
**مفتاح التقسيم:** (collection, o) - وصول مباشر عن طريق الكائن
**التجميع:** (s, p) - تصفح فعال للموضوع والمسند

**الجدول 4: إدارة المجموعات والاستعلامات SPO (triples_collection)**
```sql
CREATE TABLE triples_collection (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY (collection, s, p, o)
);
```
**التحسينات:** get_spo، delete_collection
**مفتاح التقسيم:** مجموعة فقط - يتيح عمليات فعالة على مستوى المجموعة.
**التجميع:** (s, p, o) - ترتيب ثلاثي قياسي.
**الغرض:** استخدام مزدوج للبحث الدقيق عن SPO وكمؤشر للحذف.

### تعيين الاستعلام

| الاستعلام الأصلي | الجدول الهدف | تحسين الأداء |
|----------------|-------------|------------------------|
| get_all(collection) | triples_s | السماح بالتصفية (مقبول للمسح) |
| get_s(collection, s) | triples_s | وصول مباشر إلى التقسيم |
| get_p(collection, p) | triples_p | وصول مباشر إلى التقسيم |
| get_o(collection, o) | triples_o | وصول مباشر إلى التقسيم |
| get_sp(collection, s, p) | triples_s | التقسيم + التجميع |
| get_po(collection, p, o) | triples_p | **لا مزيد من السماح بالتصفية!** |
| get_os(collection, o, s) | triples_o | التقسيم + التجميع |
| get_spo(collection, s, p, o) | triples_collection | بحث مباشر عن المفتاح |
| delete_collection(collection) | triples_collection | قراءة الفهرس، حذف مجمع |

### استراتيجية حذف المجموعة

مع مفاتيح التقسيم المركبة، لا يمكننا ببساطة تنفيذ `DELETE FROM table WHERE collection = ?`. بدلاً من ذلك:

1. **مرحلة القراءة:** استعلام `triples_collection` لسرد جميع الثلاثيات:
   ```sql
   SELECT s, p, o FROM triples_collection WHERE collection = ?
   ```
   هذا فعال لأنه `collection` هو مفتاح التقسيم لهذه الجدولة.

2. **مرحلة الحذف:** لكل ثلاثية (s, p, o)، قم بالحذف من جميع الجداول الأربعة باستخدام مفاتيح التقسيم الكاملة:
   ```sql
   DELETE FROM triples_s WHERE collection = ? AND s = ? AND p = ? AND o = ?
   DELETE FROM triples_p WHERE collection = ? AND p = ? AND o = ? AND s = ?
   DELETE FROM triples_o WHERE collection = ? AND o = ? AND s = ? AND p = ?
   DELETE FROM triples_collection WHERE collection = ? AND s = ? AND p = ? AND o = ?
   ```
   يتم تجميع البيانات في مجموعات مكونة من 100 عنصر لتحقيق الكفاءة.

**تحليل المقايضات:**
✅ يحافظ على الأداء الأمثل للاستعلامات مع الأقسام الموزعة.
✅ لا توجد أقسام "ساخنة" للمجموعات الكبيرة.
❌ منطق حذف أكثر تعقيدًا (قراءة ثم حذف).
❌ وقت الحذف يتناسب مع حجم المجموعة.

### المزايا

1. **يزيل الحاجة إلى ALLOW FILTERING** - كل استعلام لديه مسار وصول أمثل (باستثناء فحص get_all).
2. **لا توجد فهارس ثانوية** - كل جدول هو الفهرس لنمط الاستعلام الخاص به.
3. **توزيع أفضل للبيانات** - مفاتيح التقسيم المركبة توزع الحمل بشكل فعال.
4. **أداء متوقع** - وقت الاستعلام يتناسب مع حجم النتيجة، وليس إجمالي البيانات.
5. **يستفيد من نقاط قوة Cassandra** - مصمم ليتناسب مع بنية Cassandra.
6. **يمكن حذف المجموعات** - تعمل triples_collection كفهرس للحذف.

## خطة التنفيذ

### الملفات التي تتطلب تغييرات

#### الملف الأساسي للتنفيذ

**`trustgraph-flow/trustgraph/direct/cassandra_kg.py`** - مطلوب إعادة كتابة كاملة.

**الطرق الحالية التي تتطلب إعادة هيكلة:**
```python
# Schema initialization
def init(self) -> None  # Replace single table with three tables

# Insert operations
def insert(self, collection, s, p, o) -> None  # Write to all three tables

# Query operations (API unchanged, implementation optimized)
def get_all(self, collection, limit=50)      # Use triples_by_subject
def get_s(self, collection, s, limit=10)     # Use triples_by_subject
def get_p(self, collection, p, limit=10)     # Use triples_by_po
def get_o(self, collection, o, limit=10)     # Use triples_by_object
def get_sp(self, collection, s, p, limit=10) # Use triples_by_subject
def get_po(self, collection, p, o, limit=10) # Use triples_by_po (NO ALLOW FILTERING!)
def get_os(self, collection, o, s, limit=10) # Use triples_by_subject
def get_spo(self, collection, s, p, o, limit=10) # Use triples_by_subject

# Collection management
def delete_collection(self, collection) -> None  # Delete from all three tables
```

#### ملفات التكامل (لا يلزم إجراء أي تغييرات منطقية)

**`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`**
لا يلزم إجراء أي تغييرات - تستخدم واجهة برمجة تطبيقات KnowledgeGraph الحالية.
تستفيد تلقائيًا من تحسينات الأداء.

**`trustgraph-flow/trustgraph/query/triples/cassandra/service.py`**
لا يلزم إجراء أي تغييرات - تستخدم واجهة برمجة تطبيقات KnowledgeGraph الحالية.
تستفيد تلقائيًا من تحسينات الأداء.

### ملفات الاختبار التي تتطلب تحديثات

#### اختبارات الوحدة
**`tests/unit/test_storage/test_triples_cassandra_storage.py`**
تحديث توقعات الاختبار للتغييرات في المخطط.
إضافة اختبارات لضمان الاتساق بين الجداول المتعددة.
التحقق من عدم وجود ALLOW FILTERING في خطط الاستعلام.

**`tests/unit/test_query/test_triples_cassandra_query.py`**
تحديث التأكيدات المتعلقة بالأداء.
اختبار جميع أنماط الاستعلام الثمانية مقابل الجداول الجديدة.
التحقق من توجيه الاستعلام إلى الجداول الصحيحة.

#### اختبارات التكامل
**`tests/integration/test_cassandra_integration.py`**
اختبار شامل مع المخطط الجديد.
مقارنات قياس الأداء.
التحقق من اتساق البيانات عبر الجداول.

**`tests/unit/test_storage/test_cassandra_config_integration.py`**
تحديث اختبارات التحقق من صحة المخطط.
اختبار سيناريوهات الترحيل.

### استراتيجية التنفيذ

#### المرحلة الأولى: المخطط والطرق الأساسية
1. **إعادة كتابة الطريقة `init()`** - إنشاء أربعة جداول بدلاً من جدول واحد.
2. **إعادة كتابة الطريقة `insert()`** - عمليات كتابة مجمعة إلى جميع الجداول الأربعة.
3. **تنفيذ عبارات مُعدة** - للحصول على أداء مثالي.
4. **إضافة منطق توجيه الجدول** - لتوجيه الاستعلامات إلى الجداول المثلى.
5. **تنفيذ حذف المجموعة** - القراءة من triples_collection، وحذف مجمع من جميع الجداول.

#### المرحلة الثانية: تحسين طريقة الاستعلام
1. **إعادة كتابة كل طريقة get_*** لاستخدام الجدول الأمثل.
2. **إزالة جميع استخدامات ALLOW FILTERING**.
3. **تنفيذ استخدام فعال لمفتاح التجميع**.
4. **إضافة تسجيل أداء الاستعلام**.

#### المرحلة الثالثة: إدارة المجموعة
1. **تحديث `delete_collection()`** - إزالتها من جميع الجداول الثلاثة.
2. **إضافة التحقق من الاتساق** - لضمان بقاء جميع الجداول متزامنة.
3. **تنفيذ عمليات مجمعة** - لعمليات متعددة الجداول ذرية.

### تفاصيل التنفيذ الرئيسية

#### استراتيجية الكتابة المجمعة
```python
def insert(self, collection, s, p, o):
    batch = BatchStatement()

    # Insert into all four tables
    batch.add(self.insert_subject_stmt, (collection, s, p, o))
    batch.add(self.insert_po_stmt, (collection, p, o, s))
    batch.add(self.insert_object_stmt, (collection, o, s, p))
    batch.add(self.insert_collection_stmt, (collection, s, p, o))

    self.session.execute(batch)
```

#### منطق توجيه الاستعلامات
```python
def get_po(self, collection, p, o, limit=10):
    # Route to triples_p table - NO ALLOW FILTERING!
    return self.session.execute(
        self.get_po_stmt,
        (collection, p, o, limit)
    )

def get_spo(self, collection, s, p, o, limit=10):
    # Route to triples_collection table for exact SPO lookup
    return self.session.execute(
        self.get_spo_stmt,
        (collection, s, p, o, limit)
    )
```

#### منطق حذف المجموعة
```python
def delete_collection(self, collection):
    # Step 1: Read all triples from collection table
    rows = self.session.execute(
        f"SELECT s, p, o FROM {self.collection_table} WHERE collection = %s",
        (collection,)
    )

    # Step 2: Batch delete from all 4 tables
    batch = BatchStatement()
    count = 0

    for row in rows:
        s, p, o = row.s, row.p, row.o

        # Delete using full partition keys for each table
        batch.add(SimpleStatement(
            f"DELETE FROM {self.subject_table} WHERE collection = ? AND s = ? AND p = ? AND o = ?"
        ), (collection, s, p, o))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.po_table} WHERE collection = ? AND p = ? AND o = ? AND s = ?"
        ), (collection, p, o, s))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.object_table} WHERE collection = ? AND o = ? AND s = ? AND p = ?"
        ), (collection, o, s, p))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.collection_table} WHERE collection = ? AND s = ? AND p = ? AND o = ?"
        ), (collection, s, p, o))

        count += 1

        # Execute every 100 triples to avoid oversized batches
        if count % 100 == 0:
            self.session.execute(batch)
            batch = BatchStatement()

    # Execute remaining deletions
    if count % 100 != 0:
        self.session.execute(batch)

    logger.info(f"Deleted {count} triples from collection {collection}")
```

### تحسين عبارات SQL المُعدة (Prepared Statements)
```python
def prepare_statements(self):
    # Cache prepared statements for better performance
    self.insert_subject_stmt = self.session.prepare(
        f"INSERT INTO {self.subject_table} (collection, s, p, o) VALUES (?, ?, ?, ?)"
    )
    self.insert_po_stmt = self.session.prepare(
        f"INSERT INTO {self.po_table} (collection, p, o, s) VALUES (?, ?, ?, ?)"
    )
    self.insert_object_stmt = self.session.prepare(
        f"INSERT INTO {self.object_table} (collection, o, s, p) VALUES (?, ?, ?, ?)"
    )
    self.insert_collection_stmt = self.session.prepare(
        f"INSERT INTO {self.collection_table} (collection, s, p, o) VALUES (?, ?, ?, ?)"
    )
    # ... query statements
```

## استراتيجية الترحيل

### نهج ترحيل البيانات

#### الخيار الأول: النشر الأزرق-الأخضر (موصى به)
1. **نشر المخطط الجديد جنبًا إلى جنب مع المخطط الحالي** - استخدم أسماء جداول مختلفة مؤقتًا.
2. **فترة الكتابة المزدوجة** - الكتابة إلى كل من المخططين القديم والجديد خلال فترة الانتقال.
3. **ترحيل البيانات في الخلفية** - نسخ البيانات الموجودة إلى الجداول الجديدة.
4. **توجيه عمليات القراءة** - توجيه الاستعلامات إلى الجداول الجديدة بمجرد ترحيل البيانات.
5. **إزالة الجداول القديمة** - بعد فترة التحقق.

#### الخيار الثاني: الترحيل في المكان
1. **إضافة المخطط** - إنشاء جداول جديدة في مساحة المفاتيح الحالية.
2. **برنامج ترحيل البيانات** - نسخ دفعي من الجدول القديم إلى الجداول الجديدة.
3. **تحديث التطبيق** - نشر التعليمات البرمجية الجديدة بعد اكتمال الترحيل.
4. **تنظيف الجدول القديم** - إزالة الجدول القديم والفهارس.

### التوافق مع الإصدارات السابقة

#### استراتيجية النشر
```python
# Environment variable to control table usage during migration
USE_LEGACY_TABLES = os.getenv('CASSANDRA_USE_LEGACY', 'false').lower() == 'true'

class KnowledgeGraph:
    def __init__(self, ...):
        if USE_LEGACY_TABLES:
            self.init_legacy_schema()
        else:
            self.init_optimized_schema()
```

#### نص ترحيل
```python
def migrate_data():
    # Read from old table
    old_triples = session.execute("SELECT collection, s, p, o FROM triples")

    # Batch write to new tables
    for batch in batched(old_triples, 100):
        batch_stmt = BatchStatement()
        for row in batch:
            # Add to all three new tables
            batch_stmt.add(insert_subject_stmt, row)
            batch_stmt.add(insert_po_stmt, (row.collection, row.p, row.o, row.s))
            batch_stmt.add(insert_object_stmt, (row.collection, row.o, row.s, row.p))
        session.execute(batch_stmt)
```

### استراتيجية التحقق من الصحة

#### فحوصات تناسق البيانات
```python
def validate_migration():
    # Count total records in old vs new tables
    old_count = session.execute("SELECT COUNT(*) FROM triples WHERE collection = ?", (collection,))
    new_count = session.execute("SELECT COUNT(*) FROM triples_by_subject WHERE collection = ?", (collection,))

    assert old_count == new_count, f"Record count mismatch: {old_count} vs {new_count}"

    # Spot check random samples
    sample_queries = generate_test_queries()
    for query in sample_queries:
        old_result = execute_legacy_query(query)
        new_result = execute_optimized_query(query)
        assert old_result == new_result, f"Query results differ for {query}"
```

## استراتيجية الاختبار

### اختبار الأداء

#### سيناريوهات قياس الأداء
1. **مقارنة أداء الاستعلامات**
   مقاييس الأداء قبل وبعد لجميع أنواع الاستعلامات الثمانية.
   التركيز على تحسين أداء `get_po` (إزالة `ALLOW FILTERING`).
   قياس زمن استجابة الاستعلامات تحت أحجام بيانات مختلفة.

2. **اختبار التحميل**
   تنفيذ استعلامات متزامنة.
   معدل نقل البيانات مع العمليات الدفعية.
   استخدام الذاكرة ووحدة المعالجة المركزية.

3. **اختبار قابلية التوسع**
   الأداء مع زيادة أحجام المجموعات.
   توزيع الاستعلامات عبر مجموعات متعددة.
   استخدام عقد المجموعة.

#### مجموعات بيانات الاختبار
**صغيرة:** 10 آلاف ثلاثية لكل مجموعة.
**متوسطة:** 100 ألف ثلاثية لكل مجموعة.
**كبيرة:** أكثر من مليون ثلاثية لكل مجموعة.
**مجموعات متعددة:** اختبار توزيع التقسيم.

### اختبار وظيفي

#### تحديثات اختبار الوحدات
```python
# Example test structure for new implementation
class TestCassandraKGPerformance:
    def test_get_po_no_allow_filtering(self):
        # Verify get_po queries don't use ALLOW FILTERING
        with patch('cassandra.cluster.Session.execute') as mock_execute:
            kg.get_po('test_collection', 'predicate', 'object')
            executed_query = mock_execute.call_args[0][0]
            assert 'ALLOW FILTERING' not in executed_query

    def test_multi_table_consistency(self):
        # Verify all tables stay in sync
        kg.insert('test', 's1', 'p1', 'o1')

        # Check all tables contain the triple
        assert_triple_exists('triples_by_subject', 'test', 's1', 'p1', 'o1')
        assert_triple_exists('triples_by_po', 'test', 'p1', 'o1', 's1')
        assert_triple_exists('triples_by_object', 'test', 'o1', 's1', 'p1')
```

#### تحديثات اختبار التكامل
```python
class TestCassandraIntegration:
    def test_query_performance_regression(self):
        # Ensure new implementation is faster than old
        old_time = benchmark_legacy_get_po()
        new_time = benchmark_optimized_get_po()
        assert new_time < old_time * 0.5  # At least 50% improvement

    def test_end_to_end_workflow(self):
        # Test complete write -> query -> delete cycle
        # Verify no performance degradation in integration
```

### خطة التراجع

#### استراتيجية تراجع سريعة
1. **تبديل متغيرات البيئة** - العودة إلى الجداول القديمة على الفور.
2. **الاحتفاظ بالجداول القديمة** - لا تقم بإزالتها حتى يتم إثبات الأداء.
3. **تنبيهات المراقبة** - تشغيل تلقائي للتراجع بناءً على معدلات الخطأ/زمن الاستجابة.

#### التحقق من التراجع
```python
def rollback_to_legacy():
    # Set environment variable
    os.environ['CASSANDRA_USE_LEGACY'] = 'true'

    # Restart services to pick up change
    restart_cassandra_services()

    # Validate functionality
    run_smoke_tests()
```

## المخاطر والاعتبارات

### مخاطر الأداء
**زيادة زمن الاستجابة للكتابة** - 4 عمليات كتابة لكل عملية إدخال (أكثر بنسبة 33٪ من مقاربة الجدول الثلاثي)
**العبء التخزيني** - 4 أضعاف متطلبات التخزين (أكثر بنسبة 33٪ من مقاربة الجدول الثلاثي)
**فشل عمليات الكتابة المجمعة** - الحاجة إلى معالجة الأخطاء بشكل صحيح
**تعقيد الحذف** - يتطلب حذف المجموعة حلقة قراءة ثم حذف

### المخاطر التشغيلية
**تعقيد الترحيل** - ترحيل البيانات لمجموعات البيانات الكبيرة
**تحديات الاتساق** - ضمان بقاء جميع الجداول متزامنة
**فجوات المراقبة** - الحاجة إلى مقاييس جديدة لعمليات الجداول المتعددة

### استراتيجيات التخفيف
1. **النشر التدريجي** - ابدأ بمجموعات صغيرة
2. **مراقبة شاملة** - تتبع جميع مقاييس الأداء
3. **التحقق الآلي** - فحص الاتساق المستمر
4. **إمكانية التراجع السريع** - اختيار الجدول بناءً على البيئة

## معايير النجاح

### تحسينات الأداء
[ ] **إزالة ALLOW FILTERING** - تعمل الاستعلامات get_po و get_os بدون تصفية
[ ] **تقليل زمن استجابة الاستعلام** - تحسن بنسبة 50٪ أو أكثر في أوقات استجابة الاستعلام
[ ] **توزيع أفضل للعبء** - لا توجد أقسام "ساخنة"، وتوزيع متساوٍ عبر عقد المجموعة
[ ] **أداء قابل للتوسع** - وقت الاستعلام يتناسب مع حجم النتيجة، وليس إجمالي البيانات

### المتطلبات الوظيفية
[ ] **توافق واجهة برمجة التطبيقات (API)** - يستمر جميع التعليمات البرمجية الحالية في العمل دون تغيير
[ ] **اتساق البيانات** - تظل جميع الجداول الثلاثة متزامنة
[ ] **عدم فقدان البيانات** - يحافظ الترحيل على جميع الثلاثيات الموجودة
[ ] **التوافق مع الإصدارات السابقة** - القدرة على العودة إلى المخطط القديم

### المتطلبات التشغيلية
[ ] **ترحيل آمن** - نشر أخضر/أزرق مع إمكانية التراجع
[ ] **تغطية المراقبة** - مقاييس شاملة لعمليات الجداول المتعددة
[ ] **تغطية الاختبار** - تم اختبار جميع أنماط الاستعلام باستخدام معايير الأداء
[ ] **التوثيق** - تحديث إجراءات النشر والتشغيل

## الجدول الزمني

### المرحلة 1: التنفيذ
[ ] إعادة كتابة `cassandra_kg.py` باستخدام مخطط الجداول المتعددة
[ ] تنفيذ عمليات الكتابة المجمعة
[ ] إضافة تحسينات باستخدام عبارات مُعدة
[ ] تحديث اختبارات الوحدة

### المرحلة 2: اختبار التكامل
[ ] تحديث اختبارات التكامل
[ ] قياس الأداء
[ ] اختبار التحميل باستخدام أحجام بيانات واقعية
[ ] نصوص التحقق من اتساق البيانات

### المرحلة 3: تخطيط الترحيل
[ ] نصوص النشر الأخضر/الأزرق
[ ] أدوات ترحيل البيانات
[ ] تحديثات لوحة معلومات المراقبة
[ ] إجراءات التراجع

### المرحلة 4: النشر في بيئة الإنتاج
[ ] النشر التدريجي في بيئة الإنتاج
[ ] مراقبة الأداء والتحقق من صحته
[ ] تنظيف الجداول القديمة
[ ] تحديثات التوثيق

## الخلاصة

تعالج هذه الاستراتيجية لإلغاء التسوية متعددة الجداول بشكل مباشر عنقودين رئيسيين للأداء:

1. **تقضي على ALLOW FILTERING المكلفة** من خلال توفير هياكل جداول مثالية لكل نمط استعلام
2. **تحسين فعالية التجميع** من خلال مفاتيح التقسيم المركبة التي توزع الحمل بشكل صحيح

تستفيد هذه الطريقة من نقاط قوة Cassandra مع الحفاظ على توافق كامل مع واجهة برمجة التطبيقات (API)، مما يضمن أن التعليمات البرمجية الحالية تستفيد تلقائيًا من تحسينات الأداء.
