---
layout: default
title: "Mchakato wa Utoaji"
parent: "Swahili (Beta)"
---

# Mchakato wa Utoaji

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

Hati hii inaeleza jinsi data inapita katika mfumo wa utoaji wa TrustGraph, kuanzia utoaji wa hati hadi uhifadhi katika hifadhia za maarifa.

## Muhtasari

```
┌──────────┐     ┌─────────────┐     ┌─────────┐     ┌────────────────────┐
│ Librarian│────▶│ PDF Decoder │────▶│ Chunker │────▶│ Knowledge          │
│          │     │ (PDF only)  │     │         │     │ Extraction         │
│          │────────────────────────▶│         │     │                    │
└──────────┘     └─────────────┘     └─────────┘     └────────────────────┘
                                          │                    │
                                          │                    ├──▶ Triples
                                          │                    ├──▶ Entity Contexts
                                          │                    └──▶ Rows
                                          │
                                          └──▶ Document Embeddings
```

## Hifadhi ya Maudhui

### Uhifadhi wa Data (S3/Minio)

Maudhui ya nyaraka huhifadhiwa katika uhifadhi wa data unaolingana na S3:
Muundo wa njia: `doc/{object_id}` ambapo object_id ni UUID
Aina zote za nyaraka huhifadhiwa hapa: nyaraka za asili, kurasa, sehemu

### Uhifadhi wa MetaData (Cassandra)

MetaData ya nyaraka iliyohifadhiwa katika Cassandra ni pamoja na:
Kitambulisho cha nyaraka, kichwa, aina (aina ya MIME)
Rejea ya `object_id` kwa uhifadhi wa data
`parent_id` kwa nyaraka za watoto (kurasa, sehemu)
`document_type`: "chanzo", "ukurasa", "sehemu", "jibu"

### Kigezo cha Kwanza na la Kuendelea

Usafirishaji wa maudhui hutumia mkakati unaotegemea saizi:
**< 2MB**: Maudhui yajumuishwa ndani ya ujumbe (yamekodishwa kwa base64)
**≥ 2MB**: `document_id` pekee hutumwa; mchakato hupata kupitia API ya msimamizi

## Hatua ya 1: Uwasilishaji wa Nyaraka (Msimamizi)

### Kifaa cha Kuanzia

Nyaraka huingia katika mfumo kupitia operesheni ya `add-document` ya msimamizi:
1. Maudhui yamepakuliwa kwenye uhifadhi wa data
2. Rekodi ya metaData imeundwa katika Cassandra
3. Inarudisha kitambulisho cha nyaraka

### Kuanzisha Utoaji

Operesheni ya `add-processing` inaanzisha utoaji:
Inaonyesha `document_id`, `flow` (kitambulisho cha mnyororo), `collection` (hifadhi inayolengwa)
Msimamizi wa `load_document()` hupata maudhui na huyaweka kwenye folyo ya ingizo

### Muundo: Nyaraka

```
Document
├── metadata: Metadata
│   ├── id: str              # Document identifier
│   ├── user: str            # Tenant/user ID
│   ├── collection: str      # Target collection
│   └── metadata: list[Triple]  # (largely unused, historical)
├── data: bytes              # PDF content (base64, if inline)
└── document_id: str         # Librarian reference (if streaming)
```

**Uelekezaji:** Kulingana na sehemu `kind`:
`application/pdf` → Kundi `document-load` → Kipangishi cha PDF
`text/plain` → Kundi `text-load` → Kipande

## Hatua ya 2: Kipangishi cha PDF

Hubadilisha hati za PDF kuwa kurasa za maandishi.

### Mchakato

1. Pata maudhui (moja kwa moja `data` au kupitia `document_id` kutoka kwa msimamizi)
2. Toa kurasa kwa kutumia PyPDF
3. Kwa kila ukurasa:
   Hifadhi kama hati ndogo kwa msimamizi (`{doc_id}/p{page_num}`)
   Toa matoleo ya asili (ukurasa ulichukuliwa kutoka hati)
   Peleka kwa kipande

### Mpango: TextDocument

```
TextDocument
├── metadata: Metadata
│   ├── id: str              # Page URI (e.g., https://trustgraph.ai/doc/xxx/p1)
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]
├── text: bytes              # Page text content (if inline)
└── document_id: str         # Librarian reference (e.g., "doc123/p1")
```

## Hatua ya 3: Kugawanya maandishi

Hugawanya maandishi katika sehemu ndogo kulingana na ukubwa uliopangwa.

### Vigezo (vielekezi ambavyo vinaweza kusanidiwa)

`chunk_size`: Ukubwa unaolengwa wa sehemu ndogo kwa herufi (kiwango chachilia: 2000)
`chunk_overlap`: Mzunguko kati ya sehemu ndogo (kiwango chachilia: 100)

### Mchakato

1. Pata maudhui ya maandishi (moja kwa moja au kupitia mfumo wa kumbukumbu)
2. Gawanya kwa kutumia mgawaji wa herufi unaojielekeza
3. Kwa kila sehemu ndogo:
   Hifadhi kama hati ndogo katika mfumo wa kumbukumbu (`{parent_id}/c{index}`)
   Toa taarifa za asili (sehemu ndogo ilitokana na ukurasa/hati)
   Peleka kwa vichakavu vya utoaji

### Muundo: Sehemu Ndogo

```
Chunk
├── metadata: Metadata
│   ├── id: str              # Chunk URI
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]
├── chunk: bytes             # Chunk text content
└── document_id: str         # Librarian chunk ID (e.g., "doc123/p1/c3")
```

### Hierarkia ya Kitambulisho cha Hati

Hati za chini huandika urithi wao katika kitambulisho:
Chanzo: `doc123`
Ukurasa: `doc123/p5`
Sehemu kutoka ukurasa: `doc123/p5/c2`
Sehemu kutoka maandishi: `doc123/c2`

## Hatua ya 4: Utokaji wa Maarifa

Mfumo mbalimbali wa utokaji unapatikana, unaochaguliwa na usanidi wa mtiririko.

### Mfumo A: Basic GraphRAG

Wasindikaji wawili sambamba:

**kg-extract-definitions**
Ingizo: Sehemu
Patoto: Triples (ufafanuzi wa vitu), EntityContexts
Hutokaje: lebo za vitu, ufafanuzi

**kg-extract-relationships**
Ingizo: Sehemu
Patoto: Triples (uhusiano), EntityContexts
Hutokaje: uhusiano wa subjekti-kivumbe-kijisumu

### Mfumo B: Inayoendeshwa na Ontolojia (kg-extract-ontology)

Ingizo: Sehemu
Patoto: Triples, EntityContexts
Hutumia ontolojia iliyosanidiwa ili kuongoza utokaji

### Mfumo C: Inayoendeshwa na Wakala (kg-extract-agent)

Ingizo: Sehemu
Patoto: Triples, EntityContexts
Hutumia mfumo wa wakala kwa utokaji

### Mfumo D: Utokaji wa Mistari (kg-extract-rows)

Ingizo: Sehemu
Patoto: Mistari (data iliyopangwa, si triples)
Hutumia ufafanuzi wa schema ili kutokaje rekodi zilizopangwa

### Schema: Triples

```
Triples
├── metadata: Metadata
│   ├── id: str
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]  # (set to [] by extractors)
└── triples: list[Triple]
    └── Triple
        ├── s: Term              # Subject
        ├── p: Term              # Predicate
        ├── o: Term              # Object
        └── g: str | None        # Named graph
```

### Mfumo: EntityContexts

```
EntityContexts
├── metadata: Metadata
└── entities: list[EntityContext]
    └── EntityContext
        ├── entity: Term         # Entity identifier (IRI)
        ├── context: str         # Textual description for embedding
        └── chunk_id: str        # Source chunk ID (provenance)
```

### Mfumo: Safu

```
Rows
├── metadata: Metadata
├── row_schema: RowSchema
│   ├── name: str
│   ├── description: str
│   └── fields: list[Field]
└── rows: list[dict[str, str]]   # Extracted records
```

## Hatua ya 5: Uzalishaji wa Uelekezo (Embeddings)

### Uelekezo wa Grafu

Hubadilisha muktadha wa vitu katika uelekezo wa vector.

**Mchakato:**
1. Pokea Muktadha wa Vitu (EntityContexts)
2. Piga simu kwa huduma ya uelekezo (embeddings) kwa kutumia maandishi ya muktadha
3. Toa Uelekezo wa Grafu (ramani ya kitu hadi vector)

**Muundo: Uelekezo wa Grafu (GraphEmbeddings)**

```
GraphEmbeddings
├── metadata: Metadata
└── entities: list[EntityEmbeddings]
    └── EntityEmbeddings
        ├── entity: Term         # Entity identifier
        ├── vector: list[float]  # Embedding vector
        └── chunk_id: str        # Source chunk (provenance)
```

### Uelekezaji wa Hati

Hubadilisha maandishi ya sehemu moja moja kwa uelekezaji wa vector.

**Mchakato:**
1. Pokea Sehemu
2. Piga simu kwa huduma ya uelekezaji kwa kutumia maandishi ya sehemu
3. Toa Uelekezaji wa Hati

**Muundo: Uelekezaji wa Hati**

```
DocumentEmbeddings
├── metadata: Metadata
└── chunks: list[ChunkEmbeddings]
    └── ChunkEmbeddings
        ├── chunk_id: str        # Chunk identifier
        └── vector: list[float]  # Embedding vector
```

### Ulinganisho wa Safu

Hubadilisha nambari za safu kuwa ulinganisho wa vekta.

**Mchakato:**
1. Pokea Safu
2. Linganisha nambari zilizoelezwa za safu
3. Toa kwenye hifadhi ya vekta ya safu

## Hatua ya 6: Uhifadhi

### Hifadhi ya Triple

Inapokea: Triples
Uhifadhi: Cassandra (meza zenye msingi wa vitu)
Picha zilizoainishwa zinatenganisha maarifa ya msingi kutoka kwa asili:
  `""` (ya kawaida): Ukweli wa maarifa ya msingi
  `urn:graph:source`: Asili ya uondoaji
  `urn:graph:retrieval`: Uwezekano wa kufafanua wakati wa kuuliza

### Hifadhi ya Vektaja (Ulinganisho wa Picha)

Inapokea: Ulinganisho wa Picha
Uhifadhi: Qdrant, Milvus, au Pinecone
Imeorodheshwa kwa: IRI ya kitu
Meta: chunk_id kwa asili

### Hifadhi ya Vektaja (Ulinganisho wa Nyaraka)

Inapokea: Ulinganisho wa Nyaraka
Uhifadhi: Qdrant, Milvus, au Pinecone
Imeorodheshwa kwa: chunk_id

### Hifadhi ya Safu

Inapokea: Safu
Uhifadhi: Cassandra
Muundo wa meza unaoongozwa na schema

### Hifadhi ya Vektaja ya Safu

Inapokea: Ulinganisho wa safu
Uhifadhi: Hifadhi ya Vektaja
Imeorodheshwa kwa: nambari za safu

## Uchunguzi wa Uwanja wa Meta

### Uwanja Unaotumika Kwa Kazi

| Uwanja | Matumizi |
|-------|-------|
| `metadata.id` | Kitambulisho cha nyaraka/kipande, uandishi wa matukio, asili |
| `metadata.user` | Usimamizi wa wateja wengi, uelekezaji wa uhifadhi |
| `metadata.collection` | Uchaguzi wa mkusanyiko unaolengwa |
| `document_id` | Rejea ya mkusanyaji, kuunganisha asili |
| `chunk_id` | Kufuatilia asili kupitia mnyororo |

<<<<<<< HEAD
### Uwanja Unaowezekana kuwa Ziada

| Uwanja | Hali |
|-------|--------|
| `metadata.metadata` | Imepangwa kama `[]` na vichujio vyote; meta ya kiwango cha nyaraka sasa inashughulikiwa na mkusanyaji wakati wa kuwasilisha |
=======
### Uwanja Ulioondolewa

| Uwanja | Hali |
|-------|--------|
| `metadata.metadata` | Imeondolewa kutoka kwa darasa la `Metadata`. Triples za meta ya kiwango cha nyaraka sasa hutolewa moja kwa moja na mkusanyaji kwenye hifadhi ya triples wakati wa kuwasilisha, sio kuletwa kupitia mnyororo wa uondoaji. |
>>>>>>> e3bcbf73 (Uwanja wa meta (orodha ya triples) katika darasa la Mnyororo wa Meta)

### Mfumo wa Uwanja wa Bytes

Uwanja wote wa yaliyomo (`data`, `text`, `chunk`) ni `bytes` lakini huondolewa mara moja kuwa maandishi ya UTF-8 na vichujio vyote. Hakuna kichujio kinachotumia bytes mbichi.

## Usanidi wa Mnyororo

Mnyororo huainishwa nje na hutolewa kwa mkusanyaji kupitia huduma ya usanidi. Kila mnyororo unaonyesha:

Ndege za ingizo (`text-load`, `document-load`)
Mnyororo wa vichujio
Vigezo (ukubwa wa kipande, njia ya uondoaji, n.k.)

Mifano ya mnyororo:
`pdf-graphrag`: PDF → Dekoda → Kipande → Maelezo + Mahusiano → Ulinganisho
`text-graphrag`: Nakshata → Kipande → Maelezo + Mahusiano → Ulinganisho
`pdf-ontology`: PDF → Dekoda → Kipande → Uondoaji wa Ontolojia → Ulinganisho
`text-rows`: Nakshata → Kipande → Uondoaji wa Safu → Hifadhi ya Safu
