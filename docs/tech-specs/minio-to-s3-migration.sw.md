# Vipimo vya Kisaikolojia: Usaidizi wa Hifadhi Data inayolingana na S3

## Muhtasari

Huduma ya Librarian hutumia hifadhi data ya vitu inayolingana na S3 kwa kuhifadhi faili za hati. Haya yanatoa maelezo ya utekelezaji unaoleta uwezo wa kusaidia mfumo wowote wa hifadhi inayolingana na S3, ikiwa ni pamoja na MinIO, Ceph RADOS Gateway (RGW), AWS S3, Cloudflare R2, DigitalOcean Spaces, na wengine.

## Muundo

### Vipengele vya Uhifadhi
**Hifadhi ya Vitu:** Hifadhi data ya vitu inayolingana na S3 kupitia `minio` maktaba ya mteja ya Python
**Hifadhi ya MetaData:** Cassandra (hufanya kazi ya kuhifadhi uhusiano wa object_id na metadata ya hati)
**Kipengele Kilichohusika:** Huduma ya Librarian pekee
**Mfumo wa Uhifadhi:** Uhifadhi mchanganyiko na metadata katika Cassandra, na yaliyomo katika hifadhi inayolingana na S3

### Utendaji
**Maktaba:** `minio` mteja wa Python (inaunga mkono API yoyote inayolingana na S3)
**Mahali:** `trustgraph-flow/trustgraph/librarian/blob_store.py`
**Tendo:**
  `add()` - Hifadhi faili kwa kitambulisho cha kipekee (object_id)
  `get()` - Rudisha faili kwa kitambulisho cha kipekee (object_id)
  `remove()` - Futa faili kwa kitambulisho cha kipekee (object_id)
  `ensure_bucket()` - Unda kiasi (bucket) ikiwa haipo
**Kiasi (Bucket):** `library`
**Njia ya Faili:** `doc/{object_id}`
**Aina Zinazoidhinishwa (MIME Types):** `text/plain`, `application/pdf`

### Faili Muhimu
1. `trustgraph-flow/trustgraph/librarian/blob_store.py` - Utendaji wa BlobStore
2. `trustgraph-flow/trustgraph/librarian/librarian.py` - Uanzishaji wa BlobStore
3. `trustgraph-flow/trustgraph/librarian/service.py` - Usanidi wa huduma
4. `trustgraph-flow/pyproject.toml` - Utendakazi (pakiti ya `minio`)
5. `docs/apis/api-librarian.md` - Nyaraka za API

## Mifumo ya Uhifadhi Inayoungwa Mkono

Utendaji huu unafanya kazi na mfumo wowote wa hifadhi data ya vitu inayolingana na S3:

### Imethibitishwa/Inaungwa Mkono
**Ceph RADOS Gateway (RGW)** - Mfumo wa hifadhi usambazwa na API ya S3 (usanidi chaguu)
**MinIO** - Hifadhi data ya vitu nyepesi inayoweza kuendeshwa na wewe mwenyewe
**Garage** - Hifadhi data ya vitu nyepesi inayopaswa kusambazwa kijiografia inayolingana na S3

### Inapaswa Kufanya kazi (Inayolingana na S3)
**AWS S3** - Hifadhi data ya vitu ya Amazon kwenye wingu
**Cloudflare R2** - Hifadhi data inayolingana na S3 ya Cloudflare
**DigitalOcean Spaces** - Hifadhi data ya vitu ya DigitalOcean
**Wasabi** - Hifadhi data ya vitu kwenye wingu inayolingana na S3
**Backblaze B2** - Hifadhi data ya vitu inayolingana na S3 kwa ajili ya chelezo
Huduma yoyote nyingine inayotekeleza API ya S3 REST

## Usanidi

### Majadiliano ya CLI

```bash
librarian \
  --object-store-endpoint <hostname:port> \
  --object-store-access-key <access_key> \
  --object-store-secret-key <secret_key> \
  [--object-store-use-ssl] \
  [--object-store-region <region>]
```

**Kumbuka:** Usijumuishie `http://` au `https://` katika mwisho. Tumia `--object-store-use-ssl` ili kuwezesha HTTPS.

### Vigezo vya Mazingira (Mbadala)

```bash
OBJECT_STORE_ENDPOINT=<hostname:port>
OBJECT_STORE_ACCESS_KEY=<access_key>
OBJECT_STORE_SECRET_KEY=<secret_key>
OBJECT_STORE_USE_SSL=true|false  # Optional, default: false
OBJECT_STORE_REGION=<region>     # Optional
```

### Mifano

**Lango la RADOS la Ceph (linalolingana na chaguo-msingi):**
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

**Gara (Inayoambatana na S3):**
```bash
--object-store-endpoint garage:3900 \
--object-store-access-key GK000000000000000000000001 \
--object-store-secret-key b171f00be9be4c32c734f4c05fe64c527a8ab5eb823b376cfa8c2531f70fc427
```

**AWS S3 na SSL:**
```bash
--object-store-endpoint s3.amazonaws.com \
--object-store-access-key AKIAIOSFODNN7EXAMPLE \
--object-store-secret-key wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY \
--object-store-use-ssl \
--object-store-region us-east-1
```

## Uthibitisho

Vifaa vyote vinavyolingana na S3 vinahitaji uthibitisho wa AWS Signature Version 4 (au v2):

**Ufunguo wa Ufikiaji** - Kitambulisho cha umma (kama jina la mtumiaji)
**Ufunguo Siri** - Ufunguo wa siri wa usaini (kama nenosiri)

Mteja wa Python wa MinIO hushughulikia hesabu yote ya usaini kiotomatiki.

### Kuunda Anwani

**Kwa MinIO:**
```bash
# Use default credentials or create user via MinIO Console
minioadmin / minioadmin
```

**Kwa Ceph RGW:**
```bash
radosgw-admin user create --uid="trustgraph" --display-name="TrustGraph Service"
# Returns access_key and secret_key
```

**Kwa AWS S3:**
Unda mtumiaji wa IAM na ruhusa za S3
Toa ufunguo wa ufikiaji katika Konsoli ya AWS

## Chaguo la Klibu: Mteja wa MinIO Python

**Sababu:**
Nyepesi (~500KB dhidi ya ~50MB ya boto3)
Inafanana na S3 - inafanya kazi na mwisho wowote wa API ya S3
API rahisi kuliko boto3 kwa operesheni za msingi
Tayari inatumika, hakuna uhamishaji unaohitajika
Imethibitishwa kwa MinIO na mifumo mingine ya S3

## Utendaji wa BlobStore

**Mahali:** `trustgraph-flow/trustgraph/librarian/blob_store.py`

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

## Faida Muhimu

1. **Hakuna Utegemezi wa Mtoa Huduma** - Inafanya kazi na hifadhi yoyote inayolingana na S3.
2. **Nyepesi** - Mteja wa MinIO ni takriban 500KB.
3. **Uwekaji Rahisi** - Tu mwisho na anwani za kuingia.
4. **Hakuna Uhamishaji wa Data** - Badala ya moja kwa moja kati ya mifumo ya nyuma.
5. **Imethibitishwa katika Vita** - Mteja wa MinIO unafanya kazi na matoleo yote makubwa ya S3.

## Hali ya Utendaji

Msimbo wote umeongezwa ili kutumia majina ya vigezo vya S3.

✅ `blob_store.py` - Imeongezwa ili kukubali `endpoint`, `access_key`, `secret_key`
✅ `librarian.py` - Majina ya vigezo yameongezwa.
✅ `service.py` - Majadiliano ya CLI na usanidi yameongezwa.
✅ Nyaraka zimeongezwa.

## Maboresho ya Baadaye

1. **Usaidizi wa SSL/TLS** - Ongeza bendera `--s3-use-ssl` kwa HTTPS.
2. **Mantiki ya Kujaribu Upya** - Tekeleza kuchelewesha kwa eksponensia kwa kushindwa kwa muda mfupi.
3. **Anwani za Muda** - Zunda anwani za muda za kupakia/kupakua.
4. **Usaidizi wa Mikoa Mbalimbali** - Nakili data katika mikoa mbalimbali.
5. **Uunganisho wa CDN** - Toa data kupitia CDN.
6. **Daraja za Hifadhi** - Tumia daraja za hifadhi za S3 kwa uboreshaji wa gharama.
7. **Sera za Maisha** - Hifadhi/ufute data kiotomatiki.
8. **Toleo** - Hifadhi matoleo mengi ya data.

## Marejeleo

Mteja wa MinIO wa Python: https://min.io/docs/minio/linux/developers/python/API.html
API ya S3 ya Ceph RGW: https://docs.ceph.com/en/latest/radosgw/s3/
Marejeleo ya API ya S3: https://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html
