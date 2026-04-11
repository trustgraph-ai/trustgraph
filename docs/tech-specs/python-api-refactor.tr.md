# Python API Yeniden Düzenleme Teknik Özellikleri

## Genel Bakış

Bu özellik, TrustGraph Python API istemci kitaplığının, API Gateway ile özellik uyumluluğu sağlamak ve modern gerçek zamanlı iletişim kalıplarına destek eklemek için kapsamlı bir şekilde yeniden düzenlenmesini açıklamaktadır.

Bu yeniden düzenleme, dört birincil kullanım durumunu ele almaktadır:

1. **Akışlı LLM Etkileşimleri**: LLM yanıtlarının (ajan, grafik RAG, belge RAG, metin tamamlama, istemler) gerçek zamanlı olarak akışını etkinleştirin ve ilk belirteç için ~60 kat daha düşük gecikme süresi sağlayın (30 saniye yerine 500 ms).
2. **Toplu Veri İşlemleri**: Büyük ölçekli bilgi grafiği yönetimi için üçlülerin, grafik gömülme ve belge gömülme verilerinin verimli toplu olarak aktarılmasını ve dışa aktarılmasını destekleyin.
3. **Özellik Uyumluluğu**: Her API Gateway uç noktasının, grafik gömülme sorgusu da dahil olmak üzere, karşılık gelen bir Python API yöntemine sahip olduğundan emin olun.
4. **Sürekli Bağlantılar**: Çoklu istekler ve azaltılmış bağlantı yükü için WebSocket tabanlı iletişimi etkinleştirin.

## Hedefler

**Özellik Uyumluluğu**: Her Gateway API hizmetinin karşılık gelen bir Python API yöntemi vardır.
**Akış Desteği**: Tüm akış özellikli hizmetler (ajan, RAG, metin tamamlama, istem), Python API'de akışı destekler.
**WebSocket Taşıyıcı Katmanı**: Kalıcı bağlantılar ve çoklama için isteğe bağlı bir WebSocket taşıyıcı katmanı ekleyin.
**Toplu İşlemler**: Üçlüler, grafik gömülme ve belge gömülme için verimli toplu aktarım/dışa aktarma ekleyin.
**Tam Asenkron Desteği**: Tüm arayüzler (REST, WebSocket, toplu işlemler, ölçümler) için eksiksiz asenkron/bekleme uygulaması.
**Geriye Dönük Uyumluluk**: Mevcut kod, herhangi bir değişiklik yapılmadan çalışmaya devam eder.
**Tip Güvenliği**: Veri sınıfları ve tip ipuçlarıyla tip güvenli arayüzleri koruyun.
**Aşamalı Geliştirme**: Akış ve asenkron, açık arayüz seçimi yoluyla isteğe bağlıdır.
**Performans**: Akış işlemlerinde 60 kat gecikme iyileştirmesi elde edin.
**Modern Python**: Maksimum esneklik için hem senkron hem de asenkron paradigmaları destekleyin.

## Arka Plan

### Mevcut Durum

Python API'si (`trustgraph-base/trustgraph/api/`), aşağıdaki modüllere sahip REST tabanlı bir istemci kitaplığıdır:

`flow.py`: Akış yönetimi ve akış kapsamlı hizmetler (50 yöntem)
`library.py`: Belge kitaplığı işlemleri (9 yöntem)
`knowledge.py`: KG çekirdek yönetimi (4 yöntem)
`collection.py`: Koleksiyon meta verileri (3 yöntem)
`config.py`: Yapılandırma yönetimi (6 yöntem)
`types.py`: Veri türü tanımları (5 veri sınıfı)

**Toplam İşlem**: 50/59 (%85 kapsama)

### Mevcut Sınırlamalar

**Eksik İşlemler**:
Grafik gömülme sorgusu (grafik varlıkları üzerindeki semantik arama)
Üçlüler, grafik gömülme, belge gömülme, varlık bağlamları, nesneler için toplu aktarım/dışa aktarma
Ölçüm uç noktası

**Eksik Yetenekler**:
LLM hizmetleri için akış desteği
WebSocket taşıyıcısı
Çoklu eşzamanlı istekler
Kalıcı bağlantılar

**Performans Sorunları**:
LLM etkileşimleri için yüksek gecikme süresi (~30 saniye ilk belirteç)
Toplu veri aktarımı için verimsiz (her öğe için REST isteği)
Birden çok sıralı işlem için bağlantı yükü

**Kullanıcı Deneyimi Sorunları**:
LLM oluşturma sırasında gerçek zamanlı geri bildirim yok
Uzun süren LLM işlemlerini iptal edememe
Toplu işlemler için zayıf ölçeklenebilirlik

### Etki

Kasım 2024'te Gateway API'ye yapılan akış geliştirmesi, LLM etkileşimleri için 60 kat gecikme iyileştirmesi (30 saniye yerine 500 ms ilk belirteç) sağladı, ancak Python API kullanıcıları bu yeteneği kullanamıyor. Bu, Python ve Python dışı kullanıcılar arasında önemli bir deneyim boşluğuna yol açmaktadır.

## Teknik Tasarım

### Mimari

Yeniden düzenlenmiş Python API'si, farklı iletişim kalıpları için ayrı nesneler kullanan **modüler bir arayüz yaklaşımı** kullanır. Tüm arayüzler hem **senkron hem de asenkron** varyantlarda mevcuttur:

1. **REST Arayüzü** (mevcut, geliştirilmiş)
   **Senkron**: `api.flow()`, `api.library()`, `api.knowledge()`, `api.collection()`, `api.config()`
   **Asenkron**: `api.async_flow()`
   Senkron/asenkron istek/yanıt
   Basit bağlantı modeli
   Geriye dönük uyumluluk için varsayılan

2. **WebSocket Arayüzü** (yeni)
   **Senkron**: `api.socket()`
   **Asenkron**: `api.async_socket()`
   Kalıcı bağlantı
   Çoklu istekler
   Akış desteği
   İşlevselliğin örtüştüğü yerlerde REST ile aynı yöntem imzaları

3. **Toplu İşlemler Arayüzü** (yeni)
   **Senkron**: `api.bulk()`
   **Asenkron**: `api.async_bulk()`
   Verimlilik için WebSocket tabanlı
   Iterator/AsyncIterator tabanlı aktarım/dışa aktarma
   Büyük veri kümelerini işler

4. **Ölçüm Arayüzü** (yeni)
   **Senkron**: `api.metrics()`
   **Asenkron**: `api.async_metrics()`
   Prometheus ölçümleri erişimi

```python
import asyncio

# Synchronous interfaces
api = Api(url="http://localhost:8088/")

# REST (existing, unchanged)
flow = api.flow().id("default")
response = flow.agent(question="...", user="...")

# WebSocket (new)
socket_flow = api.socket().flow("default")
response = socket_flow.agent(question="...", user="...")
for chunk in socket_flow.agent(question="...", user="...", streaming=True):
    print(chunk)

# Bulk operations (new)
bulk = api.bulk()
bulk.import_triples(flow="default", triples=triple_generator())

# Asynchronous interfaces
async def main():
    api = Api(url="http://localhost:8088/")

    # Async REST (new)
    flow = api.async_flow().id("default")
    response = await flow.agent(question="...", user="...")

    # Async WebSocket (new)
    socket_flow = api.async_socket().flow("default")
    async for chunk in socket_flow.agent(question="...", streaming=True):
        print(chunk)

    # Async bulk operations (new)
    bulk = api.async_bulk()
    await bulk.import_triples(flow="default", triples=async_triple_generator())

asyncio.run(main())
```

**Temel Tasarım Prensipleri**:
**Tüm arayüzler için aynı URL**: `Api(url="http://localhost:8088/")`, tüm arayüzler için geçerlidir.
**Senkron/Asenkron simetri**: Her arayüzün hem senkron hem de asenkron varyantları vardır ve yöntem imzaları aynıdır.
**Aynı imzalar**: İşlevsellik örtüşüyorsa, REST ve WebSocket, senkron ve asenkron arasında yöntem imzaları aynıdır.
**Aşamalı iyileştirme**: İhtiyaçlara göre arayüzü seçin (basit işlemler için REST, akış için WebSocket, büyük veri kümeleri için Bulk, modern çerçeveler için asenkron).
**Açık niyet**: `api.socket()`, WebSocket'i belirtir, `api.async_socket()`, asenkron WebSocket'i belirtir.
**Geriye uyumlu**: Mevcut kod değişmeden kalır.

### Bileşenler

#### 1. Temel API Sınıfı (Değiştirilmiş)

Modül: `trustgraph-base/trustgraph/api/api.py`

**Geliştirilmiş API Sınıfı**:

```python
class Api:
    def __init__(self, url: str, timeout: int = 60, token: Optional[str] = None):
        self.url = url
        self.timeout = timeout
        self.token = token  # Optional bearer token for REST, query param for WebSocket
        self._socket_client = None
        self._bulk_client = None
        self._async_flow = None
        self._async_socket_client = None
        self._async_bulk_client = None

    # Existing synchronous methods (unchanged)
    def flow(self) -> Flow:
        """Synchronous REST-based flow interface"""
        pass

    def library(self) -> Library:
        """Synchronous REST-based library interface"""
        pass

    def knowledge(self) -> Knowledge:
        """Synchronous REST-based knowledge interface"""
        pass

    def collection(self) -> Collection:
        """Synchronous REST-based collection interface"""
        pass

    def config(self) -> Config:
        """Synchronous REST-based config interface"""
        pass

    # New synchronous methods
    def socket(self) -> SocketClient:
        """Synchronous WebSocket-based interface for streaming operations"""
        if self._socket_client is None:
            self._socket_client = SocketClient(self.url, self.timeout, self.token)
        return self._socket_client

    def bulk(self) -> BulkClient:
        """Synchronous bulk operations interface for import/export"""
        if self._bulk_client is None:
            self._bulk_client = BulkClient(self.url, self.timeout, self.token)
        return self._bulk_client

    def metrics(self) -> Metrics:
        """Synchronous metrics interface"""
        return Metrics(self.url, self.timeout, self.token)

    # New asynchronous methods
    def async_flow(self) -> AsyncFlow:
        """Asynchronous REST-based flow interface"""
        if self._async_flow is None:
            self._async_flow = AsyncFlow(self.url, self.timeout, self.token)
        return self._async_flow

    def async_socket(self) -> AsyncSocketClient:
        """Asynchronous WebSocket-based interface for streaming operations"""
        if self._async_socket_client is None:
            self._async_socket_client = AsyncSocketClient(self.url, self.timeout, self.token)
        return self._async_socket_client

    def async_bulk(self) -> AsyncBulkClient:
        """Asynchronous bulk operations interface for import/export"""
        if self._async_bulk_client is None:
            self._async_bulk_client = AsyncBulkClient(self.url, self.timeout, self.token)
        return self._async_bulk_client

    def async_metrics(self) -> AsyncMetrics:
        """Asynchronous metrics interface"""
        return AsyncMetrics(self.url, self.timeout, self.token)

    # Resource management
    def close(self) -> None:
        """Close all synchronous connections"""
        if self._socket_client:
            self._socket_client.close()
        if self._bulk_client:
            self._bulk_client.close()

    async def aclose(self) -> None:
        """Close all asynchronous connections"""
        if self._async_socket_client:
            await self._async_socket_client.aclose()
        if self._async_bulk_client:
            await self._async_bulk_client.aclose()
        if self._async_flow:
            await self._async_flow.aclose()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.aclose()
```

#### 2. Senkron WebSocket İstemcisi

Modül: `trustgraph-base/trustgraph/api/socket_client.py` (yeni)

**SocketClient Sınıfı**:

```python
class SocketClient:
    """Synchronous WebSocket client"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = self._convert_to_ws_url(url)
        self.timeout = timeout
        self.token = token
        self._connection = None
        self._request_counter = 0

    def flow(self, flow_id: str) -> SocketFlowInstance:
        """Get flow instance for WebSocket operations"""
        return SocketFlowInstance(self, flow_id)

    def _connect(self) -> WebSocket:
        """Establish WebSocket connection (lazy)"""
        # Uses asyncio.run() internally to wrap async websockets library
        pass

    def _send_request(
        self,
        service: str,
        flow: Optional[str],
        request: Dict[str, Any],
        streaming: bool = False
    ) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """Send request and handle response/streaming"""
        # Synchronous wrapper around async WebSocket calls
        pass

    def close(self) -> None:
        """Close WebSocket connection"""
        pass

class SocketFlowInstance:
    """Synchronous WebSocket flow instance with same interface as REST FlowInstance"""
    def __init__(self, client: SocketClient, flow_id: str):
        self.client = client
        self.flow_id = flow_id

    # Same method signatures as FlowInstance
    def agent(
        self,
        question: str,
        user: str,
        state: Optional[Dict[str, Any]] = None,
        group: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        streaming: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """Agent with optional streaming"""
        pass

    def text_completion(
        self,
        system: str,
        prompt: str,
        streaming: bool = False,
        **kwargs
    ) -> Union[str, Iterator[str]]:
        """Text completion with optional streaming"""
        pass

    # ... similar for graph_rag, document_rag, prompt, etc.
```

**Temel Özellikler**:
Tembel bağlantı (yalnızca ilk istek gönderildiğinde bağlantı kurulur)
İstek çoklama (en fazla 15 eşzamanlı)
Bağlantı kesildiğinde otomatik yeniden bağlanma
Akış yanıtı ayrıştırma
İş parçacığı güvenli çalışma
Asenkron WebSocket kütüphanesi için senkron sarmalayıcı

#### 3. Asenkron WebSocket İstemcisi

Modül: `trustgraph-base/trustgraph/api/async_socket_client.py` (yeni)

**AsyncSocketClient Sınıfı**:

```python
class AsyncSocketClient:
    """Asynchronous WebSocket client"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = self._convert_to_ws_url(url)
        self.timeout = timeout
        self.token = token
        self._connection = None
        self._request_counter = 0

    def flow(self, flow_id: str) -> AsyncSocketFlowInstance:
        """Get async flow instance for WebSocket operations"""
        return AsyncSocketFlowInstance(self, flow_id)

    async def _connect(self) -> WebSocket:
        """Establish WebSocket connection (lazy)"""
        # Native async websockets library
        pass

    async def _send_request(
        self,
        service: str,
        flow: Optional[str],
        request: Dict[str, Any],
        streaming: bool = False
    ) -> Union[Dict[str, Any], AsyncIterator[Dict[str, Any]]]:
        """Send request and handle response/streaming"""
        pass

    async def aclose(self) -> None:
        """Close WebSocket connection"""
        pass

class AsyncSocketFlowInstance:
    """Asynchronous WebSocket flow instance"""
    def __init__(self, client: AsyncSocketClient, flow_id: str):
        self.client = client
        self.flow_id = flow_id

    # Same method signatures as FlowInstance (but async)
    async def agent(
        self,
        question: str,
        user: str,
        state: Optional[Dict[str, Any]] = None,
        group: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        streaming: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], AsyncIterator[Dict[str, Any]]]:
        """Agent with optional streaming"""
        pass

    async def text_completion(
        self,
        system: str,
        prompt: str,
        streaming: bool = False,
        **kwargs
    ) -> Union[str, AsyncIterator[str]]:
        """Text completion with optional streaming"""
        pass

    # ... similar for graph_rag, document_rag, prompt, etc.
```

**Temel Özellikler**:
Yerleşik async/await desteği
Asenkron uygulamalar için verimli (FastAPI, aiohttp)
İş parçacığı engellemesi yok
Senkron sürümle aynı arayüz
Akış için AsyncIterator

#### 4. Senkron Toplu İşlemler İstemcisi

Modül: `trustgraph-base/trustgraph/api/bulk_client.py` (yeni)

**BulkClient Sınıfı**:

```python
class BulkClient:
    """Synchronous bulk operations client"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = self._convert_to_ws_url(url)
        self.timeout = timeout
        self.token = token

    def import_triples(
        self,
        flow: str,
        triples: Iterator[Triple],
        **kwargs
    ) -> None:
        """Bulk import triples via WebSocket"""
        pass

    def export_triples(
        self,
        flow: str,
        **kwargs
    ) -> Iterator[Triple]:
        """Bulk export triples via WebSocket"""
        pass

    def import_graph_embeddings(
        self,
        flow: str,
        embeddings: Iterator[Dict[str, Any]],
        **kwargs
    ) -> None:
        """Bulk import graph embeddings via WebSocket"""
        pass

    def export_graph_embeddings(
        self,
        flow: str,
        **kwargs
    ) -> Iterator[Dict[str, Any]]:
        """Bulk export graph embeddings via WebSocket"""
        pass

    # ... similar for document embeddings, entity contexts, objects

    def close(self) -> None:
        """Close connections"""
        pass
```

**Temel Özellikler**:
Sabit bellek kullanımı için yineleyici tabanlı.
Her işlem için özel WebSocket bağlantıları.
İlerleme takibi (isteğe bağlı geri çağırma).
Kısmi başarı raporlamasıyla hata yönetimi.

#### 5. Asenkron Toplu İşlemler İstemcisi

Modül: `trustgraph-base/trustgraph/api/async_bulk_client.py` (yeni)

**AsyncBulkClient Sınıfı**:

```python
class AsyncBulkClient:
    """Asynchronous bulk operations client"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = self._convert_to_ws_url(url)
        self.timeout = timeout
        self.token = token

    async def import_triples(
        self,
        flow: str,
        triples: AsyncIterator[Triple],
        **kwargs
    ) -> None:
        """Bulk import triples via WebSocket"""
        pass

    async def export_triples(
        self,
        flow: str,
        **kwargs
    ) -> AsyncIterator[Triple]:
        """Bulk export triples via WebSocket"""
        pass

    async def import_graph_embeddings(
        self,
        flow: str,
        embeddings: AsyncIterator[Dict[str, Any]],
        **kwargs
    ) -> None:
        """Bulk import graph embeddings via WebSocket"""
        pass

    async def export_graph_embeddings(
        self,
        flow: str,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """Bulk export graph embeddings via WebSocket"""
        pass

    # ... similar for document embeddings, entity contexts, objects

    async def aclose(self) -> None:
        """Close connections"""
        pass
```

**Temel Özellikler**:
Sabit bellek kullanımı için AsyncIterator tabanlı.
Asenkron uygulamalar için verimli.
Yerel asenkron/bekle destek.
Senkron sürümle aynı arayüz.

#### 6. REST Akışı API'si (Senkron - Değişmedi)

Modül: `trustgraph-base/trustgraph/api/flow.py`

REST Akışı API'si, geriye dönük uyumluluk için **tamamen değişmeden** kalmıştır. Tüm mevcut yöntemler çalışmaya devam etmektedir:

`Flow.list()`, `Flow.start()`, `Flow.stop()`, vb.
`FlowInstance.agent()`, `FlowInstance.text_completion()`, `FlowInstance.graph_rag()`, vb.
Tüm mevcut imzalar ve dönüş türleri korunmuştur.

**Yeni**: Özellik uyumluluğu için `graph_embeddings_query()`'ı REST FlowInstance'a ekleyin:

```python
class FlowInstance:
    # All existing methods unchanged...

    # New: Graph embeddings query (REST)
    def graph_embeddings_query(
        self,
        text: str,
        user: str,
        collection: str,
        limit: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Query graph embeddings for semantic search"""
        # Calls POST /api/v1/flow/{flow}/service/graph-embeddings
        pass
```

#### 7. Asenkron REST Akışı API'si

Modül: `trustgraph-base/trustgraph/api/async_flow.py` (yeni)

**AsyncFlow ve AsyncFlowInstance Sınıfları:**

```python
class AsyncFlow:
    """Asynchronous REST-based flow interface"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = url
        self.timeout = timeout
        self.token = token

    async def list(self) -> List[Dict[str, Any]]:
        """List all flows"""
        pass

    async def get(self, id: str) -> Dict[str, Any]:
        """Get flow definition"""
        pass

    async def start(self, class_name: str, id: str, description: str, parameters: Dict) -> None:
        """Start a flow"""
        pass

    async def stop(self, id: str) -> None:
        """Stop a flow"""
        pass

    def id(self, flow_id: str) -> AsyncFlowInstance:
        """Get async flow instance"""
        return AsyncFlowInstance(self.url, self.timeout, self.token, flow_id)

    async def aclose(self) -> None:
        """Close connection"""
        pass

class AsyncFlowInstance:
    """Asynchronous REST flow instance"""

    async def agent(
        self,
        question: str,
        user: str,
        state: Optional[Dict[str, Any]] = None,
        group: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Async agent execution"""
        pass

    async def text_completion(
        self,
        system: str,
        prompt: str,
        **kwargs
    ) -> str:
        """Async text completion"""
        pass

    async def graph_rag(
        self,
        question: str,
        user: str,
        collection: str,
        **kwargs
    ) -> str:
        """Async graph RAG"""
        pass

    # ... all other FlowInstance methods as async versions
```

**Temel Özellikler**:
`aiohttp` veya `httpx` kullanarak yerel asenkron HTTP
Senkron REST API'si ile aynı yöntem imzaları
Akış yok (akış için `async_socket()`'ı kullanın)
Asenkron uygulamalar için verimli

#### 8. Ölçüm API'si

Modül: `trustgraph-base/trustgraph/api/metrics.py` (yeni)

**Senkron Ölçümler**:

```python
class Metrics:
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = url
        self.timeout = timeout
        self.token = token

    def get(self) -> str:
        """Get Prometheus metrics as text"""
        # Call GET /api/metrics
        pass
```

**Asenkron Metrikler**:

```python
class AsyncMetrics:
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = url
        self.timeout = timeout
        self.token = token

    async def get(self) -> str:
        """Get Prometheus metrics as text"""
        # Call GET /api/metrics
        pass
```

#### 9. Gelişmiş Tipler

Modül: `trustgraph-base/trustgraph/api/types.py` (değiştirildi)

**Yeni Tipler**:

```python
from typing import Iterator, Union, Dict, Any
import dataclasses

@dataclasses.dataclass
class StreamingChunk:
    """Base class for streaming chunks"""
    content: str
    end_of_message: bool = False

@dataclasses.dataclass
class AgentThought(StreamingChunk):
    """Agent reasoning chunk"""
    chunk_type: str = "thought"

@dataclasses.dataclass
class AgentObservation(StreamingChunk):
    """Agent tool observation chunk"""
    chunk_type: str = "observation"

@dataclasses.dataclass
class AgentAnswer(StreamingChunk):
    """Agent final answer chunk"""
    chunk_type: str = "final-answer"
    end_of_dialog: bool = False

@dataclasses.dataclass
class RAGChunk(StreamingChunk):
    """RAG streaming chunk"""
    end_of_stream: bool = False
    error: Optional[Dict[str, str]] = None

# Type aliases for clarity
AgentStream = Iterator[Union[AgentThought, AgentObservation, AgentAnswer]]
RAGStream = Iterator[RAGChunk]
CompletionStream = Iterator[str]
```

#### 6. Metrik API

Modül: `trustgraph-base/trustgraph/api/metrics.py` (yeni)

```python
class Metrics:
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = url
        self.timeout = timeout
        self.token = token

    def get(self) -> str:
        """Get Prometheus metrics as text"""
        # Call GET /api/metrics
        pass
```

### Uygulama Yaklaşımı

#### 1. Aşama: Temel API Geliştirmeleri (1. Hafta)

1. `socket()`, `bulk()` ve `metrics()` yöntemlerini `Api` sınıfına ekleyin
2. WebSocket ve toplu iş yükleri için tembel başlatmayı uygulayın
3. Bağlam yöneticisi desteğini ekleyin (`__enter__`, `__exit__`)
4. Temizleme için `close()` yöntemini ekleyin
5. API sınıfı geliştirmeleri için birim testleri ekleyin
6. Geriye dönük uyumluluğu doğrulayın

**Geriye Dönük Uyumluluk**: Herhangi bir uyumsuz değişiklik yok. Sadece yeni yöntemler.

#### 2. Aşama: WebSocket İstemcisi (2-3. Haftalar)

1. Bağlantı yönetimi için `SocketClient` sınıfını uygulayın
2. `SocketFlowInstance`'ı `FlowInstance` ile aynı yöntem imzalarına sahip olacak şekilde uygulayın
3. İstek çoklama desteğini ekleyin (en fazla 15 eşzamanlı)
4. Farklı parça türleri için akış yanıtı ayrıştırmasını ekleyin
5. Otomatik yeniden bağlantı mantığını ekleyin
6. Birim ve entegrasyon testlerini ekleyin
7. WebSocket kullanım kalıplarını belgeleyin

**Geriye Dönük Uyumluluk**: Sadece yeni bir arayüz. Mevcut kod üzerinde hiçbir etkisi yok.

#### 3. Aşama: Akış Desteği (3-4. Haftalar)

1. Akış parça türü sınıflarını ekleyin (`AgentThought`, `AgentObservation`, `AgentAnswer`, `RAGChunk`)
2. `SocketClient` içinde akış yanıtı ayrıştırmasını uygulayın
3. `SocketFlowInstance` içindeki tüm LLM yöntemlerine akış parametresini ekleyin
4. Akış sırasında hata durumlarını işleyin
5. Akış için birim ve entegrasyon testlerini ekleyin
6. Belgelerdeki akış örneklerini ekleyin

**Geriye Dönük Uyumluluk**: Sadece yeni bir arayüz. Mevcut REST API değişmedi.

#### 4. Aşama: Toplu İşlemler (4-5. Haftalar)

1. `BulkClient` sınıfını uygulayın
2. Üçlüler, gömülü veriler, bağlamlar, nesneler için toplu içe/dışa aktarma yöntemlerini ekleyin
3. Sabit bellek için yineleyici tabanlı işleme uygulayın
4. İlerleme takibini ekleyin (isteğe bağlı geri çağırma)
5. Kısmi başarı raporlamasıyla hata işleme ekleyin
6. Birim ve entegrasyon testlerini ekleyin
7. Toplu işlem örneklerini ekleyin

**Geriye Dönük Uyumluluk**: Sadece yeni bir arayüz. Mevcut kod üzerinde hiçbir etkisi yok.

#### 5. Aşama: Özellik Eşitliği ve İyileştirmeler (5. Hafta)

1. REST `FlowInstance`'ine `graph_embeddings_query()`'ı ekleyin
2. `Metrics` sınıfını uygulayın
3. Kapsamlı entegrasyon testlerini ekleyin
4. Performans karşılaştırması
5. Tüm belgeleri güncelleyin
6. Geçiş kılavuzu oluşturun

**Geriye Dönük Uyumluluk**: Sadece yeni yöntemler. Mevcut kod üzerinde hiçbir etkisi yok.

### Veri Modelleri

#### Arayüz Seçimi

```python
# Single API instance, same URL for all interfaces
api = Api(url="http://localhost:8088/")

# Synchronous interfaces
rest_flow = api.flow().id("default")           # Sync REST
socket_flow = api.socket().flow("default")     # Sync WebSocket
bulk = api.bulk()                               # Sync bulk operations
metrics = api.metrics()                         # Sync metrics

# Asynchronous interfaces
async_rest_flow = api.async_flow().id("default")      # Async REST
async_socket_flow = api.async_socket().flow("default") # Async WebSocket
async_bulk = api.async_bulk()                          # Async bulk operations
async_metrics = api.async_metrics()                    # Async metrics
```

#### Akış Yanıt Türleri

**Ajan Akışı:**

```python
api = Api(url="http://localhost:8088/")

# REST interface - non-streaming (existing)
rest_flow = api.flow().id("default")
response = rest_flow.agent(question="What is ML?", user="user123")
print(response["response"])

# WebSocket interface - non-streaming (same signature)
socket_flow = api.socket().flow("default")
response = socket_flow.agent(question="What is ML?", user="user123")
print(response["response"])

# WebSocket interface - streaming (new)
for chunk in socket_flow.agent(question="What is ML?", user="user123", streaming=True):
    if isinstance(chunk, AgentThought):
        print(f"Thinking: {chunk.content}")
    elif isinstance(chunk, AgentObservation):
        print(f"Observed: {chunk.content}")
    elif isinstance(chunk, AgentAnswer):
        print(f"Answer: {chunk.content}")
        if chunk.end_of_dialog:
            break
```

**RAG Akışı:**

```python
api = Api(url="http://localhost:8088/")

# REST interface - non-streaming (existing)
rest_flow = api.flow().id("default")
response = rest_flow.graph_rag(question="What is Python?", user="user123", collection="default")
print(response)

# WebSocket interface - streaming (new)
socket_flow = api.socket().flow("default")
for chunk in socket_flow.graph_rag(
    question="What is Python?",
    user="user123",
    collection="default",
    streaming=True
):
    print(chunk.content, end="", flush=True)
    if chunk.end_of_stream:
        break
```

**Toplu İşlemler (Senkron)**:

```python
api = Api(url="http://localhost:8088/")

# Bulk import triples
def triple_generator():
    yield Triple(s="http://ex.com/alice", p="http://ex.com/type", o="Person")
    yield Triple(s="http://ex.com/alice", p="http://ex.com/name", o="Alice")
    yield Triple(s="http://ex.com/bob", p="http://ex.com/type", o="Person")

bulk = api.bulk()
bulk.import_triples(flow="default", triples=triple_generator())

# Bulk export triples
for triple in bulk.export_triples(flow="default"):
    print(f"{triple.s} -> {triple.p} -> {triple.o}")
```

**Toplu İşlemler (Asenkron)**:

```python
import asyncio

async def main():
    api = Api(url="http://localhost:8088/")

    # Async bulk import triples
    async def async_triple_generator():
        yield Triple(s="http://ex.com/alice", p="http://ex.com/type", o="Person")
        yield Triple(s="http://ex.com/alice", p="http://ex.com/name", o="Alice")
        yield Triple(s="http://ex.com/bob", p="http://ex.com/type", o="Person")

    bulk = api.async_bulk()
    await bulk.import_triples(flow="default", triples=async_triple_generator())

    # Async bulk export triples
    async for triple in bulk.export_triples(flow="default"):
        print(f"{triple.s} -> {triple.p} -> {triple.o}")

asyncio.run(main())
```

**Asenkron REST Örneği**:

```python
import asyncio

async def main():
    api = Api(url="http://localhost:8088/")

    # Async REST flow operations
    flow = api.async_flow().id("default")
    response = await flow.agent(question="What is ML?", user="user123")
    print(response["response"])

asyncio.run(main())
```

**Asenkron WebSocket Akışı Örneği**:

```python
import asyncio

async def main():
    api = Api(url="http://localhost:8088/")

    # Async WebSocket streaming
    socket = api.async_socket()
    flow = socket.flow("default")

    async for chunk in flow.agent(question="What is ML?", user="user123", streaming=True):
        if isinstance(chunk, AgentAnswer):
            print(chunk.content, end="", flush=True)
            if chunk.end_of_dialog:
                break

asyncio.run(main())
```

### API'ler

#### Yeni API'ler

1. **Temel API Sınıfı**:
   **Senkron**:
     `Api.socket()` - Senkron WebSocket istemcisini al
     `Api.bulk()` - Senkron toplu işlem istemcisini al
     `Api.metrics()` - Senkron ölçüm istemcisini al
     `Api.close()` - Tüm senkron bağlantıları kapat
     Bağlam yöneticisi desteği (`__enter__`, `__exit__`)
   **Asenkron**:
     `Api.async_flow()` - Asenkron REST akışı istemcisini al
     `Api.async_socket()` - Asenkron WebSocket istemcisini al
     `Api.async_bulk()` - Asenkron toplu işlem istemcisini al
     `Api.async_metrics()` - Asenkron ölçüm istemcisini al
     `Api.aclose()` - Tüm asenkron bağlantıları kapat
     Asenkron bağlam yöneticisi desteği (`__aenter__`, `__aexit__`)

2. **Senkron WebSocket İstemcisi**:
   `SocketClient.flow(flow_id)` - WebSocket akışı örneğini al
   `SocketFlowInstance.agent(..., streaming: bool = False)` - İsteğe bağlı akışla birlikte aracı
   `SocketFlowInstance.text_completion(..., streaming: bool = False)` - İsteğe bağlı akışla birlikte metin tamamlama
   `SocketFlowInstance.graph_rag(..., streaming: bool = False)` - İsteğe bağlı akışla birlikte grafik RAG
   `SocketFlowInstance.document_rag(..., streaming: bool = False)` - İsteğe bağlı akışla birlikte belge RAG
   `SocketFlowInstance.prompt(..., streaming: bool = False)` - İsteğe bağlı akışla birlikte istem
   `SocketFlowInstance.graph_embeddings_query()` - Grafik gömme sorgusu
   Aynı imzaya sahip diğer tüm FlowInstance yöntemleri

3. **Asenkron WebSocket İstemcisi**:
   `AsyncSocketClient.flow(flow_id)` - Asenkron WebSocket akışı örneğini al
   `AsyncSocketFlowInstance.agent(..., streaming: bool = False)` - İsteğe bağlı akışla birlikte asenkron aracı
   `AsyncSocketFlowInstance.text_completion(..., streaming: bool = False)` - İsteğe bağlı akışla birlikte asenkron metin tamamlama
   `AsyncSocketFlowInstance.graph_rag(..., streaming: bool = False)` - İsteğe bağlı akışla birlikte asenkron grafik RAG
   `AsyncSocketFlowInstance.document_rag(..., streaming: bool = False)` - İsteğe bağlı akışla birlikte asenkron belge RAG
   `AsyncSocketFlowInstance.prompt(..., streaming: bool = False)` - İsteğe bağlı akışla birlikte asenkron istem
   `AsyncSocketFlowInstance.graph_embeddings_query()` - Asenkron grafik gömme sorgusu
   Diğer tüm FlowInstance yöntemleri asenkron versiyonlardır

4. **Senkron Toplu İşlem İstemcisi**:
   `BulkClient.import_triples(flow, triples)` - Toplu üçlü içe aktarma
   `BulkClient.export_triples(flow)` - Toplu üçlü dışa aktarma
   `BulkClient.import_graph_embeddings(flow, embeddings)` - Toplu grafik gömme içe aktarma
   `BulkClient.export_graph_embeddings(flow)` - Toplu grafik gömme dışa aktarma
   `BulkClient.import_document_embeddings(flow, embeddings)` - Toplu belge gömme içe aktarma
   `BulkClient.export_document_embeddings(flow)` - Toplu belge gömme dışa aktarma
   `BulkClient.import_entity_contexts(flow, contexts)` - Toplu varlık bağlamları içe aktarma
   `BulkClient.export_entity_contexts(flow)` - Toplu varlık bağlamları dışa aktarma
   `BulkClient.import_objects(flow, objects)` - Toplu nesneler içe aktarma

5. **Asenkron Toplu İşlem İstemcisi**:
   `AsyncBulkClient.import_triples(flow, triples)` - Asenkron toplu üçlü içe aktarma
   `AsyncBulkClient.export_triples(flow)` - Asenkron toplu üçlü dışa aktarma
   `AsyncBulkClient.import_graph_embeddings(flow, embeddings)` - Asenkron toplu grafik gömme içe aktarma
   `AsyncBulkClient.export_graph_embeddings(flow)` - Asenkron toplu grafik gömme dışa aktarma
   `AsyncBulkClient.import_document_embeddings(flow, embeddings)` - Asenkron toplu belge gömme içe aktarma
   `AsyncBulkClient.export_document_embeddings(flow)` - Asenkron toplu belge gömme dışa aktarma
   `AsyncBulkClient.import_entity_contexts(flow, contexts)` - Asenkron toplu varlık bağlamları içe aktarma
   `AsyncBulkClient.export_entity_contexts(flow)` - Asenkron toplu varlık bağlamları dışa aktarma
   `AsyncBulkClient.import_objects(flow, objects)` - Asenkron toplu nesneler içe aktarma

6. **Asenkron REST Akışı İstemcisi**:
   `AsyncFlow.list()` - Tüm akışları listele (asenkron)
   `AsyncFlow.get(id)` - Akış tanımını al (asenkron)
   `AsyncFlow.start(...)` - Akışı başlat (asenkron)
   `AsyncFlow.stop(id)` - Akışı durdur (asenkron)
   `AsyncFlow.id(flow_id)` - Asenkron akış örneğini al
   `AsyncFlowInstance.agent(...)` - Asenkron aracı yürütme
   `AsyncFlowInstance.text_completion(...)` - Asenkron metin tamamlama
   `AsyncFlowInstance.graph_rag(...)` - Asenkron grafik RAG
   Diğer tüm FlowInstance yöntemleri asenkron versiyonlardır

7. **Ölçüm İstemcileri**:
   `Metrics.get()` - Senkron Prometheus ölçümleri
   `AsyncMetrics.get()` - Asenkron Prometheus ölçümleri

8. **REST Akışı API Geliştirmesi**:
   `FlowInstance.graph_embeddings_query()` - Grafik gömme sorgusu (senkron özellik uyumluluğu)
   `AsyncFlowInstance.graph_embeddings_query()` - Grafik gömme sorgusu (asenkron özellik uyumluluğu)

#### Değiştirilen API'ler

1. **Kurucu** (küçük bir iyileştirme):
   ```python
   Api(url: str, timeout: int = 60, token: Optional[str] = None)
   ```
   `token` parametresi eklendi (isteğe bağlı, kimlik doğrulama için)
   Eğer `None` belirtilmemişse (varsayılan): Kimlik doğrulama kullanılmıyor
   Eğer belirtilmişse: REST için bearer token olarak kullanılır (`Authorization: Bearer <token>`), WebSocket için sorgu parametresi olarak kullanılır (`?token=<token>`)
   Başka bir değişiklik yok - tamamen geriye dönük uyumlu

2. **Kırıcı Değişiklikler Yok**:
   Tüm mevcut REST API yöntemleri değişmedi
   Tüm mevcut imzalar korunmuş
   Tüm mevcut dönüş türleri korunmuş

### Uygulama Detayları

#### Hata Yönetimi

**WebSocket Bağlantı Hataları**:
```python
try:
    api = Api(url="http://localhost:8088/")
    socket = api.socket()
    socket_flow = socket.flow("default")
    response = socket_flow.agent(question="...", user="user123")
except ConnectionError as e:
    print(f"WebSocket connection failed: {e}")
    print("Hint: Ensure Gateway is running and WebSocket endpoint is accessible")
```

**Zarif Yedekleme:**
```python
api = Api(url="http://localhost:8088/")

try:
    # Try WebSocket streaming first
    socket_flow = api.socket().flow("default")
    for chunk in socket_flow.agent(question="...", user="...", streaming=True):
        print(chunk.content)
except ConnectionError:
    # Fall back to REST non-streaming
    print("WebSocket unavailable, falling back to REST")
    rest_flow = api.flow().id("default")
    response = rest_flow.agent(question="...", user="...")
    print(response["response"])
```

**Kısmi Akış Hataları**:
```python
api = Api(url="http://localhost:8088/")
socket_flow = api.socket().flow("default")

accumulated = []
try:
    for chunk in socket_flow.graph_rag(question="...", streaming=True):
        accumulated.append(chunk.content)
        if chunk.error:
            print(f"Error occurred: {chunk.error}")
            print(f"Partial response: {''.join(accumulated)}")
            break
except Exception as e:
    print(f"Streaming error: {e}")
    print(f"Partial response: {''.join(accumulated)}")
```

#### Kaynak Yönetimi

**Bağlam Yöneticisi Desteği**:
```python
# Automatic cleanup
with Api(url="http://localhost:8088/") as api:
    socket_flow = api.socket().flow("default")
    response = socket_flow.agent(question="...", user="user123")
# All connections automatically closed

# Manual cleanup
api = Api(url="http://localhost:8088/")
try:
    socket_flow = api.socket().flow("default")
    response = socket_flow.agent(question="...", user="user123")
finally:
    api.close()  # Explicitly close all connections (WebSocket, bulk, etc.)
```

#### İş parçacığı ve Eşzamanlılık

**İş Parçacığı Güvenliği**:
Her `Api` örneği kendi bağlantısını korur.
WebSocket taşıma katmanı, iş parçacığı güvenli istek çoklama için kilitler kullanır.
Birden fazla iş parçacığı, bir `Api` örneğini güvenli bir şekilde paylaşabilir.
Akış iteratörleri iş parçacığı güvenli değildir (tek iş parçacığından tüketilir).

**Asenkron Destek** (gelecek planlar):
```python
# Phase 2 enhancement (not in initial scope)
import asyncio

async def main():
    api = await AsyncApi(url="ws://localhost:8088/")
    flow = api.flow().id("default")

    async for chunk in flow.agent(question="...", streaming=True):
        print(chunk.content)

    await api.close()

asyncio.run(main())
```

## Güvenlik Hususları

### Kimlik Doğrulama

**Token Parametresi**:
```python
# No authentication (default)
api = Api(url="http://localhost:8088/")

# With authentication
api = Api(url="http://localhost:8088/", token="mytoken")
```

**REST İletim Yöntemi**:
Taşıyıcı belirteci, `Authorization` başlığı aracılığıyla
Tüm REST isteklerine otomatik olarak uygulanır
Format: `Authorization: Bearer <token>`

**WebSocket İletim Yöntemi**:
Belirteç, WebSocket URL'sine eklenen bir sorgu parametresi aracılığıyla
Bağlantı kurulması sırasında otomatik olarak uygulanır
Format: `ws://localhost:8088/api/v1/socket?token=<token>`

**Uygulama**:
```python
class SocketClient:
    def _connect(self) -> WebSocket:
        # Construct WebSocket URL with optional token
        ws_url = f"{self.url}/api/v1/socket"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"
        # Connect to WebSocket
        return websocket.connect(ws_url)
```

**Örnek:**
```python
# REST with auth
api = Api(url="http://localhost:8088/", token="mytoken")
flow = api.flow().id("default")
# All REST calls include: Authorization: Bearer mytoken

# WebSocket with auth
socket = api.socket()
# Connects to: ws://localhost:8088/api/v1/socket?token=mytoken
```

### Güvenli İletişim

Hem WS (WebSocket) hem de WSS (WebSocket Secure) şemalarını destekler.
WSS bağlantıları için TLS sertifika doğrulaması.
Geliştirme için isteğe bağlı sertifika doğrulama devre dışı bırakma (uyarı ile).

### Girdi Doğrulama

URL şemalarını (http, https, ws, wss) doğrula.
Taşıma parametre değerlerini doğrula.
Akış parametre kombinasyonlarını doğrula.
Toplu veri türlerini doğrula.

## Performans Hususları

### Gecikme İyileştirmeleri

**Akışlı LLM İşlemleri**:
**İlk token'a ulaşma süresi**: ~500ms (akışsız ise ~30 saniye)
**İyileşme**: Algılanan performansta 60 kat daha hızlı.
**Kullanım alanları**: Ajan, Grafik RAG, Belge RAG, Metin Tamamlama, İstek.

**Sürekli Bağlantılar**:
**Bağlantı ek yükü**: Sonraki istekler için ortadan kaldırılmıştır.
**WebSocket el sıkışması**: Tek seferlik maliyet (~100ms).
**Kullanım alanları**: WebSocket taşıma yöntemini kullanırken tüm işlemler için geçerlidir.

### Verim İyileştirmeleri

**Toplu İşlemler**:
**Üçlü veri aktarımı**: ~10.000 üçlü/saniye (REST ile tek öğe için ~100/saniye)
**Gömme veri aktarımı**: ~5.000 gömme/saniye (REST ile tek öğe için ~50/saniye)
**İyileşme**: Toplu işlemler için 100 kat daha yüksek verim.

**İstek Çoklama**:
**Eşzamanlı istekler**: Tek bağlantı üzerinden 15'e kadar eşzamanlı istek.
**Bağlantı yeniden kullanımı**: Eşzamanlı işlemler için bağlantı ek yükü yok.

### Bellek Hususları

**Akışlı Yanıtlar**:
Sabit bellek kullanımı (parçalar geldiği gibi işlenir).
Tam yanıtın tamponlanması yok.
Çok uzun çıktılar (>1MB) için uygundur.

**Toplu İşlemler**:
Yineleyici tabanlı işleme (sabit bellek).
Tüm veri kümesinin belleğe yüklenmesi yok.
Milyonlarca öğeye sahip veri kümeleri için uygundur.

### Karşılaştırmalar (Beklenen)

| İşlem | REST (mevcut) | WebSocket (akışlı) | İyileşme |
|-----------|----------------|----------------------|-------------|
| Ajan (ilk token'a ulaşma süresi) | 30s | 0.5s | 60x |
| Grafik RAG (ilk token'a ulaşma süresi) | 25s | 0.5s | 50x |
| 10K üçlü aktarımı | 100s | 1s | 100x |
| 1M üçlü aktarımı | 10.000s (2.7h) | 100s (1.6m) | 100x |
| 10 eşzamanlı küçük istek | 5s (sıralı) | 0.5s (paralel) | 10x |

## Test Stratejisi

### Birim Testleri

**Taşıma Katmanı** (`test_transport.py`):
REST taşıma isteklerini/yanıtlarını test et
WebSocket taşıma bağlantısını test et
WebSocket taşıma bağlantısının yeniden kurulmasını test et
İstek çoklama işlemini test et
Akış yanıtı ayrıştırmasını test et
Belirli testler için sahte WebSocket sunucusu oluştur

**API Yöntemleri** (`test_flow.py`, `test_library.py`, vb.):
Sahte taşıma ile yeni yöntemleri test et
Akış parametrelerinin işlenmesini test et
Toplu işlem yineleyicilerini test et
Hata işleme işlemlerini test et

**Türler** (`test_types.py`):
Yeni akış parçacık türlerini test et
Tür serileştirme/deserileştirme işlemlerini test et

### Entegrasyon Testleri

**Uçtan Uca REST** (`test_integration_rest.py`):
Tüm işlemleri gerçek Ağ geçidine karşı test et (REST modu)
Geriye dönük uyumluluğu doğrula
Hata koşullarını test et

**Uçtan Uca WebSocket** (`test_integration_websocket.py`):
Tüm işlemleri gerçek Ağ geçidine karşı test et (WebSocket modu)
Akış işlemlerini test et
Toplu işlemleri test et
Eşzamanlı istekleri test et
Bağlantı kurtarma işlemlerini test et

**Akış Hizmetleri** (`test_streaming_integration.py`):
Ajan akışını (düşünceler, gözlemler, yanıtlar) test et
RAG akışını (artımlı parçalar) test et
Metin tamamlama akışını (token-by-token) test et
İstem akışını test et
Akış sırasında hata işleme işlemlerini test et

**Toplu İşlemler** (`test_bulk_integration.py`):
Üçlülerin toplu olarak aktarılmasını/dışa aktarılmasını test et (1K, 10K, 100K öğe)
Gömme verilerinin toplu olarak aktarılmasını/dışa aktarılmasını test et
Toplu işlemler sırasında bellek kullanımını test et
İlerleme takibini test et

### Performans Testleri

**Gecikme Ölçümleri** (`test_performance_latency.py`):
İlk tokene kadar geçen süreyi ölç (akışlı vs. akışsız)
Bağlantı ek yükünü ölç (REST vs WebSocket)
Beklenen ölçümlerle karşılaştır

**Verim Ölçümleri** (`test_performance_throughput.py`):
Toplu aktarım verimini ölç
İstek çoklama verimliliğini ölç
Beklenen ölçümlerle karşılaştır

### Uyumluluk Testleri

**Geriye Dönük Uyumluluk** (`test_backward_compatibility.py`):
Mevcut test paketini yeniden düzenlenmiş API'ye karşı çalıştır
Herhangi bir uyumsuz değişikliğin olmadığını doğrulayın
Yaygın kalıplar için geçiş yolunu test edin

## Geçiş Planı

### 1. Aşama: Şeffaf Geçiş (Varsayılan)

**Kodda herhangi bir değişiklik gerekli değil**. Mevcut kod çalışmaya devam ediyor:

```python
# Existing code works unchanged
api = Api(url="http://localhost:8088/")
flow = api.flow().id("default")
response = flow.agent(question="What is ML?", user="user123")
```

### 2. Aşama: İsteğe Bağlı Yayın (Basit)

**Yayınlamayı etkinleştirmek için `api.socket()` arayüzünü kullanın:**

```python
# Before: Non-streaming REST
api = Api(url="http://localhost:8088/")
rest_flow = api.flow().id("default")
response = rest_flow.agent(question="What is ML?", user="user123")
print(response["response"])

# After: Streaming WebSocket (same parameters!)
api = Api(url="http://localhost:8088/")  # Same URL
socket_flow = api.socket().flow("default")

for chunk in socket_flow.agent(question="What is ML?", user="user123", streaming=True):
    if isinstance(chunk, AgentAnswer):
        print(chunk.content, end="", flush=True)
```

**Önemli Noktalar**:
Hem REST hem de WebSocket için aynı URL
Aynı yöntem imzaları (kolay geçiş)
Sadece `.socket()` ve `streaming=True` ekleyin

### 3. Aşama: Toplu İşlemler (Yeni Özellik)

Büyük veri kümeleri için `api.bulk()` arayüzünü kullanın:

```python
# Before: Inefficient per-item operations
api = Api(url="http://localhost:8088/")
flow = api.flow().id("default")

for triple in my_large_triple_list:
    # Slow per-item operations
    # (no direct bulk insert in REST API)
    pass

# After: Efficient bulk loading
api = Api(url="http://localhost:8088/")  # Same URL
bulk = api.bulk()

# This is fast (10,000 triples/second)
bulk.import_triples(flow="default", triples=iter(my_large_triple_list))
```

### Dokümantasyon Güncellemeleri

1. **README.md**: Akış ve WebSocket örnekleri ekleyin
2. **API Referansı**: Tüm yeni yöntemleri ve parametreleri belgeleyin
3. **Yükseltme Kılavuzu**: Akışı etkinleştirmek için adım adım kılavuz
4. **Örnekler**: Yaygın kalıplar için örnek betikler ekleyin
5. **Performans Kılavuzu**: Beklenen performans iyileştirmelerini belgeleyin

### Kullanımdan Kaldırma Politikası

**Herhangi bir kullanımdan kaldırma yok**. Tüm mevcut API'ler desteklenmeye devam ediyor. Bu, yalnızca bir geliştirmedir.

## Zaman Çizelgesi

### 1. Hafta: Temel
Taşıma soyutlama katmanı
Mevcut REST kodunu yeniden düzenleyin
Taşıma katmanı için birim testleri
Geriye dönük uyumluluk doğrulaması

### 2. Hafta: WebSocket Taşıyıcısı
WebSocket taşıyıcısı uygulaması
Bağlantı yönetimi ve yeniden bağlanma
İstek çoklama
Birim ve entegrasyon testleri

### 3. Hafta: Akış Desteği
LLM yöntemlerine akış parametresi ekleyin
Akış yanıtı ayrıştırmasını uygulayın
Akış parçacığı türleri ekleyin
Akış entegrasyon testleri

### 4. Hafta: Toplu İşlemler
Toplu içe/dışa aktarma yöntemleri ekleyin
Yineleyici tabanlı işlemleri uygulayın
Performans testi
Toplu işlem entegrasyon testleri

### 5. Hafta: Özellik Eşdeğerliği ve Dokümantasyon
Grafik gömme sorgusu ekleyin
Ölçüm API'si ekleyin
Kapsamlı dokümantasyon
Yükseltme kılavuzu
Yayın adayı

### 6. Hafta: Yayın
Son entegrasyon testleri
Performans karşılaştırması
Yayın dokümantasyonu
Topluluk duyurusu

**Toplam Süre**: 6 hafta

## Açık Sorular

### API Tasarımı Soruları

1. **Asenkron Destek**: ✅ **ÇÖZÜLDÜ** - Tam asenkron destek, ilk sürümde dahil edilmiştir
   Tüm arayüzlerin asenkron varyantları vardır: `async_flow()`, `async_socket()`, `async_bulk()`, `async_metrics()`
   Senkron ve asenkron API'ler arasında tam bir simetri sağlar
   Modern asenkron çerçeveler (FastAPI, aiohttp) için gereklidir

2. **İlerleme İzleme**: Toplu işlemler, ilerleme geri çağırmalarını desteklemeli mi?
   ```python
   def progress_callback(processed: int, total: Optional[int]):
       print(f"Processed {processed} items")

   bulk.import_triples(flow="default", triples=triples, on_progress=progress_callback)
   ```
   **Öneri**: 2. Faz'da ekleyin. İlk sürüm için kritik değil.

3. **Akış Zaman Aşımı**: Akış işlemlerinde zaman aşımını nasıl ele almalıyız?
   **Öneri**: Akış dışı işlemler için aynı zaman aşımını kullanın, ancak her parça alındığında sıfırlayın.

4. **Parça Önbelleği**: Parçaları önbelleğe almalı mıyız yoksa hemen geri mi vermeliyiz?
   **Öneri**: En düşük gecikme için hemen geri verin.

5. **WebSocket Üzerinden Küresel Hizmetler**: `api.socket()`, küresel hizmetleri (kütüphane, bilgi, koleksiyon, yapılandırma) desteklemeli mi yoksa yalnızca akışla ilgili hizmetleri mi?
   **Öneri**: Başlangıçta yalnızca akışla ilgili hizmetlerle başlayın (akışın önemli olduğu yerlerde). Gerekirse 2. Faz'da küresel hizmetleri ekleyin.

### Uygulama Soruları

1. **WebSocket Kütüphanesi**: `websockets`, `websocket-client` veya `aiohttp`'yi kullanmalı mıyız?
   **Öneri**: `websockets` (asenkron, olgun, iyi bakılan). `asyncio.run()` kullanarak senkron bir arayüzle sarın.

2. **Bağlantı Havuzu**: Birden çok eşzamanlı `Api` örneğinin bir bağlantı havuzunu paylaşmasına izin vermeli miyiz?
   **Öneri**: 2. Faz'a bırakın. Her `Api` örneğinin başlangıçta kendi bağlantıları vardır.

3. **Bağlantı Geri Dönüşümü**: `SocketClient` ve `BulkClient` aynı WebSocket bağlantısını mı kullanmalı, yoksa ayrı bağlantılar mı kullanmalı?
   **Öneri**: Ayrı bağlantılar. Daha basit uygulama, daha net sorumluluk ayrımı.

4. **Gecikmeli vs. Hızlı Bağlantı**: WebSocket bağlantısı `api.socket()` içinde mi yoksa ilk istekte mi kurulmalı?
   **Öneri**: Gecikmeli (ilk istekte). Kullanıcı yalnızca REST yöntemlerini kullanıyorsa, bağlantı ek yükünden kaçının.

### Test Soruları

1. **Sahte Ağ Geçidi**: Test için hafif bir sahte Ağ Geçidi mi oluşturmalıyız, yoksa gerçek Ağ Geçidi üzerinde mi test yapmalıyız?
   **Öneri**: Her ikisi de. Birim testleri için sahte nesneler kullanın, entegrasyon testleri için gerçek Ağ Geçidi'ni kullanın.

2. **Performans Geri Dönüşüm Testleri**: Otomatik performans geri dönüşüm testlerini CI'a eklemeli miyiz?
   **Öneri**: Evet, ancak CI ortamındaki değişkenliği hesaba katmak için cömert eşiklerle.

## Referanslar

### İlgili Teknik Özellikler
`docs/tech-specs/streaming-llm-responses.md` - Ağ Geçidi'ndeki akış uygulaması
`docs/tech-specs/rag-streaming-support.md` - RAG akış desteği

### Uygulama Dosyaları
`trustgraph-base/trustgraph/api/` - Python API kaynağı
`trustgraph-flow/trustgraph/gateway/` - Ağ Geçidi kaynağı
`trustgraph-flow/trustgraph/gateway/dispatch/mux.py` - WebSocket çoklayıcı referans uygulaması

### Belgeler
`docs/apiSpecification.md` - Tam API referansı
`docs/api-status-summary.md` - API durumu özeti
`README.websocket` - WebSocket protokolü belgeleri
`STREAMING-IMPLEMENTATION-NOTES.txt` - Akış uygulama notları

### Harici Kütüphaneler
`websockets` - Python WebSocket kütüphanesi (https://websockets.readthedocs.io/)
`requests` - Python HTTP kütüphanesi (mevcut)
