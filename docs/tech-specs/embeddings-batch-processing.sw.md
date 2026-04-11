# Vipimo vya Kiufundi vya Uendeshaji wa Pamoja wa Matukio (Embeddings)

## Muhtasari

Maelekezo haya yanaelezea uboreshaji kwa huduma ya matukio ili kusaidia uendeshaji wa pamoja wa maandishi mengi katika ombi moja. Utaratibu wa sasa huendesha maandishi moja kwa wakati, na hivyo kupoteza faida kubwa za utendaji ambazo modeli za matukio hutoa wakati wa kuendesha matukio.

1. **Utofauti wa Uendeshaji wa Maandishi Moja**: Utaratibu wa sasa unaficha maandishi ya moja ndani ya orodha, na hivyo kutumia viboresho vya uendeshaji wa FastEmbed.
2. **Mizio ya Ombi kwa Maandishi Kila Moja**: Maandishi kila moja yanahitaji ujumbe tofauti wa Pulsar.
3. **Utofauti wa Uendeshaji wa Modeli**: Modeli za matukio zina gharama thabiti kwa kila kundi; madaraja madogo hutumia rasilimali za GPU/CPU.
4. **Uendeshaji wa Mfululizo katika Huduma Zinazotumia**: Huduma muhimu huenda kupitia vipengele na kuita matukio moja kwa moja.

## Lengo

**Usaidizi wa API ya Matukio**: Kuruhusu uendeshaji wa maandishi mengi katika ombi moja.
**Ulinganifu na Mifumo ya Zamani**: Kuendelea kutoa usaidizi kwa ombi la maandishi moja.
**Uboreshaji Mkubwa wa Ufanisi**: Lengo ni uboreshaji wa ufanisi wa mara 5-10 kwa operesheni za jumla.
**Kupunguza Muda wa Kila Maandishi**: Kupunguza muda wa wastani wakati wa kuendesha matukio ya maandishi mengi.
**Ufanisi wa Kumbukumbu**: Kuendesha madaraja bila matumizi mengi ya kumbukumbu.
**Usiohusiana na Mtoa Huduma**: Kusaidia uendeshaji wa pamoja kwa FastEmbed, Ollama, na watoa huduma wengine.
**Kubadilisha Huduma Zinazotumia**: Kusasisha huduma zote zinazotumia matukio ili kutumia API ya matukio ambapo inafaa.

## Asili

### Utaratibu wa Sasa - Huduma ya Matukio

Utaratibu wa matukio katika `trustgraph-flow/trustgraph/embeddings/fastembed/processor.py` unaonyesha upotevu mkubwa wa utendaji:

```python
# fastembed/processor.py line 56
async def on_embeddings(self, text, model=None):
    use_model = model or self.default_model
    self._load_model(use_model)

    vecs = self.embeddings.embed([text])  # Single text wrapped in list

    return [v.tolist() for v in vecs]
```

**Matatizo:**

1. **Ukubwa wa Kundi 1**: Njia ya `embed()` ya FastEmbed imeundwa kwa ajili ya usindikaji wa kundi, lakini tunaiita kila wakati na `[text]` - kikundi cha ukubwa wa 1.

2. **Mizio ya Kila Ombi**: Kila ombi la uainishaji (embedding) hutoa:
   Usajili/uondoaji wa ujumbe wa Pulsar
   Muda wa kusafiri wa mtandao (latency)
   Mizio ya kuanzisha utekelezaji wa mfumo (model inference)
   Mizio ya upangaji wa async ya Python

3. **Kizuia cha Mpango (Schema)**: Mpango wa `EmbeddingsRequest` unaunga mkono tu maandishi moja:
   ```python
   @dataclass
   class EmbeddingsRequest:
       text: str = ""  # Single text only
   ```

### Wataalamu Wanaotumia Sasa - Uendeshaji wa Mfululizo

#### 1. Lango la API

**Faili:** `trustgraph-flow/trustgraph/gateway/dispatch/embeddings.py`

Lango linakubali ombi za uingizaji maandishi moja kupitia HTTP/WebSocket na huvipeleka kwa huduma ya uingizaji. Kwa sasa, hakuna mwisho wa kazi za kikundi.

```python
class EmbeddingsRequestor(ServiceRequestor):
    # Handles single EmbeddingsRequest -> EmbeddingsResponse
    request_schema=EmbeddingsRequest,  # Single text only
    response_schema=EmbeddingsResponse,
```

**Athari:** Wateja wa nje (programu za wavuti, skripti) lazima wafanye ombi la HTTP N ili kuingiza maandishi N.

#### 2. Huduma ya Kuingiza Nyaraka

**Faili:** `trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py`

Huprosesa vipande vya nyaraka moja kwa moja:

```python
async def on_message(self, msg, consumer, flow):
    v = msg.value()

    # Single chunk per request
    resp = await flow("embeddings-request").request(
        EmbeddingsRequest(text=v.chunk)
    )
    vectors = resp.vectors
```

**Athari:** Kila sehemu ya hati inahitaji ombi tofauti la uingizaji (embedding). Hati yenye sehemu 100 = ombi la uingizaji 100.

#### 3. Huduma ya Uingizaji wa Picha (Graph Embeddings Service)

**Faili:** `trustgraph-flow/trustgraph/embeddings/graph_embeddings/embeddings.py`

Inafanya mzunguko kwenye vitu na kuingiza kila kimoja kwa mtiririko:

```python
async def on_message(self, msg, consumer, flow):
    for entity in v.entities:
        # Serial embedding - one entity at a time
        vectors = await flow("embeddings-request").embed(
            text=entity.context
        )
        entities.append(EntityEmbeddings(
            entity=entity.entity,
            vectors=vectors,
            chunk_id=entity.chunk_id,
        ))
```

**Athari:** Ujumbe wenye vitu 50 = ombi la uwekaji wa maandishi (embedding) la kila kitu. Hii ni kikwazo kikubwa wakati wa uundaji wa grafu ya maarifa.

#### 4. Huduma ya Uwekaji wa Maandishi ya Safu

**Faili:** `trustgraph-flow/trustgraph/embeddings/row_embeddings/embeddings.py`

Huenda kupitia maandishi ya kipekee na huweka kila moja kwa mmoja:

```python
async def on_message(self, msg, consumer, flow):
    for text, (index_name, index_value) in texts_to_embed.items():
        # Serial embedding - one text at a time
        vectors = await flow("embeddings-request").embed(text=text)

        embeddings_list.append(RowIndexEmbedding(
            index_name=index_name,
            index_value=index_value,
            text=text,
            vectors=vectors
        ))
```

**Athari:** Kuchakata jedwali lenye maadili 100 ya kipekee yaliyopangwa = maombi 100 ya uwekaji data (embedding) kwa kila moja.

#### 5. EmbeddingsClient (Mteja wa Msingi)

**Faili:** `trustgraph-base/trustgraph/base/embeddings_client.py`

Mteja unaotumika na vichakataji vyote vya mtiririko unao na uwezo wa kuweka data (embedding) kwa maandishi moja tu:

```python
class EmbeddingsClient(RequestResponse):
    async def embed(self, text, timeout=30):
        resp = await self.request(
            EmbeddingsRequest(text=text),  # Single text
            timeout=timeout
        )
        return resp.vectors
```

**Athari:** Wateja wote wanaotumia programu hii wamezuiliwa kufanya kazi za maandishi pekee.

#### 6. Vifaa vya Amri (Command-Line Tools)

**Faili:** `trustgraph-cli/trustgraph/cli/invoke_embeddings.py`

Zana ya CLI inakubali hoja moja ya maandishi:

```python
def query(url, flow_id, text, token=None):
    result = flow.embeddings(text=text)  # Single text
    vectors = result.get("vectors", [])
```

**Athari:** Watumiaji hawawezi kuingiza data kwa wingi kupitia amri. Kuchakata faili ya maandishi inahitaji utendaji wa N mara.

#### 7. SDK ya Python

SDK ya Python hutoa madarasa mawili ya wateja kwa kuingiliana na huduma za TrustGraph. Zote mbili zinaunga mkono tu kuingiza maandishi moja.

**Faili:** `trustgraph-base/trustgraph/api/flow.py`

```python
class FlowInstance:
    def embeddings(self, text):
        """Get embeddings for a single text"""
        input = {"text": text}
        return self.request("service/embeddings", input)["vectors"]
```

**Faili:** `trustgraph-base/trustgraph/api/socket_client.py`

```python
class SocketFlowInstance:
    def embeddings(self, text: str, **kwargs: Any) -> Dict[str, Any]:
        """Get embeddings for a single text via WebSocket"""
        request = {"text": text}
        return self.client._send_request_sync(
            "embeddings", self.flow_id, request, False
        )
```

**Athari:** Wasanidi wa Python wanaotumia SDK lazima watumie mzunguko kwenye maandishi na kufanya maombi tofauti ya API. Hakuna msaada wa uingizaji wa data kwa wingi (batch) kwa watumiaji wa SDK.

### Athari za Utendaji

Kwa uingizaji wa kawaida wa hati (vifaa 1000 vya maandishi):
**Sasa**: Maombi 1000 tofauti, matumizi 1000 ya mfumo wa utambuzi (model inference).
**Kwa wingi (batch_size=32)**: Maombi 32, matumizi 32 ya mfumo wa utambuzi (96.8% ya kupungua).

Kwa uingizaji wa data kwa wingi (message na vitu 50):
**Sasa**: Simu 50 za `await` mfululizo, takriban sekunde 5-10.
**Kwa wingi**: Simu 1-2 za wingi, takriban sekunde 0.5-1 (uboreshaji wa mara 5-10).

Maktaba kama FastEmbed na zile sawa hufikia ongezeko la takriban moja kwa moja la ufanisi kwa wingi, hadi kikomo cha vifaa (kawaida vifaa 32-128 kwa wingi).

## Muundo wa Kiufundi

### Muundo

Uboreshaji wa uingizaji wa data kwa wingi unahitaji mabadiliko katika vipengele vifuatavyo:

#### 1. **Uboreshaji wa Mfumo**
   Panua `EmbeddingsRequest` ili kusaidia maandishi mengi.
   Panua `EmbeddingsResponse` ili kurejesha seti nyingi za vector.
   Dumishe utangamano na maombi ya maandishi moja.

   Moduli: `trustgraph-base/trustgraph/schema/services/llm.py`

#### 2. **Uboreshaji wa Huduma ya Msingi**
   Sasisha `EmbeddingsService` ili kushughulikia maombi ya wingi.
   Ongeza usanidi wa ukubwa wa wingi.
   Lenga ushughulikiaji wa maombi unaoelinganisha na wingi.

   Moduli: `trustgraph-base/trustgraph/base/embeddings_service.py`

#### 3. **Sasisho za Mchakato wa Mtoa Huduma**
   Sasisha mchakato wa FastEmbed ili kupitisha wingi kamili kwa `embed()`.
   Sasisha mchakato wa Ollama ili kushughulikia wingi (ikiwa inasaidiwa).
   Ongeza ushughulikiaji wa mfululizo kama njia ya dharura kwa watoa huduma ambao hawasaidii wingi.

   Moduli:
   `trustgraph-flow/trustgraph/embeddings/fastembed/processor.py`
   `trustgraph-flow/trustgraph/embeddings/ollama/processor.py`

#### 4. **Uboreshaji kwa Mteja**
   Ongeza njia ya kuingiza data kwa wingi katika `EmbeddingsClient`
   Saidia API za moja kwa moja na za wingi
   Ongeza uingizaji wa data kwa wingi kwa data kubwa

   Moduli: `trustgraph-base/trustgraph/base/embeddings_client.py`

#### 5. **Sasisho kwa Msimuizi - Wasindikaji wa Mchakato**
   Sasisha `graph_embeddings` ili kuingiza muktadha wa vitu kwa wingi
   Sasisha `row_embeddings` ili kuingiza maandishi ya faharasa kwa wingi
   Sasisha `document_embeddings` ikiwa uingizaji wa data kwa wingi unawezekana

   Moduli:
   `trustgraph-flow/trustgraph/embeddings/graph_embeddings/embeddings.py`
   `trustgraph-flow/trustgraph/embeddings/row_embeddings/embeddings.py`
   `trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py`

#### 6. **Uboreshaji kwa Lango la API**
   Ongeza mwisho wa kuingiza data kwa wingi
   Saidia safu ya maandishi katika mwili wa ombi

   Moduli: `trustgraph-flow/trustgraph/gateway/dispatch/embeddings.py`

#### 7. **Uboreshaji kwa Zana ya CLI**
   Ongeza usaidizi wa maandishi mengi au uingizaji wa faili
   Ongeza parameter ya ukubwa wa wingi

   Moduli: `trustgraph-cli/trustgraph/cli/invoke_embeddings.py`

#### 8. **Uboreshaji kwa SDK ya Python**
   Ongeza njia ya `embeddings_batch()` katika `FlowInstance`
   Ongeza njia ya `embeddings_batch()` katika `SocketFlowInstance`
   Saidia API za moja kwa moja na za wingi kwa watumiaji wa SDK

   Moduli:
   `trustgraph-base/trustgraph/api/flow.py`
   `trustgraph-base/trustgraph/api/socket_client.py`

### Mifano ya Data

#### EmbeddingsRequest

```python
@dataclass
class EmbeddingsRequest:
    texts: list[str] = field(default_factory=list)
```

Matumizi:
Nakala moja: `EmbeddingsRequest(texts=["hello world"])`
Kundi: `EmbeddingsRequest(texts=["text1", "text2", "text3"])`

#### Jibu la Uelekezaji

```python
@dataclass
class EmbeddingsResponse:
    error: Error | None = None
    vectors: list[list[list[float]]] = field(default_factory=list)
```

Muundo wa majibu:
`vectors[i]` ina mkusanyiko wa vektali kwa `texts[i]`
Kila mkusanyiko wa vektali ni `list[list[float]]` (modeli zinaweza kurejesha vektali nyingi kwa kila maandishi)
Kwa mfano: maandishi 3 → `vectors` ina vipengele 3, kila kipengele kina uelekezo wa maandishi hayo

### API

#### EmbeddingsClient

```python
class EmbeddingsClient(RequestResponse):
    async def embed(
        self,
        texts: list[str],
        timeout: float = 300,
    ) -> list[list[list[float]]]:
        """
        Embed one or more texts in a single request.

        Args:
            texts: List of texts to embed
            timeout: Timeout for the operation

        Returns:
            List of vector sets, one per input text
        """
        resp = await self.request(
            EmbeddingsRequest(texts=texts),
            timeout=timeout
        )
        if resp.error:
            raise RuntimeError(resp.error.message)
        return resp.vectors
```

#### Ncha ya Ufikiaji (Endpoint) ya Uingizaji (Embedding) ya Langara ya API

Ncha ya ufikiaji (endpoint) imesasishwa ili kusaidia uingizaji (embedding) mmoja au wa kikundi:

```
POST /api/v1/embeddings
Content-Type: application/json

{
    "texts": ["text1", "text2", "text3"],
    "flow_id": "default"
}

Response:
{
    "vectors": [
        [[0.1, 0.2, ...]],
        [[0.3, 0.4, ...]],
        [[0.5, 0.6, ...]]
    ]
}
```

### Maelezo ya Utendaji

#### Awamu ya 1: Marekebisho ya Mfumo

**Ombi la Uingizaji:**
```python
@dataclass
class EmbeddingsRequest:
    texts: list[str] = field(default_factory=list)
```

**Jibu la Uingizwaji:**
```python
@dataclass
class EmbeddingsResponse:
    error: Error | None = None
    vectors: list[list[list[float]]] = field(default_factory=list)
```

**Sasisho la `EmbeddingsService.on_request`:**
```python
async def on_request(self, msg, consumer, flow):
    request = msg.value()
    id = msg.properties()["id"]
    model = flow("model")

    vectors = await self.on_embeddings(request.texts, model=model)
    response = EmbeddingsResponse(error=None, vectors=vectors)

    await flow("response").send(response, properties={"id": id})
```

#### Awamu ya 2: Sasisho la Mchakato wa FastEmbed

**Sasa (Haina ufanisi):**
```python
async def on_embeddings(self, text, model=None):
    use_model = model or self.default_model
    self._load_model(use_model)
    vecs = self.embeddings.embed([text])  # Batch of 1
    return [v.tolist() for v in vecs]
```

**Imebhadiliwa:**
```python
async def on_embeddings(self, texts: list[str], model=None):
    """Embed texts - processes all texts in single model call"""
    if not texts:
        return []

    use_model = model or self.default_model
    self._load_model(use_model)

    # FastEmbed handles the full batch efficiently
    all_vecs = list(self.embeddings.embed(texts))

    # Return list of vector sets, one per input text
    return [[v.tolist()] for v in all_vecs]
```

#### Awamu ya 3: Sasisho la Huduma ya Uingizaji Picha kwenye Grafu

**Sasa (Mfululizo):**
```python
async def on_message(self, msg, consumer, flow):
    entities = []
    for entity in v.entities:
        vectors = await flow("embeddings-request").embed(text=entity.context)
        entities.append(EntityEmbeddings(...))
```

**Imebhadilishwa (Kundi):**
```python
async def on_message(self, msg, consumer, flow):
    # Collect all contexts
    contexts = [entity.context for entity in v.entities]

    # Single batch embedding call
    all_vectors = await flow("embeddings-request").embed(texts=contexts)

    # Pair results with entities
    entities = [
        EntityEmbeddings(
            entity=entity.entity,
            vectors=vectors[0],  # First vector from the set
            chunk_id=entity.chunk_id,
        )
        for entity, vectors in zip(v.entities, all_vectors)
    ]
```

#### Awamu ya 4: Sasisho la Huduma ya Uwekaji Data katika Safu

**Sasa (Mfululizo):**
```python
for text, (index_name, index_value) in texts_to_embed.items():
    vectors = await flow("embeddings-request").embed(text=text)
    embeddings_list.append(RowIndexEmbedding(...))
```

**Imebhadilishwa (Kundi):**
```python
# Collect texts and metadata
texts = list(texts_to_embed.keys())
metadata = list(texts_to_embed.values())

# Single batch embedding call
all_vectors = await flow("embeddings-request").embed(texts=texts)

# Pair results
embeddings_list = [
    RowIndexEmbedding(
        index_name=meta[0],
        index_value=meta[1],
        text=text,
        vectors=vectors[0]  # First vector from the set
    )
    for text, meta, vectors in zip(texts, metadata, all_vectors)
]
```

#### Awamu ya 5: Kuboresha Zana ya Kifaa cha Amri (CLI)

**CLI iliyoboreshwa:**
```python
def main():
    parser = argparse.ArgumentParser(...)

    parser.add_argument(
        'text',
        nargs='*',  # Zero or more texts
        help='Text(s) to convert to embedding vectors',
    )

    parser.add_argument(
        '-f', '--file',
        help='File containing texts (one per line)',
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='Batch size for processing (default: 32)',
    )
```

Matumizi:
```bash
# Single text (existing)
tg-invoke-embeddings "hello world"

# Multiple texts
tg-invoke-embeddings "text one" "text two" "text three"

# From file
tg-invoke-embeddings -f texts.txt --batch-size 64
```

#### Awamu ya 6: Kuboresha Kitengo cha Programu (SDK) cha Python

**FlowInstance (mfumo wa wateja wa HTTP):**

```python
class FlowInstance:
    def embeddings(self, texts: list[str]) -> list[list[list[float]]]:
        """
        Get embeddings for one or more texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of vector sets, one per input text
        """
        input = {"texts": texts}
        return self.request("service/embeddings", input)["vectors"]
```

**SocketFlowInstance (mfumo wa mteja wa WebSocket):**

```python
class SocketFlowInstance:
    def embeddings(self, texts: list[str], **kwargs: Any) -> list[list[list[float]]]:
        """
        Get embeddings for one or more texts via WebSocket.

        Args:
            texts: List of texts to embed

        Returns:
            List of vector sets, one per input text
        """
        request = {"texts": texts}
        response = self.client._send_request_sync(
            "embeddings", self.flow_id, request, False
        )
        return response["vectors"]
```

**Mfano wa Matumizi ya SDK:**

```python
# Single text
vectors = flow.embeddings(["hello world"])
print(f"Dimensions: {len(vectors[0][0])}")

# Batch embedding
texts = ["text one", "text two", "text three"]
all_vectors = flow.embeddings(texts)

# Process results
for text, vecs in zip(texts, all_vectors):
    print(f"{text}: {len(vecs[0])} dimensions")
```

## Mambo ya Kuzingatia Kuhusu Usalama

**Vikomo vya Ukubwa wa Ombi**: Punguza ukubwa wa juu wa kila kikundi ili kuzuia matumizi yasiyofaa ya rasilimali.
**Usimamizi wa Muda wa Hesabu (Timeout)**: Punguza muda wa hesabu ipasavyo kwa ukubwa wa kikundi.
**Vikomo vya Kumbukumbu**: Fuatilia matumizi ya kumbukumbu kwa vikundi vikubwa.
**Uthibitisho wa Pembejeo**: Thibitisha maandishi yote katika kikundi kabla ya kuchakata.

## Mambo ya Kuzingatia Kuhusu Utendaji

### Ubora Unaotarajiwa

**Uwezo wa Kuchakata (Throughput):**
Maandishi moja: ~10-50 maandishi/sekunde (kulingana na mfumo)
Kikundi (ukubwa wa 32): ~200-500 maandishi/sekunde (uboreshaji wa 5-10x)

**Muda wa Kuchakata Kila Maandishi:**
Maandishi moja: 50-200ms kwa kila maandishi
Kikundi (ukubwa wa 32): 5-20ms kwa kila maandishi (kwa wastani)

**Ubora Maalum kwa Huduma:**

| Huduma | Sasa | Kwa Kikundi | Uboreshaji |
|---------|---------|---------|-------------|
| Uwekaji Picha (50 vitu) | 5-10s | 0.5-1s | 5-10x |
| Uwekaji Mistari (100 maandishi) | 10-20s | 1-2s | 5-10x |
| Uingizaji wa Hati (1000 sehemu) | 100-200s | 10-30s | 5-10x |

### Vigezo vya Usanidi

```python
# Recommended defaults
DEFAULT_BATCH_SIZE = 32
MAX_BATCH_SIZE = 128
BATCH_TIMEOUT_MULTIPLIER = 2.0
```

## Mbinu ya Majaribio

### Majaribio ya Kitengo
Uingizaji wa maandishi moja (utangamano wa nyuma)
Usimamizi wa kundi tupu
Utumiaji wa ukubwa wa juu wa kundi
Usimamizi wa makosa kwa kushindwa kwa kundi

### Majaribio ya Uunganisho
Uingizaji wa kundi kamili kupitia Pulsar
Uchakataji wa kundi wa huduma ya uingizaji wa grafu
Uchakataji wa kundi wa huduma ya uingizaji wa mstari
Ncha ya kundi ya lango la API

### Majaribio ya Utendaji
Tathmini ya kasi ya uingizaji wa moja dhidi ya kundi
Matumizi ya kumbukumbu chini ya saizi tofauti za kundi
Uchambuzi wa usambazaji wa kuchelewesha

## Mpango wa Uhamisho

Hii ni toleo la mabadiliko makubwa. Awamu zote zinafanywa pamoja.

### Awamu ya 1: Mabadiliko ya Mpango
Badilisha `text: str` na `texts: list[str]` katika EmbeddingsRequest
Badilisha aina ya `vectors` kuwa `list[list[list[float]]]` katika EmbeddingsResponse

### Awamu ya 2: Masuala ya Marekebisho
Sasisha saini ya `on_embeddings` katika washauri wa FastEmbed na Ollama
Chakata kundi kamili katika wito mmoja wa modeli

### Awamu ya 3: Masuala ya Wateja
Sasisha `EmbeddingsClient.embed()` ili kukubali `texts: list[str]`

### Awamu ya 4: Watumiaji
Sasisha graph_embeddings ili kuingiza muktadha wa vitu katika kundi
Sasisha row_embeddings ili kuingiza maandishi ya faharasa katika kundi
Sasisha document_embeddings ili itumie mpango mpya
Sasisha zana ya CLI

### Awamu ya 5: Lango la API
Sasisha ncha ya uingizaji kwa mpango mpya

### Awamu ya 6: SDK ya Python
Sasisha saini ya `FlowInstance.embeddings()`
Sasisha saini ya `SocketFlowInstance.embeddings()`

## Maswali ya Funguo

**Uingizaji wa Kundi Kubwa**: Je, tunapaswa kusaidia uingizaji wa matokeo kwa kundi kubwa sana (>100 maandishi)?
**Vikomo Maalum vya Mtoa Huduma**: Je, tunapaswa kushughulikia watoa huduma wenye saizi tofauti za kundi?
**Usimamizi wa Kushindwa kwa Kiasi**: Ikiwa maandishi moja katika kundi kushindwa, je, tunapaswa kushindwa kundi lote au kurudisha matokeo ya sehemu?
**Uingizaji wa Kundi wa Mengine**: Je, tunapaswa kuingiza kote kwa ujumbe mwingi wa Chunk au kuendelea na uchakataji wa kila ujumbe?

## Marejeleo

[Dokumenti ya FastEmbed](https://github.com/qdrant/fastembed)
[API ya Uingizaji ya Ollama](https://github.com/ollama/ollama)
[Utekelezaji wa Huduma ya Uingizaji](trustgraph-base/trustgraph/base/embeddings_service.py)
[Uboreshaji wa Utendaji wa GraphRAG](graphrag-performance-optimization.md)
