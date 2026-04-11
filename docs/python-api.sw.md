# Marejeleo ya API ya Python ya TrustGraph

## Ufungaji

```bash
pip install trustgraph
```

## Kuanza Haraka

Madarasa na aina zote zinaingizwa kutoka kwenye kifurushi cha `trustgraph.api`:

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

## Jina la Yaliyomo

### Msingi

[Api](#api)

### Wateja wa Flow

[Flow](#flow)
[FlowInstance](#flowinstance)
[AsyncFlow](#asyncflow)
[AsyncFlowInstance](#asyncflowinstance)

### Wateja wa WebSocket

[SocketClient](#socketclient)
[SocketFlowInstance](#socketflowinstance)
[AsyncSocketClient](#asyncsocketclient)
[AsyncSocketFlowInstance](#asyncsocketflowinstance)

### Operesheni za Kiasi

[BulkClient](#bulkclient)
[AsyncBulkClient](#asyncbulkclient)

### Vipimo

[Metrics](#metrics)
[AsyncMetrics](#asyncmetrics)

### Aina za Data

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

### Vizuizi

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

Mteja mkuu wa API ya TrustGraph kwa operesheni za synchronous na asynchronous.

Darasa hili hutoa ufikiaji kwa huduma zote za TrustGraph, pamoja na usimamizi wa mtiririko,
operesheni za grafu ya maarifa, usindikaji wa hati, maswali ya RAG, na zaidi. Inasaidia
mifumo ya mawasiliano ya msingi wa REST na WebSocket.

Mteja unaweza kutumika kama meneja wa muktadha kwa usafi wa kiotomatiki wa rasilimali:
    ```python
    with Api(url="http://localhost:8088/") as api:
        result = api.flow().id("default").graph_rag(query="test")
    ```

### Mbinu

### `__aenter__(self)`

Ingia katika meneja wa muktadha wa asinkroni.

### `__aexit__(self, *args)`

Ondoka katika meneja wa muktadha wa asinkroni na ufungue miunganisho.

### `__enter__(self)`

Ingia katika meneja wa muktadha wa sinkroni.

### `__exit__(self, *args)`

Ondoka katika meneja wa muktadha wa sinkroni na ufungue miunganisho.

### `__init__(self, url='http://localhost:8088/', timeout=60, token: str | None = None)`

Anzisha mteja wa API ya TrustGraph.

**Vigezo:**

`url`: URL ya msingi kwa API ya TrustGraph (kiwango chachilia: "http://localhost:8088/"")
`timeout`: Muda wa kikao wa ombi katika sekunde (kiwango chachilia: 60)
`token`: Tokeni ya kuhudhuria ya hiari kwa uthibitishaji

**Mfano:**

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

Funga miunganisho yote ya mteja isiyo ya kawaida.

Njia hii inafunga miunganisho ya WebSocket isiyo ya kawaida, operesheni kubwa, na miunganisho ya mtiririko.
Inaitwa kiotomatiki wakati wa kutoka katika meneja wa muktadha usio wa kawaida.

**Mfano:**

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

Pata mteja wa operesheni za wingi zisizo za moja kwa moja.

Hutoa operesheni za uagizaji/uangamizi za wingi kwa mtindo wa async/await kupitia WebSocket
kwa ajili ya usimamizi bora wa data kubwa.

**Inarudisha:** AsyncBulkClient: Mteja wa operesheni za wingi zisizo za moja kwa moja.

**Mfano:**

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

Pata mteja wa mtiririko (flow) unaotumia REST na unaoweza kufanya kazi bila kusubiri.

Hutoa ufikiaji wa operesheni za mtiririko kwa mtindo wa async/await. Hii inapendelewa
kwa programu na mifumo ya Python inayotumia async (FastAPI, aiohttp, n.k.).

**Inarudisha:** AsyncFlow: Mteja wa mtiririko (flow) usiofanya kazi bila kusubiri.

**Mfano:**

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

Pata mteja wa metriki zisizo za moja kwa moja.

Hutoa ufikiaji wa mtindo wa async/await kwa metriki za Prometheus.

**Inarudisha:** AsyncMetrics: Mteja wa metriki zisizo za moja kwa moja.

**Mfano:**

```python
async_metrics = api.async_metrics()
prometheus_text = await async_metrics.get()
print(prometheus_text)
```

### `async_socket(self)`

Pata mteja wa WebSocket usio na utaratibu kwa operesheni za utiririshaji.

Hutoa ufikiaji wa WebSocket wa aina ya async/await pamoja na usaidizi wa utiririshaji.
Hii ndiyo njia inayopendekezwa kwa utiririshaji usio na utaratibu katika Python.

**Inarudisha:** AsyncSocketClient: Mteja wa WebSocket usio na utaratibu.

**Mfano:**

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

Pata mteja wa shughuli za wingi za moja kwa moja kwa ajili ya uagizaji/utoaji.

Shughuli za wingi huruhusu uhamishaji wa ufanisi wa data kubwa kupitia muunganisho wa WebSocket,
ikiwa ni pamoja na vitu vitatu, maandamano, muktadha wa vitu, na vitu.

**Inarudisha:** BulkClient: Mteja wa shughuli za wingi za moja kwa moja.

**Mfano:**

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

Funga miunganisho yote ya mteja ya wakati huo.

Njia hii inafunga miunganisho ya WebSocket na miunganisho ya operesheni kubwa.
Inaitwa kiotomatiki wakati wa kutoka katika meneja wa muktadha.

**Mfano:**

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

Pata mteja wa Collection kwa ajili ya kusimamia makusanyo ya data.

Makusanyo huandaa hati na data ya mfumo wa maarifa katika
vikundi vya mantiki kwa ajili ya kutenganisha na udhibiti wa ufikiaji.

**Inarudisha:** Collection: Mteja wa usimamizi wa Collection

**Mfano:**

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

Pata mteja wa Config kwa ajili ya kusimamia mipangilio.

**Inarudisha:** Config: Mteja wa usimamizi wa mipangilio.

**Mfano:**

```python
config = api.config()

# Get configuration values
values = config.get([ConfigKey(type="llm", key="model")])

# Set configuration
config.put([ConfigValue(type="llm", key="model", value="gpt-4")])
```

### `flow(self)`

Pata programu (client) ya Flow kwa ajili ya kusimamia na kuingiliana na michakato.

Michakato (Flows) ni vitengo vikuu vya utekelezaji katika TrustGraph, ikitoa ufikiaji kwa
huduma kama vile wakala, maswali ya RAG, maandamano, na usindikaji wa nyaraka.

**Inarudisha:** Flow: Programu ya usimamizi wa Flow.

**Mfano:**

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

Pata mteja wa Knowledge kwa ajili ya kusimamia msingi wa grafu ya maarifa.

**Inarudisha:** Mteja wa usimamizi wa grafu ya maarifa: Knowledge

**Mfano:**

```python
knowledge = api.knowledge()

# List available KG cores
cores = knowledge.list_kg_cores(user="trustgraph")

# Load a KG core
knowledge.load_kg_core(id="core-123", user="trustgraph")
```

### `library(self)`

Pata mteja wa Maktaba kwa usimamizi wa nyaraka.

Maktaba hutoa uhifadhi wa nyaraka, usimamizi wa metadata, na
uratibu wa mtiririko wa kazi.

**Inarudisha:** Library: Mteja wa usimamizi wa maktaba ya nyaraka.

**Mfano:**

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

Pata mteja wa metriki wa moja kwa moja kwa ajili ya ufuatiliaji.

Hupata metriki zilizofunganishwa kwa muundo wa Prometheus kutoka kwa huduma ya TrustGraph
kwa ajili ya ufuatiliaji na uwezeshaji.

**Inarudisha:** Metri: Mteja wa metriki wa moja kwa moja

**Mfano:**

```python
metrics = api.metrics()
prometheus_text = metrics.get()
print(prometheus_text)
```

### `request(self, path, request)`

Fanya ombi la API ya REST ya kiwango cha chini.

Njia hii hutumika hasa kwa matumizi ya ndani, lakini inaweza kutumika kwa ufikiaji wa moja kwa moja
wa API wakati inahitajika.

**Vigezo:**

`path`: Njia ya mwisho ya API (kulingana na URL ya msingi)
`request`: Takwimu ya ombi kama kamusi

**Inarudisha:** dict: Kijisimu cha majibu

**Inatirisha:**

`ProtocolException`: Ikiwa hali ya majibu si 200 au majibu hayana umbizo la JSON
`ApplicationException`: Ikiwa majibu yana kosa

**Mfano:**

```python
response = api.request("flow", {
    "operation": "list-flows"
})
```

### `socket(self)`

Pata mteja wa WebSocket wa aina ya moja kwa shughuli za utiririshaji.

Miunganisho ya WebSocket hutoa utiifu wa data kwa majibu ya muda halisi
kutoka kwa wakala, maswali ya RAG, na kukamilisha maandishi. Njia hii inarudisha
kifungashio cha aina ya moja kilichozunguka itifaki ya WebSocket.

**Inarudisha:** SocketClient: Mteja wa WebSocket wa aina ya moja.

**Mfano:**

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

Mteja wa usimamizi wa mtiririko kwa operesheni za muundo na mfano wa mtiririko.

Darasa hili hutoa mbinu za kusimamia muundo wa mtiririko (vipengele) na
mifano ya mtiririko (mitiririko inayoendelea). Vipengele vinafafanua muundo na
vigezo vya mitiririko, wakati mifano inawakilisha mitiririko inayofanya kazi ambayo
inaweza kutekeleza huduma.

### Mbinu

### `__init__(self, api)`

Anzisha mteja wa mtiririko.

**Majadiliano:**

`api`: Eneo la awali la Api kwa kutuma ombi.

### `delete_blueprint(self, blueprint_name)`

Futa muundo wa mtiririko.

**Majadiliano:**

`blueprint_name`: Jina la muundo kufutwa.

**Mfano:**

```python
api.flow().delete_blueprint("old-blueprint")
```

### `get(self, id)`

Pata ufafanuzi wa mfano unaoendelea.

**Vigezo:**

`id`: Kitambulisho cha mfano.

**Inarudisha:** dict: Ufafanuzi wa mfano.

**Mfano:**

```python
flow_def = api.flow().get("default")
print(flow_def)
```

### `get_blueprint(self, blueprint_name)`

Pata ufafanuzi wa mpango (blueprint) kwa jina.

**Vigezo:**

`blueprint_name`: Jina la mpango (blueprint) ambao unataka kupata

**Inarudisha:** dict: Ufafanuzi wa mpango (blueprint) kama kamusi.

**Mfano:**

```python
blueprint = api.flow().get_blueprint("default")
print(blueprint)  # Blueprint configuration
```

### `id(self, id='default')`

Pata FlowInstance ili kutekeleza shughuli kwenye mtiririko maalum.

**Vigezo:**

`id`: Kitambulisho cha mtiririko (cha kawaida: "default")

**Inarudisha:** FlowInstance: Mtiririko wa huduma kwa shughuli.

**Mfano:**

```python
flow = api.flow().id("my-flow")
response = flow.text_completion(
    system="You are helpful",
    prompt="Hello"
)
```

### `list(self)`

Orodha ya matukio yote yanayoendelea.

**Inarudisha:** list[str]: Orodha ya kitambulisho cha matukio.

**Mfano:**

```python
flows = api.flow().list()
print(flows)  # ['default', 'flow-1', 'flow-2', ...]
```

### `list_blueprints(self)`

Orodha ya mipango yote ya mtiririko inayopatikana.

**Inarudisha:** list[str]: Orodha ya majina ya mipango

**Mfano:**

```python
blueprints = api.flow().list_blueprints()
print(blueprints)  # ['default', 'custom-flow', ...]
```

### `put_blueprint(self, blueprint_name, definition)`

Kuunda au kusasisha mpango wa mtiririko.

**Vigezo:**

`blueprint_name`: Jina la mpango
`definition`: Kamusi ya ufafanuzi wa mpango

**Mfano:**

```python
definition = {
    "services": ["text-completion", "graph-rag"],
    "parameters": {"model": "gpt-4"}
}
api.flow().put_blueprint("my-blueprint", definition)
```

### `request(self, path=None, request=None)`

Fanya ombi la API katika eneo maalum.

**Vigezo:**

`path`: Ongeza ya hiari kwa njia za mwisho za eneo.
`request`: Kamusi ya data ya ombi.

**Inarudisha:** dict: Kitu kinachojibu.

**Inayotokea:**

`RuntimeError`: Ikiwa parameter ya ombi haijatolewa.

### `start(self, blueprint_name, id, description, parameters=None)`

Anza eneo jipya kutoka kwa mpango.

**Vigezo:**

`blueprint_name`: Jina la mpango ambao utaanzishwa.
`id`: Kitambulisho cha kipekee kwa eneo.
`description`: Maelezo ambayo yanaweza kueleweka.
`parameters`: Vigezo vya hiari.

**Mfano:**

```python
api.flow().start(
    blueprint_name="default",
    id="my-flow",
    description="My custom flow",
    parameters={"model": "gpt-4"}
)
```

### `stop(self, id)`

Kusimamisha mfumo unaoendelea.

**Vigezo:**

`id`: Kitambulisho cha mfumo unaoendelea ili kusimamishwa.

**Mfano:**

```python
api.flow().stop("my-flow")
```


--

## `FlowInstance`

```python
from trustgraph.api import FlowInstance
```

Mteja wa mfumo (flow) kwa kutekeleza huduma kwenye mfumo maalum.

Darasa hili hutoa ufikiaji kwa huduma zote za TrustGraph, pamoja na:
Kukamilisha maandishi na uwekaji wa data (embeddings)
Utendaji wa wakala (agent) pamoja na usimamizi wa hali (state)
Ufuatiliaji wa maswali (queries) ya RAG kwa grafu na nyaraka
Utendaji wa grafu ya maarifa (triples, vitu)
Kupakua na kuchakata nyaraka
Ubadilishaji wa lugha ya asili kuwa swali la GraphQL
Uchambuzi wa data iliyopangwa na utambuzi wa muundo (schema)
Utendaji wa zana ya MCP
Ubunifu wa kigezo cha swali (prompt templating)

Huduma zinapatikana kupitia mfumo unaoendelea (flow instance) unaotambulika na kitambulisho (ID).

### Mbinu (Methods)

### `__init__(self, api, id)`

Anzisha FlowInstance.

**Majadilisho:**

`api`: Mteja wa mfumo (flow) wa juu.
`id`: Kitambulisho cha mfumo unaoendelea (flow instance).

### `agent(self, question, user='trustgraph', state=None, group=None, history=None)`

Tekeleza utendaji wa wakala (agent) pamoja na uwezo wa kufikiri na kutumia zana.

Wakala wanaweza kufanya utafakari wa hatua nyingi, kutumia zana, na kudumisha mazungumzo
hali katika mwingiliano. Hii ni toleo la moja kwa moja (synchronous) lisilo na utiririshaji (non-streaming).

**Majadilisho:**

`question`: Swali au maagizo ya mtumiaji.
`user`: Kitambulisho cha mtumiaji (default: "trustgraph")
`state`: Kamusi ya hali (state) ya hiari kwa mazungumzo yenye hali.
`group`: Kitambulisho cha kikundi cha hiari kwa muktadha wa watumiaji wengi.
`history`: Historia ya mazungumzo ya hiari kama orodha ya maneno ya kamusi.

**Inarudisha:** string: Jibu la mwisho la wakala.

**Mfano:**

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

Gundua aina ya data ya sampuli ya data iliyohifadhiwa.

**Vigezo:**

`sample`: Sampuli ya data kuchanganua (yaliyomo katika maandishi)

**Inarudisha:** kamusi yenye aina_iliyogunduliwa, uaminifu, na metadata ya hiari

### `diagnose_data(self, sample, schema_name=None, options=None)`

Fanya uchunguzi wa pamoja wa data: gundua aina na uundue maelezo.

**Vigezo:**

`sample`: Sampuli ya data kuchanganua (yaliyomo katika maandishi)
`schema_name`: Jina la schema ya lengo la hiari kwa uundaji wa maelezo
`options`: Vigezo vya hiari (k.m., kigawanyo kwa CSV)

**Inarudisha:** kamusi yenye aina_iliyogunduliwa, uaminifu, maelezo, na metadata

### `document_embeddings_query(self, text, user, collection, limit=10)`

Tafuta vipande vya hati kwa kutumia utofauti wa maana.

Inapata vipande vya hati ambavyo yaliyomo katika vipande hivyo yanafanana kwa maana na
maandishi ya ingizo, kwa kutumia uelekezo wa vector.

**Vigezo:**

`text`: Maandishi ya swali kwa utafutaji wa maana
`user`: Kitambulisho cha mtumiaji/nafasi
`collection`: Kitambulisho cha mkusanyiko
`limit`: Nambari ya juu ya matokeo (ya kawaida: 10)

**Inarudisha:** kamusi: Matokeo ya swali yenye vipande vyenye kitambulisho cha kipande na alama

**Mfano:**

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

Tekeleza swali la Uzalishaji Ulioboreshwa na Utafiti (RAG) linalotegemea nyaraka.

RAG ya nyaraka hutumia ufashilia wa vector ili kupata vipande muhimu vya nyaraka,
kisha huunda jibu kwa kutumia LLM (Large Language Model) kwa kutumia vipande hivyo kama muktadha.

**Vigezo:**

`query`: Swali katika lugha ya asili
`user`: Kitambulisho cha mtumiaji/nafasi (cha kawaida: "trustgraph")
`collection`: Kitambulisho cha mkusanyiko (cha kawaida: "default")
`doc_limit`: Vipande vingi vya nyaraka ambavyo vitapatikana (cha kawaida: 10)

**Inarudisha:** string: Jibu lililoundwa ambalo linajumuisha muktadha wa nyaraka

**Mfano:**

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

Toa ufafanuzi wa vector kwa maandishi moja au zaidi.

Hubadilisha maandishi kuwa uwakilishi wa vector mnono unaofaa kwa utafutaji wa maana
na kulinganisha sawa.

**Vigezo:**

`texts`: Orodha ya maandishi ya pembeni ambayo yanahitajika kufafanuliwa

**Inarudisha:** list[list[list[float]]]: Ufafanuzi wa vector, seti moja kwa kila maandishi ya pembeni

**Mfano:**

```python
flow = api.flow().id("default")
vectors = flow.embeddings(["quantum computing"])
print(f"Embedding dimension: {len(vectors[0][0])}")
```

### `generate_descriptor(self, sample, data_type, schema_name, options=None)`

Tengeneza maelezo kwa ajili ya uhusiano wa data iliyopangwa na mpango maalum.

**Vigezo:**

`sample`: Sampuli ya data ya kuchambua (maudhui ya maandishi)
`data_type`: Aina ya data (csv, json, xml)
`schema_name`: Jina la mpango unaolengwa kwa ajili ya utengenezaji wa maelezo
`options`: Vigezo vya hiari (k.m., kigawanyo kwa CSV)

**Inarudisha:** kamusi yenye maelezo na metadata

### `graph_embeddings_query(self, text, user, collection, limit=10)`

Tafuta vitu vya grafu ya maarifa kwa kutumia ufanano wa maana.

Inatafuta vitu katika grafu ya maarifa ambavyo maelezo yake yanafanana
na maandishi yaingizwavyo, kwa kutumia uelekezo wa vector.

**Vigezo:**

`text`: Maandishi ya swali kwa ajili ya utafutaji wa maana
`user`: Kitambulisho cha mtumiaji/nafasi
`collection`: Kitambulisho cha mkusanyiko
`limit`: Nambari ya juu ya matokeo (ya kawaida: 10)

**Inarudisha:** kamusi: Matokeo ya swali na vitu vinavyofanana

**Mfano:**

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

Tekeleza swali la Uzalishaji Ulioboreshwa na Utafutaji (RAG) unaotegemea grafu.

RAG ya grafu hutumia muundo wa grafu ya maarifa ili kupata muktadha unaohusiana kwa
kutumia uhusiano wa vitu, kisha huunda jibu kwa kutumia LLM.

**Vigezo:**

`query`: Swali la lugha ya asili
`user`: Kitambulisho cha mtumiaji/nafasi (cha kawaida: "trustgraph")
`collection`: Kitambulisho cha mkusanyiko (cha kawaida: "default")
`entity_limit`: Vitu vingi zaidi ya kuchuja (cha kawaida: 50)
`triple_limit`: Triples nyingi zaidi kwa kila kitu (cha kawaida: 30)
`max_subgraph_size`: Triples jumla nyingi zaidi katika subgraph (cha kawaida: 150)
`max_path_length`: Kina cha juu zaidi cha utafutaji (cha kawaida: 2)

**Inarudisha:** string: Jibu lililoundwa ambalo linajumuisha muktadha wa grafu

**Mfano:**

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

Pakia hati ya binary ili kuendelea na usindikaji.

Hupakia hati (PDF, DOCX, picha, n.k.) ili kuchukua maelezo na
kuendelea na usindikaji kupitia mchakato wa hati.

**Vigezo:**

`document`: Yaliyomo katika hati kama bytes
`id`: Kitambulisho cha hati cha hiari (kinatengenezwa kiotomatiki ikiwa hakipo)
`metadata`: Meta-data ya hiari (orodha ya Triples au kitu na njia ya emit)
`user`: Kitambulisho cha mtumiaji/nafasi (cha hiari)
`collection`: Kitambulisho cha mkusanyiko (cha hiari)

**Inarudisha:** dict: Jibu la usindikaji

**Inatirisha:**

`RuntimeError`: Ikiwa meta-data imetolewa bila kitambulisho

**Mfano:**

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

Pakia maudhui ya maandishi kwa ajili ya uchakataji.

Hupakia maudhui ya maandishi kwa ajili ya uondoaji na uchakataji kupitia njia ya maandishi ya mtiririko.


**Vigezo:**

`text`: Maudhui ya maandishi kama bytes
`id`: Kitambulisho cha hati cha hiari (kinaundwa kiotomatiki ikiwa hakipo)
`metadata`: Meta data ya hiari (orodha ya Triples au kitu na njia ya emit)
`charset`: Ufuatiliaji wa herufi (kiasi: "utf-8")
`user`: Kitambulisho cha mtumiaji/nafasi (cha hiari)
`collection`: Kitambulisho cha mkusanyiko (cha hiari)

**Inarudisha:** dict: Jibu la uchakataji

**Inayotokea:**

`RuntimeError`: Ikiwa meta data imetolewa bila kitambulisho

**Mfano:**

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

Fanya kazi na zana ya Itifaki ya Mfumo (MCP).

Zana za MCP hutoa utendakazi unaoweza kupanuliwa kwa wakala na michakato,
kuruhusu ujumuishaji na mifumo na huduma za nje.

**Vigezo:**

`name`: Jina/kitambulisho cha zana
`parameters`: Kamusi ya vigezo vya zana (ya kawaida: {})

**Inarudisha:** string au kamusi: Matokeo ya utekelezaji wa zana

**Inatirisha:**

`ProtocolException`: Ikiwa muundo wa majibu hauna uhakika

**Mfano:**

```python
flow = api.flow().id("default")

# Execute a tool
result = flow.mcp_tool(
    name="search-web",
    parameters={"query": "latest AI news", "limit": 5}
)
```

### `nlp_query(self, question, max_results=100)`

Badilisha swali la lugha ya asili kuwa ombi la GraphQL.

**Vigezo:**

`question`: Swali la lugha ya asili
`max_results`: Nambari ya juu ya matokeo yanayorudishwa (ya kawaida: 100)

**Inarudisha:** kamusi yenye graphql_query, variables, detected_schemas, uaminifu

### `prompt(self, id, variables)`

Tekeleza kiolezo cha ombi kwa kubadilisha vigezo.

Kiolezo cha ombi huruhusu muundo wa ombi unaoweza kutumika tena na kubadilisha vigezo,
muhimu kwa uhandisi wa ombi unaoendana.

**Vigezo:**

`id`: Kitambulisho cha kiolezo cha ombi
`variables`: Kamusi ya ulinganisho wa jina la kigezo hadi thamani

**Inarudisha:** string au kamusi: Matokeo ya ombi yaliyobadilishwa (maandishi au kitu kilicho na muundo)

**Inatirisha:**

`ProtocolException`: Ikiwa muundo wa jibu sio sahihi

**Mfano:**

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

Toa ombi la huduma katika toleo hili la mtiririko.

**Vigezo:**

`path`: Njia ya huduma (k.m., "service/text-completion")
`request`: Kamusi ya data ya ombi

**Inarudisha:** dict: Jibu la huduma

### `row_embeddings_query(self, text, schema_name, user='trustgraph', collection='default', index_name=None, limit=10)`

Tafuta data ya mstari kwa kutumia ufanano wa maana kwenye sehemu zilizofichwa.

Inatafuta mistari ambayo maadili ya sehemu zilizofichwa yanafanana kwa maana na
maandishi ya ingizo, kwa kutumia uelekezo wa vector. Hii inaruhusu utafutaji wa "fuzzy"/maana
kwenye data iliyopangwa.

**Vigezo:**

`text`: Maandishi ya swali kwa utafutaji wa maana
`schema_name`: Jina la mpango wa kutafuta ndani
`user`: Kitambulisho cha mtumiaji/nafasi (cha kawaida: "trustgraph")
`collection`: Kitambulisho cha mkusanyiko (cha kawaida: "default")
`index_name`: Jina la fahirisi la hiari ili kuchuja utafutaji kwa fahirisi maalum
`limit`: Idadi ya juu ya matokeo (cha kawaida: 10)

**Inarudisha:** dict: Matokeo ya utafutaji ambayo yana mechi, na yana index_name, index_value, text, na score

**Mfano:**

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

Tekeleza swali la GraphQL dhidi ya safu zilizopangwa katika grafu ya maarifa.

Maswali hutumia data iliyopangwa kwa lugha ya GraphQL, na kuruhusu maswali magumu
yenye kuchujwa, ukusanyaji, na uhusiano.

**Vigezo:**

`query`: Mnyororo wa swali la GraphQL
`user`: Kitambulisho cha mtumiaji/nafasi (cha kawaida: "trustgraph")
`collection`: Kitambulisho cha mkusanyiko (cha kawaida: "default")
`variables`: Kamusi ya vigezo vya swali ya hiari
`operation_name`: Jina la operesheni ya hiari kwa hati za operesheni nyingi

**Inarudisha:** dict: Jibu la GraphQL na sehemu za 'data', 'errors', na/au 'extensions'

**Inatirisha:**

`ProtocolException`: Ikiwa hitilafu ya kiwango cha mfumo hutokea

**Mfano:**

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

Chagua schemas zinazolingana kwa sampuli ya data kwa kutumia uchambuzi wa swali.

**Vigezo:**

`sample`: Sampuli ya data ya kuchambua (maudhui ya maandishi)
`options`: Vigezo vya hiari

**Inarudisha:** kamusi yenye safu ya schema_matches na metadata

### `structured_query(self, question, user='trustgraph', collection='default')`

Tekeleza swali la lugha ya asili dhidi ya data iliyopangwa.
Inachanganya ubadilishaji wa swali la NLP na utekelezaji wa GraphQL.

**Vigezo:**

`question`: Swali la lugha ya asili
`user`: Kitambulisho cha nafasi ya Cassandra (cha kawaida: "trustgraph")
`collection`: Kitambulisho cha mkusanyiko wa data (cha kawaida: "default")

**Inarudisha:** kamusi yenye data na makosa yanayohitajika

### `text_completion(self, system, prompt)`

Tekeleza kukamilisha maandishi kwa kutumia LLM ya mtiririko.

**Vigezo:**

`system`: Swali la mfumo linalobainisha tabia ya msaidizi
`prompt`: Swali/swali la mtumiaji

**Inarudisha:** maandishi: Jibu lililoundwa

**Mfano:**

```python
flow = api.flow().id("default")
response = flow.text_completion(
    system="You are a helpful assistant",
    prompt="What is quantum computing?"
)
print(response)
```

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=10000)`

Tafuta ujuzi wa grapu kwa kutumia utangamano.

Inatafuta triplet za RDF zinazofanana na mada, tabia, na/au
mifumo ya kitu. Vigezo visivyotajwa hufanya kama vichwa vya habari.

**Vigezo:**

`s`: URI ya mada (hiari, tumia None kwa kichwa cha habari)
`p`: URI ya tabia (hiari, tumia None kwa kichwa cha habari)
`o`: URI ya kitu au Literal (hiari, tumia None kwa kichwa cha habari)
`user`: Kitambulisho cha mtumiaji/nafasi (hiari)
`collection`: Kitambulisho cha mkusanyiko (hiari)
`limit`: Matokeo ya juu ya kurejesha (ya kawaida: 10000)

**Inarejea:** list[Triple]: Orodha ya vitu vinavyolingana vya Triple

**Inatiruka:**

`RuntimeError`: Ikiwa s au p si Uri, au o si Uri/Literal

**Mfano:**

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

Mteja wa usimamizi wa mtiririko usio na usawisi, unaotumia API ya REST.

Hutoa operesheni za usimamizi wa mtiririko kulingana na async/await, ikiwa ni pamoja na kuorodhesha,
kuanzisha, kusimamisha mitiririko, na kusimamia ufafanuzi wa darasa la mtiririko. Pia hutoa
ufikiaji wa huduma za mtiririko kama vile wakala, RAG, na maswali kupitia sehemu za mwisho za REST ambazo hazitumii utiririshaji.


Kumbuka: Kwa usaidizi wa utiririshaji, tumia AsyncSocketClient badala yake.

### Mbinu

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Anzisha mteja wa mtiririko usio na usawisi.

**Majadiliano:**

`url`: URL ya msingi ya API ya TrustGraph
`timeout`: Muda wa kuchelewa wa ombi kwa sekunde
`token`: Tokeni ya kuhifadhiwa ya hiari kwa uthibitishaji

### `aclose(self) -> None`

Funga mteja usio na usawisi na safisha rasilimali.

Kumbuka: Usafishaji unashughulikiwa kiotomatiki na meneja wa muktadha wa kikao cha aiohttp.
Mbinu hii hutolewa kwa utangamano na wateja wengine wasio na usawisi.

### `delete_class(self, class_name: str)`

Futa ufafanuzi wa darasa la mtiririko.

Huondoa mpango wa darasa la mtiririko kutoka kwenye mfumo. Haathiri
mifano ya mtiririko inayoruka.

**Majadiliano:**

`class_name`: Jina la darasa la mtiririko kufutwa

**Mfano:**

```python
async_flow = await api.async_flow()

# Delete a flow class
await async_flow.delete_class("old-flow-class")
```

### `get(self, id: str) -> Dict[str, Any]`

Pata ufafanuzi wa mtiririko.

Hupata usanidi kamili wa mtiririko, pamoja na jina lake la darasa,
maelezo, na vigezo.

**Vigezo:**

`id`: Kitambulisho cha mtiririko

**Inarudisha:** dict: Kitu cha ufafanuzi wa mtiririko

**Mfano:**

```python
async_flow = await api.async_flow()

# Get flow definition
flow_def = await async_flow.get("default")
print(f"Flow class: {flow_def.get('class-name')}")
print(f"Description: {flow_def.get('description')}")
```

### `get_class(self, class_name: str) -> Dict[str, Any]`

Pata ufafanuzi wa darasa la mtiririko.

Inapata ufafanuzi wa mpango wa darasa la mtiririko, pamoja na
mpango wake wa usanidi na viunganisho vya huduma.

**Vigezo:**

`class_name`: Jina la darasa la mtiririko

**Inarudisha:** dict: Kitu kinachowakilisha ufafanuzi wa darasa la mtiririko

**Mfano:**

```python
async_flow = await api.async_flow()

# Get flow class definition
class_def = await async_flow.get_class("default")
print(f"Services: {class_def.get('services')}")
```

### `id(self, flow_id: str)`

Pata mteja wa mtiririko wa async.

Inarudisha mteja kwa ajili ya kuingiliana na huduma za mtiririko maalum
(wakala, RAG, maswali, ufumbuzi, n.k.).

**Majadiliano:**

`flow_id`: Kitambulisho cha mtiririko

**Inarudisha:** AsyncFlowInstance: Mteja kwa operesheni maalum za mtiririko

**Mfano:**

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

Orodha ya kitambulisho cha kila mtiririko.

Inapata kitambulisho cha kila mtiririko unaoendeshwa kwa sasa katika mfumo.

**Inarudisha:** list[str]: Orodha ya kitambulisho cha mtiririko

**Mfano:**

```python
async_flow = await api.async_flow()

# List all flows
flows = await async_flow.list()
print(f"Available flows: {flows}")
```

### `list_classes(self) -> List[str]`

Orodha ya majina yote ya darasa la mtiririko.

Inapata majina ya madarasa yote ya mtiririko (mipango) yanayopatikana katika mfumo.

**Inarudisha:** list[str]: Orodha ya majina ya darasa la mtiririko.

**Mfano:**

```python
async_flow = await api.async_flow()

# List available flow classes
classes = await async_flow.list_classes()
print(f"Available flow classes: {classes}")
```

### `put_class(self, class_name: str, definition: Dict[str, Any])`

Kuunda au kusasisha ufafanuzi wa darasa la mtiririko.

Hifadhi mfumo wa darasa la mtiririko ambao unaweza kutumika kuunda mitiririko.

**Vigezo:**

`class_name`: Jina la darasa la mtiririko
`definition`: Kifaa cha ufafanuzi cha darasa la mtiririko

**Mfano:**

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

Fanya ombi la HTTP POST lisilo na usumbufu kwa API ya Gateway.

Njia ya ndani ya kutuma ombi lililo na uthibitisho kwa API ya TrustGraph.

**Vigezo:**

`path`: Njia ya mwisho ya API (kulinganisha na URL ya msingi)
`request_data`: Kamusi ya data inayotumwa kwenye ombi

**Inarudisha:** dict: Kielelezo cha majibu kutoka kwa API

**Inayotokea:**

`ProtocolException`: Ikiwa hali ya HTTP si 200 au majibu hayana umbizo sahihi la JSON
`ApplicationException`: Ikiwa API inarudisha jibu la kosa

### `start(self, class_name: str, id: str, description: str, parameters: Dict | None = None)`

Anzisha mfumo mpya wa utekelezaji.

Huunda na kuanzisha mfumo kutoka kwa ufafanuzi wa darasa la mfumo pamoja na
vigezo vilivyoelezwa.

**Vigezo:**

`class_name`: Jina la darasa la mfumo linalotumiwa
`id`: Kitambulisho cha mfumo mpya
`description`: Maelezo yanayoweza kusomwa na binadamu ya mfumo
`parameters`: Vigezo vya ziada vya usanidi vya mfumo

**Mfano:**

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

Kusimamisha mtiririko unaoendelea.

Inasimamisha na kuondoa mfano wa mtiririko, na kutoa rasilimali zake.

**Vigezo:**

`id`: Kitambulisho cha mtiririko ili kusimamishwa

**Mfano:**

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

Mteja wa mfumo wa kazi usiofanyika kwa wakati mmoja.

Hutoa ufikiaji wa async/await kwa huduma za mfumo wa kazi, ikiwa ni pamoja na wakala,
Maswali ya RAG, maandamano, na maswali ya grafu. Operesheni zote hurudisha
majibu kamili (ya moja kwa moja).

Kumbuka: Kwa usaidizi wa utiririshaji, tumia AsyncSocketFlowInstance.

### Mbinu

### `__init__(self, flow: trustgraph.api.async_flow.AsyncFlow, flow_id: str)`

Anzisha mfumo wa kazi usiofanyika kwa wakati mmoja.

**Majadiliano:**

`flow`: Mteja wa AsyncFlow mkuu
`flow_id`: Kitambulisho cha mfumo wa kazi

### `agent(self, question: str, user: str, state: Dict | None = None, group: str | None = None, history: List | None = None, **kwargs: Any) -> Dict[str, Any]`

Fanya operesheni ya wakala (ya moja kwa moja).

Huendesha wakala kujibu swali, pamoja na hali ya mazungumzo na
historia. Inarudisha jibu kamili baada ya wakala kumaliza
kuchakata.

Kumbuka: Njia hii haitumii utiririshaji. Kwa mawazo na matokeo ya wakala
ya wakati halisi, tumia AsyncSocketFlowInstance.agent() badala yake.

**Majadiliano:**

`question`: Suali au maagizo ya mtumiaji
`user`: Kitambulisho cha mtumiaji
`state`: Kamusi ya hali ya hiari kwa muktadha wa mazungumzo
`group`: Kitambulisho cha kikundi cha hiari kwa usimamizi wa kikao
`history`: Orodha ya historia ya mazungumzo ya hiari
`**kwargs`: Vigezo vya ziada maalum kwa huduma

**Inarudisha:** dict: Jibu kamili la wakala ikiwa ni pamoja na jibu na metadata

**Mfano:**

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

Fanya swali la RAG (Retrieval-Augmented Generation) linalotegemea hati (si mtiririko).

Hufanya Uundaji Ulioboreshwa kwa Upatanishaji kwa kutumia ufichuo wa hati.
Hupata vipande muhimu vya hati kupitia utafutaji wa maana, kisha huunda
jibu linalotegemea hati zilizopatikana. Inarudisha jibu kamili.

Kumbuka: Njia hii haitumii mtiririko. Kwa majibu ya RAG yanayotumia mtiririko,
tumia AsyncSocketFlowInstance.document_rag() badala yake.

**Vigezo:**

`query`: Nakala ya swali la mtumiaji
`user`: Kitambulisho cha mtumiaji
`collection`: Kitambulisho cha mkusanyiko unao na hati
`doc_limit`: Nambari ya juu ya vipande vya hati ambavyo vinaweza kupatikana (kiwango chachilia: 10)
`**kwargs`: Vigezo vya ziada vinavyohusiana na huduma

**Inarudisha:** str: Jibu kamili lililoundwa na linalotegemea data ya hati

**Mfano:**

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

Toa maelezo kwa maandishi ya pembejeo.

Hubadilisha maandishi kuwa uwakilishi wa nambari za vector kwa kutumia
mfumo wa embedding uliopangwa wa mtiririko. Ni muhimu kwa utafutaji wa maana na
ulinganisho wa alama.

**Vigezo:**

`texts`: Orodha ya maandishi ya pembejeo ambayo yanahitajika kuwekwa maelezo.
`**kwargs`: Vigezo vya ziada maalum kwa huduma.

**Inarudisha:** dict: Jibu lenye vector za maelezo.

**Mfano:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Generate embeddings
result = await flow.embeddings(texts=["Sample text to embed"])
vectors = result.get("vectors")
print(f"Embedding dimension: {len(vectors[0][0])}")
```

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any)`

Tafuta ujumuishi wa grafu kwa ajili ya utafutaji wa vitu vya maana.

Hufanya utafutaji wa maana kwenye ujumuishi wa vitu vya grafu ili kupata vitu
ambavyo ni muhimu zaidi kwa maandishi yaliyopo. Inarudisha vitu vilivyopangwa kwa umuhimu.

**Vigezo:**

`text`: Maandishi ya swali kwa utafutaji wa maana
`user`: Kitambulisho cha mtumiaji
`collection`: Kitambulisho cha mkusanyiko unao na ujumuishi wa grafu
`limit`: Nambari ya juu ya matokeo yanayorudishwa (ya kawaida: 10)
`**kwargs`: Vigezo vya ziada maalum kwa huduma

**Inarudisha:** dict: Jibu linalo na vitu vinavyolingana vilivyopangwa pamoja na alama za umuhimu

**Mfano:**

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

Tekeleza swali la RAG linalotegemea grafu (lisilo na utiririshaji).

Hufanya Uundaji Ulioboreshwa na Upatanishaji kwa kutumia data ya grafu ya maarifa.
Hutambua vitu muhimu na uhusiano wao, kisha huunda
jibu ambalo limekithiri katika muundo wa grafu. Inarudisha jibu kamili.

Kumbuka: Njia hii haitumii utiririshaji. Kwa majibu ya RAG yanayotumia utiririshaji,
tumia AsyncSocketFlowInstance.graph_rag() badala yake.

**Vigezo:**

`query`: Nakala ya swali la mtumiaji
`user`: Kitambulisho cha mtumiaji
`collection`: Kitambulisho cha mkusanyiko unao na grafu ya maarifa
`max_subgraph_size`: Nambari ya juu ya triplet kwa kila subgrafu (ya kawaida: 1000)
`max_subgraph_count`: Nambari ya juu ya subgrafu za kuchukuliwa (ya kawaida: 5)
`max_entity_distance`: Umbali wa juu wa grafu kwa upanuzi wa vitu (ya kawaida: 3)
`**kwargs`: Vigezo vya ziada vya huduma maalum

**Inarudisha:** string: Jibu kamili lililoundwa ambalo limekithiri katika data ya grafu

**Mfano:**

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

Tafadhali omba huduma iliyo ndani ya eneo la mtiririko.

Njia ya ndani ya kuita huduma ndani ya mfano huu wa mtiririko.

**Vigezo:**

`service`: Jina la huduma (k.m., "agent", "graph-rag", "triples")
`request_data`: Takwimu ya ombi la huduma

**Inarudisha:** dict: Kielelezo cha jibu la huduma

**Inatirisha:**

`ProtocolException`: Ikiwa ombi halikubaliwi au jibu ni batili
`ApplicationException`: Ikiwa huduma inarudisha kosa

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs: Any)`

Tafuta ujumbe wa mistari ili kutafuta maana katika data iliyopangwa.

Hufanya utafutaji wa maana kwenye ujumbe wa mistari ili kupata mistari ambayo
maadili ya sehemu iliyopangwa ni sawa zaidi na maandishi ya ingizo. Inaruhusu
utangamano/ufanisi wa maana katika data iliyopangwa.

**Vigezo:**

`text`: Maandishi ya swali kwa utafutaji wa maana
`schema_name`: Jina la mpango wa kutafuta ndani
`user`: Kitambulisho cha mtumiaji (kawaida: "trustgraph")
`collection`: Kitambulisho cha mkusanyiko (kawaida: "default")
`index_name`: Jina la faharasa la hiari ili kuchuja utafutaji kwa faharasa maalum
`limit`: Nambari ya juu ya matokeo ya kurejesha (kawaida: 10)
`**kwargs`: Vigezo vya ziada vya huduma

**Inarudisha:** dict: Jibu linalo na mechi pamoja na index_name, index_value, text, na score

**Mfano:**

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

Tekeleza swali la GraphQL kwenye mistari iliyohifadhiwa.

Maswali hutumia mistari iliyo na muundo kwa kutumia sintaksia ya GraphQL. Inasaidia
maswali magumu yenye vigezo na operesheni zilizo na majina.

**Vigezo:**

`query`: Mnyororo wa swali la GraphQL
`user`: Kitambulisho cha mtumiaji
`collection`: Kitambulisho cha mkusanyiko unao na mistari
`variables`: Vigezo vya swali la GraphQL vya hiari
`operation_name`: Jina la operesheni la hiari kwa maswali mengi
`**kwargs`: Vigezo vya ziada vya mahitaji ya huduma

**Inarudisha:** dict: Jibu la GraphQL lenye data na/au makosa

**Mfano:**

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

Toa maandishi yaliyokamilika (hayajazalishwa kwa utiririshaji).

Huunda jibu la maandishi kutoka kwa mfumo wa LLM (Large Language Model) kwa kutumia maagizo ya mfumo na maagizo ya mtumiaji.
Inarudisha maandishi kamili ya jibu.

Kumbuka: Njia hii haitumii utiririshaji. Kwa utiririshaji wa maandishi,
tumia AsyncSocketFlowInstance.text_completion() badala yake.

**Vigezo:**

`system`: Maagizo ya mfumo ambayo yanaeleza tabia ya mfumo wa LLM.
`prompt`: Maagizo ya mtumiaji au swali.
`**kwargs`: Vigezo vya ziada ambavyo ni mahususi kwa huduma.

**Inarudisha:** str: Jibu kamili la maandishi lililozalishwa.

**Mfano:**

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

Tafuta maneno matatu ya RDF kwa kutumia utambuzi wa muundo.

Inatafuta maneno matatu yanayolingana na mada, sifa, na/au
mifumo ya kitu. Mifumo hutumia "Hakuna" kama ishara ya kujielekeza ili kuangalia thamani yoyote.

**Vigezo:**

`s`: Mfumo wa mada (Hakuna kwa kujielekeza)
`p`: Mfumo wa sifa (Hakuna kwa kujielekeza)
`o`: Mfumo wa kitu (Hakuna kwa kujielekeza)
`user`: Kitambulisho cha mtumiaji (Hakuna kwa watumiaji wote)
`collection`: Kitambulisho cha mkusanyiko (Hakuna kwa mkusanyiko wote)
`limit`: Nambari ya juu ya maneno matatu ya kurejesha (ya kawaida: 100)
`**kwargs`: Vigezo vya ziada maalum kwa huduma

**Inarejea:** dict: Jibu lenye maneno matatu yanayolingana

**Mfano:**

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

Mteja wa WebSocket wa wakati mmoja kwa operesheni za utiririshaji.

Hutoa kiolesura cha wakati mmoja kwa huduma za TrustGraph zinazotegemea WebSocket,
ikibadilisha maktabu ya websockets ya asinkroni na jenereta za wakati mmoja ili iwe rahisi kutumia.
Inasaidia majibu ya utiririshaji kutoka kwa wakala, maswali ya RAG, na kukamilisha maandishi.

Kumbuka: Hii ni kifungashio cha wakati mmoja kilichoanzishwa kwenye operesheni za WebSocket za asinkroni. Kwa
usaidizi wa kweli wa asinkroni, tumia AsyncSocketClient badala yake.

### Mbinu

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Anzisha mteja wa WebSocket wa wakati mmoja.

**Majadiliano:**

`url`: URL ya msingi kwa API ya TrustGraph (HTTP/HTTPS itabadilishwa kuwa WS/WSS)
`timeout`: Muda wa kimya wa WebSocket kwa sekunde
`token`: Tokeni ya kuhifadhia ya hiari kwa uthibitishaji

### `close(self) -> None`

Funga miunganisho ya WebSocket.

Kumbuka: Usafi unashughulikiwa kiotomatiki na wasimamizi wa muktadha katika msimbo wa asinkroni.

### `flow(self, flow_id: str) -> 'SocketFlowInstance'`

Pata mfano wa mtiririko kwa operesheni za utiririshaji wa WebSocket.

**Majadiliano:**

`flow_id`: Kitambulisho cha mtiririko

**Inarudisha:** SocketFlowInstance: Mfano wa mtiririko na mbinu za utiririshaji

**Mfano:**

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

Mfumo wa mawasiliano ya WebSocket wa wakati mmoja kwa operesheni za utiririshaji.

Hutoa kiolesura sawa na FlowInstance ya REST lakini na msaada wa utiririshaji wa WebSocket
kwa majibu ya wakati halisi. Mbinu zote zinaunga mkono parameter ya hiari
`streaming` ili kuwezesha utoaji wa matokeo kwa hatua.

### Mbinu

### `__init__(self, client: trustgraph.api.socket_client.SocketClient, flow_id: str) -> None`

Anzisha mfumo wa utiririshaji wa soketi.

**Majadiliano:**

`client`: Soketi ya Msimamizi
`flow_id`: Kitambulisho cha mtiririko

### `agent(self, question: str, user: str, state: Dict[str, Any] | None = None, group: str | None = None, history: List[Dict[str, Any]] | None = None, streaming: bool = False, **kwargs: Any) -> Dict[str, Any] | Iterator[trustgraph.api.types.StreamingChunk]`

Fanya operesheni ya wakala na msaada wa utiririshaji.

Wakala wanaweza kufanya utaratibu wa hatua kadhaa kwa kutumia zana. Mbinu hii daima
hurudisha vipande vya utiririshaji (mawazo, uchunguzi, majibu) hata wakati
streaming=False, ili kuonyesha mchakato wa utafakari wa wakala.

**Majadiliano:**

`question`: Swali au maagizo ya mtumiaji
`user`: Kitambulisho cha mtumiaji
`state`: Kamusi ya hiari ya hali kwa mazungumzo ya hali
`group`: Kitambulisho cha hiari cha kikundi kwa muktadha wa watumiaji wengi
`history`: Historia ya hiari ya mazungumzo kama orodha ya maneno
`streaming`: Washa hali ya utiririshaji (kiasi: False)
`**kwargs`: Vigezo vya ziada vilivyopitishwa kwa huduma ya wakala

**Hurejesha:** Iterator[StreamingChunk]: Mto wa mawazo, uchunguzi, na majibu ya wakala

**Mfano:**

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

Fanya operesheni ya wakala pamoja na ufuatiliaji wa uelewaji.

Hutuma vipande vya maudhui (AgentThought, AgentObservation, AgentAnswer)
na matukio ya asili (ProvenanceEvent). Matukio ya asili yana anwani za mtandao (URIs)
ambazo zinaweza kupatikana kwa kutumia ExplainabilityClient ili kupata maelezo
kuhusu mchakato wa utafakari wa wakala.

Ufuatiliaji wa wakala una vipengele vifuatavyo:
Kipindi: Swali la awali na metadata ya kipindi
Mzunguko: Kila mzunguko wa mawazo/tendo/uchunguzi
Hitimisho: Jibu la mwisho

**Vigezo:**

`question`: Swali au maagizo ya mtumiaji
`user`: Kitambulisho cha mtumiaji
`collection`: Kitambulisho cha mkusanyiko kwa uhifadhi wa asili
`state`: Kamusi ya hali inayobadilika (optional) kwa mazungumzo yanayoendelea
`group`: Kitambulisho cha kikundi (optional) kwa mazingira ya watumiaji wengi
`history`: Historia ya mazungumzo (optional) kama orodha ya maneno
`**kwargs`: Vigezo vya ziada ambavyo hutumwa kwa huduma ya wakala
`Yields`: 
`Union[StreamingChunk, ProvenanceEvent]`: Vipande vya wakala na matukio ya asili

**Mfano:**

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

Tafuta vipande vya hati kwa kutumia utambulisho wa maana.

**Vigezo:**

`text`: Nakala ya swali kwa utafutaji wa maana
`user`: Kitambulisho cha mtumiaji/nafasi
`collection`: Kitambulisho cha mkusanyiko
`limit`: Nambari ya juu ya matokeo (ya kawaida: 10)
`**kwargs`: Vigezo vya ziada vilivyopitishwa kwa huduma

**Inarudisha:** dict: Matokeo ya swali na kitambulisho cha vipande vya hati vinavyolingana

**Mfano:**

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

Fanya swali la RAG (Retrieval-Augmented Generation) linalotegemea hati, na uwezekano wa kutumia utiririshaji.

Hutumia ufashiliaji wa vector ili kupata vipande muhimu vya hati, kisha huunda
jibu kwa kutumia LLM (Large Language Model). Njia ya utiririshaji huwasilisha matokeo hatua kwa hatua.

**Vigezo:**

`query`: Swali la lugha ya asili
`user`: Kitambulisho cha mtumiaji/nafasi
`collection`: Kitambulisho cha mkusanyiko
`doc_limit`: Idadi ya juu ya vipande vya hati ambavyo vinaweza kupatikana (kiwango chachilia: 10)
`streaming`: Washa hali ya utiririshaji (kiwango chachilia: False)
`**kwargs`: Vigezo vya ziada ambavyo hutumwa kwa huduma

**Hurejesha:** Union[str, Iterator[str]]: Jibu kamili au mkondo wa vipande vya maandishi

**Mfano:**

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

Fanya swali la RAG (Retrieval-Augmented Generation) linalotegemea hati na linalo na uwezo wa kueleza.

Hutuma vipande vya maudhui (RAGChunk) na matukio ya asili (ProvenanceEvent).
Matukio ya asili yana anwani za mtandao (URIs) ambazo zinaweza kupatikana kwa kutumia ExplainabilityClient
ili kupata maelezo ya kina kuhusu jinsi jibu lilivyoundwa.

Mfuatiliaji wa RAG wa hati una vipengele vifuatavyo:
Swali: Swali la mtumiaji
Uchunguzi: Vipande vilivyopatikana kutoka kwenye hifadhi ya hati (idadi ya vipande)
Muundo: Jibu lililoundwa

**Vigezo:**

`query`: Swali kwa lugha ya asili
`user`: Kitambulisho cha mtumiaji/nafasi
`collection`: Kitambulisho cha mkusanyiko
`doc_limit`: Vipande vingi vya hati ambavyo vinaweza kupatikana (kiwango chachilia: 10)
`**kwargs`: Vigezo vya ziada ambavyo vinatumiwa kwa huduma
`Yields`: 
`Union[RAGChunk, ProvenanceEvent]`: Vipande vya maudhui na matukio ya asili

**Mfano:**

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

Toa ufafanuzi wa maandishi kwa ajili ya maandishi moja au zaidi.

**Vigezo:**

`texts`: Orodha ya maandishi ya pembeni ambayo yatatumika kuunda ufafanuzi.
`**kwargs`: Vigezo vya ziada ambavyo hutumwa kwa huduma.

**Inarudisha:** dict: Jibu ambalo lina ufafanuzi (kundi moja kwa kila maandishi ya pembeni).

**Mfano:**

```python
socket = api.socket()
flow = socket.flow("default")

result = flow.embeddings(["quantum computing"])
vectors = result.get("vectors", [])
```

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any) -> Dict[str, Any]`

Tafuta vitu vya grafu ya maarifa kwa kutumia utambulisho wa maana.

**Vigezo:**

`text`: Nakala ya swali kwa utafutaji wa maana
`user`: Kitambulisho cha mtumiaji/nafasi
`collection`: Kitambulisho cha mkusanyiko
`limit`: Nambari ya juu ya matokeo (ya kawaida: 10)
`**kwargs`: Vigezo vya ziada vilivyopitishwa kwa huduma

**Inarudisha:** dict: Matokeo ya swali na vitu vinavyofanana

**Mfano:**

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

Tekeleza swali la RAG linalotegemea grafu pamoja na utiririshaji wa hiari.

Hutumia muundo wa grafu ya maarifa ili kupata muktadha unaohusika, kisha huunda
jibu kwa kutumia LLM. Njia ya utiririshaji huwasilisha matokeo hatua kwa hatua.

**Vigezo:**

`query`: Swali la lugha ya asili
`user`: Kitambulisho cha mtumiaji/nafasi
`collection`: Kitambulisho cha mkusanyiko
`max_subgraph_size`: Idadi ya juu ya triplet katika subgrafu (ya kawaida: 1000)
`max_subgraph_count`: Idadi ya juu ya subgrafu (ya kawaida: 5)
`max_entity_distance`: Kina cha juu cha utafutaji (ya kawaida: 3)
`streaming`: Washa hali ya utiririshaji (ya kawaida: False)
`**kwargs`: Vigezo vya ziada ambavyo hutumwa kwa huduma

**Hurejesha:** Union[str, Iterator[str]]: Jibu kamili au mkondo wa vipande vya maandishi

**Mfano:**

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

Tekeleza swali la RAG linalotegemea grafu pamoja na utumiaji wa uelewaji.

Hutiririsha vipande vya maudhui (RAGChunk) na matukio ya asili (ProvenanceEvent).
Matukio ya asili yana URI ambazo zinaweza kupatikana kwa kutumia ExplainabilityClient
ili kupata maelezo ya kina kuhusu jinsi jibu lilivyoundwa.

**Vigezo:**

`query`: Swali la lugha ya asili
`user`: Kitambulisho cha mtumiaji/nafasi
`collection`: Kitambulisho cha mkusanyiko
`max_subgraph_size`: Idadi ya juu ya triplet katika subgrafu (ya kawaida: 1000)
`max_subgraph_count`: Idadi ya juu ya subgrafu (ya kawaida: 5)
`max_entity_distance`: Kina cha juu cha utafutaji (ya kawaida: 3)
`**kwargs`: Vigezo vya ziada ambavyo hutumwa kwa huduma
`Yields`: 
`Union[RAGChunk, ProvenanceEvent]`: Vipande vya maudhui na matukio ya asili

**Mfano:**

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

Fanya kazi ya zana ya Itifaki ya Mfumo (MCP).

**Vigezo:**

`name`: Jina/kitambulisho cha zana
`parameters`: Kamusi ya vigezo vya zana
`**kwargs`: Vigezo vya ziada vilivyopitishwa kwa huduma

**Inarudisha:** dict: Matokeo ya utekelezaji wa zana

**Mfano:**

```python
socket = api.socket()
flow = socket.flow("default")

result = flow.mcp_tool(
    name="search-web",
    parameters={"query": "latest AI news", "limit": 5}
)
```

### `prompt(self, id: str, variables: Dict[str, str], streaming: bool = False, **kwargs: Any) -> str | Iterator[str]`

Tekeleza mfumo wa kielelezo cha ombi pamoja na utiririshaji wa hiari.

**Vigezo:**

`id`: Kitambulisho cha kielelezo cha ombi
`variables`: Kamusi ya uhusiano kati ya jina la vigezo na maadili
`streaming`: Washa hali ya utiririshaji (kiwango chake: Feleke)
`**kwargs`: Vigezo vya ziada ambavyo hutumwa kwa huduma

**Inarudisha:** Union[str, Iterator[str]]: Jibu kamili au mkondo wa vipande vya maandishi

**Mfano:**

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

Tafuta data ya safu kwa kutumia utofauti wa maana kwenye sehemu zilizofichwa.

Inatafuta safu ambazo maadili ya sehemu zilizofichwa zinafanana kwa maana na
maandishi ya ingizo, kwa kutumia uelekezo wa vector. Hii inaruhusu utafutaji wa "fuzzy"/maana
kwenye data iliyopangwa.

**Vigezo:**

`text`: Maandishi ya swali kwa utafutaji wa maana
`schema_name`: Jina la schema ili kutafuta ndani
`user`: Kitambulisho cha mtumiaji/keyspace (cha kawaida: "trustgraph")
`collection`: Kitambulisho cha mkusanyiko (cha kawaida: "default")
`index_name`: Jina la index la hiari ili kuchuja utafutaji kwa index maalum
`limit`: Nambari ya juu ya matokeo (cha kawaida: 10)
`**kwargs`: Vigezo vya ziada vilivyopitishwa kwa huduma

**Inarudisha:** dict: Matokeo ya swali ambayo yana mechi zinazojumuisha index_name, index_value, text, na score

**Mfano:**

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

Tekeleza swali la GraphQL dhidi ya mistari iliyopangwa.

**Vigezo:**

`query`: Mnyororo wa swali la GraphQL
`user`: Kitambulisho cha mtumiaji/nafasi
`collection`: Kitambulisho cha mkusanyiko
`variables`: Kamusi ya vigezo vya swali ya hiari
`operation_name`: Jina la operesheni ya hiari kwa hati za operesheni nyingi
`**kwargs`: Vigezo vya ziada vilivyopitishwa kwa huduma

**Inarudisha:** dict: Jibu la GraphQL lenye data, makosa, na/au nyongeza

**Mfano:**

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

Tekeleza kukamilisha maandishi kwa kutumia utiririshaji wa hiari.

**Vigezo:**

`system`: Maelezo ya mfumo ambayo yanaelezea tabia ya msaidizi.
`prompt`: Maelezo ya mtumiaji/swali.
`streaming`: Washa hali ya utiririshaji (kiwango chachilia: False).
`**kwargs`: Vigezo vya ziada ambavyo hutumwa kwa huduma.

**Inarudisha:** Union[str, Iterator[str]]: Jibu kamili au mkondo wa vipande vya maandishi.

**Mfano:**

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

Tafuta tripli za grafu ya maarifa kwa kutumia utambuzi wa muundo.

**Vigezo:**

`s`: Kichujio cha somo - Msururu wa URI, kamusi ya neno, au None kwa kichujio cha kila kitu.
`p`: Kichujio cha tabia - Msururu wa URI, kamusi ya neno, au None kwa kichujio cha kila kitu.
`o`: Kichujio cha kitu - Msururu wa URI/lita, kamusi ya neno, au None kwa kichujio cha kila kitu.
`g`: Kichujio cha grafu iliyojulikana - Msururu wa URI au None kwa grafu zote.
`user`: Kitambulisho cha mtumiaji/nafasi (hiari).
`collection`: Kitambulisho cha mkusanyiko (hiari).
`limit`: Matokeo ya kiwango cha juu ya kurudishwa (kiwango chachilia: 100).
`**kwargs`: Vigezo vya ziada vilivyopitishwa kwa huduma.

**Inarudisha:** Orodha[Dict]: Orodha ya tripli zinazolingana katika muundo wa msingi.

**Mfano:**

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

Tafuta tripla za grafu ya maarifa kwa kutumia mikondo ya data.

Hutoa mikondo ya tripla kadri zinavyofika, na hivyo kupunguza muda wa kupata matokeo ya kwanza
na matumizi ya kumbukumbu kwa matokeo makubwa.

**Vigezo:**

`s`: Kichujio cha mada - Msururu wa URI, kamusi ya neno, au None kwa kichujio cha wote.
`p`: Kichujio cha sifa - Msururu wa URI, kamusi ya neno, au None kwa kichujio cha wote.
`o`: Kichujio cha kitu - Msururu wa URI/lita, kamusi ya neno, au None kwa kichujio cha wote.
`g`: Kichujio cha grafu iliyojulikana - Msururu wa URI au None kwa grafu zote.
`user`: Kitambulisho cha mtumiaji/nafasi (hiari).
`collection`: Kitambulisho cha mkusanyiko (hiari).
`limit`: Matokeo mengi ya kurejesha (ya kawaida: 100).
`batch_size`: Tripla kwa kila kikundi (ya kawaida: 20).
`**kwargs`: Vigezo vya ziada vilivyopitishwa kwa huduma.
`Yields`: 
`List[Dict]`: Mikundi ya tripla katika umbizo la mawasiliano.

**Mfano:**

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

Mteja wa WebSocket asinkroni.

### Mbinu

### `__init__(self, url: str, timeout: int, token: str | None)`

Anzisha `self`. Angalia `help(type(self))` kwa maelezo sahihi ya muundo.

### `aclose(self)`

Funga muunganisho wa WebSocket.

### `flow(self, flow_id: str)`

Pata mfumo wa kazi asinkroni kwa operesheni za WebSocket.


--

## `AsyncSocketFlowInstance`

```python
from trustgraph.api import AsyncSocketFlowInstance
```

Mfumo wa mtiririko wa WebSocket usiohusisha wakati.

### Mbinu

### `__init__(self, client: trustgraph.api.async_socket_client.AsyncSocketClient, flow_id: str)`

Anzisha `self`. Angalia `help(type(self))` kwa maelezo sahihi ya jinsi ya kutumia.

### `agent(self, question: str, user: str, state: Dict[str, Any] | None = None, group: str | None = None, history: list | None = None, streaming: bool = False, **kwargs) -> Dict[str, Any] | AsyncIterator`

Wakala na utiririshaji wa hiari.

### `document_rag(self, query: str, user: str, collection: str, doc_limit: int = 10, streaming: bool = False, **kwargs)`

Andika RAG (Retrieval-Augmented Generation) na utiririshaji wa hiari.

### `embeddings(self, texts: list, **kwargs)`

Tengeneza ufichishaji wa maandishi.

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs)`

Tafuta ufichishaji wa grafu kwa utafutaji wa maana.

### `graph_rag(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, streaming: bool = False, **kwargs)`

Grafu RAG na utiririshaji wa hiari.

### `mcp_tool(self, name: str, parameters: Dict[str, Any], **kwargs)`

Endesha zana ya MCP.

### `prompt(self, id: str, variables: Dict[str, str], streaming: bool = False, **kwargs)`

Endesha ombi na utiririshaji wa hiari.

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs)`

Tafuta ufichishaji wa mistari kwa utafutaji wa maana kwenye data iliyopangwa.

### `rows_query(self, query: str, user: str, collection: str, variables: Dict | None = None, operation_name: str | None = None, **kwargs)`

Ombi la GraphQL dhidi ya mistari iliyopangwa.

### `text_completion(self, system: str, prompt: str, streaming: bool = False, **kwargs)`

Kukamilisha maandishi na utiririshaji wa hiari.

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=100, **kwargs)`

Uchunguzi wa muundo wa tatu.


--

### `build_term(value: Any, term_type: str | None = None, datatype: str | None = None, language: str | None = None) -> Dict[str, Any] | None`

Jenga kamusi ya Term ya muundo kutoka kwa thamani.

Kanuni za utambuzi wa kiotomatiki (wakati `term_type` ni `None`):
  Tayari ni kamusi yenye ufunguo 't' -> irudishe kama ilivyo (tayari ni Term)
  Inaanzia na http://, https://, urn: -> IRI
  Imezungushwa ndani ya <> (e.g., <http://...>) -> IRI (brashi za pembe zimeondolewa)
  Kila kitu kingine -> literal

**Majadiliano:**

`value`: Thamani ya Term (mfululizo, kamusi, au `None`)
`term_type`: Moja kati ya 'iri', 'literal', au `None` kwa utambuzi wa kiotomatiki
`datatype`: Aina ya data kwa vitu vya literal (e.g., xsd:integer)
`language`: Lango la lugha kwa vitu vya literal (e.g., en)

**Inarudisha:** kamusi: Kamusi ya Term ya muundo, au `None` ikiwa thamani ni `None`


--

## `BulkClient`

```python
from trustgraph.api import BulkClient
```

Mteja wa operesheni za wingi za wakati mmoja kwa uagizaji/utoaji.

Hutoa uhamishaji wa data wa wingi unaofaa kupitia WebSocket kwa data kubwa.
Huweka operesheni za WebSocket za asinkroni na jenereta za wakati mmoja ili kupunguza ugumu.

Kumbuka: Kwa usaidizi halisi wa asinkroni, tumia AsyncBulkClient badala yake.

### Mbinu

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Anzisha mteja wa wingi wa wakati mmoja.

**Majadilisho:**

`url`: URL ya msingi kwa API ya TrustGraph (HTTP/HTTPS itabadilishwa kuwa WS/WSS)
`timeout`: Muda wa timeout wa WebSocket kwa sekunde
`token`: Tokeni ya kuhifadhiwa ya hiari kwa uthibitishaji

### `close(self) -> None`

Funga miunganisho

### `export_document_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

Toa nakala za uainishaji kutoka kwa mtiririko.

Inapakua kwa ufanisi uainishaji wote wa vipande vya nyaraka kupitia utiririshaji wa WebSocket.

**Majadilisho:**

`flow`: Kitambulisho cha mtiririko
`**kwargs`: Vigezo vya ziada (hifadhiwa kwa matumizi ya baadaye)

**Inarudisha:** Iterator[Dict[str, Any]]: Msururu wa kamusi za uainishaji

**Mfano:**

```python
bulk = api.bulk()

# Export and process document embeddings
for embedding in bulk.export_document_embeddings(flow="default"):
    chunk_id = embedding.get("chunk_id")
    vector = embedding.get("embedding")
    print(f"{chunk_id}: {len(vector)} dimensions")
```

### `export_entity_contexts(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

Uhamisho wa wingi wa muktadha wa vitu kutoka kwa mtiririko.

Inapakua habari yote ya muktadha wa vitu kwa ufanisi kupitia utiririshaji wa WebSocket.

**Vigezo:**

`flow`: Kitambulisho cha mtiririko
`**kwargs`: Vigezo vya ziada (hifadhiwa kwa matumizi ya baadaye)

**Inarudisha:** Iterator[Dict[str, Any]]: Msururu wa kamusi za muktadha

**Mfano:**

```python
bulk = api.bulk()

# Export and process entity contexts
for context in bulk.export_entity_contexts(flow="default"):
    entity = context.get("entity")
    text = context.get("context")
    print(f"{entity}: {text[:100]}...")
```

### `export_graph_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

Uhamisho wa wingi wa maandamano ya grafu kutoka kwa mtiririko.

Inapakua kwa ufanisi maandamano yote ya vitu vya grafu kupitia utiririshaji wa WebSocket.

**Vigezo:**

`flow`: Kitambulisho cha mtiririko
`**kwargs`: Vigezo vya ziada (hifadhiwa kwa matumizi ya baadaye)

**Inarudisha:** Iterator[Dict[str, Any]]: Mto wa kamusi za maandamano

**Mfano:**

```python
bulk = api.bulk()

# Export and process embeddings
for embedding in bulk.export_graph_embeddings(flow="default"):
    entity = embedding.get("entity")
    vector = embedding.get("embedding")
    print(f"{entity}: {len(vector)} dimensions")
```

### `export_triples(self, flow: str, **kwargs: Any) -> Iterator[trustgraph.api.types.Triple]`

Uhamisho wa wingi wa data ya RDF kutoka kwa mtiririko.

Inapakua data yote kwa ufanisi kupitia utiririshaji wa WebSocket.

**Vigezo:**

`flow`: Kitambulisho cha mtiririko.
`**kwargs`: Vigezo vya ziada (hifadhiwa kwa matumizi ya baadaye).

**Inarudisha:** Iterator[Triple]: Mto wa vitu vya Triple.

**Mfano:**

```python
bulk = api.bulk()

# Export and process triples
for triple in bulk.export_triples(flow="default"):
    print(f"{triple.s} -> {triple.p} -> {triple.o}")
```

### `import_document_embeddings(self, flow: str, embeddings: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

Kuleta kwa wingi maandishi ya kuingizwa katika mtiririko.

Huainisha kwa ufanisi maandishi ya vipande vya maandishi kupitia utiririshaji wa WebSocket
kwa matumizi katika maswali ya RAG ya maandishi.

**Vigezo:**

`flow`: Kitambulisho cha mtiririko
`embeddings`: Mfumo unaotoa kamusi za kuingizwa
`**kwargs`: Vigezo vya ziada (hifadhiwa kwa matumizi ya baadaye)

**Mfano:**

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

Kuleta kwa wingi maelezo ya vitu ndani ya mtiririko.

Huwezesha kupakia taarifa za maelezo ya vitu kupitia utiririshaji wa WebSocket.
Maelezo ya vitu hutoa maelezo ya ziada ya maandishi kuhusu vitu vya chati
ili kuboresha utendaji wa RAG.

**Vigezo:**

`flow`: Kitambulisho cha mtiririko
`contexts`: Iteratili inayotoa kamusi za maelezo
`metadata`: Kamusi ya metadata yenye id, metadata, mtumiaji, mkusanyiko
`batch_size`: Idadi ya maelezo kwa kila kundi (ya kawaida 100)
`**kwargs`: Vigezo vya ziada (vimehifadhiwa kwa matumizi ya baadaye)

**Mfano:**

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

Kuleta kwa wingi michoro ya pembejeo katika mtiririko.

Huainisha kwa ufanisi pembejeo za michoro kupitia utiririshaji wa WebSocket.

**Vigezo:**

`flow`: Kitambulisho cha mtiririko
`embeddings`: Mfuatiliao unaotoa kamusi za pembejeo
`**kwargs`: Vigezo vya ziada (hifadhiwa kwa matumizi ya baadaye)

**Mfano:**

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

Kuingiza kwa wingi mistari iliyoandaliwa katika mtiririko.

Inapakia data iliyoandaliwa kwa ufanisi kupitia utiririshaji wa WebSocket
kwa ajili ya matumizi katika maswali ya GraphQL.

**Vigezo:**

`flow`: Kitambulisho cha mtiririko
`rows`: Mfuatiliazo unaotoa kamusi za mistari
`**kwargs`: Vigezo vya ziada (hifadhiwa kwa matumizi ya baadaye)

**Mfano:**

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

Uingizaji wa jumla wa triplet za RDF katika mtiririko.

Huainisha triplet nyingi kwa ufanisi kupitia utiririshaji wa WebSocket.

**Vigezo:**

`flow`: Kitambulisho cha mtiririko
`triples`: Itereta inayotoa vitu vya Triple
`metadata`: Kamusi ya metadata yenye id, metadata, mtumiaji, mkusanyiko
`batch_size`: Idadi ya triplet kwa kila kundi (ya kawaida 100)
`**kwargs`: Vigezo vya ziada (vimehifadhiwa kwa matumizi ya baadaye)

**Mfano:**

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

Mteja wa operesheni za wingi zisizo za wakati.

### Mbinu

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Anzisha `self`. Angalia `help(type(self))` kwa maelezo sahihi ya muundo.

### `aclose(self) -> None`

Funga miunganisho.

### `export_document_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

Uhamisho wa wingi wa maandishi ya nyaraka kupitia WebSocket.

### `export_entity_contexts(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

Uhamisho wa wingi wa muktadha wa vitu kupitia WebSocket.

### `export_graph_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

Uhamisho wa wingi wa maandishi ya chati kupitia WebSocket.

### `export_triples(self, flow: str, **kwargs: Any) -> AsyncIterator[trustgraph.api.types.Triple]`

Uhamisho wa wingi wa triplet kupitia WebSocket.

### `import_document_embeddings(self, flow: str, embeddings: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

Uingizaji wa wingi wa maandishi ya nyaraka kupitia WebSocket.

### `import_entity_contexts(self, flow: str, contexts: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

Uingizaji wa wingi wa muktadha wa vitu kupitia WebSocket.

### `import_graph_embeddings(self, flow: str, embeddings: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

Uingizaji wa wingi wa maandishi ya chati kupitia WebSocket.

### `import_rows(self, flow: str, rows: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

Uingizaji wa wingi wa mistari kupitia WebSocket.

### `import_triples(self, flow: str, triples: AsyncIterator[trustgraph.api.types.Triple], **kwargs: Any) -> None`

Uingizaji wa wingi wa triplet kupitia WebSocket.


--

## `Metrics`

```python
from trustgraph.api import Metrics
```

Mteja wa metriki za wakati mmoja.

### Mbinu

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Anzisha `self`. Angalia `help(type(self))` kwa maelezo sahihi ya muundo.

### `get(self) -> str`

Pata metriki za Prometheus kama maandishi.


--

## `AsyncMetrics`

```python
from trustgraph.api import AsyncMetrics
```

Mteja wa metriki zisizo za wakati (asynchronous).

### Mbinu (Methods)

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Anzisha (Initialize) `self`. Angalia `help(type(self))` kwa maelezo sahihi ya muundo.

### `aclose(self) -> None`

Funga miunganisho (Close connections).

### `get(self) -> str`

Pata metriki za Prometheus kama maandishi (Get Prometheus metrics as text).


--

## `ExplainabilityClient`

```python
from trustgraph.api import ExplainabilityClient
```

Mteja wa kupata vitu vya uhalisia kwa utaratibu wa utangamano wa mwisho.

Hutumia utambuzi wa utulivu: pata, subiri, pata tena, linganisha.
Ikiwa matokeo ni sawa, data ni thabiti.

### Mbinu

### `__init__(self, flow_instance, retry_delay: float = 0.2, max_retries: int = 10)`

Anzisha mteja wa uhalisia.

**Majadiliano:**

`flow_instance`: Toleo la SocketFlowInstance kwa kuuliza vitatu.
`retry_delay`: Kuchelewesha kati ya majaribio katika sekunde (kiwango chote: 0.2).
`max_retries`: Jaribio la juu zaidi (kiwango chote: 10).

### `detect_session_type(self, session_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> str`

Thibitisha ikiwa kikao ni cha aina ya GraphRAG au Agent.

**Vigezo:**

`session_uri`: URI ya kipindi/swali
`graph`: Grafu iliyopewa jina
`user`: Kitambulisho cha mtumiaji/nafasi
`collection`: Kitambulisho cha mkusanyiko

**Inarudisha:** "graphrag" au "agent"

### `fetch_agent_trace(self, session_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

Pata faili kamili ya "Agent" kuanzia URI ya kipindi.

Fuata mnyororo wa asili: Swali -> Uchambuzi(s) -> Hitimisho

**Vigezo:**

`session_uri`: URI ya kipindi cha "agent"/swali
`graph`: Grafu iliyopewa jina (ya kawaida: urn:graph:retrieval)
`user`: Kitambulisho cha mtumiaji/nafasi
`collection`: Kitambulisho cha mkusanyiko
`api`: Ena ya TrustGraph API kwa ufikiaji wa "librarian" (hiari)
`max_content`: Urefu wa juu wa maudhui kwa hitimisho

**Inarudi:** Kamusi yenye swali, mara (Orodha ya uchambuzi), na vitu vya hitimisho.

### `fetch_docrag_trace(self, question_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

Kuchukua faili kamili ya "DocumentRAG" kuanzia URI ya swali.

Kufuata mnyororo wa asili:
    Swali -> Msingi -> Uchunguzi -> Muunganisho

**Majadiliano:**

`question_uri`: URI ya swali.
`graph`: Grafu iliyoitwa (ya kawaida: urn:graph:retrieval).
`user`: Kitambulisho cha mtumiaji/nafasi.
`collection`: Kitambulisho cha mkusanyiko.
`api`: Eneo la TrustGraph API kwa ufikiaji wa "librarian" (hiari).
`max_content`: Urefu wa juu wa yaliyomo kwa muunganisho.

**Inarudi:** Kamusi yenye swali, msingi, uchunguzi, na vitu vya muunganisho.

### `fetch_document_content(self, document_uri: str, api: Any, user: str | None = None, max_content: int = 10000) -> str`

Kuchukua yaliyomo kutoka kwa "librarian" kwa URI ya hati.

**Majadiliano:**

`document_uri`: URI ya hati katika "librarian".
`api`: Eneo la TrustGraph API kwa ufikiaji wa "librarian".
`user`: Kitambulisho cha mtumiaji kwa "librarian".
`max_content`: Urefu wa juu wa yaliyomo yanayorudishwa.

**Inarudi:** Yaliyomo ya hati kama mfululizo.

### `fetch_edge_selection(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.EdgeSelection | None`

Kuchukua kitambulisho cha uchaguzi wa "edge" (kinachotumika na Focus).

**Majadiliano:**

`uri`: URI ya uchaguzi wa "edge".
`graph`: Grafu iliyoitwa ya kuchunguza.
`user`: Kitambulisho cha mtumiaji/nafasi.
`collection`: Kitambulisho cha mkusanyiko.

**Inarudi:** EdgeSelection au None ikiwa haipatikani.

### `fetch_entity(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.ExplainEntity | None`

Kuchukua na kueleza kitu (entity) kwa kutumia URI, na kusimamia utaratibu wa uthabiti.

Hutumia utambuzi wa utulivu:
1. Kuchukua data (triples) kwa URI
2. Ikiwa hakuna matokeo, jaribu tena
3. Ikiwa kuna matokeo, subiri na chukua tena
4. Ikiwa matokeo ni sawa, data imetulia - changanua na urudishe
5. Ikiwa matokeo ni tofauti, data bado inaanzishwa - jaribu tena

**Vigezo:**

`uri`: URI ya kitu (entity) kinachohitajika
`graph`: Picha (graph) inayotumika kwa utafutaji (e.g., "urn:graph:retrieval")
`user`: Kitambulisho cha mtumiaji/nafasi
`collection`: Kitambulisho cha mkusanyiko

**Inarudisha:** Kifaa cha aina ya ExplainEntity au None ikiwa haipatikani

### `fetch_focus_with_edges(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.Focus | None`

Kuchukua kitu (entity) cha "Focus" na uteuzi wake wote wa "edge".

**Vigezo:**

`uri`: URI ya kitu (entity) cha "Focus"
`graph`: Picha (graph) inayotumika kwa utafutaji
`user`: Kitambulisho cha mtumiaji/nafasi
`collection`: Kitambulisho cha mkusanyiko

**Inarudisha:** "Focus" iliyo na "edge_selections" zilizojazwa, au None

### `fetch_graphrag_trace(self, question_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

Kuchukua "GraphRAG" kamili kuanzia URI ya swali.

Ifuatilia mnyororo wa asili: Swali -> Uthabiti -> Uchunguzi -> Focus -> Muhtasari

**Vigezo:**

`question_uri`: URI ya swali
`graph`: Picha (default: urn:graph:retrieval)
`user`: Kitambulisho cha mtumiaji/nafasi
`collection`: Kitambulisho cha mkusanyiko
`api`: Ena ya TrustGraph API kwa ufikiaji wa "librarian" (hiari)
`max_content`: Urefu wa juu wa yaliyomo kwa ajili ya muhtasari

**Inarudisha:** Kamusi yenye vitu vya swali, msingi, uchunguzi, lengo, na muhtasari.

### `list_sessions(self, graph: str | None = None, user: str | None = None, collection: str | None = None, limit: int = 50) -> List[trustgraph.api.explainability.Question]`

Orodha ya vipindi vyote vya kufafanua (maswali) katika mkusanyiko.

**Majadiliano:**

`graph`: Picha iliyopewa jina (ya kawaida: urn:graph:retrieval)
`user`: Kitambulisho cha mtumiaji/nafasi
`collection`: Kitambulisho cha mkusanyiko
`limit`: Nambari ya juu ya vipindi kurudishwa

**Inarudisha:** Orodha ya vitu vya Swali vilivyopangwa kwa wakati (vya hivi karibuni kwanza)

### `resolve_edge_labels(self, edge: Dict[str, str], user: str | None = None, collection: str | None = None) -> Tuple[str, str, str]`

Tatua lebo kwa vipengele vyote vya triplet ya ukingo.

**Majadiliano:**

`edge`: Kamusi yenye funguo za "s", "p", na "o"
`user`: Kitambulisho cha mtumiaji/nafasi
`collection`: Kitambulisho cha mkusanyiko

**Inarudisha:** Jozi ya (s_label, p_label, o_label)

### `resolve_label(self, uri: str, user: str | None = None, collection: str | None = None) -> str`

Tatua rdfs:label kwa URI, pamoja na kuhifadhi.

**Majadiliano:**

`uri`: URI ambayo lebo inapaswa kupatikana
`user`: Kitambulisho cha mtumiaji/nafasi
`collection`: Kitambulisho cha mkusanyiko

**Inarudisha:** Lebo ikiwa imepatikana, vinginevyo URI yenyewe.


--

## `ExplainEntity`

```python
from trustgraph.api import ExplainEntity
```

Darasa la msingi kwa vitu vya uelewaji.

**Vipengele:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>

### Mbinu

### `__init__(self, uri: str, entity_type: str = '') -> None`

Anzisha self. Angalia help(type(self)) kwa maelezo sahihi.


--

## `Question`

```python
from trustgraph.api import Question
```

Swali la mtumiaji - swali la mtumiaji ambalo lilianzisha kipindi.

**Vifaa:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`query`: <class 'str'>
`timestamp`: <class 'str'>
`question_type`: <class 'str'>

### Mbinu

### `__init__(self, uri: str, entity_type: str = '', query: str = '', timestamp: str = '', question_type: str = '') -> None`

Anzisha self. Angalia help(type(self)) kwa maelezo sahihi.


--

## `Exploration`

```python
from trustgraph.api import Exploration
```

Kitengo cha utafiti - pembejeo/sehemu zilizopatikana kutoka kwenye hifadhi ya maarifa.

**Vifaa:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`edge_count`: <class 'int'>
`chunk_count`: <class 'int'>
`entities`: typing.List[str]

### Mbinu

### `__init__(self, uri: str, entity_type: str = '', edge_count: int = 0, chunk_count: int = 0, entities: List[str] = <factory>) -> None`

Anzisha self. Angalia help(type(self)) kwa maelezo sahihi ya muundo.


--

## `Focus`

```python
from trustgraph.api import Focus
```

Mfumo wa msingi - pembe zilizochaguliwa pamoja na utaratibu wa akili wa LLM (GraphRAG pekee).

**Sehemu:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`selected_edge_uris`: typing.List[str]
`edge_selections`: typing.List[trustgraph.api.explainability.EdgeSelection]

### Mbinu

### `__init__(self, uri: str, entity_type: str = '', selected_edge_uris: List[str] = <factory>, edge_selections: List[trustgraph.api.explainability.EdgeSelection] = <factory>) -> None`

Anzisha self. Angalia help(type(self)) kwa maelezo sahihi ya muundo.


--

## `Synthesis`

```python
from trustgraph.api import Synthesis
```

Kitengo cha muhtasari - jibu la mwisho.

**Sehemu:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`document`: <class 'str'>

### Mbinu

### `__init__(self, uri: str, entity_type: str = '', document: str = '') -> None`

Anzisha self. Angalia help(type(self)) kwa maelezo sahihi.


--

## `Analysis`

```python
from trustgraph.api import Analysis
```

Kitengo cha uchambuzi - mzunguko mmoja wa kufikiria/kutenda/kuchunguza (Kwa wakala pekee).

**Vyunzo:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`action`: <class 'str'>
`arguments`: <class 'str'>
`thought`: <class 'str'>
`observation`: <class 'str'>

### Mbinu

### `__init__(self, uri: str, entity_type: str = '', action: str = '', arguments: str = '', thought: str = '', observation: str = '') -> None`

Anzisha self. Angalia help(type(self)) kwa maelezo sahihi ya muundo.


--

## `Conclusion`

```python
from trustgraph.api import Conclusion
```

Hitimisho la kitengo - jibu la mwisho (Kwa wakala pekee).

**Sehemu:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`document`: <class 'str'>

### Mbinu

### `__init__(self, uri: str, entity_type: str = '', document: str = '') -> None`

Anzisha self. Angalia help(type(self)) kwa maelezo sahihi.


--

## `EdgeSelection`

```python
from trustgraph.api import EdgeSelection
```

Kichwa kilichochaguliwa pamoja na hoja kutoka hatua ya GraphRAG Focus.

**Sehemu:**

`uri`: <class 'str'>
`edge`: typing.Dict[str, str] | None
`reasoning`: <class 'str'>

### Mbinu

### `__init__(self, uri: str, edge: Dict[str, str] | None = None, reasoning: str = '') -> None`

Anzisha self. Angalia help(type(self)) kwa maelezo sahihi ya muundo.


--

### `wire_triples_to_tuples(wire_triples: List[Dict[str, Any]]) -> List[Tuple[str, str, Any]]`

Badilisha triplet katika umbizo la waya kuwa tuples za (s, p, o).


--

### `extract_term_value(term: Dict[str, Any]) -> Any`

Toa thamani kutoka kwenye kamusi ya Term katika umbizo la waya.


--

## `Triple`

```python
from trustgraph.api import Triple
```

Mfumo wa data wa RDF unaoonyesha sentensi ya grafu ya maarifa.

**Sehemu:**

`s`: <class 'str'>
`p`: <class 'str'>
`o`: <class 'str'>

### Mbinu

### `__init__(self, s: str, p: str, o: str) -> None`

Anzisha self. Angalia help(type(self)) kwa maelezo sahihi ya muundo.


--

## `Uri`

```python
from trustgraph.api import Uri
```

str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Unda mnyororo mpya kutoka kwa kitu kilichopewa. Ikiwa encoding au
errors imebainishwa, basi kitu lazima kiwe na buffer ya data
ambayo itafichuliwa kwa kutumia encoding iliyopewa na kidhibiti cha makosa.
Vinginevyo, hurudia matokeo ya kitu.__str__() (ikiwa imefafanuliwa)
au repr(kitu).
encoding huwezeshwa kuwa 'utf-8'.
errors huwezeshwa kuwa 'strict'.

### Mbinu

### `is_literal(self)`

### `is_triple(self)`

### `is_uri(self)`


--

## `Literal`

```python
from trustgraph.api import Literal
```

str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Unda mnyororo mpya kutoka kwa kitu kilichopewa. Ikiwa encoding au
errors imebainishwa, basi kitu lazima kiwe na buffer ya data
ambayo itafichuliwa kwa kutumia usimbaji (encoding) na kidhibiti cha makosa (error handler) uliobainishwa.
Vinginevyo, hurudia matokeo ya kitu.__str__() (ikiwa imefafanuliwa)
au repr(object).
usimbaji (encoding) huanguka kwa 'utf-8'.
makosa (errors) huanguka kwa 'strict'.

### Mbinu

### `is_literal(self)`

### `is_triple(self)`

### `is_uri(self)`


--

## `ConfigKey`

```python
from trustgraph.api import ConfigKey
```

Kitambulisho cha ufunguo wa usanidi.

**Sehemu:**

`type`: <class 'str'>
`key`: <class 'str'>

### Mbinu

### `__init__(self, type: str, key: str) -> None`

Anzisha self. Angalia help(type(self)) kwa maelezo sahihi.


--

## `ConfigValue`

```python
from trustgraph.api import ConfigValue
```

Jozi ya ufunguo na thamani ya usanidi.

**Sehemu:**

`type`: <class 'str'>
`key`: <class 'str'>
`value`: <class 'str'>

### Mbinu

### `__init__(self, type: str, key: str, value: str) -> None`

Anzisha self. Angalia help(type(self)) kwa maelezo sahihi.


--

## `DocumentMetadata`

```python
from trustgraph.api import DocumentMetadata
```

Meta data kwa hati katika maktaba.

**Sifa:**

`parent_id: Parent document ID for child documents (empty for top`: ngazi ya hati

**Nafasi:**

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

### Mbinu

### `__init__(self, id: str, time: datetime.datetime, kind: str, title: str, comments: str, metadata: List[trustgraph.api.types.Triple], user: str, tags: List[str], parent_id: str = '', document_type: str = 'source') -> None`

Anzisha self. Angalia help(type(self)) kwa maelezo sahihi ya muundo.


--

## `ProcessingMetadata`

```python
from trustgraph.api import ProcessingMetadata
```

Meta data kwa kazi ya usindikaji hati inayofanya kazi.

**Vyunzo:**

`id`: <class 'str'>
`document_id`: <class 'str'>
`time`: <class 'datetime.datetime'>
`flow`: <class 'str'>
`user`: <class 'str'>
`collection`: <class 'str'>
`tags`: typing.List[str]

### Mbinu

### `__init__(self, id: str, document_id: str, time: datetime.datetime, flow: str, user: str, collection: str, tags: List[str]) -> None`

Anzisha self. Angalia help(type(self)) kwa maelezo sahihi ya muundo.


--

## `CollectionMetadata`

```python
from trustgraph.api import CollectionMetadata
```

Meta data kwa mkusanyiko wa data.

Mikusanyiko hutoa uainishaji na kutenganisha kwa mantiki kwa hati na
data ya mfumo wa maarifa.

**Sifa:**

`name: Human`: jina la mkusanyiko linalosoma

**Nafasi:**

`user`: <class 'str'>
`collection`: <class 'str'>
`name`: <class 'str'>
`description`: <class 'str'>
`tags`: typing.List[str]

### Mbinu

### `__init__(self, user: str, collection: str, name: str, description: str, tags: List[str]) -> None`

Anzisha self. Angalia help(type(self)) kwa saini sahihi.


--

## `StreamingChunk`

```python
from trustgraph.api import StreamingChunk
```

Darasa la msingi kwa ajili ya vipande vya majibu yanayotumwa.

Hutumika kwa operesheni za utiririshaji zinazotegemea WebSocket ambapo majibu hutolewa
hatua kwa hatua yanapozalishwa.

**Vipengele:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>

### Njia

### `__init__(self, content: str, end_of_message: bool = False) -> None`

Anzisha self. Angalia help(type(self)) kwa maelezo sahihi.


--

## `AgentThought`

```python
from trustgraph.api import AgentThought
```

Sehemu ya hoja au mchakato wa kufikiri wa wakala.

Inawakilisha hoja au hatua za upangaji za ndani za wakala wakati wa utekelezaji.
Sehemu hizi zinaonyesha jinsi wakala anavyofikiri kuhusu tatizo.

**Vifaa:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>

### Mbinu

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'thought') -> None`

Anzisha self. Angalia help(type(self)) kwa maelezo sahihi ya muundo.


--

## `AgentObservation`

```python
from trustgraph.api import AgentObservation
```

Sehemu ya matokeo au uchunguzi wa matumizi ya zana.

Inawakilisha matokeo au uchunguzi kutoka kwa matumizi ya zana au kitendo.
Sehemu hizi zinaonyesha kile ambacho wakala alijifunza kutokana na matumizi ya zana.

**Vifaa:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>

### Mbinu

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'observation') -> None`

Anzisha self. Angalia help(type(self)) kwa maelezo sahihi ya muundo.


--

## `AgentAnswer`

```python
from trustgraph.api import AgentAnswer
```

Sehemu ya jibu la mwisho la wakala.

Inawakilisha jibu la mwisho la wakala kwa swali la mtumiaji baada ya kukamilisha
utaratibu wake na matumizi ya zana.

**Sifa:**

`chunk_type: Always "final`: jibu"

**Nafasi:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>
`end_of_dialog`: <class 'bool'>

### Mbinu

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'final-answer', end_of_dialog: bool = False) -> None`

Anzisha self. Angalia help(type(self)) kwa maelezo sahihi ya muundo.


--

## `RAGChunk`

```python
from trustgraph.api import RAGChunk
```

Sehemu inayotumika kwa utiririshaji ya RAG (Uundaji Ulioboreshwa na Urekebishaji).

Inatumika kwa utiririshaji wa majibu kutoka kwa RAG ya grafu, RAG ya hati, kukamilisha maandishi,
na huduma zingine za uundaji.

**Vipengele:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>
`end_of_stream`: <class 'bool'>
`error`: typing.Dict[str, str] | None

### Mbinu

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'rag', end_of_stream: bool = False, error: Dict[str, str] | None = None) -> None`

Anzisha self. Angalia help(type(self)) kwa maelezo sahihi ya muundo.


--

## `ProvenanceEvent`

```python
from trustgraph.api import ProvenanceEvent
```

Tukio la asili kwa ajili ya uelewaji.

Hutolewa wakati wa maswali ya GraphRAG wakati hali ya uelewaji imeanzishwa.
Kila tukio linawakilisha nodi ya asili iliyoundwa wakati wa uchakataji wa swali.

**Vifaa:**

`explain_id`: <class 'str'>
`explain_graph`: <class 'str'>
`event_type`: <class 'str'>

### Mbinu

### `__init__(self, explain_id: str, explain_graph: str = '', event_type: str = '') -> None`

Anzisha self. Angalia help(type(self)) kwa ajili ya saini sahihi.


--

## `ProtocolException`

```python
from trustgraph.api import ProtocolException
```

Inayotokea wakati wa hitilafu za itifaki ya WebSocket.


--

## `TrustGraphException`

```python
from trustgraph.api import TrustGraphException
```

Darasa la msingi kwa makosa yote ya huduma ya TrustGraph.


--

## `AgentError`

```python
from trustgraph.api import AgentError
```

Kosa la huduma ya wakala.


--

## `ConfigError`

```python
from trustgraph.api import ConfigError
```

Kosa la huduma ya usanidi.


--

## `DocumentRagError`

```python
from trustgraph.api import DocumentRagError
```

Kosa la upokeaji wa hati kutoka kwa mfumo.


--

## `FlowError`

```python
from trustgraph.api import FlowError
```

Kosa la usimamizi wa mtiririko


--

## `GatewayError`

```python
from trustgraph.api import GatewayError
```

Kosa la API Gateway


--

## `GraphRagError`

```python
from trustgraph.api import GraphRagError
```

Kosa la urejesho la mfumo wa RAG.


--

## `LLMError`

```python
from trustgraph.api import LLMError
```

Kosa la huduma ya LLM.


--

## `LoadError`

```python
from trustgraph.api import LoadError
```

Kosa la kupakia data.


--

## `LookupError`

```python
from trustgraph.api import LookupError
```

Kosa la utafutaji/tazama.


--

## `NLPQueryError`

```python
from trustgraph.api import NLPQueryError
```

Kosa la huduma ya utafutaji kwa lugha.


--

## `RowsQueryError`

```python
from trustgraph.api import RowsQueryError
```

Kosa la huduma ya utafutaji wa data.


--

## `RequestError`

```python
from trustgraph.api import RequestError
```

Kosa katika usindikaji wa ombi.


--

## `StructuredQueryError`

```python
from trustgraph.api import StructuredQueryError
```

Kosa la huduma ya maswali iliyopangwa.


--

## `UnexpectedError`

```python
from trustgraph.api import UnexpectedError
```

Kosa lisilotarajiwa/lisilojulikana.


--

## `ApplicationException`

```python
from trustgraph.api import ApplicationException
```

Darasa la msingi kwa makosa yote ya huduma ya TrustGraph.


--

