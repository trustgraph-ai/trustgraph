# Teknik Özellikler: S3 Uyumlu Depolama Arka Ucu Desteği

## Genel Bakış

Librarian hizmeti, belge bloğu depolaması için S3 uyumlu nesne depolamayı kullanır. Bu özellik, MinIO, Ceph RADOS Gateway (RGW), AWS S3, Cloudflare R2, DigitalOcean Spaces ve diğerleri dahil olmak üzere herhangi bir S3 uyumlu arka uç için desteği etkinleştiren uygulamayı belgelemektedir.

## Mimari

### Depolama Bileşenleri
**Bloğu Depolama**: `minio` Python istemci kitaplığı aracılığıyla S3 uyumlu nesne depolama
**Metaveri Depolama**: Cassandra (object_id eşlemesini ve belge meta verilerini depolar)
**Etkilenen Bileşen**: Yalnızca Librarian hizmeti
**Depolama Modeli**: Cassandra'da metaveri, S3 uyumlu depolamada içerikle hibrit depolama

### Uygulama
**Kitaplık**: `minio` Python istemcisi (herhangi bir S3 uyumlu API'yi destekler)
**Konum**: `trustgraph-flow/trustgraph/librarian/blob_store.py`
**İşlemler**:
  `add()` - UUID object_id ile bloğu kaydet
  `get()` - object_id ile bloğu al
  `remove()` - object_id ile bloğu sil
  `ensure_bucket()` - Yoksa bucket oluştur
**Bucket**: `library`
**Nesne Yolu**: `doc/{object_id}`
**Desteklenen MIME Türleri**: `text/plain`, `application/pdf`

### Önemli Dosyalar
1. `trustgraph-flow/trustgraph/librarian/blob_store.py` - BlobStore uygulaması
2. `trustgraph-flow/trustgraph/librarian/librarian.py` - BlobStore başlatma
3. `trustgraph-flow/trustgraph/librarian/service.py` - Hizmet yapılandırması
4. `trustgraph-flow/pyproject.toml` - Bağımlılıklar (`minio` paketi)
5. `docs/apis/api-librarian.md` - API dokümantasyonu

## Desteklenen Depolama Arka Uçları

Bu uygulama, herhangi bir S3 uyumlu nesne depolama sistemiyle çalışır:

### Test Edildi/Destekleniyor
**Ceph RADOS Gateway (RGW)** - S3 API'sine sahip dağıtılmış depolama sistemi (varsayılan yapılandırma)
**MinIO** - Hafif, kendi kendine barındırılan nesne depolama
**Garage** - Hafif, coğrafi olarak dağıtılmış S3 uyumlu depolama

### Çalışması Gerekiyor (S3 Uyumlu)
**AWS S3** - Amazon'un bulut nesne depolaması
**Cloudflare R2** - Cloudflare'in S3 uyumlu depolaması
**DigitalOcean Spaces** - DigitalOcean'ın nesne depolaması
**Wasabi** - S3 uyumlu bulut depolama
**Backblaze B2** - S3 uyumlu yedekleme depolama
S3 REST API'sini uygulayan herhangi bir hizmet

## Yapılandırma

### CLI Argümanları

```bash
librarian \
  --object-store-endpoint <hostname:port> \
  --object-store-access-key <access_key> \
  --object-store-secret-key <secret_key> \
  [--object-store-use-ssl] \
  [--object-store-region <region>]
```

**Not:** `http://` veya `https://`'i uç noktada dahil etmeyin. HTTPS'yi etkinleştirmek için `--object-store-use-ssl`'yi kullanın.

### Ortam Değişkenleri (Alternatif)

```bash
OBJECT_STORE_ENDPOINT=<hostname:port>
OBJECT_STORE_ACCESS_KEY=<access_key>
OBJECT_STORE_SECRET_KEY=<secret_key>
OBJECT_STORE_USE_SSL=true|false  # Optional, default: false
OBJECT_STORE_REGION=<region>     # Optional
```

### Örnekler

**Ceph RADOS Ağ Geçidi (varsayılan):**
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

**Garaj (S3 uyumlu):**
```bash
--object-store-endpoint garage:3900 \
--object-store-access-key GK000000000000000000000001 \
--object-store-secret-key b171f00be9be4c32c734f4c05fe64c527a8ab5eb823b376cfa8c2531f70fc427
```

**AWS S3 SSL ile:**
```bash
--object-store-endpoint s3.amazonaws.com \
--object-store-access-key AKIAIOSFODNN7EXAMPLE \
--object-store-secret-key wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY \
--object-store-use-ssl \
--object-store-region us-east-1
```

## Kimlik Doğrulama

Tüm S3 uyumlu arka uçlar, AWS Signature Version 4 (veya v2) kimlik doğrulamasını gerektirir:

**Erişim Anahtarı** - Genel tanımlayıcı (kullanıcı adı gibi)
**Gizli Anahtar** - Özel imzalama anahtarı (parola gibi)

MinIO Python istemcisi, tüm imza hesaplamalarını otomatik olarak yapar.

### Kimlik Bilgilerini Oluşturma

**MinIO için:**
```bash
# Use default credentials or create user via MinIO Console
minioadmin / minioadmin
```

**Ceph RGW için:**
```bash
radosgw-admin user create --uid="trustgraph" --display-name="TrustGraph Service"
# Returns access_key and secret_key
```

**AWS S3 için:**
S3 izinlerine sahip bir IAM kullanıcısı oluşturun.
AWS Konsolu'nda bir erişim anahtarı oluşturun.

## Kütüphane Seçimi: MinIO Python İstemcisi

**Gerekçe:**
Hafif (~500KB, boto3'ün ~50MB'sine kıyasla)
S3 uyumlu - herhangi bir S3 API uç noktasıyla çalışır.
Temel işlemler için boto3'e göre daha basit bir API.
Zaten kullanımda, herhangi bir geçişe gerek yok.
MinIO ve diğer S3 sistemleriyle test edilmiş.

## BlobStore Uygulaması

**Konum:** `trustgraph-flow/trustgraph/librarian/blob_store.py`

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

## Temel Avantajlar

1. **Satıcıya Bağlılık Yok** - Herhangi bir S3 uyumlu depolama ile çalışır.
2. **Hafif** - MinIO istemcisi yaklaşık 500KB'dir.
3. **Basit Yapılandırma** - Sadece uç nokta + kimlik bilgileri gereklidir.
4. **Veri Göçü Yok** - Arka uçlar arasında doğrudan değiştirilebilir.
5. **Kanıtlanmış** - MinIO istemcisi, tüm büyük S3 uygulamalarıyla çalışır.

## Uygulama Durumu

Tüm kod, genel S3 parametre adlarını kullanacak şekilde güncellenmiştir:

✅ `blob_store.py` - `endpoint`, `access_key` ve `secret_key`'ü kabul edecek şekilde güncellendi.
✅ `librarian.py` - Parametre adları güncellendi.
✅ `service.py` - CLI argümanları ve yapılandırma güncellendi.
✅ Belgeler güncellendi.

## Gelecek Geliştirmeler

1. **SSL/TLS Desteği** - HTTPS için `--s3-use-ssl` bayrağı eklenecek.
2. **Yeniden Deneme Mantığı** - Geçici hatalar için üstel geri alma uygulanacak.
3. **Önceden İmzalı URL'ler** - Geçici yükleme/indirme URL'leri oluşturulacak.
4. **Çok Bölgeli Destek** - Verileri bölgeler arasında çoğaltılacak.
5. **CDN Entegrasyonu** - Veriler CDN üzerinden sunulacak.
6. **Depolama Sınıfları** - Maliyet optimizasyonu için S3 depolama sınıfları kullanılacak.
7. **Yaşam Döngüsü Politikaları** - Otomatik arşivleme/silme.
8. **Sürümleme** - Verilerin birden fazla sürümü saklanacak.

## Referanslar

MinIO Python İstemcisi: https://min.io/docs/minio/linux/developers/python/API.html
Ceph RGW S3 API: https://docs.ceph.com/en/latest/radosgw/s3/
S3 API Referansı: https://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html
