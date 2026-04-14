---
layout: default
title: "TrustGraph Python API Referansı"
parent: "Turkish (Beta)"
---

# TrustGraph Python API Referansı

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Kurulum

```bash
pip install trustgraph
```

## Hızlı Başlangıç

Tüm sınıflar ve tipler, `trustgraph.api` paketinden içe aktarılmıştır:

```python
from trustgraph.api import Api, Triple, ConfigKey

# Create API client
api = Api(url="http://localhost:8088/")

# Get a flow instance
flow = api.flow().id("default")

# Execute a graph RAG query
response = flow.graph_rag(
    query="What are the main topics?",
    user="trustgraph",
    collection="default"
)
```

## İçindekiler

### Çekirdek

[Api](#api)

### Akış İstemcileri

[Flow](#flow)
[FlowInstance](#flowinstance)
[AsyncFlow](#asyncflow)
[AsyncFlowInstance](#asyncflowinstance)

### WebSocket İstemcileri

[SocketClient](#socketclient)
[SocketFlowInstance](#socketflowinstance)
[AsyncSocketClient](#asyncsocketclient)
[AsyncSocketFlowInstance](#asyncsocketflowinstance)

### Toplu İşlemler

[BulkClient](#bulkclient)
[AsyncBulkClient](#asyncbulkclient)

### Metrikler

[Metrics](#metrics)
[AsyncMetrics](#asyncmetrics)

### Veri Tipleri

[Triple](#triple)
[ConfigKey](#configkey)
[ConfigValue](#configvalue)
[DocumentMetadata](#documentmetadata)
[ProcessingMetadata](#processingmetadata)
[CollectionMetadata](#collectionmetadata)
[StreamingChunk](#streamingchunk)
[AgentThought](#agentthought)
[AgentObservation](#agentobservation)
[AgentAnswer](#agentanswer)
[RAGChunk](#ragchunk)

### İstisnalar

[ProtocolException](#protocolexception)
[TrustGraphException](#trustgraphexception)
[AgentError](#agenterror)
[ConfigError](#configerror)
[DocumentRagError](#documentragerror)
[FlowError](#flowerror)
[GatewayError](#gatewayerror)
[GraphRagError](#graphragerror)
[LLMError](#llmerror)
[LoadError](#loaderror)
[LookupError](#lookuperror)
[NLPQueryError](#nlpqueryerror)
[RowsQueryError](#rowsqueryerror)
[RequestError](#requesterror)
[StructuredQueryError](#structuredqueryerror)
[UnexpectedError](#unexpectederror)
[ApplicationException](#applicationexception)

--

## `Api`

```python
from trustgraph.api import Api
```

Senkron ve asenkron işlemler için ana TrustGraph API istemcisi.

Bu sınıf, akış yönetimi,
bilgi grafiği işlemleri, belge işleme, RAG sorguları ve daha fazlası dahil olmak üzere tüm TrustGraph hizmetlerine erişim sağlar. Hem REST tabanlı hem de WebSocket tabanlı iletişim modellerini destekler.


İstemci, otomatik kaynak temizliği için bir bağlam yöneticisi olarak kullanılabilir:
    ```python
    with Api(url="http://localhost:8088/") as api:
        result = api.flow().id("default").graph_rag(query="test")
    ```

### Yöntemler

### `__aenter__(self)`

Asenkron bağlam yöneticisine girin.

### `__aexit__(self, *args)`

Asenkron bağlam yöneticisinden çıkın ve bağlantıları kapatın.

### `__enter__(self)`

Senkron bağlam yöneticisine girin.

### `__exit__(self, *args)`

Senkron bağlam yöneticisinden çıkın ve bağlantıları kapatın.

### `__init__(self, url='http://localhost:8088/', timeout=60, token: str | None = None)`

TrustGraph API istemciyi başlatın.

**Argümanlar:**

`url`: TrustGraph API'si için temel URL (varsayılan: "http://localhost:8088/"")
`timeout`: İstek zaman aşımı süresi (saniye cinsinden) (varsayılan: 60)
`token`: İsteğe bağlı doğrulama için taşıyıcı belirteci

**Örnek:**

```python
# Local development
api = Api()

# Production with authentication
api = Api(
    url="https://trustgraph.example.com/",
    timeout=120,
    token="your-api-token"
)
```

### `aclose(self)`

Tüm asenkron istemci bağlantılarını kapatın.

Bu yöntem, asenkron WebSocket, toplu işlem ve akış bağlantılarını kapatır.
Bu, asenkron bir bağlam yöneticisinden çıkıldığında otomatik olarak çağrılır.

**Örnek:**

```python
api = Api()
async_socket = api.async_socket()
# ... use async_socket
await api.aclose()  # Clean up connections

# Or use async context manager (automatic cleanup)
async with Api() as api:
    async_socket = api.async_socket()
    # ... use async_socket
# Automatically closed
```

### `async_bulk(self)`

Asenkron toplu işlemler istemcisi alın.

WebSocket üzerinden asenkron/bekleme tarzı toplu içe/dışa aktarma işlemleri sağlar,
böylece büyük veri kümelerinin verimli bir şekilde işlenmesini sağlar.

**Döndürür:** AsyncBulkClient: Asenkron toplu işlemler istemcisi

**Örnek:**

```python
async_bulk = api.async_bulk()

# Export triples asynchronously
async for triple in async_bulk.export_triples(flow="default"):
    print(f"{triple.s} {triple.p} {triple.o}")

# Import with async generator
async def triple_gen():
    yield Triple(s="subj", p="pred", o="obj")
    # ... more triples

await async_bulk.import_triples(
    flow="default",
    triples=triple_gen()
)
```

### `async_flow(self)`

Asenkron, REST tabanlı bir akış istemcisi alın.

Akış işlemlerine, async/await stili erişim sağlar. Bu, asenkron Python uygulamaları ve çerçeveleri (FastAPI, aiohttp, vb.) için tercih edilir.


**Döndürür:** AsyncFlow: Asenkron akış istemcisi

**Örnek:**

```python
async_flow = api.async_flow()

# List flows
flow_ids = await async_flow.list()

# Execute operations
instance = async_flow.id("default")
result = await instance.text_completion(
    system="You are helpful",
    prompt="Hello"
)
```

### `async_metrics(self)`

Asenkron bir metrik istemcisi alın.

Prometheus metriklerine, async/await tarzında erişim sağlar.

**Döndürür:** AsyncMetrics: Asenkron metrik istemcisi

**Örnek:**

```python
async_metrics = api.async_metrics()
prometheus_text = await async_metrics.get()
print(prometheus_text)
```

### `async_socket(self)`

Akış işlemleri için asenkron bir WebSocket istemcisi alın.

Akış desteği ile asenkron/bekleme tarzı WebSocket erişimi sağlar.
Bu, Python'da asenkron akış için tercih edilen yöntemdir.

**Döndürür:** AsyncSocketClient: Asenkron WebSocket istemcisi

**Örnek:**

```python
async_socket = api.async_socket()
flow = async_socket.flow("default")

# Stream agent responses
async for chunk in flow.agent(
    question="Explain quantum computing",
    user="trustgraph",
    streaming=True
):
    if hasattr(chunk, 'content'):
        print(chunk.content, end='', flush=True)
```

### `bulk(self)`

İçe/dışa aktarım için senkron toplu işlemler istemcisi alın.

Toplu işlemler, üçlüler, gömülü veriler, varlık bağlamları ve nesneler dahil olmak üzere büyük veri kümelerinin WebSocket bağlantıları aracılığıyla verimli bir şekilde aktarılmasını sağlar.

**Döndürür:** BulkClient: Senkron toplu işlemler istemcisi

**Örnek:**


```python
bulk = api.bulk()

# Export triples
for triple in bulk.export_triples(flow="default"):
    print(f"{triple.s} {triple.p} {triple.o}")

# Import triples
def triple_generator():
    yield Triple(s="subj", p="pred", o="obj")
    # ... more triples

bulk.import_triples(flow="default", triples=triple_generator())
```

### `close(self)`

Tüm senkronize istemci bağlantılarını kapatın.

Bu yöntem, WebSocket ve toplu işlem bağlantılarını kapatır.
Bir bağlam yöneticisinden çıkılırken otomatik olarak çağrılır.

**Örnek:**

```python
api = Api()
socket = api.socket()
# ... use socket
api.close()  # Clean up connections

# Or use context manager (automatic cleanup)
with Api() as api:
    socket = api.socket()
    # ... use socket
# Automatically closed
```

### `collection(self)`

Veri koleksiyonlarını yönetmek için bir Collection istemcisi alın.

Koleksiyonlar, belgeleri ve bilgi grafiği verilerini,
izolasyon ve erişim kontrolü için mantıksal gruplara ayırır.

**Döndürür:** Collection: Koleksiyon yönetimi istemcisi

**Örnek:**

```python
collection = api.collection()

# List collections
colls = collection.list_collections(user="trustgraph")

# Update collection metadata
collection.update_collection(
    user="trustgraph",
    collection="default",
    name="Default Collection",
    description="Main data collection"
)
```

### `config(self)`

Yapılandırma ayarlarını yönetmek için bir Config istemcisi alın.

**Döndürür:** Config: Yapılandırma yönetimi istemcisi

**Örnek:**

```python
config = api.config()

# Get configuration values
values = config.get([ConfigKey(type="llm", key="model")])

# Set configuration
config.put([ConfigValue(type="llm", key="model", value="gpt-4")])
```

### `flow(self)`

Akışları yönetmek ve etkileşim kurmak için bir Flow istemcisi edinin.

Akışlar, TrustGraph'ta birincil yürütme birimleridir ve ajanlar, RAG sorguları, gömme ve belge işleme gibi
hizmetlere erişim sağlar.

**Döndürür:** Flow: Akış yönetimi istemcisi

**Örnek:**

```python
flow_client = api.flow()

# List available blueprints
blueprints = flow_client.list_blueprints()

# Get a specific flow instance
flow_instance = flow_client.id("default")
response = flow_instance.text_completion(
    system="You are helpful",
    prompt="Hello"
)
```

### `knowledge(self)`

Bilgi grafiği çekirdeklerini yönetmek için bir Knowledge istemcisi edinin.

**Döndürür:** Knowledge: Bilgi grafiği yönetimi istemcisi

**Örnek:**

```python
knowledge = api.knowledge()

# List available KG cores
cores = knowledge.list_kg_cores(user="trustgraph")

# Load a KG core
knowledge.load_kg_core(id="core-123", user="trustgraph")
```

### `library(self)`

Belge yönetimi için bir Kütüphane istemcisi edinin.

Bu kütüphane, belge depolama, meta veri yönetimi ve
iş akışı koordinasyonu sağlar.

**Döndürür:** Library: Belge kütüphanesi yönetimi istemcisi

**Örnek:**

```python
library = api.library()

# Add a document
library.add_document(
    document=b"Document content",
    id="doc-123",
    metadata=[],
    user="trustgraph",
    title="My Document",
    comments="Test document"
)

# List documents
docs = library.get_documents(user="trustgraph")
```

### `metrics(self)`

İzleme için senkron bir ölçüm istemcisi alın.

İzleme ve gözlemlenebilirlik için TrustGraph hizmetinden Prometheus formatında ölçümleri alır.

**Döndürür:** Ölçümler: Senkron ölçüm istemcisi


**Örnek:**

```python
metrics = api.metrics()
prometheus_text = metrics.get()
print(prometheus_text)
```

### `request(self, path, request)`

Düşük seviyeli bir REST API isteği yapın.

Bu yöntem öncelikle dahili kullanım içindir, ancak gerektiğinde doğrudan
API erişimi için kullanılabilir.

**Argümanlar:**

`path`: API uç noktası yolu (temel URL'ye göre)
`request`: İstek yükü, bir sözlük olarak

**Döndürür:** dict: Yanıt nesnesi

**Hatalar:**

`ProtocolException`: Yanıt durum kodu 200 değilse veya yanıt JSON değilse
`ApplicationException`: Yanıt bir hata içeriyorsa

**Örnek:**

```python
response = api.request("flow", {
    "operation": "list-flows"
})
```

### `socket(self)`

Akış işlemleri için senkron bir WebSocket istemcisi alın.

WebSocket bağlantıları, gerçek zamanlı yanıtlar için akış desteği sağlar
ajanlardan, RAG sorgularından ve metin tamamlama işlemlerinden. Bu yöntem, WebSocket protokolünün
senkron bir sarmalayıcısını döndürür.

**Döndürür:** SocketClient: Senkron WebSocket istemcisi

**Örnek:**

```python
socket = api.socket()
flow = socket.flow("default")

# Stream agent responses
for chunk in flow.agent(
    question="Explain quantum computing",
    user="trustgraph",
    streaming=True
):
    if hasattr(chunk, 'content'):
        print(chunk.content, end='', flush=True)
```


--

## `Flow`

```python
from trustgraph.api import Flow
```

Blueprint ve akış örneği işlemlerini gerçekleştirmek için kullanılan akış yönetimi istemcisi.

Bu sınıf, akış blueprint'larını (şablonları) ve
akış örneklerini (çalışan akışları) yönetmek için yöntemler sağlar. Blueprint'ler, akışların yapısını ve
parametrelerini tanımlarken, örnekler, hizmetleri çalıştırabilen aktif akışları temsil eder.


### Yöntemler

### `__init__(self, api)`

Akış istemcisini başlat.

**Argümanlar:**

`api`: İstekler göndermek için kullanılan üst düzey Api örneği.

### `delete_blueprint(self, blueprint_name)`

Bir akış blueprint'ini sil.

**Argümanlar:**

`blueprint_name`: Silinecek blueprint'in adı.

**Örnek:**

```python
api.flow().delete_blueprint("old-blueprint")
```

### `get(self, id)`

Çalışan bir akış örneğinin tanımını alın.

**Argümanlar:**

`id`: Akış örneği kimliği

**Döndürür:** dict: Akış örneği tanımı

**Örnek:**

```python
flow_def = api.flow().get("default")
print(flow_def)
```

### `get_blueprint(self, blueprint_name)`

Bir akış şema tanımını ada göre alın.

**Argümanlar:**

`blueprint_name`: Alınacak şemanın adı

**Döndürür:** dict: Şema tanımı bir sözlük olarak

**Örnek:**

```python
blueprint = api.flow().get_blueprint("default")
print(blueprint)  # Blueprint configuration
```

### `id(self, id='default')`

Belirli bir akış üzerinde işlemler yürütmek için bir FlowInstance alın.

**Argümanlar:**

`id`: Akış tanımlayıcısı (varsayılan: "default")

**Döndürür:** FlowInstance: Servis işlemleri için akış örneği

**Örnek:**

```python
flow = api.flow().id("my-flow")
response = flow.text_completion(
    system="You are helpful",
    prompt="Hello"
)
```

### `list(self)`

Tüm aktif akış örneklerini listele.

**Döndürür:** list[str]: Akış örnekleri kimliklerinin listesi

**Örnek:**

```python
flows = api.flow().list()
print(flows)  # ['default', 'flow-1', 'flow-2', ...]
```

### `list_blueprints(self)`

Mevcut tüm akış şemalarını listele.

**Döndürür:** list[str]: Şema adlarının listesi

**Örnek:**

```python
blueprints = api.flow().list_blueprints()
print(blueprints)  # ['default', 'custom-flow', ...]
```

### `put_blueprint(self, blueprint_name, definition)`

Bir akış şemasını oluştur veya güncelle.

**Argümanlar:**

`blueprint_name`: Şema için isim
`definition`: Şema tanım sözlüğü

**Örnek:**

```python
definition = {
    "services": ["text-completion", "graph-rag"],
    "parameters": {"model": "gpt-4"}
}
api.flow().put_blueprint("my-blueprint", definition)
```

### `request(self, path=None, request=None)`

Akış kapsamlı bir API isteği yapın.

**Argümanlar:**

`path`: Akış uç noktaları için isteğe bağlı yol soneki
`request`: İstek yükü sözlüğü

**Döndürür:** dict: Yanıt nesnesi

**Hatalar:**

`RuntimeError`: İstek parametresi belirtilmediyse

### `start(self, blueprint_name, id, description, parameters=None)`

Bir şablondan yeni bir akış örneği başlatın.

**Argümanlar:**

`blueprint_name`: Oluşturulacak şablonun adı
`id`: Akış örneği için benzersiz tanımlayıcı
`description`: İnsan tarafından okunabilir açıklama
`parameters`: İsteğe bağlı parametreler sözlüğü

**Örnek:**

```python
api.flow().start(
    blueprint_name="default",
    id="my-flow",
    description="My custom flow",
    parameters={"model": "gpt-4"}
)
```

### `stop(self, id)`

Çalışan bir akış örneğini durdurun.

**Argümanlar:**

`id`: Durdurulacak akış örneği kimliği

**Örnek:**

```python
api.flow().stop("my-flow")
```


--

## `FlowInstance`

```python
from trustgraph.api import FlowInstance
```

Belirli bir akış üzerinde hizmetleri çalıştırmak için kullanılan akış örneği istemcisi.

Bu sınıf, aşağıdaki TrustGraph hizmetlerine erişim sağlar:
Metin tamamlama ve gömme
Durum yönetimi ile birlikte aracı işlemleri
Grafik ve belge RAG sorguları
Bilgi grafiği işlemleri (üçlüler, nesneler)
Belge yükleme ve işleme
Doğal dili GraphQL sorgusuna dönüştürme
Yapılandırılmış veri analizi ve şema algılama
MCP aracı yürütme
İstek şablonlama

Hizmetler, ID ile tanımlanan çalışan bir akış örneği aracılığıyla erişilir.

### Yöntemler

### `__init__(self, api, id)`

FlowInstance'ı başlat.

**Argümanlar:**

`api`: Üst akış istemcisi
`id`: Akış örneği tanımlayıcısı

### `agent(self, question, user='trustgraph', state=None, group=None, history=None)`

Akıl yürütme ve araç kullanma yetenekleriyle bir aracı işlemi yürüt.

Aracıların çok adımlı akıl yürütme yapabilmesi, araçları kullanabilmesi ve etkileşimler arasında konuşma
durumunu koruyabilmesi mümkündür. Bu, senkron, akışsız bir versiyondur.

**Argümanlar:**

`question`: Kullanıcı sorusu veya talimatı
`user`: Kullanıcı tanımlayıcısı (varsayılan: "trustgraph")
`state`: Durumlu konuşmalar için isteğe bağlı durum sözlüğü
`group`: Çok kullanıcılı bağlamlar için isteğe bağlı grup tanımlayıcısı
`history`: İsteğe bağlı olarak mesaj sözlükleri listesi olarak konuşma geçmişi

**Döndürür:** str: Aracının son cevabı

**Örnek:**

```python
flow = api.flow().id("default")

# Simple question
answer = flow.agent(
    question="What is the capital of France?",
    user="trustgraph"
)

# With conversation history
history = [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi! How can I help?"}
]
answer = flow.agent(
    question="Tell me about Paris",
    user="trustgraph",
    history=history
)
```

### `detect_type(self, sample)`

Yapılandırılmış bir veri örneğinin veri türünü tespit edin.

**Argümanlar:**

`sample`: Analiz edilecek veri örneği (metin içeriği)

**Döndürür:** tespit_türü, güven ve isteğe bağlı meta verileri içeren bir sözlük.

### `diagnose_data(self, sample, schema_name=None, options=None)`

Birleşik veri tanılama işlemini gerçekleştirin: türü tespit edin ve tanımlayıcı oluşturun.

**Argümanlar:**

`sample`: Analiz edilecek veri örneği (metin içeriği)
`schema_name`: İsteğe bağlı, tanımlayıcı oluşturmak için hedef şema adı
`options`: İsteğe bağlı parametreler (örneğin, CSV için ayraç)

**Döndürür:** tespit_türü, güven, tanımlayıcı ve meta verileri içeren bir sözlük.

### `document_embeddings_query(self, text, user, collection, limit=10)`

Anlamsal benzerlik kullanarak belge parçalarına sorgu yapın.

Vektör gömüler kullanarak, içeriği giriş metnine anlamsal olarak benzeyen belge parçalarını bulur.


**Argümanlar:**

`text`: Anlamsal arama için sorgu metni
`user`: Kullanıcı/keyspace tanımlayıcısı
`collection`: Koleksiyon tanımlayıcısı
`limit`: Maksimum sonuç sayısı (varsayılan: 10)

**Döndürür:** dict: Parçaları içeren sonuçlar, chunk_id ve puan ile birlikte.

**Örnek:**

```python
flow = api.flow().id("default")
results = flow.document_embeddings_query(
    text="machine learning algorithms",
    user="trustgraph",
    collection="research-papers",
    limit=5
)
# results contains {"chunks": [{"chunk_id": "doc1/p0/c0", "score": 0.95}, ...]}
```

### `document_rag(self, query, user='trustgraph', collection='default', doc_limit=10)`

Belge tabanlı Geliştirilmiş Bilgi Alma (RAG) sorgusunu çalıştırın.

Belge RAG, ilgili belge parçalarını bulmak için vektör gömülerini kullanır,
ardından bu parçaları bağlam olarak kullanarak bir LLM ile bir yanıt oluşturur.

**Argümanlar:**

`query`: Doğal dil sorgusu
`user`: Kullanıcı/keyspace tanımlayıcısı (varsayılan: "trustgraph")
`collection`: Koleksiyon tanımlayıcısı (varsayılan: "default")
`doc_limit`: Alınacak maksimum belge parçası sayısı (varsayılan: 10)

**Döndürür:** str: Belge bağlamını içeren oluşturulan yanıt

**Örnek:**

```python
flow = api.flow().id("default")
response = flow.document_rag(
    query="Summarize the key findings",
    user="trustgraph",
    collection="research-papers",
    doc_limit=5
)
print(response)
```

### `embeddings(self, texts)`

Bir veya daha fazla metin için vektör gömme işlemleri gerçekleştirin.

Metinleri, semantik
arama ve benzerlik karşılaştırması için uygun olan yoğun vektör gösterimlerine dönüştürür.

**Argümanlar:**

`texts`: Gömülecek giriş metinlerinin listesi

**Döndürür:** list[list[list[float]]]: Vektör gömmeleri, her giriş metni için bir set.

**Örnek:**

```python
flow = api.flow().id("default")
vectors = flow.embeddings(["quantum computing"])
print(f"Embedding dimension: {len(vectors[0][0])}")
```

### `generate_descriptor(self, sample, data_type, schema_name, options=None)`

Belirli bir şemaya yapılandırılmış veri eşlemesi için bir tanımlayıcı oluşturun.

**Argümanlar:**

`sample`: Analiz edilecek veri örneği (metin içeriği)
`data_type`: Veri türü (csv, json, xml)
`schema_name`: Tanımlayıcı oluşturmak için hedef şema adı
`options`: İsteğe bağlı parametreler (örneğin, CSV için ayraç)

**Döndürür:** tanımlayıcı ve meta verileri içeren sözlük

### `graph_embeddings_query(self, text, user, collection, limit=10)`

Anlamsal benzerlik kullanarak bilgi grafiği varlıklarını sorgulayın.

Vektör gömüler kullanarak, giriş metnine anlamsal olarak
benzer açıklamaları olan bilgi grafiğindeki varlıkları bulur.

**Argümanlar:**

`text`: Anlamsal arama için sorgu metni
`user`: Kullanıcı/keyspace tanımlayıcısı
`collection`: Koleksiyon tanımlayıcısı
`limit`: Maksimum sonuç sayısı (varsayılan: 10)

**Döndürür:** dict: Benzer varlıklarla birlikte sorgu sonuçları

**Örnek:**

```python
flow = api.flow().id("default")
results = flow.graph_embeddings_query(
    text="physicist who discovered radioactivity",
    user="trustgraph",
    collection="scientists",
    limit=5
)
# results contains {"entities": [{"entity": {...}, "score": 0.95}, ...]}
```

### `graph_rag(self, query, user='trustgraph', collection='default', entity_limit=50, triple_limit=30, max_subgraph_size=150, max_path_length=2)`

Grafik tabanlı, Bilgiyle Zenginleştirilmiş Üretim (RAG) sorgusunu çalıştırın.

Grafik RAG, ilgili bağlamı bulmak için bilgi grafiği yapısını kullanarak, varlık ilişkilerini
izleyerek ve ardından bir LLM kullanarak bir yanıt oluşturur.

**Argümanlar:**

`query`: Doğal dil sorgusu
`user`: Kullanıcı/veri kümesi tanımlayıcısı (varsayılan: "trustgraph")
`collection`: Koleksiyon tanımlayıcısı (varsayılan: "default")
`entity_limit`: Alınacak maksimum varlık sayısı (varsayılan: 50)
`triple_limit`: Her varlık için maksimum üçlü sayısı (varsayılan: 30)
`max_subgraph_size`: Alt grafik içindeki maksimum toplam üçlü sayısı (varsayılan: 150)
`max_path_length`: Maksimum gezinme derinliği (varsayılan: 2)

**Döndürür:** str: Grafik bağlamını içeren oluşturulmuş yanıt

**Örnek:**

```python
flow = api.flow().id("default")
response = flow.graph_rag(
    query="Tell me about Marie Curie's discoveries",
    user="trustgraph",
    collection="scientists",
    entity_limit=20,
    max_path_length=3
)
print(response)
```

### `load_document(self, document, id=None, metadata=None, user=None, collection=None)`

Bir belgeyi işleme için yükleyin.

Bir belgeyi (PDF, DOCX, resimler, vb.) çıkarma ve
iş akışının belge işleme hattı aracılığıyla işlenmesi için yükleyin.

**Argümanlar:**

`document`: Belge içeriği (bayt olarak)
`id`: İsteğe bağlı belge tanımlayıcısı (None ise otomatik olarak oluşturulur)
`metadata`: İsteğe bağlı meta veri (Üçlüler listesi veya emit yöntemine sahip nesne)
`user`: Kullanıcı/veri alanı tanımlayıcısı (isteğe bağlı)
`collection`: Koleksiyon tanımlayıcısı (isteğe bağlı)

**Döndürür:** dict: İşleme yanıtı

**Hatalar:**

`RuntimeError`: Meta veri sağlanırsa ancak kimlik belirtilmezse

**Örnek:**

```python
flow = api.flow().id("default")

# Load a PDF document
with open("research.pdf", "rb") as f:
    result = flow.load_document(
        document=f.read(),
        id="research-001",
        user="trustgraph",
        collection="papers"
    )
```

### `load_text(self, text, id=None, metadata=None, charset='utf-8', user=None, collection=None)`

İşlenmek üzere metin içeriğini yükleyin.

Metin içeriğini, akışın metin işleme hattı aracılığıyla çıkarma ve işleme için yükler.


**Argümanlar:**

`text`: Metin içeriği (bayt olarak)
`id`: İsteğe bağlı belge tanımlayıcısı (None ise otomatik olarak oluşturulur)
`metadata`: İsteğe bağlı meta veri (Üçlüler listesi veya emit yöntemine sahip nesne)
`charset`: Karakter kodlaması (varsayılan: "utf-8")
`user`: Kullanıcı/keyspace tanımlayıcısı (isteğe bağlı)
`collection`: Koleksiyon tanımlayıcısı (isteğe bağlı)

**Döndürür:** dict: İşleme yanıtı

**Hatalar:**

`RuntimeError`: Meta veri sağlanmış ancak id belirtilmemişse

**Örnek:**

```python
flow = api.flow().id("default")

# Load text content
text_content = b"This is the document content..."
result = flow.load_text(
    text=text_content,
    id="text-001",
    charset="utf-8",
    user="trustgraph",
    collection="documents"
)
```

### `mcp_tool(self, name, parameters={})`

Bir Model Bağlam Protokolü (MCP) aracını çalıştırın.

MCP araçları, ajanlar ve iş akışları için genişletilebilir işlevsellik sağlar,
ve harici sistemler ve hizmetlerle entegrasyon imkanı sunar.

**Argümanlar:**

`name`: Araç adı/tanımlayıcı
`parameters`: Araç parametreleri sözlüğü (varsayılan: {})

**Döndürür:** str veya dict: Aracın çalıştırma sonucu

**Hatalar:**

`ProtocolException`: Yanıt formatı geçersizse

**Örnek:**

```python
flow = api.flow().id("default")

# Execute a tool
result = flow.mcp_tool(
    name="search-web",
    parameters={"query": "latest AI news", "limit": 5}
)
```

### `nlp_query(self, question, max_results=100)`

Doğal bir dil sorusunu GraphQL sorgusuna dönüştürün.

**Argümanlar:**

`question`: Doğal dil sorusu
`max_results`: Döndürülecek maksimum sonuç sayısı (varsayılan: 100)

**Döndürür:** graphql_query, variables, detected_schemas, confidence alanlarını içeren bir sözlük.

### `prompt(self, id, variables)`

Değişken yerleştirmesiyle bir istem şablonunu çalıştırın.

İstek şablonları, dinamik değişkenlerle yeniden kullanılabilir istek kalıplarına olanak tanır ve tutarlı istek mühendisliği için kullanışlıdır.


**Argümanlar:**

`id`: İstek şablonu tanımlayıcısı
`variables`: Değişken adı ile değer eşlemelerinin sözlüğü

**Döndürür:** str veya dict: Oluşturulmuş istek sonucu (metin veya yapılandırılmış nesne)

**Hatalar:**

`ProtocolException`: Yanıt formatı geçersizse

**Örnek:**

```python
flow = api.flow().id("default")

# Text template
result = flow.prompt(
    id="summarize-template",
    variables={"topic": "quantum computing", "length": "brief"}
)

# Structured template
result = flow.prompt(
    id="extract-entities",
    variables={"text": "Marie Curie won Nobel Prizes"}
)
```

### `request(self, path, request)`

Bu işlem örneği üzerinden bir hizmet isteği oluşturun.

**Parametreler:**

`path`: Hizmet yolu (örneğin, "service/text-completion")
`request`: İstek yükü sözlüğü

**Dönüş:** dict: Hizmet yanıtı

### `row_embeddings_query(self, text, schema_name, user='trustgraph', collection='default', index_name=None, limit=10)`

İndekslenmiş alanlar üzerinde semantik benzerlik kullanarak satır verilerini sorgulayın.

İndeksli alan değerlerinin, vektör gömüler kullanılarak, giriş metnine anlamsal olarak benzer olduğu satırları bulur. Bu, yapılandırılmış veriler üzerinde bulanık/anlamsal eşleşme sağlar.

**Argümanlar:**



`text`: Anlamsal arama için sorgu metni
`schema_name`: İçinde arama yapılacak şema adı
`user`: Kullanıcı/veri tabanı tanımlayıcısı (varsayılan: "trustgraph")
`collection`: Koleksiyon tanımlayıcısı (varsayılan: "default")
`index_name`: Aramayı belirli bir indekse sınırlamak için isteğe bağlı indeks adı
`limit`: Maksimum sonuç sayısı (varsayılan: 10)

**Döndürür:** dict: Eşleşmeleri içeren, index_name, index_value, text ve score alanlarını içeren sorgu sonuçları

**Örnek:**

```python
flow = api.flow().id("default")

# Search for customers by name similarity
results = flow.row_embeddings_query(
    text="John Smith",
    schema_name="customers",
    user="trustgraph",
    collection="sales",
    limit=5
)

# Filter to specific index
results = flow.row_embeddings_query(
    text="machine learning engineer",
    schema_name="employees",
    index_name="job_title",
    limit=10
)
```

### `rows_query(self, query, user='trustgraph', collection='default', variables=None, operation_name=None)`

Bilgi grafiğindeki yapılandırılmış satırlara karşı bir GraphQL sorgusu çalıştırın.

GraphQL sözdizimini kullanarak yapılandırılmış verileri sorgular, bu sayede filtreleme, toplama ve ilişki taraması gibi karmaşık sorgular
mümkün hale gelir.

**Parametreler:**

`query`: GraphQL sorgu dizesi
`user`: Kullanıcı/veri alanı tanımlayıcısı (varsayılan: "trustgraph")
`collection`: Koleksiyon tanımlayıcısı (varsayılan: "default")
`variables`: İsteğe bağlı sorgu değişkenleri sözlüğü
`operation_name`: Çoklu işlem belgeleri için isteğe bağlı işlem adı

**Döndürür:** dict: 'data', 'errors' ve/veya 'extensions' alanlarına sahip GraphQL yanıtı

**Hatalar:**

`ProtocolException`: Sistem düzeyinde bir hata oluşursa

**Örnek:**

```python
flow = api.flow().id("default")

# Simple query
query = '''
{
  scientists(limit: 10) {
    name
    field
    discoveries
  }
}
'''
result = flow.rows_query(
    query=query,
    user="trustgraph",
    collection="scientists"
)

# Query with variables
query = '''
query GetScientist($name: String!) {
  scientists(name: $name) {
    name
    nobelPrizes
  }
}
'''
result = flow.rows_query(
    query=query,
    variables={"name": "Marie Curie"}
)
```

### `schema_selection(self, sample, options=None)`

Bir veri örneği için, istem analizi kullanarak eşleşen şemaları seçin.

**Argümanlar:**

`sample`: Analiz edilecek veri örneği (metin içeriği)
`options`: İsteğe bağlı parametreler

**Döndürür:** schema_matches dizisi ve meta veriler içeren bir sözlük.

### `structured_query(self, question, user='trustgraph', collection='default')`

Yapılandırılmış verilere karşı doğal dil sorgusu yürütün.
NLP sorgu dönüşümü ve GraphQL yürütmeyi birleştirir.

**Argümanlar:**

`question`: Doğal dil sorgusu
`user`: Cassandra keyspace tanımlayıcısı (varsayılan: "trustgraph")
`collection`: Veri koleksiyonu tanımlayıcısı (varsayılan: "default")

**Döndürür:** veri ve isteğe bağlı hataları içeren bir sözlük.

### `text_completion(self, system, prompt)`

İş akışının LLM'sini kullanarak metin tamamlama işlemini yürütün.

**Argümanlar:**

`system`: Yardımcının davranışını tanımlayan sistem istemi
`prompt`: Kullanıcı istemi/sorusu

**Döndürür:** str: Oluşturulan yanıt metni

**Örnek:**

```python
flow = api.flow().id("default")
response = flow.text_completion(
    system="You are a helpful assistant",
    prompt="What is quantum computing?"
)
print(response)
```

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=10000)`

Desen eşleştirme kullanarak bilgi grafiği üçlülerini sorgulayın.

Belirtilen konu, yüklem ve/veya
nesne desenlerine uyan RDF üçlülerini arar. Belirtilmemiş parametreler, joker karakter olarak işlev görür.

**Argümanlar:**

`s`: Konu URI'si (isteğe bağlı, joker karakter için None kullanın)
`p`: Yüklem URI'si (isteğe bağlı, joker karakter için None kullanın)
`o`: Nesne URI'si veya Literal (isteğe bağlı, joker karakter için None kullanın)
`user`: Kullanıcı/veri tabanı tanımlayıcısı (isteğe bağlı)
`collection`: Koleksiyon tanımlayıcısı (isteğe bağlı)
`limit`: Döndürülecek maksimum sonuç sayısı (varsayılan: 10000)

**Döndürür:** list[Triple]: Eşleşen Triple nesnelerinin listesi

**Hatalar:**

`RuntimeError`: s veya p bir Uri değilse veya o bir Uri/Literal değilse

**Örnek:**

```python
from trustgraph.knowledge import Uri, Literal

flow = api.flow().id("default")

# Find all triples about a specific subject
triples = flow.triples_query(
    s=Uri("http://example.org/person/marie-curie"),
    user="trustgraph",
    collection="scientists"
)

# Find all instances of a specific relationship
triples = flow.triples_query(
    p=Uri("http://example.org/ontology/discovered"),
    limit=100
)
```


--

## `AsyncFlow`

```python
from trustgraph.api import AsyncFlow
```

REST API'sini kullanan asenkron akış yönetimi istemcisi.

Listeleme,
akışları başlatma, durdurma ve akış sınıf tanımlarını yönetme gibi, async/await tabanlı akış yönetimi işlemleri sağlar. Ayrıca, ajanlar, RAG ve sorgular gibi akış kapsamlı hizmetlere, akış olmayan REST uç noktaları aracılığıyla erişim sağlar.

Not: Akış desteği için, AsyncSocketClient'ı kullanın.

### Yöntemler

### Yöntemler

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Asenkron akış istemciyi başlat.

**Argümanlar:**

`url`: TrustGraph API'si için temel URL
`timeout`: İstek zaman aşımı (saniye cinsinden)
`token`: Kimlik doğrulama için isteğe bağlı taşıyıcı belirteci

### `aclose(self) -> None`

Asenkron istemciyi kapatın ve kaynakları temizleyin.

Not: Temizleme, aiohttp oturum bağlam yöneticileri tarafından otomatik olarak yapılır.
Bu yöntem, diğer asenkron istemcilerle tutarlılık sağlamak için sağlanmıştır.

### `delete_class(self, class_name: str)`

Bir akış sınıf tanımını silin.

Sistemden bir akış sınıf şablonunu kaldırır. Çalışan akış örneklerini etkilemez.


**Argümanlar:**

`class_name`: Silinecek akış sınıf adı

**Örnek:**

```python
async_flow = await api.async_flow()

# Delete a flow class
await async_flow.delete_class("old-flow-class")
```

### `get(self, id: str) -> Dict[str, Any]`

Akış tanımını al.

Sınıf adı,
açıklaması ve parametreleri dahil olmak üzere eksiksiz akış yapılandırmasını alır.

**Argümanlar:**

`id`: Akış tanımlayıcısı

**Döndürür:** dict: Akış tanımı nesnesi

**Örnek:**

```python
async_flow = await api.async_flow()

# Get flow definition
flow_def = await async_flow.get("default")
print(f"Flow class: {flow_def.get('class-name')}")
print(f"Description: {flow_def.get('description')}")
```

### `get_class(self, class_name: str) -> Dict[str, Any]`

Akış sınıfı tanımını alın.

Bir akış sınıfının, yapılandırma şeması ve hizmet bağlamaları dahil olmak üzere, temel tasarım tanımını alır.


**Parametreler:**

`class_name`: Akış sınıfı adı

**Döndürür:** dict: Akış sınıfı tanım nesnesi

**Örnek:**

```python
async_flow = await api.async_flow()

# Get flow class definition
class_def = await async_flow.get_class("default")
print(f"Services: {class_def.get('services')}")
```

### `id(self, flow_id: str)`

Asenkron akış örneği istemciyi alın.

Belirli bir akışın hizmetleriyle etkileşim kurmak için bir istemci döndürür
(ajan, RAG, sorgular, gömme vb.).

**Argümanlar:**

`flow_id`: Akış tanımlayıcısı

**Döndürür:** AsyncFlowInstance: Akışa özel işlemler için istemci

**Örnek:**

```python
async_flow = await api.async_flow()

# Get flow instance
flow = async_flow.id("default")

# Use flow services
result = await flow.graph_rag(
    query="What is TrustGraph?",
    user="trustgraph",
    collection="default"
)
```

### `list(self) -> List[str]`

Tüm akış tanımlayıcılarını listele.

Sistemde şu anda dağıtılmış olan tüm akışların kimliklerini alır.

**Döndürür:** list[str]: Akış tanımlayıcılarının listesi

**Örnek:**

```python
async_flow = await api.async_flow()

# List all flows
flows = await async_flow.list()
print(f"Available flows: {flows}")
```

### `list_classes(self) -> List[str]`

Tüm akış sınıfı adlarını listele.

Sistemdeki mevcut tüm akış sınıfı (şablon) adlarını alır.

**Döndürür:** list[str]: Akış sınıfı adlarının listesi

**Örnek:**

```python
async_flow = await api.async_flow()

# List available flow classes
classes = await async_flow.list_classes()
print(f"Available flow classes: {classes}")
```

### `put_class(self, class_name: str, definition: Dict[str, Any])`

Bir akış sınıf tanımını oluşturun veya güncelleyin.

Akışları örneklemek için kullanılabilecek bir akış sınıf şablonunu saklar.

**Argümanlar:**

`class_name`: Akış sınıf adı
`definition`: Akış sınıf tanımı nesnesi

**Örnek:**

```python
async_flow = await api.async_flow()

# Create a custom flow class
class_def = {
    "services": {
        "agent": {"module": "agent", "config": {...}},
        "graph-rag": {"module": "graph-rag", "config": {...}}
    }
}
await async_flow.put_class("custom-flow", class_def)
```

### `request(self, path: str, request_data: Dict[str, Any]) -> Dict[str, Any]`

Gateway API'sine asenkron HTTP POST isteği gönderin.

TrustGraph API'sine kimlik doğrulaması yapılmış istekler göndermek için kullanılan iç metot.

**Argümanlar:**

`path`: API uç noktası yolu (temel URL'ye göre)
`request_data`: İstek yükü sözlüğü

**Döndürür:** dict: API'den gelen yanıt nesnesi

**Hatalar:**

`ProtocolException`: HTTP durum kodu 200 değilse veya yanıt geçerli bir JSON değilse
`ApplicationException`: API bir hata yanıtı döndürürse

### `start(self, class_name: str, id: str, description: str, parameters: Dict | None = None)`

Yeni bir akış örneği başlatın.

Belirtilen parametrelerle, bir akış sınıf tanımından bir akış oluşturur ve başlatır.


**Argümanlar:**

`class_name`: Oluşturulacak akış sınıfının adı
`id`: Yeni akış örneği için tanımlayıcı
`description`: Akışın insan tarafından okunabilir açıklaması
`parameters`: Akış için isteğe bağlı yapılandırma parametreleri

**Örnek:**

```python
async_flow = await api.async_flow()

# Start a flow from a class
await async_flow.start(
    class_name="default",
    id="my-flow",
    description="Custom flow instance",
    parameters={"model": "claude-3-opus"}
)
```

### `stop(self, id: str)`

Çalışan bir akışı durdur.

Bir akış örneğini durdurur ve kaldırır, böylece kaynakları serbest bırakılır.

**Argümanlar:**

`id`: Durdurulacak akış tanımlayıcısı

**Örnek:**

```python
async_flow = await api.async_flow()

# Stop a flow
await async_flow.stop("my-flow")
```


--

## `AsyncFlowInstance`

```python
from trustgraph.api import AsyncFlowInstance
```

Asenkron akış örneği istemcisi.

Ajanlar,
RAG sorguları, gömülme işlemleri ve grafik sorguları dahil olmak üzere akış kapsamındaki hizmetlere asenkron/bekleme erişimi sağlar. Tüm işlemler, eksiksiz
yanıtları (akışsız) döndürür.

Not: Akış desteği için, AsyncSocketFlowInstance'ı kullanın.

### Yöntemler

### `__init__(self, flow: trustgraph.api.async_flow.AsyncFlow, flow_id: str)`

Asenkron akış örneğini başlatır.

**Argümanlar:**

`flow`: Üst düzey AsyncFlow istemcisi
`flow_id`: Akış tanımlayıcısı

### `agent(self, question: str, user: str, state: Dict | None = None, group: str | None = None, history: List | None = None, **kwargs: Any) -> Dict[str, Any]`

Bir ajan işlemini (akışsız) yürütür.

Bir soruyu yanıtlamak için bir ajan çalıştırır, isteğe bağlı konuşma durumu ve
geçmişi ile. Ajan işleme işlemini tamamladıktan sonra eksiksiz yanıtı döndürür.


Not: Bu yöntem akışı desteklemez. Gerçek zamanlı ajan düşünceleri ve
gözlemler için, AsyncSocketFlowInstance.agent() yöntemini kullanın.

**Argümanlar:**

`question`: Kullanıcı sorusu veya talimatı
`user`: Kullanıcı tanımlayıcısı
`state`: İsteğe bağlı, konuşma bağlamı için durum sözlüğü
`group`: İsteğe bağlı, oturum yönetimi için grup tanımlayıcısı
`history`: İsteğe bağlı, konuşma geçmişi listesi
`**kwargs`: Ek, hizmete özgü parametreler

**Döndürür:** dict: Cevap ve meta verileri içeren eksiksiz ajan yanıtı

**Örnek:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Execute agent
result = await flow.agent(
    question="What is the capital of France?",
    user="trustgraph"
)
print(f"Answer: {result.get('response')}")
```

### `document_rag(self, query: str, user: str, collection: str, doc_limit: int = 10, **kwargs: Any) -> str`

Belge tabanlı RAG sorgusunu (akışsız) çalıştırın.

Belge gömüler kullanarak, bilgi artırılmış metin oluşturma işlemini gerçekleştirir.
Anlamsal arama yoluyla ilgili belge parçalarını alır ve ardından alınan belgelerle
ilişkili bir yanıt oluşturur. Tam yanıtı döndürür.

Not: Bu yöntem akışı desteklemez. Akışlı RAG yanıtları için,
bunun yerine AsyncSocketFlowInstance.document_rag() yöntemini kullanın.

**Argümanlar:**

`query`: Kullanıcı sorgusu metni
`user`: Kullanıcı kimliği
`collection`: Belgeleri içeren koleksiyon kimliği
`doc_limit`: Alınacak maksimum belge parçası sayısı (varsayılan: 10)
`**kwargs`: Ek hizmete özgü parametreler

**Döndürür:** str: Belge verilerine dayalı olarak oluşturulan tam yanıt

**Örnek:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Query documents
response = await flow.document_rag(
    query="What does the documentation say about authentication?",
    user="trustgraph",
    collection="docs",
    doc_limit=5
)
print(response)
```

### `embeddings(self, texts: list, **kwargs: Any)`

Girdi metinleri için gömme (embedding) oluşturur.

Metinleri, akışın yapılandırılmış gömme modelini kullanarak sayısal vektör gösterimlerine dönüştürür. Anlamsal arama ve benzerlik
karşılaştırmaları için kullanışlıdır.


**Argümanlar:**

`texts`: Gömülecek girdi metinlerinin listesi
`**kwargs`: Ek hizmete özgü parametreler

**Döndürür:** dict: Gömme vektörlerini içeren yanıt

**Örnek:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Generate embeddings
result = await flow.embeddings(texts=["Sample text to embed"])
vectors = result.get("vectors")
print(f"Embedding dimension: {len(vectors[0][0])}")
```

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any)`

Anlamsal varlık araması için grafik gömme verilerini sorgular.

Varlıkların anlamsal olarak aranmasını, grafik varlık gömmeleri üzerinde gerçekleştirerek, giriş metnine en uygun varlıkları bulur. Benzerliğe göre sıralanmış varlıkları döndürür.


**Argümanlar:**

`text`: Anlamsal arama için sorgu metni
`user`: Kullanıcı kimliği
`collection`: Grafik gömmelerini içeren koleksiyon kimliği
`limit`: Döndürülecek maksimum sonuç sayısı (varsayılan: 10)
`**kwargs`: Ek hizmete özel parametreler

**Döndürür:** dict: Sıralanmış varlık eşleşmelerini ve benzerlik puanlarını içeren yanıt

**Örnek:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Find related entities
results = await flow.graph_embeddings_query(
    text="machine learning algorithms",
    user="trustgraph",
    collection="tech-kb",
    limit=5
)

for entity in results.get("entities", []):
    print(f"{entity['name']}: {entity['score']}")
```

### `graph_rag(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, **kwargs: Any) -> str`

Grafik tabanlı RAG sorgusunu (akışsız) çalıştırın.

Bilgi grafi veri kullanarak, bilgiyle zenginleştirilmiş metin üretimi gerçekleştirir.
İlgili varlıkları ve bunların ilişkilerini belirler, ardından grafiğin yapısına dayalı olarak bir
yanıt oluşturur. Tam yanıtı döndürür.

Not: Bu yöntem akışı desteklemez. Akışlı RAG yanıtları için, bunun yerine AsyncSocketFlowInstance.graph_rag() kullanın.


**Argümanlar:**

`query`: Kullanıcı sorgusu metni
`user`: Kullanıcı kimliği
`collection`: Bilgi grafiğini içeren koleksiyon kimliği
`max_subgraph_size`: Her alt grafik için maksimum üçlü sayısı (varsayılan: 1000)
`max_subgraph_count`: Alınacak maksimum alt grafik sayısı (varsayılan: 5)
`max_entity_distance`: Varlık genişletmesi için maksimum grafik mesafesi (varsayılan: 3)
`**kwargs`: Ek hizmete özgü parametreler

**Döndürür:** str: Grafik verilerine dayalı olarak oluşturulan tam yanıt

**Örnek:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Query knowledge graph
response = await flow.graph_rag(
    query="What are the relationships between these entities?",
    user="trustgraph",
    collection="medical-kb",
    max_subgraph_count=3
)
print(response)
```

### `request(self, service: str, request_data: Dict[str, Any]) -> Dict[str, Any]`

Bir akış kapsamındaki bir hizmete istek gönderin.

Bu akış örneği içindeki hizmetleri çağırmak için kullanılan iç metot.

**Argümanlar:**

`service`: Hizmet adı (örneğin, "agent", "graph-rag", "triples")
`request_data`: Hizmet isteği yükü

**Döndürür:** dict: Hizmet yanıt nesnesi

**Hatalar:**

`ProtocolException`: İstek başarısız olursa veya yanıt geçersizse
`ApplicationException`: Hizmet bir hata döndürürse

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs: Any)`

Yapılandırılmış veriler üzerinde semantik arama için satır gömme vektörlerini sorgular.

Satır indeks gömme vektörleri üzerinde semantik arama gerçekleştirir ve giriş metnine en benzer indeksli alan değerlerine sahip satırları bulur. Yapılandırılmış veriler üzerinde bulanık/semantik eşleşme sağlar.


**Argümanlar:**


`text`: Semantik arama için sorgu metni
`schema_name`: Arama yapılacak şema adı
`user`: Kullanıcı kimliği (varsayılan: "trustgraph")
`collection`: Koleksiyon kimliği (varsayılan: "default")
`index_name`: Aramayı belirli bir indekse sınırlamak için isteğe bağlı indeks adı
`limit`: Döndürülecek maksimum sonuç sayısı (varsayılan: 10)
`**kwargs`: Ek hizmete özgü parametreler

**Döndürür:** dict: index_name, index_value, text ve score ile eşleşmeleri içeren yanıt

**Örnek:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Search for customers by name similarity
results = await flow.row_embeddings_query(
    text="John Smith",
    schema_name="customers",
    user="trustgraph",
    collection="sales",
    limit=5
)

for match in results.get("matches", []):
    print(f"{match['index_name']}: {match['index_value']} (score: {match['score']})")
```

### `rows_query(self, query: str, user: str, collection: str, variables: Dict | None = None, operation_name: str | None = None, **kwargs: Any)`

Saklanan satırları kullanarak bir GraphQL sorgusu çalıştırın.

GraphQL sözdizimini kullanarak yapılandırılmış veri satırlarını sorgular. Değişkenler ve adlandırılmış işlemler içeren karmaşık
sorguları destekler.

**Argümanlar:**

`query`: GraphQL sorgu dizesi
`user`: Kullanıcı tanımlayıcısı
`collection`: Satırları içeren koleksiyon tanımlayıcısı
`variables`: İsteğe bağlı GraphQL sorgu değişkenleri
`operation_name`: Çoklu işlem sorguları için isteğe bağlı işlem adı
`**kwargs`: Ek hizmete özgü parametreler

**Döndürür:** dict: Veri ve/veya hataları içeren GraphQL yanıtı

**Örnek:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Execute GraphQL query
query = '''
    query GetUsers($status: String!) {
        users(status: $status) {
            id
            name
            email
        }
    }
'''

result = await flow.rows_query(
    query=query,
    user="trustgraph",
    collection="users",
    variables={"status": "active"}
)

for user in result.get("data", {}).get("users", []):
    print(f"{user['name']}: {user['email']}")
```

### `text_completion(self, system: str, prompt: str, **kwargs: Any) -> str`

Metin tamamlama oluşturun (akış olmadan).

Bir sistem istemi ve kullanıcı istemi verildiğinde, bir LLM'den metin yanıtı oluşturur.
Tam yanıt metnini döndürür.

Not: Bu yöntem akışı desteklemez. Akışlı metin oluşturma için,
bunun yerine AsyncSocketFlowInstance.text_completion() yöntemini kullanın.

**Argümanlar:**

`system`: LLM'nin davranışını tanımlayan sistem istemi
`prompt`: Kullanıcı istemi veya sorusu
`**kwargs`: Ek hizmete özgü parametreler

**Döndürür:** str: Tam oluşturulmuş metin yanıtı

**Örnek:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Generate text
response = await flow.text_completion(
    system="You are a helpful assistant.",
    prompt="Explain quantum computing in simple terms."
)
print(response)
```

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=100, **kwargs: Any)`

Desen eşleştirme kullanarak RDF üçlülerini sorgulayın.

Belirtilen konu, yüklem ve/veya
nesne desenlerine uyan üçlüleri arar. Desenler, herhangi bir değeri eşleştirmek için "None" değerini joker karakter olarak kullanır.

**Argümanlar:**

`s`: Konu deseni (joker karakter için "None")
`p`: Yüklem deseni (joker karakter için "None")
`o`: Nesne deseni (joker karakter için "None")
`user`: Kullanıcı kimliği (tüm kullanıcılar için "None")
`collection`: Koleksiyon kimliği (tüm koleksiyonlar için "None")
`limit`: Döndürülecek maksimum üçlü sayısı (varsayılan: 100)
`**kwargs`: Ek hizmete özgü parametreler

**Döndürür:** dict: Eşleşen üçlüleri içeren yanıt

**Örnek:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Find all triples with a specific predicate
results = await flow.triples_query(
    p="knows",
    user="trustgraph",
    collection="social",
    limit=50
)

for triple in results.get("triples", []):
    print(f"{triple['s']} knows {triple['o']}")
```


--

## `SocketClient`

```python
from trustgraph.api import SocketClient
```

Akış işlemleri için senkron WebSocket istemcisi.

WebSocket tabanlı TrustGraph hizmetlerine senkron bir arayüz sağlar,
kullanımı kolaylaştırmak için senkron oluşturucularla asenkron WebSocket kütüphanesini sarar.
Ajanlardan gelen akış yanıtlarını, RAG sorgularını ve metin tamamlama işlemlerini destekler.

Not: Bu, asenkron WebSocket işlemlerinin etrafında oluşturulmuş bir senkron katmandır.
Gerçek asenkron destek için AsyncSocketClient'ı kullanın.

### Yöntemler

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Senkron WebSocket istemcisini başlatın.

**Argümanlar:**

`url`: TrustGraph API'si için temel URL (HTTP/HTTPS, WS/WSS'ye dönüştürülecektir)
`timeout`: Saniyeler cinsinden WebSocket zaman aşımı
`token`: İsteğe bağlı kimlik doğrulama için taşıyıcı belirteci

### `close(self) -> None`

WebSocket bağlantılarını kapatın.

Not: Temizleme, asenkron kodda bağlam yöneticileri tarafından otomatik olarak yapılır.

### `flow(self, flow_id: str) -> 'SocketFlowInstance'`

WebSocket akış işlemleri için bir akış örneği alın.

**Argümanlar:**

`flow_id`: Akış tanımlayıcısı

**Döndürür:** SocketFlowInstance: Akış yöntemleri içeren akış örneği

**Örnek:**

```python
socket = api.socket()
flow = socket.flow("default")

# Stream agent responses
for chunk in flow.agent(question="Hello", user="trustgraph", streaming=True):
    print(chunk.content, end='', flush=True)
```


--

## `SocketFlowInstance`

```python
from trustgraph.api import SocketFlowInstance
```

Akış işlemleri için senkron WebSocket akışı örneği.

REST FlowInstance ile aynı arayüzü sağlar, ancak gerçek zamanlı yanıtlar için WebSocket tabanlı
akış desteği sunar. Tüm yöntemler, kademeli sonuç teslimini etkinleştirmek için isteğe bağlı
`streaming` parametresini destekler.

### Yöntemler

### `__init__(self, client: trustgraph.api.socket_client.SocketClient, flow_id: str) -> None`

Soket akışı örneğini başlatır.

**Argümanlar:**

`client`: Üst SoketClient
`flow_id`: Akış tanımlayıcısı

### `agent(self, question: str, user: str, state: Dict[str, Any] | None = None, group: str | None = None, history: List[Dict[str, Any]] | None = None, streaming: bool = False, **kwargs: Any) -> Dict[str, Any] | Iterator[trustgraph.api.types.StreamingChunk]`

Akış desteği ile bir ajan işlemi gerçekleştirin.

Ajanlar, araç kullanımıyla çok aşamalı akıl yürütme yapabilir. Bu yöntem, streaming=False olsa bile, her zaman
akış parçaları (düşünceler, gözlemler, cevaplar) döndürür, böylece ajanın akıl yürütme süreci gösterilir.


**Argümanlar:**

`question`: Kullanıcı sorusu veya talimatı
`user`: Kullanıcı kimliği
`state`: Durumlu konuşmalar için isteğe bağlı durum sözlüğü
`group`: Çok kullanıcılı bağlamlar için isteğe bağlı grup kimliği
`history`: İsteğe bağlı olarak mesaj sözlüklerinin listesi olarak konuşma geçmişi
`streaming`: Akış modunu etkinleştir (varsayılan: False)
`**kwargs`: Ajan hizmetine iletilen ek parametreler

**Döndürür:** Iterator[StreamingChunk]: Ajanın düşüncelerinin, gözlemlerinin ve cevaplarının akışı

**Örnek:**

```python
socket = api.socket()
flow = socket.flow("default")

# Stream agent reasoning
for chunk in flow.agent(
    question="What is quantum computing?",
    user="trustgraph",
    streaming=True
):
    if isinstance(chunk, AgentThought):
        print(f"[Thinking] {chunk.content}")
    elif isinstance(chunk, AgentObservation):
        print(f"[Observation] {chunk.content}")
    elif isinstance(chunk, AgentAnswer):
        print(f"[Answer] {chunk.content}")
```

### `agent_explain(self, question: str, user: str, collection: str, state: Dict[str, Any] | None = None, group: str | None = None, history: List[Dict[str, Any]] | None = None, **kwargs: Any) -> Iterator[trustgraph.api.types.StreamingChunk | trustgraph.api.types.ProvenanceEvent]`

Açıklanabilirlik desteğiyle bir ajan işlemini yürütün.

Hem içerik parçalarını (AgentThought, AgentObservation, AgentAnswer)
ve kaynak olaylarını (ProvenanceEvent) akışa aktarır. Kaynak olayları, ayrıntılı bilgi
almak için ExplainabilityClient kullanılarak alınabilen URI'ler içerir
ve ajanın akıl yürütme süreci hakkında.

Ajan izi şunlardan oluşur:
Oturum: Başlangıç sorusu ve oturum meta verileri
Yinelemeler: Her düşünce/eylem/gözlem döngüsü
Sonuç: Nihai cevap

**Argümanlar:**

`question`: Kullanıcı sorusu veya talimatı
`user`: Kullanıcı tanımlayıcısı
`collection`: Kaynak depolama için koleksiyon tanımlayıcısı
`state`: Durumlu konuşmalar için isteğe bağlı durum sözlüğü
`group`: Çoklu kullanıcı bağlamları için isteğe bağlı grup tanımlayıcısı
`history`: İsteğe bağlı olarak mesaj sözlüklerinin listesi olarak konuşma geçmişi
`**kwargs`: Ajan hizmetine iletilen ek parametreler
`Yields`: 
`Union[StreamingChunk, ProvenanceEvent]`: Ajan parçaları ve kaynak olayları

**Örnek:**

```python
from trustgraph.api import Api, ExplainabilityClient, ProvenanceEvent
from trustgraph.api import AgentThought, AgentObservation, AgentAnswer

socket = api.socket()
flow = socket.flow("default")
explain_client = ExplainabilityClient(flow)

provenance_ids = []
for item in flow.agent_explain(
    question="What is the capital of France?",
    user="trustgraph",
    collection="default"
):
    if isinstance(item, AgentThought):
        print(f"[Thought] {item.content}")
    elif isinstance(item, AgentObservation):
        print(f"[Observation] {item.content}")
    elif isinstance(item, AgentAnswer):
        print(f"[Answer] {item.content}")
    elif isinstance(item, ProvenanceEvent):
        provenance_ids.append(item.explain_id)

# Fetch session trace after completion
if provenance_ids:
    trace = explain_client.fetch_agent_trace(
        provenance_ids[0],  # Session URI is first
        graph="urn:graph:retrieval",
        user="trustgraph",
        collection="default"
    )
```

### `document_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any) -> Dict[str, Any]`

Anlamlı benzerlik kullanarak belge parçalarını sorgulayın.

**Argümanlar:**

`text`: Anlamlı arama için sorgu metni
`user`: Kullanıcı/veri kümesi tanımlayıcısı
`collection`: Koleksiyon tanımlayıcısı
`limit`: Maksimum sonuç sayısı (varsayılan: 10)
`**kwargs`: Hizmete iletilen ek parametreler

**Dönüş:** dict: Eşleşen belge parçalarının chunk_id'leri ile birlikte sorgu sonuçları

**Örnek:**

```python
socket = api.socket()
flow = socket.flow("default")

results = flow.document_embeddings_query(
    text="machine learning algorithms",
    user="trustgraph",
    collection="research-papers",
    limit=5
)
# results contains {"chunks": [{"chunk_id": "...", "score": 0.95}, ...]}
```

### `document_rag(self, query: str, user: str, collection: str, doc_limit: int = 10, streaming: bool = False, **kwargs: Any) -> str | Iterator[str]`

Belge tabanlı RAG sorgusunu, isteğe bağlı olarak akış modunda çalıştırın.

İlgili belge parçalarını bulmak için vektör gömülmelerini kullanır, ardından bir LLM kullanarak
bir yanıt oluşturur. Akış modu, sonuçları kademeli olarak sunar.

**Argümanlar:**

`query`: Doğal dil sorgusu
`user`: Kullanıcı/veri kümesi tanımlayıcısı
`collection`: Koleksiyon tanımlayıcısı
`doc_limit`: Alınacak maksimum belge parçası sayısı (varsayılan: 10)
`streaming`: Akış modunu etkinleştir (varsayılan: False)
`**kwargs`: Hizmete iletilen ek parametreler

**Döndürür:** Union[str, Iterator[str]]: Tam yanıt veya metin parçalarının akışı

**Örnek:**

```python
socket = api.socket()
flow = socket.flow("default")

# Streaming document RAG
for chunk in flow.document_rag(
    query="Summarize the key findings",
    user="trustgraph",
    collection="research-papers",
    doc_limit=5,
    streaming=True
):
    print(chunk, end='', flush=True)
```

### `document_rag_explain(self, query: str, user: str, collection: str, doc_limit: int = 10, **kwargs: Any) -> Iterator[trustgraph.api.types.RAGChunk | trustgraph.api.types.ProvenanceEvent]`

Açıklanabilirlik desteğiyle belge tabanlı RAG sorgusunu çalıştırın.

Hem içerik parçalarını (RAGChunk) hem de kaynak olaylarını (ProvenanceEvent) akışa aktarır.
Kaynak olayları, yanıtın nasıl oluşturulduğuna dair ayrıntılı bilgi almak için ExplainabilityClient kullanılarak alınabilen URI'ler içerir.


Belge RAG izi şunlardan oluşur:
Soru: Kullanıcının sorgusu
Keşif: Belge deposundan alınan parçalar (parça_sayısı)
Sentez: Oluşturulan yanıt

**Argümanlar:**

`query`: Doğal dil sorgusu
`user`: Kullanıcı/keyspace tanımlayıcısı
`collection`: Koleksiyon tanımlayıcısı
`doc_limit`: Alınacak maksimum belge parçası sayısı (varsayılan: 10)
`**kwargs`: Hizmete iletilen ek parametreler
`Yields`: 
`Union[RAGChunk, ProvenanceEvent]`: İçerik parçaları ve kaynak olayları

**Örnek:**

```python
from trustgraph.api import Api, ExplainabilityClient, RAGChunk, ProvenanceEvent

socket = api.socket()
flow = socket.flow("default")
explain_client = ExplainabilityClient(flow)

for item in flow.document_rag_explain(
    query="Summarize the key findings",
    user="trustgraph",
    collection="research-papers",
    doc_limit=5
):
    if isinstance(item, RAGChunk):
        print(item.content, end='', flush=True)
    elif isinstance(item, ProvenanceEvent):
        # Fetch entity details
        entity = explain_client.fetch_entity(
            item.explain_id,
            graph=item.explain_graph,
            user="trustgraph",
            collection="research-papers"
        )
        print(f"Event: {entity}", file=sys.stderr)
```

### `embeddings(self, texts: list, **kwargs: Any) -> Dict[str, Any]`

Bir veya daha fazla metin için vektör gömme işlemleri gerçekleştirin.

**Argümanlar:**

`texts`: Gömülecek giriş metinlerinin listesi
`**kwargs`: Hizmete iletilen ek parametreler

**Döndürür:** dict: Vektörleri içeren (her giriş metni için bir set) yanıt

**Örnek:**

```python
socket = api.socket()
flow = socket.flow("default")

result = flow.embeddings(["quantum computing"])
vectors = result.get("vectors", [])
```

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any) -> Dict[str, Any]`

Anlamsal benzerlik kullanarak bilgi grafiği varlıklarını sorgulayın.

**Argümanlar:**

`text`: Anlamsal arama için sorgu metni
`user`: Kullanıcı/veri kümesi tanımlayıcısı
`collection`: Koleksiyon tanımlayıcısı
`limit`: Maksimum sonuç sayısı (varsayılan: 10)
`**kwargs`: Hizmete iletilen ek parametreler

**Dönüş:** dict: Benzer varlıklarla birlikte sorgu sonuçları

**Örnek:**

```python
socket = api.socket()
flow = socket.flow("default")

results = flow.graph_embeddings_query(
    text="physicist who discovered radioactivity",
    user="trustgraph",
    collection="scientists",
    limit=5
)
```

### `graph_rag(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, streaming: bool = False, **kwargs: Any) -> str | Iterator[str]`

İsteğe bağlı akışla, grafik tabanlı RAG sorgusunu çalıştırın.

İlgili bağlamı bulmak için bilgi grafiği yapısını kullanır, ardından
bir LLM kullanarak bir yanıt oluşturur. Akış modu, sonuçları kademeli olarak sunar.

**Argümanlar:**

`query`: Doğal dil sorgusu
`user`: Kullanıcı/veri kümesi tanımlayıcısı
`collection`: Koleksiyon tanımlayıcısı
`max_subgraph_size`: Alt grafikteki maksimum toplam üçlü sayısı (varsayılan: 1000)
`max_subgraph_count`: Maksimum alt grafik sayısı (varsayılan: 5)
`max_entity_distance`: Maksimum gezinme derinliği (varsayılan: 3)
`streaming`: Akış modunu etkinleştir (varsayılan: False)
`**kwargs`: Hizmete iletilen ek parametreler

**Döndürür:** Union[str, Iterator[str]]: Tam yanıt veya metin parçalarının akışı

**Örnek:**

```python
socket = api.socket()
flow = socket.flow("default")

# Streaming graph RAG
for chunk in flow.graph_rag(
    query="Tell me about Marie Curie",
    user="trustgraph",
    collection="scientists",
    streaming=True
):
    print(chunk, end='', flush=True)
```

### `graph_rag_explain(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, **kwargs: Any) -> Iterator[trustgraph.api.types.RAGChunk | trustgraph.api.types.ProvenanceEvent]`

Açıklanabilirlik desteğiyle grafik tabanlı RAG sorgusunu çalıştırın.

Hem içerik parçalarını (RAGChunk) hem de kaynak olaylarını (ProvenanceEvent) iletir.
Kaynak olayları, yanıtın nasıl oluşturulduğuna dair ayrıntılı bilgi almak için ExplainabilityClient kullanılarak alınabilen URI'ler içerir.


**Argümanlar:**

`query`: Doğal dil sorgusu
`user`: Kullanıcı/keyspace tanımlayıcısı
`collection`: Koleksiyon tanımlayıcısı
`max_subgraph_size`: Alt grafik içindeki maksimum toplam üçlü sayısı (varsayılan: 1000)
`max_subgraph_count`: Maksimum alt grafik sayısı (varsayılan: 5)
`max_entity_distance`: Maksimum gezinme derinliği (varsayılan: 3)
`**kwargs`: Hizmete iletilen ek parametreler
`Yields`: 
`Union[RAGChunk, ProvenanceEvent]`: İçerik parçaları ve kaynak olayları

**Örnek:**

```python
from trustgraph.api import Api, ExplainabilityClient, RAGChunk, ProvenanceEvent

socket = api.socket()
flow = socket.flow("default")
explain_client = ExplainabilityClient(flow)

provenance_ids = []
response_text = ""

for item in flow.graph_rag_explain(
    query="Tell me about Marie Curie",
    user="trustgraph",
    collection="scientists"
):
    if isinstance(item, RAGChunk):
        response_text += item.content
        print(item.content, end='', flush=True)
    elif isinstance(item, ProvenanceEvent):
        provenance_ids.append(item.provenance_id)

# Fetch explainability details
for prov_id in provenance_ids:
    entity = explain_client.fetch_entity(
        prov_id,
        graph="urn:graph:retrieval",
        user="trustgraph",
        collection="scientists"
    )
    print(f"Entity: {entity}")
```

### `mcp_tool(self, name: str, parameters: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]`

Bir Model Bağlam Protokolü (MCP) aracını çalıştırın.

**Argümanlar:**

`name`: Araç adı/tanımlayıcı
`parameters`: Araç parametreleri sözlüğü
`**kwargs`: Hizmete iletilen ek parametreler

**Döndürür:** dict: Aracın çalıştırma sonucu

**Örnek:**

```python
socket = api.socket()
flow = socket.flow("default")

result = flow.mcp_tool(
    name="search-web",
    parameters={"query": "latest AI news", "limit": 5}
)
```

### `prompt(self, id: str, variables: Dict[str, str], streaming: bool = False, **kwargs: Any) -> str | Iterator[str]`

İsteğe bağlı akışla bir istem şablonunu yürütün.

**Argümanlar:**

`id`: İstem şablonu tanımlayıcısı
`variables`: Değişken adı ile değer eşlemelerinin sözlüğü
`streaming`: Akış modunu etkinleştir (varsayılan: False)
`**kwargs`: Hizmete iletilen ek parametreler

**Döndürür:** Union[str, Iterator[str]]: Tam yanıt veya metin parçacıklarının akışı

**Örnek:**

```python
socket = api.socket()
flow = socket.flow("default")

# Streaming prompt execution
for chunk in flow.prompt(
    id="summarize-template",
    variables={"topic": "quantum computing", "length": "brief"},
    streaming=True
):
    print(chunk, end='', flush=True)
```

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs: Any) -> Dict[str, Any]`

İndekslenmiş alanlar üzerinde semantik benzerlik kullanarak sorgu satır verilerini alın.

Giriş metnine semantik olarak benzer olan, indekslenmiş alan değerlerine sahip satırları bulur, vektör gömme teknikleri kullanılarak. Bu, yapılandırılmış veriler üzerinde bulanık/semantik eşleşme
sağlar.


**Argümanlar:**

`text`: Anlamsal arama için sorgu metni
`schema_name`: İçinde arama yapılacak şema adı
`user`: Kullanıcı/veri tabanı tanımlayıcısı (varsayılan: "trustgraph")
`collection`: Koleksiyon tanımlayıcısı (varsayılan: "default")
`index_name`: Aramayı belirli bir indekse sınırlamak için isteğe bağlı indeks adı
`limit`: Maksimum sonuç sayısı (varsayılan: 10)
`**kwargs`: Hizmete iletilen ek parametreler

**Döndürür:** dict: Eşleşmeleri içeren, index_name, index_value, text ve score alanlarını içeren sorgu sonuçları

**Örnek:**

```python
socket = api.socket()
flow = socket.flow("default")

# Search for customers by name similarity
results = flow.row_embeddings_query(
    text="John Smith",
    schema_name="customers",
    user="trustgraph",
    collection="sales",
    limit=5
)

# Filter to specific index
results = flow.row_embeddings_query(
    text="machine learning engineer",
    schema_name="employees",
    index_name="job_title",
    limit=10
)
```

### `rows_query(self, query: str, user: str, collection: str, variables: Dict[str, Any] | None = None, operation_name: str | None = None, **kwargs: Any) -> Dict[str, Any]`

Yapılandırılmış satırlara karşı bir GraphQL sorgusu çalıştırın.

**Argümanlar:**

`query`: GraphQL sorgu dizesi
`user`: Kullanıcı/keyspace tanımlayıcısı
`collection`: Koleksiyon tanımlayıcısı
`variables`: İsteğe bağlı sorgu değişkenleri sözlüğü
`operation_name`: Çoklu işlem belgeleri için isteğe bağlı işlem adı
`**kwargs`: Hizmete iletilen ek parametreler

**Döndürür:** dict: Veri, hatalar ve/veya uzantılar içeren GraphQL yanıtı

**Örnek:**

```python
socket = api.socket()
flow = socket.flow("default")

query = '''
{
  scientists(limit: 10) {
    name
    field
    discoveries
  }
}
'''
result = flow.rows_query(
    query=query,
    user="trustgraph",
    collection="scientists"
)
```

### `text_completion(self, system: str, prompt: str, streaming: bool = False, **kwargs) -> str | Iterator[str]`

İsteğe bağlı akışla metin tamamlama işlemini gerçekleştirin.

**Argümanlar:**

`system`: Asistanın davranışını tanımlayan sistem istemi
`prompt`: Kullanıcı istemi/sorusu
`streaming`: Akış modunu etkinleştir (varsayılan: False)
`**kwargs`: Hizmete iletilen ek parametreler

**Dönüş:** Union[str, Iterator[str]]: Tamamlanmış yanıt veya metin parçalarının akışı

**Örnek:**

```python
socket = api.socket()
flow = socket.flow("default")

# Non-streaming
response = flow.text_completion(
    system="You are helpful",
    prompt="Explain quantum computing",
    streaming=False
)
print(response)

# Streaming
for chunk in flow.text_completion(
    system="You are helpful",
    prompt="Explain quantum computing",
    streaming=True
):
    print(chunk, end='', flush=True)
```

### `triples_query(self, s: str | Dict[str, Any] | None = None, p: str | Dict[str, Any] | None = None, o: str | Dict[str, Any] | None = None, g: str | None = None, user: str | None = None, collection: str | None = None, limit: int = 100, **kwargs: Any) -> List[Dict[str, Any]]`

Desen eşleştirme kullanarak bilgi grafiği üçlülerini sorgulayın.

**Argümanlar:**

`s`: Konu filtresi - URI dizesi, Terim sözlüğü veya joker karakter için None
`p`: Özne filtresi - URI dizesi, Terim sözlüğü veya joker karakter için None
`o`: Nesne filtresi - URI/literal dizesi, Terim sözlüğü veya joker karakter için None
`g`: Adlandırılmış grafik filtresi - URI dizesi veya tüm grafikler için None
`user`: Kullanıcı/uzay kimlik tanımlayıcısı (isteğe bağlı)
`collection`: Koleksiyon kimlik tanımlayıcısı (isteğe bağlı)
`limit`: Döndürülecek maksimum sonuç sayısı (varsayılan: 100)
`**kwargs`: Hizmete geçirilecek ek parametreler

**Döndürür:** List[Dict]: Tel formatındaki eşleşen üçlülerin listesi

**Örnek:**

```python
socket = api.socket()
flow = socket.flow("default")

# Find all triples about a specific subject
triples = flow.triples_query(
    s="http://example.org/person/marie-curie",
    user="trustgraph",
    collection="scientists"
)

# Query with named graph filter
triples = flow.triples_query(
    s="urn:trustgraph:session:abc123",
    g="urn:graph:retrieval",
    user="trustgraph",
    collection="default"
)
```

### `triples_query_stream(self, s: str | Dict[str, Any] | None = None, p: str | Dict[str, Any] | None = None, o: str | Dict[str, Any] | None = None, g: str | None = None, user: str | None = None, collection: str | None = None, limit: int = 100, batch_size: int = 20, **kwargs: Any) -> Iterator[List[Dict[str, Any]]]`

Akışlı toplu işlemlerle bilgi grafiği üçlülerini sorgulayın.

Üçlüleri geldikleri gibi toplu olarak döndürür, böylece ilk sonuç alma süresini ve büyük sonuç kümeleri için bellek yükünü azaltır.


**Parametreler:**

`s`: Konu filtresi - URI dizesi, Terim sözlüğü veya joker karakter için None
`p`: Özne filtresi - URI dizesi, Terim sözlüğü veya joker karakter için None
`o`: Nesne filtresi - URI/literal dizesi, Terim sözlüğü veya joker karakter için None
`g`: Adlandırılmış grafik filtresi - URI dizesi veya tüm grafikler için None
`user`: Kullanıcı/keyspace tanımlayıcısı (isteğe bağlı)
`collection`: Koleksiyon tanımlayıcısı (isteğe bağlı)
`limit`: Döndürülecek maksimum sonuç sayısı (varsayılan: 100)
`batch_size`: Toplu işlemdeki üçlü sayısı (varsayılan: 20)
`**kwargs`: Hizmete geçirilecek ek parametreler
`Yields`: 
`List[Dict]`: Tel formatındaki üçlü topları

**Örnek:**

```python
socket = api.socket()
flow = socket.flow("default")

for batch in flow.triples_query_stream(
    user="trustgraph",
    collection="default"
):
    for triple in batch:
        print(triple["s"], triple["p"], triple["o"])
```


--

## `AsyncSocketClient`

```python
from trustgraph.api import AsyncSocketClient
```

Asenkron WebSocket istemcisi

### Yöntemler

### `__init__(self, url: str, timeout: int, token: str | None)`

Kendini başlat. Doğru imza için help(type(self))'e bakın.

### `aclose(self)`

WebSocket bağlantısını kapat

### `flow(self, flow_id: str)`

WebSocket işlemleri için asenkron akış örneğini al


--

## `AsyncSocketFlowInstance`

```python
from trustgraph.api import AsyncSocketFlowInstance
```

Asenkron WebSocket akışı örneği

### Yöntemler

### `__init__(self, client: trustgraph.api.async_socket_client.AsyncSocketClient, flow_id: str)`

Kendini başlat. Doğru imza için help(type(self))'e bakın.

### `agent(self, question: str, user: str, state: Dict[str, Any] | None = None, group: str | None = None, history: list | None = None, streaming: bool = False, **kwargs) -> Dict[str, Any] | AsyncIterator`

İsteğe bağlı akışa sahip ajan

### `document_rag(self, query: str, user: str, collection: str, doc_limit: int = 10, streaming: bool = False, **kwargs)`

İsteğe bağlı akışa sahip RAG dokümanı

### `embeddings(self, texts: list, **kwargs)`

Metin gömülmelerini oluştur

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs)`

Anlamsal arama için grafik gömülmelerini sorgula

### `graph_rag(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, streaming: bool = False, **kwargs)`

İsteğe bağlı akışa sahip grafik RAG

### `mcp_tool(self, name: str, parameters: Dict[str, Any], **kwargs)`

MCP aracını çalıştır

### `prompt(self, id: str, variables: Dict[str, str], streaming: bool = False, **kwargs)`

İsteğe bağlı akışa sahip istemi çalıştır

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs)`

Yapılandırılmış veriler üzerinde anlamsal arama için satır gömülmelerini sorgula

### `rows_query(self, query: str, user: str, collection: str, variables: Dict | None = None, operation_name: str | None = None, **kwargs)`

Yapılandırılmış satırlara karşı GraphQL sorgusu

### `text_completion(self, system: str, prompt: str, streaming: bool = False, **kwargs)`

İsteğe bağlı akışa sahip metin tamamlama

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=100, **kwargs)`

Üçlü desen sorgusu


--

### `build_term(value: Any, term_type: str | None = None, datatype: str | None = None, language: str | None = None) -> Dict[str, Any] | None`

Bir değerden tel formatlı Term sözlüğünü oluştur.

Otomatik algılama kuralları (term_type None olduğunda):
  Zaten 't' anahtarına sahip bir sözlük -> olduğu gibi döndür (zaten bir Term)
  http://, https://, urn: ile başlıyorsa -> IRI
  <> (örneğin, <http://...>) içinde ise -> IRI (köşeli parantezler kaldırılır)
  Başka bir şey -> literal

**Argümanlar:**

`value`: Term değeri (string, sözlük veya None)
`term_type`: 'iri', 'literal' veya otomatik algılama için
`datatype`: Literal nesneler için veri türü (örneğin, xsd:integer)
`language`: Literal nesneler için dil etiketi (örneğin, en)

**Döndürür:** sözlük: Tel formatlı Term sözlüğü veya değer None ise None


--

## `BulkClient`

```python
from trustgraph.api import BulkClient
```

İçe/dışa aktarım için senkron toplu işlemler istemcisi.

Büyük veri kümeleri için WebSocket üzerinden verimli toplu veri aktarımı sağlar.
Kullanım kolaylığı için asenkron WebSocket işlemlerini senkron oluşturucularla birleştirir.

Not: Gerçek asenkron destek için, AsyncBulkClient'ı kullanın.

### Yöntemler

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Senkron toplu istemciyi başlatır.

**Argümanlar:**

`url`: TrustGraph API'si için temel URL (HTTP/HTTPS, WS/WSS'ye dönüştürülecektir).
`timeout`: WebSocket zaman aşımı (saniye cinsinden).
`token`: İsteğe bağlı, kimlik doğrulama için taşıyıcı belirteci.

### `close(self) -> None`

Bağlantıları kapatır.

### `export_document_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

Bir akıştan toplu belge gömme çıktılarını dışa aktarır.

Tüm belge parçası gömmelerini WebSocket akışı üzerinden verimli bir şekilde indirir.

**Argümanlar:**

`flow`: Akış tanımlayıcısı.
`**kwargs`: Ek parametreler (gelecekteki kullanım için ayrılmıştır).

**Döndürür:** Iterator[Dict[str, Any]]: Gömme sözlüklerinin akışı.

**Örnek:**

```python
bulk = api.bulk()

# Export and process document embeddings
for embedding in bulk.export_document_embeddings(flow="default"):
    chunk_id = embedding.get("chunk_id")
    vector = embedding.get("embedding")
    print(f"{chunk_id}: {len(vector)} dimensions")
```

### `export_entity_contexts(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

Bir akıştan toplu olarak varlık bağlamlarını dışa aktarın.

Tüm varlık bağlamı bilgilerini WebSocket akışı aracılığıyla verimli bir şekilde indirir.

**Argümanlar:**

`flow`: Akış tanımlayıcısı
`**kwargs`: Ek parametreler (gelecekteki kullanım için ayrılmıştır)

**Döndürür:** Iterator[Dict[str, Any]]: Bağlam sözlüklerinin akışı

**Örnek:**

```python
bulk = api.bulk()

# Export and process entity contexts
for context in bulk.export_entity_contexts(flow="default"):
    entity = context.get("entity")
    text = context.get("context")
    print(f"{entity}: {text[:100]}...")
```

### `export_graph_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

Bir akıştan toplu grafik gömme verilerini dışa aktarın.

Tüm grafik varlık gömme verilerini WebSocket üzerinden verimli bir şekilde indirir.

**Parametreler:**

`flow`: Akış tanımlayıcısı
`**kwargs`: Ek parametreler (gelecekteki kullanım için ayrılmıştır)

**Döndürür:** Iterator[Dict[str, Any]]: Gömme sözlüklerinin akışı

**Örnek:**

```python
bulk = api.bulk()

# Export and process embeddings
for embedding in bulk.export_graph_embeddings(flow="default"):
    entity = embedding.get("entity")
    vector = embedding.get("embedding")
    print(f"{entity}: {len(vector)} dimensions")
```

### `export_triples(self, flow: str, **kwargs: Any) -> Iterator[trustgraph.api.types.Triple]`

Bir akıştan RDF üçlülerini toplu olarak dışa aktarın.

Tüm üçlüleri WebSocket akışı aracılığıyla verimli bir şekilde indirir.

**Argümanlar:**

`flow`: Akış tanımlayıcısı
`**kwargs`: Ek parametreler (gelecekteki kullanım için ayrılmıştır)

**Döndürür:** Iterator[Triple]: Triple nesnelerinin akışı

**Örnek:**

```python
bulk = api.bulk()

# Export and process triples
for triple in bulk.export_triples(flow="default"):
    print(f"{triple.s} -> {triple.p} -> {triple.o}")
```

### `import_document_embeddings(self, flow: str, embeddings: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

Bir akışa belge gömme verilerini toplu olarak aktarın.

Belge parçası gömme verilerini, belge RAG sorgularında kullanılmak üzere, WebSocket akışı aracılığıyla verimli bir şekilde yükler.


**Argümanlar:**

`flow`: Akış tanımlayıcısı
`embeddings`: Gömme sözlükleri üreten yineleyici
`**kwargs`: Ek parametreler (gelecekteki kullanım için ayrılmıştır)

**Örnek:**

```python
bulk = api.bulk()

# Generate document embeddings to import
def doc_embedding_generator():
    yield {"chunk_id": "doc1/p0/c0", "embedding": [0.1, 0.2, ...]}
    yield {"chunk_id": "doc1/p0/c1", "embedding": [0.3, 0.4, ...]}
    # ... more embeddings

bulk.import_document_embeddings(
    flow="default",
    embeddings=doc_embedding_generator()
)
```

### `import_entity_contexts(self, flow: str, contexts: Iterator[Dict[str, Any]], metadata: Dict[str, Any] | None = None, batch_size: int = 100, **kwargs: Any) -> None`

Bir akışa toplu olarak varlık bağlamlarını aktarın.

Varlık bağlamı bilgilerini WebSocket akışı aracılığıyla verimli bir şekilde yükler.
Varlık bağlamları, grafik varlıkları hakkında ek metinsel bağlam sağlar
ve geliştirilmiş RAG performansı için kullanılır.

**Argümanlar:**

`flow`: Akış tanımlayıcısı
`contexts`: Bağlam sözlükleri üreten yineleyici
`metadata`: id, metadata, kullanıcı, koleksiyon içeren meta veri sözlüğü
`batch_size`: Toplu iş başına bağlam sayısı (varsayılan 100)
`**kwargs`: Ek parametreler (gelecekteki kullanım için ayrılmıştır)

**Örnek:**

```python
bulk = api.bulk()

# Generate entity contexts to import
def context_generator():
    yield {"entity": {"v": "entity1", "e": True}, "context": "Description..."}
    yield {"entity": {"v": "entity2", "e": True}, "context": "Description..."}
    # ... more contexts

bulk.import_entity_contexts(
    flow="default",
    contexts=context_generator(),
    metadata={"id": "doc1", "metadata": [], "user": "user1", "collection": "default"}
)
```

### `import_graph_embeddings(self, flow: str, embeddings: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

Bir akışa toplu olarak grafik gömme verilerini aktarın.

Grafik varlık gömme verilerini WebSocket üzerinden verimli bir şekilde yükleyin.

**Parametreler:**

`flow`: Akış tanımlayıcısı
`embeddings`: Gömme sözlükleri üreten yineleyici
`**kwargs`: Ek parametreler (gelecekteki kullanım için ayrılmıştır)

**Örnek:**

```python
bulk = api.bulk()

# Generate embeddings to import
def embedding_generator():
    yield {"entity": "entity1", "embedding": [0.1, 0.2, ...]}
    yield {"entity": "entity2", "embedding": [0.3, 0.4, ...]}
    # ... more embeddings

bulk.import_graph_embeddings(
    flow="default",
    embeddings=embedding_generator()
)
```

### `import_rows(self, flow: str, rows: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

Bir akışa yapılandırılmış satırları toplu olarak aktarın.

Yapılandırılmış veri satırlarını, GraphQL sorgularında kullanılmak üzere WebSocket akışı aracılığıyla verimli bir şekilde yükleyin.


**Argümanlar:**

`flow`: Akış tanımlayıcısı
`rows`: Satır sözlükleri üreten yineleyici
`**kwargs`: Ek parametreler (gelecekteki kullanım için ayrılmıştır)

**Örnek:**

```python
bulk = api.bulk()

# Generate rows to import
def row_generator():
    yield {"id": "row1", "name": "Row 1", "value": 100}
    yield {"id": "row2", "name": "Row 2", "value": 200}
    # ... more rows

bulk.import_rows(
    flow="default",
    rows=row_generator()
)
```

### `import_triples(self, flow: str, triples: Iterator[trustgraph.api.types.Triple], metadata: Dict[str, Any] | None = None, batch_size: int = 100, **kwargs: Any) -> None`

Bir akışa RDF üçlülerini toplu olarak aktarın.

Büyük miktarlarda üçlü verisini WebSocket akışı aracılığıyla verimli bir şekilde yükler.

**Parametreler:**

`flow`: Akış tanımlayıcısı
`triples`: Triple nesneleri üreten yineleyici
`metadata`: id, metadata, kullanıcı, koleksiyon içeren meta veri sözlüğü
`batch_size`: Her topluluktaki üçlü sayısı (varsayılan 100)
`**kwargs`: Ek parametreler (gelecekteki kullanım için ayrılmıştır)

**Örnek:**

```python
from trustgraph.api import Triple

bulk = api.bulk()

# Generate triples to import
def triple_generator():
    yield Triple(s="subj1", p="pred", o="obj1")
    yield Triple(s="subj2", p="pred", o="obj2")
    # ... more triples

# Import triples
bulk.import_triples(
    flow="default",
    triples=triple_generator(),
    metadata={"id": "doc1", "metadata": [], "user": "user1", "collection": "default"}
)
```


--

## `AsyncBulkClient`

```python
from trustgraph.api import AsyncBulkClient
```

Asenkron toplu işlemler istemcisi

### Yöntemler

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Kendini başlat. Doğru imza için help(type(self))'e bakın.

### `aclose(self) -> None`

Bağlantıları kapat

### `export_document_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

WebSocket üzerinden belge gömme verilerini toplu olarak dışa aktar

### `export_entity_contexts(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

WebSocket üzerinden varlık bağlamlarını toplu olarak dışa aktar

### `export_graph_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

WebSocket üzerinden grafik gömme verilerini toplu olarak dışa aktar

### `export_triples(self, flow: str, **kwargs: Any) -> AsyncIterator[trustgraph.api.types.Triple]`

WebSocket üzerinden üçlüleri toplu olarak dışa aktar

### `import_document_embeddings(self, flow: str, embeddings: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

WebSocket üzerinden belge gömme verilerini toplu olarak içe aktar

### `import_entity_contexts(self, flow: str, contexts: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

WebSocket üzerinden varlık bağlamlarını toplu olarak içe aktar

### `import_graph_embeddings(self, flow: str, embeddings: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

WebSocket üzerinden grafik gömme verilerini toplu olarak içe aktar

### `import_rows(self, flow: str, rows: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

WebSocket üzerinden satırları toplu olarak içe aktar

### `import_triples(self, flow: str, triples: AsyncIterator[trustgraph.api.types.Triple], **kwargs: Any) -> None`

WebSocket üzerinden üçlüleri toplu olarak içe aktar


--

## `Metrics`

```python
from trustgraph.api import Metrics
```

Senkron ölçüm istemcisi

### Yöntemler

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Kendini başlat. Doğru imza için help(type(self))'e bakın.

### `get(self) -> str`

Prometheus ölçümlerini metin olarak al


--

## `AsyncMetrics`

```python
from trustgraph.api import AsyncMetrics
```

Asenkron metrik istemcisi

### Yöntemler

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Kendini başlat. Doğru imza için help(type(self))'e bakın.

### `aclose(self) -> None`

Bağlantıları kapat

### `get(self) -> str`

Prometheus metriklerini metin olarak al


--

## `ExplainabilityClient`

```python
from trustgraph.api import ExplainabilityClient
```

Açıklanabilirlik varlıklarını, nihai tutarlılık işleme ile getirmek için kullanılan istemci.

Aşağıdaki dinlenme algılama yöntemini kullanır: getirme, bekleme, tekrar getirme, karşılaştırma.
Sonuçlar aynıysa, veri kararlıdır.

### Yöntemler

### `__init__(self, flow_instance, retry_delay: float = 0.2, max_retries: int = 10)`

Açıklanabilirlik istemcisini başlat.

**Argümanlar:**

`flow_instance`: Üçlüleri sorgulamak için bir SocketFlowInstance.
`retry_delay`: Tekrar denemeler arasındaki gecikme (varsayılan: 0.2).
`max_retries`: Maksimum tekrar deneme sayısı (varsayılan: 10).

### `detect_session_type(self, session_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> str`

Bir oturumun GraphRAG veya Agent türünde olup olmadığını tespit edin.

**Argümanlar:**

`session_uri`: Oturum/soru URI'si.
`graph`: Adlandırılmış grafik.
`user`: Kullanıcı/keyspace tanımlayıcısı.
`collection`: Koleksiyon tanımlayıcısı.

**Döndürür:** "graphrag" veya "agent".

### `fetch_agent_trace(self, session_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

Bir oturum URI'sinden başlayarak, tamamlanmış Agent izini alın.

Aşağıdaki köken zincirini izleyin: Soru -> Analiz(ler) -> Sonuç.

**Argümanlar:**

`session_uri`: Agent oturum/soru URI'si.
`graph`: Adlandırılmış grafik (varsayılan: urn:graph:retrieval).
`user`: Kullanıcı/keyspace tanımlayıcısı.
`collection`: Koleksiyon tanımlayıcısı.
`api`: Kütüphaneci erişimi için TrustGraph Api örneği (isteğe bağlı).
`max_content`: Sonuç için maksimum içerik uzunluğu.

**Döndürür:** Soru, yinelemeler (Analiz listesi), sonuç varlıkları ile birlikte bir Sözlük.

### `fetch_docrag_trace(self, question_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

Bir soru URI'sinden başlayarak, tamamlanmış DocumentRAG izini alın.

Aşağıdaki köken zincirini izleyin:
    Soru -> Yerleştirme -> Keşif -> Sentez.

**Argümanlar:**

`question_uri`: Soru varlık URI'si.
`graph`: Adlandırılmış grafik (varsayılan: urn:graph:retrieval).
`user`: Kullanıcı/keyspace tanımlayıcısı.
`collection`: Koleksiyon tanımlayıcısı.
`api`: Kütüphaneci erişimi için TrustGraph Api örneği (isteğe bağlı).
`max_content`: Sentez için maksimum içerik uzunluğu.

**Döndürür:** Soru, yerleştirme, keşif, sentez varlıkları ile birlikte bir Sözlük.

### `fetch_document_content(self, document_uri: str, api: Any, user: str | None = None, max_content: int = 10000) -> str`

Bir belge URI'si tarafından kütüphaneciden içerik alın.

**Argümanlar:**

`document_uri`: Kütüphanecideki belge URI'si.
`api`: Kütüphaneci erişimi için TrustGraph Api örneği.
`user`: Kütüphaneci için kullanıcı tanımlayıcısı.
`max_content`: Döndürülecek maksimum içerik uzunluğu.

**Döndürür:** Belge içeriğini bir dize olarak.

### `fetch_edge_selection(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.EdgeSelection | None`

Bir kenar seçimi varlığı alın (Focus tarafından kullanılır).

**Argümanlar:**

`uri`: Kenar seçimi URI'si.
`graph`: Sorgulanacak adlandırılmış grafik.
`user`: Kullanıcı/keyspace tanımlayıcısı.
`collection`: Koleksiyon tanımlayıcısı.

**Döndürür:** EdgeSelection veya bulunamazsa None.

### `fetch_entity(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.ExplainEntity | None`

Bir URI'yi, olası tutarlılık yönetimi ile bir açıklanabilirlik varlığı olarak alın.

Aşağıdaki durgunluk tespitini kullanır:
1. URI için üçlüleri alın
2. Sıfır sonuç varsa, tekrar deneyin
3. Sıfır olmayan sonuçlar varsa, bekleyin ve tekrar alın
4. Aynı sonuçlar varsa, veri kararlıdır - ayrıştırın ve döndürün
5. Farklı sonuçlar varsa, veri hala yazılıyor - tekrar deneyin

**Argümanlar:**

`uri`: Alınacak varlık URI'si
`graph`: Sorgulanacak adlandırılmış grafik (örneğin, "urn:graph:retrieval")
`user`: Kullanıcı/anahtar alanı tanımlayıcısı
`collection`: Koleksiyon tanımlayıcısı

**Döndürür:** Açıklanabilir Varlık alt sınıfı veya bulunamazsa None

### `fetch_focus_with_edges(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.Focus | None`

Bir Focus varlığını ve tüm kenar seçimlerini alın.

**Argümanlar:**

`uri`: Focus varlık URI'si
`graph`: Sorgulanacak adlandırılmış grafik
`user`: Kullanıcı/anahtar alanı tanımlayıcısı
`collection`: Koleksiyon tanımlayıcısı

**Döndürür:** Doldurulmuş kenar_seçimleri ile Focus veya bulunamazsa None

### `fetch_graphrag_trace(self, question_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

Bir soru URI'sinden başlayarak, tamamlanmış GraphRAG izini alın.

Aşağıdaki köken zincirini izler: Soru -> Yerleştirme -> Keşif -> Focus -> Sentez

**Argümanlar:**

`question_uri`: Soru varlık URI'si
`graph`: Adlandırılmış grafik (varsayılan: urn:graph:retrieval)
`user`: Kullanıcı/anahtar alanı tanımlayıcısı
`collection`: Koleksiyon tanımlayıcısı
`api`: Kütüphaneci erişimi için TrustGraph Api örneği (isteğe bağlı)
`max_content`: Sentez için maksimum içerik uzunluğu

**Döndürür:** Soru, yerleştirme, keşif, focus, sentez varlıkları ile Sözlük

### `list_sessions(self, graph: str | None = None, user: str | None = None, collection: str | None = None, limit: int = 50) -> List[trustgraph.api.explainability.Question]`

Bir koleksiyondaki tüm açıklanabilirlik oturumlarını (soruları) listeleyin.

**Argümanlar:**

`graph`: Adlandırılmış grafik (varsayılan: urn:graph:retrieval)
`user`: Kullanıcı/anahtar alanı tanımlayıcısı
`collection`: Koleksiyon tanımlayıcısı
`limit`: Döndürülecek maksimum oturum sayısı

**Döndürür:** Zaman damgasına göre sıralanmış (en yeni ilk) Soru varlıkları listesi

### `resolve_edge_labels(self, edge: Dict[str, str], user: str | None = None, collection: str | None = None) -> Tuple[str, str, str]`

Bir kenar üçlüsünün tüm bileşenleri için etiketleri çözün.

**Argümanlar:**

`edge`: "s", "p", "o" anahtarlarına sahip Sözlük
`user`: Kullanıcı/anahtar alanı tanımlayıcısı
`collection`: Koleksiyon tanımlayıcısı

**Döndürür:** (s_etiketi, p_etiketi, o_etiketi) tuple'ı

### `resolve_label(self, uri: str, user: str | None = None, collection: str | None = None) -> str`

Bir URI için rdfs:label'i, önbellekleme ile çözün.

**Argümanlar:**

`uri`: Etiketi alınacak URI
`user`: Kullanıcı/anahtar alanı tanımlayıcısı
`collection`: Koleksiyon tanımlayıcısı

**Döndürür:** Bulunursa etiketi, aksi takdirde URI'yi kendisi


--

## `ExplainEntity`

```python
from trustgraph.api import ExplainEntity
```

Açıklanabilirlik varlıkları için temel sınıf.

**Alanlar:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>

### Yöntemler

### `__init__(self, uri: str, entity_type: str = '') -> None`

Kendini başlatır. Doğru imza için help(type(self))'e bakın.


--

## `Question`

```python
from trustgraph.api import Question
```

Soru varlığı - oturumu başlatan kullanıcının sorgusu.

**Alanlar:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`query`: <class 'str'>
`timestamp`: <class 'str'>
`question_type`: <class 'str'>

### Yöntemler

### `__init__(self, uri: str, entity_type: str = '', query: str = '', timestamp: str = '', question_type: str = '') -> None`

Kendini başlat. Doğru imza için help(type(self))'e bakın.


--

## `Exploration`

```python
from trustgraph.api import Exploration
```

Keşif varlığı - bilgi deposundan alınan kenarlar/parçalar.

**Alanlar:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`edge_count`: <class 'int'>
`chunk_count`: <class 'int'>
`entities`: typing.List[str]

### Yöntemler

### `__init__(self, uri: str, entity_type: str = '', edge_count: int = 0, chunk_count: int = 0, entities: List[str] = <factory>) -> None`

Kendini başlat. Doğru imza için help(type(self))'e bakın.


--

## `Focus`

```python
from trustgraph.api import Focus
```

Odak varlığı - LLM akıl yürütmesiyle seçilen kenarlar (yalnızca GraphRAG).

**Alanlar:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`selected_edge_uris`: typing.List[str]
`edge_selections`: typing.List[trustgraph.api.explainability.EdgeSelection]

### Yöntemler

### `__init__(self, uri: str, entity_type: str = '', selected_edge_uris: List[str] = <factory>, edge_selections: List[trustgraph.api.explainability.EdgeSelection] = <factory>) -> None`

Kendini başlat. Doğru imza için help(type(self))'e bakın.


--

## `Synthesis`

```python
from trustgraph.api import Synthesis
```

Sentez varlığı - nihai cevap.

**Alanlar:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`document`: <class 'str'>

### Yöntemler

### `__init__(self, uri: str, entity_type: str = '', document: str = '') -> None`

Kendini başlat. Doğru imza için help(type(self))'e bakın.


--

## `Analysis`

```python
from trustgraph.api import Analysis
```

Analiz varlığı - bir düşünme/eylem/gözlem döngüsü (Sadece Ajan).

**Alanlar:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`action`: <class 'str'>
`arguments`: <class 'str'>
`thought`: <class 'str'>
`observation`: <class 'str'>

### Yöntemler

### `__init__(self, uri: str, entity_type: str = '', action: str = '', arguments: str = '', thought: str = '', observation: str = '') -> None`

Kendini başlat. Doğru imza için help(type(self))'e bakın.


--

## `Conclusion`

```python
from trustgraph.api import Conclusion
```

Sonuç varlığı - kesin cevap (Sadece Ajan).

**Alanlar:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`document`: <class 'str'>

### Yöntemler

### `__init__(self, uri: str, entity_type: str = '', document: str = '') -> None`

Kendini başlat. Doğru imza için help(type(self))'e bakın.


--

## `EdgeSelection`

```python
from trustgraph.api import EdgeSelection
```

GraphRAG Odak adımı tarafından sağlanan bir mantıkla seçilen bir kenar.

**Alanlar:**

`uri`: <class 'str'>
`edge`: typing.Dict[str, str] | None
`reasoning`: <class 'str'>

### Yöntemler

### `__init__(self, uri: str, edge: Dict[str, str] | None = None, reasoning: str = '') -> None`

Kendini başlat. Doğru imza için help(type(self))'e bakın.


--

### `wire_triples_to_tuples(wire_triples: List[Dict[str, Any]]) -> List[Tuple[str, str, Any]]`

Kablolu üçlüleri (s, p, o) demetlerine dönüştürün.


--

### `extract_term_value(term: Dict[str, Any]) -> Any`

Bir kablolu Term sözlüğünden değer çıkarın.


--

## `Triple`

```python
from trustgraph.api import Triple
```

Bilgi grafiği ifadesini temsil eden RDF üçlüsü.

**Alanlar:**

`s`: <class 'str'>
`p`: <class 'str'>
`o`: <class 'str'>

### Yöntemler

### `__init__(self, s: str, p: str, o: str) -> None`

Kendini başlat. Doğru imza için help(type(self))'e bakın.


--

## `Uri`

```python
from trustgraph.api import Uri
```

str(nesne='') -> str
str(bayt_veya_tampon[, kodlama[, hatalar]]) -> str

Verilen nesneden yeni bir dize nesnesi oluşturur. Eğer kodlama veya
hatalar belirtildiyse, nesne, belirtilen kodlama ve hata işleyicisi kullanılarak
çözümlenecek bir veri tamponu içermelidir.
Aksi takdirde, object.__str__()'nin sonucunu (eğer tanımlıysa)
veya repr(object)'in sonucunu döndürür.
kodlama varsayılan olarak 'utf-8' değerine sahiptir.
hatalar varsayılan olarak 'strict' değerine sahiptir.

### Metotlar

### `is_literal(self)`

### `is_triple(self)`

### `is_uri(self)`


--

## `Literal`

```python
from trustgraph.api import Literal
```

str(nesne='') -> str
str(bayt_veya_tampon[, kodlama[, hatalar]]) -> str

Verilen nesneden yeni bir dize nesnesi oluşturur. Eğer kodlama veya
hatalar belirtildiyse, nesne, belirtilen kodlama ve hata işleyici kullanılarak
çözümlenecek bir veri tamponu içermelidir.
Aksi takdirde, nesnenin object.__str__() (eğer tanımlıysa)
veya repr(nesne) sonucunu döndürür.
kodlama varsayılan olarak 'utf-8' değerine sahiptir.
hatalar varsayılan olarak 'strict' değerine sahiptir.

### Yöntemler

### `is_literal(self)`

### `is_triple(self)`

### `is_uri(self)`


--

## `ConfigKey`

```python
from trustgraph.api import ConfigKey
```

Yapılandırma anahtar tanımlayıcısı.

**Alanlar:**

`type`: <class 'str'>
`key`: <class 'str'>

### Yöntemler

### `__init__(self, type: str, key: str) -> None`

Kendini başlat. Doğru imza için help(type(self))'e bakın.


--

## `ConfigValue`

```python
from trustgraph.api import ConfigValue
```

Yapılandırma anahtar-değer çifti.

**Alanlar:**

`type`: <class 'str'>
`key`: <class 'str'>
`value`: <class 'str'>

### Metotlar

### `__init__(self, type: str, key: str, value: str) -> None`

Kendini başlat. Doğru imza için help(type(self))'e bakın.


--

## `DocumentMetadata`

```python
from trustgraph.api import DocumentMetadata
```

Kütüphanedeki bir belge için meta veri.

**Özellikler:**

`parent_id: Parent document ID for child documents (empty for top`: level docs)

**Alanlar:**

`id`: <class 'str'>
`time`: <class 'datetime.datetime'>
`kind`: <class 'str'>
`title`: <class 'str'>
`comments`: <class 'str'>
`metadata`: typing.List[trustgraph.api.types.Triple]
`user`: <class 'str'>
`tags`: typing.List[str]
`parent_id`: <class 'str'>
`document_type`: <class 'str'>

### Yöntemler

### `__init__(self, id: str, time: datetime.datetime, kind: str, title: str, comments: str, metadata: List[trustgraph.api.types.Triple], user: str, tags: List[str], parent_id: str = '', document_type: str = 'source') -> None`

Kendini başlat. Doğru imza için help(type(self))'e bakın.


--

## `ProcessingMetadata`

```python
from trustgraph.api import ProcessingMetadata
```

Etkin bir belge işleme işi için meta veriler.

**Alanlar:**

`id`: <class 'str'>
`document_id`: <class 'str'>
`time`: <class 'datetime.datetime'>
`flow`: <class 'str'>
`user`: <class 'str'>
`collection`: <class 'str'>
`tags`: typing.List[str]

### Yöntemler

### `__init__(self, id: str, document_id: str, time: datetime.datetime, flow: str, user: str, collection: str, tags: List[str]) -> None`

Kendini başlat. Doğru imza için help(type(self))'e bakın.


--

## `CollectionMetadata`

```python
from trustgraph.api import CollectionMetadata
```

Bir veri koleksiyonu için meta veri.

Koleksiyonlar, belgeler ve
bilgi grafiği verileri için mantıksal gruplama ve izolasyon sağlar.

**Özellikler:**

`name: Human`: okunabilir koleksiyon adı

**Alanlar:**

`user`: <class 'str'>
`collection`: <class 'str'>
`name`: <class 'str'>
`description`: <class 'str'>
`tags`: typing.List[str]

### Yöntemler

### `__init__(self, user: str, collection: str, name: str, description: str, tags: List[str]) -> None`

Kendini başlat. Doğru imza için help(type(self))'e bakın.


--

## `StreamingChunk`

```python
from trustgraph.api import StreamingChunk
```

Akış yanıtı parçacıkları için temel sınıf.

Yanıtların üretildikleri gibi kademeli olarak iletildiği, WebSocket tabanlı akış işlemlerinde kullanılır.


**Alanlar:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>

### Yöntemler

### `__init__(self, content: str, end_of_message: bool = False) -> None`

Kendini başlatır. Doğru imza için help(type(self))'e bakın.


--

## `AgentThought`

```python
from trustgraph.api import AgentThought
```

Ajanın muhakeme/düşünce süreci parçası.

Ajanın yürütme sırasında kullandığı iç muhakeme veya planlama adımlarını temsil eder.
Bu parçalar, ajanın problemi nasıl düşündüğünü gösterir.

**Alanlar:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>

### Yöntemler

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'thought') -> None`

Kendini başlat. Doğru imza için help(type(self))'e bakın.


--

## `AgentObservation`

```python
from trustgraph.api import AgentObservation
```

Ajan aracı yürütme gözlemi parçası.

Bir aracın veya eylemin yürütülmesinden elde edilen sonucu veya gözlemi temsil eder.
Bu parçalar, ajanın araçları kullanmaktan ne öğrendiğini gösterir.

**Alanlar:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>

### Yöntemler

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'observation') -> None`

Kendini başlat. Doğru imza için help(type(self))'e bakın.


--

## `AgentAnswer`

```python
from trustgraph.api import AgentAnswer
```

Ajanın son yanıt parçası.

Kullanıcının sorgusuna, akıl yürütme ve araç kullanımını tamamladıktan sonra, ajanın verdiği son yanıtı temsil eder.


**Özellikler:**

`chunk_type: Always "final`: answer"

**Alanlar:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>
`end_of_dialog`: <class 'bool'>

### Yöntemler

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'final-answer', end_of_dialog: bool = False) -> None`

Kendini başlat. Doğru imza için help(type(self))'e bakın.


--

## `RAGChunk`

```python
from trustgraph.api import RAGChunk
```

RAG (Retrieval-Augmented Generation) akışı parçası.

Grafik RAG, belge RAG, metin tamamlama,
ve diğer üretken hizmetlerden gelen yanıtları akış için kullanılır.

**Alanlar:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>
`end_of_stream`: <class 'bool'>
`error`: typing.Dict[str, str] | None

### Yöntemler

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'rag', end_of_stream: bool = False, error: Dict[str, str] | None = None) -> None`

Kendini başlatır. Doğru imza için help(type(self))'e bakın.


--

## `ProvenanceEvent`

```python
from trustgraph.api import ProvenanceEvent
```

Açıklanabilirlik için köken olayları.

Açıklanabilir mod etkinleştirildiğinde GraphRAG sorguları sırasında yayımlanır.
Her olay, sorgu işleme sırasında oluşturulan bir köken düğümünü temsil eder.

**Alanlar:**

`explain_id`: <class 'str'>
`explain_graph`: <class 'str'>
`event_type`: <class 'str'>

### Yöntemler

### `__init__(self, explain_id: str, explain_graph: str = '', event_type: str = '') -> None`

Kendini başlat. Doğru imza için help(type(self))'e bakın.


--

## `ProtocolException`

```python
from trustgraph.api import ProtocolException
```

WebSocket protokolü hataları oluştuğunda tetiklenir.


--

## `TrustGraphException`

```python
from trustgraph.api import TrustGraphException
```

Tüm TrustGraph hizmeti hataları için temel sınıf.


--

## `AgentError`

```python
from trustgraph.api import AgentError
```

Ajan hizmeti hatası


--

## `ConfigError`

```python
from trustgraph.api import ConfigError
```

Yapılandırma hizmeti hatası


--

## `DocumentRagError`

```python
from trustgraph.api import DocumentRagError
```

Belge RAG (Retrieval-Augmented Generation) alma hatası


--

## `FlowError`

```python
from trustgraph.api import FlowError
```

Akış yönetimi hatası


--

## `GatewayError`

```python
from trustgraph.api import GatewayError
```

API Ağ Geçidi hatası


--

## `GraphRagError`

```python
from trustgraph.api import GraphRagError
```

Grafik RAG geri alma hatası


--

## `LLMError`

```python
from trustgraph.api import LLMError
```

LLM hizmeti hatası


--

## `LoadError`

```python
from trustgraph.api import LoadError
```

Veri yükleme hatası


--

## `LookupError`

```python
from trustgraph.api import LookupError
```

Arama/ara hata


--

## `NLPQueryError`

```python
from trustgraph.api import NLPQueryError
```

NLP sorgu hizmeti hatası


--

## `RowsQueryError`

```python
from trustgraph.api import RowsQueryError
```

Satır sorgu hizmeti hatası


--

## `RequestError`

```python
from trustgraph.api import RequestError
```

İstek işleme hatası


--

## `StructuredQueryError`

```python
from trustgraph.api import StructuredQueryError
```

Yapılandırılmış sorgu hizmeti hatası


--

## `UnexpectedError`

```python
from trustgraph.api import UnexpectedError
```

Beklenmedik/bilinmeyen hata


--

## `ApplicationException`

```python
from trustgraph.api import ApplicationException
```

Tüm TrustGraph hizmeti hataları için temel sınıf.


--
