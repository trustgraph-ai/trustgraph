# OpenAPI विनिर्देश - तकनीकी विनिर्देश

## लक्ष्य

ट्रस्टग्राफ REST API गेटवे के लिए एक व्यापक, मॉड्यूलर OpenAPI 3.1 विनिर्देश बनाना जो:
सभी REST एंडपॉइंट्स का दस्तावेजीकरण करता है
मॉड्यूलरिटी और रखरखाव के लिए बाहरी `$ref` का उपयोग करता है
सीधे संदेश अनुवाद कोड से मेल खाता है
सटीक अनुरोध/प्रतिक्रिया स्कीमा प्रदान करता है

## सत्य का स्रोत

API को निम्नलिखित द्वारा परिभाषित किया गया है:
**संदेश अनुवादक**: `trustgraph-base/trustgraph/messaging/translators/*.py`
**डिस्पैचर मैनेजर**: `trustgraph-flow/trustgraph/gateway/dispatch/manager.py`
**एंडपॉइंट मैनेजर**: `trustgraph-flow/trustgraph/gateway/endpoint/manager.py`

## निर्देशिका संरचना

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

## सर्विस मैपिंग

### ग्लोबल सर्विसेज (`/api/v1/{kind}`)
`config` - कॉन्फ़िगरेशन प्रबंधन
`flow` - फ्लो लाइफसाइकिल
`librarian` - दस्तावेज़ लाइब्रेरी
`knowledge` - नॉलेज कोर
`collection-management` - कलेक्शन मेटाडेटा

### फ्लो-होस्टेड सर्विसेज (`/api/v1/flow/{flow}/service/{kind}`)

**अनुरोध/प्रतिक्रिया:**
`agent`, `text-completion`, `prompt`, `mcp-tool`
`graph-rag`, `document-rag`
`embeddings`, `graph-embeddings`, `document-embeddings`
`triples`, `objects`, `nlp-query`, `structured-query`, `structured-diag`

**फायर-एंड-फॉरगेट:**
`text-load`, `document-load`

### इम्पोर्ट/एक्सपोर्ट
`/api/v1/import-core` (POST)
`/api/v1/export-core` (GET)
`/api/v1/flow/{flow}/import/{kind}` (WebSocket)
`/api/v1/flow/{flow}/export/{kind}` (WebSocket)

### अन्य
`/api/v1/socket` (WebSocket मल्टीप्लेक्स)
`/api/metrics` (Prometheus)

## दृष्टिकोण

### चरण 1: सेटअप
1. डायरेक्टरी संरचना बनाएं
2. मुख्य `openapi.yaml` बनाएं जिसमें मेटाडेटा, सर्वर, सुरक्षा शामिल हो
3. पुन: प्रयोज्य घटक बनाएं (त्रुटियां, सामान्य पैरामीटर, सुरक्षा योजनाएं)

### चरण 2: सामान्य स्कीमा
साझा स्कीमा बनाएं जिनका उपयोग सेवाओं में किया जाता है:
`RdfValue`, `Triple` - RDF/ट्रिपल संरचनाएं
`ErrorObject` - त्रुटि प्रतिक्रिया
`DocumentMetadata`, `ProcessingMetadata` - मेटाडेटा संरचनाएं
सामान्य पैरामीटर: `FlowId`, `User`, `Collection`

### चरण 3: ग्लोबल सर्विसेज
प्रत्येक ग्लोबल सर्विस (कॉन्फ़िग, फ्लो, लाइब्रेरियन, नॉलेज, कलेक्शन-मैनेजमेंट) के लिए:
1. `paths/` में पाथ फ़ाइल बनाएं
2. `components/schemas/{service}/` में अनुरोध स्कीमा बनाएं
3. प्रतिक्रिया स्कीमा बनाएं
4. उदाहरण जोड़ें
5. मुख्य `openapi.yaml` से संदर्भ लें

### चरण 4: फ्लो-होस्टेड सर्विसेज
प्रत्येक फ्लो-होस्टेड सर्विस के लिए:
1. `paths/flow-services/` में पाथ फ़ाइल बनाएं
2. `components/schemas/ai-services/` में अनुरोध/प्रतिक्रिया स्कीमा बनाएं
3. जहां लागू हो, स्ट्रीमिंग फ़्लैग दस्तावेज़ जोड़ें
4. मुख्य `openapi.yaml` से संदर्भ लें

### चरण 5: इम्पोर्ट/एक्सपोर्ट और WebSocket
1. मुख्य इम्पोर्ट/एक्सपोर्ट एंडपॉइंट्स का दस्तावेज़ बनाएं
2. WebSocket प्रोटोकॉल पैटर्न का दस्तावेज़ बनाएं
3. फ्लो-लेवल इम्पोर्ट/एक्सपोर्ट WebSocket एंडपॉइंट्स का दस्तावेज़ बनाएं

### चरण 6: सत्यापन
1. OpenAPI सत्यापन उपकरणों के साथ सत्यापित करें
2. Swagger UI के साथ परीक्षण करें
3. सत्यापित करें कि सभी अनुवादक कवर किए गए हैं

## फ़ील्ड नामकरण सम्मेलन

सभी JSON फ़ील्ड **केबाब-केस** का उपयोग करते हैं:
`flow-id`, `blueprint-name`, `doc-limit`, `entity-limit`, आदि।

## स्कीमा फ़ाइलें बनाना

प्रत्येक अनुवादक के लिए `trustgraph-base/trustgraph/messaging/translators/`:

1. **अनुवादक `to_pulsar()` विधि पढ़ें** - अनुरोध स्कीमा को परिभाषित करता है
2. **अनुवादक `from_pulsar()` विधि पढ़ें** - प्रतिक्रिया स्कीमा को परिभाषित करता है
3. **फ़ील्ड नाम और प्रकार निकालें**
4. **OpenAPI स्कीमा बनाएं** जिसमें:
   फ़ील्ड नाम (केबाब-केस)
   प्रकार (स्ट्रिंग, पूर्णांक, बूलियन, ऑब्जेक्ट, सरणी)
   आवश्यक फ़ील्ड
   डिफ़ॉल्ट
   विवरण

### उदाहरण मैपिंग प्रक्रिया

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

अनुवाद:

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

## स्ट्रीमिंग प्रतिक्रियाएं

वे सेवाएं जो स्ट्रीमिंग का समर्थन करती हैं, वे `end_of_stream` ध्वज के साथ कई प्रतिक्रियाएं लौटाती हैं:
`agent`, `text-completion`, `prompt`
`document-rag`, `graph-rag`

इस पैटर्न को प्रत्येक सेवा की प्रतिक्रिया स्कीमा में प्रलेखित करें।

## त्रुटि प्रतिक्रियाएं

सभी सेवाएं निम्नलिखित लौटा सकती हैं:
```yaml
error:
  oneOf:
    - type: string
    - $ref: '#/components/schemas/ErrorObject'
```

जहाँ `ErrorObject` है:
```yaml
type: object
properties:
  type:
    type: string
  message:
    type: string
```

## संदर्भ

अनुवादक: `trustgraph-base/trustgraph/messaging/translators/`
डिस्पैचर मैपिंग: `trustgraph-flow/trustgraph/gateway/dispatch/manager.py`
एंडपॉइंट रूटिंग: `trustgraph-flow/trustgraph/gateway/endpoint/manager.py`
सेवा सारांश: `API_SERVICES_SUMMARY.md`
