---
layout: default
title: "तकनीकी विनिर्देश: S3-संगत स्टोरेज बैकएंड समर्थन"
parent: "Hindi (Beta)"
---

# तकनीकी विनिर्देश: S3-संगत स्टोरेज बैकएंड समर्थन

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## अवलोकन

लाइब्रेरियन सेवा दस्तावेज़ ब्लॉब स्टोरेज के लिए S3-संगत ऑब्जेक्ट स्टोरेज का उपयोग करती है। यह विनिर्देश उस कार्यान्वयन का दस्तावेज़ करता है जो किसी भी S3-संगत बैकएंड के लिए समर्थन को सक्षम करता है, जिसमें MinIO, Ceph RADOS गेटवे (RGW), AWS S3, Cloudflare R2, DigitalOcean Spaces और अन्य शामिल हैं।

## वास्तुकला

### स्टोरेज घटक
**ब्लॉब स्टोरेज**: `minio` पायथन क्लाइंट लाइब्रेरी के माध्यम से S3-संगत ऑब्जेक्ट स्टोरेज
**मेटाडेटा स्टोरेज**: कैसेंड्रा (ऑब्जेक्ट_आईडी मैपिंग और दस्तावेज़ मेटाडेटा संग्रहीत करता है)
**प्रभावित घटक**: केवल लाइब्रेरियन सेवा
**स्टोरेज पैटर्न**: कैसेंड्रा में मेटाडेटा और S3-संगत स्टोरेज में सामग्री के साथ हाइब्रिड स्टोरेज

### कार्यान्वयन
**लाइब्रेरी**: `minio` पायथन क्लाइंट (किसी भी S3-संगत API का समर्थन करता है)
**स्थान**: `trustgraph-flow/trustgraph/librarian/blob_store.py`
**ऑपरेशन**:
  `add()` - UUID ऑब्जेक्ट_आईडी के साथ ब्लॉब संग्रहीत करें
  `get()` - ऑब्जेक्ट_आईडी द्वारा ब्लॉब पुनर्प्राप्त करें
  `remove()` - ऑब्जेक्ट_आईडी द्वारा ब्लॉब हटाएं
  `ensure_bucket()` - यदि मौजूद नहीं है तो बकेट बनाएं
**बकेट**: `library`
**ऑब्जेक्ट पथ**: `doc/{object_id}`
**समर्थित MIME प्रकार**: `text/plain`, `application/pdf`

### महत्वपूर्ण फाइलें
1. `trustgraph-flow/trustgraph/librarian/blob_store.py` - BlobStore कार्यान्वयन
2. `trustgraph-flow/trustgraph/librarian/librarian.py` - BlobStore इनिशियलाइज़ेशन
3. `trustgraph-flow/trustgraph/librarian/service.py` - सेवा कॉन्फ़िगरेशन
4. `trustgraph-flow/pyproject.toml` - निर्भरताएँ (`minio` पैकेज)
5. `docs/apis/api-librarian.md` - एपीआई दस्तावेज़

## समर्थित स्टोरेज बैकएंड

कार्यान्वयन किसी भी S3-संगत ऑब्जेक्ट स्टोरेज सिस्टम के साथ काम करता है:

### परीक्षण किया गया/समर्थित
**Ceph RADOS गेटवे (RGW)** - S3 API के साथ वितरित स्टोरेज सिस्टम (डिफ़ॉल्ट कॉन्फ़िगरेशन)
**MinIO** - हल्का स्व-होस्टेड ऑब्जेक्ट स्टोरेज
**गैराज** - हल्का जियो-वितरित S3-संगत स्टोरेज

### काम करना चाहिए (S3-संगत)
**AWS S3** - अमेज़ॅन का क्लाउड ऑब्जेक्ट स्टोरेज
**Cloudflare R2** - Cloudflare का S3-संगत स्टोरेज
**DigitalOcean Spaces** - DigitalOcean का ऑब्जेक्ट स्टोरेज
**Wasabi** - S3-संगत क्लाउड स्टोरेज
**Backblaze B2** - S3-संगत बैकअप स्टोरेज
S3 REST API को लागू करने वाली कोई भी अन्य सेवा

## कॉन्फ़िगरेशन

### CLI तर्क

```bash
librarian \
  --object-store-endpoint <hostname:port> \
  --object-store-access-key <access_key> \
  --object-store-secret-key <secret_key> \
  [--object-store-use-ssl] \
  [--object-store-region <region>]
```

**ध्यान दें:** अंतिम बिंदु में `http://` या `https://` को शामिल न करें। HTTPS को सक्षम करने के लिए `--object-store-use-ssl` का उपयोग करें।

### पर्यावरण चर (वैकल्पिक)

```bash
OBJECT_STORE_ENDPOINT=<hostname:port>
OBJECT_STORE_ACCESS_KEY=<access_key>
OBJECT_STORE_SECRET_KEY=<secret_key>
OBJECT_STORE_USE_SSL=true|false  # Optional, default: false
OBJECT_STORE_REGION=<region>     # Optional
```

### उदाहरण

**सेफ रेडोस गेटवे (डिफ़ॉल्ट):**
```bash
--object-store-endpoint ceph-rgw:7480 \
--object-store-access-key object-user \
--object-store-secret-key object-password
```

**मिनियो:**
```bash
--object-store-endpoint minio:9000 \
--object-store-access-key minioadmin \
--object-store-secret-key minioadmin
```

**गैराज (एस3-संगत):**
```bash
--object-store-endpoint garage:3900 \
--object-store-access-key GK000000000000000000000001 \
--object-store-secret-key b171f00be9be4c32c734f4c05fe64c527a8ab5eb823b376cfa8c2531f70fc427
```

**AWS S3 एसएसएल के साथ:**
```bash
--object-store-endpoint s3.amazonaws.com \
--object-store-access-key AKIAIOSFODNN7EXAMPLE \
--object-store-secret-key wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY \
--object-store-use-ssl \
--object-store-region us-east-1
```

## प्रमाणीकरण

सभी S3-संगत बैकएंड को AWS सिग्नेचर संस्करण 4 (या v2) प्रमाणीकरण की आवश्यकता होती है:

**एक्सेस कुंजी** - सार्वजनिक पहचानकर्ता (जैसे उपयोगकर्ता नाम)
**सीक्रेट कुंजी** - निजी हस्ताक्षर कुंजी (जैसे पासवर्ड)

MinIO पायथन क्लाइंट सभी हस्ताक्षर गणना को स्वचालित रूप से संभालता है।

### क्रेडेंशियल बनाना

**MinIO के लिए:**
```bash
# Use default credentials or create user via MinIO Console
minioadmin / minioadmin
```

**सेफ आरजीडब्ल्यू के लिए:**
```bash
radosgw-admin user create --uid="trustgraph" --display-name="TrustGraph Service"
# Returns access_key and secret_key
```

**AWS S3 के लिए:**
S3 अनुमतियों के साथ एक IAM उपयोगकर्ता बनाएँ।
AWS कंसोल में एक्सेस कुंजी उत्पन्न करें।

## लाइब्रेरी चयन: MinIO Python क्लाइंट

**तर्क:**
हल्का (~500KB बनाम boto3 का ~50MB)
S3-संगत - किसी भी S3 API एंडपॉइंट के साथ काम करता है।
बुनियादी कार्यों के लिए boto3 की तुलना में सरल API।
पहले से उपयोग में है, माइग्रेशन की आवश्यकता नहीं है।
MinIO और अन्य S3 सिस्टम के साथ परीक्षण किया गया।

## BlobStore कार्यान्वयन

**स्थान:** `trustgraph-flow/trustgraph/librarian/blob_store.py`

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

## मुख्य लाभ

1. **कोई विक्रेता लॉक-इन नहीं** - किसी भी S3-संगत स्टोरेज के साथ काम करता है।
2. **हल्का** - MinIO क्लाइंट केवल ~500KB है।
3. **सरल कॉन्फ़िगरेशन** - केवल एंडपॉइंट + क्रेडेंशियल।
4. **कोई डेटा माइग्रेशन नहीं** - बैकएंड के बीच ड्रॉप-इन रिप्लेसमेंट।
5. **युद्ध-परीक्षित** - MinIO क्लाइंट सभी प्रमुख S3 कार्यान्वयन के साथ काम करता है।

## कार्यान्वयन स्थिति

सभी कोड को जेनेरिक S3 पैरामीटर नामों का उपयोग करने के लिए अपडेट किया गया है:

✅ `blob_store.py` - `endpoint`, `access_key`, `secret_key` को स्वीकार करने के लिए अपडेट किया गया।
✅ `librarian.py` - पैरामीटर नामों को अपडेट किया गया।
✅ `service.py` - CLI तर्क और कॉन्फ़िगरेशन को अपडेट किया गया।
✅ दस्तावेज़ अपडेट किया गया।

## भविष्य के सुधार

1. **SSL/TLS समर्थन** - HTTPS के लिए `--s3-use-ssl` ध्वज जोड़ें।
2. **पुन: प्रयास तर्क** - क्षणिक विफलताओं के लिए घातीय बैकऑफ़ लागू करें।
3. **प्रीसाइंड URL** - अस्थायी अपलोड/डाउनलोड URL उत्पन्न करें।
4. **मल्टी-रीजन समर्थन** - क्षेत्रों में ब्लॉब्स को दोहराएं।
5. **CDN एकीकरण** - CDN के माध्यम से ब्लॉब्स परोसें।
6. **स्टोरेज क्लासेस** - लागत अनुकूलन के लिए S3 स्टोरेज क्लासेस का उपयोग करें।
7. **लाइफसाइकिल नीतियां** - स्वचालित अभिलेखागार/हटाना।
8. **वर्जनिंग** - ब्लॉब्स के कई संस्करणों को संग्रहीत करें।

## संदर्भ

MinIO Python क्लाइंट: https://min.io/docs/minio/linux/developers/python/API.html
Ceph RGW S3 API: https://docs.ceph.com/en/latest/radosgw/s3/
S3 API संदर्भ: https://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html
