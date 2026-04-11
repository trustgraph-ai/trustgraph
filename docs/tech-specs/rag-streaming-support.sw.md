---
layout: default
title: "Vigezo vya Ufundi kwa Usaidizi wa Utiririshaji (Streaming)"
parent: "Swahili (Beta)"
---

# Vigezo vya Ufundi kwa Usaidizi wa Utiririshaji (Streaming)

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Muhtasari

Vigezo hivi vinaelezea kuongeza usaidizi wa utiririshaji kwa huduma za GraphRAG na DocumentRAG, na hivyo kuruhusu majibu ya wakati halisi, token kwa token, kwa maswali ya chati ya maarifa na utafutaji wa nyaraka. Hii inaongeza usanifu uliopo wa utiririshaji ambao tayari umetumiwa kwa huduma za kukamilisha maandishi, matamshi, na wakala (agent) za LLM.

## Lengo

**Uzoefu sawa wa utiririshaji**: Kutoa uzoefu sawa wa utiririshaji katika huduma zote za TrustGraph.
**Mabadiliko madogo ya API**: Kuongeza usaidizi wa utiririshaji kwa bendera moja `streaming`, kufuata mifumo iliyopo.
**Ulinganifu na matumizi ya awali**: Kuhifadhi tabia ya sasa isiyo ya utiririshaji kama chaguo-msingi.
**Kutumia miundombinu iliyopo**: Kutumia utiririshaji wa PromptClient ambao tayari umetumiwa.
**Usaidizi wa lango (gateway)**: Kuruhusu utiririshaji kupitia lango la websocket kwa programu za wateja.

## Asili

Huduma za utiririshaji zilizotumiwa kwa sasa:
**Huduma ya kukamilisha maandishi ya LLM**: Awamu ya 1 - utiririshaji kutoka kwa watoa huduma wa LLM.
**Huduma ya matamshi**: Awamu ya 2 - utiririshaji kupitia vipatacho vya matamshi.
**Huduma ya wakala**: Awamu ya 3-4 - utiririshaji wa majibu ya ReAct kwa vipande vya hatua/angalifu/jibu.

Mapungufu ya sasa kwa huduma za RAG:
GraphRAG na DocumentRAG zinaunga mkono tu majibu ya kukomesha.
Watumiaji lazima wasubiri majibu kamili ya LLM kabla ya kuona matokeo yoyote.
Uzoefu mbaya kwa majibu marefu kutoka kwa chati ya maarifa au maswali ya nyaraka.
Uzoefu usio sawa na huduma zingine za TrustGraph.

Vigezo hivi vinashughulikia pengo hizi kwa kuongeza usaidizi wa utiririshaji kwa GraphRAG na DocumentRAG. Kwa kuruhusu majibu ya token kwa token, TrustGraph inaweza:
Kutoa uzoefu sawa wa utiririshaji kwa aina zote za maswali.
Kupunguza muda uliodhaniwa wa maswali ya RAG.
Kuruhusu maoni bora ya maendeleo kwa maswali yanayoendelea.
Kusaidia onyesho la wakati halisi katika programu za wateja.

## Muundo wa Ufundi

### Usanifu

Utumiaji wa utiririshaji wa RAG hutumia miundombinu iliyopo:

1. **Utiririshaji wa PromptClient** (Tayari umetumiwa)
   `kg_prompt()` na `document_prompt()` tayari hupokea vigezo vya `streaming` na `chunk_callback`.
   Haya huita `prompt()` ndani na usaidizi wa utiririshaji.
   Hakuna mabadiliko yanayohitajika kwa PromptClient.

   Moduli: `trustgraph-base/trustgraph/base/prompt_client.py`

2. **Huduma ya GraphRAG** (Inahitaji kupitisha parameter ya utiririshaji)
   Ongeza parameter ya `streaming` kwa njia ya `query()`.
   Pasa bendera ya utiririshaji na vipengele vya kurudisha (callbacks) kwa `prompt_client.kg_prompt()`.
   Schema ya GraphRagRequest inahitaji sehemu ya `streaming`.

   Moduli:
   `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py`
   `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` (Mchakato)
   `trustgraph-base/trustgraph/schema/graph_rag.py` (Schema ya ombi)
   `trustgraph-flow/trustgraph/gateway/dispatch/graph_rag.py` (Lango)

3. **Huduma ya DocumentRAG** (Inahitaji kupitisha parameter ya utiririshaji)
   Ongeza parameter ya `streaming` kwa njia ya `query()`.
   Pasa bendera ya utiririshaji na vipengele vya kurudisha (callbacks) kwa `prompt_client.document_prompt()`.
   Schema ya DocumentRagRequest inahitaji sehemu ya `streaming`.

   Moduli:
   `trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py`
   `trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` (Mchakato)
   `trustgraph-base/trustgraph/schema/document_rag.py` (Schema ya ombi)
   `trustgraph-flow/trustgraph/gateway/dispatch/document_rag.py` (Lango)

### Mtiririko wa Data

**Usiokuwa na utiririshaji (sasa)**:
```
Client → Gateway → RAG Service → PromptClient.kg_prompt(streaming=False)
                                   ↓
                                Prompt Service → LLM
                                   ↓
                                Complete response
                                   ↓
Client ← Gateway ← RAG Service ←  Response
```

**Utiririshaji (kupendekezwa):**
```
Client → Gateway → RAG Service → PromptClient.kg_prompt(streaming=True, chunk_callback=cb)
                                   ↓
                                Prompt Service → LLM (streaming)
                                   ↓
                                Chunk → callback → RAG Response (chunk)
                                   ↓                       ↓
Client ← Gateway ← ────────────────────────────────── Response stream
```

### API

**Mabadiliko ya GraphRAG**:

1. **GraphRag.query()** - Ongeza vigezo vya utiririshaji
```python
async def query(
    self, query, user, collection,
    verbose=False, streaming=False, chunk_callback=None  # NEW
):
    # ... existing entity/triple retrieval ...

    if streaming and chunk_callback:
        resp = await self.prompt_client.kg_prompt(
            query, kg,
            streaming=True,
            chunk_callback=chunk_callback
        )
    else:
        resp = await self.prompt_client.kg_prompt(query, kg)

    return resp
```

2. **Muundo wa GraphRagRequest** - Ongeza sehemu ya utiririshaji.
```python
class GraphRagRequest(Record):
    query = String()
    user = String()
    collection = String()
    streaming = Boolean()  # NEW
```

3. **Muundo wa GraphRagResponse** - Ongeza sehemu za utiririshaji (fuata mfumo wa Wakala).
```python
class GraphRagResponse(Record):
    response = String()    # Legacy: complete response
    chunk = String()       # NEW: streaming chunk
    end_of_stream = Boolean()  # NEW: indicates last chunk
```

4. **Mchakato** - Ruhusu mtiririko kupita.
```python
async def handle(self, msg):
    # ... existing code ...

    async def send_chunk(chunk):
        await self.respond(GraphRagResponse(
            chunk=chunk,
            end_of_stream=False,
            response=None
        ))

    if request.streaming:
        full_response = await self.rag.query(
            query=request.query,
            user=request.user,
            collection=request.collection,
            streaming=True,
            chunk_callback=send_chunk
        )
        # Send final message
        await self.respond(GraphRagResponse(
            chunk=None,
            end_of_stream=True,
            response=full_response
        ))
    else:
        # Existing non-streaming path
        response = await self.rag.query(...)
        await self.respond(GraphRagResponse(response=response))
```

**Mabadiliko ya DocumentRAG**:

Muundo sawa na GraphRAG:
1. Ongeza vigezo `streaming` na `chunk_callback` kwenye `DocumentRag.query()`
2. Ongeza sehemu `streaming` kwenye `DocumentRagRequest`
3. Ongeza sehemu `chunk` na `end_of_stream` kwenye `DocumentRagResponse`
4. Sasisha Processor ili kushughulikia utiririshaji pamoja na arifa

**Mabadiliko ya Gateway**:

Zote `graph_rag.py` na `document_rag.py` katika gateway/dispatch zinahitaji sasisho ili kusambaza vipande vya utiririshaji hadi kwenye websocket:

```python
async def handle(self, message, session, websocket):
    # ... existing code ...

    if request.streaming:
        async def recipient(resp):
            if resp.chunk:
                await websocket.send(json.dumps({
                    "id": message["id"],
                    "response": {"chunk": resp.chunk},
                    "complete": resp.end_of_stream
                }))
            return resp.end_of_stream

        await self.rag_client.request(request, recipient=recipient)
    else:
        # Existing non-streaming path
        resp = await self.rag_client.request(request)
        await websocket.send(...)
```

### Maelekezo ya Utendaji

**Utaratibu wa utendaji**:
1. Ongeza sehemu za schema (Ombi + Jibu kwa huduma zote za RAG)
2. Sasisha mbinu za GraphRag.query() na DocumentRag.query()
3. Sasisha Wasindikaji ili kushughulikia utiririshaji
4. Sasisha vichakavu vya usambazaji
5. Ongeza `--no-streaming` bendera kwenye `tg-invoke-graph-rag` na `tg-invoke-document-rag` (utiririshaji umeanzishwa kwa chaguizi, kufuatia mtindo wa CLI ya wakala)

**Mfumo wa kurudisha matokeo**:
Fuata mfumo sawa wa kurudisha matokeo wa async uliopo katika utiririshaji wa Wakala:
Wasindikaji hufafanua `async def send_chunk(chunk)` kurudisha matokeo
Hutuma kurudisha matokeo kwa huduma ya RAG
Huduma ya RAG hutuma kurudisha matokeo kwa PromptClient
PromptClient huita kurudisha matokeo kwa kila kipande cha LLM
Wasindikaji hutuma ujumbe wa utiririshaji wa jibu kwa kila kipande

**Usimamizi wa makosa**:
Makosa wakati wa utiririshaji yanapaswa kutuma jibu la makosa na `end_of_stream=True`
Fuata mifumo iliyopo ya usambazaji wa makosa kutoka kwa utiririshaji wa Wakala

## Masuala ya Usalama

Hakuna masuala mapya ya usalama zaidi ya huduma zilizopo za RAG:
Majibu ya utiririshaji hutumia kutengwa sawa kwa mtumiaji/mkusanyiko
Hakuna mabadiliko ya uthibitishaji au idhini
Hifadhi za vipande hazifichui data nyeti

## Masuala ya Utendaji

**Faida**:
Kupunguza latensi iliyohisiwa (vipande vya kwanza vinakuja haraka)
Uzoefu bora wa mtumiaji kwa majibu marefu
Matumizi ya chini ya kumbukumbu (hakuna haja ya kuhifadhi jibu kamili)

**Masuala yanayoweza kutokea**:
Ujumbe zaidi wa Pulsar kwa majibu ya utiririshaji
CPU kidogo ya juu kwa gharama ya vipande/kurudisha matokeo
Imepunguzwa na: utiririshaji ni chaguo, chaguo-msingi inabaki bila utiririshaji

**Masuala ya upimaji**:
Pima na vielelezo vikubwa vya maarifa (triple nyingi)
Pima na hati nyingi zilizopatikana
Pima gharama ya utiririshaji dhidi ya utiririshaji usio na utiririshaji

## Mkakati wa Upimaji

**Majaribio ya kitengo**:
Pima GraphRag.query() na streaming=True/False
Pima DocumentRag.query() na streaming=True/False
Fanya PromptClient kuwa bandia ili kuhakikisha utendaji wa kurudisha matokeo

**Majaribio ya ujumuu**:
Pima mtiririko kamili wa GraphRAG wa utiririshaji (sawa na majaribio ya sasa ya utiririshaji wa wakala)
Pima mtiririko kamili wa DocumentRAG wa utiririshaji
Pima usambazaji wa utiririshaji wa Gateway
Pima pato la utiririshaji la CLI

**Upimaji wa mwongozo**:
`tg-invoke-graph-rag -q "What is machine learning?"` (utiririshaji kwa chaguizi)
`tg-invoke-document-rag -q "Summarize the documents about AI"` (utiririshaji kwa chaguizi)
`tg-invoke-graph-rag --no-streaming -q "..."` (pima hali ya utiririshaji usio na utiririshaji)
Hakikisha pato linaloongezwa linaonekana katika hali ya utiririshaji

## Mpango wa Uhamisho

Hakuna uhamishaji unaohitajika:
Utiririshaji ni chaguo kupitia parameter ya `streaming` (ina chaguizi kuwa Fele)
Wateja wenyewe wanaendelea kufanya kazi bila mabadiliko
Wateja wapya wanaweza kuchagua utiririshaji

## Muda

Muda uliokadiriwa wa utekelezaji: saa 4-6
Awamu ya 1 (saa 2): Usaidizi wa utiririshaji wa GraphRAG
Awamu ya 2 (saa 2): Usaidizi wa utiririshaji wa DocumentRAG
Awamu ya 3 (saa 1-2): Madaisho ya Gateway na bendera za CLI
Upimaji: Umejumuishwa katika kila awamu

## Maswali yaliyofunguliwa

Je, tunapaswa kuongeza usaidizi wa utiririshaji kwa huduma ya NLP Query pia?
Je, tunataka kuonyesha hatua za kati (k.m., "Kupata vyombo vya habari...", "Kusahihisha grafu...") au tu pato la LLM?
Je, majibu ya GraphRAG/DocumentRAG yanapaswa kujumuisha metadata ya kipande (k.m., nambari ya kipande, jumla inayotarajiwa)?

## Marejeleo

Utekelezaji uliopo: `docs/tech-specs/streaming-llm-responses.md`
Utiririshaji wa Wakala: `trustgraph-flow/trustgraph/agent/react/agent_manager.py`
PromptClient utiririshaji: `trustgraph-base/trustgraph/base/prompt_client.py`
