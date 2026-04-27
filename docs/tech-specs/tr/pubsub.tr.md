---
layout: default
title: "Pub/Sub Altyapısı"
parent: "Turkish (Beta)"
---

# Pub/Sub Altyapısı

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Genel Bakış

Bu belge, TrustGraph kod tabanı ile pub/sub altyapısı arasındaki tüm bağlantıları listeler. Şu anda sistem, Apache Pulsar'ı kullanmak üzere sabit kodlanmıştır. Bu analiz, yapılandırılabilir bir pub/sub soyutlamasına yönelik gelecekteki yeniden düzenlemeleri bilgilendirmek için tüm entegrasyon noktalarını belirler.

## Mevcut Durum: Pulsar Entegrasyon Noktaları

### 1. Doğrudan Pulsar İstemci Kullanımı

**Konum:** `trustgraph-flow/trustgraph/gateway/service.py`

API ağ geçidi, doğrudan Pulsar istemcisini içe aktarır ve örnekler:

**Satır 20:** `import pulsar`
**Satırlar 54-61:** `pulsar.Client()`'ın doğrudan örneklenmesi, isteğe bağlı `pulsar.AuthenticationToken()` ile birlikte
**Satırlar 33-35:** Ortam değişkenlerinden varsayılan Pulsar ana bilgisayarı yapılandırması
**Satırlar 178-192:** `--pulsar-host`, `--pulsar-api-key` ve `--pulsar-listener` için CLI argümanları
**Satırlar 78, 124:** `pulsar_client`'ı `ConfigReceiver` ve `DispatcherManager`'ye geçirir

Bu, bir soyutlama katmanı dışında bir Pulsar istemcisinin doğrudan örneklenmesini yapan tek konumdur.

### 2. Temel İşlemci Çerçevesi

**Konum:** `trustgraph-base/trustgraph/base/async_processor.py`

Tüm işlemciler için temel sınıf, Pulsar bağlantısı sağlar:

**Satır 9:** `import _pulsar` (istisna işleme için)
**Satır 18:** `from . pubsub import PulsarClient`
**Satır 38:** `pulsar_client_object = PulsarClient(**params)` oluşturur
**Satırlar 104-108:** `pulsar_host` ve `pulsar_client`'i ortaya koyan özellikler
**Satır 250:** Statik yöntem `add_args()`, CLI argümanları için `PulsarClient.add_args(parser)`'i çağırır
**Satırlar 223-225:** `_pulsar.Interrupted` için istisna işleme

Tüm işlemciler `AsyncProcessor`'dan türetildiği için, bu merkezi bir entegrasyon noktasıdır.

### 3. Tüketici Soyutlaması

**Konum:** `trustgraph-base/trustgraph/base/consumer.py`

Kuyruklardan mesajlar tüketir ve işleyici fonksiyonlarını çağırır:

**Pulsar içe aktarmaları:**
**Satır 12:** `from pulsar.schema import JsonSchema`
**Satır 13:** `import pulsar`
**Satır 14:** `import _pulsar`

**Pulsar'a özgü kullanım:**
**Satırlar 100, 102:** `pulsar.InitialPosition.Earliest` / `pulsar.InitialPosition.Latest`
**Satır 108:** `JsonSchema(self.schema)` sarmalayıcısı
**Satır 110:** `pulsar.ConsumerType.Shared`
**Satırlar 104-111:** Pulsar'a özgü parametrelerle `self.client.subscribe()`
**Satırlar 143, 150, 65:** `consumer.unsubscribe()` ve `consumer.close()` yöntemleri
**Satır 162:** `_pulsar.Timeout` istisnası
**Satırlar 182, 205, 232:** `consumer.acknowledge()` / `consumer.negative_acknowledge()`

**Belge dosyası:** `trustgraph-base/trustgraph/base/consumer_spec.py`
**Satır 22:** `processor.pulsar_client`'a referans

### 4. Yayıncı Soyutlaması

**Konum:** `trustgraph-base/trustgraph/base/producer.py`

Kuyruklara mesaj gönderir:

**Pulsar içe aktarmaları:**
**Satır 2:** `from pulsar.schema import JsonSchema`

**Pulsar'a özgü kullanım:**
**Satır 49:** `JsonSchema(self.schema)` sarmalayıcısı
**Satırlar 47-51:** Pulsar'a özgü parametrelerle (konu, şema, chunking_enabled) `self.client.create_producer()`
**Satırlar 31, 76:** `producer.close()` yöntemi
**Satırlar 64-65:** Mesaj ve özelliklerle `producer.send()`

**Belge dosyası:** `trustgraph-base/trustgraph/base/producer_spec.py`
**Satır 18:** `processor.pulsar_client`'a referans

### 5. Yayıncı Soyutlaması

**Konum:** `trustgraph-base/trustgraph/base/publisher.py`

Kuyruklu tamponlama ile asenkron mesaj yayınlama:

**Pulsar içe aktarmaları:**
**Satır 2:** `from pulsar.schema import JsonSchema`
**Satır 6:** `import pulsar`

**Pulsar'a özgü kullanım:**
**Satır 52:** `JsonSchema(self.schema)` sarmalayıcısı
**Satırlar 50-54:** Pulsar'a özgü parametrelerle `self.client.create_producer()`
**Satırlar 101, 103:** Mesaj ve isteğe bağlı özelliklerle `producer.send()`
**Satırlar 106-107:** `producer.flush()` ve `producer.close()` yöntemleri

### 6. Abonelik Soyutlaması

**Konum:** `trustgraph-base/trustgraph/base/subscriber.py`

Kuyruklardan çoklu alıcıya mesaj dağıtımı sağlar:

**Pulsar importları:**
**6. Satır:** `from pulsar.schema import JsonSchema`
**8. Satır:** `import _pulsar`

**Pulsar'a özgü kullanım:**
**55. Satır:** `JsonSchema(self.schema)` wrapper
**57. Satır:** `self.client.subscribe(**subscribe_args)`
**101, 136, 160, 167-172. Satırlar:** Pulsar istisnaları: `_pulsar.Timeout`, `_pulsar.InvalidConfiguration`, `_pulsar.AlreadyClosed`
**159, 166, 170. Satırlar:** Tüketici metotları: `negative_acknowledge()`, `unsubscribe()`, `close()`
**247, 251. Satırlar:** Mesaj onayı: `acknowledge()`, `negative_acknowledge()`

**Spec dosyası:** `trustgraph-base/trustgraph/base/subscriber_spec.py`
**19. Satır:** `processor.pulsar_client`'a referans

### 7. Şema Sistemi (Heart of Darkness)

**Konum:** `trustgraph-base/trustgraph/schema/`

Sistemdeki her mesaj şeması, Pulsar'ın şema çerçevesi kullanılarak tanımlanır.

**Temel öğeler:** `schema/core/primitives.py`
**2. Satır:** `from pulsar.schema import Record, String, Boolean, Array, Integer`
Tüm şemalar, Pulsar'ın `Record` temel sınıfından türetilir.
Tüm alan türleri Pulsar türleridir: `String()`, `Integer()`, `Boolean()`, `Array()`, `Map()`, `Double()`

**Örnek şemalar:**
`schema/services/llm.py` (2. Satır): `from pulsar.schema import Record, String, Array, Double, Integer, Boolean`
`schema/services/config.py` (2. Satır): `from pulsar.schema import Record, Bytes, String, Boolean, Array, Map, Integer`

**Konu adlandırması:** `schema/core/topic.py`
**2-3. Satırlar:** Konu formatı: `{kind}://{tenant}/{namespace}/{topic}`
Bu URI yapısı Pulsar'a özgüdür (örneğin, `persistent://tg/flow/config`)

**Etki:**
Kod tabanındaki tüm istek/yanıt mesaj tanımları, Pulsar şemalarını kullanır.
Bu, aşağıdaki hizmetler için geçerlidir: yapılandırma, akış, LLM, istem, sorgu, depolama, aracı, koleksiyon, tanı, kütüphane, arama, NLP sorgusu, nesne sorgusu, alma, yapılandırılmış sorgu.
Şema tanımları, tüm işlemciler ve hizmetler genelinde kapsamlı bir şekilde içe aktarılır ve kullanılır.

## Özet

### Kategoriye Göre Pulsar Bağımlılıkları

1. **İstem oluşturma:**
   Doğrudan: `gateway/service.py`
   Soyutlanmış: `async_processor.py` → `pubsub.py` (PulsarClient)

2. **Mesaj taşıma:**
   Tüketici: `consumer.py`, `consumer_spec.py`
   Üretici: `producer.py`, `producer_spec.py`
   Yayıncı: `publisher.py`
   Abonelik: `subscriber.py`, `subscriber_spec.py`

3. **Şema sistemi:**
   Temel türler: `schema/core/primitives.py`
   Tüm hizmet şemaları: `schema/services/*.py`
   Konu adlandırması: `schema/core/topic.py`

4. **Gereken Pulsar'a özgü kavramlar:**
   Konuya dayalı mesajlaşma
   Şema sistemi (Kayıt, alan türleri)
   Paylaşımlı abonelikler
   Mesaj onayı (olumlu/olumsuz)
   Tüketici konumlandırması (en erken/en son)
   Mesaj özellikleri
   Başlangıç konumları ve tüketici türleri
   Parçalama desteği
   Kalıcı ve kalıcı olmayan konular

### Yeniden Düzenleme Zorlukları

İyi haber: Soyutlama katmanı (Tüketici, Üretici, Yayıncı, Abonelik), çoğu Pulsar etkileşimini temiz bir şekilde kapsar.

Zorluklar:
1. **Şema sisteminin yaygınlığı:** Her mesaj tanımı `pulsar.schema.Record` ve Pulsar alan türlerini kullanır.
2. **Pulsar'a özgü numaralandırmalar:** `InitialPosition`, `ConsumerType`
3. **Pulsar istisnaları:** `_pulsar.Timeout`, `_pulsar.Interrupted`, `_pulsar.InvalidConfiguration`, `_pulsar.AlreadyClosed`
4. **Metot imzaları:** `acknowledge()`, `negative_acknowledge()`, `subscribe()`, `create_producer()`, vb.
5. **Konu URI formatı:** Pulsar'ın `kind://tenant/namespace/topic` yapısı

### Sonraki Adımlar

Yayın/abone altyapısını yapılandırılabilir hale getirmek için şunları yapmamız gerekiyor:

1. İstem/şema sistemi için bir soyutlama arayüzü oluşturun.
2. Pulsar'a özgü numaralandırmaları ve istisnaları soyutlayın.
3. Şema sargıları veya alternatif şema tanımları oluşturun.
4. Arayüzü hem Pulsar hem de alternatif sistemler (Kafka, RabbitMQ, Redis Streams, vb.) için uygulayın.
5. `pubsub.py`'ı yapılandırılabilir hale getirin ve çoklu arka uçları destekleyin.
6. Mevcut dağıtımlar için bir geçiş yolu sağlayın.

## Yaklaşım Taslağı 1: Şema Çeviri Katmanıyla Adaptör Kalıbı

### Temel Bilgi
**Şema sistemi**, en derin entegrasyon noktasıdır - her şey ondan kaynaklanır. Önce bunu çözmemiz gerekiyor, aksi takdirde tüm kodu yeniden yazmamız gerekecek.

### Strateji: Minimum Bozulma ile Adaptörler

**1. Pulsar şemalarını, dahili gösterim olarak koruyun**
Tüm şema tanımlarını yeniden yazmayın
Şemalar, dahili olarak `pulsar.schema.Record` olarak kalır
Adaptörleri, kendi kodumuz ile yayın/abonelik arka ucu arasındaki sınırdaki çevirileri yapmak için kullanın

**2. Bir yayın/abonelik soyutlama katmanı oluşturun:**

```
┌─────────────────────────────────────┐
│   Existing Code (unchanged)         │
│   - Uses Pulsar schemas internally  │
│   - Consumer/Producer/Publisher     │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│   PubSubFactory (configurable)      │
│   - Creates backend-specific client │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
┌───────▼─────┐  ┌────▼─────────┐
│ PulsarAdapter│  │ KafkaAdapter │  etc...
│ (passthrough)│  │ (translates) │
└──────────────┘  └──────────────┘
```

**3. Soyut arayüzleri tanımlayın:**
`PubSubClient` - istemci bağlantısı
`PubSubProducer` - mesaj gönderme
`PubSubConsumer` - mesaj alma
`SchemaAdapter` - Pulsar şemalarını JSON'a veya arka uç özel formatlarına dönüştürme/dönüştürme

**4. Uygulama detayları:**

**Pulsar adaptörü için:** Neredeyse doğrudan geçiş, minimum çeviri

**Diğer arka uçlar için** (Kafka, RabbitMQ, vb.):
Pulsar Kayıt nesnelerini JSON/byte'a serileştirin
Aşağıdaki kavramları eşleyin:
  `InitialPosition.Earliest/Latest` → Kafka'nın auto.offset.reset'i
  `acknowledge()` → Kafka'nın commit'i
  `negative_acknowledge()` → Yeniden kuyruklama veya DLQ deseni
  Konu URI'leri → Arka uç özel konu adları

### Analiz

**Artıları:**
✅ Mevcut hizmetlerde minimum kod değişikliği
✅ Şemalar olduğu gibi kalır (büyük bir yeniden yazım olmaz)
✅ Aşamalı geçiş yolu
✅ Pulsar kullanıcıları hiçbir fark görmez
✅ Yeni arka uçlar adaptörler aracılığıyla eklenir

**Eksileri:**
⚠️ Hala Pulsar bağımlılığı taşır (şema tanımları için)
⚠️ Kavramları çevirirken bazı uyumsuzluklar olabilir

### Alternatif Düşünce

Bir **TrustGraph şema sistemi** oluşturun; bu sistem, pub/sub'dan bağımsızdır (dataclass'lar veya Pydantic kullanarak). Ardından, bu sistemden Pulsar/Kafka/vb. şemalarını oluşturun. Bu, her şema dosyasının yeniden yazılmasını gerektirir ve potansiyel olarak uyumsuzluklara neden olabilir.

### Taslak 1 için Öneri

**Adaptör yaklaşımıyla** başlayın çünkü:
1. Pratik bir yaklaşımdır - mevcut kodla çalışır
2. Minimum riskle kavramı kanıtlar
3. Gerekirse daha sonra yerel bir şema sistemine dönüştürülebilir
4. Yapılandırma odaklıdır: tek bir ortam değişkeni arka uçları değiştirir

## Yaklaşım Taslağı 2: Dataclass'larla Arka Uçtan Bağımsız Şema Sistemi

### Temel Kavram

Python **dataclass'ları** tarafsız şema tanımı formatı olarak kullanın. Her pub/sub arka ucu, dataclass'lar için kendi serileştirme/deserileştirme işlemlerini sağlar; bu, Pulsar şemalarının kod tabanında kalma ihtiyacını ortadan kaldırır.

### Fabrika Seviyesinde Şema Çok Biçimliliği

Pulsar şemalarını çevirmek yerine, **her arka uç, standart Python dataclass'larıyla çalışan kendi şema işleme yöntemini sağlar**.

### Yayıncı Akışı

```python
# 1. Get the configured backend from factory
pubsub = get_pubsub()  # Returns PulsarBackend, MQTTBackend, etc.

# 2. Get schema class from the backend
# (Can be imported directly - backend-agnostic)
from trustgraph.schema.services.llm import TextCompletionRequest

# 3. Create a producer/publisher for a specific topic
producer = pubsub.create_producer(
    topic="text-completion-requests",
    schema=TextCompletionRequest  # Tells backend what schema to use
)

# 4. Create message instances (same API regardless of backend)
request = TextCompletionRequest(
    system="You are helpful",
    prompt="Hello world",
    streaming=False
)

# 5. Send the message
producer.send(request)  # Backend serializes appropriately
```

### Tüketici Akışı

```python
# 1. Get the configured backend
pubsub = get_pubsub()

# 2. Create a consumer
consumer = pubsub.subscribe(
    topic="text-completion-requests",
    schema=TextCompletionRequest  # Tells backend how to deserialize
)

# 3. Receive and deserialize
msg = consumer.receive()
request = msg.value()  # Returns TextCompletionRequest dataclass instance

# 4. Use the data (type-safe access)
print(request.system)   # "You are helpful"
print(request.prompt)   # "Hello world"
print(request.streaming)  # False
```

### Sahne Arkasındaki Olaylar

**Pulsar arka ucu için:**
`create_producer()` → JSON şeması veya dinamik olarak oluşturulmuş bir kayıtla Pulsar üreticisi oluşturur.
`send(request)` → veri sınıfını JSON/Pulsar formatına serileştirir ve Pulsar'a gönderir.
`receive()` → Pulsar mesajını alır, veri sınıfına geri serileştirir.

**MQTT arka ucu için:**
`create_producer()` → MQTT aracısına bağlanır, şema kaydı gerektirmez.
`send(request)` → veri sınıfını JSON'a dönüştürür ve MQTT konusuna yayınlar.
`receive()` → MQTT konusuna abone olur, JSON'ı veri sınıfına geri serileştirir.

**Kafka arka ucu için:**
`create_producer()` → Kafka üreticisini oluşturur, gerekirse Avro şemasını kaydeder.
`send(request)` → veri sınıfını Avro formatına serileştirir ve Kafka'ya gönderir.
`receive()` → Kafka mesajını alır, Avro'yu veri sınıfına geri serileştirir.

### Temel Tasarım Noktaları

1. **Şema nesnesi oluşturma**: Veri sınıfı örneği (`TextCompletionRequest(...)`), arka uçtan bağımsız olarak aynıdır.
2. **Arka uç, kodlamayı yönetir**: Her arka uç, veri sınıfını kablo formatına nasıl serileştireceğini bilir.
3. **Oluşturma sırasında şema tanımı**: Üretici/tüketici oluştururken, şema türünü belirtirsiniz.
4. **Tür güvenliği korunur**: Doğru bir `TextCompletionRequest` nesnesi alırsınız, bir sözlük değil.
5. **Arka uç sızıntısı yok**: Uygulama kodu, arka uçla ilgili özel kütüphaneleri asla içe aktarmaz.

### Örnek Dönüşüm

**Mevcut (Pulsar'a özel):**
```python
# schema/services/llm.py
from pulsar.schema import Record, String, Boolean, Integer

class TextCompletionRequest(Record):
    system = String()
    prompt = String()
    streaming = Boolean()
```

**Yeni (Arka uçtan bağımsız):**
```python
# schema/services/llm.py
from dataclasses import dataclass

@dataclass
class TextCompletionRequest:
    system: str
    prompt: str
    streaming: bool = False
```

### Arka Uç Entegrasyonu

Her arka uç, veri sınıflarının serileştirme/deserileştirme işlemlerini gerçekleştirir:

**Pulsar arka ucu:**
Veri sınıflarından dinamik olarak `pulsar.schema.Record` sınıfları oluşturun
Veya veri sınıflarını JSON'a serileştirin ve Pulsar'ın JSON şemasını kullanın
Mevcut Pulsar kurulumlarıyla uyumluluğu korur

**MQTT/Redis arka ucu:**
Veri sınıfı örneklerinin doğrudan JSON serileştirilmesi
`dataclasses.asdict()` / `from_dict()` kullanın
Hafif, şema kayıt defterine gerek yok

**Kafka arka ucu:**
Veri sınıfı tanımlarından Avro şemaları oluşturun
Confluent'ın şema kayıt defterini kullanın
Şema evrimi desteğiyle tür güvenli serileştirme

### Mimari

```
┌─────────────────────────────────────┐
│   Application Code                  │
│   - Uses dataclass schemas          │
│   - Backend-agnostic                │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│   PubSubFactory (configurable)      │
│   - get_pubsub() returns backend    │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
┌───────▼─────────┐  ┌────▼──────────────┐
│ PulsarBackend   │  │ MQTTBackend       │
│ - JSON schema   │  │ - JSON serialize  │
│ - or dynamic    │  │ - Simple queues   │
│   Record gen    │  │                   │
└─────────────────┘  └───────────────────┘
```

### Uygulama Detayları

**1. Şema tanımları:** Basit dataclass'lar ve tür ipuçları
   `str`, `int`, `bool`, `float` temel veri tipleri için
   `list[T]` diziler için
   `dict[str, T]` haritalar için
   Karmaşık tipler için iç içe dataclass'lar

**2. Her arka uç şunları sağlar:**
   Serileştirici: `dataclass → bytes/wire format`
   Seri dışa aktarıcı: `bytes/wire format → dataclass`
   Şema kaydı (gerekirse, örneğin Pulsar/Kafka)

**3. Tüketici/Üretici soyutlaması:**
   Zaten mevcut (consumer.py, producer.py)
   Arka uç tarafından sağlanan seri dışa aktarmayı kullanmak için güncellenmeli
   Doğrudan Pulsar içe aktarmalarını kaldırmalı

**4. Tür eşlemeleri:**
   Pulsar `String()` → Python `str`
   Pulsar `Integer()` → Python `int`
   Pulsar `Boolean()` → Python `bool`
   Pulsar `Array(T)` → Python `list[T]`
   Pulsar `Map(K, V)` → Python `dict[K, V]`
   Pulsar `Double()` → Python `float`
   Pulsar `Bytes()` → Python `bytes`

### Geçiş Yolu

1. `trustgraph/schema/` içindeki tüm şemaların **dataclass versiyonlarını oluşturun**
2. Arka uç tarafından sağlanan seri dışa aktarmayı kullanmak için **arka uç sınıflarını (Tüketici, Üretici, Yayıncı, Abonelik) güncelleyin**
3. JSON şemasını veya dinamik Kayıt oluşturmayı kullanarak **PulsarBackend'i uygulayın**
4. **Mevcut dağıtımlarla geriye dönük uyumluluğu sağlamak için Pulsar ile test edin**
5. Gerekirse **yeni arka uçlar ekleyin (MQTT, Kafka, Redis, vb.)**
6. Şema dosyalarından **Pulsar içe aktarmalarını kaldırın**

### Avantajlar

✅ **Şema tanımlarında herhangi bir yayın/abonelik bağımlılığı yok**
✅ **Standart Python** - anlaşılması, tür denetimi yapılması ve belgelenmesi kolay
✅ **Modern araçlar** - mypy, IDE otomatik tamamlama, lint araçlarıyla çalışır
✅ **Arka uç odaklı** - her arka uç yerel seri dışa aktarmayı kullanır
✅ **Çeviri ek yükü yok** - doğrudan seri dışa aktarma, adaptörler yok
✅ **Tür güvenliği** - uygun türlere sahip gerçek nesneler
✅ **Kolay doğrulama** - gerekirse Pydantic kullanılabilir

### Zorluklar & Çözümler

**Zorluk:** Pulsar'ın `Record`'ı çalışma zamanı alan doğrulamasına sahiptir
**Çözüm:** Gerekirse doğrulama için Pydantic dataclass'larını kullanın veya `__post_init__` ile Python 3.10+ dataclass özelliklerini kullanın

**Zorluk:** Bazı Pulsar'a özgü özellikler (örneğin `Bytes` türü)
**Çözüm:** Bu türü dataclass'ta `bytes` türüne eşleyin, arka uç uygun şekilde kodlamayı işler

**Zorluk:** Konu adlandırması (`persistent://tenant/namespace/topic`)
**Çözüm:** Şema tanımlarında konu adlarını soyutlayın, arka uç uygun formata dönüştürür

**Zorluk:** Şema evrimi ve sürüm oluşturma
**Çözüm:** Her arka uç, yeteneklerine göre bunu işler (Pulsar şema sürümleri, Kafka şema kaydı, vb.)

**Zorluk:** İç içe karmaşık türler
**Çözüm:** İç içe dataclass'ları kullanın, arka uçlar yinelemeli olarak seri dışa aktarır/serileştirir

### Tasarım Kararları

1. **Basit dataclass'lar mı yoksa Pydantic mi?**
   ✅ **Karar: Basit Python dataclass'ları kullanın**
   Daha basit, ek bağımlılık yok
   Uygulamada doğrulama gerekli değil
   Anlaşılması ve bakımı daha kolay

2. **Şema evrimi:**
   ✅ **Karar: Herhangi bir sürüm oluşturma mekanizmasına gerek yok**
   Şemalar kararlı ve uzun ömürlü
   Güncellemeler genellikle yeni alanlar ekler (geriye dönük uyumlu)
   Arka uçlar, yeteneklerine göre şema evrimini işler

3. **Geriye dönük uyumluluk:**
   ✅ **Karar: Ana sürüm değişikliği, geriye dönük uyumluluk gerekli değil**
   Bu, bir kopma değişikliği olacak ve geçiş talimatları sağlanacak
   Temiz bir kopma, daha iyi bir tasarım sağlar
   Mevcut dağıtımlar için bir geçiş kılavuzu sağlanacaktır

4. **İç içe türler ve karmaşık yapılar:**
   ✅ **Karar: İç içe dataclass'ları doğal olarak kullanın**
   Python dataclass'ları iç içe geçmeyi mükemmel şekilde işler
   Diziler için `list[T]`, haritalar için `dict[K, V]`
   Arka uçlar yinelemeli olarak seri dışa aktarır/serileştirir
   Örnek:
     ```python
     @dataclass
     class Value:
         value: str
         is_uri: bool

     @dataclass
     class Triple:
         s: Value              # Nested dataclass
         p: Value
         o: Value

     @dataclass
     class GraphQuery:
         triples: list[Triple]  # Array of nested dataclasses
         metadata: dict[str, str]
     ```

5. **Varsayılan değerler ve isteğe bağlı alanlar:**
   ✅ **Karar: Gerekli, varsayılan ve isteğe bağlı alanların birleşimi**
   Gerekli alanlar: Herhangi bir varsayılan değer yok
   Varsayılan değerlere sahip alanlar: Her zaman mevcut, anlamlı varsayılan değerlere sahip
   Tamamen isteğe bağlı alanlar: `T | None = None`, `None` olduğunda serileştirmeden çıkarılır
   Örnek:
     ```python
     @dataclass
     class TextCompletionRequest:
         system: str              # Required, no default
         prompt: str              # Required, no default
         streaming: bool = False  # Optional with default value
         metadata: dict | None = None  # Truly optional, can be absent
     ```

   **Önemli serileştirme kuralları:**

   `metadata = None` olduğunda:
   ```json
   {
       "system": "...",
       "prompt": "...",
       "streaming": false
       // metadata field NOT PRESENT
   }
   ```

   `metadata = {}` (açıkça boş) olduğunda:
   ```json
   {
       "system": "...",
       "prompt": "...",
       "streaming": false,
       "metadata": {}  // Field PRESENT but empty
   }
   ```

   **Temel ayrım:**
   `None` → JSON'da bulunmayan alan (serileştirilmiyor)
   Boş değer (`{}`, `[]`, `""`) → alan, boş bir değerle mevcut
   Bu, anlamsal olarak önemlidir: "sağlanmadı" ile "açıkça boş"
   Serileştirme arka uçları, `None` alanlarını atlamalı, bunları `null` olarak kodlamamalıdır.

## Yaklaşım Taslağı 3: Uygulama Detayları

### Genel Kuyruk Adlandırma Formatı

Arka uçlara özgü kuyruk adlarını, arka uçların uygun şekilde eşleyebileceği genel bir formata dönüştürün.

**Format:** `{qos}/{tenant}/{namespace}/{queue-name}`

Nerede:
`qos`: Hizmet kalitesi seviyesi
  `q0` = en iyi çaba (ateşle ve unut, onay yok)
  `q1` = en az bir kez (onay gerektirir)
  `q2` = tam olarak bir kez (iki aşamalı onay)
`tenant`: Çok kiracılılık için mantıksal gruplandırma
`namespace`: Kiracı içindeki alt gruplandırma
`queue-name`: Gerçek kuyruk/konu adı

**Örnekler:**
```
q1/tg/flow/text-completion-requests
q2/tg/config/config-push
q0/tg/metrics/stats
```

### Arka Uç Konu Eşlemesi

Her arka uç, genel formatı kendi yerel formatına eşler:

**Pulsar Arka Ucu:**
```python
def map_topic(self, generic_topic: str) -> str:
    # Parse: q1/tg/flow/text-completion-requests
    qos, tenant, namespace, queue = generic_topic.split('/', 3)

    # Map QoS to persistence
    persistence = 'persistent' if qos in ['q1', 'q2'] else 'non-persistent'

    # Return Pulsar URI: persistent://tg/flow/text-completion-requests
    return f"{persistence}://{tenant}/{namespace}/{queue}"
```

**MQTT Altyapısı:**
```python
def map_topic(self, generic_topic: str) -> tuple[str, int]:
    # Parse: q1/tg/flow/text-completion-requests
    qos, tenant, namespace, queue = generic_topic.split('/', 3)

    # Map QoS level
    qos_level = {'q0': 0, 'q1': 1, 'q2': 2}[qos]

    # Build MQTT topic including tenant/namespace for proper namespacing
    mqtt_topic = f"{tenant}/{namespace}/{queue}"

    return mqtt_topic, qos_level
```

### Güncellenmiş Konu Yardımcı Fonksiyonu

```python
# schema/core/topic.py
def topic(queue_name, qos='q1', tenant='tg', namespace='flow'):
    """
    Create a generic topic identifier that can be mapped by backends.

    Args:
        queue_name: The queue/topic name
        qos: Quality of service
             - 'q0' = best-effort (no ack)
             - 'q1' = at-least-once (ack required)
             - 'q2' = exactly-once (two-phase ack)
        tenant: Tenant identifier for multi-tenancy
        namespace: Namespace within tenant

    Returns:
        Generic topic string: qos/tenant/namespace/queue_name

    Examples:
        topic('my-queue')  # q1/tg/flow/my-queue
        topic('config', qos='q2', namespace='config')  # q2/tg/config/config
    """
    return f"{qos}/{tenant}/{namespace}/{queue_name}"
```

### Yapılandırma ve Başlatma

**Komut Satırı Argümanları + Ortam Değişkenleri:**

```python
# In base/async_processor.py - add_args() method
@staticmethod
def add_args(parser):
    # Pub/sub backend selection
    parser.add_argument(
        '--pubsub-backend',
        default=os.getenv('PUBSUB_BACKEND', 'pulsar'),
        choices=['pulsar', 'mqtt'],
        help='Pub/sub backend (default: pulsar, env: PUBSUB_BACKEND)'
    )

    # Pulsar-specific configuration
    parser.add_argument(
        '--pulsar-host',
        default=os.getenv('PULSAR_HOST', 'pulsar://localhost:6650'),
        help='Pulsar host (default: pulsar://localhost:6650, env: PULSAR_HOST)'
    )

    parser.add_argument(
        '--pulsar-api-key',
        default=os.getenv('PULSAR_API_KEY', None),
        help='Pulsar API key (env: PULSAR_API_KEY)'
    )

    parser.add_argument(
        '--pulsar-listener',
        default=os.getenv('PULSAR_LISTENER', None),
        help='Pulsar listener name (env: PULSAR_LISTENER)'
    )

    # MQTT-specific configuration
    parser.add_argument(
        '--mqtt-host',
        default=os.getenv('MQTT_HOST', 'localhost'),
        help='MQTT broker host (default: localhost, env: MQTT_HOST)'
    )

    parser.add_argument(
        '--mqtt-port',
        type=int,
        default=int(os.getenv('MQTT_PORT', '1883')),
        help='MQTT broker port (default: 1883, env: MQTT_PORT)'
    )

    parser.add_argument(
        '--mqtt-username',
        default=os.getenv('MQTT_USERNAME', None),
        help='MQTT username (env: MQTT_USERNAME)'
    )

    parser.add_argument(
        '--mqtt-password',
        default=os.getenv('MQTT_PASSWORD', None),
        help='MQTT password (env: MQTT_PASSWORD)'
    )
```

**Fabrika Fonksiyonu:**

```python
# In base/pubsub.py or base/pubsub_factory.py
def get_pubsub(**config) -> PubSubBackend:
    """
    Create and return a pub/sub backend based on configuration.

    Args:
        config: Configuration dict from command-line args
                Must include 'pubsub_backend' key

    Returns:
        Backend instance (PulsarBackend, MQTTBackend, etc.)
    """
    backend_type = config.get('pubsub_backend', 'pulsar')

    if backend_type == 'pulsar':
        return PulsarBackend(
            host=config.get('pulsar_host'),
            api_key=config.get('pulsar_api_key'),
            listener=config.get('pulsar_listener'),
        )
    elif backend_type == 'mqtt':
        return MQTTBackend(
            host=config.get('mqtt_host'),
            port=config.get('mqtt_port'),
            username=config.get('mqtt_username'),
            password=config.get('mqtt_password'),
        )
    else:
        raise ValueError(f"Unknown pub/sub backend: {backend_type}")
```

**AsyncProcessor'da Kullanım:**

```python
# In async_processor.py
class AsyncProcessor:
    def __init__(self, **params):
        self.id = params.get("id")

        # Create backend from config (replaces PulsarClient)
        self.pubsub = get_pubsub(**params)

        # Rest of initialization...
```

### Arka Uç Arayüzü

```python
class PubSubBackend(Protocol):
    """Protocol defining the interface all pub/sub backends must implement."""

    def create_producer(self, topic: str, schema: type, **options) -> BackendProducer:
        """
        Create a producer for a topic.

        Args:
            topic: Generic topic format (qos/tenant/namespace/queue)
            schema: Dataclass type for messages
            options: Backend-specific options (e.g., chunking_enabled)

        Returns:
            Backend-specific producer instance
        """
        ...

    def create_consumer(
        self,
        topic: str,
        subscription: str,
        schema: type,
        initial_position: str = 'latest',
        consumer_type: str = 'shared',
        **options
    ) -> BackendConsumer:
        """
        Create a consumer for a topic.

        Args:
            topic: Generic topic format (qos/tenant/namespace/queue)
            subscription: Subscription/consumer group name
            schema: Dataclass type for messages
            initial_position: 'earliest' or 'latest' (MQTT may ignore)
            consumer_type: 'shared', 'exclusive', 'failover' (MQTT may ignore)
            options: Backend-specific options

        Returns:
            Backend-specific consumer instance
        """
        ...

    def close(self) -> None:
        """Close the backend connection."""
        ...
```

```python
class BackendProducer(Protocol):
    """Protocol for backend-specific producer."""

    def send(self, message: Any, properties: dict = {}) -> None:
        """Send a message (dataclass instance) with optional properties."""
        ...

    def flush(self) -> None:
        """Flush any buffered messages."""
        ...

    def close(self) -> None:
        """Close the producer."""
        ...
```

```python
class BackendConsumer(Protocol):
    """Protocol for backend-specific consumer."""

    def receive(self, timeout_millis: int = 2000) -> Message:
        """
        Receive a message from the topic.

        Raises:
            TimeoutError: If no message received within timeout
        """
        ...

    def acknowledge(self, message: Message) -> None:
        """Acknowledge successful processing of a message."""
        ...

    def negative_acknowledge(self, message: Message) -> None:
        """Negative acknowledge - triggers redelivery."""
        ...

    def unsubscribe(self) -> None:
        """Unsubscribe from the topic."""
        ...

    def close(self) -> None:
        """Close the consumer."""
        ...
```

```python
class Message(Protocol):
    """Protocol for a received message."""

    def value(self) -> Any:
        """Get the deserialized message (dataclass instance)."""
        ...

    def properties(self) -> dict:
        """Get message properties/metadata."""
        ...
```

### Mevcut Sınıfların Yeniden Düzenlenmesi

Mevcut `Consumer`, `Producer`, `Publisher`, `Subscriber` sınıfları büyük ölçüde aynı kalacaktır:

**Mevcut sorumluluklar (saklanacak):**
Asenkron iş parçacığı modeli ve görev grupları
Yeniden bağlantı mantığı ve tekrar deneme işleme
Ölçüm toplama
Hız sınırlama
Eşzamanlılık yönetimi

**Gerekli değişiklikler:**
Doğrudan Pulsar içe aktarmalarını kaldırın (`pulsar.schema`, `pulsar.InitialPosition`, vb.)
`BackendProducer`/`BackendConsumer`'i Pulsar istemcisi yerine kullanın
Gerçek yayın/abonelik işlemlerini arka uç örneklerine devredin
Genel kavramları arka uç çağrılarına eşleyin

**Örnek yeniden düzenleme:**

```python
# OLD - consumer.py
class Consumer:
    def __init__(self, client, topic, subscriber, schema, ...):
        self.client = client  # Direct Pulsar client
        # ...

    async def consumer_run(self):
        # Uses pulsar.InitialPosition, pulsar.ConsumerType
        self.consumer = self.client.subscribe(
            topic=self.topic,
            schema=JsonSchema(self.schema),
            initial_position=pulsar.InitialPosition.Earliest,
            consumer_type=pulsar.ConsumerType.Shared,
        )

# NEW - consumer.py
class Consumer:
    def __init__(self, backend_consumer, schema, ...):
        self.backend_consumer = backend_consumer  # Backend-specific consumer
        self.schema = schema
        # ...

    async def consumer_run(self):
        # Backend consumer already created with right settings
        # Just use it directly
        while self.running:
            msg = await asyncio.to_thread(
                self.backend_consumer.receive,
                timeout_millis=2000
            )
            await self.handle_message(msg)
```

### Arka Uç Özel Davranışlar

**Pulsar Arka Uç:**
`q0`'ı `non-persistent://`'e, `q1`/`q2`'ü `persistent://`'e eşler.
Tüm tüketici türlerini (paylaşımlı, özel, yedekli) destekler.
Başlangıç konumunu (en erken/en son) destekler.
Yerel mesaj onayı.
Şema kayıt defteri desteği.

**MQTT Arka Uç:**
`q0`/`q1`/`q2`'yi MQTT QoS seviyeleri 0/1/2'ye eşler.
Adlandırma için konu yoluna kiracı/isim alanı ekler.
Abonelik adlarından otomatik olarak istemci kimlikleri oluşturur.
Başlangıç konumunu yoksayar (temel MQTT'de mesaj geçmişi yoktur).
Tüketici türünü yoksayar (MQTT, tüketici grupları yerine istemci kimlikleri kullanır).
Basit yayın/abone modeli.

### Tasarım Kararları Özeti

1. ✅ **Genel kuyruk adlandırması**: `qos/tenant/namespace/queue-name` formatı
2. ✅ **Kuyruk kimliğindeki QoS**: Kuyruk tanımı tarafından belirlenir, yapılandırma ile değil.
3. ✅ **Yeniden bağlanma**: Tüketici/Üretici sınıfları tarafından işlenir, arka uçlar tarafından değil.
4. ✅ **MQTT konuları**: Doğru adlandırma için kiracı/isim alanı içerir.
5. ✅ **Mesaj geçmişi**: MQTT, `initial_position` parametresini yoksayar (gelecek geliştirmeler).
6. ✅ **İstemci kimlikleri**: MQTT arka ucu, abonelik adından otomatik olarak oluşturur.

### Gelecek Geliştirmeler

**MQTT mesaj geçmişi:**
İsteğe bağlı bir kalıcılık katmanı eklenebilir (örneğin, saklanan mesajlar, harici depolama).
`initial_position='earliest'`'ı desteklemeyi mümkün kılacaktır.
Başlangıç uygulamasında gerekli değildir.
