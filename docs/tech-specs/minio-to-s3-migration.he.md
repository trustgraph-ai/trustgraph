# Tech Spec: S3-Compatible Storage Backend Support

## Overview

השירות Librarian משתמש באחסון אובייקטים תואם ל-S3 לאחסון קבצים. מסמך זה מתאר את היישום המאפשר תמיכה בכל אחסון תואם ל-S3, כולל MinIO, Ceph RADOS Gateway (RGW), AWS S3, Cloudflare R2, DigitalOcean Spaces, ואחרים.

## Architecture

### Storage Components
**Blob Storage**: אחסון אובייקטים תואם ל-S3 באמצעות `minio` ספריית לקוח Python
**Metadata Storage**: Cassandra (מאחסן מיפוי object_id ונתוני מטא-דאטה של מסמכים)
**Affected Component**: רק השירות Librarian
**Storage Pattern**: אחסון היברידי עם מטא-דאטה ב-Cassandra ותוכן באחסון תואם ל-S3

### Implementation
**Library**: `minio` לקוח Python (תומך בכל API תואם ל-S3)
**Location**: `trustgraph-flow/trustgraph/librarian/blob_store.py`
**Operations**:
  `add()` - שמירת קובץ עם מזהה אובייקט UUID
  `get()` - שליפת קובץ לפי מזהה אובייקט
  `remove()` - מחיקת קובץ לפי מזהה אובייקט
  `ensure_bucket()` - יצירת תיקייה אם היא לא קיימת
**Bucket**: `library`
**Object Path**: `doc/{object_id}`
**Supported MIME Types**: `text/plain`, `application/pdf`

### Key Files
1. `trustgraph-flow/trustgraph/librarian/blob_store.py` - יישום BlobStore
2. `trustgraph-flow/trustgraph/librarian/librarian.py` - אתחול BlobStore
3. `trustgraph-flow/trustgraph/librarian/service.py` - תצורת שירות
4. `trustgraph-flow/pyproject.toml` - תלויות (חבילת `minio`)
5. `docs/apis/api-librarian.md` - תיעוד API

## Supported Storage Backends

היישום עובד עם כל מערכת אחסון אובייקטים תואמת ל-S3:

### Tested/Supported
**Ceph RADOS Gateway (RGW)** - מערכת אחסון מבוזרת עם API של S3 (תצורת ברירת מחדל)
**MinIO** - אחסון אובייקטים קל משקל, הניתן לאירוח עצמי
**Garage** - אחסון S3-תואם, מבוזר גיאוגרפית, קל משקל

### Should Work (S3-Compatible)
**AWS S3** - אחסון אובייקטים בענן של Amazon
**Cloudflare R2** - אחסון S3-תואם של Cloudflare
**DigitalOcean Spaces** - אחסון אובייקטים של DigitalOcean
**Wasabi** - אחסון בענן S3-תואם
**Backblaze B2** - אחסון גיבוי S3-תואם
כל שירות אחר המיישם את ממשק ה-API של S3

## Configuration

### CLI Arguments

```bash
librarian \
  --object-store-endpoint <hostname:port> \
  --object-store-access-key <access_key> \
  --object-store-secret-key <secret_key> \
  [--object-store-use-ssl] \
  [--object-store-region <region>]
```

**הערה:** אל תכללו את `http://` או `https://` בסוף. השתמשו ב-`--object-store-use-ssl` כדי להפעיל HTTPS.

### משתני סביבה (חלופי)

```bash
OBJECT_STORE_ENDPOINT=<hostname:port>
OBJECT_STORE_ACCESS_KEY=<access_key>
OBJECT_STORE_SECRET_KEY=<secret_key>
OBJECT_STORE_USE_SSL=true|false  # Optional, default: false
OBJECT_STORE_REGION=<region>     # Optional
```

### דוגמאות

**שער Ceph RADOS (ברירת מחדל):**
```bash
--object-store-endpoint ceph-rgw:7480 \
--object-store-access-key object-user \
--object-store-secret-key object-password
```

**MinIO:**
```bash
--object-store-endpoint minio:9000 \
--object-store-access-key minioadmin \
--object-store-secret-key minioadmin
```

**מחסן (תואם S3):**
```bash
--object-store-endpoint garage:3900 \
--object-store-access-key GK000000000000000000000001 \
--object-store-secret-key b171f00be9be4c32c734f4c05fe64c527a8ab5eb823b376cfa8c2531f70fc427
```

**AWS S3 עם SSL:**
```bash
--object-store-endpoint s3.amazonaws.com \
--object-store-access-key AKIAIOSFODNN7EXAMPLE \
--object-store-secret-key wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY \
--object-store-use-ssl \
--object-store-region us-east-1
```

## אימות

כל השרתים התומכים ב-S3 דורשים אימות AWS Signature Version 4 (או v2):

**מפתח גישה (Access Key)** - מזהה ציבורי (כמו שם משתמש)
**מפתח סודי (Secret Key)** - מפתח חתימה פרטי (כמו סיסמה)

לקוח ה-Python של MinIO מטפל בכל חישוב החתימה באופן אוטומטי.

### יצירת פרטי גישה

**עבור MinIO:**
```bash
# Use default credentials or create user via MinIO Console
minioadmin / minioadmin
```

**עבור Ceph RGW:**
```bash
radosgw-admin user create --uid="trustgraph" --display-name="TrustGraph Service"
# Returns access_key and secret_key
```

**עבור AWS S3:**
צור משתמש IAM עם הרשאות S3
צור מפתח גישה בלוח הבקרה של AWS

## בחירת ספרייה: לקוח Python של MinIO

**ההצדקה:**
קל משקל (~500KB לעומת ~50MB של boto3)
תואם ל-S3 - עובד עם כל נקודת קצה של ממשק API של S3
ממשק API פשוט יותר מ-boto3 עבור פעולות בסיסיות
כבר בשימוש, אין צורך בהעברה
נבדק היטב עם MinIO ומערכות S3 אחרות

## יישום BlobStore

**מיקום:** `trustgraph-flow/trustgraph/librarian/blob_store.py`

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

## יתרונות מרכזיים

1. **ללא תלות בספק** - עובד עם כל אחסון התומך ב-S3
2. **קל משקל** - הלקוח של MinIO הוא בגודל של כ-500KB בלבד
3. **הגדרות פשוטות** - רק נקודת קצה (endpoint) ואישורים
4. **ללא העברת נתונים** - החלפה ישירה בין מערכות אחסון שונות
5. **נבדק ביסודיות** - לקוח MinIO עובד עם כל המימושים העיקריים של S3

## סטטוס יישום

כל הקוד עודכן לשימוש בשמות פרמטרים גנריים של S3:

✅ `blob_store.py` - עודכן כדי לקבל `endpoint`, `access_key`, `secret_key`
✅ `librarian.py` - עודכנו שמות הפרמטרים
✅ `service.py` - עודכנו ארגומנטים של שורת הפקודה והגדרות
✅ תיעוד עודכן

## שיפורים עתידיים

1. **תמיכה ב-SSL/TLS** - הוספת דגל `--s3-use-ssl` עבור HTTPS
2. **לוגיקת ניסיונות חוזרים** - יישום של דחייה אקספוננציאלית עבור כשלים זמניים
3. **כתובות URL חתומות** - יצירת כתובות URL זמניות להעלאה/הורדה
4. **תמיכה בריבוי אזורים** - שכפול קבצים בין אזורים
5. **אינטגרציה עם CDN** - שירות קבצים באמצעות CDN
6. **מדרגי אחסון** - שימוש במדרגי אחסון של S3 למיטוב עלויות
7. **מדיניות מחזור חיים** - ארכיון/מחיקה אוטומטיים
8. **גרסאות** - שמירת גרסאות מרובות של קבצים

## הפניות

לקוח MinIO לפייתון: https://min.io/docs/minio/linux/developers/python/API.html
Ceph RGW S3 API: https://docs.ceph.com/en/latest/radosgw/s3/
מדריך API של S3: https://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html
