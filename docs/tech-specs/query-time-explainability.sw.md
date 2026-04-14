---
layout: default
title: "Ufafanuzi wa Wakati wa Uchunguzi"
parent: "Swahili (Beta)"
---

# Ufafanuzi wa Wakati wa Uchunguzi

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Hali

Imetekelezwa

## Muhtasari

Maelekezo haya yanaelezea jinsi GraphRAG inavyorekodi na kuwasilisha data ya ufafanuzi wakati wa utekelezaji wa uchunguzi. Lengo ni ufuatiliaji kamili: kutoka kwa jibu la mwisho, kiasi kupitia miunganisho iliyochaguliwa, hadi kwa nyaraka za asili.

Ufafanuzi wa wakati wa uchunguzi unaeleza kile ambacho mstari wa GraphRAG ulifanya wakati wa utaratibu. Inahusiana na uhifadhi wa wakati wa uchimbaji ambao unarekodi mahali ambapo ukweli wa grafu ya maarifa ulitoka.

## Dhana

| Neno | Ufafanuzi |
|------|------------|
| **Ufafanuzi** | Rekodi ya jinsi matokeo yalivyopatikana |
| **Kipindi** | Utendaji mmoja wa GraphRAG |
| **Uchaguzi wa Miunganisho** | Uchaguzi wa miunganisho inayofaa inayodumishwa na LLM pamoja na utaratibu |
| **Mnyororo wa Uhifadhi** | Njia kutoka kwa miunganisho → kipande → ukurasa → nyaraka |

## Muundo

### Mtiririko wa Ufafanuzi

```
GraphRAG Query
    │
    ├─► Session Activity
    │       └─► Query text, timestamp
    │
    ├─► Retrieval Entity
    │       └─► All edges retrieved from subgraph
    │
    ├─► Selection Entity
    │       └─► Selected edges with LLM reasoning
    │           └─► Each edge links to extraction provenance
    │
    └─► Answer Entity
            └─► Reference to synthesized response (in librarian)
```

### Mfumo wa Hatua Mbili wa GraphRAG

1. **Uchaguzi wa Njia (Edge)**: LLM huangalia njia muhimu kutoka kwenye sehemu ndogo ya grafu, hutoa maelezo kwa kila moja.
2. **Uunganisho (Synthesis)**: LLM huunda jibu kutoka kwa njia zilizochaguliwa pekee.

Tofauti hii inaruhusu uelewaji - tunajua hasa ni njia zipi zilizochangia.

### Uhifadhi

Matriki ya uelewaji yaliyohifadhiwa katika mkusanyiko unaoweza kusanidiwa (kiwango chake: `explainability`)
Hutumia ontolojia ya PROV-O kwa uhusiano wa asili.
Ufafanuzi wa RDF-star kwa marejeleo ya njia.
Yaliyomo ya jibu yamehifadhiwa katika huduma ya "librarian" (hayapo ndani - ni makubwa).

### Uhamishaji wa Muda Halisi

Matukio ya uelewaji huhamishwa kwa mteja wakati swali linapojibiwa:

1. Kipindi kimeanzishwa → tukio limehamishwa
2. Njia zimepatikana → tukio limehamishwa
3. Njia zimechaguliwa pamoja na maelezo → tukio limehamishwa
4. Jibu limeunganishwa → tukio limehamishwa

Mteja hupokea `explain_id` na `explain_collection` ili kupata maelezo kamili.

## Muundo wa URI

URI zote hutumia nafasi ya `urn:trustgraph:` pamoja na UUIDs:

| Kitu | Muundo wa URI |
|--------|-------------|
| Kipindi | `urn:trustgraph:session:{uuid}` |
| Kupata | `urn:trustgraph:prov:retrieval:{uuid}` |
| Uchaguzi | `urn:trustgraph:prov:selection:{uuid}` |
| Jibu | `urn:trustgraph:prov:answer:{uuid}` |
| Uchaguzi wa Njia | `urn:trustgraph:prov:edge:{uuid}:{index}` |

## Mfumo wa RDF (PROV-O)

### Shughuli ya Kipindi

```turtle
<session-uri> a prov:Activity ;
    rdfs:label "GraphRAG query session" ;
    prov:startedAtTime "2024-01-15T10:30:00Z" ;
    tg:query "What was the War on Terror?" .
```

### Kitengo cha Upatikanaji

```turtle
<retrieval-uri> a prov:Entity ;
    rdfs:label "Retrieved edges" ;
    prov:wasGeneratedBy <session-uri> ;
    tg:edgeCount 50 .
```

### Kitengo cha Uchaguzi

```turtle
<selection-uri> a prov:Entity ;
    rdfs:label "Selected edges" ;
    prov:wasDerivedFrom <retrieval-uri> ;
    tg:selectedEdge <edge-sel-0> ;
    tg:selectedEdge <edge-sel-1> .

<edge-sel-0> tg:edge << <s> <p> <o> >> ;
    tg:reasoning "This edge establishes the key relationship..." .
```

### Jibu la Kitu

```turtle
<answer-uri> a prov:Entity ;
    rdfs:label "GraphRAG answer" ;
    prov:wasDerivedFrom <selection-uri> ;
    tg:document <urn:trustgraph:answer:{uuid}> .
```

`tg:document` inarejelea jibu lililohifadhiwa katika huduma ya msimamizi.

## Mara kwa Mara za Nafasi

Zimefafumiwa katika `trustgraph-base/trustgraph/provenance/namespaces.py`:

| Mara kwa Mara | URI |
|----------|-----|
| `TG_QUERY` | `https://trustgraph.ai/ns/query` |
| `TG_EDGE_COUNT` | `https://trustgraph.ai/ns/edgeCount` |
| `TG_SELECTED_EDGE` | `https://trustgraph.ai/ns/selectedEdge` |
| `TG_EDGE` | `https://trustgraph.ai/ns/edge` |
| `TG_REASONING` | `https://trustgraph.ai/ns/reasoning` |
| `TG_CONTENT` | `https://trustgraph.ai/ns/content` |
| `TG_DOCUMENT` | `https://trustgraph.ai/ns/document` |

## Muundo wa GraphRagResponse

```python
@dataclass
class GraphRagResponse:
    error: Error | None = None
    response: str = ""
    end_of_stream: bool = False
    explain_id: str | None = None
    explain_collection: str | None = None
    message_type: str = ""  # "chunk" or "explain"
    end_of_session: bool = False
```

### Aina za Ujumbe

| aina_ya_ujumbe | Madhumuni |
|--------------|---------|
| `chunk` | Nakala ya majibu (ya mtiririko au ya mwisho) |
| `explain` | Tukio la kufafanua na rejea ya IRI |

### Mzunguko wa Kisesheni

1. Ujumbe mwingi wa `explain` (kisesheni, upataji, uchaguzi, jibu)
2. Ujumbe mwingi wa `chunk` (jibu la mtiririko)
3. `chunk` ya mwisho na `end_of_session=True`

## Muundo wa Uchaguzi wa Njia

LLM hurudisha JSONL na njia zilizochaguliwa:

```jsonl
{"id": "edge-hash-1", "reasoning": "This edge shows the key relationship..."}
{"id": "edge-hash-2", "reasoning": "Provides supporting evidence..."}
```

`id` ni hash ya `(labeled_s, labeled_p, labeled_o)` iliyohesabiwa na `edge_id()`.

## Uhifadhi wa URI

### Tatizo

GraphRAG huonyesha lebo zinazoweza kusomwa na binadamu kwa LLM, lakini uelewaji unahitaji URI za asili kwa ajili ya kufuatilia asili.

### Suluhisho

`get_labelgraph()` hurudisha vitu viwili:
`labeled_edges`: Orodha ya `(label_s, label_p, label_o)` kwa ajili ya LLM
`uri_map`: Kamusi inayoeleanisha `edge_id(labels)` → `(uri_s, uri_p, uri_o)`

Wakati wa kuhifadhi data ya uelewaji, URI kutoka `uri_map` hutumiwa.

## Kufuatilia Asili

### Kutoka Kwenye Njia hadi Chanzo

Njia zilizochaguliwa zinaweza kufuatiliwa hadi kwenye hati za asili:

1. Tafuta subgraph inayoyajumuisha: `?subgraph tg:contains <<s p o>>`
2. Fuata mnyororo wa `prov:wasDerivedFrom` hadi kwenye hati ya msingi
3. Kila hatua katika mnyororo: kipande → ukurasa → hati

### Usaidizi wa Triple Zilizotiwa Nukuu wa Cassandra

Huduma ya utafutaji ya Cassandra inasaidia kulinganisha triple zilizotiwa nukuu:

```python
# In get_term_value():
elif term.type == TRIPLE:
    return serialize_triple(term.triple)
```

Hii inawezesha maswali kama vile:
```
?subgraph tg:contains <<http://example.org/s http://example.org/p "value">>
```

## Matumizi ya Kifaa Kikuu (CLI)

```bash
tg-invoke-graph-rag --explainable -q "What was the War on Terror?"
```

### Muundo wa Matokeo

```
[session] urn:trustgraph:session:abc123

[retrieval] urn:trustgraph:prov:retrieval:abc123

[selection] urn:trustgraph:prov:selection:abc123
    Selected 12 edge(s)
      Edge: (Guantanamo, definition, A detention facility...)
        Reason: Directly connects Guantanamo to the War on Terror
        Source: Chunk 1 → Page 2 → Beyond the Vigilant State

[answer] urn:trustgraph:prov:answer:abc123

Based on the provided knowledge statements...
```

### Vipengele

Matukio ya uwazi wa matendo kwa wakati halisi wakati wa swali.
Utatuzi wa lebo kwa vipengele vya pembe kupitia `rdfs:label`
Ufuatiliaji wa mnyororo wa chanzo kupitia `prov:wasDerivedFrom`
Kumbukumbu ya lebo ili kuepuka maswali yanayorudiwa.

## Faili Zilizotumiwa

| Faili | Madhumuni |
|------|---------|
| `trustgraph-base/trustgraph/provenance/uris.py` | Vitu vya kuunda URI |
| `trustgraph-base/trustgraph/provenance/namespaces.py` | Mara kwa mara ya nafasi ya RDF |
| `trustgraph-base/trustgraph/provenance/triples.py` | Vitu vya kuunda triple |
| `trustgraph-base/trustgraph/schema/services/retrieval.py` | Mpango wa GraphRagResponse |
| `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py` | GraphRAG ya msingi na uhifadhi wa URI |
| `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` | Huduma na ujumuishaji wa msimamizi |
| `trustgraph-flow/trustgraph/query/triples/cassandra/service.py` | Usaidizi wa swali la triple lililotiwa nukuu |
| `trustgraph-cli/trustgraph/cli/invoke_graph_rag.py` | CLI na onyesho la uwazi |

## Marejeleo

PROV-O (Ontolojia ya Asili ya W3C): https://www.w3.org/TR/prov-o/
RDF-star: https://w3c.github.io/rdf-star/
Asili ya wakati wa uondoaji: `docs/tech-specs/extraction-time-provenance.md`
