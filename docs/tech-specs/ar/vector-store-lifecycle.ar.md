---
layout: default
title: "إدارة دورة حياة مستودع المتجهات"
parent: "Arabic (Beta)"
---

# إدارة دورة حياة مستودع المتجهات

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## نظرة عامة

يصف هذا المستند كيفية إدارة TrustGraph لمجموعات مستودعات المتجهات عبر تطبيقات خلفية مختلفة (Qdrant، Pinecone، Milvus). يعالج التصميم تحدي دعم التضمينات بأبعاد مختلفة دون ترميز قيم الأبعاد بشكل ثابت.

## بيان المشكلة

تتطلب مستودعات المتجهات تحديد بُعد التضمين عند إنشاء المجموعات/الفهارس. ومع ذلك:
تنتج نماذج التضمين المختلفة أبعادًا مختلفة (مثل 384، 768، 1536)
لا يتم معرفة البُعد حتى يتم إنشاء أول تضمين
قد تتلقى مجموعة TrustGraph واحدة تضمينات من نماذج متعددة
يؤدي ترميز بُعد (مثل 384) إلى حدوث أعطال مع أحجام تضمين أخرى

## مبادئ التصميم

1. **الإنشاء الكسول (Lazy Creation):** يتم إنشاء المجموعات عند الطلب أثناء الكتابة الأولى، وليس أثناء عمليات إدارة المجموعة.
2. **تسمية قائمة على البُعد (Dimension-Based Naming):** تتضمن أسماء المجموعات بُعد التضمين كلاحقة.
3. **التدهور السلس (Graceful Degradation):** تُرجع الاستعلامات التي تستهدف مجموعات غير موجودة نتائج فارغة، وليس أخطاء.
4. **دعم متعدد الأبعاد (Multi-Dimension Support):** يمكن أن تحتوي مجموعة منطقية واحدة على مجموعات فعلية متعددة (واحدة لكل بُعد).

## البنية

### اصطلاح تسمية المجموعة

تستخدم مجموعات مستودعات المتجهات لاحقات الأبعاد لدعم أحجام تضمين متعددة:

**تضمينات المستندات:**
Qdrant: `d_{user}_{collection}_{dimension}`
Pinecone: `d-{user}-{collection}-{dimension}`
Milvus: `doc_{user}_{collection}_{dimension}`

**تضمينات الرسم البياني:**
Qdrant: `t_{user}_{collection}_{dimension}`
Pinecone: `t-{user}-{collection}-{dimension}`
Milvus: `entity_{user}_{collection}_{dimension}`

أمثلة:
`d_alice_papers_384` - مجموعة أوراق أليس مع تضمينات ذات أبعاد 384.
`d_alice_papers_768` - نفس المجموعة المنطقية مع تضمينات ذات أبعاد 768.
`t_bob_knowledge_1536` - رسم بياني معرفة بوب مع تضمينات ذات أبعاد 1536.

### مراحل دورة الحياة

#### 1. طلب إنشاء المجموعة

**تدفق الطلب:**
```
User/System → Librarian → Storage Management Topic → Vector Stores
```

**السلوك:**
يقوم أمين المكتبة ببث طلبات `create-collection` إلى جميع أنظمة التخزين الخلفية.
تقوم معالجات مخازن المتجهات بالاعتراف بالطلب ولكن **لا تقوم بإنشاء مجموعات فعلية**.
يتم إرجاع الاستجابة على الفور مع الإشارة إلى النجاح.
يتم تأجيل إنشاء المجموعة الفعلي حتى أول عملية كتابة.

**السبب:**
الأبعاد غير معروفة في وقت الإنشاء.
يتجنب إنشاء مجموعات بأبعاد خاطئة.
يبسط منطق إدارة المجموعات.

#### 2. عمليات الكتابة (الإنشاء المؤجل)

**تدفق الكتابة:**
```
Data → Storage Processor → Check Collection → Create if Needed → Insert
```

**السلوك:**
1. استخراج بُعد التضمين من المتجه: `dim = len(vector)`
2. إنشاء اسم المجموعة مع لاحقة البُعد
3. التحقق مما إذا كانت المجموعة موجودة بهذا البُعد المحدد
4. إذا لم تكن موجودة:
   إنشاء مجموعة بالبُعد الصحيح
   تسجيل: `"Lazily creating collection {name} with dimension {dim}"`
5. إدراج التضمين في المجموعة الخاصة بالبُعد

**سيناريو مثال:**
```
1. User creates collection "papers"
   → No physical collections created yet

2. First document with 384-dim embedding arrives
   → Creates d_user_papers_384
   → Inserts data

3. Second document with 768-dim embedding arrives
   → Creates d_user_papers_768
   → Inserts data

Result: Two physical collections for one logical collection
```

#### 3. عمليات الاستعلام

**تدفق الاستعلام:**
```
Query Vector → Determine Dimension → Check Collection → Search or Return Empty
```

**السلوك:**
1. استخراج البُعد من متجه الاستعلام: `dim = len(vector)`
2. إنشاء اسم المجموعة مع لاحقة البُعد
3. التحقق مما إذا كانت المجموعة موجودة
4. إذا كانت موجودة:
   إجراء بحث عن التشابه
   إرجاع النتائج
5. إذا لم تكن موجودة:
   تسجيل: `"Collection {name} does not exist, returning empty results"`
   إرجاع قائمة فارغة (دون إثارة أي خطأ)

**أبعاد متعددة في نفس الاستعلام:**
إذا كان الاستعلام يحتوي على متجهات بأبعاد مختلفة
تستعلم كل بُعد عن المجموعة المقابلة له
يتم تجميع النتائج
يتم تخطي المجموعات المفقودة (ولا يتم التعامل معها كأخطاء)

**السبب:**
الاستعلام عن مجموعة فارغة هو حالة استخدام صالحة
إرجاع نتائج فارغة هو أمر منطقي
يتجنب الأخطاء أثناء بدء تشغيل النظام أو قبل استيعاب البيانات

#### 4. حذف المجموعة

**عملية الحذف:**
```
Delete Request → List All Collections → Filter by Prefix → Delete All Matches
```

**السلوك:**
1. إنشاء نمط البادئة: `d_{user}_{collection}_` (لاحظ الشرطة السفلية في النهاية)
2. سرد جميع المجموعات في مخزن المتجهات.
3. تصفية المجموعات التي تتطابق مع البادئة.
4. حذف جميع المجموعات المتطابقة.
5. تسجيل كل عملية حذف: `"Deleted collection {name}"`
6. سجل ملخص: `"Deleted {count} collection(s) for {user}/{collection}"`

**مثال:**
```
Collections in store:
- d_alice_papers_384
- d_alice_papers_768
- d_alice_reports_384
- d_bob_papers_384

Delete "papers" for alice:
→ Deletes: d_alice_papers_384, d_alice_papers_768
→ Keeps: d_alice_reports_384, d_bob_papers_384
```

**الأساس المنطقي:**
يضمن التنظيف الكامل لجميع المتغيرات الأبعاد.
يمنع مطابقة الأنماط الحذف العرضي للمجموعات غير المرتبطة.
عملية ذرية من وجهة نظر المستخدم (يتم حذف جميع الأبعاد معًا).

## الخصائص السلوكية

### العمليات العادية

**إنشاء المجموعة:**
✓ يُرجع النجاح على الفور.
✓ لا يتم تخصيص مساحة تخزين فعلية.
✓ عملية سريعة (لا يوجد إدخال/إخراج خلفي).

**الكتابة الأولى:**
✓ ينشئ مجموعة بالبعد الصحيح.
✓ أبطأ قليلاً بسبب تكلفة إنشاء المجموعة.
✓ عمليات الكتابة اللاحقة لنفس البعد سريعة.

**الاستعلامات قبل أي عمليات كتابة:**
✓ تُرجع نتائج فارغة.
✓ لا توجد أخطاء أو استثناءات.
✓ يظل النظام مستقرًا.

**عمليات كتابة الأبعاد المختلطة:**
✓ ينشئ تلقائيًا مجموعات منفصلة لكل بُعد.
✓ يتم عزل كل بُعد في مجموعته الخاصة.
✓ لا توجد تعارضات في الأبعاد أو أخطاء في المخطط.

**حذف المجموعة:**
✓ يزيل جميع متغيرات الأبعاد.
✓ تنظيف كامل.
✓ لا توجد مجموعات يتيمة.

### الحالات الخاصة

**نماذج تضمين متعددة:**
```
Scenario: User switches from model A (384-dim) to model B (768-dim)
Behavior:
- Both dimensions coexist in separate collections
- Old data (384-dim) remains queryable with 384-dim vectors
- New data (768-dim) queryable with 768-dim vectors
- Cross-dimension queries return results only for matching dimension
```

**الكتابات الأولية المتزامنة:**
```
Scenario: Multiple processes write to same collection simultaneously
Behavior:
- Each process checks for existence before creating
- Most vector stores handle concurrent creation gracefully
- If race condition occurs, second create is typically idempotent
- Final state: Collection exists and both writes succeed
```

**ترحيل الأبعاد:**
```
Scenario: User wants to migrate from 384-dim to 768-dim embeddings
Behavior:
- No automatic migration
- Old collection (384-dim) persists
- New collection (768-dim) created on first new write
- Both dimensions remain accessible
- Manual deletion of old dimension collections possible
```

**استعلامات المجموعة الفارغة:**
```
Scenario: Query a collection that has never received data
Behavior:
- Collection doesn't exist (never created)
- Query returns empty list
- No error state
- System logs: "Collection does not exist, returning empty results"
```

## ملاحظات حول التنفيذ

### تفاصيل حول نظام التخزين الخاص

**Qdrant:**
يستخدم `collection_exists()` للتحقق من الوجود
يستخدم `get_collections()` لعرض القائمة أثناء الحذف
يتطلب إنشاء المجموعة `VectorParams(size=dim, distance=Distance.COSINE)`

**Pinecone:**
يستخدم `has_index()` للتحقق من الوجود
يستخدم `list_indexes()` لعرض القائمة أثناء الحذف
يتطلب إنشاء الفهرس الانتظار حتى حالة "جاهز"
يتم تكوين المواصفات بدون خادم مع السحابة/المنطقة

**Milvus:**
تدير الفئات المباشرة (`DocVectors`، `EntityVectors`) دورة الحياة
ذاكرة تخزين مؤقت داخلية `self.collections[(dim, user, collection)]` للأداء
يتم تنظيف أسماء المجموعات (أحرف وأرقام وشرطة سفلية فقط)
يدعم مخططًا بمعرفات متزايدة تلقائيًا

### اعتبارات الأداء

**زمن الوصول للكتابة الأولية:**
تكلفة إضافية بسبب إنشاء المجموعة
Qdrant: ~100-500 مللي ثانية
Pinecone: ~10-30 ثانية (توفير بدون خادم)
Milvus: ~500-2000 مللي ثانية (يتضمن الفهرسة)

**أداء الاستعلام:**
يضيف التحقق من الوجود تكلفة إضافية ضئيلة (~1-10 مللي ثانية)
لا يوجد تأثير على الأداء بمجرد وجود المجموعة
يتم تحسين كل مجموعة أبعاد بشكل مستقل

**تكلفة التخزين:**
بيانات وصفية قليلة لكل مجموعة
التكلفة الرئيسية هي التخزين لكل بُعد
مقايضة: مساحة التخزين مقابل مرونة الأبعاد

## اعتبارات مستقبلية

**توحيد الأبعاد التلقائي:**
يمكن إضافة عملية خلفية لتحديد ودمج متغيرات الأبعاد غير المستخدمة
سيتطلب ذلك إعادة تضمين أو تقليل الأبعاد

**اكتشاف الأبعاد:**
يمكن تعريض واجهة برمجة تطبيقات لسرد جميع الأبعاد المستخدمة لمجموعة
مفيد للإدارة والمراقبة

**تفضيل الأبعاد الافتراضي:**
يمكن تتبع "البُعد الأساسي" لكل مجموعة
يستخدم للاستعلامات عندما يكون سياق البُعد غير متاح

**حصص التخزين:**
قد تكون هناك حاجة إلى حدود الأبعاد لكل مجموعة
يمنع الانتشار المفرط لمتغيرات الأبعاد

## ملاحظات حول الترحيل

**من نظام لاحقة الأبعاد القديم:**
المجموعات القديمة: `d_{user}_{collection}` (بدون لاحقة البُعد)
المجموعات الجديدة: `d_{user}_{collection}_{dim}` (مع لاحقة البُعد)
لا يوجد ترحيل تلقائي - تظل المجموعات القديمة قابلة للوصول
ضع في اعتبارك برنامج ترحيل يدوي إذا لزم الأمر
يمكن تشغيل كلا نظامي التسمية في وقت واحد

## المراجع

إدارة المجموعات: `docs/tech-specs/collection-management.md`
مخطط التخزين: `trustgraph-base/trustgraph/schema/services/storage.py`
خدمة أمين المكتبة: `trustgraph-flow/trustgraph/librarian/service.py`
