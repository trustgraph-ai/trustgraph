# المواصفات الفنية: دعم البيئات متعددة المستأجرين

## نظرة عامة

تمكين عمليات النشر متعددة المستأجرين عن طريق إصلاح عدم تطابق أسماء المعلمات التي تمنع تخصيص قائمة الانتظار وإضافة معلمات مساحة مفاتيح Cassandra.

## سياق البنية

### حل قائمة الانتظار القائم على التدفق

يستخدم نظام TrustGraph بنية **قائمة انتظار قائمة على التدفق** لحل ديناميكي لقوائم الانتظار، والتي تدعم بشكل طبيعي البيئات متعددة المستأجرين:

يتم تخزين **تعريفات التدفق** في Cassandra وتحدد أسماء قوائم الانتظار عبر تعريفات الواجهة.
**تستخدم أسماء قوائم الانتظار قوالب** مع متغيرات `{id}` يتم استبدالها بمعرفات مثيلات التدفق.
**تقوم الخدمات بحل قوائم الانتظار ديناميكيًا** عن طريق البحث عن تكوينات التدفق في وقت الطلب.
**يمكن لكل مستأجر أن يكون لديه تدفقات فريدة** بأسماء قوائم انتظار مختلفة، مما يوفر عزلًا.

مثال لتعريف واجهة التدفق:
```json
{
  "interfaces": {
    "triples-store": "persistent://tg/flow/triples-store:{id}",
    "graph-embeddings-store": "persistent://tg/flow/graph-embeddings-store:{id}"
  }
}
```

عندما يبدأ المستأجر أ سير العمل `tenant-a-prod` ويبدأ المستأجر ب سير العمل `tenant-b-prod`، فإنهم يحصلون تلقائيًا على قوائم انتظار معزولة:
`persistent://tg/flow/triples-store:tenant-a-prod`
`persistent://tg/flow/triples-store:tenant-b-prod`

**الخدمات المصممة بشكل صحيح لدعم تعدد المستأجرين:**
✅ **إدارة المعرفة (الأساسيات)** - تحل ديناميكيًا قوائم الانتظار من تكوين سير العمل الذي يتم تمريره في الطلبات.

**الخدمات التي تحتاج إلى إصلاحات:**
🔴 **خدمة التكوين** - عدم تطابق اسم المعلمة يمنع تخصيص قائمة الانتظار.
🔴 **خدمة أمين المكتبة** - مواضيع إدارة التخزين المبرمجة بشكل ثابت (موضحة أدناه).
🔴 **جميع الخدمات** - لا يمكن تخصيص مساحة مفتاح Cassandra.

## بيان المشكلة

### المشكلة رقم 1: عدم تطابق اسم المعلمة في AsyncProcessor
**يعرف سطر الأوامر:** `--config-queue` (تسمية غير واضحة)
**يقوم Argparse بتحويلها إلى:** `config_queue` (في قاموس المعلمات)
**يبحث الكود عن:** `config_push_queue`
**النتيجة:** يتم تجاهل المعلمة، وتعود إلى القيمة الافتراضية `persistent://tg/config/config`.
**التأثير:** يؤثر على أكثر من 32 خدمة ترث من AsyncProcessor.
**يمنع:** لا يمكن لنشر تعدد المستأجرين استخدام قوائم انتظار تكوين خاصة بالمستأجر.
**الحل:** إعادة تسمية معلمة سطر الأوامر إلى `--config-push-queue` من أجل الوضوح (تغيير كاسر مقبول نظرًا لأن الميزة معطلة حاليًا).

### المشكلة رقم 2: عدم تطابق اسم المعلمة في خدمة التكوين
**يعرف سطر الأوامر:** `--push-queue` (تسمية غامضة)
**يقوم Argparse بتحويلها إلى:** `push_queue` (في قاموس المعلمات)
**يبحث الكود عن:** `config_push_queue`
**النتيجة:** يتم تجاهل المعلمة.
**التأثير:** لا يمكن لخدمة التكوين استخدام قائمة انتظار دفع مخصصة.
**الحل:** إعادة تسمية معلمة سطر الأوامر إلى `--config-push-queue` من أجل الاتساق والوضوح (تغيير كاسر مقبول).

### المشكلة رقم 3: مساحة مفتاح Cassandra مبرمجة بشكل ثابت
**الحالي:** مساحة المفتاح مبرمجة بشكل ثابت كـ `"config"`، `"knowledge"`، `"librarian"` في خدمات مختلفة.
**النتيجة:** لا يمكن تخصيص مساحة المفتاح لنشر تعدد المستأجرين.
**التأثير:** خدمات التكوين والأساسيات وأمين المكتبة.
**يمنع:** لا يمكن لعدة مستأجرين استخدام مساحات مفاتيح Cassandra منفصلة.

### المشكلة رقم 4: بنية إدارة المجموعات ✅ مكتمل
**السابق:** تم تخزين المجموعات في مساحة مفاتيح Cassandra الخاصة بأمين المكتبة عبر جدول مجموعات منفصل.
**السابق:** استخدم أمين المكتبة 4 مواضيع إدارة تخزين مبرمجة بشكل ثابت لتنسيق إنشاء/حذف المجموعة:
  `vector_storage_management_topic`
  `object_storage_management_topic`
  `triples_storage_management_topic`
  `storage_management_response_topic`
**المشاكل (تم حلها):**
  لا يمكن تخصيص المواضيع المبرمجة بشكل ثابت لنشر تعدد المستأجرين.
  تنسيق غير متزامن معقد بين أمين المكتبة و 4+ خدمات تخزين.
  جدول منفصل وبنية تحتية لإدارة.
  قوائم انتظار طلب/استجابة غير دائمة للعمليات الهامة.
**الحل المنفذ:** تم نقل المجموعات إلى تخزين خدمة التكوين، واستخدام دفع التكوين للتوزيع.
**الحالة:** تم نقل جميع خلفيات التخزين إلى النمط `CollectionConfigHandler`.

## الحل

تعالج هذه المواصفات المشكلات رقم 1 و 2 و 3 و 4.

### الجزء الأول: إصلاح عدم تطابق اسم المعلمة

#### التغيير 1: فئة AsyncProcessor الأساسية - إعادة تسمية معلمة سطر الأوامر
**الملف:** `trustgraph-base/trustgraph/base/async_processor.py`
**السطر:** 260-264

**الحالي:**
```python
parser.add_argument(
    '--config-queue',
    default=default_config_queue,
    help=f'Config push queue {default_config_queue}',
)
```

**ثابت:**
```python
parser.add_argument(
    '--config-push-queue',
    default=default_config_queue,
    help=f'Config push queue (default: {default_config_queue})',
)
```

**السبب:**
تسمية أوضح وأكثر تفصيلاً.
تتطابق مع اسم المتغير الداخلي `config_push_queue`.
التغيير قد يكون مؤثراً، ولكن هذا مقبول لأن الميزة غير فعالة حاليًا.
لا حاجة لتغيير أي كود في `params.get()` - فهو يبحث بالفعل عن الاسم الصحيح.

#### التغيير الثاني: خدمة التكوين - إعادة تسمية معلمة سطر الأوامر
**الملف:** `trustgraph-flow/trustgraph/config/service/service.py`
**السطر:** 276-279

**الحالي:**
```python
parser.add_argument(
    '--push-queue',
    default=default_config_push_queue,
    help=f'Config push queue (default: {default_config_push_queue})'
)
```

**ثابت:**
```python
parser.add_argument(
    '--config-push-queue',
    default=default_config_push_queue,
    help=f'Config push queue (default: {default_config_push_queue})'
)
```

**السبب:**
تسمية أوضح - "config-push-queue" أكثر وضوحًا من مجرد "push-queue".
يتطابق مع اسم المتغير الداخلي `config_push_queue`.
متسق مع معلمة `--config-push-queue` الخاصة بـ AsyncProcessor.
التغيير غير المتوافق مقبول نظرًا لأن الميزة غير وظيفية حاليًا.
لا حاجة لتغيير التعليمات البرمجية في params.get() - فهو يبحث بالفعل عن الاسم الصحيح.

### الجزء الثاني: إضافة معلمات مساحة مفاتيح Cassandra

#### التغيير الثالث: إضافة معلمة مساحة المفاتيح إلى وحدة cassandra_config
**الملف:** `trustgraph-base/trustgraph/base/cassandra_config.py`

**إضافة وسيط سطر الأوامر** (في دالة `add_cassandra_args()`):
```python
parser.add_argument(
    '--cassandra-keyspace',
    default=None,
    help='Cassandra keyspace (default: service-specific)'
)
```

**إضافة دعم لمتغيرات البيئة** (في الدالة `resolve_cassandra_config()`):
```python
keyspace = params.get(
    "cassandra_keyspace",
    os.environ.get("CASSANDRA_KEYSPACE")
)
```

**تحديث قيمة الإرجاع** لـ `resolve_cassandra_config()`:
حاليًا، تُرجع: `(hosts, username, password)`
التغيير إلى إرجاع: `(hosts, username, password, keyspace)`

**السبب:**
يتوافق مع نمط تكوين Cassandra الحالي
متاح لجميع الخدمات عبر `add_cassandra_args()`
يدعم كل من تكوين سطر الأوامر ومتغيرات البيئة

#### التغيير الرابع: خدمة التكوين - استخدام مفاتيح مساحة المفاتيح المعلمة
**الملف:** `trustgraph-flow/trustgraph/config/service/service.py`

**السطر 30** - إزالة اسم مساحة المفاتيح الثابت:
```python
# DELETE THIS LINE:
keyspace = "config"
```

**السطور من 69 إلى 73** - تحديث آلية حل مشاكل إعدادات كاساندرا:

**الحالي:**
```python
cassandra_host, cassandra_username, cassandra_password = \
    resolve_cassandra_config(params)
```

**ثابت:**
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="config")
```

**السبب:**
يحافظ على التوافق مع الإصدارات السابقة باستخدام "config" كإعداد افتراضي.
يسمح بالتجاوز عبر `--cassandra-keyspace` أو `CASSANDRA_KEYSPACE`.

#### التغيير 5: الخدمات الأساسية/خدمة المعرفة - استخدام مفاتيح مساحة معلمات.
**الملف:** `trustgraph-flow/trustgraph/cores/service.py`

**السطر 37** - إزالة مفتاح مساحة مُبرمج بشكل ثابت:
```python
# DELETE THIS LINE:
keyspace = "knowledge"
```

**تحديث آلية حل إعدادات كاساندرا** (في نفس الموقع مثل خدمة الإعدادات):
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="knowledge")
```

#### التغيير 6: خدمة أمين المكتبة - استخدام مفاتيح مساحة معلمات.
**الملف:** `trustgraph-flow/trustgraph/librarian/service.py`

**السطر 51** - إزالة اسم مساحة المفاتيح المبرمج بشكل ثابت:
```python
# DELETE THIS LINE:
keyspace = "librarian"
```

**تحديث آلية حل إعدادات Cassandra** (في نفس الموقع مثل خدمة الإعدادات):
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="librarian")
```

### الجزء الثالث: ترحيل إدارة المجموعات إلى خدمة التكوين

#### نظرة عامة
ترحيل المجموعات من مساحة مفاتيح Cassandra librarian إلى تخزين خدمة التكوين. هذا يلغي مواضيع إدارة التخزين المضمنة ويبسط البنية باستخدام آلية دفع التكوين الحالية للتوزيع.

#### البنية الحالية
```
API Request → Gateway → Librarian Service
                            ↓
                    CollectionManager
                            ↓
                    Cassandra Collections Table (librarian keyspace)
                            ↓
                    Broadcast to 4 Storage Management Topics (hardcoded)
                            ↓
        Wait for 4+ Storage Service Responses
                            ↓
                    Response to Gateway
```

#### العمارة الجديدة
```
API Request → Gateway → Librarian Service
                            ↓
                    CollectionManager
                            ↓
                    Config Service API (put/delete/getvalues)
                            ↓
                    Cassandra Config Table (class='collections', key='user:collection')
                            ↓
                    Config Push (to all subscribers on config-push-queue)
                            ↓
        All Storage Services receive config update independently
```

#### التغيير 7: مدير المجموعة - استخدام واجهة برمجة تطبيقات خدمة التكوين
**الملف:** `trustgraph-flow/trustgraph/librarian/collection_manager.py`

**إزالة:**
استخدام `LibraryTableStore` (الأسطر 33، 40-41)
تهيئة منتجي إدارة التخزين (الأسطر 86-140)
طريقة `on_storage_response` (الأسطر 400-430)
تتبع `pending_deletions` (الأسطر 57، 90-96، والاستخدام في جميع أنحاء البرنامج)

**إضافة:**
عميل خدمة التكوين لإجراء مكالمات واجهة برمجة التطبيقات (نمط الطلب/الاستجابة)

**إعداد عميل التكوين:**
```python
# In __init__, add config request/response producers/consumers
from trustgraph.schema.services.config import ConfigRequest, ConfigResponse

# Producer for config requests
self.config_request_producer = Producer(
    client=pulsar_client,
    topic=config_request_queue,
    schema=ConfigRequest,
)

# Consumer for config responses (with correlation ID)
self.config_response_consumer = Consumer(
    taskgroup=taskgroup,
    client=pulsar_client,
    flow=None,
    topic=config_response_queue,
    subscriber=f"{id}-config",
    schema=ConfigResponse,
    handler=self.on_config_response,
)

# Tracking for pending config requests
self.pending_config_requests = {}  # request_id -> asyncio.Event
```

**تعديل `list_collections` (الأسطر من 145 إلى 180):**
```python
async def list_collections(self, user, tag_filter=None, limit=None):
    """List collections from config service"""
    # Send getvalues request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='getvalues',
        type='collections',
    )

    # Send request and wait for response
    response = await self.send_config_request(request)

    # Parse collections from response
    collections = []
    for key, value_json in response.values.items():
        if ":" in key:
            coll_user, collection = key.split(":", 1)
            if coll_user == user:
                metadata = json.loads(value_json)
                collections.append(CollectionMetadata(**metadata))

    # Apply tag filtering in-memory (as before)
    if tag_filter:
        collections = [c for c in collections if any(tag in c.tags for tag in tag_filter)]

    # Apply limit
    if limit:
        collections = collections[:limit]

    return collections

async def send_config_request(self, request):
    """Send config request and wait for response"""
    event = asyncio.Event()
    self.pending_config_requests[request.id] = event

    await self.config_request_producer.send(request)
    await event.wait()

    return self.pending_config_requests.pop(request.id + "_response")

async def on_config_response(self, message, consumer, flow):
    """Handle config response"""
    response = message.value()
    if response.id in self.pending_config_requests:
        self.pending_config_requests[response.id + "_response"] = response
        self.pending_config_requests[response.id].set()
```

**تعديل `update_collection` (الأسطر من 182 إلى 312):**
```python
async def update_collection(self, user, collection, name, description, tags):
    """Update collection via config service"""
    # Create metadata
    metadata = CollectionMetadata(
        user=user,
        collection=collection,
        name=name,
        description=description,
        tags=tags,
    )

    # Send put request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='put',
        type='collections',
        key=f'{user}:{collection}',
        value=json.dumps(metadata.to_dict()),
    )

    response = await self.send_config_request(request)

    if response.error:
        raise RuntimeError(f"Config update failed: {response.error.message}")

    # Config service will trigger config push automatically
    # Storage services will receive update and create collections
```

**تعديل `delete_collection` (الأسطر من 314 إلى 398):**
```python
async def delete_collection(self, user, collection):
    """Delete collection via config service"""
    # Send delete request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='delete',
        type='collections',
        key=f'{user}:{collection}',
    )

    response = await self.send_config_request(request)

    if response.error:
        raise RuntimeError(f"Config delete failed: {response.error.message}")

    # Config service will trigger config push automatically
    # Storage services will receive update and delete collections
```

**تنسيق بيانات التعريف للمجموعة:**
يتم تخزينها في جدول التكوين كـ: `class='collections', key='user:collection'`
القيمة هي بيانات تعريف المجموعة (CollectionMetadata) مُسلسلة بصيغة JSON (بدون حقول الطابع الزمني)
الحقول: `user`، `collection`، `name`، `description`، `tags`
مثال: `class='collections', key='alice:my-docs', value='{"user":"alice","collection":"my-docs","name":"My Documents","description":"...","tags":["work"]}'`

#### التغيير 8: خدمة أمين المكتبة - إزالة بنية إدارة التخزين
**الملف:** `trustgraph-flow/trustgraph/librarian/service.py`

**إزالة:**
منتجي إدارة التخزين (الأسطر 173-190):
  `vector_storage_management_producer`
  `object_storage_management_producer`
  `triples_storage_management_producer`
مستهلك الاستجابة للتخزين (الأسطر 192-201)
معالج `on_storage_response` (الأسطر 467-473)

**تعديل:**
تهيئة CollectionManager (الأسطر 215-224) - إزالة معلمات منتج التخزين

**ملاحظة:** تظل واجهة برمجة التطبيقات الخارجية للمجموعة دون تغيير:
`list-collections`
`update-collection`
`delete-collection`

#### التغيير 9: إزالة جدول المجموعات من LibraryTableStore
**الملف:** `trustgraph-flow/trustgraph/tables/library.py`

**حذف:**
عبارة CREATE لجدول المجموعات (الأسطر 114-127)
عبارات Collections المُعدة (الأسطر 205-240)
جميع طرق المجموعة (الأسطر 578-717):
  `ensure_collection_exists`
  `list_collections`
  `update_collection`
  `delete_collection`
  `get_collection`
  `create_collection`

**السبب:**
يتم الآن تخزين المجموعات في جدول التكوين
التغيير غير المتوافق مقبول - لا توجد حاجة لنقل البيانات
يبسط خدمة أمين المكتبة بشكل كبير

#### التغيير 10: خدمات التخزين - إدارة المجموعة المستندة إلى التكوين ✅ تم

**الحالة:** تم ترحيل جميع خدمات التخزين الـ 11 لاستخدام `CollectionConfigHandler`.

**الخدمات المتأثرة (11 خدمة إجمالاً):**
تضمينات المستندات: milvus, pinecone, qdrant
تضمينات الرسم البياني: milvus, pinecone, qdrant
تخزين الكائنات: cassandra
تخزين الثلاثيات: cassandra, falkordb, memgraph, neo4j

**الملفات:**
`trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/pinecone/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/triples/falkordb/write.py`
`trustgraph-flow/trustgraph/storage/triples/memgraph/write.py`
`trustgraph-flow/trustgraph/storage/triples/neo4j/write.py`

**نمط التنفيذ (جميع الخدمات):**

1. **سجل معالج التكوين في `__init__`:**
```python
# Add after AsyncProcessor initialization
self.register_config_handler(self.on_collection_config)
self.known_collections = set()  # Track (user, collection) tuples
```

2. **تنفيذ معالج التهيئة:**
```python
async def on_collection_config(self, config, version):
    """Handle collection configuration updates"""
    logger.info(f"Collection config version: {version}")

    if "collections" not in config:
        return

    # Parse collections from config
    # Key format: "user:collection" in config["collections"]
    config_collections = set()
    for key in config["collections"].keys():
        if ":" in key:
            user, collection = key.split(":", 1)
            config_collections.add((user, collection))

    # Determine changes
    to_create = config_collections - self.known_collections
    to_delete = self.known_collections - config_collections

    # Create new collections (idempotent)
    for user, collection in to_create:
        try:
            await self.create_collection_internal(user, collection)
            self.known_collections.add((user, collection))
            logger.info(f"Created collection: {user}/{collection}")
        except Exception as e:
            logger.error(f"Failed to create {user}/{collection}: {e}")

    # Delete removed collections (idempotent)
    for user, collection in to_delete:
        try:
            await self.delete_collection_internal(user, collection)
            self.known_collections.discard((user, collection))
            logger.info(f"Deleted collection: {user}/{collection}")
        except Exception as e:
            logger.error(f"Failed to delete {user}/{collection}: {e}")
```

3. **تهيئة المجموعات المعروفة عند بدء التشغيل:**
```python
async def start(self):
    """Start the processor"""
    await super().start()
    await self.sync_known_collections()

async def sync_known_collections(self):
    """Query backend to populate known_collections set"""
    # Backend-specific implementation:
    # - Milvus/Pinecone/Qdrant: List collections/indexes matching naming pattern
    # - Cassandra: Query keyspaces or collection metadata
    # - Neo4j/Memgraph/FalkorDB: Query CollectionMetadata nodes
    pass
```

4. **إعادة هيكلة طرق المعالجة الحالية:**
```python
# Rename and remove response sending:
# handle_create_collection → create_collection_internal
# handle_delete_collection → delete_collection_internal

async def create_collection_internal(self, user, collection):
    """Create collection (idempotent)"""
    # Same logic as current handle_create_collection
    # But remove response producer calls
    # Handle "already exists" gracefully
    pass

async def delete_collection_internal(self, user, collection):
    """Delete collection (idempotent)"""
    # Same logic as current handle_delete_collection
    # But remove response producer calls
    # Handle "not found" gracefully
    pass
```

5. **إزالة البنية التحتية لإدارة التخزين:**
   إزالة الإعداد والتشغيل `self.storage_request_consumer`.
   إزالة الإعداد `self.storage_response_producer`.
   إزالة طريقة الموزع `on_storage_management`.
   إزالة المقاييس لإدارة التخزين.
   إزالة الاستيرادات: `StorageManagementRequest`، `StorageManagementResponse`.

**اعتبارات خاصة بالخلفية:**

**مخازن المتجهات (Milvus, Pinecone, Qdrant):** تتبع `(user, collection)` المنطقية في `known_collections`، ولكن قد يتم إنشاء مجموعات خلفية متعددة لكل بُعد. استمر في نمط الإنشاء الكسول. يجب أن تزيل عمليات الحذف جميع المتغيرات الأبعاد.

**Cassandra Objects:** المجموعات هي خصائص الصفوف، وليست هياكل. تتبع معلومات على مستوى مساحة المفاتيح.

**مخازن الرسوم البيانية (Neo4j, Memgraph, FalkorDB):** استعلام عن عقد `CollectionMetadata` عند بدء التشغيل. إنشاء/حذف عقد البيانات الوصفية عند المزامنة.

**Cassandra Triples:** استخدم واجهة برمجة التطبيقات `KnowledgeGraph` لعمليات المجموعة.

**نقاط التصميم الرئيسية:**

**الاتساق النهائي:** لا يوجد آلية طلب/استجابة، يتم بث دفع التكوين.
**التكرار:** يجب أن تكون جميع عمليات الإنشاء/الحذف آمنة لإعادة المحاولة.
**معالجة الأخطاء:** سجل الأخطاء ولكن لا تقاطع تحديثات التكوين.
**التعافي الذاتي:** ستعيد العمليات الفاشلة المحاولة في دفع التكوين التالي.
**تنسيق مفتاح المجموعة:** `"user:collection"` في `config["collections"]`.

#### التغيير 11: تحديث مخطط المجموعة - إزالة الطوابع الزمنية
**الملف:** `trustgraph-base/trustgraph/schema/services/collection.py`

**تعديل CollectionMetadata (الأسطر 13-21):**
إزالة الحقول `created_at` و `updated_at`:
```python
class CollectionMetadata(Record):
    user = String()
    collection = String()
    name = String()
    description = String()
    tags = Array(String())
    # Remove: created_at = String()
    # Remove: updated_at = String()
```

**تعديل طلب إدارة المجموعة (الأسطر من 25 إلى 47):**
إزالة حقول الطابع الزمني:
```python
class CollectionManagementRequest(Record):
    operation = String()
    user = String()
    collection = String()
    timestamp = String()
    name = String()
    description = String()
    tags = Array(String())
    # Remove: created_at = String()
    # Remove: updated_at = String()
    tag_filter = Array(String())
    limit = Integer()
```

**السبب:**
لا تضيف الطوابع الزمنية قيمة للمجموعات.
خدمة التكوين تحتفظ بآلية تتبع الإصدار الخاصة بها.
تبسط المخطط وتقلل التخزين.

#### فوائد ترحيل خدمة التكوين

1. ✅ **تقضي على مواضيع إدارة التخزين المضمنة بشكل ثابت** - تحل مشكلة المستخدمين المتعددين.
2. ✅ **تنسيق أبسط** - لا يوجد انتظار غير متزامن معقد لـ 4+ استجابات للتخزين.
3. ✅ **الاتساق النهائي** - تقوم خدمات التخزين بالتحديث بشكل مستقل عبر دفع التكوين.
4. ✅ **موثوقية أفضل** - دفع تكوين دائم مقابل طلب/استجابة غير دائمة.
5. ✅ **نموذج تكوين موحد** - يتم التعامل مع المجموعات على أنها تكوين.
6. ✅ **تقلل التعقيد** - تزيل حوالي 300 سطر من كود التنسيق.
7. ✅ **جاهزة لدعم المستخدمين المتعددين** - تدعم التكوين بالفعل عزل المستخدمين عبر مساحة المفاتيح.
8. ✅ **تتبع الإصدار** - توفر آلية إصدار خدمة التكوين مسار تدقيق.

## ملاحظات التنفيذ

### التوافق مع الإصدارات السابقة

**تغييرات في المعلمات:**
إعادة تسمية معلمات سطر الأوامر هي تغييرات جذرية ولكنها مقبولة (الميزة غير وظيفية حاليًا).
تعمل الخدمات بدون معلمات (تستخدم القيم الافتراضية).
تم الحفاظ على مساحات المفاتيح الافتراضية: "config" و "knowledge" و "librarian".
قائمة الانتظار الافتراضية: `persistent://tg/config/config`

**إدارة المجموعات:**
**تغيير جذري:** تمت إزالة جدول المجموعات من مساحة مفاتيح librarian.
**لا يتم توفير ترحيل للبيانات** - مقبول لهذه المرحلة.
واجهة برمجة تطبيقات المجموعة الخارجية لم تتغير (عمليات القائمة/التحديث/الحذف).
تم تبسيط تنسيق بيانات تعريف المجموعة (تمت إزالة الطوابع الزمنية).

### متطلبات الاختبار

**اختبار المعلمات:**
1. تحقق من أن المعلمة `--config-push-queue` تعمل على خدمة graph-embeddings.
2. تحقق من أن المعلمة `--config-push-queue` تعمل على خدمة text-completion.
3. تحقق من أن المعلمة `--config-push-queue` تعمل على خدمة التكوين.
4. تحقق من أن المعلمة `--cassandra-keyspace` تعمل لخدمة التكوين.
5. تحقق من أن المعلمة `--cassandra-keyspace` تعمل لخدمة cores.
6. تحقق من أن المعلمة `--cassandra-keyspace` تعمل لخدمة librarian.
7. تحقق من أن الخدمات تعمل بدون معلمات (تستخدم القيم الافتراضية).
8. تحقق من نشر متعدد المستخدمين باستخدام أسماء قوائم الانتظار ومساحات المفاتيح المخصصة.

**اختبار إدارة المجموعات:**
9. تحقق من العملية `list-collections` عبر خدمة التكوين.
10. تحقق من أن `update-collection` تقوم بإنشاء/تحديث في جدول التكوين.
11. تحقق من أن `delete-collection` تقوم بإزالة من جدول التكوين.
12. تحقق من أن دفع التكوين يتم تشغيله عند تحديث المجموعات.
13. تحقق من أن تصفية العلامات تعمل مع التخزين المستند إلى التكوين.
14. تحقق من أن عمليات المجموعة تعمل بدون حقول الطوابع الزمنية.

### مثال النشر متعدد المستخدمين
```bash
# Tenant: tg-dev
graph-embeddings \
  -p pulsar+ssl://broker:6651 \
  --pulsar-api-key <KEY> \
  --config-push-queue persistent://tg-dev/config/config

config-service \
  -p pulsar+ssl://broker:6651 \
  --pulsar-api-key <KEY> \
  --config-push-queue persistent://tg-dev/config/config \
  --cassandra-keyspace tg_dev_config
```

## تحليل الأثر

### الخدمات المتأثرة بالتغيير 1-2 (إعادة تسمية معلمة سطر الأوامر)
جميع الخدمات التي ترث من AsyncProcessor أو FlowProcessor:
config-service
cores-service
librarian-service
graph-embeddings
document-embeddings
text-completion-* (جميع المزودين)
extract-* (جميع أدوات الاستخراج)
query-* (جميع خدمات الاستعلام)
retrieval-* (جميع خدمات استرجاع المعلومات)
storage-* (جميع خدمات التخزين)
وأكثر من 20 خدمة أخرى

### الخدمات المتأثرة بالتغييرات 3-6 (مساحة مفاتيح Cassandra)
config-service
cores-service
librarian-service

### الخدمات المتأثرة بالتغييرات 7-11 (إدارة المجموعات)

**التغييرات الفورية:**
librarian-service (collection_manager.py, service.py)
tables/library.py (إزالة جدول المجموعات)
schema/services/collection.py (إزالة الطابع الزمني)

**التغييرات المكتملة (التغيير 10):** ✅
جميع خدمات التخزين (11 إجمالاً) - تم ترحيلها إلى دفع التكوين لتحديثات المجموعة عبر `CollectionConfigHandler`
تم إزالة مخطط إدارة التخزين من `storage.py`

## اعتبارات مستقبلية

### نموذج مساحة مفاتيح خاصة بالمستخدم

تستخدم بعض الخدمات **مساحات مفاتيح خاصة بالمستخدم** ديناميكيًا، حيث يحصل كل مستخدم على مساحة مفاتيح Cassandra خاصة به:

**الخدمات التي تستخدم مساحات مفاتيح خاصة بالمستخدم:**
1. **خدمة استعلام الثلاثيات** (`trustgraph-flow/trustgraph/query/triples/cassandra/service.py:65`)
   تستخدم `keyspace=query.user`
2. **خدمة استعلام الكائنات** (`trustgraph-flow/trustgraph/query/objects/cassandra/service.py:479`)
   تستخدم `keyspace=self.sanitize_name(user)`
3. **الوصول المباشر إلى الرسم البياني المعرفي** (`trustgraph-flow/trustgraph/direct/cassandra_kg.py:18`)
   المعلمة الافتراضية `keyspace="trustgraph"`

**الحالة:** هذه **غير معدلة** في هذا المواصفات.

**مراجعة مستقبلية مطلوبة:**
تقييم ما إذا كانت نموذج مساحة مفاتيح خاصة بالمستخدم تخلق مشاكل عزل المستأجر
ضع في اعتبارك ما إذا كانت عمليات النشر متعددة المستأجرين تحتاج إلى أنماط بادئة لمساحة مفاتيح (مثل `tenant_a_user1`)
مراجعة للاحتمالية المحتملة لتصادم معرف المستخدم عبر المستأجرين
تقييم ما إذا كانت مساحة مفاتيح مشتركة واحدة لكل مستأجر مع عزل الصفوف المستند إلى المستخدم هي الأفضل

**ملاحظة:** هذا لا يمنع التنفيذ متعدد المستأجرين الحالي ولكنه يجب مراجعته قبل عمليات نشر متعددة المستأجرين في الإنتاج.

## مراحل التنفيذ

### المرحلة 1: إصلاحات المعلمات (التغييرات 1-6)
إصلاح تسمية المعلمة `--config-push-queue`
إضافة دعم المعلمة `--cassandra-keyspace`
**النتيجة:** تم تمكين قائمة الانتظار متعددة المستأجرين وتكوين مساحة المفاتيح

### المرحلة 2: ترحيل إدارة المجموعة (التغييرات 7-9، 11)
ترحيل تخزين المجموعة إلى خدمة التكوين
إزالة جدول المجموعات من librarian
تحديث مخطط المجموعة (إزالة الطوابع الزمنية)
**النتيجة:** يلغي إدارة التخزين المضمنة، ويبسط librarian

### المرحلة 3: تحديثات خدمة التخزين (التغيير 10) ✅ مكتمل
تم تحديث جميع خدمات التخزين لاستخدام دفع التكوين للمجموعات عبر `CollectionConfigHandler`
تمت إزالة البنية التحتية لطلبات واستجابات إدارة التخزين
تمت إزالة تعريفات المخطط القديمة
**النتيجة:** تم تحقيق إدارة المجموعة المستندة إلى التكوين بالكامل

## المراجع
مشكلة GitHub: https://github.com/trustgraph-ai/trustgraph/issues/582
الملفات ذات الصلة:
  `trustgraph-base/trustgraph/base/async_processor.py`
  `trustgraph-base/trustgraph/base/cassandra_config.py`
  `trustgraph-base/trustgraph/schema/core/topic.py`
  `trustgraph-base/trustgraph/schema/services/collection.py`
  `trustgraph-flow/trustgraph/config/service/service.py`
  `trustgraph-flow/trustgraph/cores/service.py`
  `trustgraph-flow/trustgraph/librarian/service.py`
  `trustgraph-flow/trustgraph/librarian/collection_manager.py`
  `trustgraph-flow/trustgraph/tables/library.py`
