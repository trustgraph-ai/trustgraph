**MAELEZO MAZOE:**
- Weka ВИWAMU za muundo, vichungi, viungo na alama za HTML.
- Usitafsiri nakala ndani ya alama za ``` au katika blok za nakala.
- Toa NA TUJUI tu, bila utangulizi au maelezo.

Nakala inayohitajika:
# Mabadiliko ya API Gateway: v1.8 hadi v2.1

## Muhtasari

API gateway imepata mpya wa huduma za WebSocket kwa ajili ya majabuzi, kiungo cha mpya cha REST kwa maudhui, na imepitia mabadiliko muhimu katika muundo wa data kutoka `Value` hadi `Term`. Huduma "objects" imebadilishwa na "rows".

---

## Wengine Wepya wa Huduma za WebSocket

Hizi ni huduma mpya za ombi/majibu zinazopatikana kupitia multiplexer ya WebSocket katika `/api/v1/socket` (na msingi wa "flow"):

| Key ya Huduma | Maelezo |
|-------------|-------------|
| `document-embeddings` | Inatafuta sehemu za hati kwa utofauti wa maandishi. Ombi/majibu hutumia miundo `DocumentEmbeddingsRequest`/`DocumentEmbeddingsResponse`. |
| `row-embeddings` | Inatafuta data iliyoandaliwa kwa utofauti wa maandishi kwenye majina iliyosawazwa. Ombi/majibu hutumia miundo `RowEmbeddingsRequest`/`RowEmbeddingsResponse`. |

Hizi zinaunganishwa na `graph-embeddings` iliyopo tayari katika v1.8, lakini inaweza kuwa imeboreshwa.

### Orodha kamili ya huduma za WebSocket (v2.1)

Huduma za ombi/majibu (kupitia `/api/v1/flow/{flow}/service/{kind}` au WebSocket mux):

- `agent`, `text-completion`, `prompt`, `mcp-tool`
- `graph-rag`, `document-rag`
- `embeddings`, `graph-embeddings`, `document-embeddings`
- `triples`, `rows`, `nlp-query`, `structured-query`, `structured-diag`
- `row-embeddings`

---

## Kiungo cha REST cha Mpya

| Njia | Path | Maelezo |
|--------|------|-------------|
| `GET` | `/api/v1/document-stream` | Inatoa maudhui ya hati kutoka kwenye makala kama data ya msingi. Parametari za ombi: `user` (lazima), `document-id` (lazima), `chunk-size` (bora, chaguo, 1MB). Inarudisha maudhui ya hati kama data iliyobadilishwa, na inatumia teknolojia ya "chunked transfer encoding" ya base64. |

---

## Huduma iliyobadilishwa: "objects" hadi "rows"

| v1.8 | v2.1 | Maelezo |
|------|------|-------|
| `objects_query.py` / `ObjectsQueryRequestor` | `rows_query.py` / `RowsQueryRequestor` | Muundo umebadilishwa kutoka `ObjectsQueryRequest`/`ObjectsQueryResponse` hadi `RowsQueryRequest`/`RowsQueryResponse`. |
| `objects_import.py` / `ObjectsImport` | `rows_import.py` / `RowsImport` | Huduma ya import kwa data iliyoandaliwa. |

Key ya huduma ya WebSocket imebadilishwa kutoka "objects" hadi "rows", na key ya import pia imebadilishwa.

---

## Mabadiliko ya Muundo: Value hadi Term

Sura ya usimamizaji (`serialize.py`) imeandikwa upya ili kutumia aina mpya ya "Term" badala ya aina ya "Value" iliyokuwa.

### Sura ya awali (v1.8 — Value)

```json
{"v": "http://example.org/entity", "e": true}
```

- `v`: thamani (string)
- `e`: bendera ya booleani inayoeleza kama thamani ni URI

### Sura mpya (v2.1 — Term)

IRIs:
```json
{"t": "i", "i": "http://example.org/entity"}
```

Literals:
```json
{"t": "l", "v": "some text", "d": "datatype-uri", "l": "en"}
```

Triple za mlangano (RDF-star):
```json
{"t": "r", "r": {"s": {...}, "p": {...}, "o": {...}}}
```

- `t`: makazi - `"i"` (URI), `"l"` (thamini), `"r"` (triple), `"b"` (blank node)
- Usimamizi sasa unaendeleza kwa `TermTranslator` na `TripleTranslator` kutoka `trustgraph.messaging.translators.primitives`

### Mabadiliko mengine ya usimamizaji

| Kipa | v1.8 | v2.1 |
|-------|------|------|
| Metadata | `metadata.metadata` (subgraph) | `metadata.root` (thamini rahisi) |
| Graph embeddings entity | `entity.vectors` (pl) | `entity.vector` (singular) |
| Document embeddings chunk | `chunk.vectors` + `chunk.chunk` (text) | `chunk.vector` + `chunk.chunk_id` (ID reference) |

---

## Mabadiliko Muhimu

- **Muundo Value hadi Term**: Wote wa wateja wanaotumia nakala, ujumizi, au maudhui wanapaswa kubadilishwa kwa muundo mpya wa Term.
- **"objects" hadi "rows"**: Key ya huduma na key ya import zimebadilishwa.
- **Mabadiliko ya key ya Metadata**: `metadata.metadata` (subgraph iliyosimamizwa) imebadilishwa na `metadata.root` (thamini rahisi).
- **Mabadiliko ya key ya Embeddings**: `vectors` (plural) imebadilishwa na `vector` (singular); ujumizi wa hati sasa inaangalia `chunk_id` badala ya "chunk" ya msingi.
- **Kiungo cha mpya `/api/v1/document-stream`**: Haiathiri.