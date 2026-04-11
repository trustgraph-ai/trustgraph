# GraphQL Query Technical Specification

## Overview

<<<<<<< HEAD
تصف هذه المواصفات تنفيذ واجهة استعلام GraphQL للبيانات المنظمة المخزنة في Apache Cassandra. بناءً على إمكانات البيانات المنظمة الموضحة في المواصفات الموجودة في structured-data.md، يوضح هذا المستند كيفية تنفيذ استعلامات GraphQL على جداول Cassandra التي تحتوي على كائنات منظمة مستخرجة ومُدخلة.

سيوفر خدمة استعلام GraphQL واجهة مرنة وآمنة من حيث النوع للاستعلام عن البيانات المنظمة المخزنة في Cassandra. ستتكيف ديناميكيًا مع تغييرات المخطط، وتدعم الاستعلامات المعقدة بما في ذلك العلاقات بين الكائنات، وتتكامل بسلاسة مع بنية TrustGraph الحالية القائمة على الرسائل.

## الأهداف

**دعم المخططات الديناميكي**: التكيف تلقائيًا مع تغييرات المخطط في التكوين دون إعادة تشغيل الخدمة.
**الامتثال لمعايير GraphQL**: توفير واجهة GraphQL قياسية متوافقة مع أدوات GraphQL والعملاء الحاليين.
**استعلامات Cassandra فعالة**: ترجمة استعلامات GraphQL إلى استعلامات Cassandra CQL فعالة مع احترام مفاتيح التقسيم والفهارس.
**حل العلاقات**: دعم محللات الحقول GraphQL للعلاقات بين أنواع الكائنات المختلفة.
**الأمان من حيث النوع**: ضمان تنفيذ الاستعلامات وتوليد الاستجابات بطريقة آمنة من حيث النوع بناءً على تعريفات المخطط.
**أداء قابل للتوسع**: التعامل مع الاستعلامات المتزامنة بكفاءة مع تجميع الاتصالات وتحسين الاستعلامات المناسب.
**التكامل مع الطلبات والاستجابات**: الحفاظ على التوافق مع نمط الطلب/الاستجابة القائم على Pulsar في TrustGraph.
**معالجة الأخطاء**: توفير تقارير أخطاء شاملة لمطابقة المخططات وأخطاء الاستعلامات ومشكلات التحقق من صحة البيانات.

## الخلفية

تقوم عملية تخزين البيانات المنظمة (trustgraph-flow/trustgraph/storage/objects/cassandra/) بكتابة الكائنات إلى جداول Cassandra بناءً على تعريفات المخطط المخزنة في نظام تكوين TrustGraph. تستخدم هذه الجداول هيكل مفتاح تقسيم مركب مع مفاتيح أولية محددة في المجموعة ومحددة في المخطط، مما يتيح استعلامات فعالة داخل المجموعات.

القيود الحالية التي تعالجها هذه المواصفات:
لا توجد واجهة استعلام للبيانات المنظمة المخزنة في Cassandra.
عدم القدرة على الاستفادة من إمكانات الاستعلام القوية لـ GraphQL للبيانات المنظمة.
عدم وجود دعم لتتبع العلاقات بين الكائنات ذات الصلة.
عدم وجود لغة استعلام موحدة للوصول إلى البيانات المنظمة.

ستقوم خدمة استعلام GraphQL بسد هذه الفجوات من خلال:
توفير واجهة GraphQL قياسية للاستعلام عن جداول Cassandra.
توليد مخططات GraphQL ديناميكيًا من تكوين TrustGraph.
ترجمة استعلامات GraphQL بكفاءة إلى Cassandra CQL.
دعم حل العلاقات من خلال محللات الحقول.

## التصميم الفني

### البنية

سيتم تنفيذ خدمة استعلام GraphQL كمعالج TrustGraph جديد باتباع الأنماط الراسخة:

**الموقع**: `trustgraph-flow/trustgraph/query/objects/cassandra/`

**المكونات الرئيسية**:

1. **معالج خدمة استعلام GraphQL**:
   يرث من الفئة الأساسية FlowProcessor.
   ينفذ نمط الطلب/الاستجابة المشابه لخدمات الاستعلام الحالية.
   يراقب التكوين بحثًا عن تحديثات المخطط.
   يحافظ على تزامن مخطط GraphQL مع التكوين.

2. **مولد المخططات الديناميكي**:
   يحول تعريفات TrustGraph RowSchema إلى أنواع GraphQL.
   ينشئ أنواع كائنات GraphQL مع تعريفات الحقول المناسبة.
   يولد نوع الاستعلام الجذر مع محللات قائمة على المجموعة.
   يقوم بتحديث مخطط GraphQL عند حدوث تغييرات في التكوين.

3. **منفذ الاستعلام**:
   يحلل استعلامات GraphQL الواردة باستخدام مكتبة Strawberry.
   يتحقق من صحة الاستعلامات مقابل المخطط الحالي.
   ينفذ الاستعلامات ويعيد استجابات منظمة.
   يتعامل مع الأخطاء بأمان مع رسائل خطأ مفصلة.

4. **مترجم استعلامات Cassandra**:
   يحول عمليات اختيار GraphQL إلى استعلامات CQL.
   يحسن الاستعلامات بناءً على الفهارس ومفاتيح التقسيم المتاحة.
   يتعامل مع التصفية والتقسيم والترتيب.
   يدير تجميع الاتصالات ودورة حياة الجلسة.

5. **محلل العلاقات**:
   ينفذ محللات الحقول للعلاقات بين الكائنات.
   يقوم بتحميل دفعات بكفاءة لتجنب استعلامات N+1.
   يقوم بتخزين العلاقات التي تم حلها في سياق الطلب.
   يدعم كل من تتبع العلاقات الأمامية والعكسية.

### مراقبة مخطط التكوين

ستقوم الخدمة بتسجيل معالج تكوين لتلقي تحديثات المخطط:
=======
This specification describes the implementation of a GraphQL query interface for TrustGraph's structured data storage in Apache Cassandra. Building upon the structured data capabilities outlined in the structured-data.md specification, this document details how GraphQL queries will be executed against Cassandra tables containing extracted and ingested structured objects.

The GraphQL query service will provide a flexible, type-safe interface for querying structured data stored in Cassandra. It will dynamically adapt to schema changes, support complex queries including relationships between objects, and integrate seamlessly with TrustGraph's existing message-based architecture.

## Goals

**Dynamic Schema Support**: Automatically adapt to schema changes in configuration without service restarts
**GraphQL Standards Compliance**: Provide a standard GraphQL interface compatible with existing GraphQL tooling and clients
**Efficient Cassandra Queries**: Translate GraphQL queries into efficient Cassandra CQL queries respecting partition keys and indexes
**Relationship Resolution**: Support GraphQL field resolvers for relationships between different object types
**Type Safety**: Ensure type-safe query execution and response generation based on schema definitions
**Scalable Performance**: Handle concurrent queries efficiently with proper connection pooling and query optimization
**Request/Response Integration**: Maintain compatibility with TrustGraph's Pulsar-based request/response pattern
**Error Handling**: Provide comprehensive error reporting for schema mismatches, query errors, and data validation issues

## Background

The structured data storage implementation (trustgraph-flow/trustgraph/storage/objects/cassandra/) writes objects to Cassandra tables based on schema definitions stored in TrustGraph's configuration system. These tables use a composite partition key structure with collection and schema-defined primary keys, enabling efficient queries within collections.

Current limitations that this specification addresses:
No query interface for the structured data stored in Cassandra
Inability to leverage GraphQL's powerful query capabilities for structured data
Missing support for relationship traversal between related objects
Lack of a standardized query language for structured data access

The GraphQL query service will bridge these gaps by:
Providing a standard GraphQL interface for querying Cassandra tables
Dynamically generating GraphQL schemas from TrustGraph configuration
Efficiently translating GraphQL queries to Cassandra CQL
Supporting relationship resolution through field resolvers

## Technical Design

### Architecture

The GraphQL query service will be implemented as a new TrustGraph flow processor following established patterns:

**Module Location**: `trustgraph-flow/trustgraph/query/objects/cassandra/`

**Key Components**:

1. **GraphQL Query Service Processor**
   Extends base FlowProcessor class
   Implements request/response pattern similar to existing query services
   Monitors configuration for schema updates
   Maintains GraphQL schema synchronized with configuration

2. **Dynamic Schema Generator**
   Converts TrustGraph RowSchema definitions to GraphQL types
   Creates GraphQL object types with proper field definitions
   Generates root Query type with collection-based resolvers
   Updates GraphQL schema when configuration changes

3. **Query Executor**
   Parses incoming GraphQL queries using Strawberry library
   Validates queries against current schema
   Executes queries and returns structured responses
   Handles errors gracefully with detailed error messages

4. **Cassandra Query Translator**
   Converts GraphQL selections to CQL queries
   Optimizes queries based on available indexes and partition keys
   Handles filtering, pagination, and sorting
   Manages connection pooling and session lifecycle

5. **Relationship Resolver**
   Implements field resolvers for object relationships
   Performs efficient batch loading to avoid N+1 queries
   Caches resolved relationships within request context
   Supports both forward and reverse relationship traversal

### Configuration Schema Monitoring

The service will register a configuration handler to receive schema updates:
>>>>>>> 82edf2d (New md files from RunPod)

```python
self.register_config_handler(self.on_schema_config)
```

عندما تتغير المخططات:
1. تحليل تعريفات المخططات الجديدة من التكوين.
2. إعادة إنشاء أنواع GraphQL والمحللات.
<<<<<<< HEAD
3. تحديث المخطط القابل للتنفيذ.
=======
3. تحديث المخطط التنفيذي.
>>>>>>> 82edf2d (New md files from RunPod)
4. مسح أي ذاكرة تخزين مؤقت تعتمد على المخطط.

### توليد مخطط GraphQL

لكل RowSchema في التكوين، قم بإنشاء:

1. **نوع كائن GraphQL**:
<<<<<<< HEAD
   مطابقة أنواع الحقول (string → String, integer → Int, float → Float, boolean → Boolean).
=======
   تعيين أنواع الحقول (string → String, integer → Int, float → Float, boolean → Boolean).
>>>>>>> 82edf2d (New md files from RunPod)
   وضع علامة على الحقول المطلوبة على أنها غير قابلة للقيم الفارغة في GraphQL.
   إضافة أوصاف الحقول من المخطط.

2. **حقول الاستعلام الجذرية**:
   استعلام المجموعة (مثل `customers`، `transactions`).
   وسائط التصفية بناءً على الحقول المفهرسة.
   دعم التقسيم (limit, offset).
   خيارات الفرز للحقول القابلة للفرز.

3. **حقول العلاقات**:
   تحديد علاقات المفاتيح الخارجية من المخطط.
   إنشاء محللات حقول للكائنات ذات الصلة.
   دعم كل من علاقات الكائنات الفردية وقوائم الكائنات.

### تدفق تنفيذ الاستعلام

1. **استقبال الطلب**:
   استقبال ObjectsQueryRequest من Pulsar.
   استخراج سلسلة استعلام GraphQL والمتغيرات.
   تحديد سياق المستخدم والمجموعة.

2. **التحقق من صحة الاستعلام**:
   تحليل استعلام GraphQL باستخدام Strawberry.
   التحقق من الصحة مقابل المخطط الحالي.
   التحقق من عمليات اختيار الحقول وأنواع الوسائط.

3. **توليد CQL**:
   تحليل عمليات اختيار GraphQL.
   إنشاء استعلام CQL مع عبارات WHERE المناسبة.
   تضمين المجموعة في مفتاح التقسيم.
   تطبيق عوامل التصفية بناءً على وسائط GraphQL.

4. **تنفيذ الاستعلام**:
   تنفيذ استعلام CQL مقابل Cassandra.
<<<<<<< HEAD
   مطابقة النتائج مع هيكل استجابة GraphQL.
=======
   تعيين النتائج إلى هيكل استجابة GraphQL.
>>>>>>> 82edf2d (New md files from RunPod)
   حل أي حقول علاقات.
   تنسيق الاستجابة وفقًا لمواصفات GraphQL.

5. **تسليم الاستجابة**:
   إنشاء ObjectsQueryResponse مع النتائج.
   تضمين أي أخطاء في التنفيذ.
   إرسال الاستجابة عبر Pulsar بمعرف الارتباط.

### نماذج البيانات

<<<<<<< HEAD
> **ملاحظة**: يوجد مخطط StructuredQueryRequest/Response موجود في `trustgraph-base/trustgraph/schema/services/structured_query.py`. ومع ذلك، فإنه يفتقر إلى حقول مهمة (المستخدم، المجموعة) ويستخدم أنواعًا دون المستوى الأمثل. تمثل المخططات أدناه التطور الموصى به، والتي يجب إما أن تحل محل المخططات الحالية أو يتم إنشاؤها كأنواع ObjectsQueryRequest/Response جديدة.
=======
> **ملاحظة**: يوجد مخطط StructuredQueryRequest/Response موجود في `trustgraph-base/trustgraph/schema/services/structured_query.py`. ومع ذلك، فإنه يفتقر إلى حقول مهمة (المستخدم، المجموعة) ويستخدم أنواعًا دون المستوى الأمثل. تمثل المخططات أدناه التطور الموصى به، والتي يجب إما استبدال المخططات الموجودة بها أو إنشاؤها كأنواع ObjectsQueryRequest/Response جديدة.
>>>>>>> 82edf2d (New md files from RunPod)

#### مخطط الطلب (ObjectsQueryRequest)

```python
from pulsar.schema import Record, String, Map, Array

class ObjectsQueryRequest(Record):
    user = String()              # Cassandra keyspace (follows pattern from TriplesQueryRequest)
    collection = String()        # Data collection identifier (required for partition key)
    query = String()             # GraphQL query string
    variables = Map(String())    # GraphQL variables (consider enhancing to support all JSON types)
    operation_name = String()    # Operation to execute for multi-operation documents
```

**السبب وراء التغييرات من طلب الاستعلام المنظم الحالي:**
تمت إضافة الحقول `user` و `collection` لمطابقة نمط خدمات الاستعلام الأخرى.
هذه الحقول ضرورية لتحديد مساحة مفاتيح Cassandra والمجموعة.
تظل المتغيرات كـ Map(String()) في الوقت الحالي، ولكن من الأفضل أن تدعم جميع أنواع JSON.

#### مخطط الاستجابة (ObjectsQueryResponse)

```python
from pulsar.schema import Record, String, Array
from ..core.primitives import Error

class GraphQLError(Record):
    message = String()
    path = Array(String())       # Path to the field that caused the error
    extensions = Map(String())   # Additional error metadata

class ObjectsQueryResponse(Record):
    error = Error()              # System-level error (connection, timeout, etc.)
    data = String()              # JSON-encoded GraphQL response data
    errors = Array(GraphQLError) # GraphQL field-level errors
    extensions = Map(String())   # Query metadata (execution time, etc.)
```

**الأساس المنطقي للتغييرات من الاستجابة المنظمة للاستعلامات الحالية:**
التمييز بين أخطاء النظام (`error`) وأخطاء GraphQL (`errors`).
استخدام كائنات GraphQLError منظمة بدلاً من مصفوفة سلسلة.
إضافة حقل `extensions` للامتثال لمواصفات GraphQL.
الحفاظ على البيانات كسلسلة JSON للتوافق، على الرغم من أن الأنواع الأصلية ستكون مفضلة.

### تحسين استعلامات Cassandra

ستقوم الخدمة بتحسين استعلامات Cassandra عن طريق:

1. **احترام مفاتيح التقسيم:**
   تضمين المجموعة دائمًا في الاستعلامات.
   استخدام المفاتيح الأساسية المعرفة في المخطط بكفاءة.
   تجنب عمليات المسح الكاملة للجدول.

2. **الاستفادة من الفهارس:**
   استخدام الفهارس الثانوية للتصفية.
   دمج عوامل التصفية المتعددة كلما أمكن ذلك.
<<<<<<< HEAD
   التحذير عندما قد تكون الاستعلامات غير فعالة.

3. **التحميل الدفعي:**
   جمع استعلامات العلاقات.
=======
   إصدار تحذير عندما قد تكون الاستعلامات غير فعالة.

3. **التحميل الدفعي:**
   تجميع استعلامات العلاقات.
>>>>>>> 82edf2d (New md files from RunPod)
   تنفيذها على دفعات لتقليل عدد الرحلات ذهابًا وإيابًا.
   تخزين النتائج مؤقتًا داخل سياق الطلب.

4. **إدارة الاتصالات:**
   الحفاظ على جلسات Cassandra مستمرة.
   استخدام تجميع الاتصالات.
<<<<<<< HEAD
   التعامل مع إعادة الاتصال في حالة حدوث أخطاء.
=======
   التعامل مع إعادة الاتصال في حالة حدوث أعطال.
>>>>>>> 82edf2d (New md files from RunPod)

### أمثلة لاستعلامات GraphQL

#### استعلام بسيط للمجموعة
```graphql
{
  customers(status: "active") {
    customer_id
    name
    email
    registration_date
  }
}
```

#### استعلام مع العلاقات
```graphql
{
  orders(order_date_gt: "2024-01-01") {
    order_id
    total_amount
    customer {
      name
      email
    }
    items {
      product_name
      quantity
      price
    }
  }
}
```

#### استعلام مُقسّم إلى صفحات
```graphql
{
  products(limit: 20, offset: 40) {
    product_id
    name
    price
    category
  }
}
```

### الاعتمادات الخاصة بالتنفيذ

**Strawberry GraphQL**: لتعريف مخطط GraphQL وتنفيذ الاستعلامات.
**Cassandra Driver**: للاتصال بقاعدة البيانات (يتم استخدامه بالفعل في وحدة التخزين).
**TrustGraph Base**: لـ FlowProcessor وتعريفات المخططات.
**Configuration System**: لمراقبة المخططات وتحديثها.

### واجهة سطر الأوامر

سيوفر الخدمة أمر سطر أوامر: `kg-query-objects-graphql-cassandra`

الوسائط:
`--cassandra-host`: نقطة اتصال مجموعة Cassandra.
`--cassandra-username`: اسم مستخدم المصادقة.
`--cassandra-password`: كلمة مرور المصادقة.
`--config-type`: نوع التكوين للمخططات (افتراضي: "schema").
وسائط FlowProcessor القياسية (تكوين Pulsar، إلخ).

## تكامل واجهة برمجة التطبيقات

### مواضيع Pulsar

**موضوع الإدخال**: `objects-graphql-query-request`
المخطط: ObjectsQueryRequest
يتلقى استعلامات GraphQL من خدمات البوابة.

**موضوع الإخراج**: `objects-graphql-query-response`
المخطط: ObjectsQueryResponse
يُرجع نتائج الاستعلام والأخطاء.

### تكامل البوابة

ستحتاج البوابة والبوابة العكسية إلى نقاط نهاية لـ:
1. قبول استعلامات GraphQL من العملاء.
2. توجيهها إلى خدمة الاستعلام عبر Pulsar.
3. إرجاع الاستجابات إلى العملاء.
<<<<<<< HEAD
4. دعم استعلامات GraphQL الخاصة بالتحقق من المخطط.
=======
4. دعم استعلامات GraphQL الخاصة بالتحقق (introspection).
>>>>>>> 82edf2d (New md files from RunPod)

### تكامل أداة الوكيل

ستتيح فئة أداة وكيل جديدة:
توليد استعلامات GraphQL من اللغة الطبيعية.
تنفيذ استعلامات GraphQL مباشرة.
<<<<<<< HEAD
تفسير وتنسيق النتائج.
التكامل مع مسارات قرار الوكيل.
=======
تفسير النتائج وتنسيقها.
التكامل مع تدفقات قرار الوكيل.
>>>>>>> 82edf2d (New md files from RunPod)

## اعتبارات الأمان

**تحديد عمق الاستعلام**: منع الاستعلامات المتداخلة بعمق والتي يمكن أن تسبب مشاكل في الأداء.
<<<<<<< HEAD
**تحليل تعقيد الاستعلام**: الحد من تعقيد الاستعلام لمنع استنفاد الموارد.
**أذونات على مستوى الحقل**: دعم مستقبلي للتحكم في الوصول على مستوى الحقل بناءً على أدوار المستخدم.
**تنظيف الإدخال**: التحقق من صحة وتنظيف جميع مدخلات الاستعلام لمنع هجمات الحقن.
**تحديد المعدل**: تنفيذ تحديد معدل الاستعلام لكل مستخدم/مجموعة.
=======
**تحليل تعقيد الاستعلام**: تحديد تعقيد الاستعلام لمنع استنفاد الموارد.
**أذونات على مستوى الحقل**: دعم مستقبلي للتحكم في الوصول على مستوى الحقل بناءً على أدوار المستخدم.
**تنظيف الإدخال**: التحقق من صحة وتنظيف جميع مدخلات الاستعلام لمنع هجمات الحقن.
**تحديد المعدل**: تطبيق تحديد معدل الاستعلام لكل مستخدم/مجموعة.
>>>>>>> 82edf2d (New md files from RunPod)

## اعتبارات الأداء

**تخطيط الاستعلام**: تحليل الاستعلامات قبل التنفيذ لتحسين توليد CQL.
**تخزين النتائج مؤقتًا**: ضع في اعتبارك تخزين البيانات التي يتم الوصول إليها بشكل متكرر مؤقتًا على مستوى محلل الحقل.
<<<<<<< HEAD
**تجميع الاتصالات**: حافظ على مجموعات اتصالات فعالة إلى Cassandra.
=======
**تجميع الاتصالات**: حافظ على تجمعات اتصالات فعالة إلى Cassandra.
>>>>>>> 82edf2d (New md files from RunPod)
**العمليات الدفعية**: اجمع بين استعلامات متعددة كلما أمكن ذلك لتقليل زمن الوصول.
**المراقبة**: تتبع مقاييس أداء الاستعلام لتحسين الأداء.

## استراتيجية الاختبار

### اختبارات الوحدة
توليد المخططات من تعريفات RowSchema
تحليل وتدقيق استعلامات GraphQL
منطق توليد استعلامات CQL
تطبيقات محللات الحقول

### اختبارات العقود
الامتثال لعقد رسائل Pulsar
صلاحية مخطط GraphQL
التحقق من تنسيق الاستجابة
التحقق من صحة هيكل الأخطاء

### اختبارات التكامل
<<<<<<< HEAD
تنفيذ استعلامات شاملة مقابل نسخة اختبار Cassandra
=======
تنفيذ الاستعلامات من طرف إلى طرف مقابل مثيل Cassandra للاختبار
>>>>>>> 82edf2d (New md files from RunPod)
معالجة تحديثات المخططات
حل العلاقات
الترقيم والتصفية
سيناريوهات الأخطاء

### اختبارات الأداء
معدل نقل البيانات للاستعلامات تحت الضغط
وقت الاستجابة لتعقيدات الاستعلامات المختلفة
استخدام الذاكرة مع مجموعات نتائج كبيرة
كفاءة مجموعة الاتصالات

## خطة الترحيل

لا يلزم إجراء أي ترحيل نظرًا لأن هذا ميزة جديدة. ستقوم الخدمة بما يلي:
1. قراءة المخططات الموجودة من التكوين
2. الاتصال بجداول Cassandra الموجودة التي تم إنشاؤها بواسطة وحدة التخزين
3. البدء في قبول الاستعلامات على الفور عند النشر

## الجدول الزمني

الأسبوع 1-2: تنفيذ الخدمة الأساسية وتوليد المخططات
الأسبوع 3: تنفيذ الاستعلامات وترجمة CQL
الأسبوع 4: حل العلاقات والتحسين
الأسبوع 5: الاختبار وضبط الأداء
الأسبوع 6: التكامل مع البوابة والتوثيق

## أسئلة مفتوحة

1. **تطور المخططات**: كيف يجب أن تتعامل الخدمة مع الاستعلامات أثناء عمليات انتقال المخططات؟
   خيار: وضع الاستعلامات في قائمة انتظار أثناء تحديثات المخططات
   خيار: دعم إصدارات متعددة من المخططات في نفس الوقت

2. **استراتيجية التخزين المؤقت**: هل يجب تخزين نتائج الاستعلامات مؤقتًا؟
   ضع في اعتبارك: انتهاء الصلاحية بناءً على الوقت
   ضع في اعتبارك: الإبطال بناءً على الأحداث

3. **دعم التجميع**: هل يجب أن تدعم الخدمة تجميع GraphQL لدمجها مع مصادر بيانات أخرى؟
<<<<<<< HEAD
   سيمكن ذلك من إجراء استعلامات موحدة عبر البيانات المهيكلة والبيانات الرسومية
=======
   سيمكن ذلك من الاستعلامات الموحدة عبر البيانات المهيكلة والبيانات الرسومية
>>>>>>> 82edf2d (New md files from RunPod)

4. **دعم الاشتراكات**: هل يجب أن تدعم الخدمة اشتراكات GraphQL للتحديثات في الوقت الفعلي؟
   سيتطلب ذلك دعم WebSocket في البوابة

<<<<<<< HEAD
5. **أنواع قياسية مخصصة**: هل يجب دعم الأنواع القياسية المخصصة لأنواع البيانات الخاصة بالمجال؟
=======
5. **الأنواع العددية المخصصة**: هل يجب دعم الأنواع العددية المخصصة لأنواع البيانات الخاصة بالمجال؟
>>>>>>> 82edf2d (New md files from RunPod)
   أمثلة: DateTime، UUID، حقول JSON

## المراجع

المواصفات الفنية للبيانات المهيكلة: `docs/tech-specs/structured-data.md`
<<<<<<< HEAD
وثائق GraphQL Strawberry: https://strawberry.rocks/
=======
وثائق Strawberry GraphQL: https://strawberry.rocks/
>>>>>>> 82edf2d (New md files from RunPod)
مواصفات GraphQL: https://spec.graphql.org/
مرجع Apache Cassandra CQL: https://cassandra.apache.org/doc/stable/cassandra/cql/
وثائق معالج التدفق TrustGraph: وثائق داخلية