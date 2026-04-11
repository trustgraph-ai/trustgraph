# Huduma za Zana: Zana za Wakala Zinazoweza Kuunganishwa Kwenye Mfumo

## Hali

Imetekelezwa

## Muhtasari

Maelezo haya yanafafanua mfumo wa zana za wakala ambazo zinaweza kuunganishwa kwenye mfumo, zinazojulikana kama "huduma za zana". Tofauti na aina za zana zilizojumuishwa awali (`KnowledgeQueryImpl`, `McpToolImpl`, n.k.), huduma za zana huruhusu zana mpya kuletwa kwa:

1. Kuanzisha huduma mpya iliyojengwa kwenye Pulsar
2. Kuongeza maelezo ya usanidi ambayo huambia wakala jinsi ya kuiita

Hii inaruhusu uboreshaji bila kubadilisha mfumo msingi wa wakala.

## Dhana

| Neno | Ufafanuzi |
|------|------------|
| **Zana Iliyojumuishwa** | Aina za zana zilizopo zilizo na matumizi yaliyopangwa mapema katika `tools.py` |
| **Huduma ya Zana** | Huduma ya Pulsar ambayo inaweza kuita kama zana ya wakala, iliyoainishwa na maelezo ya huduma |
| **Zana** | Toleo lililosanidiwa ambalo linarejelea huduma ya zana, lililowezeshwa kwa wakala/LLM |

Hii ni mfumo wa tabaka mbili, sawa na zana za MCP:
MCP: Seva ya MCP inaainisha kiolesura cha zana → Usanidi wa zana huirejelea
Huduma za Zana: Huduma ya zana inaainisha kiolesura cha Pulsar → Usanidi wa zana huirejelea

## Asili: Zana Zilizopo

### Utendaji wa Zana Iliyojumuishwa

Zana kwa sasa zinafafanuliwa katika `trustgraph-flow/trustgraph/agent/react/tools.py` na matumizi yaliyopangwa:

```python
class KnowledgeQueryImpl:
    async def invoke(self, question):
        client = self.context("graph-rag-request")
        return await client.rag(question, self.collection)
```

Kila aina ya zana:
Ina huduma ya Pulsar iliyopangwa tayari ambayo inaitumia (k.m., `graph-rag-request`)
Inajua njia sahihi ya kuita kwenye mteja (k.m., `client.rag()`)
Ina vigezo vilivyopangwa ambavyo vimefafuliwa katika utekelezaji

### Usajili wa Zana (service.py:105-214)

Zana huzamilishwa kutoka kwa usanidi na sehemu ya `type` ambayo inaelekeza kwenye utekelezaji:

```python
if impl_id == "knowledge-query":
    impl = functools.partial(KnowledgeQueryImpl, collection=data.get("collection"))
elif impl_id == "text-completion":
    impl = TextCompletionImpl
# ... etc
```

## Usanifu

### Mfumo wa Tabaka Mbili

#### Tabaka la 1: Kisajili cha Huduma ya Zana

Huduma ya zana inaelezea kiolesura cha huduma ya Pulsar. Inaangazia:
Mizinga ya Pulsar kwa ombi/jibu
Vigezo vya usanidi ambavyo vinahitajika na zana zinazotumia huduma hiyo

```json
{
  "id": "custom-rag",
  "request-queue": "non-persistent://tg/request/custom-rag",
  "response-queue": "non-persistent://tg/response/custom-rag",
  "config-params": [
    {"name": "collection", "required": true}
  ]
}
```

Huduma ya zana ambayo haihitaji vigezo vya usanidi:

```json
{
  "id": "calculator",
  "request-queue": "non-persistent://tg/request/calc",
  "response-queue": "non-persistent://tg/response/calc",
  "config-params": []
}
```

#### Kategoria ya 2: Kisajili cha Zana

Zana inarejelea huduma ya zana na hutoa:
Maelezo ya vigezo ya usanidi (yakinayo na mahitaji ya huduma)
Meta-data ya zana kwa wakala (jina, maelezo)
Ufafanuzi wa hoja kwa mfumo wa lugha (LLM)

```json
{
  "type": "tool-service",
  "name": "query-customers",
  "description": "Query the customer knowledge base",
  "service": "custom-rag",
  "collection": "customers",
  "arguments": [
    {
      "name": "question",
      "type": "string",
      "description": "The question to ask about customers"
    }
  ]
}
```

Zana nyingi zinaweza kurejelea huduma moja kwa usanidi tofauti:

```json
{
  "type": "tool-service",
  "name": "query-products",
  "description": "Query the product knowledge base",
  "service": "custom-rag",
  "collection": "products",
  "arguments": [
    {
      "name": "question",
      "type": "string",
      "description": "The question to ask about products"
    }
  ]
}
```

### Muundo wa Ombi

Wakati zana inaitwa, ombi kwa huduma ya zana linajumuisha:
`user`: Kutoka ombi la wakala (utumiaji wa pamoja)
`config`: Maelezo ya usanidi yaliyokandwa katika umbizo la JSON kutoka kwa maelezo ya zana
`arguments`: Majadilisho yaliyokandwa katika umbizo la JSON kutoka kwa mfumo wa lugha kubwa (LLM)

```json
{
  "user": "alice",
  "config": "{\"collection\": \"customers\"}",
  "arguments": "{\"question\": \"What are the top customer complaints?\"}"
}
```

Huduma ya zana hupokea haya kama dictionaries yaliyochanganishwa katika njia ya `invoke`.

### Utendakazi wa Huduma ya Zana ya Jumla

Darasa la `ToolServiceImpl` huita huduma za zana kulingana na usanidi:

```python
class ToolServiceImpl:
    def __init__(self, context, request_queue, response_queue, config_values, arguments, processor):
        self.request_queue = request_queue
        self.response_queue = response_queue
        self.config_values = config_values  # e.g., {"collection": "customers"}
        # ...

    async def invoke(self, **arguments):
        client = await self._get_or_create_client()
        response = await client.call(user, self.config_values, arguments)
        if isinstance(response, str):
            return response
        else:
            return json.dumps(response)
```

## Maamuzi ya Ubunifu

### Mfumo wa Uwekaji wa Tabaka Mbili

Huduma za zana zinafuata mfumo wa tabaka mbili, sawa na zana za MCP:

1. **Huduma ya Zana**: Inaelezea kiolesura cha huduma ya Pulsar (mada, vigezo muhimu vya usanidi)
2. **Zana**: Inarejelea huduma ya zana, hutoa maadili ya usanidi, inaelezea hoja za LLM

Tofauti hii inaruhusu:
Huduma moja ya zana kutumika na zana nyingi zenye usanidi tofauti
Tofauti wazi kati ya kiolesura cha huduma na usanidi wa zana
Ujuzi wa matumizi wa maelezo ya huduma

### Ramani ya Ombi: Kupitisha na Kifurushi

Ombi kwa huduma ya zana ni kifurushi kilicho na muundo, kinachojumuisha:
`user`: Inasambazwa kutoka ombi la wakala kwa ajili ya utumiaji wa pamoja
Maadili ya usanidi: Kutoka kwa maelezo ya zana (k.m., `collection`)
`arguments`: Hoja zilizotolewa na LLM, zinazopitishwa kama kamusi

Kidhibiti cha wakala huchanganua jibu la LLM kuwa `act.arguments` kama kamusi (`agent_manager.py:117-154`). Kamusi hii inajumuishwa katika kifurushi cha ombi.

### Usimamizi wa Mpango: Bila Aina

Maombi na majibu hutumia kamusi zisizo na aina. Hakuna uthibitishaji wa mpango katika ngazi ya wakala - huduma ya zana inawajibika kwa uthibitishaji wa pembejeo zake. Hii hutoa uwezo mkubwa wa kufafanua huduma mpya.

### Kiolesura cha Mteja: Mada za Moja kwa Moja za Pulsar

Huduma za zana hutumia mada za moja kwa moja za Pulsar bila kuhitaji usanidi wa mtiririko. Maelezo ya huduma-ya-zana yanaelezea majina kamili ya folyo:

```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [...]
}
```

Hii inaruhusu huduma kuwa zimepakwa kwenye nafasi yoyote.

### Usimamizi wa Makosa: Mfumo wa Makosa wa Kawaida

Majibu ya huduma ya zana yanafuata mfumo wa sasa wa muundo na sehemu ya `error`:

```python
@dataclass
class Error:
    type: str = ""
    message: str = ""
```

Muundo wa majibu:
Mafanikio: `error` ni `None`, majibu yana matokeo
Kosa: `error` imejaa na `type` na `message`

Hii inafanana na muundo uliotumika katika huduma zingine (e.g., `PromptResponse`, `QueryResponse`, `AgentResponse`).

### Uhusiano wa Ombi/Jibu

Maombi na majibu yanahusishwa kwa kutumia `id` katika vipengele vya ujumbe wa Pulsar:

Ombi linajumuisha `id` katika vipengele: `properties={"id": id}`
Majibu (mengi) yanajumuisha `id` sawa: `properties={"id": id}`

Hii inafuata muundo uliopo katika codebase (e.g., `agent_service.py`, `llm_service.py`).

### Usaidizi wa Uhamaji (Streaming)

Huduma za zana zinaweza kurejesha majibu ya uhamaji:

Ujumbe mwingi wa majibu wenye `id` sawa katika vipengele
Kila jibu linajumuisha `end_of_stream: bool`
Jibu la mwisho lina `end_of_stream: True`

Hii inafanana na muundo uliotumika katika `AgentResponse` na huduma zingine za uhamaji.

### Usimamizi wa Majibu: Kurudisha Kamba (String)

Zana zote zilizopo zinafuata muundo huo: **kupokea hoja kama orodha, kurejesha matokeo kama kamba**.

| Zana | Usimamizi wa Majibu |
|------|------------------|
| `KnowledgeQueryImpl` | Inarejea `client.rag()` moja kwa moja (kamba) |
| `TextCompletionImpl` | Inarejea `client.question()` moja kwa moja (kamba) |
| `McpToolImpl` | Inarejea kamba, au `json.dumps(output)` ikiwa si kamba |
| `StructuredQueryImpl` | Inaweka matokeo katika kamba |
| `PromptImpl` | Inarejea `client.prompt()` moja kwa moja (kamba) |

Huduma za zana zinafuata mkataba huo:
Huduma inarejea jibu la kamba (matokeo)
Ikiwa jibu si kamba, linabadilishwa kupitia `json.dumps()`
Hakuna usanidi wa uondoaji unaohitajika katika maelezo

Hii huweka maelezo kuwa rahisi na kuweka jukumu kwa huduma kurejesha jibu la maandishi linalofaa kwa wakala.

## Mwongozo wa Usanidi

Ili kuongeza huduma mpya ya zana, vipengele viwili vya usanidi vinahitajika:

### 1. Usanidi wa Huduma ya Zana

Inahifadhiwa chini ya ufunguo wa usanidi `tool-service`. Inaelezea folyo za Pulsar na vigezo vinavyopatikana vya usanidi.

| Uwanja | Inahitajika | Maelezo |
|-------|----------|-------------|
| `id` | Ndiyo | Kitambulisho cha kipekee kwa huduma ya zana |
| `request-queue` | Ndiyo | Mada kamili ya Pulsar kwa maombi (e.g., `non-persistent://tg/request/joke`) |
| `response-queue` | Ndiyo | Mada kamili ya Pulsar kwa majibu (e.g., `non-persistent://tg/response/joke`) |
| `config-params` | Hapana | Safu ya vigezo vya usanidi ambavyo huduma inakubali |

Kila kiparamu cha usanidi kinaweza kuainisha:
`name`: Jina la kiparamu (inahitajika)
`required`: Ikiwa kiparamu lazima kipewe na zana (cha kawaida: bandia)

Mfano:
```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [
    {"name": "style", "required": false}
  ]
}
```

### 2. Usanidi wa Zana

Hifadhiwa chini ya ufunguo wa `tool`. Inaelezea zana ambayo wakala anaweza kutumia.

| Sehemu | Inahitajika | Maelezo |
|-------|----------|-------------|
| `type` | Ndiyo | Lazima iwe `"tool-service"` |
| `name` | Ndiyo | Jina la zana linaloonyeshwa kwa LLM |
| `description` | Ndiyo | Maelezo ya kile ambacho zana inafanya (yanaonyeshwa kwa LLM) |
| `service` | Ndiyo | Kitambulisho cha huduma ya zana inayotumiwa |
| `arguments` | Hapana | Safu ya maelezo ya hoja kwa ajili ya LLM |
| *(vigezo vya usanidi)* | Hubadilika | Vigezo vyovyote vya usanidi vilivyobainishwa na huduma |

Kila hoja inaweza kubainisha:
`name`: Jina la hoja (inahitajika)
`type`: Aina ya data, kwa mfano, `"string"` (inahitajika)
`description`: Maelezo yanayoonyeshwa kwa LLM (inahitajika)

Mfano:
```json
{
  "type": "tool-service",
  "name": "tell-joke",
  "description": "Tell a joke on a given topic",
  "service": "joke-service",
  "style": "pun",
  "arguments": [
    {
      "name": "topic",
      "type": "string",
      "description": "The topic for the joke (e.g., programming, animals, food)"
    }
  ]
}
```

### Upakiaji wa Mipangilio

Tumia `tg-put-config-item` ili kupakia mipangilio:

```bash
# Load tool-service config
tg-put-config-item tool-service/joke-service < joke-service.json

# Load tool config
tg-put-config-item tool/tell-joke < tell-joke.json
```

Wakala-mtawala lazima uanzishwe tena ili kuchukua usanidi mpya.

## Maelezo ya Utendaji

### Mpango

Aina za ombi na majibu katika `trustgraph-base/trustgraph/schema/services/tool_service.py`:

```python
@dataclass
class ToolServiceRequest:
    user: str = ""           # User context for multi-tenancy
    config: str = ""         # JSON-encoded config values from tool descriptor
    arguments: str = ""      # JSON-encoded arguments from LLM

@dataclass
class ToolServiceResponse:
    error: Error | None = None
    response: str = ""       # String response (the observation)
    end_of_stream: bool = False
```

### Upande wa Server: Huduma ya DynamicToolService

Darasa la msingi katika `trustgraph-base/trustgraph/base/dynamic_tool_service.py`:

```python
class DynamicToolService(AsyncProcessor):
    """Base class for implementing tool services."""

    def __init__(self, **params):
        topic = params.get("topic", default_topic)
        # Constructs topics: non-persistent://tg/request/{topic}, non-persistent://tg/response/{topic}
        # Sets up Consumer and Producer

    async def invoke(self, user, config, arguments):
        """Override this method to implement the tool's logic."""
        raise NotImplementedError()
```

### Upande wa Mteja: Huduma ya ToolServiceImpl

Utendaji katika `trustgraph-flow/trustgraph/agent/react/tools.py`:

```python
class ToolServiceImpl:
    def __init__(self, context, request_queue, response_queue, config_values, arguments, processor):
        # Uses the provided queue paths directly
        # Creates ToolServiceClient on first use

    async def invoke(self, **arguments):
        client = await self._get_or_create_client()
        response = await client.call(user, config_values, arguments)
        return response if isinstance(response, str) else json.dumps(response)
```

### Faili

| Faili | Madhumuni |
|------|---------|
| `trustgraph-base/trustgraph/schema/services/tool_service.py` | Mifumo ya ombi/jibu |
| `trustgraph-base/trustgraph/base/tool_service_client.py` | Mteja wa kutumia huduma |
| `trustgraph-base/trustgraph/base/dynamic_tool_service.py` | Darasa la msingi kwa utekelezaji wa huduma |
| `trustgraph-flow/trustgraph/agent/react/tools.py` | Darasa la `ToolServiceImpl` |
| `trustgraph-flow/trustgraph/agent/react/service.py` | Kupakia usanidi |

### Mifano: Huduma ya Utani

Mfano wa huduma katika `trustgraph-flow/trustgraph/tool_service/joke/`:

```python
class Processor(DynamicToolService):
    async def invoke(self, user, config, arguments):
        style = config.get("style", "pun")
        topic = arguments.get("topic", "")
        joke = pick_joke(topic, style)
        return f"Hey {user}! Here's a {style} for you:\n\n{joke}"
```

Usanidi wa huduma za zana:
```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [{"name": "style", "required": false}]
}
```

Usanidi wa zana:
```json
{
  "type": "tool-service",
  "name": "tell-joke",
  "description": "Tell a joke on a given topic",
  "service": "joke-service",
  "style": "pun",
  "arguments": [
    {"name": "topic", "type": "string", "description": "The topic for the joke"}
  ]
}
```

### Ulinganishi na Matoleo ya Zamani

Aina za zana zilizopo zilizojumuishwa zinaendelea kufanya kazi bila kubadilishwa.
`tool-service` ni aina mpya ya zana pamoja na aina zilizopo (`knowledge-query`, `mcp-tool`, n.k.).

## Mambo ya Kuzingatia Baadaye

### Huduma Zinajitangaza Zenyewe

Uboreshaji wa siku zijazo unaweza kuruhusu huduma kuchapisha maelezo yao wenyewe:

Huduma huchapisha kwenye mada iliyojulikana ya `tool-descriptors` wakati wa kuanza.
Wakala husajili na kusajili zana kwa njia ya moja kwa moja.
Inaruhusu uunganishaji halisi wa "plug-and-play" bila mabadiliko ya usanidi.

Hii ni nje ya upeo wa utekelezaji wa awali.

## Marejeleo

Utaratibu wa sasa wa zana: `trustgraph-flow/trustgraph/agent/react/tools.py`
Usajili wa zana: `trustgraph-flow/trustgraph/agent/react/service.py:105-214`
Schemas za wakala: `trustgraph-base/trustgraph/schema/services/agent.py`
