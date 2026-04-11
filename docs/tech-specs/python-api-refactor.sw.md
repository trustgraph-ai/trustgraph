# Vipangilio vya Kisaikolojia la API ya Python

## Muhtasari

Vipangilio hivi vinaelezea marekebisho kamili ya maktaba ya mteja wa API ya Python ya TrustGraph ili kufikia utendaji sawa na API Gateway na kuongeza ufuatiliaji wa mitindo ya kisasa ya mawasiliano ya muda halisi.

Marekebisho haya yanashughulikia matumizi manne makuu:

1. **Mwingiliano wa LLM wa Msururu**: Ruhusu utiririshaji wa wakati halisi wa majibu ya LLM (wakala, RAG ya chati, RAG ya hati, kukamilisha maandishi, maagizo) na kuchelewesha chini ya ~60x (500ms dhidi ya 30s kwa tokeni ya kwanza)
2. **Operesheni za Data za Kiasi**: Unga uingizaji/utoaji wa data nyingi wa triples, uingizaji wa chati, na uingizaji wa hati kwa usimamizi wa grafu kubwa.
3. **Ulinganishi wa Vipengele**: Hakikisha kila mwisho wa API Gateway una mbinu inayolingana ya API ya Python, pamoja na swali la uingizaji wa chati.
4. **Miunganisho ya Kudumu**: Ruhusu mawasiliano ya WebSocket kwa maombi ya kuzingatia na kupunguza gharama ya muunganisho.

## Lengo

**Ulinganishi wa Vipengele**: Huduma kila Gateway API ina mbinu inayolingana ya API ya Python
**Ufuatiliaji**: Huduma zote za ufuatiliaji (wakala, RAG, kukamilisha maandishi, agizo) zinaunga mkono ufuatiliaji katika API ya Python
**Usafirishaji wa WebSocket**: Ongeza safu ya usafirishaji ya hiari ya WebSocket kwa miunganisho ya kudumu na kuzingatia
**Operesheni za Kiasi**: Ongeza uingizaji/utoaji wa data nyingi wa triples, uingizaji wa chati, na uingizaji wa hati
**Ufuatiliaji Kamili**: Utekelezaji kamili wa async/wait kwa interfaces zote (REST, WebSocket, operesheni za kiasi, metrics)
**Ulinganisho na Msimu wa Uendeshaji**: Msimu wa uendeshaji wa sasa unaendelea kufanya kazi bila mabadiliko
**Usalama wa Aina**: Dumishe interfaces za usalama wa aina na dataclasses na vidokezo vya aina
**Uboreshaji wa Hatua kwa Hatua**: Ufuatiliaji na async ni chaguo kupitia uteuzi wa wazi wa interface
**Utendaji**: Pata uboreshaji wa kuchelewesha wa 60x kwa operesheni za ufuatiliaji
**Python ya Kisasa**: Usaidizi wa paradigm za sync na async kwa uwezekano mwingi

## Asili

### Hali ya Sasa

API ya Python (`trustgraph-base/trustgraph/api/`) ni maktaba ya mteja ya REST pekee na moduli zifuatazo:

`flow.py`: Usimamizi wa mtiririko na huduma za mtiririko (mbinu 50)
`library.py`: Operesheni za maktaba ya hati (mbinu 9)
`knowledge.py`: Usimamizi wa msingi wa KG (mbinu 4)
`collection.py`: Metadata ya mkusanyiko (mbinu 3)
`config.py`: Usimamizi wa usanidi (mbinu 6)
`types.py`: Ufafanuzi wa aina ya data (dataclasses 5)

**Operesheni Jumla**: 50/59 (ufafanuzi wa 85%)

### Mapungufu ya Sasa

**Operesheni Zinazokosekana**:
Swali la uingizaji wa chati (utafutaji wa kiufundi juu ya vitu vya chati)
Uingizaji/utoaji wa data nyingi wa triples, uingizaji wa chati, uingizaji wa hati, muktadha wa vitu, vitu
Mwisho wa metrics

**Uwezekano Usio Kutosha**:
Usaidizi wa utiririshaji kwa huduma za LLM
Usafirishaji wa WebSocket
Maombi mengi yanayotendua wakati mmoja
Muunganisho unaoendelea

**Matatizo ya Utendaji**:
Kuchelewesha kwa muda kwa mwingiliano wa LLM (~sekunde 30 hadi tokeni ya kwanza)
Usafirishaji usio na ufanisi wa data kwa wingi (ombi la REST kwa kila kipengele)
Mizigo ya muunganisho kwa operesheni nyingi mfululizo

**Matatizo ya Uzoefu wa Mtumiaji**:
Hakuna maoni ya wakati halisi wakati wa uzalishaji wa LLM
Haiwezekani kughairi operesheni ndefu za LLM
Uwezo duni wa kuongezeka kwa operesheni kwa wingi

### Athari

Uboresho wa utiririshaji wa Novemba 2024 kwa API ya Gateway uliweka uboreshaji wa ucheleweshaji wa mara 60 (ms 500 dhidi ya sekunde 30 ya tokeni ya kwanza) kwa mwingiliano wa LLM, lakini watumiaji wa API ya Python hawawezi kutumia uwezo huu. Hii huunda pengo kubwa la uzoefu kati ya watumiaji wa Python na wasio wa Python.

## Muundo wa Kiufundi

### Usanifu

API ya Python iliyoboreshwa hutumia **mbinu ya kiolesura ya moduli** na vitu tofauti kwa mifumo tofauti ya mawasiliano. Violesho vyote vinapatikana katika matoleo **ya wakati mmoja na ya isiyo ya wakati mmoja**:

1. **Kiolesho cha REST** (kipo, kimeboreshwa)
   **Sync**: `api.flow()`, `api.library()`, `api.knowledge()`, `api.collection()`, `api.config()`
   **Async**: `api.async_flow()`
   Ombi/jibu la wakati mmoja/la isiyo ya wakati mmoja
   Mfumo rahisi wa muunganisho
   Chaguo-msingi kwa utangamano wa nyuma

2. **Kiolesho cha WebSocket** (kipo)
   **Sync**: `api.socket()`
   **Async**: `api.async_socket()`
   Muunganisho unaoendelea
   Maombi yaliyounganishwa
   Usaidizi wa utiririshaji
   Alama sawa za mbinu kama REST ambapo utendaji unapanuka

3. **Kiolesho cha Operesheni kwa Wingi** (kipo)
   **Sync**: `api.bulk()`
   **Async**: `api.async_bulk()`
   Kulingana na WebSocket kwa ufanisi
   Import/export kulingana na Iterator/AsyncIterator
   Hushughulikia data kubwa

4. **Kiolesho cha Metrics** (kipo)
   **Sync**: `api.metrics()`
   **Async**: `api.async_metrics()`
   Ufikiaji wa metrics ya Prometheus

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

**Kanuni Muhimu za Ubunifu**:
**URL moja kwa kila aina ya muunganisho**: `Api(url="http://localhost:8088/")` inafanya kazi kwa aina zote.
**Ulinganisho kati ya utendaji wa papo hapo na usio wa papo hapo**: Kila aina ya muunganisho ina matoleo ya utendaji wa papo hapo na yasiyo wa papo hapo yenye saini sawa za mbinu.
**Saini sawa**: Pale ambapo utendaji unapanuka, saini za mbinu ni sawa kati ya REST na WebSocket, utendaji wa papo hapo na usio wa papo hapo.
**Uboreshaji wa hatua kwa hatua**: Chagua aina ya muunganisho kulingana na mahitaji (REST kwa mambo rahisi, WebSocket kwa utiririshaji, Bulk kwa data kubwa, utendaji usio wa papo hapo kwa mifumo ya kisasa).
**Lengo lililo wazi**: `api.socket()` inaonyesha WebSocket, `api.async_socket()` inaonyesha WebSocket ya utendaji usio wa papo hapo.
**Inafaa na mifumo ya zamani**: Msimbo uliopo haubahatishwi.

### Vipengele

#### 1. Darasa la API Kuu (Imebadilishwa)

Moduli: `trustgraph-base/trustgraph/api/api.py`

**Darasa la API Lililoboreshwa**:

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

#### 2. Mteja wa WebSocket wa Moja kwa Moja

Moduli: `trustgraph-base/trustgraph/api/socket_client.py` (mpya)

**Darasa la SocketClient**:

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

**Sifa Muhimu**:
Muunganisho wa polepole (unaunganisha tu wakati ombi la kwanza lilitumwa)
Uunganishaji wa ombi ( hadi 15 ufuatiliaji)
Muunganisho wa kiotomatiki unapokatika
Uchanganuzi wa jibu la utiririshaji
Uendeshaji salama wa uzi
Kifungashio cha usawisi kwa maktaba ya websockets isiyo na usawisi

#### 3. Mteja wa WebSocket Usio na Usawisi

Moduli: `trustgraph-base/trustgraph/api/async_socket_client.py` (mpya)

**Darasa la AsyncSocketClient**:

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

**Sifa Muhimu**:
Usaidizi wa asilia wa async/await.
Ufanisi kwa matumizi ya async (FastAPI, aiohttp).
Hakuna kuzuiliwa kwa uzi.
Muundo sawa na toleo la sync.
AsyncIterator kwa utiririshaji.

#### 4. Mteja wa Operesheni za Kiasi za Synchronous

Moduli: `trustgraph-base/trustgraph/api/bulk_client.py` (mpya)

**Darasa la BulkClient**:

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

**Sifa Muhimu**:
Inatumia itereja ili kuhakikisha matumizi thabiti ya kumbukumbu.
Miunganisho maalum ya WebSocket kwa kila operesheni.
Ufuatiliaji wa maendeleo (rudisho la hiari).
Usimamizi wa makosa na ripoti ya mafanikio ya kiasi.

#### 5. Mteja wa Operesheni za Kiasi za Asynchronous

Moduli: `trustgraph-base/trustgraph/api/async_bulk_client.py` (mpya)

**Darasa la AsyncBulkClient**:

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

**Sifa Muhimu**:
Inatumia AsyncIterator kwa matumizi thabiti ya kumbukumbu.
Inafaa kwa matumizi ya asynchronous.
Inasaidia natively async/await.
Ina interface sawa na toleo la synchronous.

#### 6. API ya Mtiririko wa REST (Synchronous - Haibadiliki)

Moduli: `trustgraph-base/trustgraph/api/flow.py`

API ya Mtiririko wa REST inabaki **haiibadiliki kabisa** kwa utangamano wa nyuma. Njia zote zilizopo zinaendelea kufanya kazi:

`Flow.list()`, `Flow.start()`, `Flow.stop()`, n.k.
`FlowInstance.agent()`, `FlowInstance.text_completion()`, `FlowInstance.graph_rag()`, n.k.
Alama zote zilizopo na aina za kurudi zimehifadhiwa.

**Mpya**: Ongeza `graph_embeddings_query()` kwenye REST FlowInstance kwa utangamano wa vipengele:

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

#### 7. API ya Mtiririko wa REST Asynchronous

Moduli: `trustgraph-base/trustgraph/api/async_flow.py` (mpya)

**Darasa za AsyncFlow na AsyncFlowInstance**:

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

**Vipengele Muhimu**:
Matumizi ya HTTP ya asinkroniki kwa kutumia `aiohttp` au `httpx`
Sauti sawa za mbinu kama API ya REST ya taslimu
Hakuna utiririshaji (tumia `async_socket()` kwa utiririshaji)
Inafaa kwa programu za asinkroniki

#### 8. API ya Vipimo

Moduli: `trustgraph-base/trustgraph/api/metrics.py` (mpya)

**Vipimo vya Taslimu**:

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

**Vipimo Visivyokuwa na Tatizo la Muda (Asynchronous)**:

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

#### 9. Aina Zilizoboreshwa

Moduli: `trustgraph-base/trustgraph/api/types.py` (iliyorekebishwa)

**Aina Mpya**:

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

#### 6. API ya Vipimo

Moduli: `trustgraph-base/trustgraph/api/metrics.py` (mpya)

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

### Mbinu ya Utendaji

#### Awamu ya 1: Kuboresha API Kuu (Wiki ya 1)

1. Ongeza mbinu za `socket()`, `bulk()`, na `metrics()` kwenye darasa la `Api`
2. Lenga utekelezaji wa lazima kwa wateja wa WebSocket na wa wingi
3. Ongeza usaidizi wa meneja wa muktadha (`__enter__`, `__exit__`)
4. Ongeza mbinu ya `close()` kwa usafi
5. Ongeza vipimo vya kitengo kwa maboresho ya darasa la API
6. Hakikisha utangamano wa nyuma

**Utangamano wa Nyuma**: Hakuna mabadiliko ya kuvunja. Mbinu mpya tu.

#### Awamu ya 2: Mteja wa WebSocket (Wiki ya 2-3)

1. Lenga darasa la `SocketClient` na usimamizi wa muunganisho
2. Lenga `SocketFlowInstance` na maelezo sawa kama `FlowInstance`
3. Ongeza usaidizi wa uongezaji wa ombi ( hadi 15 sambamba)
4. Ongeza uchanganuzi wa jibu la utiririsho kwa aina tofauti za sehemu
5. Ongeza mantiki ya kuunganisha tena kiotomatiki
6. Ongeza vipimo na ujumuishaji
7. Andika mifumo ya matumizi ya WebSocket

**Utangamano wa Nyuma**: Kiolesura kipya tu. Hakuna athari kwenye msimbo uliopo.

#### Awamu ya 3: Usaidizi wa Utiririsho (Wiki ya 3-4)

1. Ongeza darasa za aina ya sehemu ya utiririsho (`AgentThought`, `AgentObservation`, `AgentAnswer`, `RAGChunk`)
2. Lenga uchanganuzi wa jibu la utiririsho katika `SocketClient`
3. Ongeza parameter ya utiririsho kwa mbinu zote za LLM katika `SocketFlowInstance`
4. Shughulikia hali za hitilafu wakati wa utiririsho
5. Ongeza vipimo na ujumuishaji kwa utiririsho
6. Ongeza mifano ya utiririsho kwenye hati

**Utangamano wa Nyuma**: Kiolesura kipya tu. API ya REST iliyopo haibadiliki.

#### Awamu ya 4: Operesheni za Wingi (Wiki ya 4-5)

1. Lenga darasa la `BulkClient`
2. Ongeza mbinu za uagizaji/uangavu wa wingi kwa triples, embeddings, muktadha, vitu
3. Lenga usindikaji unaotegemea iterator kwa kumbukumbu thabiti
4. Ongeza ufuatiliaji wa maendeleo (callback ya hiari)
5. Ongeza ushughulikiaji wa hitilafu na ripoti ya mafanikio ya sehemu
6. Ongeza vipimo na ujumuishaji
7. Ongeza mifano ya operesheni za wingi

**Utangamano wa Nyuma**: Kiolesura kipya tu. Hakuna athari kwenye msimbo uliopo.

#### Awamu ya 5: Ulinganishi wa Vipengele na Uboreshaji (Wiki ya 5)

1. Ongeza `graph_embeddings_query()` kwa `FlowInstance` ya REST
2. Lenga darasa la `Metrics`
3. Ongeza vipimo vya ujumuishaji vya kina
4. Upimaji wa utendaji
5. Sasisha hati zote
6. Unda mwongozo wa uhamishaji

**Utangamano wa Nyuma**: Mbinu mpya tu. Hakuna athari kwenye msimbo uliopo.

### Mifano ya Data

#### Uchaguzi wa Kiolesura

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

#### Aina za Majibu ya Utiririshaji

**Utiririshaji wa Wakala:**

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

**Utiririshaji wa RAG**:

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

**Operesheni za Kiasi (Zinazofanya kazi kwa wakati mmoja):**

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

**Operesheni za Kiasi (Zisizo za Moja kwa Moja)**:

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

**Mfano wa REST Asynchronous**:

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

**Mfano wa Utiririshaji wa WebSocket Asynchronous**:

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

### APIs

#### New APIs

1. **Darasa la API Kuu**:
   **Synchronous (Moja kwa Moja)**:
     `Api.socket()` - Pata mteja wa WebSocket moja kwa moja
     `Api.bulk()` - Pata mteja wa shughuli kubwa moja kwa moja
     `Api.metrics()` - Pata mteja wa metriki moja kwa moja
     `Api.close()` - Funga miunganisho yote moja kwa moja
     Usaidizi wa meneja wa muktadha (`__enter__`, `__exit__`)
   **Asynchronous (Isiyo Moja kwa Moja)**:
     `Api.async_flow()` - Pata mteja wa mtiririko wa REST isiyo moja kwa moja
     `Api.async_socket()` - Pata mteja wa WebSocket isiyo moja kwa moja
     `Api.async_bulk()` - Pata mteja wa shughuli kubwa isiyo moja kwa moja
     `Api.async_metrics()` - Pata mteja wa metriki isiyo moja kwa moja
     `Api.aclose()` - Funga miunganisho yote isiyo moja kwa moja
     Usaidizi wa meneja wa muktadha isiyo moja kwa moja (`__aenter__`, `__aexit__`)

2. **Mteja wa WebSocket Moja kwa Moja**:
   `SocketClient.flow(flow_id)` - Pata mfano wa mtiririko wa WebSocket
   `SocketFlowInstance.agent(..., streaming: bool = False)` - Wakala na utiririshaji wa hiari
   `SocketFlowInstance.text_completion(..., streaming: bool = False)` - Kukamilisha maandishi na utiririshaji wa hiari
   `SocketFlowInstance.graph_rag(..., streaming: bool = False)` - Graph RAG na utiririshaji wa hiari
   `SocketFlowInstance.document_rag(..., streaming: bool = False)` - Document RAG na utiririshaji wa hiari
   `SocketFlowInstance.prompt(..., streaming: bool = False)` - Ombi na utiririshaji wa hiari
   `SocketFlowInstance.graph_embeddings_query()` - Uchunguzi wa embeddings ya grafu
   Njia zingine zote za FlowInstance na saini sawa

3. **Mteja wa WebSocket Isiyo Moja kwa Moja**:
   `AsyncSocketClient.flow(flow_id)` - Pata mfano wa mtiririko wa WebSocket isiyo moja kwa moja
   `AsyncSocketFlowInstance.agent(..., streaming: bool = False)` - Wakala isiyo moja kwa moja na utiririshaji wa hiari
   `AsyncSocketFlowInstance.text_completion(..., streaming: bool = False)` - Kukamilisha maandishi isiyo moja kwa moja na utiririshaji wa hiari
   `AsyncSocketFlowInstance.graph_rag(..., streaming: bool = False)` - Async graph RAG na utiririshaji wa hiari
   `AsyncSocketFlowInstance.document_rag(..., streaming: bool = False)` - Async document RAG na utiririshaji wa hiari
   `AsyncSocketFlowInstance.prompt(..., streaming: bool = False)` - Ombi isiyo moja kwa moja na utiririshaji wa hiari
   `AsyncSocketFlowInstance.graph_embeddings_query()` - Uchunguzi wa embeddings ya grafu isiyo moja kwa moja
   Njia zingine zote za FlowInstance kama matoleo isiyo moja kwa moja

4. **Mteja wa Shughuli Kubwa Moja kwa Moja**:
   `BulkClient.import_triples(flow, triples)` - Uingizaji wa triple kubwa
   `BulkClient.export_triples(flow)` - Utoaji wa triple kubwa
   `BulkClient.import_graph_embeddings(flow, embeddings)` - Uingizaji wa embeddings kubwa ya grafu
   `BulkClient.export_graph_embeddings(flow)` - Utoaji wa embeddings kubwa ya grafu
   `BulkClient.import_document_embeddings(flow, embeddings)` - Uingizaji wa embeddings kubwa za hati
   `BulkClient.export_document_embeddings(flow)` - Utoaji wa embeddings kubwa za hati
   `BulkClient.import_entity_contexts(flow, contexts)` - Uingizaji wa muktadha mkubwa wa vitu
   `BulkClient.export_entity_contexts(flow)` - Utoaji wa muktadha mkubwa wa vitu
   `BulkClient.import_objects(flow, objects)` - Uingizaji wa vitu kubwa

5. **Mteja wa Shughuli Kubwa Isiyo Moja kwa Moja**:
   `AsyncBulkClient.import_triples(flow, triples)` - Uingizaji wa triple kubwa isiyo moja kwa moja
   `AsyncBulkClient.export_triples(flow)` - Utoaji wa triple kubwa isiyo moja kwa moja
   `AsyncBulkClient.import_graph_embeddings(flow, embeddings)` - Uingizaji wa embeddings kubwa ya grafu isiyo moja kwa moja
   `AsyncBulkClient.export_graph_embeddings(flow)` - Utoaji wa embeddings kubwa ya grafu isiyo moja kwa moja
   `AsyncBulkClient.import_document_embeddings(flow, embeddings)` - Uingizaji wa embeddings kubwa za hati isiyo moja kwa moja
   `AsyncBulkClient.export_document_embeddings(flow)` - Utoaji wa embeddings kubwa za hati isiyo moja kwa moja
   `AsyncBulkClient.import_entity_contexts(flow, contexts)` - Uingizaji wa muktadha mkubwa wa vitu isiyo moja kwa moja
   `AsyncBulkClient.export_entity_contexts(flow)` - Utoaji wa muktadha mkubwa wa vitu isiyo moja kwa moja
   `AsyncBulkClient.import_objects(flow, objects)` - Uingizaji wa vitu kubwa isiyo moja kwa moja

6. **Mteja wa Mtiririko wa REST Isiyo Moja kwa Moja**:
   `AsyncFlow.list()` - Orodha ya mtiririko wote isiyo moja kwa moja
   `AsyncFlow.get(id)` - Pata ufafanuzi wa mtiririko
   `AsyncFlow.start(...)` - Anzisha mtiririko
   `AsyncFlow.stop(id)` - Simamisha mtiririko
   `AsyncFlow.id(flow_id)` - Pata mfano wa mtiririko
   `AsyncFlowInstance.agent(...)` - Utendaji wa wakala
   `AsyncFlowInstance.text_completion(...)` - Kukamilisha maandishi
   `AsyncFlowInstance.graph_rag(...)` - Graph RAG
   Njia zingine zote za FlowInstance kama matoleo isiyo moja kwa moja

7. **Wateja wa Metriki**:
   `Metrics.get()` - Metriki za Prometheus moja kwa moja
   `AsyncMetrics.get()` - Metriki za Prometheus isiyo moja kwa moja

8. **Uboreshaji wa API ya Mtiririko wa REST**:
   `FlowInstance.graph_embeddings_query()` - Uchunguzi wa embeddings ya grafu (ufanano wa kipengele cha moja kwa moja)
   `AsyncFlowInstance.graph_embeddings_query()` - Uchunguzi wa embeddings ya grafu (ufanano wa kipengele cha isiyo moja kwa moja)

#### APIs Iliyorekebishwa

1. **Mawasiliano** (uboreshaji mdogo):
   ```python
   Api(url: str, timeout: int = 60, token: Optional[str] = None)
   ```
   Imeongezwa parameter `token` (hiari, kwa ajili ya uthibitishaji).
   Ikiwa `None` (kiwango chachilia): Hakuna uthibitishaji unaotumika.
   Ikiwa imeingizwa: Inatumika kama tokeni ya "bearer" kwa REST (`Authorization: Bearer <token>`), parameter ya swali kwa WebSocket (`?token=<token>`).
   Hakuna mabadiliko mengine - inafaa kabisa na matoleo ya awali.

2. **Hakuna Mabadiliko Yanayoweza Kusababisha Tatizo**:
   Njia zote za API za REST zilizopo hazijabadilika.
   Alama zote zilizopo zimehifadhiwa.
   Aina zote za matokeo zilizopo zimehifadhiwa.

### Maelezo ya Utendaji

#### Usimamizi wa Madhira

**Madhira ya Muunganisho wa WebSocket**:
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

**Rudi Nyuma kwa Ufasaha**:
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

**Hitilafu za Uhamisho wa Takwimu:**
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

#### Usimamizi wa Rasilimali

**Usaidizi wa Kidhibiti wa Mazingira:**
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

#### Uunganishaji na Uendeshaji Sambamba

**Ulinzi wa Mfumo wa Uendeshaji (Thread Safety)**:
Kila mfano wa `Api` huendeleza muunganisho wake mwenyewe.
Usafirishaji wa WebSocket hutumia kufuli kwa ajili ya uunganishaji salama wa ombi.
Mitandao mingi inaweza kushiriki mfano wa `Api` kwa usalama.
Iterators za utiririshaji hazina ulinzi wa mfumo wa uendeshaji (zinatumika kutoka kwenye mtandao mmoja).

**Usaidizi wa Async** (tazama baadaye):
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

## Mambo ya Kuzingatia ya Usalama

### Uthibitisho

**Parameta ya Tokeni**:
```python
# No authentication (default)
api = Api(url="http://localhost:8088/")

# With authentication
api = Api(url="http://localhost:8088/", token="mytoken")
```

**Usafirishaji (Transport) wa REST:**
Alama ya utambulisho (Bearer token) kupitia kichwa (header) cha `Authorization`
Inatumika kiotomatiki kwa ombi zote za REST
Muundo: `Authorization: Bearer <token>`

**Usafirishaji (Transport) wa WebSocket:**
Alama ya utambulisho (Token) kupitia parameter ya swali (query parameter) iliyoongezwa kwenye URL ya WebSocket
Inatumika kiotomatiki wakati wa kuunganisha
Muundo: `ws://localhost:8088/api/v1/socket?token=<token>`

**Utekelezaji (Implementation):**
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

**Mfano**:
```python
# REST with auth
api = Api(url="http://localhost:8088/", token="mytoken")
flow = api.flow().id("default")
# All REST calls include: Authorization: Bearer mytoken

# WebSocket with auth
socket = api.socket()
# Connects to: ws://localhost:8088/api/v1/socket?token=mytoken
```

### Mawasiliano Salama

Inasaidia mifumo ya WS (WebSocket) na WSS (WebSocket Secure).
Uthibitisho wa cheti cha TLS kwa miunganisho ya WSS.
Uthibitisho wa cheti unaweza kuzimwa (hiari) kwa ajili ya maendeleo (na onyo).

### Uthibitisho wa Data

Uthibitisho wa aina za URL (http, https, ws, wss).
Uthibitisho wa thamani za vigezo vya usafirishaji.
Uthibitisho wa mchanganyiko wa vigezo vya utiririshaji.
Uthibitisho wa aina za data za uagizaji wa jumla.

## Masuala ya Utendaji

### Uboreshaji wa Ucheleweshaji

**Operesheni za LLM za Utiririshaji**:
**Wakati wa tokeni ya kwanza**: ~500ms (dhidi ya ~30s bila utiririshaji)
**Uboreshaji**: Mara 60 haraka kuliko utendaji unaohisiwa.
**Inatumika kwa**: Wakala, Graph RAG, Document RAG, Kukamilisha Nakala, Ombi.

**Miunganisho ya Kudumu**:
**Mzigo wa muunganisho**: Huondolewa kwa ombi zijazo.
**Utambulisho wa WebSocket**: Gharama ya mara moja (~100ms).
**Inatumika kwa**: Operesheni zote wakati wa kutumia usafirishaji wa WebSocket.

### Uboreshaji wa Kiasi

**Operesheni za Jumla**:
**Uagizaji wa triples**: ~10,000 triples/sekunde (dhidi ya ~100/sekunde na REST kwa kila kipengele).
**Uagizaji wa embeddings**: ~5,000 embeddings/sekunde (dhidi ya ~50/sekunde na REST kwa kila kipengele).
**Uboreshaji**: Mara 100 ya kasi kwa operesheni za jumla.

**Uongezaji wa Maombi**:
**Maombi sambamba**: Hadi maombi 15 sambamba juu ya muunganisho mmoja.
**Matumizi ya muunganisho**: Hakuna mzigo wa muunganisho kwa operesheni sambamba.

### Masuala ya Kumbukumbu

**Majibu ya Utiririshaji**:
Matumizi ya kumbukumbu thabiti (prosesa vipande kadri wanavyofika).
Hakuna kuhifadhi kwa jibu kamili.
Inafaa kwa matokeo marefu sana (>1MB).

**Operesheni za Jumla**:
Uchakataji wa msingi (matumizi ya kumbukumbu thabiti).
Hakuna kupakia kwa seti data yote kwenye kumbukumbu.
Inafaa kwa seti data zilizo na milioni ya vipengele.

### Vipimo (Yanatarajiwa)

| Operesheni | REST (ya sasa) | WebSocket (ya utiririshaji) | Uboreshaji |
|-----------|----------------|----------------------|-------------|
| Wakala (wakati wa tokeni ya kwanza) | 30s | 0.5s | 60x |
| Graph RAG (wakati wa tokeni ya kwanza) | 25s | 0.5s | 50x |
| Uagizaji wa triples 10K | 100s | 1s | 100x |
| Uagizaji wa triples 1M | 10,000s (2.7h) | 100s (1.6m) | 100x |
| Maombi madogo 10 sambamba | 5s (mfululizo) | 0.5s (sambamba) | 10x |

## Mkakati wa Majaribio

### Majaribio ya Kitengo

**Safu ya Usafirishaji** (`test_transport.py`):
Jaribu ombi na majibu ya usafirishaji wa REST
Jaribu muunganisho wa usafirishaji wa WebSocket
Jaribu muunganisho wa upya wa usafirishaji wa WebSocket
Jaribu uunganishaji wa ombi
Jaribu uchanganuzi wa majibu ya utiririshaji
Unda seva bandia ya WebSocket kwa vipimo vya uhakika

**Mbinu za API** (`test_flow.py`, `test_library.py`, n.k.):
Jaribu mbinu mpya ukitumia usafirishaji bandia
Jaribu usimamizi wa vigezo vya utiririshaji
Jaribu vichanganuzi vya operesheni za wingi
Jaribu usimamizi wa makosa

**Aina** (`test_types.py`):
Jaribu aina mpya za vipande vya utiririshaji
Jaribu userikali/kusierikisha aina

### Vipimo vya Uunganisho

**REST Kamili** (`test_integration_rest.py`):
Jaribu operesheni zote dhidi ya Lango halisi (mode ya REST)
Hakikisha utangamano wa nyuma
Jaribu hali za makosa

**WebSocket Kamili** (`test_integration_websocket.py`):
Jaribu operesheni zote dhidi ya Lango halisi (mode ya WebSocket)
Jaribu operesheni za utiririshaji
Jaribu operesheni za wingi
Jaribu ombi la wakati mmoja
Jaribu urejesho wa muunganisho

**Huduma za Utiririshaji** (`test_streaming_integration.py`):
Jaribu utiririshaji wa wakala (mawazo, uchunguzi, majibu)
Jaribu utiririshaji wa RAG (vipande vya hatua kwa hatua)
Jaribu utiririshaji wa kukamilisha maandishi (token kwa token)
Jaribu utiririshaji wa ombi
Jaribu usimamizi wa makosa wakati wa utiririshaji

**Operesheni za Wingi** (`test_bulk_integration.py`):
Jaribu uingizaji/utoaji wa wingi wa vitri (vitu 1K, 10K, 100K)
Jaribu uingizaji/utoaji wa wingi wa uainishaji
Jaribu matumizi ya kumbukumbu wakati wa operesheni za wingi
Jaribu ufuatiliaji wa maendeleo

### Vipimo vya Utendaji

**Viashiria vya Kuchelewesha** (`test_performance_latency.py`):
Pima muda wa tokeni ya kwanza (utiririshaji dhidi ya usio na utiririshaji)
Pima gharama ya muunganisho (REST dhidi ya WebSocket)
Linganisha na viashiria vya kutarajiwa

**Viashiria vya Ufanisi** (`test_performance_throughput.py`):
Pima ufanisi wa uingizaji wa wingi
Pima ufanisi wa uunganishaji wa ombi
Linganisha na viashiria vya kutarajiwa

### Vipimo vya Utangamano

**Utangamano wa Nyuma** (`test_backward_compatibility.py`):
Endesha seti ya vipimo iliyopo dhidi ya API iliyobadilishwa
Hakikisha hakuna mabadiliko ya kuvunja utangamano
Jaribu njia ya uhamishaji kwa mifumo ya kawaida

## Mpango wa Uhamishaji

### Awamu ya 1: Uhamishaji Wazi (Chaguo-msingi)

**Hakuna mabadiliko ya msimbo yanayohitajika**. Msimbo uliopo unaendelea kufanya kazi:

```python
# Existing code works unchanged
api = Api(url="http://localhost:8088/")
flow = api.flow().id("default")
response = flow.agent(question="What is ML?", user="user123")
```

### Awamu ya 2: Uidhinishaji wa Utiririshaji (Rahisi)

**Tumia kiolesura `api.socket()`** ili kuwezesha utiririshaji:

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

**Pointi Muhimu**:
URL sawa kwa REST na WebSocket.
Saini sawa za mbinu (rahisi kuhamisha).
Ongeza tu `.socket()` na `streaming=True`.

### Awamu ya 3: Operesheni za Kiasi (Uwezo Mpya)

**Tumia kiolesura cha `api.bulk()`** kwa data kubwa:

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

### Sasisho la Nyaraka

1. **README.md**: Ongeza mifano ya utiririshaji na WebSocket
2. **Marejeleo ya API**: Andika mbinu na vigezo vyote vipya
3. **Mwongozo wa Uhamishaji**: Mwongozo wa hatua kwa hatua wa kuwezesha utiririshaji
4. **Mifano**: Ongeza skripti ya mfano kwa mifumo ya kawaida
5. **Mwongozo wa Utendaji**: Andika uboreshaji uliotarajiwa wa utendaji

### Sera ya Kutolewa

**Hakuna kutolewa**. API zote zilizopo zinaendelea kuungwa mkono. Hii ni uboreshaji safi.

## Ratiba

### Wiki ya 1: Msingi
Safu ya abstraction ya usafirishaji
Tengeneza upya msimbo wa REST uliopo
Vipimo vya kitengo kwa safu ya usafirishaji
Uthibitisho wa utangamano wa nyuma

### Wiki ya 2: Usafirishaji wa WebSocket
Utendaji wa usafirishaji wa WebSocket
Usimamizi wa muunganisho na muunganisho upya
Ufuatiliaji wa ombi
Vipimo vya kitengo na ushirikiano

### Wiki ya 3: Usaidizi wa Utiririshaji
Ongeza kiparamu cha utiririshaji kwa mbinu za LLM
Tengeneza utiririshaji wa jibu
Ongeza aina za vipande vya utiririshaji
Vipimo vya ushirikiano vya utiririshaji

### Wiki ya 4: Operesheni za Kiasi
Ongeza mbinu za kuingiza/kutoa kwa wingi
Tengeneza operesheni zinazotegemea iterator
Upimaji wa utendaji
Vipimo vya ushirikiano vya operesheni za wingi

### Wiki ya 5: Ulinganisho wa Vipengele na Nyaraka
Ongeza swali la uingizaji wa michoro
Ongeza API ya metriki
Nyaraka kamili
Mwongozo wa uhamishaji
Mfumo wa majaribio

### Wiki ya 6: Toa
Vipimo vya mwisho vya ushirikiano
Upimaji wa utendaji
Nyaraka za kutolewa
Tangazo la jumuiya

**Jumla ya Muda**: wiki 6

## Maswali ya Wazi

### Maswali ya Ubunifu wa API

1. **Usaidizi wa Async**: ✅ **IMEONGELEWA** - Usaidizi kamili wa async umejumuishwa katika toleo la awali
   Interfeisi zote zina matoleo ya async: `async_flow()`, `async_socket()`, `async_bulk()`, `async_metrics()`
   Hutoa usawa kamili kati ya API za sync na async
   Muhimu kwa mifumo ya kisasa ya async (FastAPI, aiohttp)

2. **Ufuatiliaji wa Maendeleo**: Je, operesheni za wingi zinapaswa kusaidia callbacks za maendeleo?
   ```python
   def progress_callback(processed: int, total: Optional[int]):
       print(f"Processed {processed} items")

   bulk.import_triples(flow="default", triples=triples, on_progress=progress_callback)
   ```
   **Pendekezo**: Ongezewe katika Hatua ya 2. Si muhimu kwa toleo la awali.

3. **Mipangilio ya Muda wa Kitendo cha Uhamisho (Streaming)**: Je, tunapaswa kushughulikia vipi vipindi vya muda ambavyo vitatokea wakati wa vitendo vya uhamishaji?
   **Pendekezo**: Tumia muda sawa kama vitendo visivyohusisha uhamishaji, lakini uweke upya kila wakati unapopokea sehemu (chunk).

4. **Uwekaji Hifadhi wa Sehemu (Chunk Buffering)**: Je, tunapaswa kuweka sehemu katika hifadhi au kuzitoa mara moja?
   **Pendekezo**: Zitoa mara moja ili kupunguza zaidi kuchelewesha.

5. **Huduma za Kimataifa kupitia WebSocket**: Je, `api.socket()` inapaswa kusaidia huduma za kimataifa (maktaba, maarifa, mkusanyiko, usanidi) au tu huduma zinazohusiana na kila uhamishaji?
   **Pendekezo**: Anza tu na huduma zinazohusiana na kila uhamishaji (ambapo uhamishaji una umuhimu). Ongeza huduma za kimataifa ikiwa ni lazima katika Hatua ya 2.

### Maswali ya Utendaji

1. **Maktaba ya WebSocket**: Je, tunapaswa kutumia `websockets`, `websocket-client`, au `aiohttp`?
   **Pendekezo**: `websockets` (ya kisasa, iliyokamilika, na inayohudumiwa vizuri). Ifunike katika muundo wa kazi (synchronous) kwa kutumia `asyncio.run()`.

2. **Uunganishaji wa Pamoja (Connection Pooling)**: Je, tunapaswa kusaidia mifano mingi ya `Api` inayoshiriki muunganisho mmoja?
   **Pendekezo**: Acha hadi Hatua ya 2. Kila mfano wa `Api` una muunganisho wake mwenyewe mwanzo.

3. **Matumizi ya Muunganisho**: Je, `SocketClient` na `BulkClient` zinapaswa kushiriki muunganisho mmoja wa WebSocket, au kutumia muunganisho tofauti?
   **Pendekezo**: Muunganisho tofauti. Utendaji rahisi, upeo wa wazi.

4. **Muunganisho wa Kwanza au wa Baadaye**: Je, muunganisho wa WebSocket unapaswa kuundwa katika `api.socket()` au wakati wa ombi la kwanza?
   **Pendekezo**: Muunganisho wa baadaye (wakati wa ombi la kwanza). Inazuia gharama ya muunganisho ikiwa mtumiaji hutumia tu mbinu za REST.

### Maswali ya Majaribio

1. **Lango la Majaribio (Mock Gateway)**: Je, tunapaswa kuunda lango la majaribio (mock) ambalo ni rahisi kwa ajili ya majaribio, au tujaribu dhidi ya lango halisi?
   **Pendekezo**: Zote. Tumia lango la majaribio kwa majaribio ya kitengo, na lango halisi kwa majaribio ya ujumuishaji.

2. **Majaribio ya Utendaji (Performance Regression Tests)**: Je, tunapaswa kuongeza majaribio ya utendaji (performance) ya kiotomatiki katika mfumo wa CI (Continuous Integration)?
   **Pendekezo**: Ndiyo, lakini na viwango vikubwa vya uvumilivu ili kuzingatia tofauti katika mazingira ya CI.

## Marejeleo

### Vipimo vya Teknolojia Vilivyohusiana
`docs/tech-specs/streaming-llm-responses.md` - Utaratibu wa utiririshaji katika lango.
`docs/tech-specs/rag-streaming-support.md` - Usaidizi wa utiririshaji wa RAG.

### Faili za Utendaji
`trustgraph-base/trustgraph/api/` - Chanzo cha API ya Python.
`trustgraph-flow/trustgraph/gateway/` - Chanzo cha lango.
`trustgraph-flow/trustgraph/gateway/dispatch/mux.py` - Utaratibu wa marejeleo wa mchanganyiko wa WebSocket.

### Nyaraka
`docs/apiSpecification.md` - Marejeleo kamili ya API.
`docs/api-status-summary.md` - Muhtasari wa hali ya API.
`README.websocket` - Nyaraka za itifaki ya WebSocket.
`STREAMING-IMPLEMENTATION-NOTES.txt` - Maelezo kuhusu utaratibu wa utiririshaji.

### Maktabu ya Nje
`websockets` - Maktaba ya WebSocket ya Python (https://websockets.readthedocs.io/).
`requests` - Maktaba ya HTTP ya Python (ilipo tayari).
