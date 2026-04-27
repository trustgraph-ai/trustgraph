---
layout: default
title: "مواصفات فنية لإدارة المجموعات"
parent: "Arabic (Beta)"
---

# مواصفات فنية لإدارة المجموعات

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## نظرة عامة

تصف هذه المواصفات إمكانات إدارة المجموعات لـ TrustGraph، والتي تتطلب إنشاء مجموعات بشكل صريح وتوفر تحكمًا مباشرًا في دورة حياة المجموعة. يجب إنشاء المجموعات بشكل صريح قبل استخدامها، مما يضمن المزامنة الصحيحة بين بيانات وصفية أمين المكتبة وجميع الواجهات الخلفية للتخزين. تدعم هذه الميزة أربع حالات استخدام رئيسية:

1. **إنشاء المجموعة**: إنشاء مجموعات بشكل صريح قبل تخزين البيانات
2. **قائمة المجموعات**: عرض جميع المجموعات الموجودة في النظام
3. **إدارة بيانات وصفية المجموعة**: تحديث أسماء المجموعات والأوصاف والعلامات
4. **حذف المجموعة**: إزالة المجموعات والبيانات المرتبطة بها عبر جميع أنواع التخزين

## الأهداف

**إنشاء المجموعة بشكل صريح**: تتطلب أن يتم إنشاء المجموعات قبل تخزين البيانات
**مزامنة التخزين**: ضمان وجود المجموعات في جميع الواجهات الخلفية للتخزين (المتجهات، والكائنات، والثلاثيات)
**إمكانية رؤية المجموعة**: تمكين المستخدمين من سرد وفحص جميع المجموعات في بيئتهم
**تنظيف المجموعة**: السماح بحذف المجموعات التي لم تعد مطلوبة
**تنظيم المجموعة**: دعم العلامات والملصقات لتتبع واكتشاف المجموعة بشكل أفضل
**إدارة البيانات الوصفية**: ربط بيانات وصفية ذات مغزى بالمجموعات من أجل الوضوح التشغيلي
**اكتشاف المجموعة**: تسهيل العثور على مجموعات معينة من خلال التصفية والبحث
**الشفافية التشغيلية**: توفير رؤية واضحة لدورة حياة المجموعة واستخدامها
**إدارة الموارد**: تمكين تنظيف المجموعات غير المستخدمة لتحسين استخدام الموارد
**سلامة البيانات**: منع وجود مجموعات معزولة في التخزين بدون تتبع البيانات الوصفية

## الخلفية

في السابق، كانت المجموعات في TrustGraph يتم إنشاؤها ضمنيًا أثناء عمليات تحميل البيانات، مما أدى إلى مشاكل في المزامنة حيث يمكن أن توجد المجموعات في الواجهات الخلفية للتخزين بدون بيانات وصفية مقابلة في أمين المكتبة. وقد أدى ذلك إلى تحديات إدارية وإمكانية وجود بيانات معزولة.

يعالج نموذج إنشاء المجموعة الصريح هذه المشكلات عن طريق:
طلب إنشاء المجموعات قبل استخدامها عبر `tg-set-collection`
بث إنشاء المجموعة إلى جميع الواجهات الخلفية للتخزين
الحفاظ على حالة متزامنة بين بيانات وصفية أمين المكتبة والتخزين
منع الكتابة إلى المجموعات غير الموجودة
توفير إدارة واضحة لدورة حياة المجموعة

تحدد هذه المواصفات نموذج إدارة المجموعة الصريح. من خلال طلب إنشاء المجموعة بشكل صريح، تضمن TrustGraph:
تتبع المجموعات في بيانات وصفية أمين المكتبة من لحظة إنشائها
أن تكون جميع الواجهات الخلفية للتخزين على علم بالمجموعات قبل استقبال البيانات
عدم وجود مجموعات معزولة في التخزين
رؤية وتحكم واضحين في دورة حياة المجموعة
معالجة أخطاء متسقة عند الإشارة العمليات إلى مجموعات غير موجودة

## التصميم الفني

### البنية التحتية

سيتم تنفيذ نظام إدارة المجموعة داخل البنية التحتية الحالية لـ TrustGraph:

1. **تكامل خدمة أمين المكتبة**
   سيتم إضافة عمليات إدارة المجموعة إلى خدمة أمين المكتبة الحالية
   لا توجد خدمة جديدة مطلوبة - تستفيد من أنماط المصادقة والوصول الحالية
   تتعامل مع قائمة المجموعات وحذفها وإدارة بياناتها الوصفية

   الوحدة: trustgraph-librarian

2. **جدول بيانات وصفية المجموعة في Cassandra**
   جدول جديد في مساحة مفاتيح أمين المكتبة الحالية
   يخزن بيانات وصفية المجموعة مع وصول المستخدم
   المفتاح الأساسي: (user_id, collection_id) لضمان تعدد المستأجرين المناسب

   الوحدة: trustgraph-librarian

3. **واجهة سطر الأوامر لإدارة المجموعة**
   واجهة سطر أوامر لعمليات المجموعة
   يوفر أوامر للقائمة والحذف والملصقات والعلامات
   يتكامل مع إطار عمل سطر الأوامر الحالي

   الوحدة: trustgraph-cli

### نماذج البيانات

#### جدول بيانات وصفية المجموعة في Cassandra

سيتم تخزين بيانات وصفية المجموعة في جدول Cassandra منظم في مساحة مفاتيح أمين المكتبة:

```sql
CREATE TABLE collections (
    user text,
    collection text,
    name text,
    description text,
    tags set<text>,
    created_at timestamp,
    updated_at timestamp,
    PRIMARY KEY (user, collection)
);
```

هيكل الجدول:
**user**: + **collection**: مفتاح أساسي مركب يضمن عزل المستخدم
**name**: اسم المجموعة الذي يمكن قراءته بواسطة الإنسان
**description**: وصف تفصيلي لغرض المجموعة
**tags**: مجموعة من العلامات لتصنيف وتصفية
**created_at**: طابع زمني لإنشاء المجموعة
**updated_at**: طابع زمني لآخر تعديل

هذا النهج يسمح بـ:
إدارة مجموعات متعددة المستأجرين مع عزل المستخدم
استعلام فعال حسب المستخدم والمجموعة
نظام تصنيف مرن للتنظيم
تتبع دورة حياة المجموعة للحصول على رؤى تشغيلية

#### دورة حياة المجموعة

يتم إنشاء المجموعات بشكل صريح في المكتبة قبل أن تتمكن عمليات البيانات من المضي قدمًا:

1. **إنشاء المجموعة** (مساران):

   **المسار أ: الإنشاء الذي يبدأه المستخدم** عبر `tg-set-collection`:
   يقوم المستخدم بتوفير معرف المجموعة والاسم والوصف والعلامات
   تقوم المكتبة بإنشاء سجل بيانات وصفية في جدول `collections`
   تقوم المكتبة ببث "إنشاء مجموعة" إلى جميع الواجهات الخلفية للتخزين
   تقوم جميع معالجات التخزين بإنشاء المجموعة وتأكيد النجاح
   أصبحت المجموعة الآن جاهزة لعمليات البيانات

   **المسار ب: الإنشاء التلقائي عند إرسال المستند**:
   يقوم المستخدم بإرسال مستند يحدد معرف مجموعة
   تتحقق المكتبة مما إذا كانت المجموعة موجودة في جدول البيانات الوصفية
   إذا لم تكن موجودة: تقوم المكتبة بإنشاء بيانات وصفية مع القيم الافتراضية (الاسم = معرف المجموعة، وصف/علامات فارغة)
   تقوم المكتبة ببث "إنشاء مجموعة" إلى جميع الواجهات الخلفية للتخزين
   تقوم جميع معالجات التخزين بإنشاء المجموعة وتأكيد النجاح
   تستمر معالجة المستند مع إنشاء المجموعة الآن

   يضمن كلا المسارين وجود المجموعة في بيانات المكتبة الوصفية وجميع الواجهات الخلفية للتخزين قبل السماح بعمليات البيانات.

2. **التحقق من التخزين**: تتحقق عمليات الكتابة من وجود المجموعة:
   تتحقق معالجات التخزين من حالة المجموعة قبل قبول عمليات الكتابة
   تؤدي عمليات الكتابة إلى مجموعات غير موجودة إلى إرجاع خطأ
   يمنع هذا عمليات الكتابة المباشرة التي تتجاوز منطق إنشاء المجموعة الخاص بالمكتبة

3. **سلوك الاستعلام**: تتعامل عمليات الاستعلام مع المجموعات غير الموجودة بأمان:
   تؤدي الاستعلامات إلى مجموعات غير موجودة إلى إرجاع نتائج فارغة
   لا يتم إرجاع أي خطأ لعمليات الاستعلام
   يسمح بالاستكشاف دون الحاجة إلى وجود المجموعة

4. **تحديثات البيانات الوصفية**: يمكن للمستخدمين تحديث بيانات وصفية للمجموعة بعد الإنشاء:
   قم بتحديث الاسم والوصف والعلامات عبر `tg-set-collection`
   تنطبق التحديثات على بيانات المكتبة الوصفية فقط
   تحتفظ الواجهات الخلفية للتخزين بالمجموعة ولكن لا يتم نشر تحديثات البيانات الوصفية

5. **الحذف الصريح**: يقوم المستخدمون بحذف المجموعات عبر `tg-delete-collection`:
   تقوم المكتبة ببث "حذف مجموعة" إلى جميع الواجهات الخلفية للتخزين
   تنتظر تأكيدًا من جميع معالجات التخزين
   تحذف سجل بيانات المكتبة الوصفية فقط بعد اكتمال تنظيف التخزين
   يضمن عدم وجود بيانات متبقية في التخزين

**المبدأ الأساسي**: المكتبة هي نقطة التحكم الوحيدة لإنشاء المجموعة. سواء تم بدءها بأمر المستخدم أو بإرسال مستند، تضمن المكتبة تتبع البيانات الوصفية المناسبة ومزامنة الواجهة الخلفية للتخزين قبل السماح بعمليات البيانات.

العمليات المطلوبة:
**إنشاء مجموعة**: عملية المستخدم عبر `tg-set-collection` أو تلقائيًا عند إرسال مستند
**تحديث بيانات وصفية للمجموعة**: عملية المستخدم لتعديل الاسم والوصف والعلامات
**حذف مجموعة**: عملية المستخدم لإزالة المجموعة والبيانات المرتبطة بها عبر جميع المتاجر
**قائمة المجموعات**: عملية المستخدم لعرض المجموعات مع التصفية حسب العلامات

#### إدارة المجموعة عبر المتاجر

توجد المجموعات عبر واجهات خلفية تخزين متعددة في TrustGraph:
**مخازن المتجهات** (Qdrant، Milvus، Pinecone): تخزن التضمينات والبيانات المتجهة
**مخازن الكائنات** (Cassandra): تخزن المستندات وبيانات الملف
**مخازن الثلاثيات** (Cassandra، Neo4j، Memgraph، FalkorDB): تخزن بيانات الرسم البياني/RDF

Each store type implements:
**Collection State Tracking**: Maintain knowledge of which collections exist
**Collection Creation**: Accept and process "create-collection" operations
**Collection Validation**: Check collection exists before accepting writes
**Collection Deletion**: Remove all data for specified collection

The librarian service coordinates collection operations across all store types, ensuring:
Collections created in all backends before use
All backends confirm creation before returning success
Synchronized collection lifecycle across storage types
Consistent error handling when collections don't exist

#### Collection State Tracking by Storage Type

Each storage backend tracks collection state differently based on its capabilities:

**Cassandra Triple Store:**
Uses existing `triples_collection` table
Creates system marker triple when collection created
Query: `SELECT collection FROM triples_collection WHERE collection = ? LIMIT 1`
Efficient single-partition check for collection existence

**Qdrant/Milvus/Pinecone Vector Stores:**
Native collection APIs provide existence checking
Collections created with proper vector configuration
`collection_exists()` method uses storage API
Collection creation validates dimension requirements

**Neo4j/Memgraph/FalkorDB Graph Stores:**
Use `:CollectionMetadata` nodes to track collections
Node properties: `{user, collection, created_at}`
Query: `MATCH (c:CollectionMetadata {user: $user, collection: $collection})`
Separate from data nodes for clean separation
Enables efficient collection listing and validation

**Cassandra Object Store:**
Uses collection metadata table or marker rows
Similar pattern to triple store
Validates collection before document writes

### APIs

Collection Management APIs (Librarian):
**Create/Update Collection**: Create new collection or update existing metadata via `tg-set-collection`
**List Collections**: Retrieve collections for a user with optional tag filtering
**Delete Collection**: Remove collection and associated data, cascading to all store types

Storage Management APIs (All Storage Processors):
**Create Collection**: Handle "create-collection" operation, establish collection in storage
**Delete Collection**: Handle "delete-collection" operation, remove all collection data
**Collection Exists Check**: Internal validation before accepting write operations

Data Operation APIs (Modified Behavior):
**Write APIs**: Validate collection exists before accepting data, return error if not
**Query APIs**: Return empty results for non-existent collections without error

### Implementation Details

The implementation will follow existing TrustGraph patterns for service integration and CLI command structure.

#### Collection Deletion Cascade

When a user initiates collection deletion through the librarian service:

1. **Metadata Validation**: Verify collection exists and user has permission to delete
2. **Store Cascade**: Librarian coordinates deletion across all store writers:
   Vector store writer: Remove embeddings and vector indexes for the user and collection
   Object store writer: Remove documents and files for the user and collection
   Triple store writer: Remove graph data and triples for the user and collection
3. **Metadata Cleanup**: Remove collection metadata record from Cassandra
4. **Error Handling**: If any store deletion fails, maintain consistency through rollback or retry mechanisms

#### Collection Management Interface

**⚠️ LEGACY APPROACH - REPLACED BY CONFIG-BASED PATTERN**

The queue-based architecture described below has been replaced with a config-based approach using `CollectionConfigHandler`. All storage backends now receive collection updates via config push messages instead of dedicated management queues.

~~All store writers implement a standardized collection management interface with a common schema:~~

~~**Message Schema (`StorageManagementRequest`):**~~
```json
{
  "operation": "create-collection" | "delete-collection",
  "user": "user123",
  "collection": "documents-2024"
}
```

~~**هيكلة قائمة الانتظار:**~~
~~**قائمة انتظار إدارة مخزن المتجهات** (`vector-storage-management`): مخازن المتجهات/التضمينات~~
~~**قائمة انتظار إدارة مخزن الكائنات** (`object-storage-management`): مخازن الكائنات/المستندات~~
~~**قائمة انتظار إدارة مخزن الثلاثيات** (`triples-storage-management`): مخازن الرسم البياني/RDF~~
~~**قائمة انتظار استجابة التخزين** (`storage-management-response`): يتم إرسال جميع الاستجابات هنا~~

**التنفيذ الحالي:**

تستخدم جميع واجهات التخزين الخلفية الآن `CollectionConfigHandler`:
**تكامل دفع التكوين**: تسجل خدمات التخزين للحصول على إشعارات دفع التكوين
**المزامنة التلقائية**: يتم إنشاء/حذف المجموعات بناءً على تغييرات التكوين
**نموذج تصريحي**: يتم تعريف المجموعات في خدمة التكوين، وتقوم الواجهات الخلفية بالمزامنة للمطابقة
**لا يوجد طلب/استجابة**: يلغي تكامل التنسيق وتتبع الاستجابة
**تتبع حالة المجموعة**: يتم الحفاظ عليه عبر ذاكرة التخزين المؤقت `known_collections`
**عمليات قابلة للعكس**: من الآمن معالجة نفس التكوين عدة مرات

تقوم كل واجهة تخزين خلفية بتنفيذ:
`create_collection(user: str, collection: str, metadata: dict)` - إنشاء هياكل المجموعة
`delete_collection(user: str, collection: str)` - إزالة جميع بيانات المجموعة
`collection_exists(user: str, collection: str) -> bool` - التحقق من الصحة قبل الكتابة

#### إعادة هيكلة مخزن الثلاثيات Cassandra

كجزء من هذا التنفيذ، سيتم إعادة هيكلة مخزن الثلاثيات Cassandra من نموذج جدول لكل مجموعة إلى نموذج جدول موحد:

**الهيكلة الحالية:**
مساحة مفاتيح لكل مستخدم، وجدول منفصل لكل مجموعة
المخطط: `(s, p, o)` مع `PRIMARY KEY (s, p, o)`
أسماء الجداول: تصبح مجموعات المستخدمين جداول Cassandra منفصلة

**الهيكلة الجديدة:**
مساحة مفاتيح لكل مستخدم، وجدول "ثلاثيات" واحد لجميع المجموعات
المخطط: `(collection, s, p, o)` مع `PRIMARY KEY (collection, s, p, o)`
عزل المجموعة من خلال تقسيم المجموعة

**التغييرات المطلوبة:**

1. **إعادة هيكلة فئة TrustGraph** (`trustgraph/direct/cassandra.py`):
   إزالة المعلمة `table` من المُنشئ، واستخدام جدول "ثلاثيات" ثابت
   إضافة المعلمة `collection` إلى جميع الطرق
   تحديث المخطط لتضمين المجموعة كأول عمود
   **تحديثات الفهرس**: سيتم إنشاء فهارس جديدة لدعم جميع أنماط الاستعلام الثمانية:
     فهرس على `(s)` للاستعلامات المستندة إلى الموضوع
     فهرس على `(p)` للاستعلامات المستندة إلى الرابط
     فهرس على `(o)` للاستعلامات المستندة إلى الكائن
     ملاحظة: لا تدعم Cassandra فهارس ثانوية متعددة الأعمدة، لذا هذه هي فهارس أحادية العمود

   **أداء نمط الاستعلام:**
     ✅ `get_all()` - فحص التقسيم على `collection`
     ✅ `get_s(s)` - يستخدم المفتاح الأساسي بكفاءة (`collection, s`)
     ✅ `get_p(p)` - يستخدم `idx_p` مع تصفية `collection`
     ✅ `get_o(o)` - يستخدم `idx_o` مع تصفية `collection`
     ✅ `get_sp(s, p)` - يستخدم المفتاح الأساسي بكفاءة (`collection, s, p`)
     ⚠️ `get_po(p, o)` - يتطلب `ALLOW FILTERING` (يستخدم إما `idx_p` أو `idx_o` بالإضافة إلى التصفية)
     ✅ `get_os(o, s)` - يستخدم `idx_o` مع تصفية إضافية على `s`
     ✅ `get_spo(s, p, o)` - يستخدم المفتاح الأساسي بكفاءة

   **ملاحظة حول ALLOW FILTERING**: يتطلب نمط استعلام `get_po` `ALLOW FILTERING` لأنه يحتاج إلى كل من قيود الرابط والكائن بدون فهرس مركب مناسب. هذا مقبول لأن نمط الاستعلام هذا أقل شيوعًا من الاستعلامات المستندة إلى الموضوع في الاستخدام النموذجي لمخزن الثلاثيات.

2. **تحديثات كاتب التخزين** (`trustgraph/storage/triples/cassandra/write.py`):
   الحفاظ على اتصال TrustGraph واحد لكل مستخدم بدلاً من لكل (مستخدم، مجموعة)
   تمرير المجموعة إلى عمليات الإدراج
   تحسين استخدام الموارد مع عدد أقل من الاتصالات

3. **تحديثات خدمة الاستعلام** (`trustgraph/query/triples/cassandra/service.py`):
   اتصال TrustGraph واحد لكل مستخدم
   تمرير المجموعة إلى جميع عمليات الاستعلام
   الحفاظ على نفس منطق الاستعلام مع معلمة المجموعة

**الفوائد:**
**تبسيط حذف المجموعة**: حذف باستخدام مفتاح التقسيم `collection` عبر جميع الجداول الأربعة
**كفاءة الموارد**: عدد أقل من اتصالات قاعدة البيانات وكائنات الجدول
**العمليات عبر المجموعات**: من الأسهل تنفيذ العمليات التي تمتد عبر مجموعات متعددة
**هيكلة متسقة**: تتماشى مع نهج بيانات التعريف الموحد للمجموعة
**التحقق من صحة المجموعة**: من السهل التحقق من وجود المجموعة عبر جدول `triples_collection`

ستكون عمليات المجموعة ذرية قدر الإمكان، وستوفر معالجة أخطاء والتحقق المناسبين.

## اعتبارات الأمان

تتطلب عمليات إدارة المجموعة تفويضًا مناسبًا لمنع الوصول غير المصرح به أو حذف المجموعات. سيتم مواءمة التحكم في الوصول مع نماذج الأمان الحالية لـ TrustGraph.

## اعتبارات الأداء

قد تتطلب عمليات سرد المجموعة الترقيم في البيئات التي تحتوي على عدد كبير من المجموعات. يجب تحسين استعلامات البيانات الوصفية للأنماط الشائعة للتصفية.

## استراتيجية الاختبار

ستغطي الاختبارات الشاملة ما يلي:
سير عمل إنشاء المجموعة من البداية إلى النهاية
مزامنة الواجهة الخلفية للتخزين
التحقق من صحة الكتابة للمجموعات غير الموجودة
معالجة الاستعلامات للمجموعات غير الموجودة
حذف المجموعة بالتتالي عبر جميع المستودعات
معالجة الأخطاء وسيناريوهات الاسترداد
اختبارات الوحدة لكل واجهة خلفية للتخزين
اختبارات التكامل للعمليات عبر المستودعات

## حالة التنفيذ

### ✅ المكونات المكتملة

1. **خدمة إدارة المجموعة Librarian** (`trustgraph-flow/trustgraph/librarian/collection_manager.py`)
   عمليات CRUD للبيانات الوصفية للمجموعة (القائمة، التحديث، الحذف)
   تكامل جدول بيانات وصفية للمجموعة في Cassandra عبر `LibraryTableStore`
   تنسيق حذف المجموعة بالتتالي عبر جميع أنواع التخزين
   معالجة الطلبات/الاستجابات غير المتزامنة مع إدارة الأخطاء المناسبة

2. **مخطط البيانات الوصفية للمجموعة** (`trustgraph-base/trustgraph/schema/services/collection.py`)
   مخططات `CollectionManagementRequest` و `CollectionManagementResponse`
   مخطط `CollectionMetadata` لسجلات المجموعة
   تعريفات موضوع قائمة انتظار الطلبات/الاستجابات للمجموعة

3. **مخطط إدارة التخزين** (`trustgraph-base/trustgraph/schema/services/storage.py`)
   مخططات `StorageManagementRequest` و `StorageManagementResponse`
   تم تعريف مواضيع قائمة انتظار إدارة التخزين
   تنسيق الرسائل لعمليات المجموعة على مستوى التخزين

4. **مخطط Cassandra المكون من 4 جداول** (`trustgraph-flow/trustgraph/direct/cassandra_kg.py`)
   مفاتيح تقسيم مركبة لأداء الاستعلام
   جدول `triples_collection` لاستعلامات SPO وتتبع الحذف
   تم تنفيذ حذف المجموعة بنمط القراءة ثم الحذف

### ✅ الترحيل إلى النمط المستند إلى التكوين - مكتمل

**تم ترحيل جميع الواجهات الخلفية للتخزين من نمط قائمة الانتظار إلى النمط المستند إلى التكوين `CollectionConfigHandler`.**

عمليات الترحيل المكتملة:
✅ `trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
✅ `trustgraph-flow/trustgraph/storage/triples/neo4j/write.py`
✅ `trustgraph-flow/trustgraph/storage/triples/memgraph/write.py`
✅ `trustgraph-flow/trustgraph/storage/triples/falkordb/write.py`
✅ `trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
✅ `trustgraph-flow/trustgraph/storage/graph_embeddings/qdrant/write.py`
✅ `trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
✅ `trustgraph-flow/trustgraph/storage/graph_embeddings/milvus/write.py`
✅ `trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`
✅ `trustgraph-flow/trustgraph/storage/graph_embeddings/pinecone/write.py`
✅ `trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`

جميع الواجهات الخلفية الآن:
ترث من `CollectionConfigHandler`
تسجيل للحصول على إشعارات دفع التكوين عبر `self.register_config_handler(self.on_collection_config)`
تنفيذ `create_collection(user, collection, metadata)` و `delete_collection(user, collection)`
استخدام `collection_exists(user, collection)` للتحقق قبل الكتابة
المزامنة التلقائية مع تغييرات خدمة التكوين

تم إزالة البنية التحتية لقائمة الانتظار القديمة:
✅ تمت إزالة مخططات `StorageManagementRequest` و `StorageManagementResponse`
✅ تمت إزالة تعريفات موضوع قائمة انتظار إدارة التخزين
✅ تمت إزالة المستهلك/المنتج لإدارة التخزين من جميع الواجهات الخلفية
✅ تمت إزالة معالجات `on_storage_management` من جميع الواجهات الخلفية
