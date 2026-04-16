---
layout: default
title: "استراتيجية تسجيل الأحداث في TrustGraph"
parent: "Arabic (Beta)"
---

# استراتيجية تسجيل الأحداث في TrustGraph

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## نظرة عامة

تستخدم TrustGraph الوحدة `logging` المضمنة في Python لجميع عمليات التسجيل، مع تكوين مركزي ودمج اختياري مع Loki لتجميع السجلات. يوفر هذا نهجًا موحدًا ومرنًا لتسجيل الأحداث عبر جميع مكونات النظام.

## التكوين الافتراضي

### مستوى التسجيل
**المستوى الافتراضي**: `INFO`
**يمكن تكوينه عبر**: وسيط سطر الأوامر `--log-level`
**الخيارات**: `DEBUG`، `INFO`، `WARNING`، `ERROR`، `CRITICAL`

### وجهات الإخراج
1. **وحدة التحكم (stdout)**: مفعل دائمًا - يضمن التوافق مع البيئات الحاويات.
2. **Loki**: تجميع سجلات مركزي اختياري (مفعل افتراضيًا، ويمكن تعطيله).

## وحدة التسجيل المركزية

تتم إدارة جميع تكوينات التسجيل بواسطة الوحدة `trustgraph.base.logging`، والتي توفر:
`add_logging_args(parser)` - يضيف وسيطات سطر الأوامر القياسية لتسجيل الأحداث.
`setup_logging(args)` - يقوم بتكوين التسجيل من الوسائط التي تم تحليلها.

يتم استخدام هذا الوحدة بواسطة جميع المكونات من جانب الخادم:
الخدمات القائمة على AsyncProcessor
بوابة API
خادم MCP

## إرشادات التنفيذ

### 1. تهيئة المسجل

يجب على كل وحدة إنشاء مسجل خاص بها باستخدام وحدة `__name__` الخاصة بالوحدة:

```python
import logging

logger = logging.getLogger(__name__)
```

اسم المسجل يُستخدم تلقائيًا كعلامة في Loki لتصفية البحث.

### 2. تهيئة الخدمة

تتلقى جميع الخدمات من جهة الخادم تلقائيًا تكوين التسجيل من خلال الوحدة المركزية:

```python
from trustgraph.base import add_logging_args, setup_logging
import argparse

def main():
    parser = argparse.ArgumentParser()

    # Add standard logging arguments (includes Loki configuration)
    add_logging_args(parser)

    # Add your service-specific arguments
    parser.add_argument('--port', type=int, default=8080)

    args = parser.parse_args()
    args = vars(args)

    # Setup logging early in startup
    setup_logging(args)

    # Rest of your service initialization
    logger = logging.getLogger(__name__)
    logger.info("Service starting...")
```

### 3. وسيطات سطر الأوامر

تدعم جميع الخدمات وسيطات التسجيل التالية:

**مستوى التسجيل:**
```bash
--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
```

**تكوين لوكي:**
```bash
--loki-enabled              # Enable Loki (default)
--no-loki-enabled           # Disable Loki
--loki-url URL              # Loki push URL (default: http://loki:3100/loki/api/v1/push)
--loki-username USERNAME    # Optional authentication
--loki-password PASSWORD    # Optional authentication
```

**أمثلة:**
```bash
# Default - INFO level, Loki enabled
./my-service

# Debug mode, console only
./my-service --log-level DEBUG --no-loki-enabled

# Custom Loki server with auth
./my-service --loki-url http://loki.prod:3100/loki/api/v1/push \
             --loki-username admin --loki-password secret
```

### 4. متغيرات البيئة

تدعم إعدادات Loki استخدام متغيرات البيئة كبدائل:

```bash
export LOKI_URL=http://loki.prod:3100/loki/api/v1/push
export LOKI_USERNAME=admin
export LOKI_PASSWORD=secret
```

تتجاوز وسائط سطر الأوامر قيم المتغيرات البيئية.

### 5. أفضل الممارسات في التسجيل.

#### استخدام مستويات التسجيل.
**DEBUG**: معلومات تفصيلية لتشخيص المشكلات (قيم المتغيرات، دخول/خروج الدالة).
**INFO**: رسائل معلومات عامة (بدء الخدمة، تحميل التكوين، مراحل المعالجة).
**WARNING**: رسائل تحذيرية لحالات قد تكون ضارة (ميزات مهملة، أخطاء قابلة للاسترداد).
**ERROR**: رسائل خطأ للمشاكل الخطيرة (عمليات فاشلة، استثناءات).
**CRITICAL**: رسائل حرجة لأعطال النظام التي تتطلب اهتمامًا فوريًا.

#### تنسيق الرسالة.
```python
# Good - includes context
logger.info(f"Processing document: {doc_id}, size: {doc_size} bytes")
logger.error(f"Failed to connect to database: {error}", exc_info=True)

# Avoid - lacks context
logger.info("Processing document")
logger.error("Connection failed")
```

#### اعتبارات الأداء
```python
# Use lazy formatting for expensive operations
logger.debug("Expensive operation result: %s", expensive_function())

# Check log level for very expensive debug operations
if logger.isEnabledFor(logging.DEBUG):
    debug_data = compute_expensive_debug_info()
    logger.debug(f"Debug data: {debug_data}")
```

### 6. التسجيل المنظم باستخدام لوكي

بالنسبة للبيانات المعقدة، استخدم التسجيل المنظم مع علامات إضافية لـ Loki:

```python
logger.info("Request processed", extra={
    'tags': {
        'request_id': request_id,
        'user_id': user_id,
        'status': 'success'
    }
})
```

تصبح هذه العلامات تصنيفات قابلة للبحث في Loki، بالإضافة إلى التصنيفات التلقائية:
`severity` - مستوى التسجيل (DEBUG، INFO، WARNING، ERROR، CRITICAL)
`logger` - اسم الوحدة (من `__name__`)

### 7. تسجيل الاستثناءات

قم دائمًا بتضمين تتبعات المكدس للاستثناءات:

```python
try:
    process_data()
except Exception as e:
    logger.error(f"Failed to process data: {e}", exc_info=True)
    raise
```

### 8. اعتبارات التسجيل غير المتزامن

يستخدم نظام التسجيل معالجات غير متزامنة ومخزنة مؤقتًا لـ Loki:
الإخراج إلى وحدة التحكم متزامن (سريع)
يتم تخزين إخراج Loki في قائمة انتظار مع مخزن مؤقت مكون من 500 رسالة
يقوم خيط الخلفية بمعالجة إرسال Loki
لا يوجد حظر لرمز التطبيق الرئيسي

```python
import asyncio
import logging

async def async_operation():
    logger = logging.getLogger(__name__)
    # Logging is thread-safe and won't block async operations
    logger.info(f"Starting async operation in task: {asyncio.current_task().get_name()}")
```

## التكامل مع Loki

### البنية التحتية

يستخدم نظام التسجيل وظائف `QueueHandler` و `QueueListener` المضمنة في Python للتكامل غير المتزامن مع Loki:

1. **QueueHandler**: يتم وضع السجلات في قائمة انتظار تحتوي على 500 رسالة (غير متزامنة).
2. **Background Thread**: يرسل QueueListener السجلات إلى Loki بشكل غير متزامن.
3. **Graceful Degradation**: إذا كان Loki غير متاح، يستمر التسجيل في وحدة التحكم.

### التسميات التلقائية

تتضمن كل سجل يتم إرساله إلى Loki:
`processor`: هوية المعالج (مثل `config-svc`، `text-completion`، `embeddings`).
`severity`: مستوى السجل (DEBUG، INFO، إلخ).
`logger`: اسم الوحدة (مثل `trustgraph.gateway.service`، `trustgraph.agent.react.service`).

### التسميات المخصصة

أضف تسميات مخصصة عبر المعامل `extra`:

```python
logger.info("User action", extra={
    'tags': {
        'user_id': user_id,
        'action': 'document_upload',
        'collection': collection_name
    }
})
```

### الاستعلام عن السجلات في Loki

```logql
# All logs from a specific processor (recommended - matches Prometheus metrics)
{processor="config-svc"}
{processor="text-completion"}
{processor="embeddings"}

# Error logs from a specific processor
{processor="config-svc", severity="ERROR"}

# Error logs from all processors
{severity="ERROR"}

# Logs from a specific processor with text filter
{processor="text-completion"} |= "Processing"

# All logs from API gateway
{processor="api-gateway"}

# Logs from processors matching pattern
{processor=~".*-completion"}

# Logs with custom tags
{processor="api-gateway"} | json | user_id="12345"
```

### التدهور الأنيق

إذا كان Loki غير متاح أو لم يتم تثبيت `python-logging-loki`:
يتم طباعة رسالة تحذير على وحدة التحكم.
يستمر تسجيل الأحداث في وحدة التحكم بشكل طبيعي.
يستمر التطبيق في العمل.
لا توجد آلية لإعادة المحاولة لاتصال Loki (الفشل السريع، والتدهور الأنيق).

## الاختبار

أثناء الاختبار، ضع في اعتبارك استخدام تكوين تسجيل مختلف:

```python
# In test setup
import logging

# Reduce noise during tests
logging.getLogger().setLevel(logging.WARNING)

# Or disable Loki for tests
setup_logging({'log_level': 'WARNING', 'loki_enabled': False})
```

## التكامل مع نظام المراقبة

### التنسيق القياسي
جميع السجلات تستخدم تنسيقًا متسقًا:
```
2025-01-09 10:30:45,123 - trustgraph.gateway.service - INFO - Request processed
```

مكونات التنسيق:
الطابع الزمني (بتنسيق ISO مع أجزاء من الثانية)
اسم المسجل (مسار الوحدة)
مستوى التسجيل
الرسالة

### استعلامات Loki للمراقبة

استعلامات مراقبة شائعة:

```logql
# Error rate by processor
rate({severity="ERROR"}[5m]) by (processor)

# Top error-producing processors
topk(5, count_over_time({severity="ERROR"}[1h]) by (processor))

# Recent errors with processor name
{severity="ERROR"} | line_format "{{.processor}}: {{.message}}"

# All agent processors
{processor=~".*agent.*"} |= "exception"

# Specific processor error count
count_over_time({processor="config-svc", severity="ERROR"}[1h])
```

## اعتبارات الأمان

**لا تقم أبدًا بتسجيل معلومات حساسة** (كلمات المرور، مفاتيح API، البيانات الشخصية، الرموز)
**قم بتنظيف مدخلات المستخدم** قبل التسجيل
**استخدم قيمًا محجوزة** للحقول الحساسة: `user_id=****1234`
**مصادقة Loki**: استخدم `--loki-username` و `--loki-password` للنشر الآمن
**نقل آمن**: استخدم HTTPS لعنوان URL الخاص بـ Loki في بيئة الإنتاج: `https://loki.prod:3100/loki/api/v1/push`

## التبعيات

يتطلب وحدة التسجيل المركزية ما يلي:
`python-logging-loki` - لتكامل Loki (اختياري، مع إمكانية التراجع الآمن في حالة عدم وجوده)

تم تضمينها بالفعل في `trustgraph-base/pyproject.toml` و `requirements.txt`.

## مسار الترحيل

بالنسبة للكود الحالي:

1. **الخدمات التي تستخدم بالفعل AsyncProcessor**: لا توجد تغييرات مطلوبة، دعم Loki تلقائي
2. **الخدمات التي لا تستخدم AsyncProcessor** (api-gateway, mcp-server): تم تحديثها بالفعل
3. **أدوات سطر الأوامر (CLI)**: خارج نطاق العمل - استمر في استخدام print() أو التسجيل البسيط

### من print() إلى التسجيل:
```python
# Before
print(f"Processing document {doc_id}")

# After
logger = logging.getLogger(__name__)
logger.info(f"Processing document {doc_id}")
```

## ملخص الإعدادات

| الوسيط | القيمة الافتراضية | متغير البيئة | الوصف |
|----------|---------|---------------------|-------------|
| `--log-level` | `INFO` | - | مستوى تسجيل وحدة التحكم و Loki |
| `--loki-enabled` | `True` | - | تمكين تسجيل Loki |
| `--loki-url` | `http://loki:3100/loki/api/v1/push` | `LOKI_URL` | نقطة النهاية لدفع البيانات إلى Loki |
| `--loki-username` | `None` | `LOKI_USERNAME` | اسم المستخدم للمصادقة في Loki |
| `--loki-password` | `None` | `LOKI_PASSWORD` | كلمة المرور للمصادقة في Loki |
