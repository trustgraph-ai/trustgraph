# مرجع واجهة برمجة التطبيقات (API) الخاصة بـ TrustGraph بلغة بايثون.

## التثبيت

```bash
pip install trustgraph
```

## البدء السريع

يتم استيراد جميع الفئات والأنواع من الحزمة `trustgraph.api`:

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

## جدول المحتويات

### الأساس

[Api](#api)

### عملاء التدفق

[Flow](#flow)
[FlowInstance](#flowinstance)
[AsyncFlow](#asyncflow)
[AsyncFlowInstance](#asyncflowinstance)

### عملاء WebSocket

[SocketClient](#socketclient)
[SocketFlowInstance](#socketflowinstance)
[AsyncSocketClient](#asyncsocketclient)
[AsyncSocketFlowInstance](#asyncsocketflowinstance)

### العمليات المجمعة

[BulkClient](#bulkclient)
[AsyncBulkClient](#asyncbulkclient)

### المقاييس

[Metrics](#metrics)
[AsyncMetrics](#asyncmetrics)

### أنواع البيانات

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

### الاستثناءات

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

عميل واجهة برمجة التطبيقات (API) الرئيسي لـ TrustGraph للعمليات المتزامنة وغير المتزامنة.

توفر هذه الفئة الوصول إلى جميع خدمات TrustGraph بما في ذلك إدارة التدفق،
وعمليات الرسم البياني المعرفي، ومعالجة المستندات، واستعلامات RAG، والمزيد. وهي تدعم
أنماط الاتصال القائمة على REST والقائمة على WebSocket.

يمكن استخدام العميل كمدير سياق للتنظيف التلقائي للموارد:
    ```python
    with Api(url="http://localhost:8088/") as api:
        result = api.flow().id("default").graph_rag(query="test")
    ```

### الطرق

### `__aenter__(self)`

أدخل مدير السياق غير المتزامن.

### `__aexit__(self, *args)`

اخرج من مدير السياق غير المتزامن وأغلق الاتصالات.

### `__enter__(self)`

أدخل مدير السياق المتزامن.

### `__exit__(self, *args)`

اخرج من مدير السياق المتزامن وأغلق الاتصالات.

### `__init__(self, url='http://localhost:8088/', timeout=60, token: str | None = None)`

تهيئة عميل واجهة برمجة تطبيقات TrustGraph.

**الوسائط:**

`url`: عنوان URL الأساسي لواجهة برمجة تطبيقات TrustGraph (الافتراضي: "http://localhost:8088/"")
`timeout`: المهلة الزمنية للطلبات بالثواني (الافتراضي: 60)
`token`: رمز مميز اختياري للمصادقة

**مثال:**

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

إغلاق جميع اتصالات العميل غير المتزامنة.

تقوم هذه الطريقة بإغلاق اتصالات WebSocket غير المتزامنة، والعمليات المجمعة، واتصالات التدفق.
يتم استدعاؤها تلقائيًا عند الخروج من مدير السياق غير المتزامن.

**مثال:**

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

احصل على عميل لعمليات مجمعة غير متزامنة.

يوفر عمليات استيراد وتصدير مجمعة بنمط async/await عبر WebSocket
للتعامل بكفاءة مع مجموعات البيانات الكبيرة.

**المرتجعات:** AsyncBulkClient: عميل للعمليات المجمعة غير المتزامنة.

**مثال:**

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

احصل على عميل تدفق قائم على REST غير متزامن.

يوفر وصولاً بنمط async/await إلى عمليات التدفق. هذا هو الخيار المفضل
لتطبيقات وأطر عمل Python غير المتزامنة (FastAPI، aiohttp، إلخ).

**المرتجعات:** AsyncFlow: عميل تدفق غير متزامن

**مثال:**

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

احصل على عميل مقاييس غير متزامن.

يوفر وصولاً بنمط async/await إلى مقاييس Prometheus.

**المرتجعات:** AsyncMetrics: عميل مقاييس غير متزامن.

**مثال:**

```python
async_metrics = api.async_metrics()
prometheus_text = await async_metrics.get()
print(prometheus_text)
```

### `async_socket(self)`

احصل على عميل WebSocket غير متزامن لعمليات البث.

يوفر وصول WebSocket بنمط async/await مع دعم البث.
هذه هي الطريقة المفضلة للبث غير المتزامن في Python.

**المرتجعات:** AsyncSocketClient: عميل WebSocket غير متزامن.

**مثال:**

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

احصل على عميل لعمليات مجمعة متزامنة للاستيراد/التصدير.

تسمح العمليات المجمعة بنقل فعال لمجموعات بيانات كبيرة عبر اتصالات WebSocket، بما في ذلك الثلاثيات، والتضمينات، وسياقات الكيانات، والكائنات.

**الإرجاع:** BulkClient: عميل للعمليات المجمعة المتزامنة.

**مثال:**


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

إغلاق جميع اتصالات العملاء المتزامنة.

تقوم هذه الطريقة بإغلاق اتصالات WebSocket والعمليات المجمعة.
يتم استدعاؤها تلقائيًا عند الخروج من مدير السياق.

**مثال:**

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

احصل على عميل المجموعة لإدارة مجموعات البيانات.

تقوم المجموعات بتنظيم المستندات وبيانات الرسم البياني المعرفي في
تجمعات منطقية للعزل والتحكم في الوصول.

**الإرجاع:** Collection: عميل إدارة المجموعة.

**مثال:**

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

احصل على عميل إعدادات لتنظيم إعدادات التكوين.

**المرتجعات:** Config: عميل إدارة التكوين.

**مثال:**

```python
config = api.config()

# Get configuration values
values = config.get([ConfigKey(type="llm", key="model")])

# Set configuration
config.put([ConfigValue(type="llm", key="model", value="gpt-4")])
```

### `flow(self)`

احصل على عميل Flow لإدارة والتفاعل مع التدفقات.

التدفقات هي الوحدات الأساسية للتنفيذ في TrustGraph، وتوفر الوصول إلى
الخدمات مثل الوكلاء، واستعلامات RAG، والتضمينات، ومعالجة المستندات.

**الإرجاع:** Flow: عميل إدارة التدفق.

**مثال:**

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

احصل على عميل Knowledge لإدارة نوى الرسم البياني للمعرفة.

**المرتجعات:** عميل إدارة الرسم البياني للمعرفة: Knowledge

**مثال:**

```python
knowledge = api.knowledge()

# List available KG cores
cores = knowledge.list_kg_cores(user="trustgraph")

# Load a KG core
knowledge.load_kg_core(id="core-123", user="trustgraph")
```

### `library(self)`

احصل على عميل مكتبة لإدارة المستندات.

توفر المكتبة تخزين المستندات، وإدارة البيانات الوصفية، و
تنسيق سير العمل للمعالجة.

**المرتجعات:** Library: عميل إدارة مكتبة المستندات.

**مثال:**

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

احصل على عميل مقاييس متزامن للمراقبة.

يسترجع مقاييس بتنسيق Prometheus من خدمة TrustGraph
للمراقبة والرؤية.

**الإرجاع:** المقاييس: عميل المقاييس المتزامن

**مثال:**

```python
metrics = api.metrics()
prometheus_text = metrics.get()
print(prometheus_text)
```

### `request(self, path, request)`

إجراء طلب واجهة برمجة تطبيقات REST منخفض المستوى.

هذه الطريقة مخصصة بشكل أساسي للاستخدام الداخلي ولكن يمكن استخدامها للوصول المباشر إلى
واجهة برمجة التطبيقات عند الحاجة.

**الوسائط:**

`path`: مسار نقطة نهاية واجهة برمجة التطبيقات (بالنسبة لعنوان URL الأساسي)
`request`: حمولة الطلب كقاموس

**الإرجاع:** dict: كائن الاستجابة

**يُثير:**

`ProtocolException`: إذا لم يكن رمز حالة الاستجابة 200 أو إذا لم تكن الاستجابة بتنسيق JSON
`ApplicationException`: إذا احتوت الاستجابة على خطأ

**مثال:**

```python
response = api.request("flow", {
    "operation": "list-flows"
})
```

### `socket(self)`

احصل على عميل WebSocket متزامن لعمليات البث.

توفر اتصالات WebSocket دعمًا للبث لعمليات الاستجابة في الوقت الفعلي
من الوكلاء، واستعلامات RAG، وإكمال النصوص. تُرجع هذه الطريقة غلافًا متزامنًا
حول بروتوكول WebSocket.

**الإرجاع:** SocketClient: عميل WebSocket متزامن.

**مثال:**

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

عميل إدارة التدفق للعمليات المتعلقة بقوالب التدفق ومثيلات التدفق.

توفر هذه الفئة طرقًا لإدارة قوالب التدفق (القوالب) و
مثيلات التدفق (التدفقات قيد التشغيل). تحدد القوالب الهيكل و
معلمات التدفقات، بينما تمثل المثيلات التدفقات النشطة التي يمكن
أن تنفذ الخدمات.

### الطرق

### `__init__(self, api)`

تهيئة عميل التدفق.

**الوسائط:**

`api`: مثيل واجهة برمجة التطبيقات (API) الأب لإجراء الطلبات.

### `delete_blueprint(self, blueprint_name)`

حذف قالب تدفق.

**الوسائط:**

`blueprint_name`: اسم القالب المراد حذفه.

**مثال:**

```python
api.flow().delete_blueprint("old-blueprint")
```

### `get(self, id)`

الحصول على تعريف لمثيل عملية قيد التشغيل.

**الوسائط:**

`id`: معرف مثيل العملية

**الإرجاع:** قاموس: تعريف مثيل العملية

**مثال:**

```python
flow_def = api.flow().get("default")
print(flow_def)
```

### `get_blueprint(self, blueprint_name)`

الحصول على تعريف مخطط تدفق بالاسم.

**الوسائط:**

`blueprint_name`: اسم المخطط المراد استرجاعه.

**الإرجاع:** قاموس: تعريف المخطط كقاموس.

**مثال:**

```python
blueprint = api.flow().get_blueprint("default")
print(blueprint)  # Blueprint configuration
```

### `id(self, id='default')`

الحصول على مثيل تدفق لتنفيذ العمليات على تدفق معين.

**الوسائط:**

`id`: مُعرّف التدفق (الافتراضي: "default")

**الإرجاع:** FlowInstance: مثيل التدفق لعمليات الخدمة

**مثال:**

```python
flow = api.flow().id("my-flow")
response = flow.text_completion(
    system="You are helpful",
    prompt="Hello"
)
```

### `list(self)`

عرض جميع مثيلات التدفق النشطة.

**النتائج:** list[str]: قائمة بمعرفات مثيلات التدفق.

**مثال:**

```python
flows = api.flow().list()
print(flows)  # ['default', 'flow-1', 'flow-2', ...]
```

### `list_blueprints(self)`

عرض جميع مخططات سير العمل المتاحة.

**النتائج:** list[str]: قائمة بأسماء المخططات.

**مثال:**

```python
blueprints = api.flow().list_blueprints()
print(blueprints)  # ['default', 'custom-flow', ...]
```

### `put_blueprint(self, blueprint_name, definition)`

إنشاء أو تحديث مخطط سير العمل.

**الوسائط:**

`blueprint_name`: اسم للمخطط.
`definition`: قاموس تعريف المخطط.

**مثال:**

```python
definition = {
    "services": ["text-completion", "graph-rag"],
    "parameters": {"model": "gpt-4"}
}
api.flow().put_blueprint("my-blueprint", definition)
```

### `request(self, path=None, request=None)`

إرسال طلب واجهة برمجة تطبيقات (API) ضمن نطاق التدفق.

**الوسائط:**

`path`: لاحقة مسار اختيارية لنقاط نهاية التدفق.
`request`: قاموس حمولة الطلب.

**الإرجاع:** dict: كائن الاستجابة.

**الاستثناءات:**

`RuntimeError`: إذا لم يتم تحديد معلمة الطلب.

### `start(self, blueprint_name, id, description, parameters=None)`

بدء مثيل تدفق جديد من مخطط.

**الوسائط:**

`blueprint_name`: اسم المخطط المراد إنشاؤه.
`id`: معرف فريد لمثيل التدفق.
`description`: وصف يمكن قراءته بواسطة الإنسان.
`parameters`: قاموس اختياري للمعلمات.

**مثال:**

```python
api.flow().start(
    blueprint_name="default",
    id="my-flow",
    description="My custom flow",
    parameters={"model": "gpt-4"}
)
```

### `stop(self, id)`

إيقاف مثيل تدفق قيد التشغيل.

**الوسائط:**

`id`: معرف مثيل التدفق الذي سيتم إيقافه.

**مثال:**

```python
api.flow().stop("my-flow")
```


--

## `FlowInstance`

```python
from trustgraph.api import FlowInstance
```

عميل مثيل التدفق لتنفيذ الخدمات في تدفق معين.

توفر هذه الفئة الوصول إلى جميع خدمات TrustGraph بما في ذلك:
إكمال النص والتضمينات.
عمليات الوكيل مع إدارة الحالة.
استعلامات Graph و RAG للوثائق.
عمليات الرسم البياني المعرفي (ثلاثيات، كائنات).
تحميل الوثائق ومعالجتها.
تحويل اللغة الطبيعية إلى استعلام GraphQL.
تحليل البيانات المنظمة واكتشاف المخطط.
تنفيذ أداة MCP.
قالب المطالبات.

يتم الوصول إلى الخدمات من خلال مثيل تدفق قيد التشغيل يتم تحديده بواسطة معرّف.

### الطرق

### `__init__(self, api, id)`

تهيئة FlowInstance.

**الوسائط:**

`api`: عميل التدفق الرئيسي.
`id`: معرّف مثيل التدفق.

### `agent(self, question, user='trustgraph', state=None, group=None, history=None)`

تنفيذ عملية وكيل مع قدرات الاستدلال واستخدام الأدوات.

يمكن للوكلاء إجراء استدلال متعدد الخطوات، واستخدام الأدوات، والحفاظ على حالة المحادثة
عبر التفاعلات. هذه نسخة متزامنة وغير متدفقة.

**الوسائط:**

`question`: سؤال المستخدم أو التعليمات.
`user`: معرف المستخدم (افتراضي: "trustgraph").
`state`: قاموس حالة اختياري للمحادثات التي تحتفظ بالحالة.
`group`: معرف مجموعة اختياري للسياقات متعددة المستخدمين.
`history`: سجل محادثة اختياري كقائمة من قواميس الرسائل.

**الإرجاع:** str: إجابة الوكيل النهائية.

**مثال:**

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

اكتشاف نوع البيانات لعينة بيانات منظمة.

**الوسائط:**

`sample`: عينة البيانات المراد تحليلها (محتوى نصي)

**النتائج:** قاموس يحتوي على detected_type و confidence و بيانات وصفية اختيارية.

### `diagnose_data(self, sample, schema_name=None, options=None)`

إجراء تشخيص بيانات مدمج: اكتشاف النوع وإنشاء وصف.

**الوسائط:**

`sample`: عينة البيانات المراد تحليلها (محتوى نصي)
`schema_name`: اسم المخطط المستهدف الاختياري لإنشاء الوصف.
`options`: معلمات اختيارية (مثل فاصل CSV).

**النتائج:** قاموس يحتوي على detected_type و confidence و descriptor و بيانات وصفية.

### `document_embeddings_query(self, text, user, collection, limit=10)`

الاستعلام عن أجزاء المستندات باستخدام التشابه الدلالي.

يجد أجزاء المستندات التي يكون محتوىها متشابهًا دلاليًا مع
النص المدخل، باستخدام تضمينات المتجهات.

**الوسائط:**

`text`: نص الاستعلام للبحث الدلالي.
`user`: معرف المستخدم/المساحة.
`collection`: معرف المجموعة.
`limit`: الحد الأقصى لعدد النتائج (افتراضي: 10).

**النتائج:** قاموس: نتائج الاستعلام مع الأجزاء التي تحتوي على chunk_id و score.

**مثال:**

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

تنفيذ استعلام استرجاع مُعزز بالبيانات (RAG) يعتمد على المستندات.

يستخدم استرجاع البيانات المُعزز بالبيانات (RAG) تضمينات المتجهات للعثور على أجزاء المستندات ذات الصلة،
ثم يقوم بإنشاء استجابة باستخدام نموذج لغوي كبير (LLM) مع استخدام تلك الأجزاء كسياق.

**الوسائط:**

`query`: استعلام بلغة طبيعية.
`user`: مُعرّف المستخدم/مساحة المفاتيح (الافتراضي: "trustgraph").
`collection`: مُعرّف المجموعة (الافتراضي: "default").
`doc_limit`: الحد الأقصى لعدد أجزاء المستندات التي سيتم استرجاعها (الافتراضي: 10).

**الإرجاع:** str: الاستجابة التي تم إنشاؤها والتي تتضمن سياق المستند.

**مثال:**

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

توليد تضمينات متجهة لنص أو أكثر.

تحويل النصوص إلى تمثيلات متجهة كثيفة مناسبة للبحث الدلالي
ومقارنة التشابه.

**الوسائط:**

`texts`: قائمة بالنصوص المدخلة المراد تضمينها.

**النتائج:** list[list[list[float]]]: تضمينات متجهة، مجموعة واحدة لكل نص مدخل.

**مثال:**

```python
flow = api.flow().id("default")
vectors = flow.embeddings(["quantum computing"])
print(f"Embedding dimension: {len(vectors[0][0])}")
```

### `generate_descriptor(self, sample, data_type, schema_name, options=None)`

إنشاء وصف لربط البيانات المهيكلة بمخطط معين.

**الوسائط:**

`sample`: عينة البيانات لتحليلها (محتوى نصي)
`data_type`: نوع البيانات (csv، json، xml)
`schema_name`: اسم المخطط المستهدف لإنشاء الوصف
`options`: معلمات اختيارية (مثل فاصل CSV)

**الإرجاع:** قاموس يحتوي على الوصف والبيانات الوصفية

### `graph_embeddings_query(self, text, user, collection, limit=10)`

الاستعلام عن كيانات الرسم البياني المعرفي باستخدام التشابه الدلالي.

يجد الكيانات في الرسم البياني المعرفي والتي تكون أوصافها متشابهة دلاليًا
مع النص المدخل، باستخدام تضمينات المتجهات.

**الوسائط:**

`text`: نص الاستعلام للبحث الدلالي
`user`: معرف المستخدم/المساحة
`collection`: معرف المجموعة
`limit`: الحد الأقصى لعدد النتائج (افتراضي: 10)

**الإرجاع:** قاموس: نتائج الاستعلام مع الكيانات المشابهة

**مثال:**

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

تنفيذ استعلام يعتمد على الرسم البياني لإنشاء استجابات مُعززة بالاسترجاع (RAG).

يستخدم الرسم البياني RAG هيكل الرسم البياني للمعرفة للعثور على السياق ذي الصلة من خلال
استكشاف علاقات الكيانات، ثم يقوم بإنشاء استجابة باستخدام نموذج لغوي كبير (LLM).

**الوسائط:**

`query`: استعلام بلغة طبيعية.
`user`: مُعرّف المستخدم/مساحة المفاتيح (الافتراضي: "trustgraph").
`collection`: مُعرّف المجموعة (الافتراضي: "default").
`entity_limit`: الحد الأقصى للكيانات التي سيتم استرجاعها (الافتراضي: 50).
`triple_limit`: الحد الأقصى للثلاثيات لكل كيان (الافتراضي: 30).
`max_subgraph_size`: الحد الأقصى لإجمالي عدد الثلاثيات في الرسم البياني الفرعي (الافتراضي: 150).
`max_path_length`: الحد الأقصى لعمق الاستكشاف (الافتراضي: 2).

**الإرجاع:** str: الاستجابة التي تم إنشاؤها والتي تتضمن سياق الرسم البياني.

**مثال:**

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

تحميل مستند ثنائي للمعالجة.

تحميل مستند (PDF، DOCX، صور، إلخ) لاستخراج ومعالجة
من خلال مسار المستند الخاص بالتدفق.

**الوسائط:**

`document`: محتوى المستند كبايت.
`id`: مُعرّف المستند الاختياري (يتم إنشاؤه تلقائيًا إذا كان فارغًا).
`metadata`: بيانات وصفية اختيارية (قائمة من الثلاثيات أو كائن مع طريقة الإرسال).
`user`: مُعرّف المستخدم/مساحة المفاتيح (اختياري).
`collection`: مُعرّف المجموعة (اختياري).

**الإرجاع:** قاموس: استجابة المعالجة.

**يُثير:**

`RuntimeError`: إذا تم توفير البيانات الوصفية بدون مُعرّف.

**مثال:**

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

تحميل محتوى نصي للمعالجة.

تحميل محتوى نصي لاستخلاصه ومعالجته من خلال مسار المعالجة النصية.


**الوسائط:**

`text`: محتوى نصي كبايت.
`id`: مُعرّف المستند الاختياري (يتم إنشاؤه تلقائيًا إذا كان فارغًا).
`metadata`: بيانات وصفية اختيارية (قائمة من الثلاثيات أو كائن مع طريقة الإرسال).
`charset`: ترميز الأحرف (افتراضي: "utf-8").
`user`: مُعرّف المستخدم/مساحة المفاتيح (اختياري).
`collection`: مُعرّف المجموعة (اختياري).

**الإرجاع:** قاموس: استجابة المعالجة.

**الأخطاء:**

`RuntimeError`: إذا تم توفير البيانات الوصفية بدون مُعرّف.

**مثال:**

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

تنفيذ أداة بروتوكول سياق النموذج (MCP).

توفر أدوات MCP وظائف قابلة للتوسيع للوكلاء وسير العمل،
مما يسمح بالتكامل مع الأنظمة والخدمات الخارجية.

**الوسائط:**

`name`: اسم/معرّف الأداة.
`parameters`: قاموس معلمات الأداة (الافتراضي: {}).

**الإرجاع:** str أو dict: نتيجة تنفيذ الأداة.

**يُثير:**

`ProtocolException`: إذا كان تنسيق الاستجابة غير صالح.

**مثال:**

```python
flow = api.flow().id("default")

# Execute a tool
result = flow.mcp_tool(
    name="search-web",
    parameters={"query": "latest AI news", "limit": 5}
)
```

### `nlp_query(self, question, max_results=100)`

تحويل سؤال بلغة طبيعية إلى استعلام GraphQL.

**الوسائط:**

`question`: سؤال بلغة طبيعية
`max_results`: الحد الأقصى لعدد النتائج المراد إرجاعها (افتراضي: 100)

**الإرجاع:** قاموس يحتوي على graphql_query و variables و detected_schemas و confidence

### `prompt(self, id, variables)`

تنفيذ نموذج مطالبة مع استبدال المتغيرات.

تسمح نماذج المطالبات بأنماط مطالبات قابلة لإعادة الاستخدام مع متغيرات ديناميكية
استبدال، وهو مفيد لهندسة المطالبات المتسقة.

**الوسائط:**

`id`: معرف نموذج المطالبة
`variables`: قاموس لتعيين اسم المتغير إلى القيمة

**الإرجاع:** سلسلة أو قاموس: نتيجة المطالبة المعروضة (نص أو كائن منظم)

**يسبب:**

`ProtocolException`: إذا كان تنسيق الاستجابة غير صالح

**مثال:**

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

قم بإنشاء طلب خدمة في هذه نسخة التدفق.

**الوسائط:**

`path`: مسار الخدمة (مثل: "service/text-completion")
`request`: قاموس حمولة الطلب

**الإرجاع:** dict: استجابة الخدمة

### `row_embeddings_query(self, text, schema_name, user='trustgraph', collection='default', index_name=None, limit=10)`

استعلام عن بيانات الصفوف باستخدام التشابه الدلالي في الحقول المفهرسة.

يجد الصفوف التي تكون فيها قيم الحقول المفهرسة متشابهة دلاليًا مع
النص المدخل، باستخدام تضمينات المتجهات. هذا يتيح المطابقة التقريبية/الدلالية
على البيانات المنظمة.

**الوسائط:**

`text`: نص الاستعلام للبحث الدلالي
`schema_name`: اسم المخطط للبحث داخله
`user`: معرف المستخدم/مساحة المفاتيح (افتراضي: "trustgraph")
`collection`: معرف المجموعة (افتراضي: "default")
`index_name`: اسم الفهرس الاختياري لتصفية البحث في فهرس معين
`limit`: الحد الأقصى لعدد النتائج (افتراضي: 10)

**الإرجاع:** dict: نتائج الاستعلام مع المطابقات التي تحتوي على index_name و index_value و text و score

**مثال:**

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

تنفيذ استعلام GraphQL مقابل الصفوف المنظمة في الرسم البياني المعرفي.

الاستعلام عن البيانات المنظمة باستخدام بناء جملة GraphQL، مما يسمح باستعلامات معقدة
مع التصفية والتجميع وتجاوز العلاقات.

**الوسائط:**

`query`: سلسلة استعلام GraphQL
`user`: معرف المستخدم/مساحة الاسم (الافتراضي: "trustgraph")
`collection`: معرف المجموعة (الافتراضي: "default")
`variables`: قاموس اختياري لمتغيرات الاستعلام
`operation_name`: اسم عملية اختياري للمستندات متعددة العمليات

**الإرجاع:** dict: استجابة GraphQL مع حقول 'data' و 'errors' و/أو 'extensions'

**يثير:**

`ProtocolException`: إذا حدث خطأ على مستوى النظام

**مثال:**

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

تحديد مخططات مطابقة لعينة بيانات باستخدام تحليل المطالبات.

**الوسائط:**

`sample`: عينة البيانات المراد تحليلها (محتوى نصي)
`options`: معلمات اختيارية

**الإرجاع:** قاموس يحتوي على مصفوفة schema_matches والبيانات الوصفية.

### `structured_query(self, question, user='trustgraph', collection='default')`

تنفيذ سؤال بلغة طبيعية مقابل بيانات منظمة.
يجمع بين تحويل استعلام معالجة اللغة الطبيعية وتنفيذ GraphQL.

**الوسائط:**

`question`: سؤال بلغة طبيعية
`user`: معرف مساحة مفاتيح Cassandra (افتراضي: "trustgraph")
`collection`: معرف مجموعة البيانات (افتراضي: "default")

**الإرجاع:** قاموس يحتوي على البيانات والأخطاء الاختيارية.

### `text_completion(self, system, prompt)`

تنفيذ إكمال نص باستخدام نموذج اللغة الكبير (LLM) الخاص بالتدفق.

**الوسائط:**

`system`: مطالبة النظام التي تحدد سلوك المساعد
`prompt`: مطالبة المستخدم/سؤال

**الإرجاع:** نص: النص الذي تم إنشاؤه.

**مثال:**

```python
flow = api.flow().id("default")
response = flow.text_completion(
    system="You are a helpful assistant",
    prompt="What is quantum computing?"
)
print(response)
```

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=10000)`

البحث في ثلاثيات الرسم البياني المعرفي باستخدام مطابقة الأنماط.

تبحث عن ثلاثيات RDF تتطابق مع الموضوع والفاعل والمفعول به المحددة. تعمل المعلمات غير المحددة كرموز بدل.


**الوسائط:**

`s`: معرف الموضوع (اختياري، استخدم None للرمز بدل)
`p`: معرف الفاعل (اختياري، استخدم None للرمز بدل)
`o`: معرف المفعول به أو حرفي (اختياري، استخدم None للرمز بدل)
`user`: معرف المستخدم/مساحة المفاتيح (اختياري)
`collection`: معرف المجموعة (اختياري)
`limit`: الحد الأقصى للنتائج المراد إرجاعها (افتراضي: 10000)

**الإرجاع:** list[Triple]: قائمة بكائنات Triple المطابقة

**يسبب أخطاء:**

`RuntimeError`: إذا كان s أو p ليس Uri، أو o ليس Uri/Literal

**مثال:**

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

عميل إدارة التدفق غير المتزامن باستخدام واجهة برمجة تطبيقات REST.

يوفر عمليات إدارة التدفق المستندة إلى `async/await` بما في ذلك عمليات القائمة،
والبدء، والإيقاف، وإدارة تعريفات فئات التدفق. كما يوفر
الوصول إلى الخدمات الخاصة بنطاق التدفق مثل الوكلاء، وRAG، والاستعلامات عبر نقاط نهاية REST غير متدفقة.


ملاحظة: للحصول على دعم التدفق، استخدم `AsyncSocketClient` بدلاً من ذلك.

### الطرق

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

تهيئة عميل التدفق غير المتزامن.

**الوسائط:**

`url`: عنوان URL الأساسي لواجهة برمجة تطبيقات TrustGraph.
`timeout`: المهلة المطلوبة بالثواني.
`token`: رمز مميز اختياري للمصادقة.

### `aclose(self) -> None`

إغلاق العميل غير المتزامن وتنظيف الموارد.

ملاحظة: يتم التعامل مع التنظيف تلقائيًا بواسطة مديري سياق جلسة `aiohttp`.
تم توفير هذه الطريقة لضمان الاتساق مع العملاء غير المتزامنين الآخرين.

### `delete_class(self, class_name: str)`

حذف تعريف فئة تدفق.

يزيل مخطط فئة التدفق من النظام. لا يؤثر على
مثيلات التدفق قيد التشغيل.

**الوسائط:**

`class_name`: اسم فئة التدفق المراد حذفها.

**مثال:**

```python
async_flow = await api.async_flow()

# Delete a flow class
await async_flow.delete_class("old-flow-class")
```

### `get(self, id: str) -> Dict[str, Any]`

الحصول على تعريف التدفق.

يسترجع التكوين الكامل للتدفق بما في ذلك اسم الفئة الخاص به،
والوصف، والمعلمات.

**الوسائط:**

`id`: مُعرّف التدفق

**الإرجاع:** dict: كائن تعريف التدفق

**مثال:**

```python
async_flow = await api.async_flow()

# Get flow definition
flow_def = await async_flow.get("default")
print(f"Flow class: {flow_def.get('class-name')}")
print(f"Description: {flow_def.get('description')}")
```

### `get_class(self, class_name: str) -> Dict[str, Any]`

الحصول على تعريف الفئة التدفق.

يسترجع تعريف النموذج لفئة التدفق، بما في ذلك
مخطط التكوين وارتباطات الخدمة.

**الوسائط:**

`class_name`: اسم فئة التدفق

**الإرجاع:** dict: كائن تعريف فئة التدفق

**مثال:**

```python
async_flow = await api.async_flow()

# Get flow class definition
class_def = await async_flow.get_class("default")
print(f"Services: {class_def.get('services')}")
```

### `id(self, flow_id: str)`

احصل على مثيل عميل التدفق غير المتزامن.

يُرجع عميلاً للتفاعل مع خدمات تدفق معين (وكيل، واسترجاع المعلومات، والاستعلامات، والتضمينات، إلخ).


**الوسائط:**

`flow_id`: مُعرّف التدفق

**الإرجاع:** AsyncFlowInstance: عميل للعمليات الخاصة بالتدفق

**مثال:**

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

قم بإدراج جميع معرفات التدفق.

يسترجع معرفات جميع التدفقات المنشورة حاليًا في النظام.

**الإرجاع:** list[str]: قائمة بمعرفات التدفق.

**مثال:**

```python
async_flow = await api.async_flow()

# List all flows
flows = await async_flow.list()
print(f"Available flows: {flows}")
```

### `list_classes(self) -> List[str]`

قم بإدراج جميع أسماء فئات التدفق.

يسترجع أسماء جميع فئات التدفق (القوالب) المتاحة في النظام.

**الإرجاع:** list[str]: قائمة بأسماء فئات التدفق.

**مثال:**

```python
async_flow = await api.async_flow()

# List available flow classes
classes = await async_flow.list_classes()
print(f"Available flow classes: {classes}")
```

### `put_class(self, class_name: str, definition: Dict[str, Any])`

إنشاء أو تحديث تعريف لفئة التدفق.

يخزن مخططًا لفئة التدفق يمكن استخدامه لإنشاء مثيلات التدفق.

**الوسائط:**

`class_name`: اسم فئة التدفق
`definition`: كائن تعريف فئة التدفق

**مثال:**

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

إرسال طلب HTTP POST غير متزامن إلى واجهة برمجة التطبيقات (API) الخاصة بالبوابة.

طريقة داخلية لإجراء طلبات مصادقة إلى واجهة برمجة التطبيقات (API) الخاصة بـ TrustGraph.

**الوسائط:**

`path`: مسار نقطة نهاية واجهة برمجة التطبيقات (API) (بالنسبة إلى عنوان URL الأساسي).
`request_data`: قاموس حمولة الطلب.

**الإرجاع:** dict: كائن الاستجابة من واجهة برمجة التطبيقات (API).

**يُصدر:**

`ProtocolException`: إذا كان رمز حالة HTTP ليس 200 أو إذا كانت الاستجابة ليست JSON صالحة.
`ApplicationException`: إذا أرجع الـ API استجابة خطأ.

### `start(self, class_name: str, id: str, description: str, parameters: Dict | None = None)`

ابدأ نسخة جديدة من التدفق.

ينشئ ويبدأ تدفقًا من تعريف فئة التدفق مع المعلمات المحددة.


**الوسائط:**

`class_name`: اسم فئة التدفق المراد إنشاؤه.
`id`: معرف للنسخة الجديدة من التدفق.
`description`: وصف قابل للقراءة البشرية للتدفق.
`parameters`: معلمات تكوين اختيارية للتدفق.

**مثال:**

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

إيقاف عملية جارية.

يوقف ويحذف نسخة من العملية، ويحرر مواردها.

**الوسائط:**

`id`: مُعرّف العملية المراد إيقافها.

**مثال:**

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

عميل مثيل التدفق غير المتزامن.

يوفر الوصول إلى الخدمات ذات النطاق التدريجي باستخدام آليات المزامنة (async/await)، بما في ذلك الوكلاء،
واستعلامات RAG، والتضمينات، واستعلامات الرسم البياني. تُرجع جميع العمليات استجابات كاملة (غير متدفقة).


ملاحظة: للحصول على دعم التدفق، استخدم AsyncSocketFlowInstance بدلاً من ذلك.

### الطرق

### `__init__(self, flow: trustgraph.api.async_flow.AsyncFlow, flow_id: str)`

تهيئة مثيل التدفق غير المتزامن.

**الوسائط:**

`flow`: عميل التدفق غير المتزامن الرئيسي.
`flow_id`: معرف التدفق.

### `agent(self, question: str, user: str, state: Dict | None = None, group: str | None = None, history: List | None = None, **kwargs: Any) -> Dict[str, Any]`

تنفيذ عملية وكيل (غير متدفقة).

يقوم بتشغيل وكيل للإجابة على سؤال، مع حالة محادثة وسجل اختياري. تُرجع الاستجابة الكاملة بعد انتهاء الوكيل من
المعالجة.


ملاحظة: لا تدعم هذه الطريقة التدفق. للحصول على أفكار وملاحظات الوكيل في الوقت الفعلي، استخدم AsyncSocketFlowInstance.agent() بدلاً من ذلك.


**الوسائط:**

`question`: سؤال المستخدم أو التعليمات.
`user`: معرف المستخدم.
`state`: قاموس حالة اختياري لسياق المحادثة.
`group`: معرف مجموعة اختياري لإدارة الجلسة.
`history`: قائمة سجل المحادثة الاختيارية.
`**kwargs`: معلمات إضافية خاصة بالخدمة.

**الإرجاع:** dict: استجابة الوكيل الكاملة بما في ذلك الإجابة والبيانات الوصفية.

**مثال:**

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

تنفيذ استعلام RAG المستند إلى المستندات (غير متدفق).

يقوم بتنفيذ توليد معزز بالاسترجاع باستخدام تضمينات المستندات.
يسترجع أجزاء المستندات ذات الصلة من خلال البحث الدلالي، ثم يقوم بإنشاء
استجابة تستند إلى المستندات المسترجعة. يُرجع الاستجابة الكاملة.

ملاحظة: لا تدعم هذه الطريقة التدفق. للاستجابات المتدفقة لـ RAG،
استخدم AsyncSocketFlowInstance.document_rag() بدلاً من ذلك.

**الوسائط:**

`query`: نص استعلام المستخدم.
`user`: معرف المستخدم.
`collection`: معرف المجموعة التي تحتوي على المستندات.
`doc_limit`: الحد الأقصى لعدد أجزاء المستندات التي سيتم استرجاعها (افتراضي: 10).
`**kwargs`: معلمات إضافية خاصة بالخدمة.

**الإرجاع:** str: الاستجابة الكاملة التي تم إنشاؤها والتي تستند إلى بيانات المستند.

**مثال:**

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

توليد تضمينات للنصوص المدخلة.

تحويل النصوص إلى تمثيلات متجهة رقمية باستخدام نموذج التضمين المُكوّن في التدفق.
مفيد للبحث الدلالي ومقارنات التشابه.


**الوسائط:**

`texts`: قائمة بالنصوص المدخلة المراد تضمينها.
`**kwargs`: معلمات إضافية خاصة بالخدمة.

**الإرجاع:** dict: استجابة تحتوي على متجهات التضمين.

**مثال:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Generate embeddings
result = await flow.embeddings(texts=["Sample text to embed"])
vectors = result.get("vectors")
print(f"Embedding dimension: {len(vectors[0][0])}")
```

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any)`

البحث عن تضمينات الرسم البياني للاستعلام عن الكيانات الدلالية.

يقوم بإجراء بحث دلالي عبر تضمينات الكيانات في الرسم البياني للعثور على الكيانات
الأكثر صلة بالنص المدخل. يُرجع الكيانات مرتبة حسب التشابه.

**الوسائط:**

`text`: نص الاستعلام للبحث الدلالي
`user`: معرف المستخدم
`collection`: معرف المجموعة التي تحتوي على تضمينات الرسم البياني
`limit`: الحد الأقصى لعدد النتائج المراد إرجاعها (افتراضي: 10)
`**kwargs`: معلمات إضافية خاصة بالخدمة

**الإرجاع:** dict: استجابة تحتوي على تطابقات الكيانات المرتبة مع درجات التشابه

**مثال:**

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

تنفيذ استعلام RAG المستند إلى الرسم البياني (غير متدفق).

يقوم بتنفيذ توليد مُعزز بالاسترجاع باستخدام بيانات الرسم البياني المعرفي.
يحدد الكيانات ذات الصلة وعلاقاتها، ثم يقوم بإنشاء
استجابة تستند إلى هيكل الرسم البياني. يُرجع الاستجابة الكاملة.

ملاحظة: لا تدعم هذه الطريقة التدفق. للاستجابات المتدفقة لـ RAG،
استخدم AsyncSocketFlowInstance.graph_rag() بدلاً من ذلك.

**الوسائط:**

`query`: نص استعلام المستخدم.
`user`: مُعرّف المستخدم.
`collection`: مُعرّف المجموعة التي تحتوي على الرسم البياني المعرفي.
`max_subgraph_size`: الحد الأقصى لعدد الثلاثيات لكل رسم بياني فرعي (افتراضي: 1000).
`max_subgraph_count`: الحد الأقصى لعدد الرسوم البيانية الفرعية المراد استرجاعها (افتراضي: 5).
`max_entity_distance`: أقصى مسافة للرسم البياني لتوسيع الكيانات (افتراضي: 3).
`**kwargs`: معلمات إضافية خاصة بالخدمة.

**الإرجاع:** str: الاستجابة الكاملة التي تم إنشاؤها والتي تستند إلى بيانات الرسم البياني.

**مثال:**

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

إرسال طلب إلى خدمة ذات نطاق محدد.

طريقة داخلية لاستدعاء الخدمات داخل مثيل التدفق هذا.

**الوسائط:**

`service`: اسم الخدمة (مثل، "agent"، "graph-rag"، "triples")
`request_data`: حمولة طلب الخدمة

**الإرجاع:** dict: كائن استجابة الخدمة

**يُصدر:**

`ProtocolException`: إذا فشل الطلب أو كانت الاستجابة غير صالحة
`ApplicationException`: إذا أرجعت الخدمة خطأ

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs: Any)`

الاستعلام عن تضمينات الصفوف للبحث الدلالي عن البيانات المهيكلة.

يقوم بإجراء بحث دلالي عبر تضمينات فهرس الصفوف للعثور على الصفوف التي
تكون قيم الحقول المفهرسة فيها الأكثر تشابهًا مع النص المدخل. يتيح
المطابقة التقريبية/الدلالية على البيانات المهيكلة.

**الوسائط:**

`text`: نص الاستعلام للبحث الدلالي
`schema_name`: اسم المخطط للبحث داخله
`user`: معرف المستخدم (افتراضي: "trustgraph")
`collection`: معرف المجموعة (افتراضي: "default")
`index_name`: اسم الفهرس الاختياري لتصفية البحث في فهرس معين
`limit`: الحد الأقصى لعدد النتائج المراد إرجاعها (افتراضي: 10)
`**kwargs`: معلمات إضافية خاصة بالخدمة

**الإرجاع:** dict: استجابة تحتوي على التطابقات مع index_name و index_value و text و score

**مثال:**

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

تنفيذ استعلام GraphQL على الصفوف المخزنة.

تستخدم الاستعلامات صفوف البيانات المهيكلة باستخدام بناء جملة GraphQL. تدعم الاستعلامات المعقدة
مع المتغيرات والعمليات المسماة.

**الوسائط:**

`query`: سلسلة استعلام GraphQL
`user`: معرف المستخدم
`collection`: معرف المجموعة التي تحتوي على الصفوف
`variables`: متغيرات استعلام GraphQL اختيارية
`operation_name`: اسم العملية الاختياري للاستعلامات متعددة العمليات
`**kwargs`: معلمات إضافية خاصة بالخدمة

**الإرجاع:** dict: استجابة GraphQL مع البيانات و/أو الأخطاء

**مثال:**

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

توليد إكمال النص (غير متدفق).

يقوم بإنشاء استجابة نصية من نموذج لغوي كبير (LLM) بناءً على موجه النظام وموجه المستخدم.
يُرجع النص الكامل للاستجابة.

ملاحظة: هذه الطريقة لا تدعم التدفق. لتوليد النص المتدفق،
استخدم AsyncSocketFlowInstance.text_completion() بدلاً من ذلك.

**الوسائط:**

`system`: موجه النظام الذي يحدد سلوك نموذج اللغة الكبير.
`prompt`: موجه المستخدم أو السؤال.
`**kwargs`: معلمات إضافية خاصة بالخدمة.

**الإرجاع:** str: النص الكامل للاستجابة التي تم إنشاؤها.

**مثال:**

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

الاستعلام عن ثلاثيات RDF باستخدام مطابقة الأنماط.

تبحث عن ثلاثيات تتطابق مع الموضوع والفاعل والمفعول به المحددة. تستخدم الأنماط "None" كحرف بدل لمطابقة أي قيمة.


**الوسائط:**

`s`: نمط الموضوع (None للجميع)
`p`: نمط الفاعل (None للجميع)
`o`: نمط المفعول به (None للجميع)
`user`: معرف المستخدم (None لجميع المستخدمين)
`collection`: معرف المجموعة (None لجميع المجموعات)
`limit`: الحد الأقصى لعدد الثلاثيات المراد إرجاعها (الافتراضي: 100)
`**kwargs`: معلمات إضافية خاصة بالخدمة

**الإرجاع:** dict: استجابة تحتوي على الثلاثيات المتطابقة

**مثال:**

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

عميل WebSocket متزامن لعمليات البث.

يوفر واجهة متزامنة لخدمات TrustGraph القائمة على WebSocket،
مع تغليف مكتبة WebSocket غير المتزامنة باستخدام مولدات متزامنة لسهولة الاستخدام.
يدعم عمليات البث من الوكلاء، واستعلامات RAG، وإكمال النصوص.

ملاحظة: هذا هو غلاف متزامن لعمليات WebSocket غير المتزامنة. للحصول على دعم غير متزامن حقيقي، استخدم AsyncSocketClient بدلاً من ذلك.

### الطرق


### `__init__(self, url: str, timeout: int, token: str | None) -> None`

تهيئة عميل WebSocket متزامن.

**الوسائط:**

`url`: عنوان URL الأساسي لواجهة برمجة تطبيقات TrustGraph (سيتم تحويل HTTP/HTTPS إلى WS/WSS).
`timeout`: مهلة WebSocket بالثواني.
`token`: رمز مميز اختياري للمصادقة.

### `close(self) -> None`

إغلاق اتصالات WebSocket.

ملاحظة: تتم معالجة التنظيف تلقائيًا بواسطة مديري السياق في التعليمات البرمجية غير المتزامنة.

### `flow(self, flow_id: str) -> 'SocketFlowInstance'`

الحصول على مثيل تدفق لعمليات بث WebSocket.

**الوسائط:**

`flow_id`: معرف التدفق.

**الإرجاع:** SocketFlowInstance: مثيل التدفق مع طرق البث.

**مثال:**

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

مثال على تدفق WebSocket المتزامن لعمليات البث.

يوفر نفس الواجهة مثل FlowInstance الخاص بـ REST ولكنه يدعم
بثًا يعتمد على WebSocket للاستجابات في الوقت الفعلي. تدعم جميع الطرق معلمة اختيارية
`streaming` لتمكين تسليم النتائج التدريجي.

### الطرق

### `__init__(self, client: trustgraph.api.socket_client.SocketClient, flow_id: str) -> None`

تهيئة مثيل تدفق المقبس.

**الوسائط:**

`client`: عميل المقبس الأبوي.
`flow_id`: معرف التدفق.

### `agent(self, question: str, user: str, state: Dict[str, Any] | None = None, group: str | None = None, history: List[Dict[str, Any]] | None = None, streaming: bool = False, **kwargs: Any) -> Dict[str, Any] | Iterator[trustgraph.api.types.StreamingChunk]`

تنفيذ عملية وكيل مع دعم البث.

يمكن للوكلاء إجراء عمليات استدلال متعددة الخطوات مع استخدام الأدوات. تقوم هذه الطريقة دائمًا
بإرجاع أجزاء البث (الأفكار والملاحظات والإجابات) حتى عندما
يكون streaming=False، لإظهار عملية تفكير الوكيل.

**الوسائط:**

`question`: سؤال المستخدم أو التعليمات.
`user`: معرف المستخدم.
`state`: قاموس حالة اختياري للمحادثات التي تعتمد على الحالة.
`group`: معرف مجموعة اختياري للسياقات متعددة المستخدمين.
`history`: سجل محادثة اختياري كقائمة من قواميس الرسائل.
`streaming`: تمكين وضع البث (افتراضي: False).
`**kwargs`: معلمات إضافية يتم تمريرها إلى خدمة الوكيل.

**الإرجاع:** Iterator[StreamingChunk]: سلسلة من أفكار الوكيل وملاحظاته وإجاباته.

**مثال:**

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

تنفيذ عملية وكيل مع دعم الشفافية.

يقوم بإرسال كل من أجزاء المحتوى (أفكار الوكيل، ملاحظات الوكيل، إجابات الوكيل)
وأحداث المصدر (ProvenanceEvent). تحتوي أحداث المصدر على عناوين URI
يمكن استردادها باستخدام ExplainabilityClient للحصول على معلومات تفصيلية
حول عملية تفكير الوكيل.

يتكون تتبع الوكيل من:
الجلسة: السؤال الأولي وبيانات تعريف الجلسة.
التكرارات: كل دورة من الأفكار/الإجراءات/الملاحظات.
الاستنتاج: الإجابة النهائية.

**الوسائط:**

`question`: سؤال المستخدم أو التعليمات.
`user`: معرف المستخدم.
`collection`: معرف المجموعة لتخزين المصادر.
`state`: قاموس حالة اختياري للمحادثات التي تعتمد على الحالة.
`group`: معرف المجموعة الاختياري للسياقات متعددة المستخدمين.
`history`: سجل المحادثة الاختياري كقائمة من قواميس الرسائل.
`**kwargs`: معلمات إضافية يتم تمريرها إلى خدمة الوكيل.
`Yields`: 
`Union[StreamingChunk, ProvenanceEvent]`: أجزاء الوكيل وأحداث المصدر.

**مثال:**

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

الاستعلام عن أجزاء المستندات باستخدام التشابه الدلالي.

**الوسائط:**

`text`: نص الاستعلام للبحث الدلالي
`user`: معرف المستخدم/مساحة المفاتيح
`collection`: معرف المجموعة
`limit`: الحد الأقصى لعدد النتائج (افتراضي: 10)
`**kwargs`: معلمات إضافية يتم تمريرها إلى الخدمة

**الإرجاع:** قاموس: نتائج الاستعلام مع معرفات الأجزاء لأجزاء المستندات المطابقة

**مثال:**

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

تنفيذ استعلام RAG يعتمد على المستندات مع خيار التدفق.

يستخدم تضمينات المتجهات للعثور على أجزاء المستندات ذات الصلة، ثم يقوم بإنشاء
استجابة باستخدام نموذج لغوي كبير. يوفر وضع التدفق النتائج بشكل تدريجي.

**الوسائط:**

`query`: استعلام بلغة طبيعية
`user`: معرف المستخدم/مساحة الاسم
`collection`: معرف المجموعة
`doc_limit`: الحد الأقصى لعدد أجزاء المستندات التي سيتم استرجاعها (افتراضي: 10)
`streaming`: تمكين وضع التدفق (افتراضي: False)
`**kwargs`: معلمات إضافية يتم تمريرها إلى الخدمة

**الإرجاع:** Union[str, Iterator[str]]: الاستجابة الكاملة أو سلسلة من أجزاء النص

**مثال:**

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

تنفيذ استعلام RAG يعتمد على المستند مع دعم الشفافية.

يقوم بإرسال كل من أجزاء المحتوى (RAGChunk) وأحداث المصدر (ProvenanceEvent).
تحتوي أحداث المصدر على عناوين URI يمكن استردادها باستخدام ExplainabilityClient
للحصول على معلومات تفصيلية حول كيفية إنشاء الاستجابة.

يتكون تتبع RAG للمستند من:
السؤال: استعلام المستخدم.
الاستكشاف: الأجزاء المستردة من مستودع المستندات (عدد الأجزاء).
التوليف: الإجابة التي تم إنشاؤها.

**الوسائط:**

`query`: استعلام بلغة طبيعية.
`user`: معرف المستخدم/المساحة.
`collection`: معرف المجموعة.
`doc_limit`: الحد الأقصى لعدد أجزاء المستندات التي سيتم استردادها (افتراضي: 10).
`**kwargs`: معلمات إضافية يتم تمريرها إلى الخدمة.
`Yields`: 
`Union[RAGChunk, ProvenanceEvent]`: أجزاء المحتوى وأحداث المصدر.

**مثال:**

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

توليد تضمينات متجهة لنص أو أكثر.

**الوسائط:**

`texts`: قائمة بالنصوص المدخلة لإنشاء التضمينات.
`**kwargs`: معلمات إضافية يتم تمريرها إلى الخدمة.

**الإرجاع:** قاموس: استجابة تحتوي على المتجهات (مجموعة واحدة لكل نص مدخل).

**مثال:**

```python
socket = api.socket()
flow = socket.flow("default")

result = flow.embeddings(["quantum computing"])
vectors = result.get("vectors", [])
```

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any) -> Dict[str, Any]`

الاستعلام عن كيانات الرسم البياني المعرفي باستخدام التشابه الدلالي.

**الوسائط:**

`text`: نص الاستعلام للبحث الدلالي
`user`: معرف المستخدم/مساحة المفاتيح
`collection`: معرف المجموعة
`limit`: الحد الأقصى لعدد النتائج (افتراضي: 10)
`**kwargs`: معلمات إضافية يتم تمريرها إلى الخدمة

**الإرجاع:** dict: نتائج الاستعلام مع الكيانات المشابهة

**مثال:**

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

تنفيذ استعلام RAG يعتمد على الرسم البياني مع خيار التدفق.

يستخدم هيكل الرسم البياني للمعرفة للعثور على السياق ذي الصلة، ثم يقوم بإنشاء
استجابة باستخدام نموذج لغوي كبير. يوفر وضع التدفق النتائج بشكل تدريجي.

**الوسائط:**

`query`: استعلام بلغة طبيعية
`user`: معرف المستخدم/مساحة الاسم
`collection`: معرف المجموعة
`max_subgraph_size`: الحد الأقصى لإجمالي الثلاثيات في الرسم البياني الفرعي (افتراضي: 1000)
`max_subgraph_count`: الحد الأقصى لعدد الرسوم البيانية الفرعية (افتراضي: 5)
`max_entity_distance`: الحد الأقصى لعمق المسار (افتراضي: 3)
`streaming`: تمكين وضع التدفق (افتراضي: False)
`**kwargs`: معلمات إضافية يتم تمريرها إلى الخدمة

**الإرجاع:** Union[str, Iterator[str]]: الاستجابة الكاملة أو سلسلة من أجزاء النص

**مثال:**

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

تنفيذ استعلام RAG المستند إلى الرسم البياني مع دعم الشفافية.

يقوم بإرسال كل من أجزاء المحتوى (RAGChunk) وأحداث المصدر (ProvenanceEvent).
تحتوي أحداث المصدر على معرفات URI يمكن استردادها باستخدام ExplainabilityClient
للحصول على معلومات تفصيلية حول كيفية إنشاء الاستجابة.

**الوسائط:**

`query`: استعلام بلغة طبيعية.
`user`: معرف المستخدم/المساحة.
`collection`: معرف المجموعة.
`max_subgraph_size`: الحد الأقصى لإجمالي الثلاثيات في الرسم البياني الفرعي (افتراضي: 1000).
`max_subgraph_count`: الحد الأقصى لعدد الرسوم البيانية الفرعية (افتراضي: 5).
`max_entity_distance`: الحد الأقصى لعمق المسار (افتراضي: 3).
`**kwargs`: معلمات إضافية يتم تمريرها إلى الخدمة.
`Yields`: 
`Union[RAGChunk, ProvenanceEvent]`: أجزاء المحتوى وأحداث المصدر.

**مثال:**

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

تنفيذ أداة بروتوكول سياق النموذج (MCP).

**الوسائط:**

`name`: اسم/معرّف الأداة
`parameters`: قاموس معلمات الأداة
`**kwargs`: معلمات إضافية يتم تمريرها إلى الخدمة

**النتائج:** dict: نتيجة تنفيذ الأداة

**مثال:**

```python
socket = api.socket()
flow = socket.flow("default")

result = flow.mcp_tool(
    name="search-web",
    parameters={"query": "latest AI news", "limit": 5}
)
```

### `prompt(self, id: str, variables: Dict[str, str], streaming: bool = False, **kwargs: Any) -> str | Iterator[str]`

تنفيذ قالب إرشادي مع إمكانية التدفق الاختياري.

**الوسائط:**

`id`: مُعرّف قالب الإرشادي.
`variables`: قاموس لربط أسماء المتغيرات بقيمها.
`streaming`: تفعيل وضع التدفق (افتراضي: False).
`**kwargs`: معلمات إضافية يتم تمريرها إلى الخدمة.

**الإرجاع:** Union[str, Iterator[str]]: الاستجابة الكاملة أو سلسلة من أجزاء النص.

**مثال:**

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

استعلام عن بيانات الصفوف باستخدام التشابه الدلالي على الحقول المفهرسة.

يجد الصفوف التي تكون فيها قيم الحقول المفهرسة متشابهة دلاليًا مع
النص المدخل، وذلك باستخدام تضمينات المتجهات. هذا يتيح المطابقة التقريبية/الدلالية
على البيانات المنظمة.

**الوسائط:**

`text`: نص الاستعلام للبحث الدلالي
`schema_name`: اسم المخطط للبحث داخله
`user`: معرف المستخدم/مساحة المفاتيح (الافتراضي: "trustgraph")
`collection`: معرف المجموعة (الافتراضي: "default")
`index_name`: اسم الفهرس الاختياري لتصفية البحث في فهرس معين
`limit`: الحد الأقصى لعدد النتائج (الافتراضي: 10)
`**kwargs`: معلمات إضافية يتم تمريرها إلى الخدمة

**الإرجاع:** dict: نتائج الاستعلام مع التطابقات التي تحتوي على index_name و index_value و text و score

**مثال:**

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

تنفيذ استعلام GraphQL مقابل الصفوف المنظمة.

**الوسائط:**

`query`: سلسلة استعلام GraphQL
`user`: معرف المستخدم/مساحة المفاتيح
`collection`: معرف المجموعة
`variables`: قاموس اختياري لمتغيرات الاستعلام
`operation_name`: اسم العملية الاختياري للمستندات متعددة العمليات
`**kwargs`: معلمات إضافية يتم تمريرها إلى الخدمة

**الإرجاع:** dict: استجابة GraphQL مع البيانات والأخطاء و/أو الامتدادات

**مثال:**

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

تنفيذ إكمال النص مع خيار التدفق.

**الوسائط:**

`system`: نص النظام الذي يحدد سلوك المساعد.
`prompt`: نص المستخدم/سؤال.
`streaming`: تمكين وضع التدفق (افتراضي: False).
`**kwargs`: معلمات إضافية يتم تمريرها إلى الخدمة.

**الإرجاع:** Union[str, Iterator[str]]: الاستجابة الكاملة أو سلسلة من أجزاء النص.

**مثال:**

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

الاستعلام عن ثلاثيات الرسم البياني المعرفي باستخدام مطابقة الأنماط.

**الوسائط:**

`s`: عامل تصفية الموضوع - سلسلة URI، أو قاموس مصطلحات، أو None للرمز البري.
`p`: عامل تصفية المسند - سلسلة URI، أو قاموس مصطلحات، أو None للرمز البري.
`o`: عامل تصفية الكائن - سلسلة URI/حرفية، أو قاموس مصطلحات، أو None للرمز البري.
`g`: عامل تصفية الرسم البياني المسمى - سلسلة URI أو None لجميع الرسوم البيانية.
`user`: معرف المستخدم/مساحة المفاتيح (اختياري).
`collection`: معرف المجموعة (اختياري).
`limit`: الحد الأقصى للنتائج المراد إرجاعها (الافتراضي: 100).
`**kwargs`: معلمات إضافية يتم تمريرها إلى الخدمة.

**الإرجاع:** List[Dict]: قائمة بالثلاثيات المتطابقة بتنسيق السلك.

**مثال:**

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

الاستعلام عن ثلاثيات الرسم البياني المعرفي باستخدام دفعات متدفقة.

ينتج دفعات من الثلاثيات أثناء وصولها، مما يقلل من الوقت اللازم للحصول على النتيجة الأولى
وتقليل الحمل الزائد للذاكرة لمجموعات النتائج الكبيرة.

**الوسائط:**

`s`: عامل تصفية الموضوع - سلسلة URI، أو قاموس مصطلحات، أو None للرمز البرمجي.
`p`: عامل تصفية المسند - سلسلة URI، أو قاموس مصطلحات، أو None للرمز البرمجي.
`o`: عامل تصفية الكائن - سلسلة URI/حرفية، أو قاموس مصطلحات، أو None للرمز البرمجي.
`g`: عامل تصفية الرسم البياني المسمى - سلسلة URI أو None لجميع الرسوم البيانية.
`user`: معرف المستخدم/مساحة المفاتيح (اختياري).
`collection`: معرف المجموعة (اختياري).
`limit`: الحد الأقصى للنتائج المراد إرجاعها (الافتراضي: 100).
`batch_size`: الثلاثيات لكل دفعة (الافتراضي: 20).
`**kwargs`: معلمات إضافية يتم تمريرها إلى الخدمة.
`Yields`: 
`List[Dict]`: دفعات من الثلاثيات بتنسيق السلك.

**مثال:**

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

عميل WebSocket غير متزامن.

### الطرق.

### `__init__(self, url: str, timeout: int, token: str | None)`

تهيئة الكائن الذاتي. راجع help(type(self)) للحصول على التوقيع الدقيق.

### `aclose(self)`

إغلاق اتصال WebSocket.

### `flow(self, flow_id: str)`

الحصول على مثيل التدفق غير المتزامن لعمليات WebSocket.


--

## `AsyncSocketFlowInstance`

```python
from trustgraph.api import AsyncSocketFlowInstance
```

مثيل تدفق WebSocket غير متزامن.

### الطرق

### `__init__(self, client: trustgraph.api.async_socket_client.AsyncSocketClient, flow_id: str)`

تهيئة الكائن الذاتي. راجع help(type(self)) للحصول على التوقيع الدقيق.

### `agent(self, question: str, user: str, state: Dict[str, Any] | None = None, group: str | None = None, history: list | None = None, streaming: bool = False, **kwargs) -> Dict[str, Any] | AsyncIterator`

وكيل مع تدفق اختياري.

### `document_rag(self, query: str, user: str, collection: str, doc_limit: int = 10, streaming: bool = False, **kwargs)`

توثيق RAG مع تدفق اختياري.

### `embeddings(self, texts: list, **kwargs)`

إنشاء تضمينات نصية.

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs)`

الاستعلام عن تضمينات الرسم البياني للبحث الدلالي.

### `graph_rag(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, streaming: bool = False, **kwargs)`

RAG للرسم البياني مع تدفق اختياري.

### `mcp_tool(self, name: str, parameters: Dict[str, Any], **kwargs)`

تنفيذ أداة MCP.

### `prompt(self, id: str, variables: Dict[str, str], streaming: bool = False, **kwargs)`

تنفيذ موجه مع تدفق اختياري.

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs)`

الاستعلام عن تضمينات الصفوف للبحث الدلالي على البيانات المنظمة.

### `rows_query(self, query: str, user: str, collection: str, variables: Dict | None = None, operation_name: str | None = None, **kwargs)`

استعلام GraphQL عن الصفوف المنظمة.

### `text_completion(self, system: str, prompt: str, streaming: bool = False, **kwargs)`

إكمال النص مع تدفق اختياري.

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=100, **kwargs)`

استعلام نمط ثلاثي.


--

### `build_term(value: Any, term_type: str | None = None, datatype: str | None = None, language: str | None = None) -> Dict[str, Any] | None`

إنشاء قاموس Term بتنسيق سلكي من قيمة.

قواعد الكشف التلقائي (عندما يكون term_type هو None):
  إذا كان بالفعل قاموسًا مع مفتاح 't' -> إرجاعه كما هو (قاموس Term بالفعل)
  يبدأ بـ http://, https://, urn: -> IRI
  محاط بأقواس الزاوية (مثل <http://...>) -> IRI (إزالة أقواس الزاوية)
  أي شيء آخر -> حرفي

**الوسائط:**

`value`: قيمة المصطلح (سلسلة، قاموس، أو None)
`term_type`: واحد من 'iri'، 'literal'، أو None للكشف التلقائي
`datatype`: نوع البيانات للكائنات الحرفية (مثل xsd:integer)
`language`: علامة اللغة للكائنات الحرفية (مثل en)

**الإرجاع:** قاموس: قاموس Term بتنسيق سلكي، أو None إذا كانت القيمة هي None


--

## `BulkClient`

```python
from trustgraph.api import BulkClient
```

عميل للعمليات المجمعة المتزامنة للاستيراد/التصدير.

يوفر نقل بيانات مجمع فعال عبر WebSocket لمجموعات البيانات الكبيرة.
يغلف عمليات WebSocket غير المتزامنة باستخدام مولدات متزامنة لسهولة الاستخدام.

ملاحظة: للحصول على دعم غير متزامن حقيقي، استخدم AsyncBulkClient بدلاً من ذلك.

### الطرق

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

تهيئة عميل مجمع متزامن.

**الوسائط:**

`url`: عنوان URL الأساسي لواجهة برمجة تطبيقات TrustGraph (سيتم تحويل HTTP/HTTPS إلى WS/WSS).
`timeout`: مهلة WebSocket بالثواني.
`token`: رمز مميز اختياري للمصادقة.

### `close(self) -> None`

إغلاق الاتصالات.

### `export_document_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

تصدير مجمّع لتضمينات المستندات من تدفق.

يقوم بتنزيل جميع تضمينات أجزاء المستندات بكفاءة عبر بث WebSocket.

**الوسائط:**

`flow`: معرف التدفق.
`**kwargs`: معلمات إضافية (محجوزة للاستخدام المستقبلي).

**الإرجاع:** Iterator[Dict[str, Any]]: دفق من قواميس التضمين.

**مثال:**

```python
bulk = api.bulk()

# Export and process document embeddings
for embedding in bulk.export_document_embeddings(flow="default"):
    chunk_id = embedding.get("chunk_id")
    vector = embedding.get("embedding")
    print(f"{chunk_id}: {len(vector)} dimensions")
```

### `export_entity_contexts(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

تصدير كميات كبيرة من سياقات الكيانات من تدفق.

يقوم بتنزيل جميع معلومات سياق الكيانات بكفاءة عبر بث WebSocket.

**الوسائط:**

`flow`: مُعرّف التدفق
`**kwargs`: معلمات إضافية (محجوزة للاستخدام المستقبلي)

**الإرجاع:** Iterator[Dict[str, Any]]: سلسلة من قواميس السياق

**مثال:**

```python
bulk = api.bulk()

# Export and process entity contexts
for context in bulk.export_entity_contexts(flow="default"):
    entity = context.get("entity")
    text = context.get("context")
    print(f"{entity}: {text[:100]}...")
```

### `export_graph_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

تصدير جماعي لتمثيلات الرسم البياني من تدفق.

يقوم بتنزيل جميع تمثيلات الكيانات في الرسم البياني بكفاءة عبر بث WebSocket.

**الوسائط:**

`flow`: مُعرّف التدفق.
`**kwargs`: معلمات إضافية (محجوزة للاستخدام المستقبلي).

**الإرجاع:** Iterator[Dict[str, Any]]: تدفق لقواميس التمثيل.

**مثال:**

```python
bulk = api.bulk()

# Export and process embeddings
for embedding in bulk.export_graph_embeddings(flow="default"):
    entity = embedding.get("entity")
    vector = embedding.get("embedding")
    print(f"{entity}: {len(vector)} dimensions")
```

### `export_triples(self, flow: str, **kwargs: Any) -> Iterator[trustgraph.api.types.Triple]`

تصدير كميات كبيرة من الثلاثيات RDF من تدفق.

يقوم بتنزيل جميع الثلاثيات بكفاءة عبر بث WebSocket.

**الوسائط:**

`flow`: مُعرّف التدفق.
`**kwargs`: معلمات إضافية (محجوزة للاستخدام المستقبلي).

**الإرجاع:** Iterator[Triple]: دفق لكائنات Triple.

**مثال:**

```python
bulk = api.bulk()

# Export and process triples
for triple in bulk.export_triples(flow="default"):
    print(f"{triple.s} -> {triple.p} -> {triple.o}")
```

### `import_document_embeddings(self, flow: str, embeddings: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

استيراد كميات كبيرة من تضمينات المستندات إلى مسار عمل.

يقوم بتحميل تضمينات أجزاء المستندات بكفاءة عبر بث WebSocket
لاستخدامها في استعلامات استرجاع المعلومات من المستندات (RAG).

**الوسائط:**

`flow`: مُعرّف مسار العمل.
`embeddings`: مُكرّر ينتج قواميس التضمين.
`**kwargs`: معلمات إضافية (محجوزة للاستخدام المستقبلي).

**مثال:**

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

استيراد كميات كبيرة من سياقات الكيانات إلى تدفق.

يقوم بتحميل معلومات سياق الكيانات بكفاءة عبر بث WebSocket.
توفر سياقات الكيانات سياقًا نصيًا إضافيًا حول كيانات الرسم البياني
لتحسين أداء RAG.

**الوسائط:**

`flow`: مُعرّف التدفق.
`contexts`: مُكرّر ينتج قواميس السياق.
`metadata`: قاموس بيانات التعريف مع id و metadata والمستخدم والمجموعة.
`batch_size`: عدد السياقات لكل دفعة (افتراضي 100).
`**kwargs`: معلمات إضافية (محجوزة للاستخدام المستقبلي).

**مثال:**

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

استيراد كميات كبيرة من تضمينات الرسم البياني إلى مسار عمل.

يقوم بتحميل تضمينات كيانات الرسم البياني بكفاءة عبر بث WebSocket.

**الوسائط:**

`flow`: مُعرّف مسار العمل.
`embeddings`: مُكرّر ينتج قواميس التضمين.
`**kwargs`: معلمات إضافية (محجوزة للاستخدام المستقبلي).

**مثال:**

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

استيراد كميات كبيرة من الصفوف المنظمة إلى مسار عمل.

يقوم بتحميل بيانات منظمة بكفاءة عبر بث WebSocket
للاستخدام في استعلامات GraphQL.

**الوسائط:**

`flow`: مُعرّف مسار العمل.
`rows`: مُكرّر ينتج قواميس الصفوف.
`**kwargs`: معلمات إضافية (محجوزة للاستخدام المستقبلي).

**مثال:**

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

استيراد كميات كبيرة من الثلاثيات RDF إلى تدفق.

يقوم بتحميل أعداد كبيرة من الثلاثيات بكفاءة عبر بث WebSocket.

**الوسائط:**

`flow`: مُعرّف التدفق.
`triples`: مُكرّر ينتج كائنات Triple.
`metadata`: قاموس بيانات وصفية بمعرف، وبيانات وصفية، ومستخدم، ومجموعة.
`batch_size`: عدد الثلاثيات لكل دفعة (افتراضي 100).
`**kwargs`: معلمات إضافية (محجوزة للاستخدام المستقبلي).

**مثال:**

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

عميل العمليات المجمعة غير المتزامنة.

### الطرق

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

تهيئة الكائن الذاتي. راجع help(type(self)) للحصول على التوقيع الدقيق.

### `aclose(self) -> None`

إغلاق الاتصالات.

### `export_document_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

تصدير مجمّع لتمثيلات المستندات عبر WebSocket.

### `export_entity_contexts(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

تصدير مجمّع لسياقات الكيانات عبر WebSocket.

### `export_graph_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

تصدير مجمّع لتمثيلات الرسم البياني عبر WebSocket.

### `export_triples(self, flow: str, **kwargs: Any) -> AsyncIterator[trustgraph.api.types.Triple]`

تصدير مجمّع للثلاثيات عبر WebSocket.

### `import_document_embeddings(self, flow: str, embeddings: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

استيراد مجمّع لتمثيلات المستندات عبر WebSocket.

### `import_entity_contexts(self, flow: str, contexts: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

استيراد مجمّع لسياقات الكيانات عبر WebSocket.

### `import_graph_embeddings(self, flow: str, embeddings: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

استيراد مجمّع لتمثيلات الرسم البياني عبر WebSocket.

### `import_rows(self, flow: str, rows: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

استيراد مجمّع للصفوف عبر WebSocket.

### `import_triples(self, flow: str, triples: AsyncIterator[trustgraph.api.types.Triple], **kwargs: Any) -> None`

استيراد مجمّع للثلاثيات عبر WebSocket.


--

## `Metrics`

```python
from trustgraph.api import Metrics
```

عميل المقاييس المتزامنة.

### الطرق.

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

قم بتهيئة `self`. راجع `help(type(self))` للحصول على التوقيع الدقيق.

### `get(self) -> str`

احصل على مقاييس بروميثيوس كنص.


--

## `AsyncMetrics`

```python
from trustgraph.api import AsyncMetrics
```

عميل المقاييس غير المتزامن.

### الطرق.

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

قم بتهيئة `self`. راجع `help(type(self))` للحصول على التوقيع الدقيق.

### `aclose(self) -> None`

أغلق الاتصالات.

### `get(self) -> str`

احصل على مقاييس Prometheus كنص.


--

## `ExplainabilityClient`

```python
from trustgraph.api import ExplainabilityClient
```

عميل لجلب كيانات التفسير مع معالجة الاتساق النهائي.

يستخدم اكتشاف حالة السكون: الجلب، الانتظار، الجلب مرة أخرى، المقارنة.
إذا كانت النتائج متطابقة، فإن البيانات مستقرة.

### الطرق

### `__init__(self, flow_instance, retry_delay: float = 0.2, max_retries: int = 10)`

تهيئة عميل التفسير.

**الوسائط:**

`flow_instance`: مثيل SocketFlowInstance للاستعلام عن الثلاثيات.
`retry_delay`: التأخير بين عمليات إعادة المحاولة بالثواني (افتراضي: 0.2).
`max_retries`: الحد الأقصى لعدد محاولات إعادة المحاولة (افتراضي: 10).

### `detect_session_type(self, session_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> str`

الكشف عما إذا كانت الجلسة من نوع GraphRAG أو Agent.

**الوسائط:**

`session_uri`: عنوان URI للجلسة/السؤال.
`graph`: الرسم البياني المسمى.
`user`: معرف المستخدم/مساحة المفاتيح.
`collection`: معرف المجموعة.

**الإرجاع:** "graphrag" أو "agent".

### `fetch_agent_trace(self, session_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

جلب مسار Agent الكامل بدءًا من عنوان URI للجلسة.

يتبع سلسلة الأصل: سؤال -> تحليل (قائمة التحليلات) -> استنتاج.

**الوسائط:**

`session_uri`: عنوان URI لجلسة/سؤال الوكيل.
`graph`: الرسم البياني المسمى (افتراضي: urn:graph:retrieval).
`user`: معرف المستخدم/مساحة المفاتيح.
`collection`: معرف المجموعة.
`api`: مثيل TrustGraph Api للوصول إلى أمين المكتبة (اختياري).
`max_content`: الحد الأقصى لطول المحتوى للاستنتاج.

**الإرجاع:** قاموس يحتوي على السؤال والتكرارات (قائمة التحليلات) والكيانات الاستنتاجية.

### `fetch_docrag_trace(self, question_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

جلب مسار DocumentRAG الكامل بدءًا من عنوان URI للسؤال.

يتبع سلسلة الأصل:
    سؤال -> تثبيت -> استكشاف -> توليف.

**الوسائط:**

`question_uri`: عنوان URI لكيان السؤال.
`graph`: الرسم البياني المسمى (افتراضي: urn:graph:retrieval).
`user`: معرف المستخدم/مساحة المفاتيح.
`collection`: معرف المجموعة.
`api`: مثيل TrustGraph Api للوصول إلى أمين المكتبة (اختياري).
`max_content`: الحد الأقصى لطول المحتوى للتوليف.

**الإرجاع:** قاموس يحتوي على السؤال والتثبيت والاستكشاف والكيانات التوليفية.

### `fetch_document_content(self, document_uri: str, api: Any, user: str | None = None, max_content: int = 10000) -> str`

جلب المحتوى من أمين المكتبة بواسطة عنوان URI للمستند.

**الوسائط:**

`document_uri`: عنوان URI للمستند في أمين المكتبة.
`api`: مثيل TrustGraph Api للوصول إلى أمين المكتبة.
`user`: معرف المستخدم لأمين المكتبة.
`max_content`: الحد الأقصى لطول المحتوى المراد إرجاعه.

**الإرجاع:** محتوى المستند كسلسلة.

### `fetch_edge_selection(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.EdgeSelection | None`

جلب كيان تحديد الحافة (يستخدم بواسطة Focus).

**الوسائط:**

`uri`: عنوان URI لتحديد الحافة.
`graph`: الرسم البياني المسمى للاستعلام عنه.
`user`: معرف المستخدم/مساحة المفاتيح.
`collection`: معرف المجموعة.

**الإرجاع:** EdgeSelection أو None إذا لم يتم العثور عليه.

### `fetch_entity(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.ExplainEntity | None`

جلب كيان قابل للتفسير باستخدام عنوان URI مع معالجة الاتساق النهائي.

يستخدم اكتشاف حالة السكون:
1. جلب الثلاثيات لعنوان URI
2. إذا كانت النتائج صفرًا، أعد المحاولة
3. إذا كانت النتائج غير صفرية، انتظر وجلب مرة أخرى
4. إذا كانت النتائج هي نفسها، فإن البيانات مستقرة - قم بتحليلها وأرجعها
5. إذا كانت النتائج مختلفة، لا تزال البيانات قيد الكتابة - أعد المحاولة

**الوسائط:**

`uri`: عنوان URI للكيان المراد جلبه
`graph`: الرسم البياني المسمى للاستعلام (مثل "urn:graph:retrieval")
`user`: معرف المستخدم/مساحة المفاتيح
`collection`: معرف المجموعة

**الإرجاع:** فئة ExplainEntity أو None إذا لم يتم العثور عليها

### `fetch_focus_with_edges(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.Focus | None`

جلب كيان Focus وجميع اختيارات الحواف الخاصة به.

**الوسائط:**

`uri`: عنوان URI لكيان Focus
`graph`: الرسم البياني المسمى للاستعلام
`user`: معرف المستخدم/مساحة المفاتيح
`collection`: معرف المجموعة

**الإرجاع:** Focus مع اختيارات الحواف المعبأة، أو None

### `fetch_graphrag_trace(self, question_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

جلب مسار GraphRAG الكامل بدءًا من عنوان URI لسؤال.

يتبع سلسلة الأصل: سؤال -> تجسيد -> استكشاف -> Focus -> توليف

**الوسائط:**

`question_uri`: عنوان URI لكيان السؤال
`graph`: الرسم البياني (افتراضي: urn:graph:retrieval)
`user`: معرف المستخدم/مساحة المفاتيح
`collection`: معرف المجموعة
`api`: مثيل TrustGraph Api للوصول إلى أمين المكتبة (اختياري)
`max_content`: أقصى طول للمحتوى للتوليف

**الإرجاع:** قاموس يحتوي على كيانات السؤال والتجسيد والاستكشاف وFocus والتوليف

### `list_sessions(self, graph: str | None = None, user: str | None = None, collection: str | None = None, limit: int = 50) -> List[trustgraph.api.explainability.Question]`

سرد جميع جلسات التفسير (الأسئلة) في مجموعة.

**الوسائط:**

`graph`: الرسم البياني (افتراضي: urn:graph:retrieval)
`user`: معرف المستخدم/مساحة المفاتيح
`collection`: معرف المجموعة
`limit`: الحد الأقصى لعدد الجلسات المراد إرجاعها

**الإرجاع:** قائمة بكيانات السؤال مرتبة حسب الطابع الزمني (الأحدث أولاً)

### `resolve_edge_labels(self, edge: Dict[str, str], user: str | None = None, collection: str | None = None) -> Tuple[str, str, str]`

حل تسميات جميع مكونات ثلاثية الحافة.

**الوسائط:**

`edge`: قاموس مع مفاتيح "s" و "p" و "o"
`user`: معرف المستخدم/مساحة المفاتيح
`collection`: معرف المجموعة

**الإرجاع:** مجموعة من (s_label, p_label, o_label)

### `resolve_label(self, uri: str, user: str | None = None, collection: str | None = None) -> str`

حل rdfs:label لعنوان URI، مع التخزين المؤقت.

**الوسائط:**

`uri`: عنوان URI للحصول على التسمية
`user`: معرف المستخدم/مساحة المفاتيح
`collection`: معرف المجموعة

**الإرجاع:** التسمية إذا تم العثور عليها، وإلا فإن عنوان URI نفسه


--

## `ExplainEntity`

```python
from trustgraph.api import ExplainEntity
```

الفئة الأساسية لكائنات التفسير.

**الحقول:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>

### الطرق

### `__init__(self, uri: str, entity_type: str = '') -> None`

تهيئة الكائن الذاتي. راجع help(type(self)) للحصول على التوقيع الدقيق.


--

## `Question`

```python
from trustgraph.api import Question
```

كيان السؤال - استعلام المستخدم الذي بدأ الجلسة.

**الحقول:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`query`: <class 'str'>
`timestamp`: <class 'str'>
`question_type`: <class 'str'>

### الطرق

### `__init__(self, uri: str, entity_type: str = '', query: str = '', timestamp: str = '', question_type: str = '') -> None`

تهيئة الذات. راجع help(type(self)) للحصول على التوقيع الدقيق.


--

## `Exploration`

```python
from trustgraph.api import Exploration
```

كيان الاستكشاف - الحواف/الأجزاء المسترجعة من مستودع المعرفة.

**الحقول:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`edge_count`: <class 'int'>
`chunk_count`: <class 'int'>
`entities`: typing.List[str]

### الطرق

### `__init__(self, uri: str, entity_type: str = '', edge_count: int = 0, chunk_count: int = 0, entities: List[str] = <factory>) -> None`

تهيئة الذات. راجع help(type(self)) للحصول على التوقيع الدقيق.


--

## `Focus`

```python
from trustgraph.api import Focus
```

الكيان المستهدف - الحواف المحددة مع الاستدلال باستخدام نماذج اللغة الكبيرة (GraphRAG فقط).

**الحقول:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`selected_edge_uris`: typing.List[str]
`edge_selections`: typing.List[trustgraph.api.explainability.EdgeSelection]

### الطرق

### `__init__(self, uri: str, entity_type: str = '', selected_edge_uris: List[str] = <factory>, edge_selections: List[trustgraph.api.explainability.EdgeSelection] = <factory>) -> None`

تهيئة الذات. راجع help(type(self)) للحصول على التوقيع الدقيق.


--

## `Synthesis`

```python
from trustgraph.api import Synthesis
```

الكيان التجميعي - الإجابة النهائية.

**الحقول:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`document`: <class 'str'>

### الطرق

### `__init__(self, uri: str, entity_type: str = '', document: str = '') -> None`

تهيئة الذات. راجع help(type(self)) للحصول على التوقيع الدقيق.


--

## `Analysis`

```python
from trustgraph.api import Analysis
```

كيان التحليل - دورة تفكير/فعل/ملاحظة واحدة (للوكيل فقط).

**الحقول:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`action`: <class 'str'>
`arguments`: <class 'str'>
`thought`: <class 'str'>
`observation`: <class 'str'>

### الطرق

### `__init__(self, uri: str, entity_type: str = '', action: str = '', arguments: str = '', thought: str = '', observation: str = '') -> None`

تهيئة الذات. راجع help(type(self)) للحصول على التوقيع الدقيق.


--

## `Conclusion`

```python
from trustgraph.api import Conclusion
```

الخلاصة: الإجابة النهائية (للممثل فقط).

**الحقول:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`document`: <class 'str'>

### الطرق

### `__init__(self, uri: str, entity_type: str = '', document: str = '') -> None`

تهيئة الذات. راجع help(type(self)) للحصول على التوقيع الدقيق.


--

## `EdgeSelection`

```python
from trustgraph.api import EdgeSelection
```

حافة محددة مع شرح من خطوة GraphRAG Focus.

**الحقول:**

`uri`: <class 'str'>
`edge`: typing.Dict[str, str] | None
`reasoning`: <class 'str'>

### الطرق

### `__init__(self, uri: str, edge: Dict[str, str] | None = None, reasoning: str = '') -> None`

تهيئة الذات. راجع help(type(self)) للحصول على التوقيع الدقيق.


--

### `wire_triples_to_tuples(wire_triples: List[Dict[str, Any]]) -> List[Tuple[str, str, Any]]`

تحويل الثلاثيات بتنسيق الأسلاك إلى صفوف (s, p, o).


--

### `extract_term_value(term: Dict[str, Any]) -> Any`

استخراج القيمة من قاموس Term بتنسيق الأسلاك.


--

## `Triple`

```python
from trustgraph.api import Triple
```

ثلاثية RDF تمثل عبارة في رسم بياني للمعرفة.

**الحقول:**

`s`: <class 'str'>
`p`: <class 'str'>
`o`: <class 'str'>

### الطرق

### `__init__(self, s: str, p: str, o: str) -> None`

تهيئة الذات. راجع help(type(self)) للحصول على التوقيع الدقيق.


--

## `Uri`

```python
from trustgraph.api import Uri
```

str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

إنشاء كائن سلسلة جديد من الكائن المعطى. إذا تم تحديد ترميز أو
معالج أخطاء، فيجب أن يعرض الكائن مخزن بيانات سيتم فك ترميزه باستخدام الترميز ومعالج الأخطاء المحددين.
بخلاف ذلك، يتم إرجاع نتيجة object.__str__() (إذا تم تعريفه)
أو repr(object).
الترميز الافتراضي هو 'utf-8'.
معالج الأخطاء الافتراضي هو 'strict'.


### الطرق

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

إنشاء كائن سلسلة جديد من الكائن المعطى. إذا تم تحديد ترميز أو
معالجة الأخطاء، فيجب أن يعرض الكائن مخزن بيانات سيتم فك ترميزه باستخدام الترميز ومعالج الأخطاء المحدد.
بخلاف ذلك، يتم إرجاع نتيجة object.__str__() (إذا تم تعريفه)
أو repr(object).
الترميز الافتراضي هو 'utf-8'.
معالجة الأخطاء الافتراضية هي 'strict'.


### الطرق

### `is_literal(self)`

### `is_triple(self)`

### `is_uri(self)`


--

## `ConfigKey`

```python
from trustgraph.api import ConfigKey
```

مُعرّف مفتاح التكوين.

**الحقول:**

`type`: <class 'str'>
`key`: <class 'str'>

### الطرق

### `__init__(self, type: str, key: str) -> None`

تهيئة الذات. راجع help(type(self)) للحصول على التوقيع الدقيق.


--

## `ConfigValue`

```python
from trustgraph.api import ConfigValue
```

زوج مفتاح-قيمة للتكوين.

**الحقول:**

`type`: <class 'str'>
`key`: <class 'str'>
`value`: <class 'str'>

### الطرق

### `__init__(self, type: str, key: str, value: str) -> None`

تهيئة الذات. راجع help(type(self)) للحصول على التوقيع الدقيق.


--

## `DocumentMetadata`

```python
from trustgraph.api import DocumentMetadata
```

بيانات وصفية لـمستند في المكتبة.

**الخصائص:**

`parent_id: Parent document ID for child documents (empty for top`: (مستوى المستندات)

**الحقول:**

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

### الطرق

### `__init__(self, id: str, time: datetime.datetime, kind: str, title: str, comments: str, metadata: List[trustgraph.api.types.Triple], user: str, tags: List[str], parent_id: str = '', document_type: str = 'source') -> None`

تهيئة self. راجع help(type(self)) للحصول على التوقيع الدقيق.


--

## `ProcessingMetadata`

```python
from trustgraph.api import ProcessingMetadata
```

بيانات وصفية لعملية معالجة مستند نشطة.

**الحقول:**

`id`: <class 'str'>
`document_id`: <class 'str'>
`time`: <class 'datetime.datetime'>
`flow`: <class 'str'>
`user`: <class 'str'>
`collection`: <class 'str'>
`tags`: typing.List[str]

### الطرق

### `__init__(self, id: str, document_id: str, time: datetime.datetime, flow: str, user: str, collection: str, tags: List[str]) -> None`

تهيئة الـ self.  راجع help(type(self)) للحصول على التوقيع الدقيق.


--

## `CollectionMetadata`

```python
from trustgraph.api import CollectionMetadata
```

بيانات وصفية لمجموعة بيانات.

توفر المجموعات تجميعًا منطقيًا وعزلًا للمستندات وبيانات الرسم البياني المعرفي.


**الخصائص:**

`name: Human`: اسم المجموعة الذي يمكن قراءته.

**الحقول:**

`user`: <class 'str'>
`collection`: <class 'str'>
`name`: <class 'str'>
`description`: <class 'str'>
`tags`: typing.List[str]

### الطرق

### `__init__(self, user: str, collection: str, name: str, description: str, tags: List[str]) -> None`

تهيئة الذات. راجع help(type(self)) للحصول على التوقيع الدقيق.


--

## `StreamingChunk`

```python
from trustgraph.api import StreamingChunk
```

الفئة الأساسية لمعالجة أجزاء الاستجابة المتدفقة.

تُستخدم لعمليات التدفق المستندة إلى WebSocket حيث يتم تسليم الاستجابات
بشكل تدريجي أثناء إنشائها.

**الحقول:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>

### الطرق

### `__init__(self, content: str, end_of_message: bool = False) -> None`

تهيئة الكائن الذاتي. راجع help(type(self)) للحصول على التوقيع الدقيق.


--

## `AgentThought`

```python
from trustgraph.api import AgentThought
```

جزء من تفكير أو عملية استنتاج الوكيل.

يمثل خطوات التفكير أو التخطيط الداخلية للوكيل أثناء التنفيذ.
تُظهر هذه الأجزاء كيف يفكر الوكيل في المشكلة.

**الحقول:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>

### الطرق

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'thought') -> None`

تهيئة الذات. راجع help(type(self)) للحصول على التوقيع الدقيق.


--

## `AgentObservation`

```python
from trustgraph.api import AgentObservation
```

جزء من ملاحظات تنفيذ أداة الوكيل.

يمثل النتيجة أو الملاحظة الناتجة عن تنفيذ أداة أو إجراء.
تُظهر هذه الأجزاء ما تعلمه الوكيل من استخدام الأدوات.

**الحقول:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>

### الطرق

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'observation') -> None`

تهيئة الذات. راجع help(type(self)) للحصول على التوقيع الدقيق.


--

## `AgentAnswer`

```python
from trustgraph.api import AgentAnswer
```

الجزء النهائي للإجابة من الوكيل.

يمثل الاستجابة النهائية للوكيل للمستخدم بعد الانتهاء من
عملية التفكير واستخدام الأدوات.

**الخصائص:**

`chunk_type: Always "final`: answer"

**الحقول:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>
`end_of_dialog`: <class 'bool'>

### الطرق

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'final-answer', end_of_dialog: bool = False) -> None`

تهيئة الـ self.  راجع help(type(self)) للحصول على التوقيع الدقيق.


--

## `RAGChunk`

```python
from trustgraph.api import RAGChunk
```

تدفق جزء (Chunk) لـ RAG (الجيل المعزز بالاسترجاع).

يُستخدم لإرسال الاستجابات من مخطط RAG، و RAG المستندات، وإكمال النصوص،
والخدمات التوليدية الأخرى.

**الحقول:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>
`end_of_stream`: <class 'bool'>
`error`: typing.Dict[str, str] | None

### الطرق

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'rag', end_of_stream: bool = False, error: Dict[str, str] | None = None) -> None`

تهيئة الذات (self). راجع help(type(self)) للحصول على التوقيع الدقيق.


--

## `ProvenanceEvent`

```python
from trustgraph.api import ProvenanceEvent
```

حدث التتبع الأصلي لغرض التوضيح.

يتم إصداره أثناء استعلامات GraphRAG عندما يكون وضع التوضيح مفعلاً.
يمثل كل حدث عقدة تتبع أصل تم إنشاؤها أثناء معالجة الاستعلام.

**الحقول:**

`explain_id`: <class 'str'>
`explain_graph`: <class 'str'>
`event_type`: <class 'str'>

### الطرق

### `__init__(self, explain_id: str, explain_graph: str = '', event_type: str = '') -> None`

تهيئة الذات. راجع help(type(self)) للحصول على التوقيع الدقيق.


--

## `ProtocolException`

```python
from trustgraph.api import ProtocolException
```

يتم إطلاق هذا الحدث عند حدوث أخطاء في بروتوكول WebSocket.


--

## `TrustGraphException`

```python
from trustgraph.api import TrustGraphException
```

الفئة الأساسية لجميع أخطاء خدمة TrustGraph.


--

## `AgentError`

```python
from trustgraph.api import AgentError
```

خطأ في خدمة الوكيل.


--

## `ConfigError`

```python
from trustgraph.api import ConfigError
```

خطأ في خدمة التكوين.


--

## `DocumentRagError`

```python
from trustgraph.api import DocumentRagError
```

خطأ استرجاع المستندات.


--

## `FlowError`

```python
from trustgraph.api import FlowError
```

خطأ في إدارة التدفق.


--

## `GatewayError`

```python
from trustgraph.api import GatewayError
```

خطأ في بوابة واجهة برمجة التطبيقات (API Gateway).


--

## `GraphRagError`

```python
from trustgraph.api import GraphRagError
```

خطأ استرجاع الرسوم البيانية.


--

## `LLMError`

```python
from trustgraph.api import LLMError
```

خطأ في خدمة نموذج اللغة الكبير.


--

## `LoadError`

```python
from trustgraph.api import LoadError
```

خطأ في تحميل البيانات.


--

## `LookupError`

```python
from trustgraph.api import LookupError
```

خطأ في البحث/الاستعلام.


--

## `NLPQueryError`

```python
from trustgraph.api import NLPQueryError
```

خطأ في خدمة الاستعلام عن معالجة اللغة الطبيعية.


--

## `RowsQueryError`

```python
from trustgraph.api import RowsQueryError
```

خطأ في خدمة استعلام الصفوف.


--

## `RequestError`

```python
from trustgraph.api import RequestError
```

خطأ في معالجة الطلب.


--

## `StructuredQueryError`

```python
from trustgraph.api import StructuredQueryError
```

خطأ في خدمة الاستعلامات المنظمة.


--

## `UnexpectedError`

```python
from trustgraph.api import UnexpectedError
```

خطأ غير متوقع/مجهول.


--

## `ApplicationException`

```python
from trustgraph.api import ApplicationException
```

الفئة الأساسية لجميع أخطاء خدمة TrustGraph.


--

