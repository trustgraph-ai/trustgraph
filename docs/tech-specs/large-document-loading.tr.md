# Büyük Belge Yükleme Teknik Özellikleri

## Genel Bakış

Bu teknik özellik, TrustGraph'e büyük belgelerin yüklenmesi sırasında ortaya çıkan ölçeklenebilirlik ve kullanıcı deneyimi sorunlarını ele almaktadır. Mevcut mimari, belge yüklemeyi tek bir atomik işlem olarak ele almaktadır, bu da boru hattının çeşitli noktalarında bellek yüklenmesine neden olmakta ve kullanıcılara herhangi bir geri bildirim veya kurtarma seçeneği sunmamaktadır.

Bu uygulama, aşağıdaki kullanım senaryolarına yöneliktir:


1. **Büyük PDF İşleme**: Belleği tüketmeden yüzlerce megabayt boyutunda PDF dosyalarını yükleyin ve işleyin.

2. **Devam Eden Yüklemeler**: Kesintiye uğrayan yüklemelerin, baştan başlamak yerine, durdurulduğu yerden devam etmesini sağlayın.
   
3. **İlerleme Geri Bildirimi**: Kullanıcılara yükleme ve işleme sürecinin gerçek zamanlı görünürlüğünü sağlayın.
   
4. **Bellek Verimli İşleme**: Belgeleri, tüm dosyaları bellekte tutmadan, akış halinde işleyin.
   

   ## Hedefler


**Artımlı Yükleme**: REST ve WebSocket üzerinden parçalı belge yüklemeyi destekleyin.
**Devam Eden Aktarımlar**: Kesintiye uğrayan yüklemelerden kurtarmayı sağlayın.
**İlerleme Görünürlüğü**: İstemcilere yükleme/işleme sürecinin ilerleme durumunu geri bildirin.
**Bellek Verimliliği**: Boru hattının tamamında tam belge tamponlamayı ortadan kaldırın.
**Geriye Dönük Uyumluluk**: Mevcut, küçük belge iş akışlarının değişmeden devam etmesini sağlayın.
**Akış İşleme**: PDF kod çözme ve metin parçalama işlemleri, akışlar üzerinde gerçekleştirilir.

## Arka Plan


### Mevcut Mimari

Belge gönderme işlemi, aşağıdaki yolu izlemektedir:

1. **İstemci**, belgeyi REST (`POST /api/v1/librarian`) veya WebSocket üzerinden gönderir.
2. **API Ağ Geçidi**, base64 ile kodlanmış belge içeriği içeren eksiksiz isteği alır.
3. **LibrarianRequestor**, isteği Pulsar mesajına dönüştürür.
4. **Librarian Hizmeti**, mesajı alır, belgeyi belleğe kodlar.
5. **BlobStore**, belgeyi Garage/S3'e yükler.
6. **Cassandra**, nesne referansı ile birlikte meta verileri depolar.
7. İşleme için: belge S3'ten alınır, kodlanır, parçalara ayrılır - hepsi bellekte.

Önemli dosyalar:
REST/WebSocket girişi: `trustgraph-flow/trustgraph/gateway/service.py`
Librarian çekirdeği: `trustgraph-flow/trustgraph/librarian/librarian.py`
Blob depolama: `trustgraph-flow/trustgraph/librarian/blob_store.py`
Cassandra tabloları: `trustgraph-flow/trustgraph/tables/library.py`
API şeması: `trustgraph-base/trustgraph/schema/services/library.py`

### Mevcut Sınırlamalar

Mevcut tasarımın, çeşitli birikimli bellek ve kullanıcı deneyimi sorunları bulunmaktadır:

1. **Atomik Yükleme İşlemi**: Tüm belge,
   tek bir istekte iletilmelidir. Büyük belgeler, bağlantı başarısız olursa geri alma mekanizması olmadan, ilerleme göstergesi olmayan uzun süreli istekler gerektirir.
   

2. **API Tasarımı**: Hem REST hem de WebSocket API'leri,
   tüm belgeyi tek bir mesajda bekler. Şema (`LibrarianRequest`), tüm base64 ile kodlanmış belgeyi içeren tek bir `content`
   alanına sahiptir.

3. **Kütüphaneci Belleği**: Kütüphaneci hizmeti, belgeyi S3'e yüklemeden önce tüm belgeyi belleğe aktarır. 500MB'lık bir PDF için, bu, işlem belleğinde 500MB+'yi tutmak anlamına gelir.
   500MB+ işlem belleğinde tutmak anlamına gelir.
   

4. **PDF Kod Çözücü Belleği**: İşleme başladığında, PDF kod çözücü, metni çıkarmak için tüm PDF'yi belleğe yükler. PyPDF ve benzeri kütüphaneler genellikle belgenin tamamına erişim gerektirir.
   
   

5. **Parçalayıcı Belleği**: Metin parçalayıcı, çıkarılan tamamlanmış metni alır ve parçalar oluştururken bunu bellekte tutar.
   

**Bellek Kullanımı Örneği** (500MB PDF):
Gateway: ~700MB (base64 kodlama ek yükü)
Librarian: ~500MB (çözülmüş baytlar)
PDF Çözücü: ~500MB + çıkarma arabellekleri
Parçalayıcı: çıkarılan metin (değişken, potansiyel olarak 100MB+)

Tek bir büyük belge için toplam maksimum bellek kullanımı 2GB'ı aşabilir.

## Teknik Tasarım

### Tasarım İlkeleri

1. **API Arayüzü**: Tüm istemci etkileşimi, librarian API'si üzerinden gerçekleşir. İstemciler,
   temelindeki S3/Garage depolamaya doğrudan erişemez veya bu depolama hakkında bilgi sahibi değildir.

2. **S3 Çoklu Parça Yükleme**: Temelde standart S3 çoklu parça yükleme özelliğini kullanın.
   Bu, S3 uyumlu sistemlerde (AWS S3, MinIO, Garage,
   Ceph, DigitalOcean Spaces, Backblaze B2, vb.) yaygın olarak desteklenir ve taşınabilirliği sağlar.

3. **Atomik Tamamlama**: S3 çoklu parça yüklemeleri doğası gereği atomiktir; yüklenen
   parçalar, `CompleteMultipartUpload` çağrılana kadar görünmez. Geçici
   dosyalar veya yeniden adlandırma işlemleri gerekmez.

4. **Takip Edilebilir Durum**: Yükleme oturumları Cassandra'da takip edilir, bu da
   tamamlanmamış yüklemeler hakkında görünürlük sağlar ve devam ettirme özelliğini etkinleştirir.

### Parçalı Yükleme Akışı

```
Client                    Librarian API                   S3/Garage
  │                            │                              │
  │── begin-upload ───────────►│                              │
  │   (metadata, size)         │── CreateMultipartUpload ────►│
  │                            │◄── s3_upload_id ─────────────│
  │◄── upload_id ──────────────│   (store session in          │
  │                            │    Cassandra)                │
  │                            │                              │
  │── upload-chunk ───────────►│                              │
  │   (upload_id, index, data) │── UploadPart ───────────────►│
  │                            │◄── etag ─────────────────────│
  │◄── ack + progress ─────────│   (store etag in session)    │
  │         ⋮                  │         ⋮                    │
  │   (repeat for all chunks)  │                              │
  │                            │                              │
  │── complete-upload ────────►│                              │
  │   (upload_id)              │── CompleteMultipartUpload ──►│
  │                            │   (parts coalesced by S3)    │
  │                            │── store doc metadata ───────►│ Cassandra
  │◄── document_id ────────────│   (delete session)           │
```

Müşteri, S3 ile doğrudan etkileşimde bulunmaz. Kütüphaneci, parçalı yükleme API'miz ile S3 çok parçalı işlemler arasında dahili olarak çeviri yapar.

### Kütüphaneci API İşlemleri
### Kütüphaneci API İşlemleri

#### `begin-upload`

Parçalı bir yükleme oturumu başlatın.

İstek:
```json
{
  "operation": "begin-upload",
  "document-metadata": {
    "id": "doc-123",
    "kind": "application/pdf",
    "title": "Large Document",
    "user": "user-id",
    "tags": ["tag1", "tag2"]
  },
  "total-size": 524288000,
  "chunk-size": 5242880
}
```

Yanıt:
```json
{
  "upload-id": "upload-abc-123",
  "chunk-size": 5242880,
  "total-chunks": 100
}
```

Kütüphaneci:
1. Benzersiz bir `upload_id` ve `object_id` oluşturur (blob depolama için UUID).
2. S3'ü `CreateMultipartUpload` ile çağırır, `s3_upload_id`'i alır.
3. Cassandra'da oturum kaydını oluşturur.
4. `upload_id`'ı istemciye döndürür.

#### `upload-chunk`

Tek bir bölüm yükleyin.

İstek:
```json
{
  "operation": "upload-chunk",
  "upload-id": "upload-abc-123",
  "chunk-index": 0,
  "content": "<base64-encoded-chunk>"
}
```

Yanıt:
```json
{
  "upload-id": "upload-abc-123",
  "chunk-index": 0,
  "chunks-received": 1,
  "total-chunks": 100,
  "bytes-received": 5242880,
  "total-bytes": 524288000
}
```

Kütüphaneci:
1. `upload_id` ile oturumu arar.
2. Mülkiyeti doğrular (kullanıcı, oturum oluşturucuyu eşleştirmelidir).
3. Parça verileriyle S3'ü `UploadPart` ile çağırır, `etag` alır.
4. Parça indeksini ve etiketini kullanarak oturum kaydını günceller.
5. İlerleme durumunu istemciye döndürür.

Başarısız parçalar tekrar denenebilir - aynı `chunk-index`'ı tekrar gönderin.

#### `complete-upload`

Yüklemeyi tamamlayın ve belgeyi oluşturun.

İstek:
```json
{
  "operation": "complete-upload",
  "upload-id": "upload-abc-123"
}
```

Yanıt:
```json
{
  "document-id": "doc-123",
  "object-id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Kütüphaneci:
1. Oturumu kontrol eder, tüm parçaların alındığından emin olur.
2. Parça etiketleriyle birlikte S3'ü `CompleteMultipartUpload` ile çağırır (S3 parçaları dahili olarak birleştirir - kütüphaneci için bellek maliyeti sıfırdır).
   3. Cassandra'da, meta veriler ve nesne referansı ile birlikte bir belge kaydı oluşturur.
4. Yükleme oturumu kaydını siler.
5. Belge kimliğini müşteriye döndürür.


#### `abort-upload`

Devam eden bir yüklemeyi iptal et.

İstek:
```json
{
  "operation": "abort-upload",
  "upload-id": "upload-abc-123"
}
```

Kütüphaneci:
1. Parçaları temizlemek için S3 `AbortMultipartUpload`'ı çağırır.
2. Oturum kaydını Cassandra'dan siler.

#### `get-upload-status`

Bir yüklemenin durumunu sorgula (devam ettirme özelliği için).

İstek:
```json
{
  "operation": "get-upload-status",
  "upload-id": "upload-abc-123"
}
```

Yanıt:
```json
{
  "upload-id": "upload-abc-123",
  "state": "in-progress",
  "chunks-received": [0, 1, 2, 5, 6],
  "missing-chunks": [3, 4, 7, 8],
  "total-chunks": 100,
  "bytes-received": 36700160,
  "total-bytes": 524288000
}
```

#### `list-uploads`

Bir kullanıcı için eksik yüklemeleri listele.

İstek:
```json
{
  "operation": "list-uploads"
}
```

Yanıt:
```json
{
  "uploads": [
    {
      "upload-id": "upload-abc-123",
      "document-metadata": { "title": "Large Document", ... },
      "progress": { "chunks-received": 43, "total-chunks": 100 },
      "created-at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Yükleme Oturum Depolama

Cassandra'da devam eden yüklemeleri takip edin:

```sql
CREATE TABLE upload_session (
    upload_id text PRIMARY KEY,
    user text,
    document_id text,
    document_metadata text,      -- JSON: title, kind, tags, comments, etc.
    s3_upload_id text,           -- internal, for S3 operations
    object_id uuid,              -- target blob ID
    total_size bigint,
    chunk_size int,
    total_chunks int,
    chunks_received map<int, text>,  -- chunk_index → etag
    created_at timestamp,
    updated_at timestamp
) WITH default_time_to_live = 86400;  -- 24 hour TTL

CREATE INDEX upload_session_user ON upload_session (user);
```

**TTL Davranışı:**
Oturumlar, tamamlanmadığı takdirde 24 saat sonra sona erer.
Cassandra TTL'si dolduğunda, oturum kaydı silinir.
Yalnız kalmış S3 parçaları, S3 yaşam döngüsü politikası tarafından temizlenir (kovada yapılandırılır).

### Hata Yönetimi ve Atomiklik

**Parça yükleme hatası:**
İstemci, başarısız olan parçayı tekrar dener (aynı `upload_id` ve `chunk-index`).
S3 `UploadPart`, aynı parça numarası için idempotent'tir.
Oturum, hangi parçaların başarılı olduğunu takip eder.

**İstemci, yükleme sırasında bağlantıyı keser:**
Oturum, Cassandra'da alınan parçalarla birlikte kalır.
İstemci, eksik olanları görmek için `get-upload-status`'ı çağırabilir.
Yalnızca eksik parçaları yükleyerek devam edin ve ardından `complete-upload`'ı çağırın.

**Tamamlanmış yükleme hatası:**
S3 `CompleteMultipartUpload` atomiktir - ya tamamen başarılı olur ya da başarısız olur.
Başarısızlık durumunda, parçalar kalır ve istemci `complete-upload`'ı tekrar deneyebilir.
Hiçbir kısmi belge görünmez.

**Oturumun sona ermesi:**
Cassandra TTL, oturum kaydını 24 saat sonra siler.
S3 kova yaşam döngüsü politikası, tamamlanmamış çok parçalı yüklemeleri temizler.
Manuel temizliğe gerek yoktur.

### S3 Çok Parçalı Atomiklik

S3 çok parçalı yüklemeler, yerleşik atomiklik sağlar:

1. **Parçalar görünmezdir:** Yüklenen parçalar, nesne olarak erişilemez.
   Bunlar yalnızca tamamlanmamış bir çok parçalı yüklemenin parçaları olarak vardır.

2. **Atomik tamamlama:** `CompleteMultipartUpload` ya başarılı olur (nesne
   atomik olarak görünür) ya da başarısız olur (nesne oluşturulmaz). Herhangi bir kısmi durum yoktur.

3. **Yeniden adlandırmaya gerek yoktur:** Son nesne anahtarı,
   `CreateMultipartUpload` zamanında belirtilir. Parçalar doğrudan bu anahtara birleştirilir.

4. **Sunucu tarafı birleştirme:** S3, parçaları dahili olarak birleştirir. Kütüphaneci
   parçaları asla tekrar okumaz - belgenin boyutundan bağımsız olarak sıfır bellek yükü.

### BlobStore Uzantıları

**Dosya:** `trustgraph-flow/trustgraph/librarian/blob_store.py`

Çok parçalı yükleme yöntemleri ekleyin:

```python
class BlobStore:
    # Existing methods...

    def create_multipart_upload(self, object_id: UUID, kind: str) -> str:
        """Initialize multipart upload, return s3_upload_id."""
        # minio client: create_multipart_upload()

    def upload_part(
        self, object_id: UUID, s3_upload_id: str,
        part_number: int, data: bytes
    ) -> str:
        """Upload a single part, return etag."""
        # minio client: upload_part()
        # Note: S3 part numbers are 1-indexed

    def complete_multipart_upload(
        self, object_id: UUID, s3_upload_id: str,
        parts: List[Tuple[int, str]]  # [(part_number, etag), ...]
    ) -> None:
        """Finalize multipart upload."""
        # minio client: complete_multipart_upload()

    def abort_multipart_upload(
        self, object_id: UUID, s3_upload_id: str
    ) -> None:
        """Cancel multipart upload, clean up parts."""
        # minio client: abort_multipart_upload()
```

### Parça Boyutu Hususları

**S3 minimumu**: Parça başına 5 MB (son parça hariç)
**S3 maksimumu**: Bir yükleme başına 10.000 parça
**Pratik varsayılan**: 5 MB'lık parçalar
  500 MB'lık bir belge = 100 parça
  5 GB'lık bir belge = 1.000 parça
**İlerleme hassasiyeti**: Daha küçük parçalar = daha hassas ilerleme güncellemeleri
**Ağ verimliliği**: Daha büyük parçalar = daha az sayıda istek

Parça boyutu, belirli sınırlar içinde (5 MB - 100 MB) istemci tarafından yapılandırılabilir.

### Belge İşleme: Akışlı Alma

Yükleme akışı, belgelerin depolamaya verimli bir şekilde aktarılmasını sağlar. İşleme akışı, belgelerin tamamını belleğe yüklemeden, belgelerin çıkarılmasını ve parçalara ayrılmasını sağlar.



#### Tasarım İlkesi: İçerik Değil, Tanımlayıcı

Şu anda, işleme başlatıldığında, belge içeriği Pulsar mesajları aracılığıyla akar. Bu, tüm belgelerin belleğe yüklenmesine neden olur. Bunun yerine:


Pulsar mesajları yalnızca **belge tanımlayıcısını** taşır
İşleyiciler, belge içeriğini doğrudan kütüphaneden alırlar
Alma işlemi, bir **geçici dosyaya akış şeklinde** gerçekleşir
Belgeye özgü ayrıştırma (PDF, metin vb.), bellek arabellekleri yerine dosyalarla çalışır

Bu, kütüphanenin belge yapısına bağımlı olmamasını sağlar. PDF ayrıştırma, metin
çıkarma ve diğer biçime özgü mantık, ilgili kodlayıcılarda kalır.

#### İşleme Akışı

```
Pulsar              PDF Decoder                Librarian              S3
  │                      │                          │                  │
  │── doc-id ───────────►│                          │                  │
  │  (processing msg)    │                          │                  │
  │                      │                          │                  │
  │                      │── stream-document ──────►│                  │
  │                      │   (doc-id)               │── GetObject ────►│
  │                      │                          │                  │
  │                      │◄── chunk ────────────────│◄── stream ───────│
  │                      │   (write to temp file)   │                  │
  │                      │◄── chunk ────────────────│◄── stream ───────│
  │                      │   (append to temp file)  │                  │
  │                      │         ⋮                │         ⋮        │
  │                      │◄── EOF ──────────────────│                  │
  │                      │                          │                  │
  │                      │   ┌──────────────────────────┐              │
  │                      │   │ temp file on disk        │              │
  │                      │   │ (memory stays bounded)   │              │
  │                      │   └────────────┬─────────────┘              │
  │                      │                │                            │
  │                      │   PDF library opens file                    │
  │                      │   extract page 1 text ──►  chunker          │
  │                      │   extract page 2 text ──►  chunker          │
  │                      │         ⋮                                   │
  │                      │   close file                                │
  │                      │   delete temp file                          │
```

#### Kütüphaneci Akış API'si

Bir akışlı belge alma işlemi ekleyin:

**`stream-document`**

İstek:
```json
{
  "operation": "stream-document",
  "document-id": "doc-123"
}
```

Yanıt: Akışlı ikili veri parçaları (tek bir yanıt değil).

REST API için, bu, `Transfer-Encoding: chunked` ile bir akışlı yanıt döndürür.

İç hizmetler arası iletişimler (işlemci ile kütüphaneci), şu şekilde olabilir:
İmza yoluyla doğrudan S3 akışı (eğer iç ağ izin veriyorsa)
Hizmet protokolü üzerinden parçalı yanıtlar
Özel bir akış uç noktası

Temel gereksinim: Veri, kütüphaneci tarafından asla tamamen tamponlanmadan, parçalar halinde akmalıdır.

#### PDF Kod Çözücü Değişiklikleri

**Mevcut uygulama** (bellek yoğun):

```python
def decode_pdf(document_content: bytes) -> str:
    reader = PdfReader(BytesIO(document_content))  # full doc in memory
    text = ""
    for page in reader.pages:
        text += page.extract_text()  # accumulating
    return text  # full text in memory
```

**Yeni uygulama** (geçici dosya, kademeli):

```python
def decode_pdf_streaming(doc_id: str, librarian_client) -> Iterator[str]:
    """Yield extracted text page by page."""

    with tempfile.NamedTemporaryFile(delete=True, suffix='.pdf') as tmp:
        # Stream document to temp file
        for chunk in librarian_client.stream_document(doc_id):
            tmp.write(chunk)
        tmp.flush()

        # Open PDF from file (not memory)
        reader = PdfReader(tmp.name)

        # Yield pages incrementally
        for page in reader.pages:
            yield page.extract_text()

        # tmp file auto-deleted on context exit
```

Bellek profili:
Geçici dosya diskte: PDF'nin boyutu (disk ucuzdur)
Bellekte: bir seferde bir sayfanın metni
Maksimum bellek: sınırlı, belge boyutundan bağımsız

#### Metin Belgesi Kod Çözücü Değişiklikleri

Düz metin belgeleri için, daha da basit - geçici dosyaya ihtiyaç yok:

```python
def decode_text_streaming(doc_id: str, librarian_client) -> Iterator[str]:
    """Yield text in chunks as it streams from storage."""

    buffer = ""
    for chunk in librarian_client.stream_document(doc_id):
        buffer += chunk.decode('utf-8')

        # Yield complete lines/paragraphs as they arrive
        while '\n\n' in buffer:
            paragraph, buffer = buffer.split('\n\n', 1)
            yield paragraph + '\n\n'

    # Yield remaining buffer
    if buffer:
        yield buffer
```

Metin belgeleri, geçici bir dosyaya ihtiyaç duymadan doğrudan akış halinde iletilebilir, çünkü bunlar
doğrusal bir yapıya sahiptir.

#### Akış Tabanlı Parçalama Entegrasyonu

Parçalayıcı, metin (sayfalar veya paragraflar)den oluşan bir yineleyici alır ve
parçaları kademeli olarak üretir:

```python
class StreamingChunker:
    def __init__(self, chunk_size: int, overlap: int):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def process(self, text_stream: Iterator[str]) -> Iterator[str]:
        """Yield chunks as text arrives."""
        buffer = ""

        for text_segment in text_stream:
            buffer += text_segment

            while len(buffer) >= self.chunk_size:
                chunk = buffer[:self.chunk_size]
                yield chunk
                # Keep overlap for context continuity
                buffer = buffer[self.chunk_size - self.overlap:]

        # Yield remaining buffer as final chunk
        if buffer.strip():
            yield buffer
```

#### Uçtan Uca İşlem Hattı

```python
async def process_document(doc_id: str, librarian_client, embedder):
    """Process document with bounded memory."""

    # Get document metadata to determine type
    metadata = await librarian_client.get_document_metadata(doc_id)

    # Select decoder based on document type
    if metadata.kind == 'application/pdf':
        text_stream = decode_pdf_streaming(doc_id, librarian_client)
    elif metadata.kind == 'text/plain':
        text_stream = decode_text_streaming(doc_id, librarian_client)
    else:
        raise UnsupportedDocumentType(metadata.kind)

    # Chunk incrementally
    chunker = StreamingChunker(chunk_size=1000, overlap=100)

    # Process each chunk as it's produced
    for chunk in chunker.process(text_stream):
        # Generate embeddings, store in vector DB, etc.
        embedding = await embedder.embed(chunk)
        await store_chunk(doc_id, chunk, embedding)
```

Hiçbir noktada, tam belge veya tam çıkarılmış metin bellekte tutulmaz.

#### Geçici Dosya Hususları

**Konum:** Sistem geçici dizinini kullanın (`/tmp` veya eşdeğeri).
Sanallaştırılmış dağıtımlar için, geçici dizinin yeterli alana sahip olduğundan ve mümkünse hızlı depolama üzerinde olduğundan emin olun.


**Temizleme:** Temizlemenin, istisnalar olsa bile, sağlanması için bağlam yöneticileri (`with tempfile...`) kullanın.


**Eşzamanlı işleme:** Her işleme görevi kendi geçici dosyasına sahiptir.
Paralel belge işleme arasında herhangi bir çakışma olmaz.

**Disk alanı:** Geçici dosyalar, kısa ömürlüdür (işlem süresi boyunca).
500MB'lık bir PDF için, işleme sırasında 500MB geçici alana ihtiyaç vardır. Disk alanı sınırlıysa, boyut sınırı yükleme sırasında uygulanabilir.


### Birlikte Çalışan İşlem Arayüzü: Alt Belgeler

PDF çıkarma ve metin belge işleme, aynı
aşağı akış hattına (parçalayıcı → gömüler → depolama) beslenmelidir. Bunu, tutarlı bir "ID'ye göre alma" arayüzüyle sağlamak için, çıkarılan metin blokları, "librarian"a alt belgeler olarak geri kaydedilir.



#### Alt Belgelerle İşlem Akışı

```
PDF Document                                         Text Document
     │                                                     │
     ▼                                                     │
pdf-extractor                                              │
     │                                                     │
     │ (stream PDF from librarian)                         │
     │ (extract page 1 text)                               │
     │ (store as child doc → librarian)                    │
     │ (extract page 2 text)                               │
     │ (store as child doc → librarian)                    │
     │         ⋮                                           │
     ▼                                                     ▼
[child-doc-id, child-doc-id, ...]                    [doc-id]
     │                                                     │
     └─────────────────────┬───────────────────────────────┘
                           ▼
                       chunker
                           │
                           │ (receives document ID)
                           │ (streams content from librarian)
                           │ (chunks incrementally)
                           ▼
                    [chunks → embedding → storage]
```

Parçalayıcı, tek bir standart arayüze sahiptir:
Bir belge kimliğini alın (Pulsar aracılığıyla)
Kütüphaneden içeriği akış olarak alın
Bunu parçalara ayırın

Bu, kimliğin neye atıfta bulunduğunu bilmez veya umursamaz:
Kullanıcı tarafından yüklenen bir metin belgesi
Bir PDF sayfasından çıkarılan bir metin bloğu
Herhangi bir gelecekteki belge türü

#### Alt Belge Meta Verileri

Belge şemasını, ana/alt ilişkilerini izlemek için genişletin:

```sql
-- Add columns to document table
ALTER TABLE document ADD parent_id text;
ALTER TABLE document ADD document_type text;

-- Index for finding children of a parent
CREATE INDEX document_parent ON document (parent_id);
```

**Belge türleri:**

| `document_type` | Açıklama |
|-----------------|-------------|
| `source` | Kullanıcı tarafından yüklenen belge (PDF, metin, vb.) |
| `extracted` | Kaynak bir belgeden türetilmiş (örneğin, PDF sayfa metni) |

**Meta veri alanları:**

| Alan | Kaynak Belge | Çıkarılan Alt Belge |
|-------|-----------------|-----------------|
| `id` | kullanıcı tarafından sağlanan veya oluşturulan | oluşturulan (örneğin, `{parent-id}-page-{n}`) |
| `parent_id` | `NULL` | ana belge kimliği |
| `document_type` | `source` | `extracted` |
| `kind` | `application/pdf`, vb. | `text/plain` |
| `title` | kullanıcı tarafından sağlanan | oluşturulan (örneğin, "Rapor.pdf'nin 3. sayfası") |
| `user` | kimliği doğrulanmış kullanıcı | ana belge ile aynı |

#### Alt Belgeler için Kütüphaneci API'si

**Alt belgeler oluşturma** (içerik, pdf-extractor tarafından kullanılır):

```json
{
  "operation": "add-child-document",
  "parent-id": "doc-123",
  "document-metadata": {
    "id": "doc-123-page-1",
    "kind": "text/plain",
    "title": "Page 1"
  },
  "content": "<base64-encoded-text>"
}
```

Küçük boyutlu, çıkarılmış metinler için (tipik bir sayfa metni < 100KB), tek seferlik yükleme kabul edilebilir. Çok büyük metin çıkarımları için, parçalı yükleme kullanılabilir.

**Alt belgelerin listelenmesi** (hata ayıklama/yönetim için):



```json
{
  "operation": "list-children",
  "parent-id": "doc-123"
}
```

Yanıt:
```json
{
  "children": [
    { "id": "doc-123-page-1", "title": "Page 1", "kind": "text/plain" },
    { "id": "doc-123-page-2", "title": "Page 2", "kind": "text/plain" },
    ...
  ]
}
```

#### Kullanıcı Arayüzü Davranışı

**`list-documents` varsayılan davranış:**

```sql
SELECT * FROM document WHERE user = ? AND parent_id IS NULL;
```

Yalnızca en üst düzey (kaynak) belgeler, kullanıcının belge listesinde görünür.
Alt belgeler, varsayılan olarak filtrelenir.

**İsteğe bağlı "çocukları-dahil-et" bayrağı** (yönetici/hata ayıklama için):

```json
{
  "operation": "list-documents",
  "include-children": true
}
```

#### Kaskad Sıralı Silme

Bir üst belge silindiğinde, tüm alt belgelerin de silinmesi gerekir:

```python
def delete_document(doc_id: str):
    # Find all children
    children = query("SELECT id, object_id FROM document WHERE parent_id = ?", doc_id)

    # Delete child blobs from S3
    for child in children:
        blob_store.delete(child.object_id)

    # Delete child metadata from Cassandra
    execute("DELETE FROM document WHERE parent_id = ?", doc_id)

    # Delete parent blob and metadata
    parent = get_document(doc_id)
    blob_store.delete(parent.object_id)
    execute("DELETE FROM document WHERE id = ? AND user = ?", doc_id, user)
```

#### Depolama Hususları

Çıkarılan metin blokları, yinelenen içerik oluşturur:
Orijinal PDF, "Garage" (Depo) içinde saklanır.
Her sayfa için çıkarılan metin de "Garage" içinde saklanır.

Bu denge şunları sağlar:
**Tutarlı bir parçalama arayüzü**: Parçalayıcı her zaman ID'ye göre veri alır.
**Devam ettirme/yeniden deneme**: PDF'i yeniden çıkarmadan, parçalama aşamasında yeniden başlatılabilir.
**Hata ayıklama**: Çıkarılan metin incelenebilir.
**Sorumlulukların ayrılması**: PDF çıkarıcı ve parçalayıcı bağımsız hizmetlerdir.

200 sayfalık ve sayfa başına ortalama 5KB metin içeren 500MB'lık bir PDF için:
PDF depolama: 500MB
Çıkarılan metin depolama: ~1MB toplam
Ek yük: ihmal edilebilir

#### PDF Çıkarıcı Çıktısı

pdf-çıkarıcı, bir belgeyi işledikten sonra:

1. PDF'i "librarian" (kütüphaneci) üzerinden geçici bir dosyaya aktarır.
2. Metni sayfa sayfa çıkarır.
3. Her sayfa için, çıkarılan metni "librarian" aracılığıyla bir alt belge olarak saklar.
4. Alt belge ID'lerini parçalayıcı kuyruğuna gönderir.
ÇIKTI SÖZLEŞMESİ (tam olarak aşağıdaki formatı takip etmelidir):
```python
async def extract_pdf(doc_id: str, librarian_client, output_queue):
    """Extract PDF pages and store as child documents."""

    with tempfile.NamedTemporaryFile(delete=True, suffix='.pdf') as tmp:
        # Stream PDF to temp file
        for chunk in librarian_client.stream_document(doc_id):
            tmp.write(chunk)
        tmp.flush()

        # Extract pages
        reader = PdfReader(tmp.name)
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()

            # Store as child document
            child_id = f"{doc_id}-page-{page_num}"
            await librarian_client.add_child_document(
                parent_id=doc_id,
                document_id=child_id,
                kind="text/plain",
                title=f"Page {page_num}",
                content=text.encode('utf-8')
            )

            # Send to chunker queue
            await output_queue.send(child_id)
```

Parçalayıcı, bu alt kimlikleri alır ve bunları, bir kullanıcının yüklediği bir metin belgesini işlerken olduğu gibi aynı şekilde işler.

### İstemci Güncellemeleri

#### Python SDK


Python SDK'sı (`trustgraph-base/trustgraph/api/library.py`), parçalı yüklemeleri şeffaf bir şekilde işlemelidir. Kamu arayüzü değişmeden kalır:


```python
# Existing interface - no change for users
library.add_document(
    id="doc-123",
    title="Large Report",
    kind="application/pdf",
    content=large_pdf_bytes,  # Can be hundreds of MB
    tags=["reports"]
)
```

İçeride, SDK belge boyutunu algılar ve stratejiyi değiştirir:

```python
class Library:
    CHUNKED_UPLOAD_THRESHOLD = 2 * 1024 * 1024  # 2MB

    def add_document(self, id, title, kind, content, tags=None, ...):
        if len(content) < self.CHUNKED_UPLOAD_THRESHOLD:
            # Small document: single operation (existing behavior)
            return self._add_document_single(id, title, kind, content, tags)
        else:
            # Large document: chunked upload
            return self._add_document_chunked(id, title, kind, content, tags)

    def _add_document_chunked(self, id, title, kind, content, tags):
        # 1. begin-upload
        session = self._begin_upload(
            document_metadata={...},
            total_size=len(content),
            chunk_size=5 * 1024 * 1024
        )

        # 2. upload-chunk for each chunk
        for i, chunk in enumerate(self._chunk_bytes(content, session.chunk_size)):
            self._upload_chunk(session.upload_id, i, chunk)

        # 3. complete-upload
        return self._complete_upload(session.upload_id)
```

**İlerleme geri bildirimleri** (isteğe bağlı iyileştirme):

```python
def add_document(self, ..., on_progress=None):
    """
    on_progress: Optional callback(bytes_sent, total_bytes)
    """
```

Bu, kullanıcı arayüzlerinin temel API'yi değiştirmeden yükleme ilerlemesini görüntülemesini sağlar.

#### Komut Satırı Araçları

**`tg-add-library-document`** değişmeden çalışmaya devam ediyor:

```bash
# Works transparently for any size - SDK handles chunking internally
tg-add-library-document --file large-report.pdf --title "Large Report"
```

İsteğe bağlı bir ilerleme durumu göstergesi eklenebilir:

```bash
tg-add-library-document --file large-report.pdf --title "Large Report" --progress
# Output:
# Uploading: 45% (225MB / 500MB)
```

**Eski araçlar kaldırıldı:**

`tg-load-pdf` - kullanımdan kaldırıldı, `tg-add-library-document`'i kullanın.
`tg-load-text` - kullanımdan kaldırıldı, `tg-add-library-document`'i kullanın.

**Yönetici/hata ayıklama komutları** (isteğe bağlı, düşük öncelikli):

```bash
# List incomplete uploads (admin troubleshooting)
tg-add-library-document --list-pending

# Resume specific upload (recovery scenario)
tg-add-library-document --resume upload-abc-123 --file large-report.pdf
```

Bunlar, ayrı araçlar yerine mevcut komuttaki bayraklar olabilir.

#### API Özellik Güncellemeleri

OpenAPI spesifikasyonu (`specs/api/paths/librarian.yaml`), aşağıdaki güncellemeleri gerektiriyor:

**Yeni işlemler:**

`begin-upload` - Parçalı yükleme oturumunu başlat
`upload-chunk` - Tek bir parçayı yükle
`complete-upload` - Yüklemeyi tamamla
`abort-upload` - Yüklemeyi iptal et
`get-upload-status` - Yükleme ilerlemesini sorgula
`list-uploads` - Kullanıcı için tamamlanmamış yüklemeleri listele
`stream-document` - Akışlı belge alma
`add-child-document` - Çıkarılan metni kaydet (iç)
`list-children` - Alt belgeleri listele (yönetici)

**Değiştirilen işlemler:**

`list-documents` - `include-children` parametresini ekle

**Yeni şemalar:**

`ChunkedUploadBeginRequest`
`ChunkedUploadBeginResponse`
`ChunkedUploadChunkRequest`
`ChunkedUploadChunkResponse`
`UploadSession`
`UploadProgress`

**WebSocket spesifikasyonunda yapılan güncellemeler** (`specs/websocket/`):

WebSocket istemcileri için REST işlemlerini yansıtın, böylece yükleme sırasında gerçek zamanlı
ilerleme güncellemeleri sağlanır.

#### Kullanıcı Deneyimi Hususları

API spesifikasyonundaki güncellemeler, ön yüzdeki iyileştirmelere olanak tanır:

**Yükleme ilerleme arayüzü:**
Yüklenen parçaları gösteren ilerleme çubuğu
Kalan tahmini süre
Duraklatma/devam ettirme özelliği

**Hata kurtarma:**
Kesintiye uğramış yüklemeler için "Yüklemeyi devam ettir" seçeneği
Yeniden bağlanırken bekleyen yüklemelerin listesi

**Büyük dosya işleme:**
İstemci tarafında dosya boyutu tespiti
Büyük dosyalar için otomatik parçalı yükleme
Uzun yüklemeler sırasında net geri bildirim

Bu kullanıcı deneyimi iyileştirmeleri, güncellenmiş API spesifikasyonu tarafından yönlendirilen ön yüz işleme gerektirir.
