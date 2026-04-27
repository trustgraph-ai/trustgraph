---
layout: default
title: "ट्रस्टग्राफ पायथन एपीआई संदर्भ"
parent: "Hindi (Beta)"
---

# ट्रस्टग्राफ पायथन एपीआई संदर्भ

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## स्थापना

```bash
pip install trustgraph
```

## त्वरित शुरुआत

सभी कक्षाएं और प्रकार `trustgraph.api` पैकेज से आयात किए गए हैं:

```python
from trustgraph.api import Api, Triple, ConfigKey

# Create API client
api = Api(url="http://localhost:8088/")

# Get a flow instance
flow = api.flow().id("default")

# Execute a graph RAG query
response = flow.graph_rag(
    query="What are the main topics?",
    user="trustgraph",
    collection="default"
)
```

## सामग्री तालिका

### मुख्य भाग

[Api](#api)

### फ्लो क्लाइंट

[Flow](#flow)
[FlowInstance](#flowinstance)
[AsyncFlow](#asyncflow)
[AsyncFlowInstance](#asyncflowinstance)

### वेबसॉकेट क्लाइंट

[SocketClient](#socketclient)
[SocketFlowInstance](#socketflowinstance)
[AsyncSocketClient](#asyncsocketclient)
[AsyncSocketFlowInstance](#asyncsocketflowinstance)

### बल्क ऑपरेशन

[BulkClient](#bulkclient)
[AsyncBulkClient](#asyncbulkclient)

### मेट्रिक्स

[Metrics](#metrics)
[AsyncMetrics](#asyncmetrics)

### डेटा प्रकार

[Triple](#triple)
[ConfigKey](#configkey)
[ConfigValue](#configvalue)
[DocumentMetadata](#documentmetadata)
[ProcessingMetadata](#processingmetadata)
[CollectionMetadata](#collectionmetadata)
[StreamingChunk](#streamingchunk)
[AgentThought](#agentthought)
[AgentObservation](#agentobservation)
[AgentAnswer](#agentanswer)
[RAGChunk](#ragchunk)

### अपवाद

[ProtocolException](#protocolexception)
[TrustGraphException](#trustgraphexception)
[AgentError](#agenterror)
[ConfigError](#configerror)
[DocumentRagError](#documentragerror)
[FlowError](#flowerror)
[GatewayError](#gatewayerror)
[GraphRagError](#graphragerror)
[LLMError](#llmerror)
[LoadError](#loaderror)
[LookupError](#lookuperror)
[NLPQueryError](#nlpqueryerror)
[RowsQueryError](#rowsqueryerror)
[RequestError](#requesterror)
[StructuredQueryError](#structuredqueryerror)
[UnexpectedError](#unexpectederror)
[ApplicationException](#applicationexception)

--

## `Api`

```python
from trustgraph.api import Api
```

सिंक्रोनस और एसिंक्रोनस कार्यों के लिए मुख्य ट्रस्टग्राफ एपीआई क्लाइंट।

यह क्लास सभी ट्रस्टग्राफ सेवाओं तक पहुंच प्रदान करती है, जिसमें फ्लो प्रबंधन,
नॉलेज ग्राफ ऑपरेशन, दस्तावेज़ प्रसंस्करण, आरएजी क्वेरी और बहुत कुछ शामिल हैं। यह
रेस्ट-आधारित और वेबसॉकेट-आधारित दोनों संचार पैटर्न का समर्थन करता है।

क्लाइंट का उपयोग स्वचालित संसाधन सफाई के लिए एक संदर्भ प्रबंधक के रूप में किया जा सकता है:
    ```python
    with Api(url="http://localhost:8088/") as api:
        result = api.flow().id("default").graph_rag(query="test")
    ```

### विधियाँ

### `__aenter__(self)`

एसिंक्रोनस संदर्भ प्रबंधक में प्रवेश करें।

### `__aexit__(self, *args)`

एसिंक्रोनस संदर्भ प्रबंधक से बाहर निकलें और कनेक्शन बंद करें।

### `__enter__(self)`

सिंक्रोनस संदर्भ प्रबंधक में प्रवेश करें।

### `__exit__(self, *args)`

सिंक्रोनस संदर्भ प्रबंधक से बाहर निकलें और कनेक्शन बंद करें।

### `__init__(self, url='http://localhost:8088/', timeout=60, token: str | None = None)`

ट्रस्टग्राफ एपीआई क्लाइंट को आरंभ करें।

**तर्क:**

`url`: ट्रस्टग्राफ एपीआई के लिए आधार यूआरएल (डिफ़ॉल्ट: "http://localhost:8088/"")
`timeout`: सेकंड में अनुरोध समय-सीमा (डिफ़ॉल्ट: 60)
`token`: प्रमाणीकरण के लिए वैकल्पिक बेयरर टोकन

**उदाहरण:**

```python
# Local development
api = Api()

# Production with authentication
api = Api(
    url="https://trustgraph.example.com/",
    timeout=120,
    token="your-api-token"
)
```

### `aclose(self)`

सभी एसिंक्रोनस क्लाइंट कनेक्शन बंद करें।

यह विधि एसिंक्रोनस वेबसॉकेट, बल्क ऑपरेशन और फ्लो कनेक्शन को बंद करती है।
यह स्वचालित रूप से तब कॉल किया जाता है जब किसी एसिंक्रोनस कॉन्टेक्स्ट मैनेजर से बाहर निकलते हैं।

**उदाहरण:**

```python
api = Api()
async_socket = api.async_socket()
# ... use async_socket
await api.aclose()  # Clean up connections

# Or use async context manager (automatic cleanup)
async with Api() as api:
    async_socket = api.async_socket()
    # ... use async_socket
# Automatically closed
```

### `async_bulk(self)`

एसिंक्रोनस बल्क ऑपरेशंस क्लाइंट प्राप्त करें।

वेबसॉकेट के माध्यम से एसिंक्रोनस/अवेइट शैली के बल्क इम्पोर्ट/एक्सपोर्ट ऑपरेशंस प्रदान करता है
बड़े डेटासेट के कुशल प्रबंधन के लिए।

**रिटर्न:** AsyncBulkClient: एसिंक्रोनस बल्क ऑपरेशंस क्लाइंट

**उदाहरण:**

```python
async_bulk = api.async_bulk()

# Export triples asynchronously
async for triple in async_bulk.export_triples(flow="default"):
    print(f"{triple.s} {triple.p} {triple.o}")

# Import with async generator
async def triple_gen():
    yield Triple(s="subj", p="pred", o="obj")
    # ... more triples

await async_bulk.import_triples(
    flow="default",
    triples=triple_gen()
)
```

### `async_flow(self)`

एक एसिंक्रोनस, REST-आधारित फ्लो क्लाइंट प्राप्त करें।

यह फ्लो ऑपरेशन्स तक एसिंक्रोनस/अवेइट शैली में एक्सेस प्रदान करता है। यह एसिंक्रोनस पायथन एप्लिकेशन और फ्रेमवर्क (फास्टएपीआई, एआईओएचटीटीपी, आदि) के लिए पसंदीदा है।


**रिटर्न:** AsyncFlow: एसिंक्रोनस फ्लो क्लाइंट

**उदाहरण:**

```python
async_flow = api.async_flow()

# List flows
flow_ids = await async_flow.list()

# Execute operations
instance = async_flow.id("default")
result = await instance.text_completion(
    system="You are helpful",
    prompt="Hello"
)
```

### `async_metrics(self)`

एक एसिंक्रोनस मेट्रिक्स क्लाइंट प्राप्त करें।

प्रोमेथियस मेट्रिक्स तक एसिंक्रोनस/अवेइट शैली में पहुँच प्रदान करता है।

**वापसी:** AsyncMetrics: एसिंक्रोनस मेट्रिक्स क्लाइंट

**उदाहरण:**

```python
async_metrics = api.async_metrics()
prometheus_text = await async_metrics.get()
print(prometheus_text)
```

### `async_socket(self)`

स्ट्रीमिंग कार्यों के लिए एक एसिंक्रोनस वेबसॉकेट क्लाइंट प्राप्त करें।

यह स्ट्रीमिंग समर्थन के साथ एसिंक/अवेट शैली वेबसॉकेट एक्सेस प्रदान करता है।
यह पायथन में एसिंक स्ट्रीमिंग के लिए पसंदीदा तरीका है।

**रिटर्न:** AsyncSocketClient: एसिंक्रोनस वेबसॉकेट क्लाइंट

**उदाहरण:**

```python
async_socket = api.async_socket()
flow = async_socket.flow("default")

# Stream agent responses
async for chunk in flow.agent(
    question="Explain quantum computing",
    user="trustgraph",
    streaming=True
):
    if hasattr(chunk, 'content'):
        print(chunk.content, end='', flush=True)
```

### `bulk(self)`

आयात/निर्यात के लिए एक सिंक्रोनस बल्क ऑपरेशंस क्लाइंट प्राप्त करें।

बल्क ऑपरेशंस, वेबसॉकेट कनेक्शन के माध्यम से बड़े डेटासेट के कुशल हस्तांतरण की अनुमति देते हैं, जिसमें ट्रिपल, एम्बेडिंग, एंटिटी कॉन्टेक्स्ट और ऑब्जेक्ट शामिल हैं।

**रिटर्न:** BulkClient: सिंक्रोनस बल्क ऑपरेशंस क्लाइंट

**उदाहरण:**


```python
bulk = api.bulk()

# Export triples
for triple in bulk.export_triples(flow="default"):
    print(f"{triple.s} {triple.p} {triple.o}")

# Import triples
def triple_generator():
    yield Triple(s="subj", p="pred", o="obj")
    # ... more triples

bulk.import_triples(flow="default", triples=triple_generator())
```

### `close(self)`

सभी सिंक्रोनस क्लाइंट कनेक्शन बंद करें।

यह विधि WebSocket और बल्क ऑपरेशन कनेक्शन बंद करती है।
यह स्वचालित रूप से तब कॉल किया जाता है जब किसी कॉन्टेक्स्ट मैनेजर से बाहर निकलते हैं।

**उदाहरण:**

```python
api = Api()
socket = api.socket()
# ... use socket
api.close()  # Clean up connections

# Or use context manager (automatic cleanup)
with Api() as api:
    socket = api.socket()
    # ... use socket
# Automatically closed
```

### `collection(self)`

डेटा संग्रहों को प्रबंधित करने के लिए एक कलेक्शन क्लाइंट प्राप्त करें।

कलेक्शन दस्तावेजों और नॉलेज ग्राफ डेटा को व्यवस्थित करते हैं
तार्किक समूहों में, अलगाव और एक्सेस नियंत्रण के लिए।

**रिटर्न:** कलेक्शन: कलेक्शन प्रबंधन क्लाइंट

**उदाहरण:**

```python
collection = api.collection()

# List collections
colls = collection.list_collections(user="trustgraph")

# Update collection metadata
collection.update_collection(
    user="trustgraph",
    collection="default",
    name="Default Collection",
    description="Main data collection"
)
```

### `config(self)`

कॉन्फ़िगरेशन सेटिंग्स को प्रबंधित करने के लिए एक कॉन्फ़िग क्लाइंट प्राप्त करें।

**रिटर्न:** कॉन्फ़िग: कॉन्फ़िगरेशन प्रबंधन क्लाइंट

**उदाहरण:**

```python
config = api.config()

# Get configuration values
values = config.get([ConfigKey(type="llm", key="model")])

# Set configuration
config.put([ConfigValue(type="llm", key="model", value="gpt-4")])
```

### `flow(self)`

फ्लो को प्रबंधित करने और उसके साथ इंटरैक्ट करने के लिए एक फ्लो क्लाइंट प्राप्त करें।

फ्लो, ट्रस्टग्राफ में प्राथमिक निष्पादन इकाइयाँ हैं, जो एजेंट, आरएजी क्वेरी, एम्बेडिंग और दस्तावेज़ प्रसंस्करण जैसी सेवाओं तक पहुंच प्रदान करती हैं।

**रिटर्न:** फ्लो: फ्लो प्रबंधन क्लाइंट

**उदाहरण:**


```python
flow_client = api.flow()

# List available blueprints
blueprints = flow_client.list_blueprints()

# Get a specific flow instance
flow_instance = flow_client.id("default")
response = flow_instance.text_completion(
    system="You are helpful",
    prompt="Hello"
)
```

### `knowledge(self)`

ज्ञान ग्राफ कोर को प्रबंधित करने के लिए एक नॉलेज क्लाइंट प्राप्त करें।

**रिटर्न:** नॉलेज: ज्ञान ग्राफ प्रबंधन क्लाइंट

**उदाहरण:**

```python
knowledge = api.knowledge()

# List available KG cores
cores = knowledge.list_kg_cores(user="trustgraph")

# Load a KG core
knowledge.load_kg_core(id="core-123", user="trustgraph")
```

### `library(self)`

दस्तावेज़ प्रबंधन के लिए एक लाइब्रेरी क्लाइंट प्राप्त करें।

यह लाइब्रेरी दस्तावेज़ भंडारण, मेटाडेटा प्रबंधन और
प्रसंस्करण कार्यप्रवाह समन्वय प्रदान करती है।

**रिटर्न:** लाइब्रेरी: दस्तावेज़ लाइब्रेरी प्रबंधन क्लाइंट

**उदाहरण:**

```python
library = api.library()

# Add a document
library.add_document(
    document=b"Document content",
    id="doc-123",
    metadata=[],
    user="trustgraph",
    title="My Document",
    comments="Test document"
)

# List documents
docs = library.get_documents(user="trustgraph")
```

### `metrics(self)`

निगरानी के लिए एक सिंक्रोनस मेट्रिक्स क्लाइंट प्राप्त करें।

यह ट्रस्टग्राफ सेवा से प्रोमेथियस-स्वरूपित मेट्रिक्स प्राप्त करता है
निगरानी और अवलोकन के लिए।

**रिटर्न:** मेट्रिक्स: सिंक्रोनस मेट्रिक्स क्लाइंट

**उदाहरण:**

```python
metrics = api.metrics()
prometheus_text = metrics.get()
print(prometheus_text)
```

### `request(self, path, request)`

एक निम्न-स्तरीय REST API अनुरोध करें।

यह विधि मुख्य रूप से आंतरिक उपयोग के लिए है, लेकिन जब आवश्यक हो तो इसका उपयोग सीधे
API एक्सेस के लिए किया जा सकता है।

**तर्क:**

`path`: API एंडपॉइंट पथ (बेस URL के सापेक्ष)
`request`: अनुरोध पेलोड एक डिक्शनरी के रूप में

**रिटर्न:** dict: प्रतिक्रिया ऑब्जेक्ट

**अपवाद:**

`ProtocolException`: यदि प्रतिक्रिया स्थिति 200 नहीं है या प्रतिक्रिया JSON नहीं है
`ApplicationException`: यदि प्रतिक्रिया में कोई त्रुटि है

**उदाहरण:**

```python
response = api.request("flow", {
    "operation": "list-flows"
})
```

### `socket(self)`

स्ट्रीमिंग कार्यों के लिए एक सिंक्रोनस वेबसॉकेट क्लाइंट प्राप्त करें।

वेबसॉकेट कनेक्शन वास्तविक समय प्रतिक्रियाओं के लिए स्ट्रीमिंग समर्थन प्रदान करते हैं
एजेंटों, आरएजी प्रश्नों और टेक्स्ट पूर्णता से। यह विधि वेबसॉकेट प्रोटोकॉल के चारों ओर एक सिंक्रोनस रैपर लौटाती है।


**रिटर्न:** SocketClient: सिंक्रोनस वेबसॉकेट क्लाइंट

**उदाहरण:**

```python
socket = api.socket()
flow = socket.flow("default")

# Stream agent responses
for chunk in flow.agent(
    question="Explain quantum computing",
    user="trustgraph",
    streaming=True
):
    if hasattr(chunk, 'content'):
        print(chunk.content, end='', flush=True)
```


--

## `Flow`

```python
from trustgraph.api import Flow
```

ब्लूप्रिंट और फ्लो इंस्टेंस ऑपरेशन्स के लिए फ्लो मैनेजमेंट क्लाइंट।

यह क्लास फ्लो ब्लूप्रिंट (टेम्प्लेट) और
फ्लो इंस्टेंस (चल रहे फ्लो) को प्रबंधित करने के लिए विधियाँ प्रदान करती है। ब्लूप्रिंट फ्लो की संरचना और
पैरामीटर को परिभाषित करते हैं, जबकि इंस्टेंस सक्रिय फ्लो का प्रतिनिधित्व करते हैं जो
सेवाओं को निष्पादित कर सकते हैं।

### विधियाँ

### `__init__(self, api)`

फ्लो क्लाइंट को इनिशियलाइज़ करें।

**तर्क:**

`api`: अनुरोध करने के लिए पैरेंट एपीआई इंस्टेंस।

### `delete_blueprint(self, blueprint_name)`

एक फ्लो ब्लूप्रिंट को हटाएं।

**तर्क:**

`blueprint_name`: हटाने के लिए ब्लूप्रिंट का नाम।

**उदाहरण:**

```python
api.flow().delete_blueprint("old-blueprint")
```

### `get(self, id)`

एक चल रहे फ्लो इंस्टेंस की परिभाषा प्राप्त करें।

**तर्क:**

`id`: फ्लो इंस्टेंस आईडी

**वापसी:** डिक्ट: फ्लो इंस्टेंस परिभाषा

**उदाहरण:**

```python
flow_def = api.flow().get("default")
print(flow_def)
```

### `get_blueprint(self, blueprint_name)`

नाम से एक फ्लो ब्लूप्रिंट परिभाषा प्राप्त करें।

**तर्क:**

`blueprint_name`: प्राप्त करने के लिए ब्लूप्रिंट का नाम

**वापसी:** dict: ब्लूप्रिंट परिभाषा एक शब्दकोश के रूप में

**उदाहरण:**

```python
blueprint = api.flow().get_blueprint("default")
print(blueprint)  # Blueprint configuration
```

### `id(self, id='default')`

किसी विशिष्ट प्रवाह पर संचालन निष्पादित करने के लिए एक फ्लोइंस्टेंस प्राप्त करें।

**तर्क:**

`id`: प्रवाह पहचानकर्ता (डिफ़ॉल्ट: "default")

**वापसी:** फ्लोइंस्टेंस: सेवा संचालन के लिए फ्लो इंस्टेंस

**उदाहरण:**

```python
flow = api.flow().id("my-flow")
response = flow.text_completion(
    system="You are helpful",
    prompt="Hello"
)
```

### `list(self)`

सभी सक्रिय फ्लो इंस्टेंस की सूची बनाएं।

**रिटर्न:** list[str]: फ्लो इंस्टेंस आईडी की सूची

**उदाहरण:**

```python
flows = api.flow().list()
print(flows)  # ['default', 'flow-1', 'flow-2', ...]
```

### `list_blueprints(self)`

उपलब्ध सभी फ्लो ब्लूप्रिंट की सूची बनाएं।

**रिटर्न:** list[str]: ब्लूप्रिंट नामों की सूची

**उदाहरण:**

```python
blueprints = api.flow().list_blueprints()
print(blueprints)  # ['default', 'custom-flow', ...]
```

### `put_blueprint(self, blueprint_name, definition)`

एक फ्लो ब्लूप्रिंट बनाएं या अपडेट करें।

**तर्क:**

`blueprint_name`: ब्लूप्रिंट के लिए नाम
`definition`: ब्लूप्रिंट परिभाषा डिक्शनरी

**उदाहरण:**

```python
definition = {
    "services": ["text-completion", "graph-rag"],
    "parameters": {"model": "gpt-4"}
}
api.flow().put_blueprint("my-blueprint", definition)
```

### `request(self, path=None, request=None)`

एक फ्लो-स्कोपेड एपीआई अनुरोध करें।

**तर्क:**

`path`: फ्लो एंडपॉइंट्स के लिए वैकल्पिक पथ प्रत्यय
`request`: अनुरोध पेलोड डिक्शनरी

**रिटर्न:** डिक्ट: प्रतिक्रिया ऑब्जेक्ट

**अपवाद:**

`RuntimeError`: यदि अनुरोध पैरामीटर निर्दिष्ट नहीं है

### `start(self, blueprint_name, id, description, parameters=None)`

एक ब्लूप्रिंट से एक नया फ्लो इंस्टेंस शुरू करें।

**तर्क:**

`blueprint_name`: इंस्टेंट करने के लिए ब्लूप्रिंट का नाम
`id`: फ्लो इंस्टेंस के लिए अद्वितीय पहचानकर्ता
`description`: मानव-पठनीय विवरण
`parameters`: वैकल्पिक पैरामीटर डिक्शनरी

**उदाहरण:**

```python
api.flow().start(
    blueprint_name="default",
    id="my-flow",
    description="My custom flow",
    parameters={"model": "gpt-4"}
)
```

### `stop(self, id)`

एक चल रहे फ्लो इंस्टेंस को रोकें।

**तर्क:**

`id`: रोकने के लिए फ्लो इंस्टेंस आईडी

**उदाहरण:**

```python
api.flow().stop("my-flow")
```


--

## `FlowInstance`

```python
from trustgraph.api import FlowInstance
```

किसी विशिष्ट प्रवाह पर सेवाओं को निष्पादित करने के लिए फ्लो इंस्टेंस क्लाइंट।

यह क्लास सभी ट्रस्टग्राफ सेवाओं तक पहुंच प्रदान करता है, जिनमें शामिल हैं:
टेक्स्ट पूर्णता और एम्बेडिंग
राज्य प्रबंधन के साथ एजेंट ऑपरेशन
ग्राफ और दस्तावेज़ RAG क्वेरी
नॉलेज ग्राफ ऑपरेशन (ट्रिपल्स, ऑब्जेक्ट)
दस्तावेज़ लोडिंग और प्रोसेसिंग
प्राकृतिक भाषा से GraphQL क्वेरी रूपांतरण
संरचित डेटा विश्लेषण और स्कीमा डिटेक्शन
MCP टूल निष्पादन
प्रॉम्प्ट टेम्पलेटिंग

सेवाओं को एक चल रहे फ्लो इंस्टेंस के माध्यम से एक्सेस किया जाता है जिसकी पहचान ID से होती है।

### विधियाँ

### `__init__(self, api, id)`

फ्लोइंस्टेंस को इनिशियलाइज़ करें।

**तर्क:**

`api`: पैरेंट फ्लो क्लाइंट
`id`: फ्लो इंस्टेंस पहचानकर्ता

### `agent(self, question, user='trustgraph', state=None, group=None, history=None)`

तर्क और टूल उपयोग क्षमताओं के साथ एक एजेंट ऑपरेशन निष्पादित करें।

एजेंट बहु-चरणीय तर्क कर सकते हैं, टूल का उपयोग कर सकते हैं और बातचीत में संवादी
स्थिति को बनाए रख सकते हैं। यह एक सिंक्रोनस, नॉन-स्ट्रीमिंग संस्करण है।

**तर्क:**

`question`: उपयोगकर्ता का प्रश्न या निर्देश
`user`: उपयोगकर्ता पहचानकर्ता (डिफ़ॉल्ट: "trustgraph")
`state`: राज्यपूर्ण वार्तालापों के लिए वैकल्पिक राज्य शब्दकोश
`group`: बहु-उपयोगकर्ता संदर्भों के लिए वैकल्पिक समूह पहचानकर्ता
`history`: संदेशों की सूची के रूप में वैकल्पिक वार्तालाप इतिहास

**रिटर्न:** str: एजेंट का अंतिम उत्तर

**उदाहरण:**

```python
flow = api.flow().id("default")

# Simple question
answer = flow.agent(
    question="What is the capital of France?",
    user="trustgraph"
)

# With conversation history
history = [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi! How can I help?"}
]
answer = flow.agent(
    question="Tell me about Paris",
    user="trustgraph",
    history=history
)
```

### `detect_type(self, sample)`

संरचित डेटा नमूने के डेटा प्रकार का पता लगाएं।

**तर्क:**

`sample`: विश्लेषण करने के लिए डेटा नमूना (स्ट्रिंग सामग्री)

**रिटर्न:** detected_type, confidence और वैकल्पिक मेटाडेटा के साथ एक डिक्शनरी।

### `diagnose_data(self, sample, schema_name=None, options=None)`

संयुक्त डेटा निदान करें: प्रकार का पता लगाएं और विवरणिका उत्पन्न करें।

**तर्क:**

`sample`: विश्लेषण करने के लिए डेटा नमूना (स्ट्रिंग सामग्री)
`schema_name`: विवरणिका पीढ़ी के लिए वैकल्पिक लक्ष्य स्कीमा नाम।
`options`: वैकल्पिक पैरामीटर (जैसे, CSV के लिए विभाजक)।

**वापसी:** `detected_type`, `confidence`, `descriptor` और `metadata` के साथ एक डिक्शनरी।

### `document_embeddings_query(self, text, user, collection, limit=10)`

सिमेंटिक समानता का उपयोग करके दस्तावेज़ के टुकड़ों को क्वेरी करें।

वे दस्तावेज़ के टुकड़े खोजें जिनके सामग्री वेक्टर एम्बेडिंग का उपयोग करके इनपुट टेक्स्ट के सिमेंटिक रूप से समान हैं।


**तर्क:**

`text`: सिमेंटिक खोज के लिए क्वेरी टेक्स्ट।
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता।
`collection`: संग्रह पहचानकर्ता।
`limit`: अधिकतम परिणामों की संख्या (डिफ़ॉल्ट: 10)।

**वापसी:** `dict`: क्वेरी परिणाम जिनमें `chunk_id` और `score` वाले टुकड़े शामिल हैं।

**उदाहरण:**

```python
flow = api.flow().id("default")
results = flow.document_embeddings_query(
    text="machine learning algorithms",
    user="trustgraph",
    collection="research-papers",
    limit=5
)
# results contains {"chunks": [{"chunk_id": "doc1/p0/c0", "score": 0.95}, ...]}
```

### `document_rag(self, query, user='trustgraph', collection='default', doc_limit=10)`

दस्तावेज़-आधारित पुनर्प्राप्ति-संवर्धित पीढ़ी (RAG) क्वेरी निष्पादित करें।

दस्तावेज़ RAG प्रासंगिक दस्तावेज़ अंशों को खोजने के लिए वेक्टर एम्बेडिंग का उपयोग करता है,
फिर उन अंशों को संदर्भ के रूप में उपयोग करके एक LLM के साथ एक प्रतिक्रिया उत्पन्न करता है।

**तर्क:**

`query`: प्राकृतिक भाषा क्वेरी
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता (डिफ़ॉल्ट: "ट्रस्टग्राफ")
`collection`: संग्रह पहचानकर्ता (डिफ़ॉल्ट: "डिफ़ॉल्ट")
`doc_limit`: पुनर्प्राप्त किए जाने वाले अधिकतम दस्तावेज़ अंश (डिफ़ॉल्ट: 10)

**रिटर्न:** स्ट्रिंग: दस्तावेज़ संदर्भ को शामिल करने वाली उत्पन्न प्रतिक्रिया

**उदाहरण:**

```python
flow = api.flow().id("default")
response = flow.document_rag(
    query="Summarize the key findings",
    user="trustgraph",
    collection="research-papers",
    doc_limit=5
)
print(response)
```

### `embeddings(self, texts)`

एक या अधिक ग्रंथों के लिए वेक्टर एम्बेडिंग उत्पन्न करें।

ग्रंथों को घने वेक्टर निरूपण में परिवर्तित करता है जो सिमेंटिक
खोज और समानता तुलना के लिए उपयुक्त है।

**तर्क:**

`texts`: एम्बेड करने के लिए इनपुट ग्रंथों की सूची

**रिटर्न:** list[list[list[float]]]: वेक्टर एम्बेडिंग, प्रत्येक इनपुट टेक्स्ट के लिए एक सेट

**उदाहरण:**

```python
flow = api.flow().id("default")
vectors = flow.embeddings(["quantum computing"])
print(f"Embedding dimension: {len(vectors[0][0])}")
```

### `generate_descriptor(self, sample, data_type, schema_name, options=None)`

संरचित डेटा के लिए एक विवरण उत्पन्न करें जो एक विशिष्ट स्कीमा से मेल खाता हो।

**तर्क:**

`sample`: विश्लेषण करने के लिए डेटा नमूना (स्ट्रिंग सामग्री)
`data_type`: डेटा प्रकार (csv, json, xml)
`schema_name`: विवरण पीढ़ी के लिए लक्षित स्कीमा नाम
`options`: वैकल्पिक पैरामीटर (जैसे, CSV के लिए विभाजक)

**रिटर्न:** विवरण और मेटाडेटा के साथ डिक्ट

### `graph_embeddings_query(self, text, user, collection, limit=10)`

सिमेंटिक समानता का उपयोग करके नॉलेज ग्राफ एंटिटीज को क्वेरी करें।

नॉलेज ग्राफ में उन एंटिटीज को खोजें जिनके विवरण इनपुट टेक्स्ट के समान अर्थ वाले हों,
वेक्टर एम्बेडिंग का उपयोग करके।

**तर्क:**

`text`: सिमेंटिक खोज के लिए क्वेरी टेक्स्ट
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता
`collection`: संग्रह पहचानकर्ता
`limit`: अधिकतम परिणामों की संख्या (डिफ़ॉल्ट: 10)

**रिटर्न:** डिक्ट: समान एंटिटीज के साथ क्वेरी परिणाम

**उदाहरण:**

```python
flow = api.flow().id("default")
results = flow.graph_embeddings_query(
    text="physicist who discovered radioactivity",
    user="trustgraph",
    collection="scientists",
    limit=5
)
# results contains {"entities": [{"entity": {...}, "score": 0.95}, ...]}
```

### `graph_rag(self, query, user='trustgraph', collection='default', entity_limit=50, triple_limit=30, max_subgraph_size=150, max_path_length=2)`

ग्राफ-आधारित रिट्रीवल-ऑगमेंटेड जनरेशन (RAG) क्वेरी निष्पादित करें।

ग्राफ RAG प्रासंगिक संदर्भ खोजने के लिए नॉलेज ग्राफ संरचना का उपयोग करता है,
एंटिटी संबंधों को पार करके, और फिर एक एलएलएम का उपयोग करके एक प्रतिक्रिया उत्पन्न करता है।

**तर्क:**

`query`: प्राकृतिक भाषा क्वेरी
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता (डिफ़ॉल्ट: "ट्रस्टग्राफ")
`collection`: संग्रह पहचानकर्ता (डिफ़ॉल्ट: "डिफ़ॉल्ट")
`entity_limit`: पुनः प्राप्त करने के लिए अधिकतम एंटिटीज (डिफ़ॉल्ट: 50)
`triple_limit`: प्रति एंटिटी अधिकतम ट्रिपल (डिफ़ॉल्ट: 30)
`max_subgraph_size`: सबग्राफ में अधिकतम कुल ट्रिपल (डिफ़ॉल्ट: 150)
`max_path_length`: अधिकतम ट्रैवर्सल गहराई (डिफ़ॉल्ट: 2)

**रिटर्न:** स्ट्र: ग्राफ संदर्भ को शामिल करने वाली उत्पन्न प्रतिक्रिया

**उदाहरण:**

```python
flow = api.flow().id("default")
response = flow.graph_rag(
    query="Tell me about Marie Curie's discoveries",
    user="trustgraph",
    collection="scientists",
    entity_limit=20,
    max_path_length=3
)
print(response)
```

### `load_document(self, document, id=None, metadata=None, user=None, collection=None)`

प्रसंस्करण के लिए एक बाइनरी दस्तावेज़ लोड करें।

एक दस्तावेज़ (पीडीएफ, डॉक्स, चित्र, आदि) को निष्कर्षण और
प्रसंस्करण के लिए अपलोड करें, जो प्रवाह के दस्तावेज़ पाइपलाइन के माध्यम से होता है।

**तर्क:**

`document`: बाइट्स के रूप में दस्तावेज़ सामग्री
`id`: वैकल्पिक दस्तावेज़ पहचानकर्ता (यदि None है तो स्वचालित रूप से उत्पन्न)
`metadata`: वैकल्पिक मेटाडेटा (ट्रिपल्स की सूची या emit विधि वाला ऑब्जेक्ट)
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता (वैकल्पिक)
`collection`: संग्रह पहचानकर्ता (वैकल्पिक)

**रिटर्न:** dict: प्रसंस्करण प्रतिक्रिया

**अपवाद:**

`RuntimeError`: यदि आईडी के बिना मेटाडेटा प्रदान किया गया है

**उदाहरण:**

```python
flow = api.flow().id("default")

# Load a PDF document
with open("research.pdf", "rb") as f:
    result = flow.load_document(
        document=f.read(),
        id="research-001",
        user="trustgraph",
        collection="papers"
    )
```

### `load_text(self, text, id=None, metadata=None, charset='utf-8', user=None, collection=None)`

प्रसंस्करण के लिए पाठ सामग्री लोड करें।

प्रवाह के पाठ पाइपलाइन के माध्यम से निष्कर्षण और प्रसंस्करण के लिए पाठ सामग्री अपलोड करें।
पाठ पाइपलाइन।

**तर्क:**

`text`: बाइट्स के रूप में पाठ सामग्री
`id`: वैकल्पिक दस्तावेज़ पहचानकर्ता (यदि None है तो स्वचालित रूप से उत्पन्न)
`metadata`: वैकल्पिक मेटाडेटा (ट्रिपल की सूची या emit विधि वाला ऑब्जेक्ट)
`charset`: वर्ण एन्कोडिंग (डिफ़ॉल्ट: "utf-8")
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता (वैकल्पिक)
`collection`: संग्रह पहचानकर्ता (वैकल्पिक)

**रिटर्न:** dict: प्रसंस्करण प्रतिक्रिया

**अपवाद:**

`RuntimeError`: यदि आईडी के बिना मेटाडेटा प्रदान किया गया है

**उदाहरण:**

```python
flow = api.flow().id("default")

# Load text content
text_content = b"This is the document content..."
result = flow.load_text(
    text=text_content,
    id="text-001",
    charset="utf-8",
    user="trustgraph",
    collection="documents"
)
```

### `mcp_tool(self, name, parameters={})`

एक मॉडल कॉन्टेक्स्ट प्रोटोकॉल (MCP) टूल को निष्पादित करें।

MCP टूल एजेंटों और वर्कफ़्लो के लिए विस्तारित कार्यक्षमता प्रदान करते हैं,
जो बाहरी प्रणालियों और सेवाओं के साथ एकीकरण की अनुमति देते हैं।

**तर्क:**

`name`: टूल का नाम/पहचानकर्ता
`parameters`: टूल पैरामीटर डिक्शनरी (डिफ़ॉल्ट: {})

**रिटर्न:** स्ट्र या डिक्ट: टूल निष्पादन परिणाम

**अपवाद:**

`ProtocolException`: यदि प्रतिक्रिया प्रारूप अमान्य है

**उदाहरण:**

```python
flow = api.flow().id("default")

# Execute a tool
result = flow.mcp_tool(
    name="search-web",
    parameters={"query": "latest AI news", "limit": 5}
)
```

### `nlp_query(self, question, max_results=100)`

एक प्राकृतिक भाषा प्रश्न को GraphQL क्वेरी में बदलें।

**तर्क:**

`question`: प्राकृतिक भाषा प्रश्न
`max_results`: वापस करने के लिए अधिकतम परिणामों की संख्या (डिफ़ॉल्ट: 100)

**वापसी:** graphql_query, variables, detected_schemas, confidence के साथ एक शब्दकोश।

### `prompt(self, id, variables)`

चर प्रतिस्थापन के साथ एक प्रॉम्प्ट टेम्पलेट निष्पादित करें।

प्रॉम्प्ट टेम्प्लेट, गतिशील चर के साथ पुन: प्रयोज्य प्रॉम्प्ट पैटर्न की अनुमति देते हैं, जो सुसंगत प्रॉम्प्ट इंजीनियरिंग के लिए उपयोगी है।
चर प्रतिस्थापन, सुसंगत प्रॉम्प्ट इंजीनियरिंग के लिए उपयोगी।

**तर्क:**

`id`: प्रॉम्प्ट टेम्प्लेट पहचानकर्ता
`variables`: चर नाम से मान मैपिंग का शब्दकोश

**रिटर्न:** स्ट्र या डिक्ट: प्रस्तुत प्रॉम्प्ट परिणाम (टेक्स्ट या संरचित ऑब्जेक्ट)

**अपवाद:**

`ProtocolException`: यदि प्रतिक्रिया प्रारूप अमान्य है

**उदाहरण:**

```python
flow = api.flow().id("default")

# Text template
result = flow.prompt(
    id="summarize-template",
    variables={"topic": "quantum computing", "length": "brief"}
)

# Structured template
result = flow.prompt(
    id="extract-entities",
    variables={"text": "Marie Curie won Nobel Prizes"}
)
```

### `request(self, path, request)`

इस फ्लो इंस्टेंस पर एक सेवा अनुरोध करें।

**तर्क:**

`path`: सेवा पथ (उदाहरण के लिए, "service/text-completion")
`request`: अनुरोध पेलोड डिक्शनरी

**रिटर्न:** डिक्ट: सेवा प्रतिक्रिया

### `row_embeddings_query(self, text, schema_name, user='trustgraph', collection='default', index_name=None, limit=10)`

अनुक्रमित फ़ील्ड पर सिमेंटिक समानता का उपयोग करके पंक्ति डेटा क्वेरी करें।

उन पंक्तियों को खोजता है जिनके अनुक्रमित फ़ील्ड मान इनपुट टेक्स्ट के अर्थ के समान हों, वेक्टर एम्बेडिंग का उपयोग करके। यह संरचित डेटा पर अस्पष्ट/अर्थ संबंधी मिलान को सक्षम बनाता है।

**तर्क:**



`text`: सिमेंटिक खोज के लिए क्वेरी टेक्स्ट।
`schema_name`: खोज करने के लिए स्कीमा का नाम।
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता (डिफ़ॉल्ट: "trustgraph")।
`collection`: संग्रह पहचानकर्ता (डिफ़ॉल्ट: "default")।
`index_name`: वैकल्पिक इंडेक्स नाम, जिससे खोज को विशिष्ट इंडेक्स तक सीमित किया जा सके।
`limit`: अधिकतम परिणामों की संख्या (डिफ़ॉल्ट: 10)।

**रिटर्न:** डिक्ट: क्वेरी परिणाम जिनमें index_name, index_value, text और score शामिल हैं।

**उदाहरण:**

```python
flow = api.flow().id("default")

# Search for customers by name similarity
results = flow.row_embeddings_query(
    text="John Smith",
    schema_name="customers",
    user="trustgraph",
    collection="sales",
    limit=5
)

# Filter to specific index
results = flow.row_embeddings_query(
    text="machine learning engineer",
    schema_name="employees",
    index_name="job_title",
    limit=10
)
```

### `rows_query(self, query, user='trustgraph', collection='default', variables=None, operation_name=None)`

ज्ञान ग्राफ में संरचित पंक्तियों के विरुद्ध एक GraphQL क्वेरी निष्पादित करें।

यह GraphQL सिंटैक्स का उपयोग करके संरचित डेटा पर क्वेरी करता है, जो जटिल क्वेरी की अनुमति देता है
फ़िल्टरिंग, एग्रीगेशन और संबंध ट्रैवर्सल के साथ।

**तर्क:**

`query`: GraphQL क्वेरी स्ट्रिंग
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता (डिफ़ॉल्ट: "trustgraph")
`collection`: संग्रह पहचानकर्ता (डिफ़ॉल्ट: "default")
`variables`: वैकल्पिक क्वेरी चर शब्दकोश
`operation_name`: मल्टी-ऑपरेशन दस्तावेज़ों के लिए वैकल्पिक ऑपरेशन नाम

**रिटर्न:** dict: 'data', 'errors' और/या 'extensions' फ़ील्ड के साथ GraphQL प्रतिक्रिया

**अपवाद:**

`ProtocolException`: यदि सिस्टम-स्तरीय त्रुटि होती है

**उदाहरण:**

```python
flow = api.flow().id("default")

# Simple query
query = '''
{
  scientists(limit: 10) {
    name
    field
    discoveries
  }
}
'''
result = flow.rows_query(
    query=query,
    user="trustgraph",
    collection="scientists"
)

# Query with variables
query = '''
query GetScientist($name: String!) {
  scientists(name: $name) {
    name
    nobelPrizes
  }
}
'''
result = flow.rows_query(
    query=query,
    variables={"name": "Marie Curie"}
)
```

### `schema_selection(self, sample, options=None)`

प्रॉम्प्ट विश्लेषण का उपयोग करके डेटा नमूने के लिए मिलान करने वाले स्कीमा का चयन करें।

**तर्क:**

`sample`: विश्लेषण करने के लिए डेटा नमूना (स्ट्रिंग सामग्री)
`options`: वैकल्पिक पैरामीटर

**रिटर्न:** schema_matches सरणी और मेटाडेटा के साथ डिक्ट

### `structured_query(self, question, user='trustgraph', collection='default')`

संरचित डेटा के खिलाफ एक प्राकृतिक भाषा प्रश्न निष्पादित करें।
एनएलपी क्वेरी रूपांतरण और GraphQL निष्पादन को जोड़ता है।

**तर्क:**

`question`: प्राकृतिक भाषा प्रश्न
`user`: कैसेंड्रा कीस्पेस पहचानकर्ता (डिफ़ॉल्ट: "trustgraph")
`collection`: डेटा संग्रह पहचानकर्ता (डिफ़ॉल्ट: "default")

**रिटर्न:** डेटा और वैकल्पिक त्रुटियों के साथ डिक्ट

### `text_completion(self, system, prompt)`

फ़्लो के एलएलएम का उपयोग करके टेक्स्ट कंप्लीशन निष्पादित करें।

**तर्क:**

`system`: सिस्टम प्रॉम्प्ट जो सहायक के व्यवहार को परिभाषित करता है
`prompt`: उपयोगकर्ता प्रॉम्प्ट/प्रश्न

**रिटर्न:** स्ट्र: उत्पन्न प्रतिक्रिया पाठ

**उदाहरण:**

```python
flow = api.flow().id("default")
response = flow.text_completion(
    system="You are a helpful assistant",
    prompt="What is quantum computing?"
)
print(response)
```

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=10000)`

पैटर्न मिलान का उपयोग करके ज्ञान ग्राफ त्रिकों को क्वेरी करें।

यह आरडीएफ त्रिकों की खोज करता है जो दिए गए विषय, विधेय और/या
ऑब्जेक्ट पैटर्न से मेल खाते हैं। अनिश्चित पैरामीटर वाइल्डकार्ड के रूप में कार्य करते हैं।

**तर्क:**

`s`: विषय यूआरआई (वैकल्पिक, वाइल्डकार्ड के लिए None का उपयोग करें)
`p`: विधेय यूआरआई (वैकल्पिक, वाइल्डकार्ड के लिए None का उपयोग करें)
`o`: ऑब्जेक्ट यूआरआई या लिटरल (वैकल्पिक, वाइल्डकार्ड के लिए None का उपयोग करें)
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता (वैकल्पिक)
`collection`: संग्रह पहचानकर्ता (वैकल्पिक)
`limit`: वापस करने के लिए अधिकतम परिणाम (डिफ़ॉल्ट: 10000)

**रिटर्न:** list[Triple]: मिलान करने वाले ट्रिपल ऑब्जेक्ट की सूची

**उठाता है:**

`RuntimeError`: यदि s या p यूआरआई नहीं है, या o यूआरआई/लिटरल नहीं है

**उदाहरण:**

```python
from trustgraph.knowledge import Uri, Literal

flow = api.flow().id("default")

# Find all triples about a specific subject
triples = flow.triples_query(
    s=Uri("http://example.org/person/marie-curie"),
    user="trustgraph",
    collection="scientists"
)

# Find all instances of a specific relationship
triples = flow.triples_query(
    p=Uri("http://example.org/ontology/discovered"),
    limit=100
)
```


--

## `AsyncFlow`

```python
from trustgraph.api import AsyncFlow
```

REST API का उपयोग करके एसिंक्रोनस फ्लो प्रबंधन क्लाइंट।

यह एसिंक/अवेट पर आधारित फ्लो प्रबंधन संचालन प्रदान करता है, जिसमें लिस्टिंग,
फ्लो शुरू करना, बंद करना और फ्लो क्लास परिभाषाओं का प्रबंधन शामिल है। यह एजेंटों, RAG और प्रश्नों जैसी फ्लो-स्कोप सेवाओं तक गैर-स्ट्रीमिंग
REST एंडपॉइंट के माध्यम से पहुंच भी प्रदान करता है।


ध्यान दें: स्ट्रीमिंग समर्थन के लिए, AsyncSocketClient का उपयोग करें।

### विधियाँ

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

एसिंक्रोनस फ्लो क्लाइंट को इनिशियलाइज़ करें।

**तर्क:**

`url`: ट्रस्टग्राफ API के लिए बेस URL
`timeout`: सेकंड में अनुरोध टाइमआउट
`token`: प्रमाणीकरण के लिए वैकल्पिक बेयरर टोकन

### `aclose(self) -> None`

एसिंक्रोनस क्लाइंट को बंद करें और संसाधनों को साफ़ करें।

ध्यान दें: सफाई aiohttp सत्र संदर्भ प्रबंधकों द्वारा स्वचालित रूप से संभाली जाती है।
यह विधि अन्य एसिंक्रोनस क्लाइंट के साथ स्थिरता के लिए प्रदान की गई है।

### `delete_class(self, class_name: str)`

एक फ्लो क्लास परिभाषा को हटाएं।

यह सिस्टम से एक फ्लो क्लास ब्लूप्रिंट को हटा देता है। यह चल रहे फ्लो उदाहरणों को प्रभावित नहीं करता है।


**तर्क:**

`class_name`: हटाने के लिए फ्लो क्लास का नाम

**उदाहरण:**

```python
async_flow = await api.async_flow()

# Delete a flow class
await async_flow.delete_class("old-flow-class")
```

### `get(self, id: str) -> Dict[str, Any]`

प्रवाह परिभाषा प्राप्त करें।

यह पूर्ण प्रवाह कॉन्फ़िगरेशन प्राप्त करता है, जिसमें इसका क्लास नाम,
विवरण और पैरामीटर शामिल हैं।

**तर्क:**

`id`: प्रवाह पहचानकर्ता

**वापसी:** dict: प्रवाह परिभाषा ऑब्जेक्ट

**उदाहरण:**

```python
async_flow = await api.async_flow()

# Get flow definition
flow_def = await async_flow.get("default")
print(f"Flow class: {flow_def.get('class-name')}")
print(f"Description: {flow_def.get('description')}")
```

### `get_class(self, class_name: str) -> Dict[str, Any]`

प्रवाह वर्ग परिभाषा प्राप्त करें।

यह एक प्रवाह वर्ग के लिए ब्लूप्रिंट परिभाषा प्राप्त करता है, जिसमें इसका
कॉन्फ़िगरेशन स्कीमा और सेवा बाइंडिंग शामिल हैं।

**तर्क:**

`class_name`: प्रवाह वर्ग का नाम

**वापसी:** dict: प्रवाह वर्ग परिभाषा ऑब्जेक्ट

**उदाहरण:**

```python
async_flow = await api.async_flow()

# Get flow class definition
class_def = await async_flow.get_class("default")
print(f"Services: {class_def.get('services')}")
```

### `id(self, flow_id: str)`

एक एसिंक्रोनस फ्लो इंस्टेंस क्लाइंट प्राप्त करें।

यह एक विशिष्ट फ्लो की सेवाओं के साथ इंटरैक्ट करने के लिए एक क्लाइंट लौटाता है
(एजेंट, आरएजी, प्रश्न, एम्बेडिंग, आदि)।

**तर्क:**

`flow_id`: प्रवाह पहचानकर्ता

**वापसी:** AsyncFlowInstance: प्रवाह-विशिष्ट कार्यों के लिए क्लाइंट

**उदाहरण:**

```python
async_flow = await api.async_flow()

# Get flow instance
flow = async_flow.id("default")

# Use flow services
result = await flow.graph_rag(
    query="What is TrustGraph?",
    user="trustgraph",
    collection="default"
)
```

### `list(self) -> List[str]`

सभी फ्लो पहचानकर्ताओं की सूची बनाएं।

सिस्टम में वर्तमान में तैनात सभी फ्लो के आईडी प्राप्त करता है।

**रिटर्न:** list[str]: फ्लो पहचानकर्ताओं की सूची

**उदाहरण:**

```python
async_flow = await api.async_flow()

# List all flows
flows = await async_flow.list()
print(f"Available flows: {flows}")
```

### `list_classes(self) -> List[str]`

सभी फ्लो क्लास नामों की सूची बनाएं।

सिस्टम में उपलब्ध सभी फ्लो क्लास (ब्लूप्रिंट) के नामों को प्राप्त करता है।

**रिटर्न:** list[str]: फ्लो क्लास नामों की सूची

**उदाहरण:**

```python
async_flow = await api.async_flow()

# List available flow classes
classes = await async_flow.list_classes()
print(f"Available flow classes: {classes}")
```

### `put_class(self, class_name: str, definition: Dict[str, Any])`

एक फ्लो क्लास परिभाषा बनाएं या अपडेट करें।

यह एक फ्लो क्लास ब्लूप्रिंट संग्रहीत करता है जिसका उपयोग फ्लो को इंस्टेंटिएट करने के लिए किया जा सकता है।

**तर्क:**

`class_name`: फ्लो क्लास का नाम
`definition`: फ्लो क्लास परिभाषा ऑब्जेक्ट

**उदाहरण:**

```python
async_flow = await api.async_flow()

# Create a custom flow class
class_def = {
    "services": {
        "agent": {"module": "agent", "config": {...}},
        "graph-rag": {"module": "graph-rag", "config": {...}}
    }
}
await async_flow.put_class("custom-flow", class_def)
```

### `request(self, path: str, request_data: Dict[str, Any]) -> Dict[str, Any]`

गेटवे एपीआई को एसिंक्रोनस एचटीटीपी पोस्ट अनुरोध भेजें।

ट्रस्टग्राफ एपीआई को प्रमाणित अनुरोध भेजने के लिए आंतरिक विधि।

**तर्क:**

`path`: एपीआई एंडपॉइंट पथ (बेस यूआरएल के सापेक्ष)
`request_data`: अनुरोध पेलोड डिक्शनरी

**रिटर्न:** डिक्ट: एपीआई से प्रतिक्रिया ऑब्जेक्ट

**अपवाद:**

`ProtocolException`: यदि HTTP स्थिति 200 नहीं है या प्रतिक्रिया मान्य JSON नहीं है
`ApplicationException`: यदि API एक त्रुटि प्रतिक्रिया देता है

### `start(self, class_name: str, id: str, description: str, parameters: Dict | None = None)`

एक नया फ्लो इंस्टेंस शुरू करें।

निर्दिष्ट मापदंडों के साथ एक फ्लो क्लास परिभाषा से एक फ्लो बनाता है और शुरू करता है।


**तर्क:**

`class_name`: फ्लो क्लास का नाम जिसे इंस्टेंट किया जाना है
`id`: नए फ्लो इंस्टेंस के लिए पहचानकर्ता
`description`: फ्लो का मानव-पठनीय विवरण
`parameters`: फ्लो के लिए वैकल्पिक कॉन्फ़िगरेशन पैरामीटर

**उदाहरण:**

```python
async_flow = await api.async_flow()

# Start a flow from a class
await async_flow.start(
    class_name="default",
    id="my-flow",
    description="Custom flow instance",
    parameters={"model": "claude-3-opus"}
)
```

### `stop(self, id: str)`

किसी चल रही प्रक्रिया को रोकें।

यह एक प्रक्रिया के उदाहरण को रोकता है और उसे हटा देता है, जिससे उसके संसाधनों को मुक्त किया जा सकता है।

**तर्क:**

`id`: रोकने के लिए प्रक्रिया की पहचानकर्ता।

**उदाहरण:**

```python
async_flow = await api.async_flow()

# Stop a flow
await async_flow.stop("my-flow")
```


--

## `AsyncFlowInstance`

```python
from trustgraph.api import AsyncFlowInstance
```

एसिंक्रोनस फ्लो इंस्टेंस क्लाइंट।

यह एजेंटों,
आरएजी प्रश्नों, एम्बेडिंग और ग्राफ प्रश्नों सहित फ्लो-स्कोप सेवाओं तक एसिंक्रोनस/अवेट एक्सेस प्रदान करता है। सभी ऑपरेशन पूर्ण
प्रतिक्रियाएं (गैर-स्ट्रीमिंग) लौटाते हैं।

ध्यान दें: स्ट्रीमिंग समर्थन के लिए, AsyncSocketFlowInstance का उपयोग करें।

### विधियाँ

### `__init__(self, flow: trustgraph.api.async_flow.AsyncFlow, flow_id: str)`

एसिंक्रोनस फ्लो इंस्टेंस को इनिशियलाइज़ करें।

**तर्क:**

`flow`: पैरेंट AsyncFlow क्लाइंट
`flow_id`: फ्लो पहचानकर्ता

### `agent(self, question: str, user: str, state: Dict | None = None, group: str | None = None, history: List | None = None, **kwargs: Any) -> Dict[str, Any]`

एक एजेंट ऑपरेशन निष्पादित करें (गैर-स्ट्रीमिंग)।

यह एक प्रश्न का उत्तर देने के लिए एक एजेंट चलाता है, जिसमें वैकल्पिक वार्तालाप स्थिति और
इतिहास शामिल है। यह एजेंट द्वारा प्रसंस्करण पूरा करने के बाद पूरी प्रतिक्रिया लौटाता है।


ध्यान दें: यह विधि स्ट्रीमिंग का समर्थन नहीं करती है। वास्तविक समय में एजेंट के विचारों और
टिप्पणियों के लिए, AsyncSocketFlowInstance.agent() का उपयोग करें।

**तर्क:**

`question`: उपयोगकर्ता का प्रश्न या निर्देश
`user`: उपयोगकर्ता पहचानकर्ता
`state`: वार्तालाप संदर्भ के लिए वैकल्पिक स्थिति शब्दकोश
`group`: सत्र प्रबंधन के लिए वैकल्पिक समूह पहचानकर्ता
`history`: वैकल्पिक वार्तालाप इतिहास सूची
`**kwargs`: अतिरिक्त सेवा-विशिष्ट पैरामीटर

**रिटर्न:** dict: उत्तर और मेटाडेटा सहित एजेंट की पूरी प्रतिक्रिया

**उदाहरण:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Execute agent
result = await flow.agent(
    question="What is the capital of France?",
    user="trustgraph"
)
print(f"Answer: {result.get('response')}")
```

### `document_rag(self, query: str, user: str, collection: str, doc_limit: int = 10, **kwargs: Any) -> str`

दस्तावेज़-आधारित आरएजी क्वेरी (गैर-स्ट्रीमिंग) निष्पादित करें।

दस्तावेज़ एम्बेडिंग का उपयोग करके पुनर्प्राप्ति-संवर्धित पीढ़ी करता है।
प्रासंगिक दस्तावेज़ अंशों को सिमेंटिक खोज के माध्यम से पुनर्प्राप्त करता है, फिर पुनर्प्राप्त दस्तावेज़ों के आधार पर
एक प्रतिक्रिया उत्पन्न करता है। पूर्ण प्रतिक्रिया लौटाता है।

ध्यान दें: यह विधि स्ट्रीमिंग का समर्थन नहीं करती है। स्ट्रीमिंग आरएजी प्रतिक्रियाओं के लिए,
AsyncSocketFlowInstance.document_rag() का उपयोग करें।

**तर्क:**

`query`: उपयोगकर्ता क्वेरी टेक्स्ट
`user`: उपयोगकर्ता पहचानकर्ता
`collection`: दस्तावेज़ युक्त संग्रह पहचानकर्ता
`doc_limit`: पुनर्प्राप्त किए जाने वाले दस्तावेज़ अंशों की अधिकतम संख्या (डिफ़ॉल्ट: 10)
`**kwargs`: अतिरिक्त सेवा-विशिष्ट पैरामीटर

**रिटर्न:** str: दस्तावेज़ डेटा के आधार पर उत्पन्न पूर्ण प्रतिक्रिया

**उदाहरण:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Query documents
response = await flow.document_rag(
    query="What does the documentation say about authentication?",
    user="trustgraph",
    collection="docs",
    doc_limit=5
)
print(response)
```

### `embeddings(self, texts: list, **kwargs: Any)`

इनपुट टेक्स्ट के लिए एम्बेडिंग उत्पन्न करें।

टेक्स्ट को संख्यात्मक वेक्टर प्रतिनिधित्व में परिवर्तित करता है, जो कि फ्लो के
कॉन्फ़िगर किए गए एम्बेडिंग मॉडल का उपयोग करके किया जाता है। सिमेंटिक खोज और समानता
तुलना के लिए उपयोगी।

**तर्क:**

`texts`: एम्बेड करने के लिए इनपुट टेक्स्ट की सूची।
`**kwargs`: अतिरिक्त सेवा-विशिष्ट पैरामीटर।

**रिटर्न:** dict: एम्बेडिंग वेक्टर युक्त प्रतिक्रिया।

**उदाहरण:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Generate embeddings
result = await flow.embeddings(texts=["Sample text to embed"])
vectors = result.get("vectors")
print(f"Embedding dimension: {len(vectors[0][0])}")
```

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any)`

सिमेंटिक इकाई खोज के लिए क्वेरी ग्राफ एम्बेडिंग।

यह इनपुट टेक्स्ट के लिए सबसे प्रासंगिक इकाइयों को खोजने के लिए ग्राफ इकाई एम्बेडिंग पर सिमेंटिक खोज करता है। समानता के आधार पर रैंक की गई इकाइयों को लौटाता है।


**तर्क:**

`text`: सिमेंटिक खोज के लिए क्वेरी टेक्स्ट।
`user`: उपयोगकर्ता पहचानकर्ता।
`collection`: ग्राफ एम्बेडिंग युक्त संग्रह पहचानकर्ता।
`limit`: लौटाने के लिए अधिकतम परिणामों की संख्या (डिफ़ॉल्ट: 10)।
`**kwargs`: अतिरिक्त सेवा-विशिष्ट पैरामीटर।

**रिटर्न:** dict: रैंक किए गए इकाई मिलानों के साथ प्रतिक्रिया, जिसमें समानता स्कोर शामिल हैं।

**उदाहरण:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Find related entities
results = await flow.graph_embeddings_query(
    text="machine learning algorithms",
    user="trustgraph",
    collection="tech-kb",
    limit=5
)

for entity in results.get("entities", []):
    print(f"{entity['name']}: {entity['score']}")
```

### `graph_rag(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, **kwargs: Any) -> str`

ग्राफ-आधारित आरएजी क्वेरी (गैर-स्ट्रीमिंग) निष्पादित करें।

यह ज्ञान ग्राफ डेटा का उपयोग करके पुनर्प्राप्ति-संवर्धित पीढ़ी करता है।
यह प्रासंगिक संस्थाओं और उनके संबंधों की पहचान करता है, और फिर ग्राफ संरचना पर आधारित एक
प्रतिक्रिया उत्पन्न करता है। यह पूर्ण प्रतिक्रिया लौटाता है।

ध्यान दें: यह विधि स्ट्रीमिंग का समर्थन नहीं करती है। स्ट्रीमिंग आरएजी प्रतिक्रियाओं के लिए,
AsyncSocketFlowInstance.graph_rag() का उपयोग करें।

**तर्क:**

`query`: उपयोगकर्ता क्वेरी टेक्स्ट
`user`: उपयोगकर्ता पहचानकर्ता
`collection`: ज्ञान ग्राफ युक्त संग्रह पहचानकर्ता
`max_subgraph_size`: प्रति सबग्राफ अधिकतम त्रिकों की संख्या (डिफ़ॉल्ट: 1000)
`max_subgraph_count`: पुनर्प्राप्त किए जाने वाले अधिकतम सबग्राफ की संख्या (डिफ़ॉल्ट: 5)
`max_entity_distance`: इकाई विस्तार के लिए अधिकतम ग्राफ दूरी (डिफ़ॉल्ट: 3)
`**kwargs`: अतिरिक्त सेवा-विशिष्ट पैरामीटर

**रिटर्न:** स्ट्रिंग: ग्राफ डेटा पर आधारित पूर्ण उत्पन्न प्रतिक्रिया

**उदाहरण:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Query knowledge graph
response = await flow.graph_rag(
    query="What are the relationships between these entities?",
    user="trustgraph",
    collection="medical-kb",
    max_subgraph_count=3
)
print(response)
```

### `request(self, service: str, request_data: Dict[str, Any]) -> Dict[str, Any]`

किसी फ्लो-स्कोप सेवा को अनुरोध भेजें।

इस फ्लो इंस्टेंस के भीतर सेवाओं को कॉल करने के लिए आंतरिक विधि।

**तर्क:**

`service`: सेवा का नाम (उदाहरण के लिए, "एजेंट", "ग्राफ-आरएजी", "ट्रिपल्स")
`request_data`: सेवा अनुरोध पेलोड

**रिटर्न:** डिक्ट: सेवा प्रतिक्रिया ऑब्जेक्ट

**अपवाद:**

`ProtocolException`: यदि अनुरोध विफल हो जाता है या प्रतिक्रिया अमान्य है
`ApplicationException`: यदि सेवा कोई त्रुटि लौटाती है

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs: Any)`

संरचित डेटा पर सिमेंटिक खोज के लिए क्वेरी रो एम्बेडिंग।

पंक्तियों के रो इंडेक्स एम्बेडिंग पर सिमेंटिक खोज करता है ताकि उन पंक्तियों को खोजा जा सके जिनके
अनुक्रमित फ़ील्ड मान इनपुट टेक्स्ट के सबसे समान हैं। संरचित डेटा पर अस्पष्ट/सिमेंटिक मिलान को सक्षम करता है।

**तर्क:**


`text`: सिमेंटिक खोज के लिए क्वेरी टेक्स्ट।
`schema_name`: खोज के लिए स्कीमा नाम।
`user`: उपयोगकर्ता पहचानकर्ता (डिफ़ॉल्ट: "trustgraph")।
`collection`: संग्रह पहचानकर्ता (डिफ़ॉल्ट: "default")।
`index_name`: वैकल्पिक इंडेक्स नाम जिसका उपयोग खोज को विशिष्ट इंडेक्स तक सीमित करने के लिए किया जा सकता है।
`limit`: वापस करने के लिए अधिकतम परिणामों की संख्या (डिफ़ॉल्ट: 10)।
`**kwargs`: अतिरिक्त सेवा-विशिष्ट पैरामीटर।

**रिटर्न:** dict: मिलान वाले उत्तर जिसमें index_name, index_value, text और score शामिल हैं।

**उदाहरण:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Search for customers by name similarity
results = await flow.row_embeddings_query(
    text="John Smith",
    schema_name="customers",
    user="trustgraph",
    collection="sales",
    limit=5
)

for match in results.get("matches", []):
    print(f"{match['index_name']}: {match['index_value']} (score: {match['score']})")
```

### `rows_query(self, query: str, user: str, collection: str, variables: Dict | None = None, operation_name: str | None = None, **kwargs: Any)`

संग्रहीत पंक्तियों पर एक GraphQL क्वेरी निष्पादित करें।

यह संरचित डेटा पंक्तियों को GraphQL सिंटैक्स का उपयोग करके क्वेरी करता है। यह चर और नामित ऑपरेशनों के साथ जटिल
क्वेरी का समर्थन करता है।

**तर्क:**

`query`: GraphQL क्वेरी स्ट्रिंग
`user`: उपयोगकर्ता पहचानकर्ता
`collection`: पंक्तियों वाले संग्रह पहचानकर्ता
`variables`: वैकल्पिक GraphQL क्वेरी चर
`operation_name`: मल्टी-ऑपरेशन क्वेरी के लिए वैकल्पिक ऑपरेशन नाम
`**kwargs`: अतिरिक्त सेवा-विशिष्ट पैरामीटर

**रिटर्न:** dict: डेटा और/या त्रुटियों के साथ GraphQL प्रतिक्रिया

**उदाहरण:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Execute GraphQL query
query = '''
    query GetUsers($status: String!) {
        users(status: $status) {
            id
            name
            email
        }
    }
'''

result = await flow.rows_query(
    query=query,
    user="trustgraph",
    collection="users",
    variables={"status": "active"}
)

for user in result.get("data", {}).get("users", []):
    print(f"{user['name']}: {user['email']}")
```

### `text_completion(self, system: str, prompt: str, **kwargs: Any) -> str`

पाठ पूर्णता उत्पन्न करें (गैर-स्ट्रीमिंग)।

यह विधि, एक सिस्टम प्रॉम्प्ट और उपयोगकर्ता प्रॉम्प्ट के आधार पर, एक एलएलएम से पाठ प्रतिक्रिया उत्पन्न करती है।
यह पूर्ण प्रतिक्रिया पाठ लौटाता है।

ध्यान दें: यह विधि स्ट्रीमिंग का समर्थन नहीं करती है। स्ट्रीमिंग पाठ पीढ़ी के लिए,
AsyncSocketFlowInstance.text_completion() का उपयोग करें।

**तर्क:**

`system`: सिस्टम प्रॉम्प्ट जो एलएलएम के व्यवहार को परिभाषित करता है।
`prompt`: उपयोगकर्ता प्रॉम्प्ट या प्रश्न।
`**kwargs`: अतिरिक्त, सेवा-विशिष्ट पैरामीटर।

**रिटर्न:** str: पूर्ण उत्पन्न पाठ प्रतिक्रिया।

**उदाहरण:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Generate text
response = await flow.text_completion(
    system="You are a helpful assistant.",
    prompt="Explain quantum computing in simple terms."
)
print(response)
```

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=100, **kwargs: Any)`

पैटर्न मिलान का उपयोग करके RDF त्रिगुणों की खोज करें।

यह निर्दिष्ट विषय, विधेय और/या
ऑब्जेक्ट पैटर्न से मेल खाने वाले त्रिगुणों की खोज करता है। पैटर्न किसी भी मान से मेल खाने के लिए 'None' का उपयोग करते हैं।

**तर्क:**

`s`: विषय पैटर्न (किसी भी मान से मेल खाने के लिए 'None')
`p`: विधेय पैटर्न (किसी भी मान से मेल खाने के लिए 'None')
`o`: ऑब्जेक्ट पैटर्न (किसी भी मान से मेल खाने के लिए 'None')
`user`: उपयोगकर्ता पहचानकर्ता (सभी उपयोगकर्ताओं के लिए 'None')
`collection`: संग्रह पहचानकर्ता (सभी संग्रहों के लिए 'None')
`limit`: लौटाने के लिए त्रिगुणों की अधिकतम संख्या (डिफ़ॉल्ट: 100)
`**kwargs`: अतिरिक्त सेवा-विशिष्ट पैरामीटर

**वापसी:** dict: मिलान करने वाले त्रिगुणों वाली प्रतिक्रिया

**उदाहरण:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Find all triples with a specific predicate
results = await flow.triples_query(
    p="knows",
    user="trustgraph",
    collection="social",
    limit=50
)

for triple in results.get("triples", []):
    print(f"{triple['s']} knows {triple['o']}")
```


--

## `SocketClient`

```python
from trustgraph.api import SocketClient
```

स्ट्रीमिंग कार्यों के लिए सिंक्रोनस वेबसॉकेट क्लाइंट।

यह वेबसॉकेट-आधारित ट्रस्टग्राफ सेवाओं के लिए एक सिंक्रोनस इंटरफ़ेस प्रदान करता है,
जो उपयोग में आसानी के लिए सिंक्रोनस जनरेटर के साथ एसिंक्रोनस वेबसॉकेट लाइब्रेरी को रैप करता है।
यह एजेंटों, आरएजी प्रश्नों और टेक्स्ट पूर्णता से स्ट्रीमिंग प्रतिक्रियाओं का समर्थन करता है।

ध्यान दें: यह एसिंक्रोनस वेबसॉकेट ऑपरेशनों के चारों ओर एक सिंक्रोनस रैपर है।
वास्तविक एसिंक्रोनस समर्थन के लिए, AsyncSocketClient का उपयोग करें।

### विधियाँ

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

सिंक्रोनस वेबसॉकेट क्लाइंट को इनिशियलाइज़ करें।

**तर्क:**

`url`: ट्रस्टग्राफ एपीआई के लिए बेस यूआरएल (HTTP/HTTPS को WS/WSS में परिवर्तित किया जाएगा)
`timeout`: सेकंड में वेबसॉकेट टाइमआउट
`token`: प्रमाणीकरण के लिए वैकल्पिक बेयरर टोकन

### `close(self) -> None`

वेबसॉकेट कनेक्शन बंद करें।

ध्यान दें: एसिंक्रोनस कोड में संदर्भ प्रबंधकों द्वारा सफाई स्वचालित रूप से संभाली जाती है।

### `flow(self, flow_id: str) -> 'SocketFlowInstance'`

वेबसॉकेट स्ट्रीमिंग ऑपरेशनों के लिए एक फ्लो इंस्टेंस प्राप्त करें।

**तर्क:**

`flow_id`: फ्लो पहचानकर्ता

**रिटर्न:** SocketFlowInstance: स्ट्रीमिंग विधियों वाला फ्लो इंस्टेंस

**उदाहरण:**

```python
socket = api.socket()
flow = socket.flow("default")

# Stream agent responses
for chunk in flow.agent(question="Hello", user="trustgraph", streaming=True):
    print(chunk.content, end='', flush=True)
```


--

## `SocketFlowInstance`

```python
from trustgraph.api import SocketFlowInstance
```

सिंक्रोनस वेबसॉकेट फ्लो इंस्टेंस, स्ट्रीमिंग कार्यों के लिए।

यह REST फ्लोइंस्टेंस के समान इंटरफ़ेस प्रदान करता है, लेकिन वास्तविक समय प्रतिक्रियाओं के लिए वेबसॉकेट-आधारित
स्ट्रीमिंग समर्थन के साथ। सभी विधियाँ एक वैकल्पिक
`streaming` पैरामीटर का समर्थन करती हैं, जो वृद्धिशील परिणाम वितरण को सक्षम करता है।

### विधियाँ

### `__init__(self, client: trustgraph.api.socket_client.SocketClient, flow_id: str) -> None`

सॉकेट फ्लो इंस्टेंस को आरंभ करें।

**तर्क:**

`client`: पैरेंट सॉकेटक्लाइंट
`flow_id`: फ्लो पहचानकर्ता

### `agent(self, question: str, user: str, state: Dict[str, Any] | None = None, group: str | None = None, history: List[Dict[str, Any]] | None = None, streaming: bool = False, **kwargs: Any) -> Dict[str, Any] | Iterator[trustgraph.api.types.StreamingChunk]`

एक एजेंट ऑपरेशन को स्ट्रीमिंग समर्थन के साथ निष्पादित करें।

एजेंट टूल का उपयोग करके बहु-चरणीय तर्क कर सकते हैं। यह विधि हमेशा
स्ट्रीमिंग चंक्स (विचार, अवलोकन, उत्तर) लौटाती है, भले ही
streaming=False हो, ताकि एजेंट की तर्क प्रक्रिया दिखाई जा सके।

**तर्क:**

`question`: उपयोगकर्ता का प्रश्न या निर्देश
`user`: उपयोगकर्ता पहचानकर्ता
`state`: स्टेटफुल वार्तालापों के लिए वैकल्पिक स्टेट डिक्शनरी
`group`: मल्टी-यूजर संदर्भों के लिए वैकल्पिक समूह पहचानकर्ता
`history`: वैकल्पिक रूप से संदेशों की सूची के रूप में वार्तालाप इतिहास
`streaming`: स्ट्रीमिंग मोड सक्षम करें (डिफ़ॉल्ट: False)
`**kwargs`: एजेंट सेवा को पास किए गए अतिरिक्त पैरामीटर

**रिटर्न:** Iterator[StreamingChunk]: एजेंट के विचारों, अवलोकनों और उत्तरों का स्ट्रीम

**उदाहरण:**

```python
socket = api.socket()
flow = socket.flow("default")

# Stream agent reasoning
for chunk in flow.agent(
    question="What is quantum computing?",
    user="trustgraph",
    streaming=True
):
    if isinstance(chunk, AgentThought):
        print(f"[Thinking] {chunk.content}")
    elif isinstance(chunk, AgentObservation):
        print(f"[Observation] {chunk.content}")
    elif isinstance(chunk, AgentAnswer):
        print(f"[Answer] {chunk.content}")
```

### `agent_explain(self, question: str, user: str, collection: str, state: Dict[str, Any] | None = None, group: str | None = None, history: List[Dict[str, Any]] | None = None, **kwargs: Any) -> Iterator[trustgraph.api.types.StreamingChunk | trustgraph.api.types.ProvenanceEvent]`

स्पष्टीकरण समर्थन के साथ एक एजेंट ऑपरेशन निष्पादित करें।

यह सामग्री खंडों (AgentThought, AgentObservation, AgentAnswer)
और प्रामाणिकता घटनाओं (ProvenanceEvent) दोनों को स्ट्रीम करता है। प्रामाणिकता घटनाओं में URI होते हैं
जिन्हें विस्तृत जानकारी प्राप्त करने के लिए ExplainabilityClient का उपयोग करके प्राप्त किया जा सकता है
एजेंट के तर्क प्रक्रिया के बारे में।

एजेंट ट्रेस में शामिल हैं:
सत्र: प्रारंभिक प्रश्न और सत्र मेटाडेटा
पुनरावृत्तियाँ: प्रत्येक विचार/क्रिया/अवलोकन चक्र
निष्कर्ष: अंतिम उत्तर

**तर्क:**

`question`: उपयोगकर्ता का प्रश्न या निर्देश
`user`: उपयोगकर्ता पहचानकर्ता
`collection`: प्रामाणिकता भंडारण के लिए संग्रह पहचानकर्ता
`state`: राज्यपूर्ण वार्ता के लिए वैकल्पिक राज्य शब्दकोश
`group`: बहु-उपयोगकर्ता संदर्भों के लिए वैकल्पिक समूह पहचानकर्ता
`history`: संदेशों की सूची के रूप में वैकल्पिक वार्ता इतिहास
`**kwargs`: एजेंट सेवा को अतिरिक्त पैरामीटर
`Yields`: 
`Union[StreamingChunk, ProvenanceEvent]`: एजेंट खंड और प्रामाणिकता घटनाएँ

**उदाहरण:**

```python
from trustgraph.api import Api, ExplainabilityClient, ProvenanceEvent
from trustgraph.api import AgentThought, AgentObservation, AgentAnswer

socket = api.socket()
flow = socket.flow("default")
explain_client = ExplainabilityClient(flow)

provenance_ids = []
for item in flow.agent_explain(
    question="What is the capital of France?",
    user="trustgraph",
    collection="default"
):
    if isinstance(item, AgentThought):
        print(f"[Thought] {item.content}")
    elif isinstance(item, AgentObservation):
        print(f"[Observation] {item.content}")
    elif isinstance(item, AgentAnswer):
        print(f"[Answer] {item.content}")
    elif isinstance(item, ProvenanceEvent):
        provenance_ids.append(item.explain_id)

# Fetch session trace after completion
if provenance_ids:
    trace = explain_client.fetch_agent_trace(
        provenance_ids[0],  # Session URI is first
        graph="urn:graph:retrieval",
        user="trustgraph",
        collection="default"
    )
```

### `document_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any) -> Dict[str, Any]`

सिमेंटिक समानता का उपयोग करके दस्तावेज़ के टुकड़ों को क्वेरी करें।

**तर्क:**

`text`: सिमेंटिक खोज के लिए क्वेरी टेक्स्ट
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता
`collection`: संग्रह पहचानकर्ता
`limit`: अधिकतम परिणामों की संख्या (डिफ़ॉल्ट: 10)
`**kwargs`: सेवा को अतिरिक्त पैरामीटर

**रिटर्न:** डिक्ट: मिलान करने वाले दस्तावेज़ टुकड़ों के chunk_ids के साथ क्वेरी परिणाम

**उदाहरण:**

```python
socket = api.socket()
flow = socket.flow("default")

results = flow.document_embeddings_query(
    text="machine learning algorithms",
    user="trustgraph",
    collection="research-papers",
    limit=5
)
# results contains {"chunks": [{"chunk_id": "...", "score": 0.95}, ...]}
```

### `document_rag(self, query: str, user: str, collection: str, doc_limit: int = 10, streaming: bool = False, **kwargs: Any) -> str | Iterator[str]`

दस्तावेज़-आधारित आरएजी क्वेरी को वैकल्पिक स्ट्रीमिंग के साथ निष्पादित करें।

यह प्रासंगिक दस्तावेज़ टुकड़ों को खोजने के लिए वेक्टर एम्बेडिंग का उपयोग करता है, फिर एक एलएलएम का उपयोग करके
प्रतिक्रिया उत्पन्न करता है। स्ट्रीमिंग मोड क्रमिक रूप से परिणाम प्रदान करता है।

**तर्क:**

`query`: प्राकृतिक भाषा क्वेरी
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता
`collection`: संग्रह पहचानकर्ता
`doc_limit`: पुनर्प्राप्त किए जाने वाले अधिकतम दस्तावेज़ टुकड़ों की संख्या (डिफ़ॉल्ट: 10)
`streaming`: स्ट्रीमिंग मोड सक्षम करें (डिफ़ॉल्ट: False)
`**kwargs`: सेवा को पारित अतिरिक्त पैरामीटर

**रिटर्न:** Union[str, Iterator[str]]: पूर्ण प्रतिक्रिया या पाठ टुकड़ों की धारा

**उदाहरण:**

```python
socket = api.socket()
flow = socket.flow("default")

# Streaming document RAG
for chunk in flow.document_rag(
    query="Summarize the key findings",
    user="trustgraph",
    collection="research-papers",
    doc_limit=5,
    streaming=True
):
    print(chunk, end='', flush=True)
```

### `document_rag_explain(self, query: str, user: str, collection: str, doc_limit: int = 10, **kwargs: Any) -> Iterator[trustgraph.api.types.RAGChunk | trustgraph.api.types.ProvenanceEvent]`

दस्तावेज़-आधारित आरएजी क्वेरी को व्याख्यात्मकता समर्थन के साथ निष्पादित करें।

यह सामग्री के टुकड़ों (RAGChunk) और उत्पत्ति घटनाओं (ProvenanceEvent) दोनों को स्ट्रीम करता है।
उत्पत्ति घटनाओं में यूआरआई होते हैं जिन्हें ExplainabilityClient का उपयोग करके प्राप्त किया जा सकता है
ताकि प्रतिक्रिया कैसे उत्पन्न हुई, इसके बारे में विस्तृत जानकारी प्राप्त की जा सके।

दस्तावेज़ आरएजी ट्रेस में निम्नलिखित शामिल हैं:
प्रश्न: उपयोगकर्ता की क्वेरी
अन्वेषण: दस्तावेज़ भंडार से प्राप्त किए गए टुकड़े (chunk_count)
संश्लेषण: उत्पन्न उत्तर

**तर्क:**

`query`: प्राकृतिक भाषा क्वेरी
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता
`collection`: संग्रह पहचानकर्ता
`doc_limit`: पुनर्प्राप्त करने के लिए अधिकतम दस्तावेज़ टुकड़े (डिफ़ॉल्ट: 10)
`**kwargs`: सेवा को पारित अतिरिक्त पैरामीटर
`Yields`: 
`Union[RAGChunk, ProvenanceEvent]`: सामग्री के टुकड़े और उत्पत्ति घटनाएं

**उदाहरण:**

```python
from trustgraph.api import Api, ExplainabilityClient, RAGChunk, ProvenanceEvent

socket = api.socket()
flow = socket.flow("default")
explain_client = ExplainabilityClient(flow)

for item in flow.document_rag_explain(
    query="Summarize the key findings",
    user="trustgraph",
    collection="research-papers",
    doc_limit=5
):
    if isinstance(item, RAGChunk):
        print(item.content, end='', flush=True)
    elif isinstance(item, ProvenanceEvent):
        # Fetch entity details
        entity = explain_client.fetch_entity(
            item.explain_id,
            graph=item.explain_graph,
            user="trustgraph",
            collection="research-papers"
        )
        print(f"Event: {entity}", file=sys.stderr)
```

### `embeddings(self, texts: list, **kwargs: Any) -> Dict[str, Any]`

एक या अधिक ग्रंथों के लिए वेक्टर एम्बेडिंग उत्पन्न करें।

**तर्क:**

`texts`: एम्बेड करने के लिए इनपुट ग्रंथों की सूची
`**kwargs`: सेवा को पास किए गए अतिरिक्त पैरामीटर

**रिटर्न:** dict: वैक्टर युक्त प्रतिक्रिया (प्रत्येक इनपुट टेक्स्ट के लिए एक सेट)

**उदाहरण:**

```python
socket = api.socket()
flow = socket.flow("default")

result = flow.embeddings(["quantum computing"])
vectors = result.get("vectors", [])
```

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any) -> Dict[str, Any]`

सिमेंटिक समानता का उपयोग करके ज्ञान ग्राफ संस्थाओं को क्वेरी करें।

**तर्क:**

`text`: सिमेंटिक खोज के लिए क्वेरी टेक्स्ट
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता
`collection`: संग्रह पहचानकर्ता
`limit`: अधिकतम परिणामों की संख्या (डिफ़ॉल्ट: 10)
`**kwargs`: सेवा को अतिरिक्त पैरामीटर

**रिटर्न:** dict: समान संस्थाओं के साथ क्वेरी परिणाम

**उदाहरण:**

```python
socket = api.socket()
flow = socket.flow("default")

results = flow.graph_embeddings_query(
    text="physicist who discovered radioactivity",
    user="trustgraph",
    collection="scientists",
    limit=5
)
```

### `graph_rag(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, streaming: bool = False, **kwargs: Any) -> str | Iterator[str]`

ग्राफ-आधारित आरएजी क्वेरी को वैकल्पिक स्ट्रीमिंग के साथ निष्पादित करें।

यह प्रासंगिक संदर्भ खोजने के लिए ज्ञान ग्राफ संरचना का उपयोग करता है, और फिर
एक एलएलएम का उपयोग करके प्रतिक्रिया उत्पन्न करता है। स्ट्रीमिंग मोड क्रमिक रूप से परिणाम प्रदान करता है।

**तर्क:**

`query`: प्राकृतिक भाषा क्वेरी
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता
`collection`: संग्रह पहचानकर्ता
`max_subgraph_size`: सबग्राफ में अधिकतम कुल त्रिगुण (डिफ़ॉल्ट: 1000)
`max_subgraph_count`: उपग्राफ की अधिकतम संख्या (डिफ़ॉल्ट: 5)
`max_entity_distance`: अधिकतम ट्रैवर्सल गहराई (डिफ़ॉल्ट: 3)
`streaming`: स्ट्रीमिंग मोड सक्षम करें (डिफ़ॉल्ट: False)
`**kwargs`: सेवा को अतिरिक्त पैरामीटर जो भेजे जाते हैं

**रिटर्न:** यूनियन[स्ट्रिंग, इटरेटर[स्ट्रिंग]]: पूर्ण प्रतिक्रिया या टेक्स्ट चंक्स की स्ट्रीम

**उदाहरण:**

```python
socket = api.socket()
flow = socket.flow("default")

# Streaming graph RAG
for chunk in flow.graph_rag(
    query="Tell me about Marie Curie",
    user="trustgraph",
    collection="scientists",
    streaming=True
):
    print(chunk, end='', flush=True)
```

### `graph_rag_explain(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, **kwargs: Any) -> Iterator[trustgraph.api.types.RAGChunk | trustgraph.api.types.ProvenanceEvent]`

स्पष्टीकरण समर्थन के साथ ग्राफ-आधारित आरएजी क्वेरी निष्पादित करें।

यह सामग्री खंडों (RAGChunk) और उत्पत्ति घटनाओं (ProvenanceEvent) दोनों को स्ट्रीम करता है।
उत्पत्ति घटनाओं में यूआरआई होते हैं जिन्हें ExplainabilityClient का उपयोग करके प्राप्त किया जा सकता है
ताकि प्रतिक्रिया कैसे उत्पन्न हुई, इसके बारे में विस्तृत जानकारी प्राप्त की जा सके।

**तर्क:**

`query`: प्राकृतिक भाषा क्वेरी
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता
`collection`: संग्रह पहचानकर्ता
`max_subgraph_size`: सबग्राफ में अधिकतम कुल त्रिगुण (डिफ़ॉल्ट: 1000)
`max_subgraph_count`: उपग्राफों की अधिकतम संख्या (डिफ़ॉल्ट: 5)
`max_entity_distance`: अधिकतम ट्रैवर्सल गहराई (डिफ़ॉल्ट: 3)
`**kwargs`: सेवा को अतिरिक्त पैरामीटर
`Yields`: 
`Union[RAGChunk, ProvenanceEvent]`: सामग्री खंड और उत्पत्ति घटनाएं

**उदाहरण:**

```python
from trustgraph.api import Api, ExplainabilityClient, RAGChunk, ProvenanceEvent

socket = api.socket()
flow = socket.flow("default")
explain_client = ExplainabilityClient(flow)

provenance_ids = []
response_text = ""

for item in flow.graph_rag_explain(
    query="Tell me about Marie Curie",
    user="trustgraph",
    collection="scientists"
):
    if isinstance(item, RAGChunk):
        response_text += item.content
        print(item.content, end='', flush=True)
    elif isinstance(item, ProvenanceEvent):
        provenance_ids.append(item.provenance_id)

# Fetch explainability details
for prov_id in provenance_ids:
    entity = explain_client.fetch_entity(
        prov_id,
        graph="urn:graph:retrieval",
        user="trustgraph",
        collection="scientists"
    )
    print(f"Entity: {entity}")
```

### `mcp_tool(self, name: str, parameters: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]`

मॉडल कॉन्टेक्स्ट प्रोटोकॉल (MCP) टूल को निष्पादित करें।

**तर्क:**

`name`: टूल का नाम/पहचानकर्ता
`parameters`: टूल पैरामीटर डिक्शनरी
`**kwargs`: सेवा को पास किए गए अतिरिक्त पैरामीटर

**रिटर्न:** डिक्ट: टूल निष्पादन परिणाम

**उदाहरण:**

```python
socket = api.socket()
flow = socket.flow("default")

result = flow.mcp_tool(
    name="search-web",
    parameters={"query": "latest AI news", "limit": 5}
)
```

### `prompt(self, id: str, variables: Dict[str, str], streaming: bool = False, **kwargs: Any) -> str | Iterator[str]`

एक वैकल्पिक स्ट्रीमिंग विकल्प के साथ एक प्रॉम्प्ट टेम्पलेट निष्पादित करें।

**तर्क:**

`id`: प्रॉम्प्ट टेम्पलेट पहचानकर्ता
`variables`: चर नाम से मान मैपिंग का शब्दकोश
`streaming`: स्ट्रीमिंग मोड सक्षम करें (डिफ़ॉल्ट: False)
`**kwargs`: सेवा को अतिरिक्त पैरामीटर

**रिटर्न:** Union[str, Iterator[str]]: पूर्ण प्रतिक्रिया या टेक्स्ट चंक्स की धारा

**उदाहरण:**

```python
socket = api.socket()
flow = socket.flow("default")

# Streaming prompt execution
for chunk in flow.prompt(
    id="summarize-template",
    variables={"topic": "quantum computing", "length": "brief"},
    streaming=True
):
    print(chunk, end='', flush=True)
```

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs: Any) -> Dict[str, Any]`

अनुक्रमित फ़ील्ड पर सिमेंटिक समानता का उपयोग करके पंक्ति डेटा क्वेरी करें।

उन पंक्तियों को खोजें जिनके अनुक्रमित फ़ील्ड मान इनपुट टेक्स्ट के सिमेंटिक रूप से समान हैं,
वेक्टर एम्बेडिंग का उपयोग करके। यह संरचित डेटा पर अस्पष्ट/सिमेंटिक मिलान को सक्षम बनाता है।


**तर्क:**

`text`: सिमेंटिक खोज के लिए क्वेरी टेक्स्ट
`schema_name`: खोज के लिए स्कीमा का नाम
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता (डिफ़ॉल्ट: "trustgraph")
`collection`: संग्रह पहचानकर्ता (डिफ़ॉल्ट: "default")
`index_name`: वैकल्पिक इंडेक्स नाम जिससे खोज को विशिष्ट इंडेक्स तक सीमित किया जा सके
`limit`: अधिकतम परिणामों की संख्या (डिफ़ॉल्ट: 10)
`**kwargs`: सेवा को अतिरिक्त पैरामीटर जो पास किए जाते हैं

**रिटर्न:** dict: मिलान वाले क्वेरी परिणाम जिनमें index_name, index_value, text और score शामिल हैं

**उदाहरण:**

```python
socket = api.socket()
flow = socket.flow("default")

# Search for customers by name similarity
results = flow.row_embeddings_query(
    text="John Smith",
    schema_name="customers",
    user="trustgraph",
    collection="sales",
    limit=5
)

# Filter to specific index
results = flow.row_embeddings_query(
    text="machine learning engineer",
    schema_name="employees",
    index_name="job_title",
    limit=10
)
```

### `rows_query(self, query: str, user: str, collection: str, variables: Dict[str, Any] | None = None, operation_name: str | None = None, **kwargs: Any) -> Dict[str, Any]`

संरचित पंक्तियों के विरुद्ध एक GraphQL क्वेरी निष्पादित करें।

**तर्क:**

`query`: GraphQL क्वेरी स्ट्रिंग
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता
`collection`: संग्रह पहचानकर्ता
`variables`: वैकल्पिक क्वेरी चर शब्दकोश
`operation_name`: मल्टी-ऑपरेशन दस्तावेज़ों के लिए वैकल्पिक ऑपरेशन नाम
`**kwargs`: सेवा को पारित अतिरिक्त पैरामीटर

**रिटर्न:** dict: डेटा, त्रुटियों और/या एक्सटेंशन के साथ GraphQL प्रतिक्रिया

**उदाहरण:**

```python
socket = api.socket()
flow = socket.flow("default")

query = '''
{
  scientists(limit: 10) {
    name
    field
    discoveries
  }
}
'''
result = flow.rows_query(
    query=query,
    user="trustgraph",
    collection="scientists"
)
```

### `text_completion(self, system: str, prompt: str, streaming: bool = False, **kwargs) -> str | Iterator[str]`

वैकल्पिक स्ट्रीमिंग के साथ टेक्स्ट पूर्णता निष्पादित करें।

**तर्क:**

`system`: सिस्टम प्रॉम्प्ट जो सहायक के व्यवहार को परिभाषित करता है।
`prompt`: उपयोगकर्ता प्रॉम्प्ट/प्रश्न।
`streaming`: स्ट्रीमिंग मोड सक्षम करें (डिफ़ॉल्ट: False)।
`**kwargs`: सेवा को पारित अतिरिक्त पैरामीटर।

**रिटर्न:** Union[str, Iterator[str]]: पूर्ण प्रतिक्रिया या टेक्स्ट टुकड़ों की धारा।

**उदाहरण:**

```python
socket = api.socket()
flow = socket.flow("default")

# Non-streaming
response = flow.text_completion(
    system="You are helpful",
    prompt="Explain quantum computing",
    streaming=False
)
print(response)

# Streaming
for chunk in flow.text_completion(
    system="You are helpful",
    prompt="Explain quantum computing",
    streaming=True
):
    print(chunk, end='', flush=True)
```

### `triples_query(self, s: str | Dict[str, Any] | None = None, p: str | Dict[str, Any] | None = None, o: str | Dict[str, Any] | None = None, g: str | None = None, user: str | None = None, collection: str | None = None, limit: int = 100, **kwargs: Any) -> List[Dict[str, Any]]`

पैटर्न मिलान का उपयोग करके ज्ञान ग्राफ त्रिकों को क्वेरी करें।

**तर्क:**

`s`: विषय फ़िल्टर - URI स्ट्रिंग, टर्म डिक्शनरी, या वाइल्डकार्ड के लिए None
`p`: विधेय फ़िल्टर - URI स्ट्रिंग, टर्म डिक्शनरी, या वाइल्डकार्ड के लिए None
`o`: वस्तु फ़िल्टर - URI/लिटरल स्ट्रिंग, टर्म डिक्शनरी, या वाइल्डकार्ड के लिए None
`g`: नामित ग्राफ फ़िल्टर - URI स्ट्रिंग या सभी ग्राफों के लिए None
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता (वैकल्पिक)
`collection`: संग्रह पहचानकर्ता (वैकल्पिक)
`limit`: वापस करने के लिए अधिकतम परिणाम (डिफ़ॉल्ट: 100)
`**kwargs`: सेवा को अतिरिक्त पैरामीटर

**वापसी:** List[Dict]: वायर प्रारूप में मिलान किए गए त्रिकों की सूची

**उदाहरण:**

```python
socket = api.socket()
flow = socket.flow("default")

# Find all triples about a specific subject
triples = flow.triples_query(
    s="http://example.org/person/marie-curie",
    user="trustgraph",
    collection="scientists"
)

# Query with named graph filter
triples = flow.triples_query(
    s="urn:trustgraph:session:abc123",
    g="urn:graph:retrieval",
    user="trustgraph",
    collection="default"
)
```

### `triples_query_stream(self, s: str | Dict[str, Any] | None = None, p: str | Dict[str, Any] | None = None, o: str | Dict[str, Any] | None = None, g: str | None = None, user: str | None = None, collection: str | None = None, limit: int = 100, batch_size: int = 20, **kwargs: Any) -> Iterator[List[Dict[str, Any]]]`

स्ट्रीमिंग बैचों के साथ नॉलेज ग्राफ ट्रिपल क्वेरी करें।

जैसे ही ट्रिपल आते हैं, वे बैचों में उपलब्ध होते हैं, जिससे पहले परिणाम प्राप्त करने का समय कम होता है
और बड़े परिणाम सेट के लिए मेमोरी ओवरहेड कम होता है।

**तर्क:**

`s`: विषय फ़िल्टर - URI स्ट्रिंग, टर्म डिक्ट, या वाइल्डकार्ड के लिए None
`p`: विधेय फ़िल्टर - URI स्ट्रिंग, टर्म डिक्ट, या वाइल्डकार्ड के लिए None
`o`: वस्तु फ़िल्टर - URI/लिटरल स्ट्रिंग, टर्म डिक्ट, या वाइल्डकार्ड के लिए None
`g`: नामित ग्राफ फ़िल्टर - URI स्ट्रिंग या सभी ग्राफ के लिए None
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता (वैकल्पिक)
`collection`: संग्रह पहचानकर्ता (वैकल्पिक)
`limit`: वापस करने के लिए अधिकतम परिणाम (डिफ़ॉल्ट: 100)
`batch_size`: प्रति बैच ट्रिपल (डिफ़ॉल्ट: 20)
`**kwargs`: सेवा को पास किए गए अतिरिक्त पैरामीटर
`Yields`: 
`List[Dict]`: वायर प्रारूप में ट्रिपल के बैच

**उदाहरण:**

```python
socket = api.socket()
flow = socket.flow("default")

for batch in flow.triples_query_stream(
    user="trustgraph",
    collection="default"
):
    for triple in batch:
        print(triple["s"], triple["p"], triple["o"])
```


--

## `AsyncSocketClient`

```python
from trustgraph.api import AsyncSocketClient
```

एसिंक्रोनस वेबसॉकेट क्लाइंट

### विधियाँ

### `__init__(self, url: str, timeout: int, token: str | None)`

स्वयं को आरंभ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।

### `aclose(self)`

वेबसॉकेट कनेक्शन बंद करें

### `flow(self, flow_id: str)`

वेबसॉकेट संचालन के लिए एसिंक्रोनस फ्लो इंस्टेंस प्राप्त करें


--

## `AsyncSocketFlowInstance`

```python
from trustgraph.api import AsyncSocketFlowInstance
```

एसिंक्रोनस वेबसॉकेट फ्लो इंस्टेंस

### विधियाँ

### `__init__(self, client: trustgraph.api.async_socket_client.AsyncSocketClient, flow_id: str)`

स्वयं को आरंभ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।

### `agent(self, question: str, user: str, state: Dict[str, Any] | None = None, group: str | None = None, history: list | None = None, streaming: bool = False, **kwargs) -> Dict[str, Any] | AsyncIterator`

वैकल्पिक स्ट्रीमिंग के साथ एजेंट

### `document_rag(self, query: str, user: str, collection: str, doc_limit: int = 10, streaming: bool = False, **kwargs)`

वैकल्पिक स्ट्रीमिंग के साथ RAG दस्तावेज़

### `embeddings(self, texts: list, **kwargs)`

टेक्स्ट एम्बेडिंग उत्पन्न करें

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs)`

सिमेंटिक खोज के लिए ग्राफ एम्बेडिंग क्वेरी करें

### `graph_rag(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, streaming: bool = False, **kwargs)`

वैकल्पिक स्ट्रीमिंग के साथ ग्राफ RAG

### `mcp_tool(self, name: str, parameters: Dict[str, Any], **kwargs)`

MCP टूल निष्पादित करें

### `prompt(self, id: str, variables: Dict[str, str], streaming: bool = False, **kwargs)`

वैकल्पिक स्ट्रीमिंग के साथ प्रॉम्प्ट निष्पादित करें

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs)`

संरचित डेटा पर सिमेंटिक खोज के लिए पंक्ति एम्बेडिंग क्वेरी करें

### `rows_query(self, query: str, user: str, collection: str, variables: Dict | None = None, operation_name: str | None = None, **kwargs)`

संरचित पंक्तियों के खिलाफ GraphQL क्वेरी

### `text_completion(self, system: str, prompt: str, streaming: bool = False, **kwargs)`

वैकल्पिक स्ट्रीमिंग के साथ टेक्स्ट पूर्णता

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=100, **kwargs)`

ट्रिपल पैटर्न क्वेरी


--

### `build_term(value: Any, term_type: str | None = None, datatype: str | None = None, language: str | None = None) -> Dict[str, Any] | None`

एक मान से वायर-फॉर्मेट टर्म डिक्ट बनाएं।

ऑटो-डिटेक्शन नियम (जब term_type None है):
  पहले से ही 't' कुंजी वाला डिक्ट -> यथावत लौटाएं (पहले से ही एक टर्म)
  http://, https://, urn: से शुरू होता है -> IRI
  <> (जैसे, <http://...>) में संलग्न -> IRI (कोण कोष्ठक हटा दिए गए)
  कुछ भी और -> शाब्दिक

**तर्क:**

`value`: टर्म मान (स्ट्रिंग, डिक्ट या None)
`term_type`: 'iri', 'literal' या ऑटो-डिटेक्शन के लिए None में से एक
`datatype`: शाब्दिक ऑब्जेक्ट के लिए डेटाटाइप (जैसे, xsd:integer)
`language`: शाब्दिक ऑब्जेक्ट के लिए भाषा टैग (जैसे, en)

**रिटर्न:** डिक्ट: वायर-फॉर्मेट टर्म डिक्ट, या यदि मान None है तो None


--

## `BulkClient`

```python
from trustgraph.api import BulkClient
```

आयात/निर्यात के लिए सिंक्रोनस बल्क ऑपरेशंस क्लाइंट।

बड़े डेटासेट के लिए कुशल बल्क डेटा ट्रांसफर वेबसॉकेट के माध्यम से प्रदान करता है।
उपयोग में आसानी के लिए सिंक्रोनस जनरेटर के साथ एसिंक्रोनस वेबसॉकेट ऑपरेशंस को रैप करता है।

ध्यान दें: वास्तविक एसिंक्रोनस समर्थन के लिए, AsyncBulkClient का उपयोग करें।

### विधियाँ

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

सिंक्रोनस बल्क क्लाइंट को इनिशियलाइज़ करें।

**तर्क:**

`url`: ट्रस्टग्राफ एपीआई के लिए बेस यूआरएल (HTTP/HTTPS को WS/WSS में परिवर्तित किया जाएगा)
`timeout`: सेकंड में वेबसॉकेट टाइमआउट
`token`: प्रमाणीकरण के लिए वैकल्पिक बेयरर टोकन

### `close(self) -> None`

कनेक्शन बंद करें

### `export_document_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

एक फ्लो से बल्क एक्सपोर्ट डॉक्यूमेंट एम्बेडिंग।

वेबसॉकेट स्ट्रीमिंग के माध्यम से सभी डॉक्यूमेंट चंक एम्बेडिंग को कुशलतापूर्वक डाउनलोड करता है।

**तर्क:**

`flow`: फ्लो आइडेंटिफायर
`**kwargs`: अतिरिक्त पैरामीटर (भविष्य के उपयोग के लिए आरक्षित)

**रिटर्न:** Iterator[Dict[str, Any]]: एम्बेडिंग डिक्शनरी का स्ट्रीम

**उदाहरण:**

```python
bulk = api.bulk()

# Export and process document embeddings
for embedding in bulk.export_document_embeddings(flow="default"):
    chunk_id = embedding.get("chunk_id")
    vector = embedding.get("embedding")
    print(f"{chunk_id}: {len(vector)} dimensions")
```

### `export_entity_contexts(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

किसी फ्लो से बल्क एक्सपोर्ट एंटिटी कॉन्टेक्स्ट।

वेबसॉकेट स्ट्रीमिंग के माध्यम से सभी एंटिटी कॉन्टेक्स्ट जानकारी को कुशलतापूर्वक डाउनलोड करता है।

**तर्क:**

`flow`: फ्लो आइडेंटिफायर
`**kwargs`: अतिरिक्त पैरामीटर (भविष्य के उपयोग के लिए आरक्षित)

**रिटर्न:** Iterator[Dict[str, Any]]: कॉन्टेक्स्ट डिक्शनरी का स्ट्रीम

**उदाहरण:**

```python
bulk = api.bulk()

# Export and process entity contexts
for context in bulk.export_entity_contexts(flow="default"):
    entity = context.get("entity")
    text = context.get("context")
    print(f"{entity}: {text[:100]}...")
```

### `export_graph_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

एक फ्लो से ग्राफ एम्बेडिंग का बल्क एक्सपोर्ट।

वेबसॉकेट स्ट्रीमिंग के माध्यम से सभी ग्राफ एंटिटी एम्बेडिंग को कुशलतापूर्वक डाउनलोड करता है।

**तर्क:**

`flow`: फ्लो आइडेंटिफायर
`**kwargs`: अतिरिक्त पैरामीटर (भविष्य के उपयोग के लिए आरक्षित)

**रिटर्न:** Iterator[Dict[str, Any]]: एम्बेडिंग डिक्शनरी का स्ट्रीम

**उदाहरण:**

```python
bulk = api.bulk()

# Export and process embeddings
for embedding in bulk.export_graph_embeddings(flow="default"):
    entity = embedding.get("entity")
    vector = embedding.get("embedding")
    print(f"{entity}: {len(vector)} dimensions")
```

### `export_triples(self, flow: str, **kwargs: Any) -> Iterator[trustgraph.api.types.Triple]`

एक प्रवाह से RDF त्रिगुणों का बल्क निर्यात करें।

सभी त्रिगुणों को कुशलतापूर्वक WebSocket स्ट्रीमिंग के माध्यम से डाउनलोड करता है।

**तर्क:**

`flow`: प्रवाह पहचानकर्ता
`**kwargs`: अतिरिक्त पैरामीटर (भविष्य के उपयोग के लिए आरक्षित)

**रिटर्न:** Iterator[Triple]: ट्रिपल ऑब्जेक्ट्स की स्ट्रीम

**उदाहरण:**

```python
bulk = api.bulk()

# Export and process triples
for triple in bulk.export_triples(flow="default"):
    print(f"{triple.s} -> {triple.p} -> {triple.o}")
```

### `import_document_embeddings(self, flow: str, embeddings: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

एक फ्लो में दस्तावेज़ एम्बेडिंग को बल्क में इम्पोर्ट करें।

दस्तावेज़ RAG प्रश्नों में उपयोग के लिए, वेबसॉकेट स्ट्रीमिंग के माध्यम से कुशलतापूर्वक दस्तावेज़ चंक एम्बेडिंग अपलोड करता है।


**तर्क:**

`flow`: फ्लो पहचानकर्ता
`embeddings`: एम्बेडिंग डिक्शनरी उत्पन्न करने वाला इटरेटर
`**kwargs`: अतिरिक्त पैरामीटर (भविष्य के उपयोग के लिए आरक्षित)

**उदाहरण:**

```python
bulk = api.bulk()

# Generate document embeddings to import
def doc_embedding_generator():
    yield {"chunk_id": "doc1/p0/c0", "embedding": [0.1, 0.2, ...]}
    yield {"chunk_id": "doc1/p0/c1", "embedding": [0.3, 0.4, ...]}
    # ... more embeddings

bulk.import_document_embeddings(
    flow="default",
    embeddings=doc_embedding_generator()
)
```

### `import_entity_contexts(self, flow: str, contexts: Iterator[Dict[str, Any]], metadata: Dict[str, Any] | None = None, batch_size: int = 100, **kwargs: Any) -> None`

एक फ्लो में एंटिटी कॉन्टेक्स्ट को बल्क में इम्पोर्ट करें।

वेबसॉकेट स्ट्रीमिंग के माध्यम से एंटिटी कॉन्टेक्स्ट जानकारी को कुशलतापूर्वक अपलोड करता है।
एंटिटी कॉन्टेक्स्ट, ग्राफ एंटिटीज के बारे में अतिरिक्त पाठ्य संदर्भ प्रदान करते हैं
बेहतर RAG प्रदर्शन के लिए।

**तर्क:**

`flow`: फ्लो आइडेंटिफायर
`contexts`: कॉन्टेक्स्ट डिक्शनरी उत्पन्न करने वाला इटरेटर
`metadata`: आईडी, मेटाडेटा, उपयोगकर्ता, संग्रह के साथ मेटाडेटा डिक्ट
`batch_size`: बैच प्रति कॉन्टेक्स्ट की संख्या (डिफ़ॉल्ट 100)
`**kwargs`: अतिरिक्त पैरामीटर (भविष्य के उपयोग के लिए आरक्षित)

**उदाहरण:**

```python
bulk = api.bulk()

# Generate entity contexts to import
def context_generator():
    yield {"entity": {"v": "entity1", "e": True}, "context": "Description..."}
    yield {"entity": {"v": "entity2", "e": True}, "context": "Description..."}
    # ... more contexts

bulk.import_entity_contexts(
    flow="default",
    contexts=context_generator(),
    metadata={"id": "doc1", "metadata": [], "user": "user1", "collection": "default"}
)
```

### `import_graph_embeddings(self, flow: str, embeddings: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

एक फ्लो में ग्राफ एम्बेडिंग को बल्क में इम्पोर्ट करें।

वेबसॉकेट स्ट्रीमिंग के माध्यम से ग्राफ एंटिटी एम्बेडिंग को कुशलतापूर्वक अपलोड करता है।

**तर्क:**

`flow`: फ्लो पहचानकर्ता
`embeddings`: एम्बेडिंग डिक्शनरी उत्पन्न करने वाला इटरेटर
`**kwargs`: अतिरिक्त पैरामीटर (भविष्य के उपयोग के लिए आरक्षित)

**उदाहरण:**

```python
bulk = api.bulk()

# Generate embeddings to import
def embedding_generator():
    yield {"entity": "entity1", "embedding": [0.1, 0.2, ...]}
    yield {"entity": "entity2", "embedding": [0.3, 0.4, ...]}
    # ... more embeddings

bulk.import_graph_embeddings(
    flow="default",
    embeddings=embedding_generator()
)
```

### `import_rows(self, flow: str, rows: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

एक फ्लो में संरचित पंक्तियों को बल्क में आयात करें।

कुशलतापूर्वक संरचित डेटा पंक्तियों को WebSocket स्ट्रीमिंग के माध्यम से अपलोड करता है
जिसका उपयोग GraphQL प्रश्नों में किया जाता है।

**तर्क:**

`flow`: फ्लो पहचानकर्ता
`rows`: पंक्ति शब्दकोशों को उत्पन्न करने वाला इटरेटर
`**kwargs`: अतिरिक्त पैरामीटर (भविष्य के उपयोग के लिए आरक्षित)

**उदाहरण:**

```python
bulk = api.bulk()

# Generate rows to import
def row_generator():
    yield {"id": "row1", "name": "Row 1", "value": 100}
    yield {"id": "row2", "name": "Row 2", "value": 200}
    # ... more rows

bulk.import_rows(
    flow="default",
    rows=row_generator()
)
```

### `import_triples(self, flow: str, triples: Iterator[trustgraph.api.types.Triple], metadata: Dict[str, Any] | None = None, batch_size: int = 100, **kwargs: Any) -> None`

एक फ्लो में RDF ट्रिपल का बल्क इम्पोर्ट करें।

वेबसॉकेट स्ट्रीमिंग के माध्यम से बड़ी संख्या में ट्रिपल को कुशलतापूर्वक अपलोड करता है।

**तर्क:**

`flow`: फ्लो आइडेंटिफायर
`triples`: ट्रिपल ऑब्जेक्ट्स उत्पन्न करने वाला इटरेटर
`metadata`: आईडी, मेटाडेटा, यूजर, कलेक्शन के साथ मेटाडेटा डिक्ट
`batch_size`: प्रति बैच ट्रिपल की संख्या (डिफ़ॉल्ट 100)
`**kwargs`: अतिरिक्त पैरामीटर (भविष्य के उपयोग के लिए आरक्षित)

**उदाहरण:**

```python
from trustgraph.api import Triple

bulk = api.bulk()

# Generate triples to import
def triple_generator():
    yield Triple(s="subj1", p="pred", o="obj1")
    yield Triple(s="subj2", p="pred", o="obj2")
    # ... more triples

# Import triples
bulk.import_triples(
    flow="default",
    triples=triple_generator(),
    metadata={"id": "doc1", "metadata": [], "user": "user1", "collection": "default"}
)
```


--

## `AsyncBulkClient`

```python
from trustgraph.api import AsyncBulkClient
```

एसिंक्रोनस बल्क ऑपरेशंस क्लाइंट

### विधियाँ

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

स्वयं को इनिशियलाइज़ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।

### `aclose(self) -> None`

कनेक्शन बंद करें

### `export_document_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

वेबसॉकेट के माध्यम से दस्तावेज़ एम्बेडिंग का बल्क एक्सपोर्ट

### `export_entity_contexts(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

वेबसॉकेट के माध्यम से एंटिटी कॉन्टेक्स्ट का बल्क एक्सपोर्ट

### `export_graph_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

वेबसॉकेट के माध्यम से ग्राफ एम्बेडिंग का बल्क एक्सपोर्ट

### `export_triples(self, flow: str, **kwargs: Any) -> AsyncIterator[trustgraph.api.types.Triple]`

वेबसॉकेट के माध्यम से ट्रिपल्स का बल्क एक्सपोर्ट

### `import_document_embeddings(self, flow: str, embeddings: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

वेबसॉकेट के माध्यम से दस्तावेज़ एम्बेडिंग का बल्क इम्पोर्ट

### `import_entity_contexts(self, flow: str, contexts: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

वेबसॉकेट के माध्यम से एंटिटी कॉन्टेक्स्ट का बल्क इम्पोर्ट

### `import_graph_embeddings(self, flow: str, embeddings: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

वेबसॉकेट के माध्यम से ग्राफ एम्बेडिंग का बल्क इम्पोर्ट

### `import_rows(self, flow: str, rows: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

वेबसॉकेट के माध्यम से पंक्तियों का बल्क इम्पोर्ट

### `import_triples(self, flow: str, triples: AsyncIterator[trustgraph.api.types.Triple], **kwargs: Any) -> None`

वेबसॉकेट के माध्यम से ट्रिपल्स का बल्क इम्पोर्ट


--

## `Metrics`

```python
from trustgraph.api import Metrics
```

सिंक्रोनस मेट्रिक्स क्लाइंट

### विधियाँ

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

स्वयं को आरंभ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।

### `get(self) -> str`

प्रोमेथियस मेट्रिक्स को टेक्स्ट के रूप में प्राप्त करें


--

## `AsyncMetrics`

```python
from trustgraph.api import AsyncMetrics
```

एसिंक्रोनस मेट्रिक्स क्लाइंट

### विधियाँ

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

स्वयं को आरंभ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।

### `aclose(self) -> None`

कनेक्शन बंद करें

### `get(self) -> str`

प्रोमेथियस मेट्रिक्स को टेक्स्ट के रूप में प्राप्त करें


--

## `ExplainabilityClient`

```python
from trustgraph.api import ExplainabilityClient
```

स्पष्टीकरण संस्थाओं को लाने के लिए क्लाइंट, जिसमें अंततः स्थिरता प्रबंधन शामिल है।

यह शांत अवस्था का पता लगाने का उपयोग करता है: प्राप्त करें, प्रतीक्षा करें, फिर से प्राप्त करें, तुलना करें।
यदि परिणाम समान हैं, तो डेटा स्थिर है।

### विधियाँ

### `__init__(self, flow_instance, retry_delay: float = 0.2, max_retries: int = 10)`

स्पष्टीकरण क्लाइंट को आरंभ करें।

**तर्क:**

`flow_instance`: त्रिकों को क्वेरी करने के लिए एक SocketFlowInstance
`retry_delay`: पुन: प्रयास के बीच का विलंब (डिफ़ॉल्ट: 0.2)
`max_retries`: अधिकतम पुन: प्रयास (डिफ़ॉल्ट: 10)

### `detect_session_type(self, session_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> str`

पता करें कि क्या सत्र GraphRAG या Agent प्रकार का है।

**तर्क:**

`session_uri`: सत्र/प्रश्न URI
`graph`: नामित ग्राफ
`user`: उपयोगकर्ता/keyspace पहचानकर्ता
`collection`: संग्रह पहचानकर्ता

**रिटर्न:** "graphrag" या "agent"

### `fetch_agent_trace(self, session_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

एक सत्र URI से शुरू होने वाला संपूर्ण Agent ट्रेस प्राप्त करें।

यह उत्पत्ति श्रृंखला का अनुसरण करता है: प्रश्न -> विश्लेषण (s) -> निष्कर्ष

**तर्क:**

`session_uri`: एजेंट सत्र/प्रश्न URI
`graph`: नामित ग्राफ (डिफ़ॉल्ट: urn:graph:retrieval)
`user`: उपयोगकर्ता/keyspace पहचानकर्ता
`collection`: संग्रह पहचानकर्ता
`api`: लाइब्रेरियन एक्सेस के लिए TrustGraph Api उदाहरण (वैकल्पिक)
`max_content`: निष्कर्ष के लिए अधिकतम सामग्री लंबाई

**रिटर्न:** प्रश्न, पुनरावृत्तियों (विश्लेषण सूची), निष्कर्ष संस्थाओं के साथ डिक्ट

### `fetch_docrag_trace(self, question_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

एक प्रश्न URI से शुरू होने वाला संपूर्ण DocumentRAG ट्रेस प्राप्त करें।

यह उत्पत्ति श्रृंखला का अनुसरण करता है:
    प्रश्न -> ग्राउंडिंग -> अन्वेषण -> संश्लेषण

**तर्क:**

`question_uri`: प्रश्न इकाई URI
`graph`: नामित ग्राफ (डिफ़ॉल्ट: urn:graph:retrieval)
`user`: उपयोगकर्ता/keyspace पहचानकर्ता
`collection`: संग्रह पहचानकर्ता
`api`: लाइब्रेरियन एक्सेस के लिए TrustGraph Api उदाहरण (वैकल्पिक)
`max_content`: संश्लेषण के लिए अधिकतम सामग्री लंबाई

**रिटर्न:** प्रश्न, ग्राउंडिंग, अन्वेषण, संश्लेषण संस्थाओं के साथ डिक्ट

### `fetch_document_content(self, document_uri: str, api: Any, user: str | None = None, max_content: int = 10000) -> str`

दस्तावेज़ URI द्वारा लाइब्रेरियन से सामग्री प्राप्त करें।

**तर्क:**

`document_uri`: लाइब्रेरियन में दस्तावेज़ URI
`api`: लाइब्रेरियन एक्सेस के लिए TrustGraph Api उदाहरण
`user`: लाइब्रेरियन के लिए उपयोगकर्ता पहचानकर्ता
`max_content`: वापस करने के लिए अधिकतम सामग्री लंबाई

**रिटर्न:** स्ट्रिंग के रूप में दस्तावेज़ सामग्री

### `fetch_edge_selection(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.EdgeSelection | None`

एक एज सिलेक्शन एंटिटी प्राप्त करें (जो फोकस द्वारा उपयोग किया जाता है)।

**तर्क:**

`uri`: एज सिलेक्शन URI
`graph`: क्वेरी करने के लिए नामित ग्राफ
`user`: उपयोगकर्ता/keyspace पहचानकर्ता
`collection`: संग्रह पहचानकर्ता

**रिटर्न:** एज सिलेक्शन या यदि नहीं मिला तो None

### `fetch_entity(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.ExplainEntity | None`

URI के माध्यम से एक व्याख्यात्मकता इकाई प्राप्त करें और संभावित स्थिरता प्रबंधन के साथ।

शांत अवस्था का पता लगाने का उपयोग करता है:
1. URI के लिए ट्रिपल प्राप्त करें
2. यदि शून्य परिणाम हैं, तो पुनः प्रयास करें
3. यदि गैर-शून्य परिणाम हैं, तो प्रतीक्षा करें और फिर से प्राप्त करें
4. यदि समान परिणाम हैं, तो डेटा स्थिर है - पार्स करें और वापस करें
5. यदि अलग-अलग परिणाम हैं, तो डेटा अभी भी लिखा जा रहा है - पुनः प्रयास करें

**तर्क:**

`uri`: प्राप्त करने के लिए इकाई URI
`graph`: क्वेरी करने के लिए नामित ग्राफ (जैसे, "urn:graph:retrieval")
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता
`collection`: संग्रह पहचानकर्ता

**वापसी:** ExplainEntity उपवर्ग या यदि नहीं मिला तो None

### `fetch_focus_with_edges(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.Focus | None`

एक फोकस इकाई और उसके सभी किनारे चयन प्राप्त करें।

**तर्क:**

`uri`: फोकस इकाई URI
`graph`: क्वेरी करने के लिए नामित ग्राफ
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता
`collection`: संग्रह पहचानकर्ता

**वापसी:** भरे हुए edge_selections के साथ Focus, या None

### `fetch_graphrag_trace(self, question_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

एक प्रश्न URI से शुरू होकर संपूर्ण GraphRAG ट्रेस प्राप्त करें।

उत्पत्ति श्रृंखला का पालन करें: प्रश्न -> ग्राउंडिंग -> अन्वेषण -> फोकस -> संश्लेषण

**तर्क:**

`question_uri`: प्रश्न इकाई URI
`graph`: नामित ग्राफ (डिफ़ॉल्ट: urn:graph:retrieval)
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता
`collection`: संग्रह पहचानकर्ता
`api`: लाइब्रेरियन एक्सेस के लिए ट्रस्टग्राफ एपीआई उदाहरण (वैकल्पिक)
`max_content`: संश्लेषण के लिए अधिकतम सामग्री लंबाई

**वापसी:** प्रश्न, ग्राउंडिंग, अन्वेषण, फोकस, संश्लेषण संस्थाओं के साथ डिक्ट

### `list_sessions(self, graph: str | None = None, user: str | None = None, collection: str | None = None, limit: int = 50) -> List[trustgraph.api.explainability.Question]`

एक संग्रह में सभी व्याख्यात्मकता सत्र (प्रश्न) सूचीबद्ध करें।

**तर्क:**

`graph`: नामित ग्राफ (डिफ़ॉल्ट: urn:graph:retrieval)
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता
`collection`: संग्रह पहचानकर्ता
`limit`: वापस करने के लिए सत्रों की अधिकतम संख्या

**वापसी:** टाइमस्टैम्प द्वारा क्रमबद्ध प्रश्न संस्थाओं की सूची (नवीनतम पहले)

### `resolve_edge_labels(self, edge: Dict[str, str], user: str | None = None, collection: str | None = None) -> Tuple[str, str, str]`

एक किनारे ट्रिपल के सभी घटकों के लिए लेबल हल करें।

**तर्क:**

`edge`: "s", "p", "o" कुंजियों वाला डिक्ट
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता
`collection`: संग्रह पहचानकर्ता

**वापसी:** (s_label, p_label, o_label) का टपल

### `resolve_label(self, uri: str, user: str | None = None, collection: str | None = None) -> str`

कैशिंग के साथ एक URI के लिए rdfs:label हल करें।

**तर्क:**

`uri`: URI जिसके लिए लेबल प्राप्त करना है
`user`: उपयोगकर्ता/कीस्पेस पहचानकर्ता
`collection`: संग्रह पहचानकर्ता

**वापसी:** यदि पाया जाता है तो लेबल, अन्यथा URI स्वयं


--

## `ExplainEntity`

```python
from trustgraph.api import ExplainEntity
```

व्याख्यात्मक संस्थाओं के लिए आधार वर्ग।

**फ़ील्ड:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>

### विधियाँ

### `__init__(self, uri: str, entity_type: str = '') -> None`

स्वयं को आरंभ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।


--

## `Question`

```python
from trustgraph.api import Question
```

प्रश्न इकाई - उपयोगकर्ता का वह प्रश्न जिसने सत्र शुरू किया।

**फ़ील्ड:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`query`: <class 'str'>
`timestamp`: <class 'str'>
`question_type`: <class 'str'>

### विधियाँ

### `__init__(self, uri: str, entity_type: str = '', query: str = '', timestamp: str = '', question_type: str = '') -> None`

स्वयं को आरंभ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।


--

## `Exploration`

```python
from trustgraph.api import Exploration
```

अन्वेषण इकाई - ज्ञान भंडार से प्राप्त किनारे/खंड।

**फ़ील्ड:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`edge_count`: <class 'int'>
`chunk_count`: <class 'int'>
`entities`: typing.List[str]

### विधियाँ

### `__init__(self, uri: str, entity_type: str = '', edge_count: int = 0, chunk_count: int = 0, entities: List[str] = <factory>) -> None`

स्वयं को आरंभ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।


--

## `Focus`

```python
from trustgraph.api import Focus
```

मुख्य इकाई - एलएलएम तर्क के साथ चयनित किनारे (केवल GraphRAG)।

**फ़ील्ड:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`selected_edge_uris`: typing.List[str]
`edge_selections`: typing.List[trustgraph.api.explainability.EdgeSelection]

### विधियाँ

### `__init__(self, uri: str, entity_type: str = '', selected_edge_uris: List[str] = <factory>, edge_selections: List[trustgraph.api.explainability.EdgeSelection] = <factory>) -> None`

स्वयं को आरंभ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।


--

## `Synthesis`

```python
from trustgraph.api import Synthesis
```

संश्लेषण इकाई - अंतिम उत्तर।

**फ़ील्ड:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`document`: <class 'str'>

### विधियाँ

### `__init__(self, uri: str, entity_type: str = '', document: str = '') -> None`

स्वयं को आरंभ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।


--

## `Analysis`

```python
from trustgraph.api import Analysis
```

विश्लेषण इकाई - एक विचार/कार्य/अवलोकन चक्र (केवल एजेंट)।

**फ़ील्ड:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`action`: <class 'str'>
`arguments`: <class 'str'>
`thought`: <class 'str'>
`observation`: <class 'str'>

### विधियाँ

### `__init__(self, uri: str, entity_type: str = '', action: str = '', arguments: str = '', thought: str = '', observation: str = '') -> None`

स्वयं को आरंभ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।


--

## `Conclusion`

```python
from trustgraph.api import Conclusion
```

निष्कर्ष इकाई - अंतिम उत्तर (केवल एजेंट)।

**फ़ील्ड:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`document`: <class 'str'>

### विधियाँ

### `__init__(self, uri: str, entity_type: str = '', document: str = '') -> None`

स्वयं को आरंभ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।


--

## `EdgeSelection`

```python
from trustgraph.api import EdgeSelection
```

ग्राफआरएजी फोकस चरण से तर्क के साथ एक चयनित किनारा।

**फ़ील्ड:**

`uri`: <class 'str'>
`edge`: typing.Dict[str, str] | None
`reasoning`: <class 'str'>

### विधियाँ

### `__init__(self, uri: str, edge: Dict[str, str] | None = None, reasoning: str = '') -> None`

स्वयं को आरंभ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।


--

### `wire_triples_to_tuples(wire_triples: List[Dict[str, Any]]) -> List[Tuple[str, str, Any]]`

वायर-फॉर्मेट ट्रिपल को (s, p, o) टुपल्स में बदलें।


--

### `extract_term_value(term: Dict[str, Any]) -> Any`

एक वायर-फॉर्मेट टर्म डिक्ट से मान निकालें।


--

## `Triple`

```python
from trustgraph.api import Triple
```

आरडीएफ ट्रिपल जो एक ज्ञान ग्राफ कथन का प्रतिनिधित्व करता है।

**फ़ील्ड:**

`s`: <class 'str'>
`p`: <class 'str'>
`o`: <class 'str'>

### विधियाँ

### `__init__(self, s: str, p: str, o: str) -> None`

स्वयं को आरंभ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।


--

## `Uri`

```python
from trustgraph.api import Uri
```

str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

दिए गए ऑब्जेक्ट से एक नया स्ट्रिंग ऑब्जेक्ट बनाएं। यदि एन्कोडिंग या
त्रुटियां निर्दिष्ट हैं, तो ऑब्जेक्ट में एक डेटा बफर होना चाहिए
जिसे दिए गए एन्कोडिंग और त्रुटि हैंडलर का उपयोग करके डिकोड किया जाएगा।
अन्यथा, यह ऑब्जेक्ट.__str__() (यदि परिभाषित है) का परिणाम लौटाता है
या repr(object)।
एन्कोडिंग डिफ़ॉल्ट रूप से 'utf-8' है।
त्रुटियां डिफ़ॉल्ट रूप से 'strict' हैं।

### विधियाँ

### `is_literal(self)`

### `is_triple(self)`

### `is_uri(self)`


--

## `Literal`

```python
from trustgraph.api import Literal
```

str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

दिए गए ऑब्जेक्ट से एक नया स्ट्रिंग ऑब्जेक्ट बनाएं। यदि एन्कोडिंग या
त्रुटियां निर्दिष्ट हैं, तो ऑब्जेक्ट में एक डेटा बफर होना चाहिए
जिसे दिए गए एन्कोडिंग और त्रुटि हैंडलर का उपयोग करके डिकोड किया जाएगा।
अन्यथा, यह ऑब्जेक्ट.__str__() (यदि परिभाषित है) का परिणाम लौटाता है
या repr(object)।
एन्कोडिंग डिफ़ॉल्ट रूप से 'utf-8' है।
त्रुटियां डिफ़ॉल्ट रूप से 'strict' हैं।

### विधियाँ

### `is_literal(self)`

### `is_triple(self)`

### `is_uri(self)`


--

## `ConfigKey`

```python
from trustgraph.api import ConfigKey
```

कॉन्फ़िगरेशन कुंजी पहचानकर्ता।

**फ़ील्ड:**

`type`: <class 'str'>
`key`: <class 'str'>

### विधियाँ

### `__init__(self, type: str, key: str) -> None`

स्वयं को आरंभ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।


--

## `ConfigValue`

```python
from trustgraph.api import ConfigValue
```

कॉन्फ़िगरेशन कुंजी-मान जोड़ी।

**फ़ील्ड:**

`type`: <class 'str'>
`key`: <class 'str'>
`value`: <class 'str'>

### विधियाँ

### `__init__(self, type: str, key: str, value: str) -> None`

स्वयं को आरंभ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।


--

## `DocumentMetadata`

```python
from trustgraph.api import DocumentMetadata
```

पुस्तकालय में एक दस्तावेज़ के लिए मेटाडेटा।

**विशेषताएं:**

`parent_id: Parent document ID for child documents (empty for top`: स्तर (docs)

**फ़ील्ड:**

`id`: <class 'str'>
`time`: <class 'datetime.datetime'>
`kind`: <class 'str'>
`title`: <class 'str'>
`comments`: <class 'str'>
`metadata`: typing.List[trustgraph.api.types.Triple]
`user`: <class 'str'>
`tags`: typing.List[str]
`parent_id`: <class 'str'>
`document_type`: <class 'str'>

### विधियाँ

### `__init__(self, id: str, time: datetime.datetime, kind: str, title: str, comments: str, metadata: List[trustgraph.api.types.Triple], user: str, tags: List[str], parent_id: str = '', document_type: str = 'source') -> None`

स्वयं को आरंभ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।


--

## `ProcessingMetadata`

```python
from trustgraph.api import ProcessingMetadata
```

एक सक्रिय दस्तावेज़ प्रसंस्करण कार्य के लिए मेटाडेटा।

**फ़ील्ड:**

`id`: <class 'str'>
`document_id`: <class 'str'>
`time`: <class 'datetime.datetime'>
`flow`: <class 'str'>
`user`: <class 'str'>
`collection`: <class 'str'>
`tags`: typing.List[str]

### विधियाँ

### `__init__(self, id: str, document_id: str, time: datetime.datetime, flow: str, user: str, collection: str, tags: List[str]) -> None`

स्वयं को आरंभ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।


--

## `CollectionMetadata`

```python
from trustgraph.api import CollectionMetadata
```

डेटा संग्रह के लिए मेटाडेटा।

संग्रह दस्तावेज़ों और
ज्ञान ग्राफ डेटा के लिए तार्किक समूहीकरण और अलगाव प्रदान करते हैं।

**विशेषताएं:**

`name: Human`: पढ़ने योग्य संग्रह नाम

**फ़ील्ड:**

`user`: <class 'str'>
`collection`: <class 'str'>
`name`: <class 'str'>
`description`: <class 'str'>
`tags`: typing.List[str]

### विधियाँ

### `__init__(self, user: str, collection: str, name: str, description: str, tags: List[str]) -> None`

स्वयं को आरंभ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।


--

## `StreamingChunk`

```python
from trustgraph.api import StreamingChunk
```

स्ट्रीमिंग प्रतिक्रिया खंडों के लिए आधार वर्ग।

वेबसॉकेट-आधारित स्ट्रीमिंग कार्यों के लिए उपयोग किया जाता है, जहाँ प्रतिक्रियाएँ उत्पन्न होने पर क्रमिक रूप से भेजी जाती हैं।


**फ़ील्ड:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>

### विधियाँ

### `__init__(self, content: str, end_of_message: bool = False) -> None`

स्वयं को आरंभ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।


--

## `AgentThought`

```python
from trustgraph.api import AgentThought
```

एजेंट की तर्क/विचार प्रक्रिया का खंड।

यह एजेंट के निष्पादन के दौरान आंतरिक तर्क या योजना चरणों का प्रतिनिधित्व करता है।
ये खंड दर्शाते हैं कि एजेंट समस्या के बारे में कैसे सोच रहा है।

**फ़ील्ड:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>

### विधियाँ

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'thought') -> None`

स्वयं को आरंभ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।


--

## `AgentObservation`

```python
from trustgraph.api import AgentObservation
```

एजेंट टूल निष्पादन अवलोकन खंड।

यह किसी टूल या क्रिया को निष्पादित करने के परिणाम या अवलोकन को दर्शाता है।
ये खंड दिखाते हैं कि एजेंट ने टूल का उपयोग करके क्या सीखा।

**फ़ील्ड:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>

### विधियाँ

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'observation') -> None`

स्वयं को आरंभ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।


--

## `AgentAnswer`

```python
from trustgraph.api import AgentAnswer
```

एजेंट का अंतिम उत्तर खंड।

यह एजेंट की अंतिम प्रतिक्रिया का प्रतिनिधित्व करता है जो उपयोगकर्ता के प्रश्न का उत्तर देने के लिए
अपनी तर्क क्षमता और टूल उपयोग को पूरा करने के बाद देता है।

**विशेषताएं:**

`chunk_type: Always "final`: उत्तर"

**फ़ील्ड:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>
`end_of_dialog`: <class 'bool'>

### विधियाँ

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'final-answer', end_of_dialog: bool = False) -> None`

स्वयं को आरंभ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।


--

## `RAGChunk`

```python
from trustgraph.api import RAGChunk
```

आरएजी (रीट्रिवल-ऑगमेंटेड जनरेशन) स्ट्रीमिंग चंक।

ग्राफ आरएजी, दस्तावेज़ आरएजी, टेक्स्ट कंप्लीशन,
और अन्य जेनरेटिव सेवाओं से प्रतिक्रियाओं को स्ट्रीम करने के लिए उपयोग किया जाता है।

**फ़ील्ड:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>
`end_of_stream`: <class 'bool'>
`error`: typing.Dict[str, str] | None

### मेथड

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'rag', end_of_stream: bool = False, error: Dict[str, str] | None = None) -> None`

स्वयं को इनिशियलाइज़ करें। सटीक सिग्नेचर के लिए help(type(self)) देखें।


--

## `ProvenanceEvent`

```python
from trustgraph.api import ProvenanceEvent
```

व्याख्यात्मकता के लिए उत्पत्ति घटना।

जब व्याख्यात्मक मोड सक्षम होता है तो GraphRAG प्रश्नों के दौरान उत्सर्जित।
प्रत्येक घटना एक उत्पत्ति नोड का प्रतिनिधित्व करती है जो प्रश्न प्रसंस्करण के दौरान बनाई जाती है।

**फ़ील्ड:**

`explain_id`: <class 'str'>
`explain_graph`: <class 'str'>
`event_type`: <class 'str'>

### विधियाँ

### `__init__(self, explain_id: str, explain_graph: str = '', event_type: str = '') -> None`

स्वयं को आरंभ करें। सटीक हस्ताक्षर के लिए help(type(self)) देखें।


--

## `ProtocolException`

```python
from trustgraph.api import ProtocolException
```

जब वेबसॉकेट प्रोटोकॉल त्रुटियां होती हैं, तो यह त्रुटि उत्पन्न होती है।


--

## `TrustGraphException`

```python
from trustgraph.api import TrustGraphException
```

सभी ट्रस्टग्राफ सेवा त्रुटियों के लिए आधार वर्ग।


--

## `AgentError`

```python
from trustgraph.api import AgentError
```

एजेंट सेवा त्रुटि


--

## `ConfigError`

```python
from trustgraph.api import ConfigError
```

कॉन्फ़िगरेशन सेवा त्रुटि


--

## `DocumentRagError`

```python
from trustgraph.api import DocumentRagError
```

दस्तावेज़ पुनर्प्राप्ति त्रुटि।


--

## `FlowError`

```python
from trustgraph.api import FlowError
```

प्रवाह प्रबंधन त्रुटि


--

## `GatewayError`

```python
from trustgraph.api import GatewayError
```

एपीआई गेटवे त्रुटि


--

## `GraphRagError`

```python
from trustgraph.api import GraphRagError
```

ग्राफ आरएजी पुनर्प्राप्ति त्रुटि


--

## `LLMError`

```python
from trustgraph.api import LLMError
```

एलएलएम सेवा त्रुटि


--

## `LoadError`

```python
from trustgraph.api import LoadError
```

डेटा लोड करने में त्रुटि


--

## `LookupError`

```python
from trustgraph.api import LookupError
```

खोज/खोज त्रुटि


--

## `NLPQueryError`

```python
from trustgraph.api import NLPQueryError
```

एनएलपी क्वेरी सेवा त्रुटि


--

## `RowsQueryError`

```python
from trustgraph.api import RowsQueryError
```

पंक्तियों के क्वेरी सेवा त्रुटि


--

## `RequestError`

```python
from trustgraph.api import RequestError
```

अनुरोध प्रसंस्करण त्रुटि


--

## `StructuredQueryError`

```python
from trustgraph.api import StructuredQueryError
```

संरचित क्वेरी सेवा त्रुटि


--

## `UnexpectedError`

```python
from trustgraph.api import UnexpectedError
```

अप्रत्याशित/अज्ञात त्रुटि


--

## `ApplicationException`

```python
from trustgraph.api import ApplicationException
```

सभी ट्रस्टग्राफ सेवा त्रुटियों के लिए आधार वर्ग।


--
