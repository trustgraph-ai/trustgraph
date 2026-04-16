---
layout: default
title: "البنية التحتية للنشر والاشتراك (Pub/Sub)"
parent: "Arabic (Beta)"
---

# البنية التحتية للنشر والاشتراك (Pub/Sub)

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## نظرة عامة

يوثق هذا المستند جميع الاتصالات بين قاعدة بيانات TrustGraph والبنية التحتية للنشر والاشتراك. حاليًا، يتم ترميز النظام لاستخدام Apache Pulsar. تحدد هذه التحليلات جميع نقاط التكامل لإعلام عمليات إعادة الهيكلة المستقبلية نحو تجريد نشر واشتراك قابل للتكوين.

## الحالة الحالية: نقاط تكامل Pulsar

### 1. استخدام عميل Pulsar المباشر

**الموقع:** `trustgraph-flow/trustgraph/gateway/service.py`

يقوم بوابة واجهة برمجة التطبيقات باستيراد وتثبيت عميل Pulsar مباشرةً:

**السطر 20:** `import pulsar`
**الأسطر 54-61:** تثبيت مباشر لـ `pulsar.Client()` مع `pulsar.AuthenticationToken()` الاختياري
**الأسطر 33-35:** تكوين مضيف Pulsar الافتراضي من متغيرات البيئة
**الأسطر 178-192:** وسيطات سطر الأوامر لـ `--pulsar-host`، `--pulsar-api-key`، و `--pulsar-listener`
**الأسطر 78، 124:** تمرير `pulsar_client` إلى `ConfigReceiver` و `DispatcherManager`

هذا هو الموقع الوحيد الذي يقوم بتثبيت عميل Pulsar مباشرةً خارج طبقة التجريد.

### 2. إطار عمل المعالج الأساسي

**الموقع:** `trustgraph-base/trustgraph/base/async_processor.py`

يوفر الفئة الأساسية لجميع المعالجات اتصال Pulsar:

**السطر 9:** `import _pulsar` (للتعامل مع الاستثناءات)
**السطر 18:** `from . pubsub import PulsarClient`
**السطر 38:** إنشاء `pulsar_client_object = PulsarClient(**params)`
**الأسطر 104-108:** خصائص تعرض `pulsar_host` و `pulsar_client`
**السطر 250:** تستدعي الطريقة الثابتة `add_args()` `PulsarClient.add_args(parser)` لوسيطات سطر الأوامر
**الأسطر 223-225:** معالجة الاستثناءات لـ `_pulsar.Interrupted`

ترث جميع المعالجات من `AsyncProcessor`، مما يجعل هذا نقطة التكامل المركزية.

### 3. تجريد المستهلك

**الموقع:** `trustgraph-base/trustgraph/base/consumer.py`

يستهلك الرسائل من قوائم الانتظار ويستدعي وظائف المعالج:

**استيرادات Pulsar:**
**السطر 12:** `from pulsar.schema import JsonSchema`
**السطر 13:** `import pulsar`
**السطر 14:** `import _pulsar`

**الاستخدام المحدد لـ Pulsar:**
**الأسطر 100، 102:** `pulsar.InitialPosition.Earliest` / `pulsar.InitialPosition.Latest`
**السطر 108:** غلاف `JsonSchema(self.schema)`
**السطر 110:** `pulsar.ConsumerType.Shared`
**الأسطر 104-111:** `self.client.subscribe()` مع معلمات خاصة بـ Pulsar
**الأسطر 143، 150، 65:** طرق `consumer.unsubscribe()` و `consumer.close()`
**السطر 162:** استثناء `_pulsar.Timeout`
**الأسطر 182، 205، 232:** `consumer.acknowledge()` / `consumer.negative_acknowledge()`

**ملف المواصفات:** `trustgraph-base/trustgraph/base/consumer_spec.py`
**السطر 22:** يشير إلى `processor.pulsar_client`

### 4. تجريد الناشر

**الموقع:** `trustgraph-base/trustgraph/base/producer.py`

يرسل الرسائل إلى قوائم الانتظار:

**استيرادات Pulsar:**
**السطر 2:** `from pulsar.schema import JsonSchema`

**الاستخدام المحدد لـ Pulsar:**
**السطر 49:** غلاف `JsonSchema(self.schema)`
**الأسطر 47-51:** `self.client.create_producer()` مع معلمات خاصة بـ Pulsar (الموضوع، المخطط، تمكين التجزئة)
**الأسطر 31، 76:** طريقة `producer.close()`
**الأسطر 64-65:** `producer.send()` مع الرسالة والخصائص

**ملف المواصفات:** `trustgraph-base/trustgraph/base/producer_spec.py`
**السطر 18:** يشير إلى `processor.pulsar_client`

### 5. تجريد الناشر

**الموقع:** `trustgraph-base/trustgraph/base/publisher.py`

نشر الرسائل بشكل غير متزامن مع تخزين الرسائل مؤقتًا في قائمة الانتظار:

**استيرادات Pulsar:**
**السطر 2:** `from pulsar.schema import JsonSchema`
**السطر 6:** `import pulsar`

**الاستخدام المحدد لـ Pulsar:**
**السطر 52:** غلاف `JsonSchema(self.schema)`
**الأسطر 50-54:** `self.client.create_producer()` مع معلمات خاصة بـ Pulsar
**الأسطر 101، 103:** `producer.send()` مع الرسالة والخصائص الاختيارية
**الأسطر 106-107:** طرق `producer.flush()` و `producer.close()`

### 6. تجريد المشترك

**الموقع:** `trustgraph-base/trustgraph/base/subscriber.py`

يوفر توزيع رسائل متعددة المستلمين من خلال قوائم الانتظار:

**استيرادات Pulsar:**
**السطر 6:** `from pulsar.schema import JsonSchema`
**السطر 8:** `import _pulsar`

**الاستخدام الخاص بـ Pulsar:**
**السطر 55:** `JsonSchema(self.schema)` wrapper
**السطر 57:** `self.client.subscribe(**subscribe_args)`
**الأسطر 101، 136، 160، 167-172:** استثناءات Pulsar: `_pulsar.Timeout`, `_pulsar.InvalidConfiguration`, `_pulsar.AlreadyClosed`
**الأسطر 159، 166، 170:** طرق المستهلك: `negative_acknowledge()`, `unsubscribe()`, `close()`
**الأسطر 247، 251:** إقرار الرسالة: `acknowledge()`, `negative_acknowledge()`

**ملف المواصفات:** `trustgraph-base/trustgraph/base/subscriber_spec.py`
**السطر 19:** يشير إلى `processor.pulsar_client`

### 7. نظام المخططات (قلب الظلام)

**الموقع:** `trustgraph-base/trustgraph/schema/`

يتم تعريف كل مخطط رسالة في النظام باستخدام إطار عمل المخططات الخاص بـ Pulsar.

**المكونات الأساسية:** `schema/core/primitives.py`
**السطر 2:** `from pulsar.schema import Record, String, Boolean, Array, Integer`
ترث جميع المخططات من الفئة الأساسية `Record` الخاصة بـ Pulsar
جميع أنواع الحقول هي أنواع Pulsar: `String()`, `Integer()`, `Boolean()`, `Array()`, `Map()`, `Double()`

**أمثلة على المخططات:**
`schema/services/llm.py` (السطر 2): `from pulsar.schema import Record, String, Array, Double, Integer, Boolean`
`schema/services/config.py` (السطر 2): `from pulsar.schema import Record, Bytes, String, Boolean, Array, Map, Integer`

**تسمية الموضوع:** `schema/core/topic.py`
**الأسطر 2-3:** تنسيق الموضوع: `{kind}://{tenant}/{namespace}/{topic}`
هذه البنية URI خاصة بـ Pulsar (على سبيل المثال، `persistent://tg/flow/config`)

**التأثير:**
تستخدم جميع تعريفات الرسائل/الردود في قاعدة التعليمات البرمجية مخططات Pulsar
يتضمن ذلك الخدمات الخاصة بـ: config, flow, llm, prompt, query, storage, agent, collection, diagnosis, library, lookup, nlp_query, objects_query, retrieval, structured_query
يتم استيراد تعريفات المخططات واستخدامها على نطاق واسع في جميع المعالجات والخدمات

## ملخص

### تبعيات Pulsar حسب الفئة

1. **إنشاء العميل:**
   مباشر: `gateway/service.py`
   مجرد: `async_processor.py` → `pubsub.py` (PulsarClient)

2. **نقل الرسائل:**
   المستهلك: `consumer.py`, `consumer_spec.py`
   المنتج: `producer.py`, `producer_spec.py`
   الناشر: `publisher.py`
   المشترك: `subscriber.py`, `subscriber_spec.py`

3. **نظام المخططات:**
   الأنواع الأساسية: `schema/core/primitives.py`
   جميع مخططات الخدمة: `schema/services/*.py`
   تسمية الموضوع: `schema/core/topic.py`

4. **مفاهيم Pulsar الخاصة المطلوبة:**
   رسائل قائمة على الموضوع
   نظام المخططات (السجل، أنواع الحقول)
   اشتراكات مشتركة
   إقرار الرسالة (إيجابي/سلبي)
   موضع المستهلك (الأول/الأخير)
   خصائص الرسالة
   المواضع الأولية وأنواع المستهلك
   دعم التجزئة
   مواضيع مستمرة مقابل مواضيع غير مستمرة

### تحديات إعادة الهيكلة

الخبر السار: توفر طبقة التجريد (المستهلك، المنتج، الناشر، المشترك) تغليفًا نظيفًا لمعظم تفاعلات Pulsar.

التحديات:
1. **انتشار نظام المخططات:** يستخدم كل تعريف للرسالة `pulsar.schema.Record` وأنواع Pulsar للحقول
2. **قوائم Pulsar الخاصة:** `InitialPosition`, `ConsumerType`
3. **استثناءات Pulsar:** `_pulsar.Timeout`, `_pulsar.Interrupted`, `_pulsar.InvalidConfiguration`, `_pulsar.AlreadyClosed`
4. **توقيعات الطريقة:** `acknowledge()`, `negative_acknowledge()`, `subscribe()`, `create_producer()`، إلخ.
5. **تنسيق URI للموضوع:** هيكل Pulsar `kind://tenant/namespace/topic`

### الخطوات التالية

لجعل البنية التحتية للنشر/الاشتراك قابلة للتكوين، نحتاج إلى:

1. إنشاء واجهة تجريد لنظام العميل/المخططات
2. تجريد قوائم Pulsar الخاصة والاستثناءات
3. إنشاء أغلفة المخططات أو تعريفات مخططات بديلة
4. تنفيذ الواجهة لكل من Pulsar وأنظمة بديلة (Kafka, RabbitMQ, Redis Streams, إلخ.)
5. تحديث `pubsub.py` ليكون قابلاً للتكوين ودعم الخلفيات المتعددة
6. توفير مسار ترحيل للنشر الحالي

## مسودة النهج 1: نمط المحول مع طبقة ترجمة المخططات

### الفكرة الرئيسية
**نظام المخططات** هو نقطة التكامل الأعمق - كل شيء آخر ينبع منه. نحتاج إلى حل هذه المشكلة أولاً، وإلا سنعيد كتابة قاعدة التعليمات البرمجية بأكملها.

### الاستراتيجية: الحد الأدنى من الاضطرابات مع المحولات

**1. الحفاظ على مخططات Pulsar كتمثيل داخلي**
لا تقم بإعادة كتابة جميع تعريفات المخططات.
تبقى المخططات `pulsar.schema.Record` داخليًا.
استخدم المحولات لترجمة البيانات عند الحد بين التعليمات البرمجية الخاصة بنا والخلفية الخاصة بالنشر والاشتراك.

**2. إنشاء طبقة تجريدية للنشر والاشتراك:**

```
┌─────────────────────────────────────┐
│   Existing Code (unchanged)         │
│   - Uses Pulsar schemas internally  │
│   - Consumer/Producer/Publisher     │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│   PubSubFactory (configurable)      │
│   - Creates backend-specific client │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
┌───────▼─────┐  ┌────▼─────────┐
│ PulsarAdapter│  │ KafkaAdapter │  etc...
│ (passthrough)│  │ (translates) │
└──────────────┘  └──────────────┘
```

**3. تحديد الواجهات المجردة:**
`PubSubClient` - اتصال العميل
`PubSubProducer` - إرسال الرسائل
`PubSubConsumer` - استقبال الرسائل
`SchemaAdapter` - ترجمة مخططات Pulsar إلى/من JSON أو التنسيقات الخاصة بالخلفية

**4. تفاصيل التنفيذ:**

بالنسبة إلى **محول Pulsar**: تمرير تقريبي، ترجمة محدودة

بالنسبة إلى **الخلفيات الأخرى** (Kafka، RabbitMQ، إلخ):
تسلسل كائنات سجل Pulsar إلى JSON/بايت
مطابقة المفاهيم مثل:
  `InitialPosition.Earliest/Latest` → auto.offset.reset في Kafka
  `acknowledge()` → commit في Kafka
  `negative_acknowledge()` → نمط إعادة الترتيب أو قائمة الانتظار الميتة (DLQ)
  عناوين الموضوع → أسماء الموضوعات الخاصة بالخلفية

### التحليل

**المزايا:**
✅ تغييرات قليلة في التعليمات البرمجية للخدمات الحالية
✅ تبقى المخططات كما هي (بدون إعادة كتابة شاملة)
✅ مسار ترحيل تدريجي
✅ لا يلاحظ مستخدمو Pulsar أي فرق
✅ إضافة خلفيات جديدة عبر المحولات

**العيوب:**
⚠️ لا يزال يعتمد على Pulsar (لتحديد المخططات)
⚠️ بعض عدم التطابق في ترجمة المفاهيم

### بديل يجب أخذه في الاعتبار

إنشاء **نظام مخططات TrustGraph** مستقل عن النشر والاشتراك (باستخدام فئات البيانات أو Pydantic)، ثم إنشاء مخططات Pulsar/Kafka/إلخ من ذلك. يتطلب هذا إعادة كتابة كل ملف مخطط وقد يؤدي إلى تغييرات غير متوقعة.

### التوصية للإصدار الأول

ابدأ بـ **نهج المحول** لأنه:
1. عملي - يعمل مع التعليمات البرمجية الحالية
2. يثبت المفهوم بأقل قدر من المخاطر
3. يمكن أن يتطور إلى نظام مخططات أصلي لاحقًا إذا لزم الأمر
4. مدفوع بالتكوين: متغير بيئة واحد يقوم بتبديل الخلفيات

## النهج المقترح للإصدار الثاني: نظام مخططات مستقل عن الخلفية باستخدام فئات البيانات

### المفهوم الأساسي

استخدم **فئات البيانات** في Python كتنسيق تعريف مخطط محايد. توفر كل خلفية نشر واشتراك الخاصة بها تسلسلًا/إلغاء تسلسل لـ فئات البيانات، مما يلغي الحاجة إلى بقاء مخططات Pulsar في قاعدة التعليمات البرمجية.

### تعدد الأشكال للمخططات على مستوى المصنع

بدلاً من ترجمة مخططات Pulsar، **توفر كل خلفية معالجتها الخاصة للمخططات** والتي تعمل مع فئات البيانات القياسية في Python.

### تدفق الناشر

```python
# 1. Get the configured backend from factory
pubsub = get_pubsub()  # Returns PulsarBackend, MQTTBackend, etc.

# 2. Get schema class from the backend
# (Can be imported directly - backend-agnostic)
from trustgraph.schema.services.llm import TextCompletionRequest

# 3. Create a producer/publisher for a specific topic
producer = pubsub.create_producer(
    topic="text-completion-requests",
    schema=TextCompletionRequest  # Tells backend what schema to use
)

# 4. Create message instances (same API regardless of backend)
request = TextCompletionRequest(
    system="You are helpful",
    prompt="Hello world",
    streaming=False
)

# 5. Send the message
producer.send(request)  # Backend serializes appropriately
```

### تدفق المستهلك

```python
# 1. Get the configured backend
pubsub = get_pubsub()

# 2. Create a consumer
consumer = pubsub.subscribe(
    topic="text-completion-requests",
    schema=TextCompletionRequest  # Tells backend how to deserialize
)

# 3. Receive and deserialize
msg = consumer.receive()
request = msg.value()  # Returns TextCompletionRequest dataclass instance

# 4. Use the data (type-safe access)
print(request.system)   # "You are helpful"
print(request.prompt)   # "Hello world"
print(request.streaming)  # False
```

### ما الذي يحدث وراء الكواليس

**للخلفية التقنية لـ Pulsar:**
`create_producer()` → ينشئ مُنتج Pulsar باستخدام مخطط JSON أو سجل تم إنشاؤه ديناميكيًا.
`send(request)` → يقوم بتسلسل كائن البيانات (dataclass) إلى تنسيق JSON/Pulsar، ويرسله إلى Pulsar.
`receive()` → يستقبل رسالة Pulsar، ويقوم بإلغاء تسلسلها مرة أخرى إلى كائن البيانات.

**للخلفية التقنية لـ MQTT:**
`create_producer()` → يتصل بخادم MQTT، ولا يلزم تسجيل أي مخطط.
`send(request)` → يحول كائن البيانات إلى JSON، وينشره في موضوع MQTT.
`receive()` → يشترك في موضوع MQTT، ويقوم بإلغاء تسلسل JSON إلى كائن بيانات.

**للخلفية التقنية لـ Kafka:**
`create_producer()` → ينشئ مُنتج Kafka، ويسجل مخطط Avro إذا لزم الأمر.
`send(request)` → يقوم بتسلسل كائن البيانات إلى تنسيق Avro، ويرسله إلى Kafka.
`receive()` → يستقبل رسالة Kafka، ويقوم بإلغاء تسلسل Avro مرة أخرى إلى كائن بيانات.

### النقاط الرئيسية في التصميم

1. **إنشاء كائن المخطط**: نسخة كائن البيانات (`TextCompletionRequest(...)`) متطابقة بغض النظر عن الخلفية التقنية.
2. **الخلفية التقنية تتعامل مع الترميز**: كل خلفية تقنية تعرف كيفية تسلسل كائن البيانات الخاص بها إلى التنسيق المستخدم.
3. **تعريف المخطط عند الإنشاء**: عند إنشاء المنتج/المستهلك، تحدد نوع المخطط.
4. **الحفاظ على سلامة النوع**: تحصل على كائن `TextCompletionRequest` صحيح، وليس قاموسًا.
5. **لا يوجد تسرب للخلفية التقنية**: لا يقوم كود التطبيق باستيراد مكتبات خاصة بالخلفية التقنية.

### مثال للتحويل

**الحالي (خاص بـ Pulsar):**
```python
# schema/services/llm.py
from pulsar.schema import Record, String, Boolean, Integer

class TextCompletionRequest(Record):
    system = String()
    prompt = String()
    streaming = Boolean()
```

**جديد (لا يعتمد على الواجهة الخلفية):**
```python
# schema/services/llm.py
from dataclasses import dataclass

@dataclass
class TextCompletionRequest:
    system: str
    prompt: str
    streaming: bool = False
```

### التكامل مع الواجهة الخلفية (Backend Integration)

كل واجهة خلفية تتعامل مع التسلسل/إلغاء التسلسل لفئات البيانات (dataclasses):

**واجهة خلفية Pulsar:**
إنشاء فئات `pulsar.schema.Record` ديناميكيًا من فئات البيانات.
أو تسلسل فئات البيانات إلى JSON واستخدام مخطط JSON الخاص بـ Pulsar.
تحافظ على التوافق مع عمليات نشر Pulsar الحالية.

**واجهة خلفية MQTT/Redis:**
تسلسل JSON مباشر لمثيل فئة البيانات.
استخدم `dataclasses.asdict()` / `from_dict()`.
خفيفة الوزن، لا تحتاج إلى سجل مخططات.

**واجهة خلفية Kafka:**
إنشاء مخططات Avro من تعريفات فئات البيانات.
استخدم سجل مخططات Confluent.
تسلسل آمن من حيث النوع مع دعم تطور المخطط.

### البنية (Architecture)

```
┌─────────────────────────────────────┐
│   Application Code                  │
│   - Uses dataclass schemas          │
│   - Backend-agnostic                │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│   PubSubFactory (configurable)      │
│   - get_pubsub() returns backend    │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
┌───────▼─────────┐  ┌────▼──────────────┐
│ PulsarBackend   │  │ MQTTBackend       │
│ - JSON schema   │  │ - JSON serialize  │
│ - or dynamic    │  │ - Simple queues   │
│   Record gen    │  │                   │
└─────────────────┘  └───────────────────┘
```

### تفاصيل التنفيذ

**1. تعريفات المخططات:** فئات بيانات بسيطة مع تلميحات الأنواع
   `str`، `int`، `bool`، `float` للقيم الأولية
   `list[T]` للمصفوفات
   `dict[str, T]` للخرائط
   فئات بيانات متداخلة للأنواع المعقدة

**2. يوفر كل خلفية:**
   المُسلسل: `dataclass → bytes/wire format`
   المُفكك: `bytes/wire format → dataclass`
   تسجيل المخطط (إذا لزم الأمر، مثل Pulsar/Kafka)

**3. تجريد المستهلك/المنتج:**
   موجود بالفعل (consumer.py, producer.py)
   تحديث لاستخدام التسلسل الخاص بالخلفية
   إزالة استيرادات Pulsar المباشرة

**4. تعيينات الأنواع:**
   Pulsar `String()` → Python `str`
   Pulsar `Integer()` → Python `int`
   Pulsar `Boolean()` → Python `bool`
   Pulsar `Array(T)` → Python `list[T]`
   Pulsar `Map(K, V)` → Python `dict[K, V]`
   Pulsar `Double()` → Python `float`
   Pulsar `Bytes()` → Python `bytes`

### مسار الترحيل

1. **إنشاء إصدارات من فئات البيانات** لجميع المخططات في `trustgraph/schema/`
2. **تحديث الفئات الخلفية** (المستهلك، المنتج، الناشر، المشترك) لاستخدام التسلسل المقدم من الخلفية
3. **تنفيذ PulsarBackend** باستخدام مخطط JSON أو إنشاء سجل ديناميكي
4. **الاختبار مع Pulsar** للتأكد من التوافق مع الإصدارات السابقة للنشر
5. **إضافة خلفيات جديدة** (MQTT، Kafka، Redis، إلخ) حسب الحاجة
6. **إزالة استيرادات Pulsar** من ملفات المخططات

### الفوائد

✅ **لا يوجد اعتماد على النشر/الاشتراك** في تعريفات المخططات
✅ **Python قياسي** - سهل الفهم، التحقق من النوع، التوثيق
✅ **أدوات حديثة** - تعمل مع mypy، إكمال التعليمات البرمجية لبيئات التطوير المتكاملة، المدققين
✅ **محسّنة للخلفية** - تستخدم كل خلفية التسلسل الأصلي
✅ **لا توجد تكلفة ترجمة** - تسلسل مباشر، بدون محولات
✅ **أمان النوع** - كائنات حقيقية مع أنواع مناسبة
✅ **التحقق السهل** - يمكن استخدام Pydantic إذا لزم الأمر

### التحديات والحلول

**التحدي:** يحتوي Pulsar's `Record` على تحقق من صحة الحقول في وقت التشغيل
**الحل:** استخدم فئات بيانات Pydantic للتحقق من الصحة إذا لزم الأمر، أو ميزات فئة البيانات Python 3.10+ مع `__post_init__`

**التحدي:** بعض ميزات Pulsar الخاصة (مثل نوع `Bytes`)
**الحل:** قم بتعيين إلى نوع `bytes` في فئة البيانات، تتعامل الخلفية مع الترميز بشكل مناسب

**التحدي:** تسمية الموضوع (`persistent://tenant/namespace/topic`)
**الحل:** قم بتجريد أسماء الموضوع في تعريفات المخططات، تقوم الخلفية بتحويلها إلى التنسيق المناسب

**التحدي:** تطور المخططات والتحكم في الإصدار
**الحل:** تتعامل كل خلفية مع هذا وفقًا لقدراتها (إصدارات مخطط Pulsar، سجل مخطط Kafka، إلخ)

**التحدي:** الأنواع المعقدة المتداخلة
**الحل:** استخدم فئات بيانات متداخلة، تقوم الخلفيات بالتسلسل/فك التسلسل بشكل متكرر

### قرارات التصميم

1. **فئات بيانات عادية أو Pydantic؟**
   ✅ **القرار: استخدم فئات بيانات Python عادية**
   أبسط، بدون تبعيات إضافية
   التحقق من الصحة ليس مطلوبًا عمليًا
   أسهل في الفهم والصيانة

2. **تطور المخطط:**
   ✅ **القرار: لا يلزم آلية للتحكم في الإصدار**
   المخططات مستقرة وطويلة الأمد
   عادةً ما تضيف التحديثات حقولًا جديدة (متوافقة مع الإصدارات السابقة)
   تتعامل الخلفيات مع تطور المخطط وفقًا لقدراتها

3. **التوافق مع الإصدارات السابقة:**
   ✅ **القرار: تغيير رئيسي للإصدار، لا يلزم التوافق مع الإصدارات السابقة**
   سيكون هذا تغييرًا جذريًا مع تعليمات ترحيل
   يسمح الفصل النظيف بتصميم أفضل
   سيتم توفير دليل ترحيل للنشر الحالي

4. **الأنواع المتداخلة والهياكل المعقدة:**
   ✅ **القرار: استخدم فئات بيانات متداخلة بشكل طبيعي**
   تتعامل فئات بيانات Python مع التداخل بشكل مثالي
   `list[T]` للمصفوفات، `dict[K, V]` للخرائط
   تقوم الخلفيات بالتسلسل/فك التسلسل بشكل متكرر
   مثال:
     ```python
     @dataclass
     class Value:
         value: str
         is_uri: bool

     @dataclass
     class Triple:
         s: Value              # Nested dataclass
         p: Value
         o: Value

     @dataclass
     class GraphQuery:
         triples: list[Triple]  # Array of nested dataclasses
         metadata: dict[str, str]
     ```

5. **القيم الافتراضية والحقول الاختيارية:**
   ✅ **القرار: مزيج من الحقول المطلوبة، والقيم الافتراضية، والحقول الاختيارية**
   الحقول المطلوبة: لا توجد قيمة افتراضية.
   الحقول التي تحتوي على قيم افتراضية: موجودة دائمًا، ولها قيمة افتراضية منطقية.
   الحقول الاختيارية حقًا: `T | None = None`، يتم حذفها من التسلسل عند `None`.
   مثال:
     ```python
     @dataclass
     class TextCompletionRequest:
         system: str              # Required, no default
         prompt: str              # Required, no default
         streaming: bool = False  # Optional with default value
         metadata: dict | None = None  # Truly optional, can be absent
     ```

   **المعاني الأساسية للتسلسل الهام:**

   عندما يكون `metadata = None`:
   ```json
   {
       "system": "...",
       "prompt": "...",
       "streaming": false
       // metadata field NOT PRESENT
   }
   ```

   عندما `metadata = {}` (فارغة بشكل صريح):
   ```json
   {
       "system": "...",
       "prompt": "...",
       "streaming": false,
       "metadata": {}  // Field PRESENT but empty
   }
   ```

   **الفرق الرئيسي:**
   `None` → حقل غير موجود في JSON (غير مُسلسل)
   قيمة فارغة (`{}`، `[]`، `""`) → حقل موجود بقيمة فارغة
   هذا مهم من الناحية الدلالية: "غير مقدم" مقابل "فارغ بشكل صريح"
   يجب على أنظمة التسلسل الخلفية تخطي حقول `None`، وليس ترميزها كـ `null`

## مسودة الحل الثالث: تفاصيل التنفيذ

### تنسيق اسم قائمة انتظار عام

استبدل أسماء قوائم الانتظار الخاصة بكل نظام خلفي بتنسيق عام يمكن للأنظمة الخلفية تعيينه بشكل مناسب.

**التنسيق:** `{qos}/{tenant}/{namespace}/{queue-name}`

حيث:
`qos`: مستوى جودة الخدمة
  `q0` = بذل جهد (إرسال وإهمال، بدون إقرار)
  `q1` = مرة واحدة على الأقل (يتطلب إقرارًا)
  `q2` = مرة واحدة بالضبط (إقرار من مرحلتين)
`tenant`: تجميع منطقي للتعددية
`namespace`: تجميع فرعي داخل المستأجر
`queue-name`: اسم قائمة الانتظار/الموضوع الفعلي

**أمثلة:**
```
q1/tg/flow/text-completion-requests
q2/tg/config/config-push
q0/tg/metrics/stats
```

### ربط الموضوعات في الواجهة الخلفية

تقوم كل واجهة خلفية بتحويل التنسيق العام إلى تنسيقها الأصلي:

**الواجهة الخلفية Pulsar:**
```python
def map_topic(self, generic_topic: str) -> str:
    # Parse: q1/tg/flow/text-completion-requests
    qos, tenant, namespace, queue = generic_topic.split('/', 3)

    # Map QoS to persistence
    persistence = 'persistent' if qos in ['q1', 'q2'] else 'non-persistent'

    # Return Pulsar URI: persistent://tg/flow/text-completion-requests
    return f"{persistence}://{tenant}/{namespace}/{queue}"
```

**الخلفية التقنية لـ MQTT:**
```python
def map_topic(self, generic_topic: str) -> tuple[str, int]:
    # Parse: q1/tg/flow/text-completion-requests
    qos, tenant, namespace, queue = generic_topic.split('/', 3)

    # Map QoS level
    qos_level = {'q0': 0, 'q1': 1, 'q2': 2}[qos]

    # Build MQTT topic including tenant/namespace for proper namespacing
    mqtt_topic = f"{tenant}/{namespace}/{queue}"

    return mqtt_topic, qos_level
```

### الدالة المساعدة للموضوع المحدّثة

```python
# schema/core/topic.py
def topic(queue_name, qos='q1', tenant='tg', namespace='flow'):
    """
    Create a generic topic identifier that can be mapped by backends.

    Args:
        queue_name: The queue/topic name
        qos: Quality of service
             - 'q0' = best-effort (no ack)
             - 'q1' = at-least-once (ack required)
             - 'q2' = exactly-once (two-phase ack)
        tenant: Tenant identifier for multi-tenancy
        namespace: Namespace within tenant

    Returns:
        Generic topic string: qos/tenant/namespace/queue_name

    Examples:
        topic('my-queue')  # q1/tg/flow/my-queue
        topic('config', qos='q2', namespace='config')  # q2/tg/config/config
    """
    return f"{qos}/{tenant}/{namespace}/{queue_name}"
```

### التكوين والتهيئة

**وسائط سطر الأوامر + متغيرات البيئة:**

```python
# In base/async_processor.py - add_args() method
@staticmethod
def add_args(parser):
    # Pub/sub backend selection
    parser.add_argument(
        '--pubsub-backend',
        default=os.getenv('PUBSUB_BACKEND', 'pulsar'),
        choices=['pulsar', 'mqtt'],
        help='Pub/sub backend (default: pulsar, env: PUBSUB_BACKEND)'
    )

    # Pulsar-specific configuration
    parser.add_argument(
        '--pulsar-host',
        default=os.getenv('PULSAR_HOST', 'pulsar://localhost:6650'),
        help='Pulsar host (default: pulsar://localhost:6650, env: PULSAR_HOST)'
    )

    parser.add_argument(
        '--pulsar-api-key',
        default=os.getenv('PULSAR_API_KEY', None),
        help='Pulsar API key (env: PULSAR_API_KEY)'
    )

    parser.add_argument(
        '--pulsar-listener',
        default=os.getenv('PULSAR_LISTENER', None),
        help='Pulsar listener name (env: PULSAR_LISTENER)'
    )

    # MQTT-specific configuration
    parser.add_argument(
        '--mqtt-host',
        default=os.getenv('MQTT_HOST', 'localhost'),
        help='MQTT broker host (default: localhost, env: MQTT_HOST)'
    )

    parser.add_argument(
        '--mqtt-port',
        type=int,
        default=int(os.getenv('MQTT_PORT', '1883')),
        help='MQTT broker port (default: 1883, env: MQTT_PORT)'
    )

    parser.add_argument(
        '--mqtt-username',
        default=os.getenv('MQTT_USERNAME', None),
        help='MQTT username (env: MQTT_USERNAME)'
    )

    parser.add_argument(
        '--mqtt-password',
        default=os.getenv('MQTT_PASSWORD', None),
        help='MQTT password (env: MQTT_PASSWORD)'
    )
```

**دالة المصنع:**

```python
# In base/pubsub.py or base/pubsub_factory.py
def get_pubsub(**config) -> PubSubBackend:
    """
    Create and return a pub/sub backend based on configuration.

    Args:
        config: Configuration dict from command-line args
                Must include 'pubsub_backend' key

    Returns:
        Backend instance (PulsarBackend, MQTTBackend, etc.)
    """
    backend_type = config.get('pubsub_backend', 'pulsar')

    if backend_type == 'pulsar':
        return PulsarBackend(
            host=config.get('pulsar_host'),
            api_key=config.get('pulsar_api_key'),
            listener=config.get('pulsar_listener'),
        )
    elif backend_type == 'mqtt':
        return MQTTBackend(
            host=config.get('mqtt_host'),
            port=config.get('mqtt_port'),
            username=config.get('mqtt_username'),
            password=config.get('mqtt_password'),
        )
    else:
        raise ValueError(f"Unknown pub/sub backend: {backend_type}")
```

**الاستخدام في AsyncProcessor:**

```python
# In async_processor.py
class AsyncProcessor:
    def __init__(self, **params):
        self.id = params.get("id")

        # Create backend from config (replaces PulsarClient)
        self.pubsub = get_pubsub(**params)

        # Rest of initialization...
```

### الواجهة الخلفية

```python
class PubSubBackend(Protocol):
    """Protocol defining the interface all pub/sub backends must implement."""

    def create_producer(self, topic: str, schema: type, **options) -> BackendProducer:
        """
        Create a producer for a topic.

        Args:
            topic: Generic topic format (qos/tenant/namespace/queue)
            schema: Dataclass type for messages
            options: Backend-specific options (e.g., chunking_enabled)

        Returns:
            Backend-specific producer instance
        """
        ...

    def create_consumer(
        self,
        topic: str,
        subscription: str,
        schema: type,
        initial_position: str = 'latest',
        consumer_type: str = 'shared',
        **options
    ) -> BackendConsumer:
        """
        Create a consumer for a topic.

        Args:
            topic: Generic topic format (qos/tenant/namespace/queue)
            subscription: Subscription/consumer group name
            schema: Dataclass type for messages
            initial_position: 'earliest' or 'latest' (MQTT may ignore)
            consumer_type: 'shared', 'exclusive', 'failover' (MQTT may ignore)
            options: Backend-specific options

        Returns:
            Backend-specific consumer instance
        """
        ...

    def close(self) -> None:
        """Close the backend connection."""
        ...
```

```python
class BackendProducer(Protocol):
    """Protocol for backend-specific producer."""

    def send(self, message: Any, properties: dict = {}) -> None:
        """Send a message (dataclass instance) with optional properties."""
        ...

    def flush(self) -> None:
        """Flush any buffered messages."""
        ...

    def close(self) -> None:
        """Close the producer."""
        ...
```

```python
class BackendConsumer(Protocol):
    """Protocol for backend-specific consumer."""

    def receive(self, timeout_millis: int = 2000) -> Message:
        """
        Receive a message from the topic.

        Raises:
            TimeoutError: If no message received within timeout
        """
        ...

    def acknowledge(self, message: Message) -> None:
        """Acknowledge successful processing of a message."""
        ...

    def negative_acknowledge(self, message: Message) -> None:
        """Negative acknowledge - triggers redelivery."""
        ...

    def unsubscribe(self) -> None:
        """Unsubscribe from the topic."""
        ...

    def close(self) -> None:
        """Close the consumer."""
        ...
```

```python
class Message(Protocol):
    """Protocol for a received message."""

    def value(self) -> Any:
        """Get the deserialized message (dataclass instance)."""
        ...

    def properties(self) -> dict:
        """Get message properties/metadata."""
        ...
```

### إعادة هيكلة الفئات الحالية

تظل الفئات الحالية `Consumer`، `Producer`، `Publisher`، `Subscriber` في الغالب دون تغيير:

**المسؤوليات الحالية (يجب الحفاظ عليها):**
نموذج الخيوط غير المتزامنة ومجموعات المهام.
منطق إعادة الاتصال ومعالجة إعادة المحاولة.
جمع المقاييس.
تحديد المعدل.
إدارة التزامن.

**التغييرات المطلوبة:**
إزالة استيرادات Pulsar المباشرة (`pulsar.schema`، `pulsar.InitialPosition`، إلخ).
قبول `BackendProducer`/`BackendConsumer` بدلاً من عميل Pulsar.
تفويض عمليات النشر/الاشتراك الفعلية إلى مثيلات الواجهة الخلفية.
مطابقة المفاهيم العامة إلى استدعاءات الواجهة الخلفية.

**مثال على إعادة الهيكلة:**

```python
# OLD - consumer.py
class Consumer:
    def __init__(self, client, topic, subscriber, schema, ...):
        self.client = client  # Direct Pulsar client
        # ...

    async def consumer_run(self):
        # Uses pulsar.InitialPosition, pulsar.ConsumerType
        self.consumer = self.client.subscribe(
            topic=self.topic,
            schema=JsonSchema(self.schema),
            initial_position=pulsar.InitialPosition.Earliest,
            consumer_type=pulsar.ConsumerType.Shared,
        )

# NEW - consumer.py
class Consumer:
    def __init__(self, backend_consumer, schema, ...):
        self.backend_consumer = backend_consumer  # Backend-specific consumer
        self.schema = schema
        # ...

    async def consumer_run(self):
        # Backend consumer already created with right settings
        # Just use it directly
        while self.running:
            msg = await asyncio.to_thread(
                self.backend_consumer.receive,
                timeout_millis=2000
            )
            await self.handle_message(msg)
```

### السلوكيات الخاصة بالخادم الخلفي

**الخادم الخلفي Pulsar:**
يربط `q0` → `non-persistent://`، و `q1`/`q2` → `persistent://`
يدعم جميع أنواع المستهلكين (مشترك، حصري، احتياطي)
يدعم الموضع الأولي (الأول/الأخير)
إقرار الرسائل الأصلي
دعم سجل المخططات

**الخادم الخلفي MQTT:**
يربط `q0`/`q1`/`q2` بمستويات جودة الخدمة MQTT 0/1/2
يتضمن المستأجر/المساحة الاسمية في مسار الموضوع لعملية التمييز
يقوم بإنشاء معرفات العملاء تلقائيًا من أسماء الاشتراكات
يتجاهل الموضع الأولي (لا يوجد سجل رسائل في MQTT الأساسي)
يتجاهل نوع المستهلك (يستخدم MQTT معرفات العملاء، وليس مجموعات المستهلكين)
نموذج نشر/اشتراك بسيط

### ملخص قرارات التصميم

1. ✅ **تسمية قائمة انتظار عامة**: بتنسيق `qos/tenant/namespace/queue-name`
2. ✅ **جودة الخدمة في معرف قائمة الانتظار**: يتم تحديدها بواسطة تعريف قائمة الانتظار، وليس التكوين
3. ✅ **إعادة الاتصال**: تتم معالجتها بواسطة فئات المستهلك/المنتج، وليس الخوادم الخلفية
4. ✅ **مواضيع MQTT**: تتضمن المستأجر/المساحة الاسمية لعملية التمييز المناسبة
5. ✅ **سجل الرسائل**: يتجاهل MQTT معلمة `initial_position` (تحسين مستقبلي)
6. ✅ **معرفات العملاء**: يقوم خادم MQTT بإنشائها تلقائيًا من اسم الاشتراك

### التحسينات المستقبلية

**سجل رسائل MQTT:**
يمكن إضافة طبقة تخزين اختيارية (مثل الرسائل المحفوظة، أو مخزن خارجي)
سيسمح بدعم `initial_position='earliest'`
ليس مطلوبًا للتنفيذ الأولي
