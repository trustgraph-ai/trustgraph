# Yapılandırılmış Veri Teknik Özellikleri (Bölüm 2)

## Genel Bakış

Bu özellik, TrustGraph'ın yapılandırılmış veri entegrasyonunun ilk uygulamasının ilk aşamalarında tespit edilen sorunları ve eksiklikleri ele almaktadır, bu da `structured-data.md`'da açıklanmıştır.

## Sorun Tanımları

### 1. İsimlendirme Tutarsızlığı: "Nesne" vs "Satır"

Mevcut uygulama, "nesne" terimini tüm alanlarda kullanmaktadır (örneğin, `ExtractedObject`, nesne çıkarma, nesne gömme). Bu isimlendirme çok genel olup kafa karışıklığına neden olmaktadır:

"Nesne" terimi, yazılımda (Python nesneleri, JSON nesneleri vb.) aşırı kullanılan bir terimdir.
İşlenen veri temelde tablolardır; tanımlı şemalara sahip satırlar.
"Satır", veri modelini daha doğru bir şekilde tanımlar ve veritabanı terminolojisiyle uyumludur.

Bu tutarsızlık, modül adlarında, sınıf adlarında, mesaj türlerinde ve belgelerde görülmektedir.

### 2. Satır Depolama Sorgu Sınırlamaları

Mevcut satır depolama uygulamasının önemli sorgu sınırlamaları bulunmaktadır:

**Doğal Dil Uyumsuzluğu**: Sorgular, gerçek dünya verilerindeki değişikliklerle başa çıkmakta zorlanmaktadır. Örneğin:
`"CHESTNUT ST"` içeren bir sokak veritabanını sorgulamak, `"Chestnut Street"` hakkında bilgi almak için zordur.
Kısaltmalar, büyük/küçük harf farklılıkları ve biçimlendirme değişiklikleri, tam eşleşme sorgularını bozmaktadır.
Kullanıcılar semantik bir anlayış beklemekte, ancak depolama literal eşleşme sağlamaktadır.

**Şema Evrimi Sorunları**: Şemaların değiştirilmesi sorunlara neden olmaktadır:
Mevcut veriler, güncellenmiş şemalara uygun olmayabilir.
Tablo yapısındaki değişiklikler, sorguları ve veri bütünlüğünü bozabilir.
Şema güncellemeleri için net bir geçiş yolu bulunmamaktadır.

### 3. Satır Gömme Gerekliliği

2. soruna bağlı olarak, sistemin satır verileri için vektör gömmelere ihtiyacı vardır, bu da şunları sağlamak için gereklidir:

Yapılandırılmış veriler arasında semantik arama (örneğin, "Chestnut Street" verisinin "CHESTNUT ST" olarak bulunduğu durumlarda)
Bulanık sorgular için benzerlik eşleştirme
Yapılandırılmış filtreleri semantik benzerlikle birleştiren hibrit arama
Daha iyi doğal dil sorgu desteği

Gömme hizmeti belirtilmiş, ancak uygulanmamıştır.

### 4. Satır Veri Alımı Eksikliği

Yapılandırılmış veri alım hattı henüz tam olarak çalışır durumda değildir:

Giriş formatlarını (CSV, JSON vb.) sınıflandırmak için tanısal istemler bulunmaktadır.
Bu istemleri kullanan alım hizmeti, sisteme entegre edilmemiştir.
Önceden yapılandırılmış verileri satır deposuna yüklemek için uçtan uca bir yol bulunmamaktadır.

## Hedefler

**Şema Esnekliği**: Mevcut verileri bozmadan veya geçişler gerektirmeden şema evrimini etkinleştirin.
**Tutarlı İsimlendirme**: Kod tabanında "satır" terimini standartlaştırın.
**Semantik Sorgulanabilirlik**: Satır gömmeleri aracılığıyla bulanık/semantik eşleştirmeyi destekleyin.
**Tam Alım Hattı**: Yapılandırılmış verileri yüklemek için uçtan uca bir yol sağlayın.

## Teknik Tasarım

### Birleşik Satır Depolama Şeması

Önceki uygulamada, her şema için ayrı bir Cassandra tablosu oluşturulmuştur. Bu, şema evrimleri sırasında tablo yapısındaki değişikliklerin geçişler gerektirmesine neden olmuştur.

Yeni tasarım, tüm satır verileri için tek birleşik bir tablo kullanmaktadır:

```sql
CREATE TABLE rows (
    collection text,
    schema_name text,
    index_name text,
    index_value frozen<list<text>>,
    data map<text, text>,
    source text,
    PRIMARY KEY ((collection, schema_name, index_name), index_value)
)
```

#### Sütun Tanımları

| Sütun | Tür | Açıklama |
|--------|------|-------------|
| `collection` | `text` | Veri toplama/içe aktarma tanımlayıcısı (metaveriden) |
| `schema_name` | `text` | Bu satırın uyduğu şema adı |
| `index_name` | `text` | Birleştirilmiş virgülle indekslenen alan(lar) adı |
| `index_value` | `frozen<list<text>>` | Liste olarak indeks değerleri |
| `data` | `map<text, text>` | Satır verisi, anahtar-değer çiftleri olarak |
| `source` | `text` | Bilgi grafiğindeki kaynak bilgisine bağlanan isteğe bağlı URI. Boş bir dize veya NULL, kaynak olmadığını gösterir. |

#### İndeks Yönetimi

Her satır, şemada tanımlanan her indeks için bir kez olmak üzere birden çok kez saklanır. Birincil anahtar alanları, özel bir işaretçi olmadan bir indeks olarak kabul edilir ve bu, gelecekteki esnekliği sağlar.

**Tek alanlı indeks örneği:**
Şema, `email`'ı indeks olarak tanımlar
`index_name = "email"`
`index_value = ['foo@bar.com']`

**Bileşik indeks örneği:**
Şema, `region` ve `status` üzerinde bileşik bir indeks tanımlar
`index_name = "region,status"` (alan adları sıralanır ve virgülle birleştirilir)
`index_value = ['US', 'active']` (değerler, alan adları sırasıyla aynı sırada)

**Birincil anahtar örneği:**
Şema, `customer_id`'ı birincil anahtar olarak tanımlar
`index_name = "customer_id"`
`index_value = ['CUST001']`

#### Sorgu Desenleri

Tüm sorgular, kullanılan indeksten bağımsız olarak aynı deseni izler:

```sql
SELECT * FROM rows
WHERE collection = 'import_2024'
  AND schema_name = 'customers'
  AND index_name = 'email'
  AND index_value = ['foo@bar.com']
```

#### Tasarım Uzlaşmaları

**Avantajları:**
Şema değişiklikleri, tablo yapısı değişiklikleri gerektirmez.
Satır verileri Cassandra için şeffaftır; alan ekleme/çıkarma işlemleri şeffaftır.
Tüm erişim yöntemleri için tutarlı sorgu kalıbı.
Cassandra'nın ikincil indeksleri (ki bunlar ölçekte yavaş olabilir).
Tüm yerel Cassandra türleri (`map`, `frozen<list>`).

**Uzlaşmalar:**
Yazma çoğaltması: her satır eklemesi = N eklemesi (dizinlenmiş alan başına bir tane).
Tekrarlanan satır verilerinden kaynaklanan depolama ek yükü.
Tür bilgisi şema yapılandırmasında saklanır, dönüşüm uygulama katmanında yapılır.

#### Tutarlılık Modeli

Bu tasarım, belirli basitleştirmeleri kabul eder:

1. **Satır güncellemeleri yok:** Sistem yalnızca eklemelerle çalışır. Bu, aynı satırın birden çok kopyasının güncellenmesiyle ilgili tutarlılık sorunlarını ortadan kaldırır.

2. **Şema değişikliği toleransı:** Şemalar değiştiğinde (örneğin, indeksler eklendi/çıkarıldı), mevcut satırlar orijinal dizinlemelerini korur. Eski satırlar, gerektiğinde kullanıcılar tutarlılığı sağlamak için bir şemayı silebilir ve yeniden oluşturabilir, ancak yeni indeksler aracılığıyla bulunamaz.

### Bölüm Takibi ve Silme

#### Sorun

Bölüm anahtarı `(collection, schema_name, index_name)` ile, verimli silme, silinecek tüm bölüm anahtarlarını bilmeyi gerektirir. Yalnızca `collection` veya `collection + schema_name` ile silmek, veriye sahip olan tüm `index_name` değerlerini bilmeyi gerektirir.

#### Bölüm Takip Tablosu

Birincil olmayan bir arama tablosu, hangi bölümlerin mevcut olduğunu izler:

```sql
CREATE TABLE row_partitions (
    collection text,
    schema_name text,
    index_name text,
    PRIMARY KEY ((collection), schema_name, index_name)
)
```

Bu, silme işlemleri için bölümlerin verimli bir şekilde bulunmasını sağlar.

#### Satır Yazıcı Davranışı

Satır yazıcı, kaydedilen `(collection, schema_name)` çiftlerinin bellek içi bir önbelleğini tutar. Bir satırı işlerken:

1. `(collection, schema_name)`'ın önbellekte olup olmadığını kontrol edin.
2. Önbellekte yoksa (bu çift için ilk satır):
   Tüm indeks adlarını almak için şema yapılandırmasını arayın.
   Her `(collection, schema_name, index_name)` için `row_partitions`'a girişler ekleyin.
   Çifti önbelleğe ekleyin.
3. Satır verilerini yazmaya devam edin.

Satır yazıcı ayrıca şema yapılandırma değişiklik olaylarını da izler. Bir şema değiştiğinde, ilgili önbellek girişleri temizlenir, böylece sonraki satır, güncellenmiş indeks adlarıyla yeniden kayda alınmasını sağlar.

Bu yaklaşım şunları sağlar:
Arama tablosu yazmaları, satır başına değil, her `(collection, schema_name)` çifti için bir kez gerçekleşir.
Arama tablosu, verilerin yazıldığı sırada aktif olan indeksleri yansıtır.
İçe aktarma sırasında yapılan şema değişiklikleri doğru şekilde algılanır.

#### Silme İşlemleri

**Koleksiyonu sil:**
```sql
-- 1. Discover all partitions
SELECT schema_name, index_name FROM row_partitions WHERE collection = 'X';

-- 2. Delete each partition from rows table
DELETE FROM rows WHERE collection = 'X' AND schema_name = '...' AND index_name = '...';
-- (repeat for each discovered partition)

-- 3. Clean up the lookup table
DELETE FROM row_partitions WHERE collection = 'X';
```

**Koleksiyonu ve şemayı sil:**
```sql
-- 1. Discover partitions for this schema
SELECT index_name FROM row_partitions WHERE collection = 'X' AND schema_name = 'Y';

-- 2. Delete each partition from rows table
DELETE FROM rows WHERE collection = 'X' AND schema_name = 'Y' AND index_name = '...';
-- (repeat for each discovered partition)

-- 3. Clean up the lookup table entries
DELETE FROM row_partitions WHERE collection = 'X' AND schema_name = 'Y';
```

### Satır Gömme İşlemleri

Satır gömme işlemleri, indeksli değerlerde semantik/bulanık eşleşme sağlayarak, doğal dil uyumsuzluğu sorununu çözer (örneğin, "Chestnut Street" için arama yaparken "CHESTNUT ST" bulmak).

#### Tasarım Genel Bakışı

Her indeksli değer gömülür ve bir vektör deposunda (Qdrant) saklanır. Sorgu zamanında, sorgu gömülür, benzer vektörler bulunur ve ilişkili meta veriler, Cassandra'daki gerçek satırları bulmak için kullanılır.

#### Qdrant Koleksiyonu Yapısı

Her `(user, collection, schema_name, dimension)` tuple'ı için bir Qdrant koleksiyonu:

**Koleksiyon adı:** `rows_{user}_{collection}_{schema_name}_{dimension}`
İsimler temizlenir (alfanumerik olmayan karakterler `_` ile değiştirilir, küçük harfe dönüştürülür, sayısal önekler `r_` öneki alır)
**Gerekçe:** Bir `(user, collection, schema_name)` örneğini, eşleşen Qdrant koleksiyonlarını silerek temiz bir şekilde silmeyi sağlar; boyut soneki, farklı gömme modellerinin birlikte var olmasına olanak tanır.

#### Nelerin Gömüldüğü

İndeks değerlerinin metin gösterimi:

| İndeks Tipi | Örnek `index_value` | Gömülecek Metin |
|------------|----------------------|---------------|
| Tek Alan | `['foo@bar.com']` | `"foo@bar.com"` |
| Birleşik | `['US', 'active']` | `"US active"` (boşluklarla birleştirilmiş) |

#### Nokta Yapısı

Her Qdrant noktası şunları içerir:

```json
{
  "id": "<uuid>",
  "vector": [0.1, 0.2, ...],
  "payload": {
    "index_name": "street_name",
    "index_value": ["CHESTNUT ST"],
    "text": "CHESTNUT ST"
  }
}
```

| Yük Verisi Alanı | Açıklama |
|---------------|-------------|
| `index_name` | Bu gömme işleminin temsil ettiği indeksli alan(lar). |
| `index_value` | Cassandra araması için orijinal değer listesi. |
| `text` | Gömülen metin (hata ayıklama/görüntüleme için). |

Not: `user`, `collection` ve `schema_name`, Qdrant koleksiyon adı aracılığıyla örtülüdür. |

#### Sorgu Akışı |

1. Kullanıcı, kullanıcı U, koleksiyon X ve şema Y içinde "Chestnut Street" için sorgu yapar. |
2. Sorgu metnini gömün. |
3. Önekle eşleşen Qdrant koleksiyon adı(larını) belirleyin: `rows_U_X_Y_`. |
4. En yakın vektörler için eşleşen Qdrant koleksiyonları içinde arama yapın. |
5. `index_name` ve `index_value` içeren yük verilerine sahip eşleşen noktaları alın. |
6. Cassandra'ya sorgu yapın: |
   ```sql
   SELECT * FROM rows
   WHERE collection = 'X'
     AND schema_name = 'Y'
     AND index_name = '<from payload>'
     AND index_value = <from payload>
   ```
7. Eşleşen satırları döndür.

#### İsteğe Bağlı: İndeks Adı ile Filtreleme

Sorgular, Qdrant'ta yalnızca belirli alanları aramak için isteğe bağlı olarak `index_name` ile filtrelenebilir:

**" 'Chestnut' ile eşleşen herhangi bir alanı bul"** → koleksiyondaki tüm vektörleri arayın.
**" 'Chestnut' ile eşleşen 'street_name' alanını bul"** → `payload.index_name = 'street_name'` alanını filtreleyin.

#### Mimari

Satır gömüleri, GraphRAG tarafından kullanılan **iki aşamalı yapılandırmaya** sahiptir (grafik-gömüleri, belge-gömüleri):

**1. Aşama: Gömü hesaplama** (`trustgraph-flow/trustgraph/embeddings/row_embeddings/`) - `ExtractedObject`'i tüketir, gömü hizmeti aracılığıyla gömüleri hesaplar, `RowEmbeddings` çıktısını üretir.
**2. Aşama: Gömü depolama** (`trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/`) - `RowEmbeddings`'i tüketir, vektörleri Qdrant'a yazar.

Cassandra satır yazarı, ayrı bir paralel tüketici işlemidir:

**Cassandra satır yazarı** (`trustgraph-flow/trustgraph/storage/rows/cassandra`) - `ExtractedObject`'i tüketir, satırları Cassandra'ya yazar.

Tüm üç hizmet de aynı akıştan tüketir, böylece bunlar birbirinden ayrılır. Bu, şunları sağlar:
Cassandra yazma işlemlerinin, gömü oluşturma işlemlerine ve vektör depolama işlemlerine göre bağımsız olarak ölçeklenebilmesi.
Gerekli değilse gömü hizmetleri devre dışı bırakılabilir.
Bir hizmetteki hatalar diğerlerini etkilemez.
GraphRAG işlem hatları ile tutarlı bir mimari.

#### Yazma Yolu

**1. Aşama (satır-gömü işlemcisi):** Bir `ExtractedObject` aldığında:

1. İndeksli alanları bulmak için şemayı arayın.
2. Her indeksli alan için:
   İndeks değerinin metin gösterimini oluşturun.
   Gömü hizmeti aracılığıyla gömüyü hesaplayın.
3. Tüm hesaplanan vektörleri içeren bir `RowEmbeddings` mesajı çıktısını verin.

**2. Aşama (satır-gömü-yaz-qdrant):** Bir `RowEmbeddings` aldığında:

1. Mesajdaki her gömü için:
   `(user, collection, schema_name, dimension)`'dan Qdrant koleksiyonunu belirleyin.
   Gerekirse koleksiyonu oluşturun (ilk yazmada tembel oluşturma).
   Vektör ve yük ile noktayı ekleyin/güncelleyin.

#### Mesaj Türleri

```python
@dataclass
class RowIndexEmbedding:
    index_name: str              # The indexed field name(s)
    index_value: list[str]       # The field value(s)
    text: str                    # Text that was embedded
    vectors: list[list[float]]   # Computed embedding vectors

@dataclass
class RowEmbeddings:
    metadata: Metadata
    schema_name: str
    embeddings: list[RowIndexEmbedding]
```

#### Silme Entegrasyonu

Qdrant koleksiyonları, koleksiyon adı kalıbına göre önek eşleştirmesiyle bulunur:

**`(user, collection)`'ı Silin:**
1. Önek `rows_{user}_{collection}_` ile eşleşen tüm Qdrant koleksiyonlarını listeleyin
2. Her eşleşen koleksiyonu silin
3. Cassandra satır bölümlerini silin (yukarıda belirtildiği gibi)
4. `row_partitions` girişlerini temizleyin

**`(user, collection, schema_name)`'ı Silin:**
1. Önek `rows_{user}_{collection}_{schema_name}_` ile eşleşen tüm Qdrant koleksiyonlarını listeleyin
2. Her eşleşen koleksiyonu silin (çoklu boyutları işler)
3. Cassandra satır bölümlerini silin
4. `row_partitions`'ı temizleyin

#### Modül Konumları

| Aşama | Modül | Giriş Noktası |
|-------|--------|-------------|
| Aşama 1 | `trustgraph-flow/trustgraph/embeddings/row_embeddings/` | `row-embeddings` |
| Aşama 2 | `trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/` | `row-embeddings-write-qdrant` |

### Satır Gömme Sorgu API'si

Satır gömme sorgusu, GraphQL satır sorgu hizmetinden **ayrı bir API'dir**:

| API | Amaç | Arka Uç |
|-----|---------|---------|
| Satır Sorgusu (GraphQL) | İndekslenmiş alanlarda tam eşleşme | Cassandra |
| Satır Gömme Sorgusu | Bulanık/anlamsal eşleşme | Qdrant |

Bu ayrım, işlevleri net tutar:
GraphQL hizmeti, tam ve yapılandırılmış sorgulara odaklanır
Gömme API'si, anlamsal benzerliği işler
Kullanıcı iş akışı: adayları bulmak için gömmeler aracılığıyla bulanık arama, ardından tam satır verilerini almak için tam sorgu

#### İstek/Yanıt Şeması

```python
@dataclass
class RowEmbeddingsRequest:
    vectors: list[list[float]]    # Query vectors (pre-computed embeddings)
    user: str = ""
    collection: str = ""
    schema_name: str = ""
    index_name: str = ""          # Optional: filter to specific index
    limit: int = 10               # Max results per vector

@dataclass
class RowIndexMatch:
    index_name: str = ""          # The matched index field(s)
    index_value: list[str] = []   # The matched value(s)
    text: str = ""                # Original text that was embedded
    score: float = 0.0            # Similarity score

@dataclass
class RowEmbeddingsResponse:
    error: Error | None = None
    matches: list[RowIndexMatch] = []
```

#### Sorgu İşleyici

Modül: `trustgraph-flow/trustgraph/query/row_embeddings/qdrant`

Giriş noktası: `row-embeddings-query-qdrant`

İşleyici:
1. `RowEmbeddingsRequest` ile sorgu vektörlerini alır.
2. Önek eşleştirmesiyle uygun Qdrant koleksiyonunu bulur.
3. İsteğe bağlı `index_name` filtresiyle en yakın vektörleri arar.
4. Eşleşen indeks bilgileriyle `RowEmbeddingsResponse` döndürür.

#### API Ağ Geçidi Entegrasyonu

Ağ geçidi, standart istek/yanıt kalıbı aracılığıyla satır gömme sorgularını sunar:

| Bileşen | Konum |
|-----------|----------|
| Yönlendirici | `trustgraph-flow/trustgraph/gateway/dispatch/row_embeddings_query.py` |
| Kayıt | `"row-embeddings"`'ı `request_response_dispatchers`'e `manager.py` içinde ekleyin |

Akış arayüz adı: `row-embeddings`

Akış şablonundaki arayüz tanımı:
```json
{
  "interfaces": {
    "row-embeddings": {
      "request": "non-persistent://tg/request/row-embeddings:{id}",
      "response": "non-persistent://tg/response/row-embeddings:{id}"
    }
  }
}
```

#### Python SDK Desteği

SDK, satır gömme sorguları için yöntemler sağlar:

```python
# Flow-scoped query (preferred)
api = Api(url)
flow = api.flow().id("default")

# Query with text (SDK computes embeddings)
matches = flow.row_embeddings_query(
    text="Chestnut Street",
    collection="my_collection",
    schema_name="addresses",
    index_name="street_name",  # Optional filter
    limit=10
)

# Query with pre-computed vectors
matches = flow.row_embeddings_query(
    vectors=[[0.1, 0.2, ...]],
    collection="my_collection",
    schema_name="addresses"
)

# Each match contains:
for match in matches:
    print(match.index_name)   # e.g., "street_name"
    print(match.index_value)  # e.g., ["CHESTNUT ST"]
    print(match.text)         # e.g., "CHESTNUT ST"
    print(match.score)        # e.g., 0.95
```

#### CLI Yardımcı Programı

Komut: `tg-invoke-row-embeddings`

```bash
# Query by text (computes embedding automatically)
tg-invoke-row-embeddings \
  --text "Chestnut Street" \
  --collection my_collection \
  --schema addresses \
  --index street_name \
  --limit 10

# Query by vector file
tg-invoke-row-embeddings \
  --vectors vectors.json \
  --collection my_collection \
  --schema addresses

# Output formats
tg-invoke-row-embeddings --text "..." --format json
tg-invoke-row-embeddings --text "..." --format table
```

#### Tipik Kullanım Şekli

Satır gömme sorgusu genellikle bulanık aramadan kesin aramaya geçiş akışının bir parçası olarak kullanılır:

```python
# Step 1: Fuzzy search via embeddings
matches = flow.row_embeddings_query(
    text="chestnut street",
    collection="geo",
    schema_name="streets"
)

# Step 2: Exact lookup via GraphQL for full row data
for match in matches:
    query = f'''
    query {{
        streets(where: {{ {match.index_name}: {{ eq: "{match.index_value[0]}" }} }}) {{
            street_name
            city
            zip_code
        }}
    }}
    '''
    rows = flow.rows_query(query, collection="geo")
```

Bu iki aşamalı yapı şu olanakları sağlar:
Kullanıcı "Chestnut Street" araması yaptığında "CHESTNUT ST" ifadesinin bulunması
Tüm alanlarıyla birlikte eksiksiz satır verilerinin alınması
Anlamsal benzerliği yapılandırılmış veri erişimiyle birleştirme

### Satır Veri Alımı

Daha sonraki bir aşamaya ertelenmiştir. Diğer veri alım değişiklikleriyle birlikte tasarlanacaktır.

## Uygulama Etkisi

### Mevcut Durum Analizi

Mevcut uygulama iki ana bileşenden oluşmaktadır:

| Bileşen | Konum | Satır Sayısı | Açıklama |
|-----------|----------|-------|-------------|
| Sorgu Servisi | `trustgraph-flow/trustgraph/query/objects/cassandra/service.py` | ~740 | Tek bir blok: GraphQL şema oluşturma, filtre ayrıştırma, Cassandra sorguları, istek işleme |
| Yazıcı | `trustgraph-flow/trustgraph/storage/objects/cassandra/write.py` | ~540 | Şema başına tablo oluşturma, ikincil indeksler, ekleme/silme |

**Mevcut Sorgu Modeli:**
```sql
SELECT * FROM {keyspace}.o_{schema_name}
WHERE collection = 'X' AND email = 'foo@bar.com'
ALLOW FILTERING
```

**Yeni Sorgu Deseni:**
```sql
SELECT * FROM {keyspace}.rows
WHERE collection = 'X' AND schema_name = 'customers'
  AND index_name = 'email' AND index_value = ['foo@bar.com']
```

### Önemli Değişiklikler

1. **Sorgu anlamları basitleştirildi**: Yeni şema, yalnızca `index_value` üzerindeki tam eşleşmeleri desteklemektedir. Mevcut GraphQL filtreleri (`gt`, `lt`, `contains`, vb.):
   Gerekliyse, döndürülen veriler üzerinde arka filtreleme olarak kullanılır.
   Bulanık eşleştirme için gömülü API'nin kullanılması lehine kaldırılır.

2. **GraphQL kodu sıkı bir şekilde birleştirilmiş durumda**: Mevcut `service.py`, Strawberry türü oluşturma, filtre ayrıştırma ve Cassandra'ya özgü sorguları bir araya getirmektedir. Başka bir satır depolama arka ucunun eklenmesi, yaklaşık 400 satır GraphQL kodunun çoğaltılmasına neden olacaktır.

### Önerilen Yeniden Düzenleme

Yeniden düzenleme iki bölümden oluşmaktadır:

#### 1. GraphQL Kodunu Ayırmak

Yeniden kullanılabilir GraphQL bileşenlerini, paylaşılan bir modüle çıkarın:

```
trustgraph-flow/trustgraph/query/graphql/
├── __init__.py
├── types.py        # Filter types (IntFilter, StringFilter, FloatFilter)
├── schema.py       # Dynamic schema generation from RowSchema
└── filters.py      # Filter parsing utilities
```

Bu, şunları sağlar:
Farklı satır depolama arka uçlarında yeniden kullanılabilirlik
Daha temiz bir sorumluluk ayrımı
GraphQL mantığının bağımsız olarak daha kolay test edilebilmesi

#### 2. Yeni Tablo Şemasını Uygulayın

Cassandra'ya özgü kodu, birleşik tabloyu kullanacak şekilde yeniden düzenleyin:

**Yazıcı** (`trustgraph-flow/trustgraph/storage/rows/cassandra/`):
Her şema için ayrı tablolar yerine tek bir `rows` tablosu
Her satır için N kopyası yazın (her indeks için bir tane)
`row_partitions` tablosuna kaydolun
Daha basit tablo oluşturma (tek seferlik kurulum)

**Sorgu Hizmeti** (`trustgraph-flow/trustgraph/query/rows/cassandra/`):
Birleşik `rows` tablosunu sorgulayın
Şema oluşturma için çıkarılan GraphQL modülünü kullanın
Basitleştirilmiş filtre işleme (yalnızca veritabanı düzeyinde tam eşleşme)

### Modül Yeniden Adlandırmaları

"nesne" → "satır" adlandırma temizliği kapsamında:

| Mevcut | Yeni |
|---------|-----|
| `storage/objects/cassandra/` | `storage/rows/cassandra/` |
| `query/objects/cassandra/` | `query/rows/cassandra/` |
| `embeddings/object_embeddings/` | `embeddings/row_embeddings/` |

### Yeni Modüller

| Modül | Amaç |
|--------|---------|
| `trustgraph-flow/trustgraph/query/graphql/` | Paylaşılan GraphQL yardımcı programları |
| `trustgraph-flow/trustgraph/query/row_embeddings/qdrant/` | Satır gömme sorgu API'si |
| `trustgraph-flow/trustgraph/embeddings/row_embeddings/` | Satır gömme hesaplama (1. Aşama) |
| `trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/` | Satır gömme depolama (2. Aşama) |

## Referanslar

[Yapılandırılmış Veri Teknik Özellikleri](structured-data.md)
