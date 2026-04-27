---
layout: default
title: "Teknik Özellikler: Çok Kiracılı Destek"
parent: "Turkish (Beta)"
---

# Teknik Özellikler: Çok Kiracılı Destek

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Genel Bakış

Kuyumuzu özelleştirmeyi engelleyen parametre adı eşleşmezliklerini düzelterek ve Cassandra anahtar alanı parametrelemesini ekleyerek çok kiracılı dağıtımları etkinleştirin.

## Mimari Bağlam

### Akış Tabanlı Kuyruk Çözümlemesi

TrustGraph sistemi, dinamik kuyruk çözümlemesi için **akış tabanlı bir mimari** kullanır ve bu, doğal olarak çok kiracılığı destekler:

**Akış Tanımları**, Cassandra'da saklanır ve arayüz tanımları aracılığıyla kuyruk adlarını belirtir.
**Kuyruk adları**, akış örneği kimlikleriyle değiştirilen `{id}` değişkenlerine sahip **şablonlar** kullanır.
**Hizmetler**, istek zamanında akış yapılandırmalarını arayarak **kuyrukları dinamik olarak çözümler**.
**Her kiracı, farklı kuyruk adlarına sahip benzersiz akışlara sahip olabilir**, bu da izolasyon sağlar.

Örnek akış arayüz tanımı:
```json
{
  "interfaces": {
    "triples-store": "persistent://tg/flow/triples-store:{id}",
    "graph-embeddings-store": "persistent://tg/flow/graph-embeddings-store:{id}"
  }
}
```

Kiracı A, `tenant-a-prod` akışını başlatığında ve kiracı B, `tenant-b-prod` akışını başlattığında, otomatik olarak izole edilmiş kuyruklar elde ederler:
`persistent://tg/flow/triples-store:tenant-a-prod`
`persistent://tg/flow/triples-store:tenant-b-prod`

**Çoklu kiracılığa doğru şekilde tasarlanmış hizmetler:**
✅ **Bilgi Yönetimi (çekirdekler)** - İsteğe eklenen akış yapılandırmasından kuyrukları dinamik olarak çözer.

**Düzeltilmesi gereken hizmetler:**
🔴 **Yapılandırma Hizmeti** - Parametre adı eşleşmezliği, kuyruk özelleştirmesini engeller.
🔴 **Kütüphaneci Hizmeti** - Sabit kodlanmış depolama yönetimi konuları (aşağıda açıklanmıştır).
🔴 **Tüm Hizmetler** - Cassandra anahtar alanını özelleştiremezsiniz.

## Sorun Tanımı

### Sorun #1: AsyncProcessor'daki Parametre Adı Eşleşmezliği
**CLI tanımları:** `--config-queue` (belirsiz adlandırma)
**Argparse'ın dönüştürdüğü:** `config_queue` (params sözlüğünde)
**Kodun aradığı:** `config_push_queue`
**Sonuç:** Parametre göz ardı edilir ve varsayılan olarak `persistent://tg/config/config` olur.
**Etkisi:** AsyncProcessor'dan türeyen 32'den fazla hizmeti etkiler.
**Engeller:** Çoklu kiracılı dağıtımlar, kiracıya özel yapılandırma kuyruklarını kullanamaz.
**Çözüm:** CLI parametresinin adını `--config-push-queue` olarak değiştirerek netliği artırın (özellik şu anda bozuk olduğundan, bozucu değişiklik kabul edilebilir).

### Sorun #2: Yapılandırma Hizmetindeki Parametre Adı Eşleşmezliği
**CLI tanımları:** `--push-queue` (belirsiz adlandırma)
**Argparse'ın dönüştürdüğü:** `push_queue` (params sözlüğünde)
**Kodun aradığı:** `config_push_queue`
**Sonuç:** Parametre göz ardı edilir.
**Etkisi:** Yapılandırma hizmeti, özel bir push kuyruğunu kullanamaz.
**Çözüm:** CLI parametresinin adını `--config-push-queue` olarak değiştirerek tutarlılığı ve netliği artırın (bozucu değişiklik kabul edilebilir).

### Sorun #3: Sabit Kodlanmış Cassandra Anahtar Alanı
**Mevcut durum:** Anahtar alanı, çeşitli hizmetlerde `"config"`, `"knowledge"`, `"librarian"` olarak sabit kodlanmıştır.
**Sonuç:** Çoklu kiracılı dağıtımlar için anahtar alanı özelleştirilemez.
**Etkisi:** Yapılandırma, çekirdek ve kütüphaneci hizmetleri.
**Engeller:** Birden fazla kiracı, ayrı Cassandra anahtar alanlarını kullanamaz.

### Sorun #4: Koleksiyon Yönetimi Mimarisi ✅ TAMAMLANDI
**Önceki durum:** Koleksiyonlar, ayrı koleksiyon tablosu aracılığıyla Cassandra kütüphaneci anahtar alanında depolanıyordu.
**Önceki durum:** Kütüphaneci, koleksiyon oluşturma/silme işlemini koordine etmek için 4 sabit kodlanmış depolama yönetimi konusunu kullanıyordu:
  `vector_storage_management_topic`
  `object_storage_management_topic`
  `triples_storage_management_topic`
  `storage_management_response_topic`
**Sorunlar (Çözüldü):**
  Sabit kodlanmış konular, çoklu kiracılı dağıtımlar için özelleştirilemezdi.
  Kütüphaneci ile 4+ depolama hizmeti arasında karmaşık asenkron koordinasyon.
  Ayrı bir Cassandra tablosu ve yönetim altyapısı.
  Kritik işlemler için kalıcı olmayan istek/yanıt kuyrukları.
**Uygulanan Çözüm:** Koleksiyonları yapılandırma hizmeti depolamasına taşıdık, dağıtım için yapılandırma push'u kullandık.
**Durum:** Tüm depolama arka uçları `CollectionConfigHandler` modeline taşınmıştır.

## Çözüm

Bu özellik, Sorunlar #1, #2, #3 ve #4'ü ele alır.

### 1. Bölüm: Parametre Adı Eşleşmezliklerini Düzeltme

#### Değişiklik 1: AsyncProcessor Temel Sınıfı - CLI Parametresinin Adını Değiştirme
**Dosya:** `trustgraph-base/trustgraph/base/async_processor.py`
**Satır:** 260-264

**Mevcut:**
```python
parser.add_argument(
    '--config-queue',
    default=default_config_queue,
    help=f'Config push queue {default_config_queue}',
)
```

**Sabit:**
```python
parser.add_argument(
    '--config-push-queue',
    default=default_config_queue,
    help=f'Config push queue (default: {default_config_queue})',
)
```

**Gerekçe:**
Daha açık, daha kesin bir adlandırma
İç değişken adıyla eşleşiyor: `config_push_queue`
Özellik şu anda çalışmadığı için, bu bir değişikliktir ve kabul edilebilir.
params.get() içinde herhangi bir kod değişikliğine gerek yok; zaten doğru adı arıyor.

#### Değişiklik 2: Konfigürasyon Servisi - CLI Parametresinin Yeniden Adlandırılması
**Dosya:** `trustgraph-flow/trustgraph/config/service/service.py`
**Satır:** 276-279

**Mevcut:**
```python
parser.add_argument(
    '--push-queue',
    default=default_config_push_queue,
    help=f'Config push queue (default: {default_config_push_queue})'
)
```

**Sabit:**
```python
parser.add_argument(
    '--config-push-queue',
    default=default_config_push_queue,
    help=f'Config push queue (default: {default_config_push_queue})'
)
```

**Gerekçe:**
Daha anlaşılır bir adlandırma - "config-push-queue", sadece "push-queue"den daha açık.
İç değişken adıyla eşleşiyor: `config_push_queue`
AsyncProcessor'ın `--config-push-queue` parametresiyle tutarlı.
Özellik şu anda çalışmadığı için değişiklik kabul edilebilir.
params.get() içinde herhangi bir kod değişikliğine gerek yok - zaten doğru adı arıyor.

### 2. Bölüm: Cassandra Keyspace Parametrelendirmesi

#### 3. Değişiklik: cassandra_config Modülüne Keyspace Parametresi Ekle
**Dosya:** `trustgraph-base/trustgraph/base/cassandra_config.py`

**CLI argümanı ekle** (`add_cassandra_args()` fonksiyonunda):
```python
parser.add_argument(
    '--cassandra-keyspace',
    default=None,
    help='Cassandra keyspace (default: service-specific)'
)
```

**Ortam değişkeni desteği ekleyin** (`resolve_cassandra_config()` fonksiyonunda):
```python
keyspace = params.get(
    "cassandra_keyspace",
    os.environ.get("CASSANDRA_KEYSPACE")
)
```

**`resolve_cassandra_config()`'nin dönüş değerini güncelleyin:**
Şu anda döndürüyor: `(hosts, username, password)`
Aşağıdaki değeri döndürmesi için değiştirin: `(hosts, username, password, keyspace)`

**Gerekçe:**
Mevcut Cassandra yapılandırma kalıbıyla tutarlı
`add_cassandra_args()` aracılığıyla tüm hizmetlere erişilebilir
Hem CLI hem de ortam değişkeni yapılandırmasını destekler

#### Değişiklik 4: Yapılandırma Hizmeti - Parametreli Keyspace Kullanımı
**Dosya:** `trustgraph-flow/trustgraph/config/service/service.py`

**30. Satır** - Sabit kodlanmış keyspace'i kaldırın:
```python
# DELETE THIS LINE:
keyspace = "config"
```

**69-73 satırları** - Cassandra yapılandırma çözümlemesi güncellendi:

**Mevcut:**
```python
cassandra_host, cassandra_username, cassandra_password = \
    resolve_cassandra_config(params)
```

**Sabit:**
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="config")
```

**Gerekçe:**
"config" varsayılan olarak kullanılarak geriye dönük uyumluluk sağlanır.
`--cassandra-keyspace` veya `CASSANDRA_KEYSPACE` ile geçersiz kılınabilir.

#### Değişiklik 5: Cores/Bilgi Hizmeti - Parametreleştirilmiş Anahtar Alanı Kullanımı
**Dosya:** `trustgraph-flow/trustgraph/cores/service.py`

**Satır 37** - Sabit kodlanmış anahtar alanını kaldırın:
```python
# DELETE THIS LINE:
keyspace = "knowledge"
```

**Cassandra yapılandırma çözümlemesi güncellendi** (yapılandırma hizmetiyle benzer konumda):
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="knowledge")
```

#### Değişiklik 6: Kütüphaneci Hizmeti - Parametreleştirilmiş Anahtar Alanı Kullanımı
**Dosya:** `trustgraph-flow/trustgraph/librarian/service.py`

**Satır 51** - Sabit kodlanmış anahtar alanını kaldır:
```python
# DELETE THIS LINE:
keyspace = "librarian"
```

**Cassandra yapılandırma çözümlemesi güncellendi** (yapılandırma hizmetiyle benzer konumda):
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="librarian")
```

### 3. Bölüm: Koleksiyon Yönetimini Config Servisine Taşıma

#### Genel Bakış
Koleksiyonları Cassandra librarian anahtar alanından config servisi depolama alanına taşıyın. Bu, sabit kodlanmış depolama yönetimi konularını ortadan kaldırır ve dağıtım için mevcut config push mekanizmasını kullanarak mimariyi basitleştirir.

#### Mevcut Mimari
```
API Request → Gateway → Librarian Service
                            ↓
                    CollectionManager
                            ↓
                    Cassandra Collections Table (librarian keyspace)
                            ↓
                    Broadcast to 4 Storage Management Topics (hardcoded)
                            ↓
        Wait for 4+ Storage Service Responses
                            ↓
                    Response to Gateway
```

#### Yeni Mimari
```
API Request → Gateway → Librarian Service
                            ↓
                    CollectionManager
                            ↓
                    Config Service API (put/delete/getvalues)
                            ↓
                    Cassandra Config Table (class='collections', key='user:collection')
                            ↓
                    Config Push (to all subscribers on config-push-queue)
                            ↓
        All Storage Services receive config update independently
```

#### Değişiklik 7: Koleksiyon Yöneticisi - Config Hizmeti API'sini Kullanın
**Dosya:** `trustgraph-flow/trustgraph/librarian/collection_manager.py`

**Kaldırılacaklar:**
`LibraryTableStore` kullanımı (33, 40-41 satırları)
Depolama yönetimi üreticilerinin başlatılması (86-140 satırları)
`on_storage_response` metodu (400-430 satırları)
`pending_deletions` takibi (57, 90-96 satırları ve tüm kullanım alanları)

**Eklenecekler:**
API çağrıları için Config hizmeti istemcisi (istek/yanıt kalıbı)

**Config İstemcisi Kurulumu:**
```python
# In __init__, add config request/response producers/consumers
from trustgraph.schema.services.config import ConfigRequest, ConfigResponse

# Producer for config requests
self.config_request_producer = Producer(
    client=pulsar_client,
    topic=config_request_queue,
    schema=ConfigRequest,
)

# Consumer for config responses (with correlation ID)
self.config_response_consumer = Consumer(
    taskgroup=taskgroup,
    client=pulsar_client,
    flow=None,
    topic=config_response_queue,
    subscriber=f"{id}-config",
    schema=ConfigResponse,
    handler=self.on_config_response,
)

# Tracking for pending config requests
self.pending_config_requests = {}  # request_id -> asyncio.Event
```

**`list_collections`'ı Değiştirin (145-180. satırlar):**
```python
async def list_collections(self, user, tag_filter=None, limit=None):
    """List collections from config service"""
    # Send getvalues request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='getvalues',
        type='collections',
    )

    # Send request and wait for response
    response = await self.send_config_request(request)

    # Parse collections from response
    collections = []
    for key, value_json in response.values.items():
        if ":" in key:
            coll_user, collection = key.split(":", 1)
            if coll_user == user:
                metadata = json.loads(value_json)
                collections.append(CollectionMetadata(**metadata))

    # Apply tag filtering in-memory (as before)
    if tag_filter:
        collections = [c for c in collections if any(tag in c.tags for tag in tag_filter)]

    # Apply limit
    if limit:
        collections = collections[:limit]

    return collections

async def send_config_request(self, request):
    """Send config request and wait for response"""
    event = asyncio.Event()
    self.pending_config_requests[request.id] = event

    await self.config_request_producer.send(request)
    await event.wait()

    return self.pending_config_requests.pop(request.id + "_response")

async def on_config_response(self, message, consumer, flow):
    """Handle config response"""
    response = message.value()
    if response.id in self.pending_config_requests:
        self.pending_config_requests[response.id + "_response"] = response
        self.pending_config_requests[response.id].set()
```

**`update_collection`'yi değiştirin (182-312. satırlar):**
```python
async def update_collection(self, user, collection, name, description, tags):
    """Update collection via config service"""
    # Create metadata
    metadata = CollectionMetadata(
        user=user,
        collection=collection,
        name=name,
        description=description,
        tags=tags,
    )

    # Send put request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='put',
        type='collections',
        key=f'{user}:{collection}',
        value=json.dumps(metadata.to_dict()),
    )

    response = await self.send_config_request(request)

    if response.error:
        raise RuntimeError(f"Config update failed: {response.error.message}")

    # Config service will trigger config push automatically
    # Storage services will receive update and create collections
```

**`delete_collection`'ı Değiştirin (314-398. satırlar):**
```python
async def delete_collection(self, user, collection):
    """Delete collection via config service"""
    # Send delete request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='delete',
        type='collections',
        key=f'{user}:{collection}',
    )

    response = await self.send_config_request(request)

    if response.error:
        raise RuntimeError(f"Config delete failed: {response.error.message}")

    # Config service will trigger config push automatically
    # Storage services will receive update and delete collections
```

**Koleksiyon Meta Veri Formatı:**
`config` tablosunda şu şekilde saklanır: `class='collections', key='user:collection'`
Değer, zaman damgası alanları olmadan JSON olarak seri hale getirilmiş `CollectionMetadata`'dır.
Alanlar: `user`, `collection`, `name`, `description`, `tags`
Örnek: `class='collections', key='alice:my-docs', value='{"user":"alice","collection":"my-docs","name":"My Documents","description":"...","tags":["work"]}'`

#### 8. Değişiklik: Kütüphane Hizmeti - Depolama Yönetimi Altyapısını Kaldır
**Dosya:** `trustgraph-flow/trustgraph/librarian/service.py`

**Kaldır:**
Depolama yönetimi üreticileri (173-190. satırlar):
  `vector_storage_management_producer`
  `object_storage_management_producer`
  `triples_storage_management_producer`
Depolama yanıt tüketici (192-201. satırlar)
`on_storage_response` işleyici (467-473. satırlar)

**Değiştir:**
`CollectionManager` başlatma (215-224. satırlar) - depolama üretici parametrelerini kaldır

**Not:** Harici koleksiyon API'si değişmeden kalır:
`list-collections`
`update-collection`
`delete-collection`

#### 9. Değişiklik: Koleksiyonlar Tablosunu `LibraryTableStore`'dan Kaldır
**Dosya:** `trustgraph-flow/trustgraph/tables/library.py`

**Sil:**
Koleksiyonlar tablosu `CREATE` ifadesi (114-127. satırlar)
Koleksiyonlar için hazırlanmış ifadeler (205-240. satırlar)
Tüm koleksiyon metotları (578-717. satırlar):
  `ensure_collection_exists`
  `list_collections`
  `update_collection`
  `delete_collection`
  `get_collection`
  `create_collection`

**Gerekçe:**
Koleksiyonlar artık `config` tablosunda saklanıyor
Uyumluluk bozan bir değişiklik kabul edilebilir - veri taşıma işlemine gerek yok
Kütüphane hizmetini önemli ölçüde basitleştirir

#### 10. Değişiklik: Depolama Hizmetleri - Yapılandırmaya Dayalı Koleksiyon Yönetimi ✅ TAMAMLANDI

**Durum:** 11 depolama arka ucunun tamamı, `CollectionConfigHandler`'ı kullanmak üzere güncellendi.

**Etkilenen Hizmetler (toplam 11):**
Belge gömülüleri: milvus, pinecone, qdrant
Grafik gömülüleri: milvus, pinecone, qdrant
Nesne depolama: cassandra
Üçlü depolama: cassandra, falkordb, memgraph, neo4j

**Dosyalar:**
`trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/pinecone/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/triples/falkordb/write.py`
`trustgraph-flow/trustgraph/storage/triples/memgraph/write.py`
`trustgraph-flow/trustgraph/storage/triples/neo4j/write.py`

**Uygulama Deseni (tüm hizmetler):**

1. **Yapılandırma işleyiciyi `__init__` içinde kaydedin:**
```python
# Add after AsyncProcessor initialization
self.register_config_handler(self.on_collection_config)
self.known_collections = set()  # Track (user, collection) tuples
```

2. **Yapılandırma yöneticisini uygulayın:**
```python
async def on_collection_config(self, config, version):
    """Handle collection configuration updates"""
    logger.info(f"Collection config version: {version}")

    if "collections" not in config:
        return

    # Parse collections from config
    # Key format: "user:collection" in config["collections"]
    config_collections = set()
    for key in config["collections"].keys():
        if ":" in key:
            user, collection = key.split(":", 1)
            config_collections.add((user, collection))

    # Determine changes
    to_create = config_collections - self.known_collections
    to_delete = self.known_collections - config_collections

    # Create new collections (idempotent)
    for user, collection in to_create:
        try:
            await self.create_collection_internal(user, collection)
            self.known_collections.add((user, collection))
            logger.info(f"Created collection: {user}/{collection}")
        except Exception as e:
            logger.error(f"Failed to create {user}/{collection}: {e}")

    # Delete removed collections (idempotent)
    for user, collection in to_delete:
        try:
            await self.delete_collection_internal(user, collection)
            self.known_collections.discard((user, collection))
            logger.info(f"Deleted collection: {user}/{collection}")
        except Exception as e:
            logger.error(f"Failed to delete {user}/{collection}: {e}")
```

3. **Başlangıçta bilinen koleksiyonları başlatın:**
```python
async def start(self):
    """Start the processor"""
    await super().start()
    await self.sync_known_collections()

async def sync_known_collections(self):
    """Query backend to populate known_collections set"""
    # Backend-specific implementation:
    # - Milvus/Pinecone/Qdrant: List collections/indexes matching naming pattern
    # - Cassandra: Query keyspaces or collection metadata
    # - Neo4j/Memgraph/FalkorDB: Query CollectionMetadata nodes
    pass
```

4. **Mevcut işleyici metotları yeniden düzenleyin:**
```python
# Rename and remove response sending:
# handle_create_collection → create_collection_internal
# handle_delete_collection → delete_collection_internal

async def create_collection_internal(self, user, collection):
    """Create collection (idempotent)"""
    # Same logic as current handle_create_collection
    # But remove response producer calls
    # Handle "already exists" gracefully
    pass

async def delete_collection_internal(self, user, collection):
    """Delete collection (idempotent)"""
    # Same logic as current handle_delete_collection
    # But remove response producer calls
    # Handle "not found" gracefully
    pass
```

5. **Depolama yönetimi altyapısını kaldırın:**
   `self.storage_request_consumer` kurulumunu ve başlatmayı kaldırın
   `self.storage_response_producer` kurulumunu kaldırın
   `on_storage_management` dağıtıcı yöntemini kaldırın
   Depolama yönetimi için metrikleri kaldırın
   Aşağıdaki import'ları kaldırın: `StorageManagementRequest`, `StorageManagementResponse`

**Arka Uç Özel Hususlar:**

**Vektör depoları (Milvus, Pinecone, Qdrant):** `known_collections` içinde mantıksal `(user, collection)`'ı takip edin, ancak her boyut için birden fazla arka uç koleksiyonu oluşturabilir. Tembel oluşturma modeline devam edin. Silme işlemleri, tüm boyut varyantlarını kaldırmalıdır.

**Cassandra Nesneleri:** Koleksiyonlar, yapılar değil, satır özellikleridir. Veritabanı seviyesindeki bilgileri takip edin.

**Grafik depoları (Neo4j, Memgraph, FalkorDB):** Başlangıçta `CollectionMetadata` düğümlerini sorgulayın. Senkronizasyon sırasında meta veri düğümlerini oluşturun/silin.

**Cassandra Üçlüleri:** Koleksiyon işlemleri için `KnowledgeGraph` API'sini kullanın.

**Temel Tasarım Noktaları:**

**Son tutarlılık:** İstek/yanıt mekanizması yoktur, yapılandırma itmesi yayınlanır
**Tekrarlanabilirlik:** Tüm oluşturma/silme işlemleri, yeniden denenmek üzere güvenli olmalıdır
**Hata işleme:** Hataları günlüğe kaydedin, ancak yapılandırma güncellemelerini engellemeyin
**Kendini iyileştirme:** Başarısız işlemler, bir sonraki yapılandırma itmesinde yeniden denenecektir
**Koleksiyon anahtar biçimi:** `config["collections"]` içinde `"user:collection"`

#### Değişiklik 11: Koleksiyon Şemasını Güncelle - Zaman Damgalarını Kaldır
**Dosya:** `trustgraph-base/trustgraph/schema/services/collection.py`

**CollectionMetadata'ı değiştirin (Satırlar 13-21):**
Aşağıdaki alanları kaldırın: `created_at` ve `updated_at`:
```python
class CollectionMetadata(Record):
    user = String()
    collection = String()
    name = String()
    description = String()
    tags = Array(String())
    # Remove: created_at = String()
    # Remove: updated_at = String()
```

**CollectionManagementRequest'i Değiştir (25-47. satırlar):**
Zaman damgası alanlarını kaldır:
```python
class CollectionManagementRequest(Record):
    operation = String()
    user = String()
    collection = String()
    timestamp = String()
    name = String()
    description = String()
    tags = Array(String())
    # Remove: created_at = String()
    # Remove: updated_at = String()
    tag_filter = Array(String())
    limit = Integer()
```

**Gerekçe:**
Zaman damgaları, koleksiyonlar için değer katmaz.
Yapılandırma hizmeti, kendi sürüm takibini yapar.
Şemayı basitleştirir ve depolama alanını azaltır.

#### Yapılandırma Hizmeti Geçişinin Faydaları

1. ✅ **Sabit kodlanmış depolama yönetimi konularını ortadan kaldırır** - Çok kiracılı sorunu çözer.
2. ✅ **Daha basit koordinasyon** - 4 veya daha fazla depolama yanıtı için karmaşık asenkron beklemeler olmaz.
3. ✅ **Sonunda tutarlılık** - Depolama hizmetleri, yapılandırma itme yoluyla bağımsız olarak güncellenir.
4. ✅ **Daha iyi güvenilirlik** - Kalıcı yapılandırma itme, kalıcı olmayan istek/yanıt yerine.
5. ✅ **Birleşik yapılandırma modeli** - Koleksiyonlar, yapılandırma olarak ele alınır.
6. ✅ **Karmaşıklığı azaltır** - Yaklaşık 300 satır koordinasyon kodunu kaldırır.
7. ✅ **Çok kiracılı için hazır** - Yapılandırma, anahtar alanı aracılığıyla zaten kiracı izolasyonunu destekler.
8. ✅ **Sürüm takibi** - Yapılandırma hizmeti sürüm mekanizması, denetim izi sağlar.

## Uygulama Notları

### Geriye Dönük Uyumluluk

**Parametre Değişiklikleri:**
CLI parametrelerinin yeniden adlandırılması, bozucu değişikliklerdir ancak kabul edilebilir (özellik şu anda çalışmıyor).
Hizmetler parametreler olmadan çalışır (varsayılanları kullanır).
Varsayılan anahtar alanları korunur: "config", "knowledge", "librarian".
Varsayılan kuyruk: `persistent://tg/config/config`

**Koleksiyon Yönetimi:**
**Bozucu değişiklik:** Koleksiyon tablosu, "librarian" anahtar alanından kaldırılmıştır.
**Veri geçişi sağlanmamıştır** - bu aşama için kabul edilebilir.
Harici koleksiyon API'si değişmemiştir (listeleme/güncelleme/silme işlemleri).
Koleksiyon meta veri biçimi basitleştirilmiştir (zaman damgaları kaldırılmıştır).

### Test Gereksinimleri

**Parametre Testi:**
1. `--config-push-queue` parametresinin "graph-embeddings" hizmetinde çalıştığını doğrulayın.
2. `--config-push-queue` parametresinin "text-completion" hizmetinde çalıştığını doğrulayın.
3. `--config-push-queue` parametresinin yapılandırma hizmetinde çalıştığını doğrulayın.
4. `--cassandra-keyspace` parametresinin yapılandırma hizmeti için çalıştığını doğrulayın.
5. `--cassandra-keyspace` parametresinin "cores" hizmeti için çalıştığını doğrulayın.
6. `--cassandra-keyspace` parametresinin "librarian" hizmeti için çalıştığını doğrulayın.
7. Hizmetlerin parametreler olmadan çalıştığını (varsayılanları kullandığını) doğrulayın.
8. Özel kuyruk adları ve anahtar alanı ile çok kiracılı dağıtımı doğrulayın.

**Koleksiyon Yönetimi Testi:**
9. `list-collections` işlemini yapılandırma hizmeti aracılığıyla doğrulayın.
10. `update-collection`'ın yapılandırma tablosunda oluşturulduğunu/güncellendiğini doğrulayın.
11. `delete-collection`'ın yapılandırma tablosundan kaldırıldığını doğrulayın.
12. Koleksiyon güncellemelerinde yapılandırma itmesinin tetiklendiğini doğrulayın.
13. Etiket filtrelemenin yapılandırma tabanlı depolama ile çalıştığını doğrulayın.
14. Koleksiyon işlemlerinin zaman damgası alanları olmadan çalıştığını doğrulayın.

### Çok Kiracılı Dağıtım Örneği
```bash
# Tenant: tg-dev
graph-embeddings \
  -p pulsar+ssl://broker:6651 \
  --pulsar-api-key <KEY> \
  --config-push-queue persistent://tg-dev/config/config

config-service \
  -p pulsar+ssl://broker:6651 \
  --pulsar-api-key <KEY> \
  --config-push-queue persistent://tg-dev/config/config \
  --cassandra-keyspace tg_dev_config
```

## Etki Analizi

### 1-2 Değişikliklerinden Etkilenen Hizmetler (CLI Parametre Adı Değişikliği)
AsyncProcessor veya FlowProcessor'dan türeyen tüm hizmetler:
config-service
cores-service
librarian-service
graph-embeddings
document-embeddings
text-completion-* (tüm sağlayıcılar)
extract-* (tüm çıkarıcılar)
query-* (tüm sorgu hizmetleri)
retrieval-* (tüm RAG hizmetleri)
storage-* (tüm depolama hizmetleri)
Ve 20'den fazla hizmet daha

### 3-6 Değişikliklerinden Etkilenen Hizmetler (Cassandra Keyspace)
config-service
cores-service
librarian-service

### 7-11 Değişikliklerinden Etkilenen Hizmetler (Koleksiyon Yönetimi)

**Hızlı Uygulanacak Değişiklikler:**
librarian-service (collection_manager.py, service.py)
tables/library.py (collections tablosunun kaldırılması)
schema/services/collection.py (zaman damgası kaldırma)

**Tamamlanan Değişiklikler (Değişiklik 10):** ✅
Tüm depolama hizmetleri (toplam 11) - `CollectionConfigHandler` üzerinden koleksiyon güncellemeleri için yapılandırma itme işlemine geçirildi
Depolama yönetimi şeması `storage.py`'dan kaldırıldı

## Gelecek Hususlar

### Kullanıcı Başına Keyspace Modeli

Bazı hizmetler, her kullanıcının kendi Cassandra keyspace'ine sahip olduğu **kullanıcı başına keyspace**'leri dinamik olarak kullanır:

**Kullanıcı başına keyspace kullanan hizmetler:**
1. **Triples Sorgu Hizmeti** (`trustgraph-flow/trustgraph/query/triples/cassandra/service.py:65`)
   `keyspace=query.user` kullanır
2. **Objects Sorgu Hizmeti** (`trustgraph-flow/trustgraph/query/objects/cassandra/service.py:479`)
   `keyspace=self.sanitize_name(user)` kullanır
3. **KnowledgeGraph Doğrudan Erişim** (`trustgraph-flow/trustgraph/direct/cassandra_kg.py:18`)
   Varsayılan parametre `keyspace="trustgraph"`

**Durum:** Bu, bu belirtimde **değiştirilmemiştir**.

**Gelecekte İnceleme Gerekli:**
Kullanıcı başına keyspace modelinin kiracı izolasyonu sorunlarına neden olup olmadığını değerlendirin
Çok kiracılı dağıtımların keyspace önek kalıplarına (örneğin, `tenant_a_user1`) ihtiyaç duyup duymadığını düşünün
Kiracılar arasında potansiyel kullanıcı kimliği çakışmalarını gözden geçirin
Tek, paylaşılan keyspace'in, kullanıcı tabanlı satır izolasyonu ile birlikte daha mı tercih edilebilir olduğunu değerlendirin

**Not:** Bu, mevcut çok kiracılı uygulamayı engellemez, ancak üretim çok kiracılı dağıtımlardan önce incelenmelidir.

## Uygulama Aşamaları

### Aşama 1: Parametre Düzeltmeleri (Değişiklikler 1-6)
`--config-push-queue` parametre adlandırmasını düzeltin
`--cassandra-keyspace` parametre desteğini ekleyin
**Sonuç:** Çok kiracılı kuyruk ve keyspace yapılandırması etkinleştirildi

### Aşama 2: Koleksiyon Yönetimi Geçişi (Değişiklikler 7-9, 11)
Koleksiyon depolamasını yapılandırma hizmetine geçirin
librarian'dan koleksiyon tablosunu kaldırın
Koleksiyon şemasını güncelleyin (zaman damgalarını kaldırın)
**Sonuç:** Sabit kodlu depolama yönetimi konuları ortadan kaldırılır, librarian basitleştirilir

### Aşama 3: Depolama Hizmeti Güncellemeleri (Değişiklik 10) ✅ TAMAMLANDI
Tüm depolama hizmetlerini koleksiyonlar için yapılandırma itme işlemine almak için güncelleyin `CollectionConfigHandler`
Depolama yönetimi istek/yanıt altyapısını kaldırın
Eski şema tanımlarını kaldırın
**Sonuç:** Tamamen yapılandırmaya dayalı koleksiyon yönetimi elde edildi

## Referanslar
GitHub Sorunu: https://github.com/trustgraph-ai/trustgraph/issues/582
İlgili Dosyalar:
  `trustgraph-base/trustgraph/base/async_processor.py`
  `trustgraph-base/trustgraph/base/cassandra_config.py`
  `trustgraph-base/trustgraph/schema/core/topic.py`
  `trustgraph-base/trustgraph/schema/services/collection.py`
  `trustgraph-flow/trustgraph/config/service/service.py`
  `trustgraph-flow/trustgraph/cores/service.py`
  `trustgraph-flow/trustgraph/librarian/service.py`
  `trustgraph-flow/trustgraph/librarian/collection_manager.py`
  `trustgraph-flow/trustgraph/tables/library.py`
