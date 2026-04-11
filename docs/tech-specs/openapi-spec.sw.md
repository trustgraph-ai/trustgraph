# Maelezo ya Kiufundi ya OpenAPI

## Lengo

Kuunda maelezo kamili na yanayoweza kutenganishwa ya OpenAPI 3.1 kwa lango la API la TrustGraph ambalo:
Yanadhihirisha viungo vyote vya REST
Yanatumia `$ref` ya nje kwa utendaji na uendelevu
Yanalingana moja kwa moja na msimuaji wa ujumbe
Yanatoa muundo sahihi wa ombi/jibu

## Chanzo cha Uhakika

API inafafanuliwa na:
**Wasimamizi wa Tafsiri ya Ujumbe**: `trustgraph-base/trustgraph/messaging/translators/*.py`
**Meneja wa Msambazaji**: `trustgraph-flow/trustgraph/gateway/dispatch/manager.py`
**Meneja wa Kikoa**: `trustgraph-flow/trustgraph/gateway/endpoint/manager.py`

## Muundo wa Saraka

```
openapi/
├── openapi.yaml                          # Main entry point
├── paths/
│   ├── config.yaml                       # Global services
│   ├── flow.yaml
│   ├── librarian.yaml
│   ├── knowledge.yaml
│   ├── collection-management.yaml
│   ├── flow-services/                    # Flow-hosted services
│   │   ├── agent.yaml
│   │   ├── document-rag.yaml
│   │   ├── graph-rag.yaml
│   │   ├── text-completion.yaml
│   │   ├── prompt.yaml
│   │   ├── embeddings.yaml
│   │   ├── mcp-tool.yaml
│   │   ├── triples.yaml
│   │   ├── objects.yaml
│   │   ├── nlp-query.yaml
│   │   ├── structured-query.yaml
│   │   ├── structured-diag.yaml
│   │   ├── graph-embeddings.yaml
│   │   ├── document-embeddings.yaml
│   │   ├── text-load.yaml
│   │   └── document-load.yaml
│   ├── import-export/
│   │   ├── core-import.yaml
│   │   ├── core-export.yaml
│   │   └── flow-import-export.yaml      # WebSocket import/export
│   ├── websocket.yaml
│   └── metrics.yaml
├── components/
│   ├── schemas/
│   │   ├── config/
│   │   ├── flow/
│   │   ├── librarian/
│   │   ├── knowledge/
│   │   ├── collection/
│   │   ├── ai-services/
│   │   ├── common/
│   │   └── errors/
│   ├── parameters/
│   ├── responses/
│   └── examples/
└── security/
    └── bearerAuth.yaml
```

## Huduma za Ulinganishaji

### Huduma za Kimataifa (`/api/v1/{kind}`)
`config` - Usimamizi wa usanidi
`flow` - Mzungano wa mchakato
`librarian` - Maktaba ya nyaraka
`knowledge` - Vituo vya maarifa
`collection-management` - Meta data ya mkusanyiko

### Huduma Zilizowekwa kwenye Mchakato (`/api/v1/flow/{flow}/service/{kind}`)

**Ombi/Jibu:**
`agent`, `text-completion`, `prompt`, `mcp-tool`
`graph-rag`, `document-rag`
`embeddings`, `graph-embeddings`, `document-embeddings`
`triples`, `objects`, `nlp-query`, `structured-query`, `structured-diag`

**Tuma na Usisubiri:**
`text-load`, `document-load`

### Uingizaji/Utoaji
`/api/v1/import-core` (POST)
`/api/v1/export-core` (GET)
`/api/v1/flow/{flow}/import/{kind}` (WebSocket)
`/api/v1/flow/{flow}/export/{kind}` (WebSocket)

### Mengine
`/api/v1/socket` (WebSocket iliyounganishwa)
`/api/metrics` (Prometheus)

## Mbinu

### Awamu ya 1: Uwekaji
1. Unda muundo wa saraka
2. Unda `openapi.yaml` kuu pamoja na metadata, seva, usalama
3. Unda vipengele vinavyoweza kutumika tena (makosa, vigezo vya kawaida, mpango wa usalama)

### Awamu ya 2: Mfumo wa Kawaida
Unda mfumo wa kawaida unaotumika katika huduma:
`RdfValue`, `Triple` - Miundo ya RDF/triple
`ErrorObject` - Jibu la kosa
`DocumentMetadata`, `ProcessingMetadata` - Miundo ya metadata
Vigezo vya kawaida: `FlowId`, `User`, `Collection`

### Awamu ya 3: Huduma za Kimataifa
Kwa kila huduma ya kimataifa (usanidi, mchakato, maktaba, maarifa, usimamizi wa mkusanyiko):
1. Unda faili ya njia katika `paths/`
2. Unda mfumo wa ombi katika `components/schemas/{service}/`
3. Unda mfumo wa jibu
4. Ongeza mifano
5. Rejelea kutoka kwa `openapi.yaml` kuu

### Awamu ya 4: Huduma Zilizowekwa kwenye Mchakato
Kwa kila huduma iliyowekwa kwenye mchakato:
1. Unda faili ya njia katika `paths/flow-services/`
2. Unda mifumo ya ombi/jibu katika `components/schemas/ai-services/`
3. Ongeza maandishi ya bendera ya utiririshaji ambapo inafaa
4. Rejelea kutoka kwa `openapi.yaml` kuu

### Awamu ya 5: Uingizaji/Utoaji & WebSocket
1. Andika kuhusu mwisho wa msingi wa uingizaji/utoaji
2. Andika kuhusu mifumo ya itifaki ya WebSocket
3. Andika kuhusu mwisho wa uingizaji/utoaji wa WebSocket wa kiwango cha mchakato

### Awamu ya 6: Uthibitisho
1. Thibitisha kwa kutumia zana za uthibitisho wa OpenAPI
2. Jaribu kwa kutumia Swagger UI
3. Hakikisha kuwa watumizi wote wamefunikwa

## Mfumo wa Majina ya Nyanja

Nyanja zote za JSON hutumia **kebab-case**:
`flow-id`, `blueprint-name`, `doc-limit`, `entity-limit`, n.k.

## Kuunda Faili za Mfumo

Kwa kila mtumizi katika `trustgraph-base/trustgraph/messaging/translators/`:

1. **Soma njia ya mtumizi `to_pulsar()`** - Inaweka mfumo wa ombi
2. **Soma njia ya mtumizi `from_pulsar()`** - Inaweka mfumo wa jibu
3. **Toa majina na aina za nyanja**
4. **Unda mfumo wa OpenAPI** pamoja na:
   Majina ya nyanja (kebab-case)
   Aina (string, integer, boolean, object, array)
   Nyanja zinazohitajika
   Maagizo
   Maelezo

### Mchakato wa Ulinganishaji wa Kifaa

```python
# From retrieval.py DocumentRagRequestTranslator
def to_pulsar(self, data: Dict[str, Any]) -> DocumentRagQuery:
    return DocumentRagQuery(
        query=data["query"],                              # required string
        user=data.get("user", "trustgraph"),             # optional string, default "trustgraph"
        collection=data.get("collection", "default"),     # optional string, default "default"
        doc_limit=int(data.get("doc-limit", 20)),        # optional integer, default 20
        streaming=data.get("streaming", False)            # optional boolean, default false
    )
```

Inafanana na:

```yaml
# components/schemas/ai-services/DocumentRagRequest.yaml
type: object
required:
  - query
properties:
  query:
    type: string
    description: Search query
  user:
    type: string
    default: trustgraph
  collection:
    type: string
    default: default
  doc-limit:
    type: integer
    default: 20
    description: Maximum number of documents to retrieve
  streaming:
    type: boolean
    default: false
    description: Enable streaming responses
```

## Majibu ya Utiririshaji

Huduma zinazounga mkono utiririshaji hurudisha majibu mengi na bendera `end_of_stream`:
`agent`, `text-completion`, `prompt`
`document-rag`, `graph-rag`

Elezea mfumo huu katika schema ya majibu ya kila huduma.

## Majibu ya Kosa

Huduma zote zinaweza kurudisha:
```yaml
error:
  oneOf:
    - type: string
    - $ref: '#/components/schemas/ErrorObject'
```

Ambako `ErrorObject` iko:
```yaml
type: object
properties:
  type:
    type: string
  message:
    type: string
```

## Marejeleo

Watengenezaji: `trustgraph-base/trustgraph/messaging/translators/`
Ramani ya utumaji: `trustgraph-flow/trustgraph/gateway/dispatch/manager.py`
Uelekezaji wa mwisho: `trustgraph-flow/trustgraph/gateway/endpoint/manager.py`
Muhtasari wa huduma: `API_SERVICES_SUMMARY.md`
