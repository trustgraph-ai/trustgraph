---
layout: default
title: "مواصفات فنية: توحيد إعدادات Cassandra"
parent: "Arabic (Beta)"
---

# مواصفات فنية: توحيد إعدادات Cassandra

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

**الحالة:** مسودة
**المؤلف:** مساعد
**التاريخ:** 2024-09-03

## نظرة عامة

تتناول هذه المواصفة عدم الاتساق في أسماء وأنماط إعدادات معلمات اتصال Cassandra عبر قاعدة بيانات TrustGraph. حاليًا، توجد مخططان مختلفان لتسمية المعلمات (`cassandra_*` مقابل `graph_*`)، مما يؤدي إلى الارتباك وتعقيد الصيانة.

## بيان المشكلة

تستخدم قاعدة البيانات حاليًا مجموعتين متميزتين من معلمات إعداد Cassandra:

1. **وحدات المعرفة/التكوين/المكتبة** تستخدم:
   `cassandra_host` (قائمة المضيفين)
   `cassandra_user`
   `cassandra_password`

2. **وحدات الرسم البياني/التخزين** تستخدم:
   `graph_host` (مضيف واحد، يتم تحويله أحيانًا إلى قائمة)
   `graph_username`
   `graph_password`

3. **عرض غير متسق عبر سطر الأوامر**:
   بعض المعالجات (مثل `kg-store`) لا تعرض إعدادات Cassandra كمعلمات سطر أوامر
   تعرض معالجات أخرى هذه الإعدادات بأسماء وتنسيقات مختلفة
   لا يعكس نص المساعدة القيم الافتراضية لمتغيرات البيئة

تتصل كلتا مجموعتي المعلمات بنفس مجموعة Cassandra ولكن باتفاقيات تسمية مختلفة، مما يسبب:
ارتباك في التكوين للمستخدمين
زيادة العبء على الصيانة
توثيق غير متسق
احتمال حدوث سوء تكوين
عدم القدرة على تجاوز الإعدادات عبر سطر الأوامر في بعض المعالجات

## الحل المقترح

### 1. توحيد أسماء المعلمات

ستستخدم جميع الوحدات أسماء معلمات متسقة `cassandra_*`:
`cassandra_host` - قائمة المضيفين (مخزنة داخليًا كقائمة)
`cassandra_username` - اسم المستخدم للمصادقة
`cassandra_password` - كلمة المرور للمصادقة

### 2. معلمات سطر الأوامر

يجب على جميع المعالجات عرض إعدادات تكوين Cassandra عبر معلمات سطر الأوامر:
`--cassandra-host` - قائمة مفصولة بفواصل من المضيفين
`--cassandra-username` - اسم المستخدم للمصادقة
`--cassandra-password` - كلمة المرور للمصادقة

### 3. الاعتماد على متغيرات البيئة

إذا لم يتم توفير معلمات سطر الأوامر بشكل صريح، فسيتحقق النظام من متغيرات البيئة:
`CASSANDRA_HOST` - قائمة مفصولة بفواصل من المضيفين
`CASSANDRA_USERNAME` - اسم المستخدم للمصادقة
`CASSANDRA_PASSWORD` - كلمة المرور للمصادقة

### 4. القيم الافتراضية

إذا لم يتم تحديد أي من معلمات سطر الأوامر أو متغيرات البيئة:
`cassandra_host` افتراضيًا إلى `["cassandra"]`
`cassandra_username` افتراضيًا إلى `None` (بدون مصادقة)
`cassandra_password` افتراضيًا إلى `None` (بدون مصادقة)

### 5. متطلبات نص المساعدة

يجب أن يعرض الإخراج `--help`:
إظهار قيم متغيرات البيئة كقيم افتراضية عند تعيينها
عدم عرض قيم كلمات المرور مطلقًا (إظهار `****` أو `<set>` بدلاً من ذلك)
الإشارة بوضوح إلى ترتيب الحل في نص المساعدة

مثال على إخراج المساعدة:
```
--cassandra-host HOST
    Cassandra host list, comma-separated (default: prod-cluster-1,prod-cluster-2)
    [from CASSANDRA_HOST environment variable]

--cassandra-username USERNAME
    Cassandra username (default: cassandra_user)
    [from CASSANDRA_USERNAME environment variable]
    
--cassandra-password PASSWORD  
    Cassandra password (default: <set from environment>)
```

## تفاصيل التنفيذ

### ترتيب حل المعلمات

لكل معلمة في Cassandra، سيكون ترتيب الحل كما يلي:
1. قيمة وسيط سطر الأوامر
2. متغير البيئة (`CASSANDRA_*`)
3. القيمة الافتراضية

### معالجة معلمات المضيف

المعلمة `cassandra_host`:
يقبل سطر الأوامر سلسلة مفصولة بفواصل: `--cassandra-host "host1,host2,host3"`
يقبل متغير البيئة سلسلة مفصولة بفواصل: `CASSANDRA_HOST="host1,host2,host3"`
يتم تخزينها دائمًا داخليًا كقائمة: `["host1", "host2", "host3"]`
مضيف واحد: `"localhost"` → يتم تحويله إلى `["localhost"]`
إذا كانت بالفعل قائمة: `["host1", "host2"]` → يتم استخدامها كما هي

### منطق المصادقة

سيتم استخدام المصادقة عندما يتم توفير كل من `cassandra_username` و `cassandra_password`:
```python
if cassandra_username and cassandra_password:
    # Use SSL context and PlainTextAuthProvider
else:
    # Connect without authentication
```

## الملفات المراد تعديلها

### الوحدات التي تستخدم معلمات `graph_*` (يجب تغييرها):
`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/rows/cassandra/write.py`
`trustgraph-flow/trustgraph/query/triples/cassandra/service.py`

### الوحدات التي تستخدم معلمات `cassandra_*` (يجب تحديثها مع استخدام الإعدادات الافتراضية للبيئة):
`trustgraph-flow/trustgraph/tables/config.py`
`trustgraph-flow/trustgraph/tables/knowledge.py`
`trustgraph-flow/trustgraph/tables/library.py`
`trustgraph-flow/trustgraph/storage/knowledge/store.py`
`trustgraph-flow/trustgraph/cores/knowledge.py`
`trustgraph-flow/trustgraph/librarian/librarian.py`
`trustgraph-flow/trustgraph/librarian/service.py`
`trustgraph-flow/trustgraph/config/service/service.py`
`trustgraph-flow/trustgraph/cores/service.py`

### ملفات الاختبار المراد تحديثها:
`tests/unit/test_cores/test_knowledge_manager.py`
`tests/unit/test_storage/test_triples_cassandra_storage.py`
`tests/unit/test_query/test_triples_cassandra_query.py`
`tests/integration/test_objects_cassandra_integration.py`

## استراتيجية التنفيذ

### المرحلة الأولى: إنشاء أداة مساعدة للإعدادات المشتركة
إنشاء دوال مساعدة لتوحيد إعدادات Cassandra عبر جميع المعالجات:

```python
import os
import argparse

def get_cassandra_defaults():
    """Get default values from environment variables or fallback."""
    return {
        'host': os.getenv('CASSANDRA_HOST', 'cassandra'),
        'username': os.getenv('CASSANDRA_USERNAME'),
        'password': os.getenv('CASSANDRA_PASSWORD')
    }

def add_cassandra_args(parser: argparse.ArgumentParser):
    """
    Add standardized Cassandra arguments to an argument parser.
    Shows environment variable values in help text.
    """
    defaults = get_cassandra_defaults()
    
    # Format help text with env var indication
    host_help = f"Cassandra host list, comma-separated (default: {defaults['host']})"
    if 'CASSANDRA_HOST' in os.environ:
        host_help += " [from CASSANDRA_HOST]"
    
    username_help = f"Cassandra username"
    if defaults['username']:
        username_help += f" (default: {defaults['username']})"
        if 'CASSANDRA_USERNAME' in os.environ:
            username_help += " [from CASSANDRA_USERNAME]"
    
    password_help = "Cassandra password"
    if defaults['password']:
        password_help += " (default: <set>)"
        if 'CASSANDRA_PASSWORD' in os.environ:
            password_help += " [from CASSANDRA_PASSWORD]"
    
    parser.add_argument(
        '--cassandra-host',
        default=defaults['host'],
        help=host_help
    )
    
    parser.add_argument(
        '--cassandra-username',
        default=defaults['username'],
        help=username_help
    )
    
    parser.add_argument(
        '--cassandra-password',
        default=defaults['password'],
        help=password_help
    )

def resolve_cassandra_config(args) -> tuple[list[str], str|None, str|None]:
    """
    Convert argparse args to Cassandra configuration.
    
    Returns:
        tuple: (hosts_list, username, password)
    """
    # Convert host string to list
    if isinstance(args.cassandra_host, str):
        hosts = [h.strip() for h in args.cassandra_host.split(',')]
    else:
        hosts = args.cassandra_host
    
    return hosts, args.cassandra_username, args.cassandra_password
```

### المرحلة الثانية: تحديث الوحدات باستخدام معلمات `graph_*`
1. تغيير أسماء المعلمات من `graph_*` إلى `cassandra_*`
2. استبدال طرق `add_args()` المخصصة بطرق `add_cassandra_args()` القياسية
3. استخدام الدوال المساعدة الشائعة للتكوين
4. تحديث سلاسل التوثيق

مثال على التحويل:
```python
# OLD CODE
@staticmethod
def add_args(parser):
    parser.add_argument(
        '-g', '--graph-host',
        default="localhost",
        help=f'Graph host (default: localhost)'
    )
    parser.add_argument(
        '--graph-username',
        default=None,
        help=f'Cassandra username'
    )

# NEW CODE  
@staticmethod
def add_args(parser):
    FlowProcessor.add_args(parser)
    add_cassandra_args(parser)  # Use standard helper
```

### المرحلة الثالثة: تحديث الوحدات باستخدام معلمات `cassandra_*`
1. إضافة دعم للوسائط الخاصة بسطر الأوامر في الحالات التي تفتقر إليها (مثل: `kg-store`)
2. استبدال تعريفات الوسائط الحالية بـ `add_cassandra_args()`
3. استخدام `resolve_cassandra_config()` لتحقيق التوافق
4. التأكد من معالجة متسقة لقائمة المضيفين

### المرحلة الرابعة: تحديث الاختبارات والوثائق
1. تحديث جميع ملفات الاختبار لاستخدام أسماء المعلمات الجديدة
2. تحديث وثائق واجهة سطر الأوامر
3. تحديث وثائق واجهة برمجة التطبيقات
4. إضافة وثائق لمتغيرات البيئة

## التوافق مع الإصدارات السابقة

للحفاظ على التوافق مع الإصدارات السابقة أثناء الانتقال:

1. **تحذيرات الإيقاف التدريجي** لمعلمات `graph_*`
2. **تسمية بديلة للمعلمات** - قبول الأسماء القديمة والجديدة في البداية
3. **نشر تدريجي** على مدار عدة إصدارات
4. **تحديثات الوثائق** مع دليل الترحيل

مثال على كود التوافق مع الإصدارات السابقة:
```python
def __init__(self, **params):
    # Handle deprecated graph_* parameters
    if 'graph_host' in params:
        warnings.warn("graph_host is deprecated, use cassandra_host", DeprecationWarning)
        params.setdefault('cassandra_host', params.pop('graph_host'))
    
    if 'graph_username' in params:
        warnings.warn("graph_username is deprecated, use cassandra_username", DeprecationWarning)
        params.setdefault('cassandra_username', params.pop('graph_username'))
    
    # ... continue with standard resolution
```

## استراتيجية الاختبار

1. **اختبارات الوحدة** لمنطق حل التكوين.
2. **اختبارات التكامل** مع مجموعات تكوين مختلفة.
3. **اختبارات متغيرات البيئة**.
4. **اختبارات التوافق مع الإصدارات السابقة** مع المعلمات التي تم إيقافها.
5. **اختبارات Docker Compose** مع متغيرات البيئة.

## تحديثات التوثيق

1. تحديث جميع وثائق أوامر واجهة سطر الأوامر.
2. تحديث وثائق واجهة برمجة التطبيقات.
3. إنشاء دليل ترحيل.
4. تحديث أمثلة Docker Compose.
5. تحديث وثائق مرجع التكوين.

## المخاطر والتخفيف

| المخاطر | التأثير | التخفيف |
|------|--------|------------|
| تغييرات تؤثر على المستخدمين | مرتفع | تطبيق فترة التوافق مع الإصدارات السابقة. |
| ارتباك في التكوين أثناء الانتقال | متوسط | توثيق واضح وتحذيرات إيقاف. |
| فشل الاختبارات | متوسط | تحديثات شاملة للاختبارات. |
| مشاكل في نشر Docker | مرتفع | تحديث جميع أمثلة Docker Compose. |

## معايير النجاح

[ ] تستخدم جميع الوحدات أسماء معلمات `cassandra_*` متسقة.
[ ] تعرض جميع المعالجات إعدادات Cassandra عبر وسيطات سطر الأوامر.
[ ] يعرض نص المساعدة الخاص بسطر الأوامر القيم الافتراضية لمتغيرات البيئة.
[ ] لا يتم عرض قيم كلمات المرور في نص المساعدة.
[ ] يعمل التراجع إلى متغيرات البيئة بشكل صحيح.
[ ] يتم التعامل مع `cassandra_host` باستمرار كقائمة داخليًا.
[ ] تم الحفاظ على التوافق مع الإصدارات السابقة لمدة إصدارين على الأقل.
[ ] تجتاز جميع الاختبارات مع نظام التكوين الجديد.
[ ] تم تحديث التوثيق بالكامل.
[ ] تعمل أمثلة Docker Compose مع متغيرات البيئة.

## الجدول الزمني

**الأسبوع 1:** تنفيذ أداة مساعدة شائعة للتكوين وتحديث وحدات `graph_*`.
**الأسبوع 2:** إضافة دعم لمتغيرات البيئة إلى وحدات `cassandra_*` الحالية.
**الأسبوع 3:** تحديث الاختبارات والتوثيق.
**الأسبوع 4:** اختبار التكامل وتصحيح الأخطاء.

## اعتبارات مستقبلية

ضع في اعتبارك توسيع هذا النمط ليشمل تكوينات قواعد بيانات أخرى (مثل Elasticsearch).
تنفيذ التحقق من صحة التكوين ورسائل خطأ أفضل.
إضافة دعم لتكوين تجميع الاتصالات لـ Cassandra.
ضع في اعتبارك إضافة دعم لملفات التكوين (ملفات .env).
