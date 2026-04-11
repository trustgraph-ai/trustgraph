---
layout: default
title: "المواصفات الفنية: دعم تخزين متوافق مع S3"
parent: "Arabic (Beta)"
---

# المواصفات الفنية: دعم تخزين متوافق مع S3

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## نظرة عامة

تستخدم خدمة Librarian تخزين كائنات متوافق مع S3 لتخزين ملفات المستندات. توثق هذه المواصفة التنفيذ الذي يمكّن الدعم لأي نظام تخزين متوافق مع S3 بما في ذلك MinIO و Ceph RADOS Gateway (RGW) و AWS S3 و Cloudflare R2 و DigitalOcean Spaces وغيرها.

## البنية

### مكونات التخزين
**تخزين الكائنات (Blob Storage)**: تخزين كائنات متوافق مع S3 عبر مكتبة عميل Python `minio`
**تخزين البيانات الوصفية (Metadata Storage)**: Cassandra (تخزن مطابقة object_id وبيانات وصفية للمستندات)
**المكون المتأثر**: خدمة Librarian فقط
**نمط التخزين**: تخزين هجين مع البيانات الوصفية في Cassandra والمحتوى في تخزين متوافق مع S3

### التنفيذ
**المكتبة**: عميل Python `minio` (يدعم أي واجهة برمجة تطبيقات متوافقة مع S3)
**الموقع**: `trustgraph-flow/trustgraph/librarian/blob_store.py`
**العمليات**:
  `add()` - تخزين كائن بمعرف كائن UUID
  `get()` - استرجاع كائن بمعرف الكائن
  `remove()` - حذف كائن بمعرف الكائن
  `ensure_bucket()` - إنشاء حاوية إذا لم تكن موجودة
**الحاوية (Bucket)**: `library`
**مسار الكائن (Object Path)**: `doc/{object_id}`
**أنواع MIME المدعومة**: `text/plain`، `application/pdf`

### الملفات الرئيسية
1. `trustgraph-flow/trustgraph/librarian/blob_store.py` - تطبيق BlobStore
2. `trustgraph-flow/trustgraph/librarian/librarian.py` - تهيئة BlobStore
3. `trustgraph-flow/trustgraph/librarian/service.py` - تكوين الخدمة
4. `trustgraph-flow/pyproject.toml` - التبعيات (حزمة `minio`)
5. `docs/apis/api-librarian.md` - وثائق API

## أنظمة التخزين المدعومة

يعمل هذا التنفيذ مع أي نظام تخزين كائنات متوافق مع S3:

### تم الاختبار/مدعوم
**Ceph RADOS Gateway (RGW)** - نظام تخزين موزع مع واجهة برمجة تطبيقات S3 (التكوين الافتراضي)
**MinIO** - تخزين كائنات خفيف الوزن ومستضاف ذاتيًا
**Garage** - تخزين S3 متوافق وخفيف الوزن وموزع جغرافيًا

### يجب أن يعمل (متوافق مع S3)
**AWS S3** - تخزين الكائنات السحابي من Amazon
**Cloudflare R2** - تخزين S3 متوافق من Cloudflare
**DigitalOcean Spaces** - تخزين الكائنات من DigitalOcean
**Wasabi** - تخزين سحابي متوافق مع S3
**Backblaze B2** - تخزين نسخ احتياطي متوافق مع S3
أي خدمة أخرى تنفذ واجهة برمجة تطبيقات S3 REST

## التكوين

### وسائط سطر الأوامر

```bash
librarian \
  --object-store-endpoint <hostname:port> \
  --object-store-access-key <access_key> \
  --object-store-secret-key <secret_key> \
  [--object-store-use-ssl] \
  [--object-store-region <region>]
```

**ملاحظة:** لا تقم بتضمين `http://` أو `https://` في النهاية. استخدم `--object-store-use-ssl` لتمكين HTTPS.

### متغيرات البيئة (بديل)

```bash
OBJECT_STORE_ENDPOINT=<hostname:port>
OBJECT_STORE_ACCESS_KEY=<access_key>
OBJECT_STORE_SECRET_KEY=<secret_key>
OBJECT_STORE_USE_SSL=true|false  # Optional, default: false
OBJECT_STORE_REGION=<region>     # Optional
```

### أمثلة

**بوابة Ceph RADOS (افتراضيًا):**
```bash
--object-store-endpoint ceph-rgw:7480 \
--object-store-access-key object-user \
--object-store-secret-key object-password
```

**مينيو:**
```bash
--object-store-endpoint minio:9000 \
--object-store-access-key minioadmin \
--object-store-secret-key minioadmin
```

**مخزن (متوافق مع S3):**
```bash
--object-store-endpoint garage:3900 \
--object-store-access-key GK000000000000000000000001 \
--object-store-secret-key b171f00be9be4c32c734f4c05fe64c527a8ab5eb823b376cfa8c2531f70fc427
```

**AWS S3 مع SSL:**
```bash
--object-store-endpoint s3.amazonaws.com \
--object-store-access-key AKIAIOSFODNN7EXAMPLE \
--object-store-secret-key wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY \
--object-store-use-ssl \
--object-store-region us-east-1
```

## المصادقة

تتطلب جميع الواجهات الخلفية المتوافقة مع S3 مصادقة AWS Signature Version 4 (أو الإصدار 2):

**مفتاح الوصول (Access Key)** - مُعرّف عام (مثل اسم المستخدم)
**المفتاح السري (Secret Key)** - مفتاح توقيع خاص (مثل كلمة المرور)

يتعامل عميل MinIO بلغة Python مع جميع عمليات حساب التوقيع تلقائيًا.

### إنشاء بيانات الاعتماد

**لـ MinIO:**
```bash
# Use default credentials or create user via MinIO Console
minioadmin / minioadmin
```

**لـ Ceph RGW:**
```bash
radosgw-admin user create --uid="trustgraph" --display-name="TrustGraph Service"
# Returns access_key and secret_key
```

**لـ AWS S3:**
إنشاء مستخدم IAM مع أذونات S3.
إنشاء مفتاح وصول في وحدة تحكم AWS.

## اختيار المكتبة: عميل MinIO Python

**السبب:**
خفيف الوزن (~500 كيلوبايت مقابل ~50 ميجابايت لـ boto3).
متوافق مع S3 - يعمل مع أي نقطة نهاية S3.
واجهة برمجة تطبيقات أبسط من boto3 للعمليات الأساسية.
قيد الاستخدام بالفعل، لا حاجة إلى ترحيل.
تم اختباره بشكل مكثف مع MinIO وأنظمة S3 الأخرى.

## تنفيذ BlobStore

**الموقع:** `trustgraph-flow/trustgraph/librarian/blob_store.py`

```python
from minio import Minio
import io
import logging

logger = logging.getLogger(__name__)

class BlobStore:
    """
    S3-compatible blob storage for document content.
    Supports MinIO, Ceph RGW, AWS S3, and other S3-compatible backends.
    """

    def __init__(self, endpoint, access_key, secret_key, bucket_name,
                 use_ssl=False, region=None):
        """
        Initialize S3-compatible blob storage.

        Args:
            endpoint: S3 endpoint (e.g., "minio:9000", "ceph-rgw:7480")
            access_key: S3 access key
            secret_key: S3 secret key
            bucket_name: Bucket name for storage
            use_ssl: Use HTTPS instead of HTTP (default: False)
            region: S3 region (optional, e.g., "us-east-1")
        """
        self.client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=use_ssl,
            region=region,
        )

        self.bucket_name = bucket_name

        protocol = "https" if use_ssl else "http"
        logger.info(f"Connected to S3-compatible storage at {protocol}://{endpoint}")

        self.ensure_bucket()

    def ensure_bucket(self):
        """Create bucket if it doesn't exist"""
        found = self.client.bucket_exists(bucket_name=self.bucket_name)
        if not found:
            self.client.make_bucket(bucket_name=self.bucket_name)
            logger.info(f"Created bucket {self.bucket_name}")
        else:
            logger.debug(f"Bucket {self.bucket_name} already exists")

    async def add(self, object_id, blob, kind):
        """Store blob in S3-compatible storage"""
        self.client.put_object(
            bucket_name=self.bucket_name,
            object_name=f"doc/{object_id}",
            length=len(blob),
            data=io.BytesIO(blob),
            content_type=kind,
        )
        logger.debug("Add blob complete")

    async def remove(self, object_id):
        """Delete blob from S3-compatible storage"""
        self.client.remove_object(
            bucket_name=self.bucket_name,
            object_name=f"doc/{object_id}",
        )
        logger.debug("Remove blob complete")

    async def get(self, object_id):
        """Retrieve blob from S3-compatible storage"""
        resp = self.client.get_object(
            bucket_name=self.bucket_name,
            object_name=f"doc/{object_id}",
        )
        return resp.read()
```

## الفوائد الرئيسية

1. **لا يوجد اعتماد على مورد واحد** - يعمل مع أي تخزين متوافق مع S3.
2. **خفيف الوزن** - حجم عميل MinIO يبلغ حوالي 500 كيلوبايت فقط.
3. **تكوين بسيط** - يتطلب فقط نقطة النهاية وبيانات الاعتماد.
4. **لا حاجة لنقل البيانات** - بديل مباشر بين الأنظمة الخلفية.
5. **تم اختباره ميدانيًا** - يعمل عميل MinIO مع جميع تطبيقات S3 الرئيسية.

## حالة التنفيذ

تم تحديث جميع التعليمات البرمجية لاستخدام أسماء معلمات S3 العامة:

✅ `blob_store.py` - تم التحديث لقبول `endpoint`، `access_key`، `secret_key`.
✅ `librarian.py` - تم تحديث أسماء المعلمات.
✅ `service.py` - تم تحديث وسيطات سطر الأوامر والتكوين.
✅ تم تحديث الوثائق.

## التحسينات المستقبلية

1. **دعم SSL/TLS** - إضافة علامة `--s3-use-ssl` لـ HTTPS.
2. **منطق إعادة المحاولة** - تطبيق تأخير أُسي للأخطاء العابرة.
3. **عناوين URL مؤقتة** - إنشاء عناوين URL مؤقتة للتحميل/التنزيل.
4. **دعم متعدد المناطق** - تكرار الكائنات عبر المناطق.
5. **تكامل CDN** - تقديم الكائنات عبر CDN.
6. **فئات التخزين** - استخدام فئات تخزين S3 لتحسين التكلفة.
7. **سياسات دورة الحياة** - الأرشفة/الحذف التلقائي.
8. **التحكم في الإصدار** - تخزين إصدارات متعددة من الكائنات.

## المراجع

عميل MinIO Python: https://min.io/docs/minio/linux/developers/python/API.html
واجهة برمجة تطبيقات Ceph RGW S3: https://docs.ceph.com/en/latest/radosgw/s3/
مرجع واجهة برمجة تطبيقات S3: https://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html
