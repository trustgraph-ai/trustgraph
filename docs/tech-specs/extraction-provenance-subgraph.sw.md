---
layout: default
title: "Asili ya Utoaji: Mfumo wa Subgraph"
parent: "Swahili (Beta)"
---

# Asili ya Utoaji: Mfumo wa Subgraph

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Tatizo

<<<<<<< HEAD
Hivi sasa, utoaji wa wakati wa uondoaji huunda uelekezaji kamili kwa kila
triple iliyoundwa: `stmt_uri`, `activity_uri`, na metadata inayohusiana
ya PROV-O kwa kila ukweli wa maarifa.  Kushughulikia sehemu moja
ambayo hutoa uhusiano wa 20 hutoa triples ~220 za utoaji pamoja na
triples ~20 za maarifa - mzigo wa takriban 10:1.

Hii ni ghali (uhifadhi, uwekaji wa indexi, usambazaji) na pia si sahihi
kimaana. Kila sehemu hushughulikiwa na simu moja ya LLM ambayo hutoa
triples zake zote katika mshono mmoja.  Mfumo wa sasa wa kila triple
huficha hili kwa kuunda udanganyifu wa matukio 20 ya uondoaji
huru.

Zaidi ya hayo, vichakavu viwili vya nne vya uondoaji (kg-extract-ontology,
kg-extract-agent) havina utoaji wowote, na hivyo kuacha pengo katika
=======
Hivi sasa, utoaji wa taarifa wakati wa utoaji huunda uelekezaji kamili kwa kila
triple iliyotoa: `stmt_uri`, `activity_uri`, na metadata inayohusiana
ya PROV-O kwa kila ukweli wa maarifa.  Kushughulikia sehemu moja
ambayo hutoa uhusiano wa 20 hutoa triples ~220 za taarifa juu ya
triples ~20 za maarifa - mzigo wa takriban 10:1.

Hii ni ghali (uhifadhi, urekebishaji, usambazaji) na pia si sahihi kimaana.
Kila sehemu hushughulikiwa na simu moja ya LLM ambayo hutoa triples zake zote
katika mshughuliko mmoja.  Mfumo wa sasa wa kila triple huficha hili kwa
kuunda udanganyifu wa matukio 20 ya kujitenga ya utoaji.


Zaidi ya hayo, vichakavu viwili vya utoaji vifo (kg-extract-ontology,
kg-extract-agent) havina taarifa zozote, na hivyo kuacha pengo katika
>>>>>>> 82edf2d (New md files from RunPod)
njia ya ukaguzi.

## Suluhisho

Badilisha uelekezaji wa kila triple na **mfumo wa subgraph**: rekodi moja
<<<<<<< HEAD
ya utoaji kwa kila uondoaji wa sehemu, inayoshirikiwa na triples zote
=======
ya taarifa kwa kila utoaji wa sehemu, inayoshirikiwa na triples zote
>>>>>>> 82edf2d (New md files from RunPod)
zilizozalishwa kutoka sehemu hiyo.

### Mabadiliko ya Dhana

| Zamani | Mpya |
|-----|-----|
| `stmt_uri` (`https://trustgraph.ai/stmt/{uuid}`) | `subgraph_uri` (`https://trustgraph.ai/subgraph/{uuid}`) |
| `statement_uri()` | `subgraph_uri()` |
<<<<<<< HEAD
| `tg:reifies` (1:1, utambulisho) | `tg:contains` (1:wengi, uwezeshaji) |

### Muundo Unaolengwa

Triples zote za utoaji huwekwa katika grafu iliyoitwa `urn:graph:source`.
=======
| `tg:reifies` (1:1, utambulisho) | `tg:contains` (1:wengi, kuingia) |

### Muundo Unaolengwa

Triples zote za taarifa huwekwa katika grafu iliyoitwa `urn:graph:source`.
>>>>>>> 82edf2d (New md files from RunPod)

```
# Subgraph contains each extracted triple (RDF-star quoted triples)
<subgraph> tg:contains <<s1 p1 o1>> .
<subgraph> tg:contains <<s2 p2 o2>> .
<subgraph> tg:contains <<s3 p3 o3>> .

# Derivation from source chunk
<subgraph> prov:wasDerivedFrom <chunk_uri> .
<subgraph> prov:wasGeneratedBy <activity> .

# Activity: one per chunk extraction
<activity> rdf:type          prov:Activity .
<activity> rdfs:label        "{component_name} extraction" .
<activity> prov:used         <chunk_uri> .
<activity> prov:wasAssociatedWith <agent> .
<activity> prov:startedAtTime "2026-03-13T10:00:00Z" .
<activity> tg:componentVersion "0.25.0" .
<activity> tg:llmModel       "gpt-4" .          # if available
<activity> tg:ontology        <ontology_uri> .   # if available

# Agent: stable per component
<agent> rdf:type   prov:Agent .
<agent> rdfs:label "{component_name}" .
```

### Kulinganisha Kiasi

Kwa kila sehemu inayozalisha triples tatu zilizochukuliwa:

| | Zamani (kwa kila triple) | Mpya (subgraph) |
|---|---|---|
| `tg:contains` / `tg:reifies` | N | N |
| Triples za shughuli | ~9 x N | ~9 |
| Triples za wakala | 2 x N | 2 |
| Metadata ya taarifa/subgraph | 2 x N | 2 |
| **Triples tatu za jumla za asili** | **~13N** | **N + 13** |
| **Mfano (N=20)** | **~260** | **33** |

## Upeo

### Wasindikaji ambao Watasasishwa (asili iliyopo, kwa kila triple)

**kg-extract-definitions**
(`trustgraph-flow/trustgraph/extract/kg/definitions/extract.py`)

Hivi sasa huita `statement_uri()` + `triple_provenance_triples()` ndani
ya loop ya kila ufafanuzi.

Mabadiliko:
Hamisha `subgraph_uri()` na `activity_uri()` kabla ya loop
Kusanya triples za `tg:contains` ndani ya loop
Toa kundi la shughuli/wakala/uzalishaji mara moja baada ya loop

**kg-extract-relationships**
(`trustgraph-flow/trustgraph/extract/kg/relationships/extract.py`)

Mfano sawa na ufafanuzi. Mabadiliko sawa.

<<<<<<< HEAD
### Wasindikaji ambao Watasasishwa ili Kuongeza Asili (sasa hayapo)
=======
### Wasindikaji ambao Wataongezwa Asili (sasa hayapo)
>>>>>>> 82edf2d (New md files from RunPod)

**kg-extract-ontology**
(`trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`)

Hivi sasa hutoa triples bila asili. Ongeza asili ya subgraph
kwa kutumia mfano sawa: subgraph moja kwa kila sehemu, `tg:contains` kwa kila
triple iliyochukuliwa.

**kg-extract-agent**
(`trustgraph-flow/trustgraph/extract/kg/agent/extract.py`)

Hivi sasa hutoa triples bila asili. Ongeza asili ya subgraph
kwa kutumia mfano sawa.

<<<<<<< HEAD
### Mabadiliko ya Maktaba ya Asili iliyoshirikiwa
=======
### Mabadiliko ya Maktaba ya Asili Iliyoshirikiwa
>>>>>>> 82edf2d (New md files from RunPod)

**`trustgraph-base/trustgraph/provenance/triples.py`**

Badilisha `triple_provenance_triples()` na `subgraph_provenance_triples()`
Kazi mpya inakubali orodha ya triples zilizochukuliwa badala ya moja
Inazalisha `tg:contains` moja kwa kila triple, kundi la shughuli/wakala lililoshirikiwa
Ondoa `triple_provenance_triples()` ya zamani

**`trustgraph-base/trustgraph/provenance/uris.py`**

Badilisha `statement_uri()` na `subgraph_uri()`

**`trustgraph-base/trustgraph/provenance/namespaces.py`**

Badilisha `TG_REIFIES` na `TG_CONTAINS`

<<<<<<< HEAD
### Hayajajumuishwa katika Upeo
=======
### Hayako Katika Upeo
>>>>>>> 82edf2d (New md files from RunPod)

**kg-extract-topics**: wasindikaji wa mtindo wa zamani, hawatumiki kwa sasa katika
  mtiririko wa kawaida
**kg-extract-rows**: hutoa mistari si triples, mfumo tofauti wa
  asili
**Asili ya wakati wa swali** (`urn:graph:retrieval`): suala tofauti,
  tayari hutumia mfumo tofauti (swali/uchunguzi/lengo/muhtasari)
**Asili ya hati/ukurasa/sehemu** (dekoda ya PDF, kichunguzi): tayari hutumia
  `derived_entity_triples()` ambayo ni kwa kila kitu, si kwa kila triple — hakuna
  suala la ziada

## Maelezo ya Utendaji

### Upangaji Upya wa Loop ya Msindikaji

Kabla (kwa kila triple, katika uhusiano):
```python
for rel in rels:
    # ... build relationship_triple ...
    stmt_uri = statement_uri()
    prov_triples = triple_provenance_triples(
        stmt_uri=stmt_uri,
        extracted_triple=relationship_triple,
        ...
    )
    triples.extend(set_graph(prov_triples, GRAPH_SOURCE))
```

Baada ya (mfumo mdogo):
```python
sg_uri = subgraph_uri()

for rel in rels:
    # ... build relationship_triple ...
    extracted_triples.append(relationship_triple)

prov_triples = subgraph_provenance_triples(
    subgraph_uri=sg_uri,
    extracted_triples=extracted_triples,
    chunk_uri=chunk_uri,
    component_name=default_ident,
    component_version=COMPONENT_VERSION,
    llm_model=llm_model,
    ontology_uri=ontology_uri,
)
triples.extend(set_graph(prov_triples, GRAPH_SOURCE))
```

### Saini Mpya ya Msaidizi

```python
def subgraph_provenance_triples(
    subgraph_uri: str,
    extracted_triples: List[Triple],
    chunk_uri: str,
    component_name: str,
    component_version: str,
    llm_model: Optional[str] = None,
    ontology_uri: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> List[Triple]:
    """
    Build provenance triples for a subgraph of extracted knowledge.

    Creates:
    - tg:contains link for each extracted triple (RDF-star quoted)
    - One prov:wasDerivedFrom link to source chunk
    - One activity with agent metadata
    """
```

### Mabadiliko Makubwa

<<<<<<< HEAD
Hii ni mabadiliko makubwa kwa mfumo wa asili ya data. Asili ya data haijatolewa, kwa hivyo hakuna uhamishaji unaohitajika. Msimbo wa zamani wa ⟦CODE_0⟧ /
=======
Hii ni mabadiliko makubwa kwa mfumo wa uhakikisho. Uhakikisho haujatolewa, kwa hivyo hakuna uhamishaji unaohitajika. Msimbo wa zamani wa ⟦CODE_0⟧ /
>>>>>>> 82edf2d (New md files from RunPod)
`tg:reifies` unaweza kuondolewa kabisa.
Msimbo `statement_uri` unaweza kufutwa kabisa.
