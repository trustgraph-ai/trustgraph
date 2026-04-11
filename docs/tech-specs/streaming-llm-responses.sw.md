# Vigezo vya Kiufundi vya Utoaji wa Majibu ya LLM kwa Kutiririsha

## Muhtasari

Vigezo hivi vinaelezea utekelezaji wa msaada wa utiririshaji kwa majibu ya LLM
katika TrustGraph. Utiririshaji unawezesha utoaji wa wakati halisi wa alama (tokens)
zinazozalishwa na LLM, badala ya kusubiri hadi majibu kamili yatengenezwe.


Utendaji huu unaunga mkono matumizi yafuatayo:

1. **Mawasiliano ya Mtumiaji ya Kawaida**: Tuma alama kwenye UI wakati zinaozalishwa,
   huku ukitoa maoni ya kuonekana mara moja.
2. **Punguuzo la Muda wa Alama ya Kwanza**: Watumiaji huona matokeo mara moja
   badala ya kusubiri hadi utengenezaji kamili utimalike.
3. **Usimamizi wa Majibu Marefu**: Shirikisha matokeo marefu sana ambayo vinginevyo
   yanaweza kusababisha kukatika au kuzidi mipaka ya kumbukumbu.
4. **Matumizi Tendo**: Wezesha mawasiliano na mawakala yenye majibu.

## Lengo

**Ulinganishaji na Mifumo ya Zamani**: Wateja wa zamani ambao hawatumiwi teknolojia ya utiririshaji wanaendelea kufanya kazi
  bila mabadiliko.
**Muundo wa API Unaofuata Kanuni**: Utiririshaji na mfumo ambao hautiririshi hutumia muundo sawa
  na tofauti ndogo.
**Uwezo wa Mtoa Huduma**: Kusaidia utiririshaji pale unapopatikana, na
  utaratibu wa kurejesha pale unapokosekana.
**Utekelezaji Hatua kwa Hatua**: Utaratibu wa kutekeleza hatua kwa hatua ili kupunguza hatari.
**Usaidizi Kamili**: Utiririshaji kutoka kwa mtoa huduma wa LLM hadi kwa programu
  za mteja kupitia Pulsar, Gateway API, na Python API.

## Asili

### Muundo wa Sasa

Mchakato wa sasa wa kukamilisha maandishi wa LLM unafanya kazi kama ifuatavyo:

1. Mteja hutuma `TextCompletionRequest` pamoja na sehemu za `system` na `prompt`.
2. Huduma ya LLM huchakata ombi na kusubiri uzalishaji kamili.
3. `TextCompletionResponse` moja inarejeshwa pamoja na `response` kamili.

Muundo wa sasa (`trustgraph-base/trustgraph/schema/services/llm.py`):

```python
class TextCompletionRequest(Record):
    system = String()
    prompt = String()

class TextCompletionResponse(Record):
    error = Error()
    response = String()
    in_token = Integer()
    out_token = Integer()
    model = String()
```

### Marekebisho ya Sasa

**Ucheleweshaji**: Watumiaji lazima wasubiri hadi utengenezaji kukamilika kabisa kabla ya kuona matokeo yoyote.
**Hatari ya Muda wa Kufikia (Timeout)**: Utengenezaji mrefu unaweza kuzidi mipaka ya muda wa kufikia ya mteja.
**Uzoefu duni wa mtumiaji (UX)**: Hakuna maelezo wakati wa utengenezaji huunda hisia ya utaratibu polepole.
**Matumizi ya Rasilimali**: Majibu kamili lazima yakahifadhiwe katika kumbukumbu.

Maelekezo haya yanashughulikia mapungufu haya kwa kuwezesha utoaji wa majibu kwa hatua,
huku ikiendelea kudumisha utangamano kamili wa zamani.

## Muundo wa Kiufundi

### Awamu ya 1: Miundombinu

Awamu ya 1 huunda msingi wa utiririshaji kwa kufanya mabadiliko katika muundo, API,
na zana za CLI.

#### Mabadiliko ya Muundo

##### Muundo wa LLM (`trustgraph-base/trustgraph/schema/services/llm.py`)

**Mabadiliko ya Ombi:**

```python
class TextCompletionRequest(Record):
    system = String()
    prompt = String()
    streaming = Boolean()  # NEW: Default false for backward compatibility
```

`streaming`: Wakati `true`, huomba utoaji wa majibu kwa njia ya mtiririko.
Chaguya: `false` (tabia iliyopo inahifadhiwa).

**Mabadiliko ya Majibu:**

```python
class TextCompletionResponse(Record):
    error = Error()
    response = String()
    in_token = Integer()
    out_token = Integer()
    model = String()
    end_of_stream = Boolean()  # NEW: Indicates final message
```

`end_of_stream`: Wakati `true`, inaonyesha kwamba hii ndiyo jibu la mwisho (au pekee).
Kwa ombi lisilo la utiririshaji: Jibu moja na `end_of_stream=true`.
Kwa ombi la utiririshaji: Majibu mengi, yote na `end_of_stream=false`.
  isipokuwa jibu la mwisho.

##### Muundo wa Ombi (`trustgraph-base/trustgraph/schema/services/prompt.py`)

Huduma ya ombi inajumuisha kukamilisha maandishi, kwa hivyo inafuata muundo sawa:

**Mabadiliko ya Ombi:**

```python
class PromptRequest(Record):
    id = String()
    terms = Map(String())
    streaming = Boolean()  # NEW: Default false
```

**Mabadiliko ya Majibu:**

```python
class PromptResponse(Record):
    error = Error()
    text = String()
    object = String()
    end_of_stream = Boolean()  # NEW: Indicates final message
```

#### Mabadiliko ya API ya Langara

API ya Langara lazima iweze kuonyesha uwezo wa utiririshaji kwa wateja wa HTTP/WebSocket.

**Sasisho za API ya REST:**

`POST /api/v1/text-completion`: Kukubali parameter `streaming` katika mwili wa ombi
Tabia ya majibu inategemea bendera ya utiririshaji:
  `streaming=false`: Jibu moja la JSON (tabia ya sasa)
  `streaming=true`: Mto wa Matukio Yanayotumwa na Server (SSE) au ujumbe wa WebSocket

**Muundo wa Majibu (Utiririshaji):**

Kila sehemu iliyoyirishwa ifuataye muundo sawa:
```json
{
  "response": "partial text...",
  "end_of_stream": false,
  "model": "model-name"
}
```

Sehemu ya mwisho:
```json
{
  "response": "final text chunk",
  "end_of_stream": true,
  "in_token": 150,
  "out_token": 500,
  "model": "model-name"
}
```

#### Mabadiliko ya API ya Python

API ya mteja wa Python lazima iunge mkono njia zote mbili za utiririshaji na zisizo za utiririshaji
huku ikiendelea kutoa utangamano na matoleo ya awali.

**Sasisho za LlmClient** (`trustgraph-base/trustgraph/clients/llm_client.py`):

```python
class LlmClient(BaseClient):
    def request(self, system, prompt, timeout=300, streaming=False):
        """
        Non-streaming request (backward compatible).
        Returns complete response string.
        """
        # Existing behavior when streaming=False

    async def request_stream(self, system, prompt, timeout=300):
        """
        Streaming request.
        Yields response chunks as they arrive.
        """
        # New async generator method
```

**Sasisho za PromptClient** (`trustgraph-base/trustgraph/base/prompt_client.py`):

Mfumo sawa na parameter ya `streaming` na toleo la jenereta isiyo na usumbufu.

#### Mabadiliko ya Zana ya CLI

**tg-invoke-llm** (`trustgraph-cli/trustgraph/cli/invoke_llm.py`):

```
tg-invoke-llm [system] [prompt] [--no-streaming] [-u URL] [-f flow-id]
```

Uhamishaji (streaming) huwezeshwa kwa chagu kuendana na uzoefu bora wa mtumiaji.
Bendera `--no-streaming` inazuia uhamishaji.
Wakati uhamishaji unafanya kazi: Tuma alama (tokens) kwenye stdout kadri zinavyofika.
Wakati uhamishaji haufanyi kazi: Subiri jibu kamili, kisha toa.

**tg-invoke-prompt** (`trustgraph-cli/trustgraph/cli/invoke_prompt.py`):

```
tg-invoke-prompt [template-id] [var=value...] [--no-streaming] [-u URL] [-f flow-id]
```

Mfumo sawa na `tg-invoke-llm`.

#### Mabadiliko ya Darasa Msingi la Huduma ya LLM.

**LlmService** (`trustgraph-base/trustgraph/base/llm_service.py`):

```python
class LlmService(FlowProcessor):
    async def on_request(self, msg, consumer, flow):
        request = msg.value()
        streaming = getattr(request, 'streaming', False)

        if streaming and self.supports_streaming():
            async for chunk in self.generate_content_stream(...):
                await self.send_response(chunk, end_of_stream=False)
            await self.send_response(final_chunk, end_of_stream=True)
        else:
            response = await self.generate_content(...)
            await self.send_response(response, end_of_stream=True)

    def supports_streaming(self):
        """Override in subclass to indicate streaming support."""
        return False

    async def generate_content_stream(self, system, prompt, model, temperature):
        """Override in subclass to implement streaming."""
        raise NotImplementedError()
```

--

### Awamu ya 2: Uthibitisho wa Dhana wa VertexAI

Awamu ya 2 inatekeleza utiririshaji katika mtoa huduma mmoja (VertexAI) ili kuthibitisha
miundombinu na kuwezesha majaribio ya mwisho hadi mwisho.

#### Utendaji wa VertexAI

**Moduli:** `trustgraph-vertexai/trustgraph/model/text_completion/vertexai/llm.py`

**Mabadiliko:**

1. Badilisha `supports_streaming()` ili irudishe `True`
2. Leta mtayarishaji wa async `generate_content_stream()`
3. Shiriki modeli zote za Gemini na Claude (kupitia API ya VertexAI Anthropic)

**Utiririshaji wa Gemini:**

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    model_instance = self.get_model(model, temperature)
    response = model_instance.generate_content(
        [system, prompt],
        stream=True  # Enable streaming
    )
    for chunk in response:
        yield LlmChunk(
            text=chunk.text,
            in_token=None,  # Available only in final chunk
            out_token=None,
        )
    # Final chunk includes token counts from response.usage_metadata
```

**Claude (kupitia VertexAI Anthropic) Uhamishaji wa Data:**

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    with self.anthropic_client.messages.stream(...) as stream:
        for text in stream.text_stream:
            yield LlmChunk(text=text)
    # Token counts from stream.get_final_message()
```

#### Mtihani

Majaribio ya kitengo kwa ajili ya kusanyiko la majibu ya utiririshaji
Majaribio ya ujumuishaji na VertexAI (Gemini na Claude)
Majaribio kamili: CLI -> Gateway -> Pulsar -> VertexAI -> nyuma
Majaribio ya utangamano: Maombi ya isiyo ya utiririshaji bado hufanya kazi

--

### Awamu ya 3: Watoa Huduma Wote wa LLM

Awamu ya 3 inaongeza utiifu wa utiririshaji kwa watoa huduma wote wa LLM katika mfumo.

#### Hali ya Utumiaji wa Mtoa Huduma

Kila mtoa huduma lazima ifanye mojawapo ya yafuatayo:
1. **Utiifu Kamili wa Utiririshaji**: Tengeneza `generate_content_stream()`
2. **Njia ya Utangamano**: Shikilia bendera ya `end_of_stream` kwa usahihi
   (irudishe jibu moja na `end_of_stream=true`)

| Mtoa Huduma | Kifurushi | Utiifu wa Utiririshaji |
|----------|---------|-------------------|
| OpenAI | trustgraph-flow | Kamili (API ya asili ya utiririshaji) |
| Claude/Anthropic | trustgraph-flow | Kamili (API ya asili ya utiririshaji) |
| Ollama | trustgraph-flow | Kamili (API ya asili ya utiririshaji) |
| Cohere | trustgraph-flow | Kamili (API ya asili ya utiririshaji) |
| Mistral | trustgraph-flow | Kamili (API ya asili ya utiririshaji) |
| Azure OpenAI | trustgraph-flow | Kamili (API ya asili ya utiririshaji) |
| Google AI Studio | trustgraph-flow | Kamili (API ya asili ya utiririshaji) |
| VertexAI | trustgraph-vertexai | Kamili (Awamu ya 2) |
| Bedrock | trustgraph-bedrock | Kamili (API ya asili ya utiririshaji) |
| LM Studio | trustgraph-flow | Kamili (Inafaa na OpenAI) |
| LlamaFile | trustgraph-flow | Kamili (Inafaa na OpenAI) |
| vLLM | trustgraph-flow | Kamili (Inafaa na OpenAI) |
| TGI | trustgraph-flow | Itatolewa baadaye |
| Azure | trustgraph-flow | Itatolewa baadaye |

#### Mfumo wa Utumiaji

Kwa watoa huduma wanaofaa na OpenAI (OpenAI, LM Studio, LlamaFile, vLLM):

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    response = await self.client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        stream=True
    )
    async for chunk in response:
        if chunk.choices[0].delta.content:
            yield LlmChunk(text=chunk.choices[0].delta.content)
```

--

### Awamu ya 4: API ya Wakala

Awamu ya 4 inaongeza utiririshaji kwenye API ya Wakala. Hii ni ngumu zaidi kwa sababu
API ya Wakala tayari ni mfumo wa ujumbe mwingi (fikra → kitendo → uchunguzi
→ rudia → jibu la mwisho).

#### Mpango wa Sasa wa Wakala

```python
class AgentStep(Record):
    thought = String()
    action = String()
    arguments = Map(String())
    observation = String()
    user = String()

class AgentRequest(Record):
    question = String()
    state = String()
    group = Array(String())
    history = Array(AgentStep())
    user = String()

class AgentResponse(Record):
    answer = String()
    error = Error()
    thought = String()
    observation = String()
```

#### Mabadiliko Yanayopendekezwa ya Muundo wa Wakala

**Omba Mabadiliko:**

```python
class AgentRequest(Record):
    question = String()
    state = String()
    group = Array(String())
    history = Array(AgentStep())
    user = String()
    streaming = Boolean()  # NEW: Default false
```

**Mabadiliko ya Majibu:**

Wakala hutengeneza aina nyingi za matokeo wakati wa mchakato wake wa kufikiri:
Mawazo (ufikiri)
Vitendo (simu za zana)
Uchunguzi (matokeo ya zana)
Jibu (jibu la mwisho)
Madosa

Kwa kuwa `chunk_type` inaonyesha aina gani ya maudhui yanatumiwa, nafasi tofauti
za `answer`, `error`, `thought`, na `observation` zinaweza kuunganishwa katika
nafasi moja ya `content`:

```python
class AgentResponse(Record):
    chunk_type = String()       # "thought", "action", "observation", "answer", "error"
    content = String()          # The actual content (interpretation depends on chunk_type)
    end_of_message = Boolean()  # Current thought/action/observation/answer is complete
    end_of_dialog = Boolean()   # Entire agent dialog is complete
```

**Maana ya Viwanja:**

`chunk_type`: Inaonyesha aina ya yaliyomo katika sehemu `content`
  `"thought"`: Tafakari/fikra za wakala
  `"action"`: Chombo/kitendo kinachotumika
  `"observation"`: Matokeo ya utekelezaji wa chombo
  `"answer"`: Jibu la mwisho kwa swali la mtumiaji
  `"error"`: Ujumbe wa kosa

`content`: Yaliyomo halisi yanayotiririshwa, ambayo hutafsiriwa kulingana na `chunk_type`

`end_of_message`: Wakati `true`, aina ya sehemu ya sasa imekamilika
  Mfano: Alama zote za fikra ya sasa zimetumwa
  Inaruhusu wateja kujua wakati wa kuendelea na hatua inayofuata

`end_of_dialog`: Wakati `true`, mwingiliano wote wa wakala umekamilika
  Hii ndio ujumbe wa mwisho katika mtiririko

#### Tabia ya Utiririshaji wa Wakala

Wakati `streaming=true`:

1. **Utiririshaji wa fikra:**
   Sehemu nyingi zenye `chunk_type="thought"`, `end_of_message=false`
   Sehemu ya mwisho ya fikra ina `end_of_message=true`
2. **Arifa ya kitendo:**
   Sehemu moja yenye `chunk_type="action"`, `end_of_message=true`
3. **Uchunguzi:**
   Sehemu(ma) yenye `chunk_type="observation"`, ya mwisho ina `end_of_message=true`
4. **Rudia** hatua za 1-3 wakati wakala anafikiri
5. **Jibu la mwisho:**
   `chunk_type="answer"` yenye jibu la mwisho katika `content`
   Sehemu ya mwisho ina `end_of_message=true`, `end_of_dialog=true`

**Mfululizo wa Mfano wa Mtiririko:**

```
{chunk_type: "thought", content: "I need to", end_of_message: false, end_of_dialog: false}
{chunk_type: "thought", content: " search for...", end_of_message: true, end_of_dialog: false}
{chunk_type: "action", content: "search", end_of_message: true, end_of_dialog: false}
{chunk_type: "observation", content: "Found: ...", end_of_message: true, end_of_dialog: false}
{chunk_type: "thought", content: "Based on this", end_of_message: false, end_of_dialog: false}
{chunk_type: "thought", content: " I can answer...", end_of_message: true, end_of_dialog: false}
{chunk_type: "answer", content: "The answer is...", end_of_message: true, end_of_dialog: true}
```

Wakati `streaming=false`:
Tabia ya sasa inahifadhiwa
Jibu moja lenye jibu kamili
`end_of_message=true`, `end_of_dialog=true`

#### Bandari na API ya Python

Bandari: Njia mpya ya SSE/WebSocket kwa utiririshaji wa wakala
API ya Python: Njia mpya ya `agent_stream()` ya jenereta ya async

--

## Masuala ya Usalama

**Hakuna eneo jipya la shambulio**: Utiririshaji hutumia uthibitishaji/idhini sawa
**Mipaka ya kasi**: Tumia mipaka ya kasi kwa kila tokeni au kila sehemu ikiwa inahitajika
**Usimamizi wa muunganisho**: Vunjeni kwa usahihi mitiririsho wakati mteja anakatiza
**Usimamizi wa muda**: Maombi ya utiririshaji yanahitaji usimamizi sahihi wa muda

## Masuala ya Utendaji

**Kumbukumbu**: Utiririshaji hupunguza matumizi ya juu ya kumbukumbu (hakuna buffering kamili ya jibu)
**Ucheleweshaji**: Muda wa hadi tokeni ya kwanza umepunguzwa sana
**Mzigo wa muunganisho**: Muunganisho wa SSE/WebSocket una mzigo wa kudumisha muunganisho
**Uwezo wa Pulsar**: Ujumbe mdogo mwingi dhidi ya ujumbe mmoja mkubwa
  mbadala

## Mkakati wa Majaribio

### Majaribio ya Kitengo
Usanidi/uondoaji wa schema na sehemu mpya
Utangamano wa nyuma (sehemu zilizopotea hutumia chaguo-msingi)
Mantiki ya kusanyiko ya sehemu

### Majaribio ya Uunganisho
Utaratibu wa utiririshaji wa kila mtoa huduma wa LLM
Njia za utiririshaji za API ya Bandari
Njia za utiririshaji za mteja wa Python

### Majaribio ya Ukingo hadi Ukingo
Pato la utiririshaji la zana ya CLI
Mchakato kamili: Mteja → Bandari → Pulsar → LLM → kurudi
Mizigo mchanganyiko ya utiririshaji/isiyo ya utiririshaji

### Majaribio ya Utangamano wa Nyuma
Wateja wazima hufanya kazi bila mabadiliko
Maombi ya utiririshaji hayatendeshwi sawa

## Mpango wa Uhamishaji

### Awamu ya 1: Miundombinu
Weka mabadiliko ya schema (utangamano wa nyuma)
Weka sasisho za API ya Bandari
Weka sasisho za API ya Python
Toa sasisho za zana ya CLI

### Awamu ya 2: VertexAI
Tuma utekelezaji wa VertexAI unaotumia mtiririko.
Thibitisha kwa kutumia majaribio.

### Awamu ya 3: Watoa Huduma Wote
Toa sasisho za watoa huduma hatua kwa hatua.
Fuatilia masuala yaliyotokea.

### Awamu ya 4: API ya Wakala
Tuma mabadiliko ya muundo wa wakala.
Tuma utekelezaji wa mtiririko wa wakala.
Sasisha nyaraka.

## Ratiba

| Awamu | Maelezo | Utendaji |
|-------|-------------|--------------|
| Awamu ya 1 | Miundombinu | Hakuna |
| Awamu ya 2 | Jaribio la VertexAI | Awamu ya 1 |
| Awamu ya 3 | Watoa Huduma Wote | Awamu ya 2 |
| Awamu ya 4 | API ya Wakala | Awamu ya 3 |

## Maamuzi ya Ubunifu

Maswali yafuatayo yaliyulizwa yamejibiwa wakati wa maelezo:

1. **Hesabu za Tokeni katika Mtiririko**: Hesabu za tokeni ni tofauti, sio jumla.
   Wateja wanaweza kuzijumlisha ikiwa ni lazima. Hii inalingana na jinsi watoa huduma wengi wanavyoripoti
   matumizi na inarahisisha utekelezaji.

2. **Usimamizi wa Madhira katika Mitiririko**: Ikiwa hitilafu itatokea, sehemu ya `error`
   itajazwa na sehemu zingine hazihitajiki. Hitilafu daima ndio mawasiliano ya mwisho
   jumbe zingine za baadae haziruhusiwi au zinatarajiwa baada ya
   hitilafu. Kwa mitiririko ya LLM/Prompt, `end_of_stream=true`. Kwa mitiririko ya Wakala,
   `chunk_type="error"` pamoja na `end_of_dialog=true`.

3. **Urekebishaji wa Majibu ya Kawaida**: Itifaki ya mawasiliano (Pulsar) ni thabiti,
   kwa hivyo, kujaribu tena jumbe za mtu binafsi haihitajiki. Ikiwa mteja unapoteza
   uhusiano wa mtiririko au kukatika, lazima ujaribu tena ombi lote kutoka mwanzo.

4. **Mtiririko wa Huduma ya Prompt**: Mtiririko unaoendeshwa tu kwa maandishi (`text`)
   majibu, sio majibu yaliyopangwa (`object`). Huduma ya prompt inajua
   mapema ikiwa pato itakuwa JSON au maandishi kulingana na kiolezo cha prompt.
   Ikiwa ombi la mtiririko lilitolewa kwa prompt ya pato ya JSON, huduma
   inapaswa:
   Kurudisha JSON kamili katika jibu moja pamoja na `end_of_stream=true`, au
   Kukataa ombi la mtiririko na hitilafu

## Maswali Yaliyobaki

Hakuna kwa sasa.

## Marejeleo

Muundo wa sasa wa LLM: `trustgraph-base/trustgraph/schema/services/llm.py`
Muundo wa sasa wa prompt: `trustgraph-base/trustgraph/schema/services/prompt.py`
Muundo wa sasa wa wakala: `trustgraph-base/trustgraph/schema/services/agent.py`
Msingi wa huduma ya LLM: `trustgraph-base/trustgraph/base/llm_service.py`
Mtoa huduma wa VertexAI: `trustgraph-vertexai/trustgraph/model/text_completion/vertexai/llm.py`
API ya lango: `trustgraph-base/trustgraph/api/`
Zana za CLI: `trustgraph-cli/trustgraph/cli/`
