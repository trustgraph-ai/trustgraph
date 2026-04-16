---
layout: default
title: "מדריך הפניות ל-API של TrustGraph בפייתון"
parent: "Hebrew (Beta)"
---

# מדריך הפניות ל-API של TrustGraph בפייתון

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## התקנה

```bash
pip install trustgraph
```

## התחלה מהירה

כל המחלקות והטיפוסים מיובאים מהחבילה `trustgraph.api`:

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

## תוכן עניינים

### ליבה

[Api](#api)

### לקוחות זרימה

[Flow](#flow)
[FlowInstance](#flowinstance)
[AsyncFlow](#asyncflow)
[AsyncFlowInstance](#asyncflowinstance)

### לקוחות WebSocket

[SocketClient](#socketclient)
[SocketFlowInstance](#socketflowinstance)
[AsyncSocketClient](#asyncsocketclient)
[AsyncSocketFlowInstance](#asyncsocketflowinstance)

### פעולות מרובות

[BulkClient](#bulkclient)
[AsyncBulkClient](#asyncbulkclient)

### מדדים

[Metrics](#metrics)
[AsyncMetrics](#asyncmetrics)

### סוגי נתונים

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

### חריגות

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

לקוח API הראשי של TrustGraph לפעולות סינכרוניות ואסינכרוניות.

מחלקה זו מספקת גישה לכל שירותי TrustGraph, כולל ניהול זרימות,
פעולות גרף ידע, עיבוד מסמכים, שאילתות RAG ועוד. היא תומכת
הן בדפוסי תקשורת מבוססי REST והן בדפוסי תקשורת מבוססי WebSocket.

ניתן להשתמש בלקוח כמנהל הקשר לניקוי אוטומטי של משאבים:
    ```python
    with Api(url="http://localhost:8088/") as api:
        result = api.flow().id("default").graph_rag(query="test")
    ```

### שיטות

### `__aenter__(self)`

כניסה למנהל הקשר אסינכרוני.

### `__aexit__(self, *args)`

יציאה ממנהל הקשר האסינכרוני וסגירת חיבורים.

### `__enter__(self)`

כניסה למנהל הקשר סינכרוני.

### `__exit__(self, *args)`

יציאה ממנהל הקשר הסינכרוני וסגירת חיבורים.

### `__init__(self, url='http://localhost:8088/', timeout=60, token: str | None = None)`

אתחול לקוח ה-API של TrustGraph.

**ארגומנטים:**

`url`: כתובת הבסיס עבור ה-API של TrustGraph (ברירת מחדל: "http://localhost:8088/"")
`timeout`: זמן אחזור מקסימלי בשניות (ברירת מחדל: 60)
`token`: טוקן bearer אופציונלי לאימות

**דוגמה:**

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

סגור את כל החיבורים של הלקוח האסינכרוניים.

שיטה זו סוגרת חיבורי WebSocket אסינכרוניים, פעולות סיטונאיות וחיבורי זרימה.
היא נקראת אוטומטית כאשר יוצאים מתוך מנהל הקשר האסינכרוני.

**דוגמה:**

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

קבל לקוח לפעולות אסינכרוניות מרובות.

מספק פעולות ייבוא/ייצוא מרובות בסגנון async/await באמצעות WebSocket
לטיפול יעיל בערכות נתונים גדולות.

**מחזיר:** AsyncBulkClient: לקוח לפעולות אסינכרוניות מרובות.

**דוגמה:**

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

קבל לקוח זרימה מבוסס REST אסינכרוני.

מספק גישה בסגנון async/await לפעולות זרימה. זה מועדף
עבור יישומי ומסגרות Python אסינכרוניות (FastAPI, aiohttp, וכו').

**מחזיר:** AsyncFlow: לקוח זרימה אסינכרוני

**דוגמה:**

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

קבל לקוח מדדים אסינכרוני.

מספק גישה בסגנון async/await למדדי Prometheus.

**מחזיר:** AsyncMetrics: לקוח מדדים אסינכרוני

**דוגמה:**

```python
async_metrics = api.async_metrics()
prometheus_text = await async_metrics.get()
print(prometheus_text)
```

### `async_socket(self)`

קבל לקוח WebSocket אסינכרוני לפעולות סטרימינג.

מספק גישה ל-WebSocket בסגנון async/await עם תמיכה בסטרימינג.
זוהי השיטה המועדפת לסטרימינג אסינכרוני בפייתון.

**מחזיר:** AsyncSocketClient: לקוח WebSocket אסינכרוני.

**דוגמה:**

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

קבל לקוח לפעולות סינכרוניות מרובות לצורך ייבוא/ייצוא.

פעולות מרובות מאפשרות העברת כמויות גדולות של נתונים בצורה יעילה באמצעות חיבורי WebSocket, כולל משולשות, הטמעות, הקשרים של ישויות ואובייקטים.

**מחזיר:** BulkClient: לקוח לפעולות סינכרוניות מרובות.

**דוגמה:**


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

סגור את כל החיבורים של הלקוח הסינכרוניים.

שיטה זו סוגרת חיבורי WebSocket וחיבורים לפעולות מרובות.
היא נקראת באופן אוטומטי כאשר יוצאים מתוך מנהל הקשר.

**דוגמה:**

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

קבלת לקוח Collection לניהול אוספי נתונים.

אוספים מארגנים מסמכים ונתוני גרף ידע לקבוצות
לוגיות לצורך בידוד ובקרת גישה.

**מחזיר:** Collection: לקוח לניהול אוספים

**דוגמה:**

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

קבל לקוח Config לניהול הגדרות תצורה.

**מחזיר:** Config: לקוח לניהול תצורה

**דוגמה:**

```python
config = api.config()

# Get configuration values
values = config.get([ConfigKey(type="llm", key="model")])

# Set configuration
config.put([ConfigValue(type="llm", key="model", value="gpt-4")])
```

### `flow(self)`

קבל לקוח Flow לניהול ולביצוע אינטראקציה עם זרימות.

זרימות הן יחידות הביצוע העיקריות ב-TrustGraph, המספקות גישה ל
שירותים כמו סוכנים, שאילתות RAG, הטמעות ועיבוד מסמכים.

**מחזיר:** Flow: לקוח לניהול זרימות

**דוגמה:**

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

קבל לקוח Knowledge לניהול ליבות גרף ידע.

**מחזיר:** לקוח לניהול גרף ידע: Knowledge

**דוגמה:**

```python
knowledge = api.knowledge()

# List available KG cores
cores = knowledge.list_kg_cores(user="trustgraph")

# Load a KG core
knowledge.load_kg_core(id="core-123", user="trustgraph")
```

### `library(self)`

קבלת לקוח לספרייה לניהול מסמכים.

הספרייה מספקת אחסון מסמכים, ניהול מטא-דאטה ו
תיאום זרימת עבודה לעיבוד.

**החזר:** Library: לקוח לניהול ספריית מסמכים

**דוגמה:**

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

קבל לקוח מדדים סינכרוני למטרות ניטור.

שולף מדדים בפורמט Prometheus מהשירות TrustGraph
לצורך ניטור וניתוח.

**מחזיר:** מדדים: לקוח מדדים סינכרוני

**דוגמה:**

```python
metrics = api.metrics()
prometheus_text = metrics.get()
print(prometheus_text)
```

### `request(self, path, request)`

ביצוע בקשת REST ברמה נמוכה.

שיטה זו מיועדת בעיקר לשימוש פנימי, אך ניתן להשתמש בה לגישה ישירה
ל-API כאשר נדרש.

**ארגומנטים:**

`path`: נתיב נקודת הקצה של ה-API (ביחס לכתובת הבסיס)
`request`: מטען הבקשה כמילון

**החזרות:** dict: אובייקט תגובה

**מעלה:**

`ProtocolException`: אם מצב התגובה אינו 200 או שהתגובה אינה JSON
`ApplicationException`: אם התגובה מכילה שגיאה

**דוגמה:**

```python
response = api.request("flow", {
    "operation": "list-flows"
})
```

### `socket(self)`

קבל לקוח WebSocket סינכרוני לפעולות סטרימינג.

חיבורי WebSocket מספקים תמיכה בסטרימינג לתגובות בזמן אמת
מסוכנים, שאילתות RAG והשלמות טקסט. שיטה זו מחזירה עטיפה סינכרונית
סביב פרוטוקול ה-WebSocket.

**מחזיר:** SocketClient: לקוח WebSocket סינכרוני

**דוגמה:**

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

לקוח לניהול זרימות עבור פעולות על תוכניות זרימה ומצבי זרימה.

מחלקה זו מספקת שיטות לניהול תוכניות זרימה (תבניות) ו-
מצבי זרימה (זרימות פעילות). תוכניות זרימה מגדירות את המבנה ואת
הפרמטרים של הזרימות, בעוד שמצבי זרימה מייצגים זרימות פעילות שניתן
להפעיל שירותים.

### שיטות

### `__init__(self, api)`

אתחול לקוח זרימה.

**ארגומנטים:**

`api`: מופע Api הורה לביצוע בקשות

### `delete_blueprint(self, blueprint_name)`

מחיקת תוכנית זרימה.

**ארגומנטים:**

`blueprint_name`: שם התוכנית למחיקה

**דוגמה:**

```python
api.flow().delete_blueprint("old-blueprint")
```

### `get(self, id)`

קבלת ההגדרה של מופע זרימה פעיל.

**ארגומנטים:**

`id`: מזהה מופע זרימה

**החזר:** dict: הגדרת מופע זרימה

**דוגמה:**

```python
flow_def = api.flow().get("default")
print(flow_def)
```

### `get_blueprint(self, blueprint_name)`

קבלת הגדרה של תבנית זרימה לפי שם.

**ארגומנטים:**

`blueprint_name`: שם התבנית שיש לשלוף

**החזר:** dict: הגדרת התבנית כמילון

**דוגמה:**

```python
blueprint = api.flow().get_blueprint("default")
print(blueprint)  # Blueprint configuration
```

### `id(self, id='default')`

קבלת מופע FlowInstance לביצוע פעולות על זרימה ספציפית.

**ארגומנטים:**

`id`: מזהה זרימה (ברירת מחדל: "default")

**החזרות:** FlowInstance: מופע זרימה לפעולות שירות

**דוגמה:**

```python
flow = api.flow().id("my-flow")
response = flow.text_completion(
    system="You are helpful",
    prompt="Hello"
)
```

### `list(self)`

רשום את כל מופעי ה-flow הפעילים.

**מחזיר:** list[str]: רשימה של מזהי מופעי flow

**דוגמה:**

```python
flows = api.flow().list()
print(flows)  # ['default', 'flow-1', 'flow-2', ...]
```

### `list_blueprints(self)`

רשום את כל תבניות העבודה הזמינות.

**מחזיר:** list[str]: רשימה של שמות תבניות.

**דוגמה:**

```python
blueprints = api.flow().list_blueprints()
print(blueprints)  # ['default', 'custom-flow', ...]
```

### `put_blueprint(self, blueprint_name, definition)`

יצירת או עדכון תבנית זרימה.

**ארגומנטים:**

`blueprint_name`: שם עבור התבנית
`definition`: מילון הגדרת התבנית

**דוגמה:**

```python
definition = {
    "services": ["text-completion", "graph-rag"],
    "parameters": {"model": "gpt-4"}
}
api.flow().put_blueprint("my-blueprint", definition)
```

### `request(self, path=None, request=None)`

ביצוע בקשת API בתחום (flow).

**ארגומנטים:**

`path`: סיומת נתיב אופציונלית עבור נקודות קצה של flow.
`request`: מילון מטען בקשה.

**מחזיר:** dict: אובייקט תגובה.

**מעלה:**

`RuntimeError`: אם פרמטר הבקשה לא מצוין.

### `start(self, blueprint_name, id, description, parameters=None)`

התחלת מופע flow חדש מתבנית (blueprint).

**ארגומנטים:**

`blueprint_name`: שם התבנית (blueprint) לשימוש.
`id`: מזהה ייחודי למופע ה-flow.
`description`: תיאור קריא.
`parameters`: מילון פרמטרים אופציונלי.

**דוגמה:**

```python
api.flow().start(
    blueprint_name="default",
    id="my-flow",
    description="My custom flow",
    parameters={"model": "gpt-4"}
)
```

### `stop(self, id)`

עצירת מופע זרימה פעיל.

**ארגומנטים:**

`id`: מזהה של מופע הזרימה שיש לעצור.

**דוגמה:**

```python
api.flow().stop("my-flow")
```


--

## `FlowInstance`

```python
from trustgraph.api import FlowInstance
```

מופע לקוח של Flow לביצוע שירותים ב-flow ספציפי.

מחלקה זו מספקת גישה לכל שירותי TrustGraph, כולל:
השלמת טקסט והטמעות
פעולות סוכן עם ניהול מצב
שאילתות RAG עבור גרפים ומסמכים
פעולות גרף ידע (טריפלטים, אובייקטים)
טעינה ועיבוד מסמכים
המרה משפה טבעית לשאילתת GraphQL
ניתוח נתונים מובנים וזיהוי סכימה
ביצוע כלי MCP
תבניות הנחיה

לשירותים ניגשים באמצעות מופע Flow פעיל, המזוהה באמצעות מזהה.

### שיטות

### `__init__(self, api, id)`

אתחול FlowInstance.

**ארגומנטים:**

`api`: לקוח Flow ראשי
`id`: מזהה מופע Flow

### `agent(self, question, user='trustgraph', state=None, group=None, history=None)`

ביצוע פעולת סוכן עם יכולות חשיבה ושימוש בכלים.

סוכנים יכולים לבצע חשיבה רב-שלבית, להשתמש בכלים ולשמור על שיחה
מצב בין אינטראקציות. זו גרסה סינכרונית שאינה זורמת.

**ארגומנטים:**

`question`: שאלה או הוראה של משתמש
`user`: מזהה משתמש (ברירת מחדל: "trustgraph")
`state`: מילון מצב אופציונלי לשיחות עם מצב
`group`: מזהה קבוצה אופציונלי עבור הקשרים מרובי משתמשים
`history`: היסטוריית שיחה אופציונלית כרשימה של מילוני הודעות

**מחזיר:** str: תשובה סופית של הסוכן

**דוגמה:**

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

זיהוי סוג הנתונים של דוגמת נתונים מובנים.

**ארגומנטים:**

`sample`: דוגמת נתונים לניתוח (תוכן מחרוזת)

**החזרות:** מילון עם detected_type, confidence, ומטא-נתונים אופציונליים

### `diagnose_data(self, sample, schema_name=None, options=None)`

ביצוע אבחון נתונים משולב: זיהוי סוג ויצירת תיאור.

**ארגומנטים:**

`sample`: דוגמת נתונים לניתוח (תוכן מחרוזת)
`schema_name`: שם סכימה יעד אופציונלי ליצירת תיאור
`options`: פרמטרים אופציונליים (לדוגמה, מפריד עבור CSV)

**החזרות:** מילון עם detected_type, confidence, descriptor, ומטא-נתונים

### `document_embeddings_query(self, text, user, collection, limit=10)`

שאילתת מקטעי מסמכים באמצעות דמיון סמנטי.

מוצאת מקטעי מסמכים שהתוכן שלהם דומה מבחינה סמנטית לטקסט
הקלט, תוך שימוש בהטמעות וקטוריות.

**ארגומנטים:**

`text`: טקסט שאילתה לחיפוש סמנטי
`user`: מזהה משתמש/מרחב מפתחות
`collection`: מזהה אוסף
`limit`: מספר מקסימלי של תוצאות (ברירת מחדל: 10)

**החזרות:** מילון: תוצאות שאילתה עם מקטעים המכילים chunk_id וציון

**דוגמה:**

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

הפעל שאילתה של יצירת טקסט מבוססת אחזור מוגבר (RAG) על מסמכים.

RAG מבוסס מסמכים משתמש בהטמעות וקטוריות כדי למצוא מקטעי מסמכים רלוונטיים,
ולאחר מכן מייצר תגובה באמצעות מודל שפה גדול (LLM) תוך שימוש במקטעים אלה כהקשר.

**ארגומנטים:**

`query`: שאילתה בשפה טבעית
`user`: מזהה משתמש/מרחב מפתחות (ברירת מחדל: "trustgraph")
`collection`: מזהה אוסף (ברירת מחדל: "default")
`doc_limit`: מספר מקסימלי של מקטעי מסמכים שיש לשלוף (ברירת מחדל: 10)

**החזרות:** str: תגובה שנוצרה המשלבת הקשר של מסמכים

**דוגמה:**

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

יצירת הטמעות וקטוריות עבור טקסט אחד או יותר.

ממיר טקסטים לייצוגים וקטוריים צפופים המתאימים לחיפוש סמנטי
והשוואת דמיון.

**ארגומנטים:**

`texts`: רשימה של טקסטים קלט ליצירת הטמעות

**החזרות:** list[list[list[float]]]: הטמעות וקטוריות, סט אחד לכל טקסט קלט

**דוגמה:**

```python
flow = api.flow().id("default")
vectors = flow.embeddings(["quantum computing"])
print(f"Embedding dimension: {len(vectors[0][0])}")
```

### `generate_descriptor(self, sample, data_type, schema_name, options=None)`

יצירת תיאור עבור מיפוי נתונים מובנים לתוך סכימה ספציפית.

**ארגומנטים:**

`sample`: דוגמת נתונים לניתוח (תוכן מחרוזת)
`data_type`: סוג נתונים (csv, json, xml)
`schema_name`: שם הסכימה המיועדת ליצירת התיאור
`options`: פרמטרים אופציונליים (לדוגמה, מפריד עבור CSV)

**החזרות:** מילון עם התיאור ומטא-נתונים

### `graph_embeddings_query(self, text, user, collection, limit=10)`

שאילתת ישויות גרף ידע באמצעות דמיון סמנטי.

מציאת ישויות בגרף הידע שעבורן התיאורים שלהן דומים מבחינה סמנטית
לטקסט הקלט, תוך שימוש בהטמעות וקטוריות.

**ארגומנטים:**

`text`: טקסט שאילתה לחיפוש סמנטי
`user`: מזהה משתמש/מרחב מפתחות
`collection`: מזהה אוסף
`limit`: מספר מקסימלי של תוצאות (ברירת מחדל: 10)

**החזרות:** מילון: תוצאות שאילתה עם ישויות דומות

**דוגמה:**

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

הפעל שאילתה מבוססת גרפים של יצירת טקסט משופרת באמצעות אחזור (RAG).

Graph RAG משתמש במבנה של גרף ידע כדי למצוא הקשר רלוונטי על ידי
מעבר בין קשרים של ישויות, ולאחר מכן מייצר תגובה באמצעות מודל שפה גדול (LLM).

**ארגומנטים:**

`query`: שאילתה בשפה טבעית
`user`: מזהה משתמש/מרחב מפתחות (ברירת מחדל: "trustgraph")
`collection`: מזהה אוסף (ברירת מחדל: "default")
`entity_limit`: מספר הישויות המקסימלי שיש להחזיר (ברירת מחדל: 50)
`triple_limit`: מספר הטריפלים המקסימלי לישות (ברירת מחדל: 30)
`max_subgraph_size`: מספר הטריפלים הכולל המקסימלי בתת-גרף (ברירת מחדל: 150)
`max_path_length`: עומק מעבר מקסימלי (ברירת מחדל: 2)

**החזרות:** str: תגובה שנוצרה המשלבת הקשר גרפי

**דוגמה:**

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

טען מסמך בינארי לעיבוד.

העלאת מסמך (PDF, DOCX, תמונות וכו') לצורך חילוץ ו
עיבוד דרך צינור המסמכים של ה-flow.

**ארגומנטים:**

`document`: תוכן המסמך כבייטים
`id`: מזהה מסמך אופציונלי (נוצר אוטומטית אם לא קיים)
`metadata`: מטא-דאטה אופציונלי (רשימה של טריפלטים או אובייקט עם שיטת emit)
`user`: מזהה משתמש/מרחב מפתחות (אופציונלי)
`collection`: מזהה אוסף (אופציונלי)

**החזרות:** dict: תגובת עיבוד

**מעלה:**

`RuntimeError`: אם סופק מטא-דאטה ללא מזהה

**דוגמה:**

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

טעינת תוכן טקסטואלי לצורך עיבוד.

העלאת תוכן טקסטואלי לצורך חילוץ ועיבוד דרך צינור הטקסט של ה-flow.


**ארגומנטים:**

`text`: תוכן טקסטואלי בפורמט של בתים
`id`: מזהה מסמך אופציונלי (נוצר אוטומטית אם לא סופק)
`metadata`: מטא-דאטה אופציונלי (רשימה של טריפלטים או אובייקט עם שיטת emit)
`charset`: קידוד תווים (ברירת מחדל: "utf-8")
`user`: מזהה משתמש/מרחב מפתחות (אופציונלי)
`collection`: מזהה אוסף (אופציונלי)

**החזרות:** dict: תגובת עיבוד

**גורם לשגיאה:**

`RuntimeError`: אם סופק מטא-דאטה ללא מזהה

**דוגמה:**

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

הפעלת כלי פרוטוקול הקשר מודל (Model Context Protocol - MCP).

כלי MCP מספקים פונקציונליות ניתנת להרחבה עבור סוכנים ותהליכי עבודה,
ומאפשרים שילוב עם מערכות ושירותים חיצוניים.

**ארגומנטים:**

`name`: שם/מזהה הכלי
`parameters`: מילון פרמטרים של הכלי (ברירת מחדל: {})

**החזרות:** str או dict: תוצאת ביצוע הכלי

**מעלה:**

`ProtocolException`: אם פורמט התגובה אינו תקין

**דוגמה:**

```python
flow = api.flow().id("default")

# Execute a tool
result = flow.mcp_tool(
    name="search-web",
    parameters={"query": "latest AI news", "limit": 5}
)
```

### `nlp_query(self, question, max_results=100)`

המרת שאלה בשפה טבעית לשאילתת GraphQL.

**ארגומנטים:**

`question`: שאלה בשפה טבעית
`max_results`: מספר מקסימלי של תוצאות להחזרה (ברירת מחדל: 100)

**החזרות:** מילון עם graphql_query, variables, detected_schemas, confidence

### `prompt(self, id, variables)`

ביצוע תבנית שאילתה עם החלפת משתנים.

תבניות שאילתה מאפשרות דפוסי שאילתה לשימוש חוזר עם החלפת משתנים דינמית,
שימושי עבור הנדסת שאילתות עקבית.

**ארגומנטים:**

`id`: מזהה תבנית שאילתה
`variables`: מילון של התאמות בין שם משתנה לערך

**החזרות:** מחרוזת או מילון: תוצאת שאילתה מעובדת (טקסט או אובייקט מובנה)

**מעלה:**

`ProtocolException`: אם פורמט התגובה אינו תקין

**דוגמה:**

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

הגשת בקשה לשירות במקרה זה.

**ארגומנטים:**

`path`: נתיב השירות (לדוגמה, "service/text-completion")
`request`: מילון מטען הבקשה

**החזר:** dict: תגובת השירות

### `row_embeddings_query(self, text, schema_name, user='trustgraph', collection='default', index_name=None, limit=10)`

שאילתת נתוני שורה באמצעות דמיון סמנטי בשדות ממופים.

מוצאת שורות שבהן ערכי השדות הממופים דומים מבחינה סמנטית לטקסט
הקלט, תוך שימוש בהטמעות וקטוריות. זה מאפשר התאמה מעורפלת/סמנטית
בנתונים מובנים.

**ארגומנטים:**

`text`: טקסט שאילתה לחיפוש סמנטי
`schema_name`: שם הסכימה לחיפוש בתוכה
`user`: מזהה משתמש/אזור מפתחות (ברירת מחדל: "trustgraph")
`collection`: מזהה אוסף (ברירת מחדל: "default")
`index_name`: שם אינדקס אופציונלי לסינון החיפוש לאינדקס ספציפי
`limit`: מספר מקסימלי של תוצאות (ברירת מחדל: 10)

**החזר:** dict: תוצאות שאילתה עם התאמות המכילות index_name, index_value, text ו-score

**דוגמה:**

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

הפעל שאילתת GraphQL על שורות מובנות בגרף הידע.

שאילתות נתונים מובנים באמצעות תחביר GraphQL, המאפשר שאילתות מורכבות
עם סינון, אגרגציה וניווט ביחסים.

**ארגומנטים:**

`query`: מחרוזת שאילתת GraphQL
`user`: מזהה משתמש/מרחב (ברירת מחדל: "trustgraph")
`collection`: מזהה אוסף (ברירת מחדל: "default")
`variables`: מילון אופציונלי של משתני שאילתה
`operation_name`: שם פעולה אופציונלי עבור מסמכים מרובי פעולות

**החזרות:** dict: תגובת GraphQL עם השדות 'data', 'errors' ו/או 'extensions'

**מעלה:**

`ProtocolException`: אם מתרחשת שגיאה ברמת המערכת

**דוגמה:**

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

בחירת סכימות מתאימות עבור מדגם נתונים באמצעות ניתוח שאילתות.

**ארגומנטים:**

`sample`: מדגם נתונים לניתוח (תוכן מחרוזת)
`options`: פרמטרים אופציונליים

**החזרות:** מילון עם מערך schema_matches ומטא-נתונים

### `structured_query(self, question, user='trustgraph', collection='default')`

ביצוע שאילתה בשפה טבעית על נתונים מובנים.
משלב המרת שאילתות NLP וביצוע GraphQL.

**ארגומנטים:**

`question`: שאילתה בשפה טבעית
`user`: מזהה מרחב מפתחות Cassandra (ברירת מחדל: "trustgraph")
`collection`: מזהה אוסף נתונים (ברירת מחדל: "default")

**החזרות:** מילון עם נתונים ושגיאות אופציונליות

### `text_completion(self, system, prompt)`

ביצוע השלמת טקסט באמצעות מודל LLM של ה-flow.

**ארגומנטים:**

`system`: הנחיה מערכתית המגדירה את התנהגות העוזר
`prompt`: הנחיה/שאלה של משתמש

**החזרות:** מחרוזת: טקסט תגובה שנוצר

**דוגמה:**

```python
flow = api.flow().id("default")
response = flow.text_completion(
    system="You are a helpful assistant",
    prompt="What is quantum computing?"
)
print(response)
```

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=10000)`

שאילת משולשים בגרף ידע באמצעות התאמת תבניות.

מחפש משולשים RDF התואמים לתבניות נתונות של נושא, נשוא ואובייקט.
פרמטרים לא מוגדרים פועלים כתווים מתחלפים.

**ארגומנטים:**

`s`: מזהה URI של נושא (אופציונלי, השתמש ב-None עבור תו מתחלף)
`p`: מזהה URI של נשוא (אופציונלי, השתמש ב-None עבור תו מתחלף)
`o`: מזהה URI של אובייקט או ליטרל (אופציונלי, השתמש ב-None עבור תו מתחלף)
`user`: מזהה משתמש/מרחב מפתחות (אופציונלי)
`collection`: מזהה אוסף (אופציונלי)
`limit`: מספר תוצאות מקסימלי להחזרה (ברירת מחדל: 10000)

**מחזיר:** list[Triple]: רשימה של אובייקטי Triple התואמים

**מעלה:**

`RuntimeError`: אם s או p אינם Uri, או o אינם Uri/Literal

**דוגמה:**

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

לקוח לניהול זרימות אסינכרוניות באמצעות ממשק REST API.

מספק פעולות ניהול זרימות מבוססות async/await, כולל הצגת רשימה,
התחלה, עצירה וניהול הגדרות של סוגי זרימות. כמו כן, מספק
גישה לשירותים הקשורים לזרימה, כגון סוכנים, RAG ושאילתות, באמצעות נקודות קצה (endpoints) של REST שאינן מבוססות סטרימינג.


הערה: לתמיכה בסטרימינג, השתמשו ב-AsyncSocketClient.

### שיטות

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

אתחול לקוח זרימות אסינכרוני.

**ארגומנטים:**

`url`: כתובת URL בסיסית עבור ממשק ה-API של TrustGraph
`timeout`: זמן אחזור (timeout) לבקשות בשניות
`token`: טוקן bearer אופציונלי לאימות

### `aclose(self) -> None`

סגירת הלקוח האסינכרוני ושחרור משאבים.

הערה: ניקוי (cleanup) מטופל באופן אוטומטי על ידי מנהלי הקשר (context managers) של aiohttp.
שיטה זו מסופקת לשמירה על עקביות עם לקוחות אסינכרוניים אחרים.

### `delete_class(self, class_name: str)`

מחיקת הגדרת סוג זרימה.

מסירה תבנית (blueprint) של סוג זרימה מהמערכת. אינה משפיעה על
מופעי זרימה פעילים.

**ארגומנטים:**

`class_name`: שם סוג הזרימה למחיקה

**דוגמה:**

```python
async_flow = await api.async_flow()

# Delete a flow class
await async_flow.delete_class("old-flow-class")
```

### `get(self, id: str) -> Dict[str, Any]`

קבלת הגדרת זרימה.

מאחזר את תצורת הזרימה המלאה, כולל שם המחלקה שלה,
התיאור שלה והפרמטרים שלה.

**ארגומנטים:**

`id`: מזהה זרימה

**החזרות:** dict: אובייקט הגדרת זרימה

**דוגמה:**

```python
async_flow = await api.async_flow()

# Get flow definition
flow_def = await async_flow.get("default")
print(f"Flow class: {flow_def.get('class-name')}")
print(f"Description: {flow_def.get('description')}")
```

### `get_class(self, class_name: str) -> Dict[str, Any]`

קבלת הגדרת מחלקת זרימה.

מאחזר את הגדרת התוכנית עבור מחלקת זרימה, כולל
הסכימה שלה והקישורים לשירותים.

**ארגומנטים:**

`class_name`: שם מחלקת הזרימה

**החזרות:** dict: אובייקט הגדרת מחלקת זרימה

**דוגמה:**

```python
async_flow = await api.async_flow()

# Get flow class definition
class_def = await async_flow.get_class("default")
print(f"Services: {class_def.get('services')}")
```

### `id(self, flow_id: str)`

קבלת מופע לקוח של זרימה אסינכרונית.

מחזיר לקוח לצורך אינטראקציה עם השירותים של זרימה ספציפית (סוכן, RAG, שאילתות, הטמעות, וכו').


**ארגומנטים:**

`flow_id`: מזהה זרימה

**מחזיר:** AsyncFlowInstance: לקוח לפעולות ספציפיות לזרימה

**דוגמה:**

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

רשום את כל מזהי הזרימות.

שולף את ה-IDs של כל הזרימות הפרוסות כרגע במערכת.

**מחזיר:** list[str]: רשימה של מזהי זרימות

**דוגמה:**

```python
async_flow = await api.async_flow()

# List all flows
flows = await async_flow.list()
print(f"Available flows: {flows}")
```

### `list_classes(self) -> List[str]`

רשום את כל שמות מחלקות הזרימה.

שולף את שמות כל מחלקות הזרימה (תבניות) הזמינות במערכת.

**מחזיר:** list[str]: רשימה של שמות מחלקות זרימה.

**דוגמה:**

```python
async_flow = await api.async_flow()

# List available flow classes
classes = await async_flow.list_classes()
print(f"Available flow classes: {classes}")
```

### `put_class(self, class_name: str, definition: Dict[str, Any])`

יצירה או עדכון של הגדרה של מחלקת זרימה.

מאחסן תוכנית אב למחלקת זרימה שניתן להשתמש בה כדי ליצור מופעים של זרימות.

**ארגומנטים:**

`class_name`: שם מחלקת הזרימה
`definition`: אובייקט הגדרת מחלקת הזרימה

**דוגמה:**

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

ביצוע בקשת HTTP POST אסינכרונית ל-API של ה-Gateway.

שיטה פנימית לביצוע בקשות מאומתות ל-API של TrustGraph.

**ארגומנטים:**

`path`: נתיב נקודת הקצה של ה-API (ביחס לכתובת הבסיס)
`request_data`: מילון מטען הבקשה

**מחזיר:** dict: אובייקט תגובה מה-API

**מעלה:**

`ProtocolException`: אם קוד ה-HTTP אינו 200 או שהתגובה אינה JSON חוקי.
`ApplicationException`: אם ה-API מחזיר תגובת שגיאה.

### `start(self, class_name: str, id: str, description: str, parameters: Dict | None = None)`

התחל מופע זרימה חדש.

יוצר ומפעיל זרימה מתוך הגדרת מחלקת זרימה עם הפרמטרים שצוינו.


**ארגומנטים:**

`class_name`: שם המחלקה של הזרימה שצריך ליצור מופע עבורה.
`id`: מזהה עבור מופע הזרימה החדש.
`description`: תיאור קריא של הזרימה.
`parameters`: פרמטרי תצורה אופציונליים עבור הזרימה.

**דוגמה:**

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

עצירת תהליך פעיל.

עוצרת ומסירה מופע של תהליך, תוך שחרור המשאבים שלו.

**ארגומנטים:**

`id`: מזהה של התהליך שיש לעצור

**דוגמה:**

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

לקוח מופע זרימה אסינכרוני.

מספק גישה ל-async/await לשירותים המוגדרים בזרימה, כולל סוכנים,
שאילתות RAG, הטמעות ושאילתות גרף. כל הפעולות מחזירות
תגובות מלאות (לא בסטרימינג).

הערה: לצורך תמיכה בסטרימינג, השתמשו ב-AsyncSocketFlowInstance.

### שיטות

### `__init__(self, flow: trustgraph.api.async_flow.AsyncFlow, flow_id: str)`

אתחול מופע זרימה אסינכרוני.

**ארגומנטים:**

`flow`: לקוח AsyncFlow הראשי
`flow_id`: מזהה הזרימה

### `agent(self, question: str, user: str, state: Dict | None = None, group: str | None = None, history: List | None = None, **kwargs: Any) -> Dict[str, Any]`

ביצוע פעולה של סוכן (לא בסטרימינג).

מפעיל סוכן כדי לענות על שאלה, עם מצב שיחה ואפשרויות
היסטוריה. מחזיר את התגובה המלאה לאחר שהסוכן סיים
לעבד.

הערה: שיטה זו אינה תומכת בסטרימינג. לצורך מחשבות ותצפיות של הסוכן בזמן אמת,
השתמשו ב-AsyncSocketFlowInstance.agent() במקום.

**ארגומנטים:**

`question`: שאלה או הוראה של המשתמש
`user`: מזהה המשתמש
`state`: מילון מצב אופציונלי עבור הקשר שיחה
`group`: מזהה קבוצה אופציונלי לניהול סשנים
`history`: רשימת היסטוריית שיחה אופציונלית
`**kwargs`: פרמטרים נוספים ספציפיים לשירות

**מחזיר:** dict: תגובת סוכן מלאה הכוללת תשובה ומטא-נתונים

**דוגמה:**

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

ביצוע שאילתת RAG מבוססת מסמכים (לא סטרימינג).

מבצע יצירת טקסט מועשרת באמצעות הטמעות מסמכים.
שולף קטעי מסמכים רלוונטיים באמצעות חיפוש סמנטי, ולאחר מכן מייצר
תשובה המבוססת על המסמכים שנשלפו. מחזיר תשובה מלאה.

הערה: שיטה זו אינה תומכת בסטרימינג. עבור תגובות RAG בסטרימינג,
השתמשו ב-AsyncSocketFlowInstance.document_rag() במקום זאת.

**ארגומנטים:**

`query`: טקסט השאילתה של המשתמש
`user`: מזהה המשתמש
`collection`: מזהה האוסף המכיל מסמכים
`doc_limit`: מספר מרבי של קטעי מסמכים לשליפה (ברירת מחדל: 10)
`**kwargs`: פרמטרים נוספים ספציפיים לשירות

**החזרות:** str: תשובה מלאה שנוצרה המבוססת על נתוני המסמכים

**דוגמה:**

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

יצירת הטמעות עבור טקסטים קלט.

ממיר טקסטים לייצוגים וקטוריים מספריים באמצעות מודל ההטמעה המוגדר של ה-flow.
שימושי לחיפוש סמנטי והשוואות דמיון.


**ארגומנטים:**

`texts`: רשימה של טקסטים קלט ליצירת הטמעה
`**kwargs`: פרמטרים נוספים ספציפיים לשירות

**החזרות:** dict: תגובה המכילה וקטורי הטמעה

**דוגמה:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Generate embeddings
result = await flow.embeddings(texts=["Sample text to embed"])
vectors = result.get("vectors")
print(f"Embedding dimension: {len(vectors[0][0])}")
```

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any)`

שאילתת הטמעות גרף לחיפוש ישויות סמנטי.

מבצעת חיפוש סמנטי על הטמעות ישויות גרף כדי למצוא ישויות
הרלוונטיות ביותר לטקסט הקלט. מחזירה ישויות מדורגות לפי מידת הדמיון.

**ארגומנטים:**

`text`: טקסט שאילתה לחיפוש סמנטי
`user`: מזהה משתמש
`collection`: מזהה אוסף המכיל הטמעות גרף
`limit`: מספר מקסימלי של תוצאות להחזרה (ברירת מחדל: 10)
`**kwargs`: פרמטרים נוספים ספציפיים לשירות

**החזרות:** dict: תגובה המכילה התאמות ישויות מדורגות עם ציוני דמיון

**דוגמה:**

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

ביצוע שאילתת RAG מבוססת גרפים (לא בסטרימינג).

מבצע יצירת טקסט מועשרת באמצעות נתוני גרף ידע.
מזהה ישויות רלוונטיות ויחסים ביניהן, ולאחר מכן מייצר
תשובה המבוססת על מבנה הגרף. מחזיר תשובה מלאה.

הערה: שיטה זו אינה תומכת בסטרימינג. עבור תשובות RAG בסטרימינג,
השתמשו ב-AsyncSocketFlowInstance.graph_rag() במקום זאת.

**ארגומנטים:**

`query`: טקסט השאילתה של המשתמש
`user`: מזהה המשתמש
`collection`: מזהה אוסף המכיל את גרף הידע
`max_subgraph_size`: מספר מקסימלי של משולשים לכל תת-גרף (ברירת מחדל: 1000)
`max_subgraph_count`: מספר מקסימלי של תת-גרפים לשליפה (ברירת מחדל: 5)
`max_entity_distance`: מרחק גרף מקסימלי עבור הרחבת ישויות (ברירת מחדל: 3)
`**kwargs`: פרמטרים נוספים ספציפיים לשירות

**החזרות:** str: תשובה מלאה שנוצרה המבוססת על נתוני גרף

**דוגמה:**

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

בקשת שימוש בשירות המוגדר בתוך ה-flow.

שיטה פנימית לביצוע קריאות לשירותים בתוך מופע ה-flow הנוכחי.

**ארגומנטים:**

`service`: שם השירות (לדוגמה, "agent", "graph-rag", "triples")
`request_data`: עומס (payload) של הבקשה לשירות

**החזר:** dict: אובייקט תגובה מהשירות

**יוצא מכלל אפשרות (Raises):**

`ProtocolException`: אם הבקשה נכשלת או שהתגובה אינה תקינה
`ApplicationException`: אם השירות מחזיר שגיאה

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs: Any)`

שאילתת הטמעות שורות לחיפוש סמנטי בנתונים מובנים.

מבצעת חיפוש סמנטי על הטמעות אינדקס השורות כדי למצוא שורות שעבורן
ערכי השדות המאונדקסים דומים ביותר לטקסט הקלט. מאפשרת
התאמה מעורפלת/סמנטית על נתונים מובנים.

**ארגומנטים:**

`text`: טקסט השאילתה לחיפוש סמנטי
`schema_name`: שם הסכימה לחיפוש בתוכה
`user`: מזהה משתמש (ברירת מחדל: "trustgraph")
`collection`: מזהה אוסף (ברירת מחדל: "default")
`index_name`: שם אינדקס אופציונלי לסינון החיפוש לאינדקס ספציפי
`limit`: מספר מקסימלי של תוצאות להחזרה (ברירת מחדל: 10)
`**kwargs`: פרמטרים נוספים ספציפיים לשירות

**החזר:** dict: תגובה המכילה התאמות עם index_name, index_value, text ו-score

**דוגמה:**

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

הפעלת שאילתת GraphQL על שורות שמורות.

שאילתות שורות נתונים מובנים באמצעות תחביר GraphQL. תומך בשאילתות מורכבות
עם משתנים ופעולות בעלות שם.

**ארגומנטים:**

`query`: מחרוזת שאילתת GraphQL
`user`: מזהה משתמש
`collection`: מזהה אוסף המכיל שורות
`variables`: משתנים אופציונליים לשאילתת GraphQL
`operation_name`: שם פעולה אופציונלי עבור שאילתות מרובות פעולות
`**kwargs`: פרמטרים נוספים ספציפיים לשירות

**החזרות:** dict: תגובת GraphQL עם נתונים ושגיאות

**דוגמה:**

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

יצירת השלמת טקסט (לא בזמן אמת).

מייצרת תגובת טקסט ממודל שפה גדול (LLM) בהתבסס על הנחיה מערכתית והנחיה ממשתמש.
מחזירה את טקסט התגובה השלם.

הערה: שיטה זו אינה תומכת בסטרימינג. לטקסט שנוצר בזמן אמת,
השתמשו ב-AsyncSocketFlowInstance.text_completion() במקום זאת.

**ארגומנטים:**

`system`: הנחיה מערכתית המגדירה את התנהגות ה-LLM.
`prompt`: הנחיה ממשתמש או שאלה.
`**kwargs`: פרמטרים נוספים ספציפיים לשירות.

**מחזיר:** str: תגובת טקסט שנוצרת בשלמותה.

**דוגמה:**

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

שאילת משולשות RDF באמצעות התאמת תבניות.

מחפשת משולשות התואמות לתבניות הנקובות עבור הנושא, הנשוא ו/או
האובייקט. תבניות משתמשות ב-None כתווית מתקן כדי להתאים לכל ערך.

**ארגומנטים:**

`s`: תבנית נושא (None עבור תווית מתקן)
`p`: תבנית נשוא (None עבור תווית מתקן)
`o`: תבנית אובייקט (None עבור תווית מתקן)
`user`: מזהה משתמש (None עבור כל המשתמשים)
`collection`: מזהה אוסף (None עבור כל האוספים)
`limit`: מספר מקסימלי של משולשות להחזרה (ברירת מחדל: 100)
`**kwargs`: פרמטרים נוספים ספציפיים לשירות

**החזרות:** dict: תגובה המכילה משולשות תואמות

**דוגמה:**

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

לקוח WebSocket סינכרוני לפעולות סטרימינג.

מספק ממשק סינכרוני לשירותי TrustGraph המבוססים על WebSocket,
תוך שימוש בספריית websockets אסינכרונית עם גנרטורים סינכרוניים לנוחות השימוש.
תומך בתגובות סטרימינג מסוכנים, שאילתות RAG והשלמות טקסט.

הערה: זהו עטיפה סינכרונית סביב פעולות WebSocket אסינכרוניות. לצורך
תמיכה אסינכרונית אמיתית, השתמש ב-AsyncSocketClient.

### שיטות

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

אתחול לקוח WebSocket סינכרוני.

**ארגומנטים:**

`url`: כתובת URL בסיסית עבור ממשק ה-API של TrustGraph (HTTP/HTTPS יומרו ל-WS/WSS)
`timeout`: זמן קצוב של WebSocket בשניות
`token`: טוקן bearer אופציונלי לאימות

### `close(self) -> None`

סגירת חיבורי WebSocket.

הערה: ניקוי מתבצע באופן אוטומטי על ידי מנהלי הקשר באסינכרוני.

### `flow(self, flow_id: str) -> 'SocketFlowInstance'`

קבלת מופע זרימה לפעולות סטרימינג של WebSocket.

**ארגומנטים:**

`flow_id`: מזהה זרימה

**מחזיר:** SocketFlowInstance: מופע זרימה עם שיטות סטרימינג

**דוגמה:**

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

מופע של זרימת WebSocket סינכרונית עבור פעולות סטרימינג.

מספק את אותו ממשק כמו FlowInstance של REST, אך עם תמיכה בסטרימינג מבוסס WebSocket
עבור תגובות בזמן אמת. כל השיטות תומכות בפרמטר אופציונלי
`streaming` כדי לאפשר שליחת תוצאות מצטברות.

### שיטות

### `__init__(self, client: trustgraph.api.socket_client.SocketClient, flow_id: str) -> None`

אתחול מופע זרימת שקע.

**ארגומנטים:**

`client`: שרת שקעים הורה (Parent SocketClient)
`flow_id`: מזהה זרימה

### `agent(self, question: str, user: str, state: Dict[str, Any] | None = None, group: str | None = None, history: List[Dict[str, Any]] | None = None, streaming: bool = False, **kwargs: Any) -> Dict[str, Any] | Iterator[trustgraph.api.types.StreamingChunk]`

ביצוע פעולת סוכן עם תמיכה בסטרימינג.

סוכנים יכולים לבצע ניתוח רב-שלבי עם שימוש בכלים. שיטה זו תמיד
מחזירה מקטעי סטרימינג (מחשבות, תצפיות, תשובות), גם כאשר
streaming=False, כדי להציג את תהליך החשיבה של הסוכן.

**ארגומנטים:**

`question`: שאלה או הוראה מהמשתמש
`user`: מזהה משתמש
`state`: מילון מצב אופציונלי לשיחות עם מצב (stateful)
`group`: מזהה קבוצה אופציונלי עבור הקשרים מרובי משתמשים
`history`: היסטוריית שיחה אופציונלית כרשימה של מילוני הודעות
`streaming`: הפעלת מצב סטרימינג (ברירת מחדל: False)
`**kwargs`: פרמטרים נוספים המועברים לשירות הסוכן

**מחזיר:** Iterator[StreamingChunk]: זרם של מחשבות, תצפיות ותשובות של הסוכן

**דוגמה:**

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

הפעל פעולה של סוכן עם תמיכה בהסבר.

מעביר גם חלקי תוכן (AgentThought, AgentObservation, AgentAnswer)
וגם אירועי מקור (ProvenanceEvent). אירועי מקור מכילים URI שניתן לשלוף
באמצעות ExplainabilityClient כדי לקבל מידע מפורט על תהליך החשיבה של הסוכן.


מעקב אחר הסוכן מורכב מ:
Session: השאלה הראשונית ומטא-נתונים של הסשן
Iterations: כל מחזור מחשבה/פעולה/תצפית
Conclusion: התשובה הסופית

**ארגומנטים:**

`question`: שאלה או הוראה של המשתמש
`user`: מזהה משתמש
`collection`: מזהה אוסף לאחסון מקור
`state`: מילון מצב אופציונלי לשיחות עם מצב
`group`: מזהה קבוצה אופציונלי עבור הקשרים מרובי משתמשים
`history`: היסטוריית שיחה אופציונלית כרשימה של מילוני הודעות
`**kwargs`: פרמטרים נוספים המועברים לשירות הסוכן
`Yields`: 
`Union[StreamingChunk, ProvenanceEvent]`: חלקי סוכן ואירועי מקור

**דוגמה:**

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

שאילתת מקטעי מסמכים באמצעות דמיון סמנטי.

**ארגומנטים:**

`text`: טקסט שאילתה לחיפוש סמנטי
`user`: מזהה משתמש/מרחב מפתחות
`collection`: מזהה אוסף
`limit`: מספר מקסימלי של תוצאות (ברירת מחדל: 10)
`**kwargs`: פרמטרים נוספים המועברים לשירות

**החזרות:** dict: תוצאות שאילתה עם מזהי מקטעים של מקטעי מסמכים תואמים

**דוגמה:**

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

הפעל שאילתת RAG מבוססת מסמכים עם אפשרות של סטרימינג.

משתמש בהטמעות וקטוריות כדי למצוא מקטעי מסמכים רלוונטיים, ולאחר מכן מייצר
תגובה באמצעות מודל שפה גדול (LLM). מצב הסטרימינג מספק תוצאות באופן מצטבר.

**ארגומנטים:**

`query`: שאילתה בשפה טבעית
`user`: מזהה משתמש/מרחב
`collection`: מזהה אוסף
`doc_limit`: מספר מקסימלי של מקטעי מסמכים לשליפה (ברירת מחדל: 10)
`streaming`: הפעל מצב סטרימינג (ברירת מחדל: False)
`**kwargs`: פרמטרים נוספים המועברים לשירות

**החזרות:** Union[str, Iterator[str]]: תגובה מלאה או זרם של מקטעי טקסט

**דוגמה:**

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

הפעל שאילתת RAG מבוססת מסמכים עם תמיכה בהסבר.

מעביר גם מקטעי תוכן (RAGChunk) וגם אירועי מקור (ProvenanceEvent).
אירועי מקור מכילים URI שניתן לשלוף באמצעות ExplainabilityClient
כדי לקבל מידע מפורט על האופן שבו התגובה נוצרה.

מעקב RAG של מסמך מורכב מ:
שאלה: השאילתה של המשתמש
חיפוש: מקטעים שנשלפו ממאגר המסמכים (chunk_count)
סינתזה: התשובה שנוצרה

**ארגומנטים:**

`query`: שאילתה בשפה טבעית
`user`: מזהה משתמש/מרחב מפתחות
`collection`: מזהה אוסף
`doc_limit`: מספר מקסימלי של מקטעי מסמכים לשליפה (ברירת מחדל: 10)
`**kwargs`: פרמטרים נוספים המועברים לשירות
`Yields`: 
`Union[RAGChunk, ProvenanceEvent]`: מקטעי תוכן ואירועי מקור

**דוגמה:**

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

יצירת הטמעות וקטוריות עבור טקסט אחד או יותר.

**ארגומנטים:**

`texts`: רשימה של טקסטים קלט ליצירת הטמעות
`**kwargs`: פרמטרים נוספים המועברים לשירות

**החזרות:** dict: תגובה המכילה וקטורים (סט אחד לכל טקסט קלט)

**דוגמה:**

```python
socket = api.socket()
flow = socket.flow("default")

result = flow.embeddings(["quantum computing"])
vectors = result.get("vectors", [])
```

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any) -> Dict[str, Any]`

שאילת שאילתות לישות גרף ידע באמצעות דמיון סמנטי.

**ארגומנטים:**

`text`: טקסט שאילתה לחיפוש סמנטי
`user`: מזהה משתמש/מרחב מפתחות
`collection`: מזהה אוסף
`limit`: מספר מקסימלי של תוצאות (ברירת מחדל: 10)
`**kwargs`: פרמטרים נוספים המועברים לשירות

**החזרות:** dict: תוצאות שאילתה עם ישויות דומות

**דוגמה:**

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

הפעל שאילתת RAG מבוססת גרפים עם סטרימינג אופציונלי.

משתמש במבנה גרף ידע כדי למצוא הקשר רלוונטי, ולאחר מכן מייצר
תגובה באמצעות מודל שפה גדול (LLM). מצב הסטרימינג מספק תוצאות באופן מצטבר.

**ארגומנטים:**

`query`: שאילתה בשפה טבעית
`user`: מזהה משתמש/מרחב
`collection`: מזהה אוסף
`max_subgraph_size`: מספר מקסימלי של משולשים בסך הכל בגרף המשנה (ברירת מחדל: 1000)
`max_subgraph_count`: מספר מקסימלי של גרפים משניים (ברירת מחדל: 5)
`max_entity_distance`: עומק מעבר מקסימלי (ברירת מחדל: 3)
`streaming`: הפעל מצב סטרימינג (ברירת מחדל: False)
`**kwargs`: פרמטרים נוספים המועברים לשירות

**מחזיר:** Union[str, Iterator[str]]: תגובה מלאה או זרם של פיסות טקסט

**דוגמה:**

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

הפעל שאילתת RAG מבוססת גרפים עם תמיכה בהסבר.

מעביר גם מקטעי תוכן (RAGChunk) וגם אירועי מקור (ProvenanceEvent).
אירועי מקור מכילים URI שניתן לשלוף באמצעות ExplainabilityClient
כדי לקבל מידע מפורט על האופן שבו התגובה נוצרה.

**ארגומנטים:**

`query`: שאילתה בשפה טבעית
`user`: מזהה משתמש/מרחב
`collection`: מזהה אוסף
`max_subgraph_size`: מספר מקסימלי של משולשים בסך הכל בגרף המשנה (ברירת מחדל: 1000)
`max_subgraph_count`: מספר מקסימלי של גרפי משנה (ברירת מחדל: 5)
`max_entity_distance`: עומק מעבר מקסימלי (ברירת מחדל: 3)
`**kwargs`: פרמטרים נוספים המועברים לשירות
`Yields`: 
`Union[RAGChunk, ProvenanceEvent]`: מקטעי תוכן ואירועי מקור

**דוגמה:**

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

הפעלת כלי פרוטוקול הקשר מודל (MCP).

**ארגומנטים:**

`name`: שם/מזהה הכלי
`parameters`: מילון פרמטרים של הכלי
`**kwargs`: פרמטרים נוספים המועברים לשירות

**החזר:** dict: תוצאת ביצוע הכלי

**דוגמה:**

```python
socket = api.socket()
flow = socket.flow("default")

result = flow.mcp_tool(
    name="search-web",
    parameters={"query": "latest AI news", "limit": 5}
)
```

### `prompt(self, id: str, variables: Dict[str, str], streaming: bool = False, **kwargs: Any) -> str | Iterator[str]`

הפעל תבנית פקודה עם אפשרות של סטרימינג.

**ארגומנטים:**

`id`: מזהה של תבנית הפקודה
`variables`: מילון של התאמות בין שם משתנה לערך
`streaming`: הפעל מצב סטרימינג (ברירת מחדל: False)
`**kwargs`: פרמטרים נוספים המועברים לשירות

**החזר:** Union[str, Iterator[str]]: תגובה מלאה או סטרימינג של פיסות טקסט

**דוגמה:**

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

שליפת נתוני שורה באמצעות דמיון סמנטי בשדות ממופים.

מאתר שורות שבהן ערכי השדות הממופים דומים מבחינה סמנטית ל-
הטקסט הקלט, תוך שימוש בהטמעות וקטוריות. זה מאפשר התאמה מעורפלת/סמנטית
לנתונים מובנים.

**ארגומנטים:**

`text`: טקסט שאילתה לחיפוש סמנטי
`schema_name`: שם הסכימה לחיפוש בתוכה
`user`: מזהה משתמש/אזור מפתחות (ברירת מחדל: "trustgraph")
`collection`: מזהה אוסף (ברירת מחדל: "default")
`index_name`: שם אינדקס אופציונלי לסינון החיפוש לאינדקס ספציפי
`limit`: מספר מקסימלי של תוצאות (ברירת מחדל: 10)
`**kwargs`: פרמטרים נוספים המועברים לשירות

**החזרות:** dict: תוצאות שאילתה עם התאמות המכילות index_name, index_value, text ו-score

**דוגמה:**

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

הפעלת שאילתת GraphQL על שורות מובנות.

**ארגומנטים:**

`query`: מחרוזת שאילתת GraphQL
`user`: מזהה משתמש/מרחב מפתחות
`collection`: מזהה אוסף
`variables`: מילון אופציונלי של משתני שאילתה
`operation_name`: שם פעולה אופציונלי עבור מסמכים מרובי פעולות
`**kwargs`: פרמטרים נוספים המועברים לשירות

**החזרות:** dict: תגובת GraphQL עם נתונים, שגיאות ו/או הרחבות

**דוגמה:**

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

הפעלת השלמת טקסט עם אפשרות של סטרימינג.

**ארגומנטים:**

`system`: הנחיה למערכת המגדירה את התנהגות העוזר.
`prompt`: הנחיה/שאלה מהמשתמש.
`streaming`: הפעל מצב סטרימינג (ברירת מחדל: False).
`**kwargs`: פרמטרים נוספים המועברים לשירות.

**החזר:** Union[str, Iterator[str]]: תשובה מלאה או סטרימינג של פיסות טקסט.

**דוגמה:**

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

שאילתת משולשים בגרף ידע באמצעות התאמת תבניות.

**ארגומנטים:**

`s`: מסנן נושא - מחרוזת URI, מילון מונחים, או None עבור wildcard
`p`: מסנן נשוא - מחרוזת URI, מילון מונחים, או None עבור wildcard
`o`: מסנן אובייקט - מחרוזת URI/literal, מילון מונחים, או None עבור wildcard
`g`: מסנן גרף מוגדר - מחרוזת URI או None עבור כל הגרפים
`user`: מזהה משתמש/מרחב מפתחות (אופציונלי)
`collection`: מזהה אוסף (אופציונלי)
`limit`: מספר תוצאות מקסימלי להחזרה (ברירת מחדל: 100)
`**kwargs`: פרמטרים נוספים המועברים לשירות

**החזרות:** List[Dict]: רשימה של משולשים תואמים בפורמט פנימי

**דוגמה:**

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

שאילת משולשים בגרף ידע באמצעות אצוות סטרימינג.

מחזירה אצוות של משולשים כשהם מגיעים, מה שמקטין את הזמן לקבלת התוצאה הראשונה
ואת צריכת הזיכרון עבור קבוצות תוצאות גדולות.

**ארגומנטים:**

`s`: מסנן נושא - מחרוזת URI, מילון מונחים, או None עבור wildcard
`p`: מסנן נשוא - מחרוזת URI, מילון מונחים, או None עבור wildcard
`o`: מסנן אובייקט - מחרוזת URI/ליטרל, מילון מונחים, או None עבור wildcard
`g`: מסנן גרף מוגדר - מחרוזת URI או None עבור כל הגרפים
`user`: מזהה משתמש/מרחב מפתחות (אופציונלי)
`collection`: מזהה אוסף (אופציונלי)
`limit`: מספר תוצאות מקסימלי להחזרה (ברירת מחדל: 100)
`batch_size`: משולשים לאצווה (ברירת מחדל: 20)
`**kwargs`: פרמטרים נוספים המועברים לשירות
`Yields`: 
`List[Dict]`: אצוות של משולשים בפורמט wire

**דוגמה:**

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

לקוח WebSocket אסינכרוני

### שיטות

### `__init__(self, url: str, timeout: int, token: str | None)`

אתחול עצמי. עיין ב-help(type(self)) לקבלת חתימה מדויקת.

### `aclose(self)`

סגירת חיבור WebSocket

### `flow(self, flow_id: str)`

קבלת מופע זרימה אסינכרוני עבור פעולות WebSocket


--

## `AsyncSocketFlowInstance`

```python
from trustgraph.api import AsyncSocketFlowInstance
```

מופע של זרימת WebSocket אסינכרונית

### שיטות

### `__init__(self, client: trustgraph.api.async_socket_client.AsyncSocketClient, flow_id: str)`

אתחול של self. עיין ב-help(type(self)) לקבלת חתימה מדויקת.

### `agent(self, question: str, user: str, state: Dict[str, Any] | None = None, group: str | None = None, history: list | None = None, streaming: bool = False, **kwargs) -> Dict[str, Any] | AsyncIterator`

סוכן עם סטרימינג אופציונלי

### `document_rag(self, query: str, user: str, collection: str, doc_limit: int = 10, streaming: bool = False, **kwargs)`

תיעוד RAG עם סטרימינג אופציונלי

### `embeddings(self, texts: list, **kwargs)`

יצירת הטמעות טקסט

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs)`

שאילתא של הטמעות גרף לחיפוש סמנטי

### `graph_rag(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, streaming: bool = False, **kwargs)`

RAG גרפי עם סטרימינג אופציונלי

### `mcp_tool(self, name: str, parameters: Dict[str, Any], **kwargs)`

הרצת כלי MCP

### `prompt(self, id: str, variables: Dict[str, str], streaming: bool = False, **kwargs)`

הרצת שאילתא עם סטרימינג אופציונלי

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs)`

שאילתא של הטמעות שורות לחיפוש סמנטי על נתונים מובנים

### `rows_query(self, query: str, user: str, collection: str, variables: Dict | None = None, operation_name: str | None = None, **kwargs)`

שאילתא GraphQL על שורות מובנות

### `text_completion(self, system: str, prompt: str, streaming: bool = False, **kwargs)`

השלמת טקסט עם סטרימינג אופציונלי

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=100, **kwargs)`

שאילתא של תבנית משולשת


--

### `build_term(value: Any, term_type: str | None = None, datatype: str | None = None, language: str | None = None) -> Dict[str, Any] | None`

בניית מילון Term בפורמט wire מתוך ערך.

כללי זיהוי אוטומטיים (כאשר term_type הוא None):
  כבר מילון עם מפתח 't' -> החזר כפי שהוא (כבר Term)
  מתחיל עם http://, https://, urn: -> IRI
  עטוף בסוגריים זוויתיים (לדוגמה, <http://...>) -> IRI (סוגריים זוויתיים מוסרים)
  כל דבר אחר -> מילולי

**ארגומנטים:**

`value`: ערך ה-term (מחרוזת, מילון או None)
`term_type`: אחד מ-'iri', 'literal' או None לזיהוי אוטומטי
`datatype`: סוג נתונים עבור אובייקטים מילוליים (לדוגמה, xsd:integer)
`language`: תג שפה עבור אובייקטים מילוליים (לדוגמה, en)

**החזרות:** dict: מילון Term בפורמט wire, או None אם הערך הוא None


--

## `BulkClient`

```python
from trustgraph.api import BulkClient
```

לקוח לפעולות מרובות סינכרוניות לייבוא/ייצוא.

מספק העברת נתונים מרובה יעילה באמצעות WebSocket עבור מערכי נתונים גדולים.
עוטף פעולות WebSocket אסינכרוניות עם גנרטורים סינכרוניים לנוחות השימוש.

הערה: לתמיכה אסינכרונית אמיתית, השתמש ב-AsyncBulkClient במקום.

### שיטות

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

אתחול לקוח מרובה סינכרוני.

**ארגומנטים:**

`url`: כתובת URL בסיסית עבור ממשק ה-API של TrustGraph (HTTP/HTTPS יומרו ל-WS/WSS)
`timeout`: זמן קצוב של WebSocket בשניות
`token`: טוקן bearer אופציונלי לאימות

### `close(self) -> None`

סגירת חיבורים

### `export_document_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

ייצוא מרובה של הטמעות מסמכים מתוך זרימה.

מוריד ביעילות את כל הטמעות חלקי המסמכים באמצעות סטרימינג של WebSocket.

**ארגומנטים:**

`flow`: מזהה זרימה
`**kwargs`: פרמטרים נוספים (שמורים לשימוש עתידי)

**מחזיר:** Iterator[Dict[str, Any]]: זרם של מילוני הטמעה

**דוגמה:**

```python
bulk = api.bulk()

# Export and process document embeddings
for embedding in bulk.export_document_embeddings(flow="default"):
    chunk_id = embedding.get("chunk_id")
    vector = embedding.get("embedding")
    print(f"{chunk_id}: {len(vector)} dimensions")
```

### `export_entity_contexts(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

ייצוא בכמות גדולה של הקשרים של ישויות מתוך זרימה.

מוריד ביעילות את כל מידע ההקשר של הישויות באמצעות סטרימינג WebSocket.

**ארגומנטים:**

`flow`: מזהה זרימה
`**kwargs`: פרמטרים נוספים (שמורים לשימוש עתידי)

**מחזיר:** Iterator[Dict[str, Any]]: זרם של מילוני הקשר

**דוגמה:**

```python
bulk = api.bulk()

# Export and process entity contexts
for context in bulk.export_entity_contexts(flow="default"):
    entity = context.get("entity")
    text = context.get("context")
    print(f"{entity}: {text[:100]}...")
```

### `export_graph_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

ייצוא המוני של הטמעות גרפים מתוך זרימה.

מוריד ביעילות את כל הטמעות ישויות הגרף באמצעות סטרימינג WebSocket.

**ארגומנטים:**

`flow`: מזהה זרימה
`**kwargs`: פרמטרים נוספים (שמורים לשימוש עתידי)

**מחזיר:** Iterator[Dict[str, Any]]: זרם של מילוני הטמעות

**דוגמה:**

```python
bulk = api.bulk()

# Export and process embeddings
for embedding in bulk.export_graph_embeddings(flow="default"):
    entity = embedding.get("entity")
    vector = embedding.get("embedding")
    print(f"{entity}: {len(vector)} dimensions")
```

### `export_triples(self, flow: str, **kwargs: Any) -> Iterator[trustgraph.api.types.Triple]`

ייצוא בכמות גדולה של משולשים RDF מתוך זרימה.

מוריד ביעילות את כל המשולשים באמצעות סטרימינג WebSocket.

**ארגומנטים:**

`flow`: מזהה זרימה
`**kwargs`: פרמטרים נוספים (שמורים לשימוש עתידי)

**מחזיר:** Iterator[Triple]: זרם של אובייקטי Triple

**דוגמה:**

```python
bulk = api.bulk()

# Export and process triples
for triple in bulk.export_triples(flow="default"):
    print(f"{triple.s} -> {triple.p} -> {triple.o}")
```

### `import_document_embeddings(self, flow: str, embeddings: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

ייבוא המוני של הטמעות מסמכים לתוך זרימה.

העלאה יעילה של הטמעות מקטעי מסמכים באמצעות סטרימינג WebSocket
לשימוש בשאילתות RAG של מסמכים.

**ארגומנטים:**

`flow`: מזהה זרימה
`embeddings`: איטרטור המפיק מילוני הטמעות
`**kwargs`: פרמטרים נוספים (שמורים לשימוש עתידי)

**דוגמה:**

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

ייבוא בכמות גדולה של הקשרים של ישויות לתוך זרימה.

מעלה ביעילות מידע על הקשר של ישויות באמצעות סטרימינג WebSocket.
הקשרים של ישויות מספקים הקשר טקסטואלי נוסף לגבי ישויות גרף
לשיפור ביצועי RAG.

**ארגומנטים:**

`flow`: מזהה של זרימה
`contexts`: איטרטור המפיק מילוני הקשר
`metadata`: מילון מטא-נתונים עם id, מטא-נתונים, משתמש, אוסף
`batch_size`: מספר הקשרים בכל אצווה (ברירת מחדל 100)
`**kwargs`: פרמטרים נוספים (שמורים לשימוש עתידי)

**דוגמה:**

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

ייבוא המוני של הטמעות גרפים לתוך זרימה.

העלאה יעילה של הטמעות ישויות גרפים באמצעות סטרימינג WebSocket.

**ארגומנטים:**

`flow`: מזהה זרימה
`embeddings`: איטרטור המפיק מילוני הטמעות
`**kwargs`: פרמטרים נוספים (שמורים לשימוש עתידי)

**דוגמה:**

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

ייבוא בכמות גדולה של שורות מובנות לתוך זרימה.

העלאה יעילה של שורות נתונים מובנים באמצעות סטרימינג WebSocket
לשימוש בשאילתות GraphQL.

**ארגומנטים:**

`flow`: מזהה זרימה
`rows`: איטרטור המפיק מילוני שורות
`**kwargs`: פרמטרים נוספים (שמורים לשימוש עתידי)

**דוגמה:**

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

ייבוא בכמות גדולה של משולשים RDF לתוך זרימה.

מעלה ביעילות מספר גדול של משולשים באמצעות סטרימינג WebSocket.

**ארגומנטים:**

`flow`: מזהה של הזרימה
`triples`: איטרטור המפיק אובייקטי Triple
`metadata`: מילון מטא-דאטה עם מזהה, מטא-דאטה, משתמש, אוסף
`batch_size`: מספר המשולשים בכל אצווה (ברירת מחדל 100)
`**kwargs`: פרמטרים נוספים (שמורים לשימוש עתידי)

**דוגמה:**

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

לקוח לפעולות אסינכרוניות בכמות גדולה

### שיטות

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

אתחול של self.  עיין ב-help(type(self)) לקבלת חתימה מדויקת.

### `aclose(self) -> None`

סגירת חיבורים

### `export_document_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

ייצוא בכמות גדולה של הטמעות מסמכים באמצעות WebSocket

### `export_entity_contexts(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

ייצוא בכמות גדולה של הקשרים של ישויות באמצעות WebSocket

### `export_graph_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

ייצוא בכמות גדולה של הטמעות גרפים באמצעות WebSocket

### `export_triples(self, flow: str, **kwargs: Any) -> AsyncIterator[trustgraph.api.types.Triple]`

ייצוא בכמות גדולה של משולשות באמצעות WebSocket

### `import_document_embeddings(self, flow: str, embeddings: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

ייבוא בכמות גדולה של הטמעות מסמכים באמצעות WebSocket

### `import_entity_contexts(self, flow: str, contexts: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

ייבוא בכמות גדולה של הקשרים של ישויות באמצעות WebSocket

### `import_graph_embeddings(self, flow: str, embeddings: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

ייבוא בכמות גדולה של הטמעות גרפים באמצעות WebSocket

### `import_rows(self, flow: str, rows: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

ייבוא בכמות גדולה של שורות באמצעות WebSocket

### `import_triples(self, flow: str, triples: AsyncIterator[trustgraph.api.types.Triple], **kwargs: Any) -> None`

ייבוא בכמות גדולה של משולשות באמצעות WebSocket


--

## `Metrics`

```python
from trustgraph.api import Metrics
```

לקוח למדדי סינכרוניים

### שיטות

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

אתחול של self. עיין ב-help(type(self)) לקבלת חתימה מדויקת.

### `get(self) -> str`

קבלת מדדי Prometheus כטקסט


--

## `AsyncMetrics`

```python
from trustgraph.api import AsyncMetrics
```

לקוח מדדים אסינכרוני

### שיטות

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

אתחול self. עיין ב-help(type(self)) לקבלת חתימה מדויקת.

### `aclose(self) -> None`

סגירת חיבורים

### `get(self) -> str`

קבלת מדדי Prometheus כטקסט


--

## `ExplainabilityClient`

```python
from trustgraph.api import ExplainabilityClient
```

לקוח לשליפת ישויות הסברתיות עם טיפול בעקביות סופית.

משתמש בגילוי שקט: שליפה, המתנה, שליפה חוזרת, השוואה.
אם התוצאות זהות, הנתונים יציבים.

### שיטות

### `__init__(self, flow_instance, retry_delay: float = 0.2, max_retries: int = 10)`

אתחול לקוח הסברתי.

**ארגומנטים:**

`flow_instance`: מופע SocketFlowInstance לשליפת משולשות
`retry_delay`: השהייה בין ניסיונות חוזרים בשניות (ברירת מחדל: 0.2)
`max_retries`: מספר מקסימלי של ניסיונות חוזרים (ברירת מחדל: 10)

### `detect_session_type(self, session_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> str`

זיהוי האם סשן הוא מסוג GraphRAG או Agent.

**ארגומנטים:**

`session_uri`: ה-URI של הסשן/שאלה
`graph`: גרף מוגדר
`user`: מזהה משתמש/מרחב מפתחות
`collection`: מזהה אוסף

**מחזיר:** "graphrag" או "agent"

### `fetch_agent_trace(self, session_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

שליפת רצף ה-Agent השלם החל מ-URI של סשן.

עוקב אחר שרשרת המוצא: שאלה -> ניתוח (ים) -> מסקנה

**ארגומנטים:**

`session_uri`: ה-URI של סשן/שאלה של ה-agent
`graph`: גרף מוגדר (ברירת מחדל: urn:graph:retrieval)
`user`: מזהה משתמש/מרחב מפתחות
`collection`: מזהה אוסף
`api`: מופע TrustGraph Api לגישה לספרן (אופציונלי)
`max_content`: אורך תוכן מקסימלי למסקנה

**מחזיר:** מילון עם שאלה, איטרציות (רשימת ניתוחים), ישויות מסקנה

### `fetch_docrag_trace(self, question_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

שליפת רצף ה-DocumentRAG השלם החל מ-URI של שאלה.

עוקב אחר שרשרת המוצא:
    שאלה -> עיגון -> חקירה -> סינתזה

**ארגומנטים:**

`question_uri`: ה-URI של ישות השאלה
`graph`: גרף מוגדר (ברירת מחדל: urn:graph:retrieval)
`user`: מזהה משתמש/מרחב מפתחות
`collection`: מזהה אוסף
`api`: מופע TrustGraph Api לגישה לספרן (אופציונלי)
`max_content`: אורך תוכן מקסימלי לסינתזה

**מחזיר:** מילון עם שאלה, עיגון, חקירה, ישויות סינתזה

### `fetch_document_content(self, document_uri: str, api: Any, user: str | None = None, max_content: int = 10000) -> str`

שליפת תוכן מהספרן לפי URI של מסמך.

**ארגומנטים:**

`document_uri`: ה-URI של המסמך בספרן
`api`: מופע TrustGraph Api לגישה לספרן
`user`: מזהה משתמש עבור הספרן
`max_content`: אורך תוכן מקסימלי להחזרה

**מחזיר:** התוכן של המסמך כרצף

### `fetch_edge_selection(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.EdgeSelection | None`

שליפת ישות בחירת קצה (משמשת על ידי Focus).

**ארגומנטים:**

`uri`: ה-URI של בחירת הקצה
`graph`: גרף מוגדר לשליפה
`user`: מזהה משתמש/מרחב מפתחות
`collection`: מזהה אוסף

**מחזיר:** EdgeSelection או None אם לא נמצא

### `fetch_entity(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.ExplainEntity | None`

שליפת ישות הסברות באמצעות URI עם טיפול בעקביות סופית.

משתמש בגילוי שקטות:
1. שליפת משולשים עבור URI
2. אם אין תוצאות, לנסות שוב
3. אם יש תוצאות, לחכות ולשלוף שוב
4. אם התוצאות זהות, הנתונים יציבים - לנתח ולהחזיר
5. אם התוצאות שונות, הנתונים עדיין נכתבים - לנסות שוב

**ארגומנטים:**

`uri`: ה-URI של הישות שיש לשלוף
`graph`: גרף בעל שם לשאילתה (לדוגמה, "urn:graph:retrieval")
`user`: מזהה משתמש/מרחב מפתחות
`collection`: מזהה אוסף

**החזרות:** תת-מחלקה של ExplainEntity או None אם לא נמצא

### `fetch_focus_with_edges(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.Focus | None`

שליפת ישות Focus וכל בחירות הקצוות שלה.

**ארגומנטים:**

`uri`: ה-URI של ישות ה-Focus
`graph`: גרף בעל שם לשאילתה
`user`: מזהה משתמש/מרחב מפתחות
`collection`: מזהה אוסף

**החזרות:** Focus עם edge_selections מאוכלס, או None

### `fetch_graphrag_trace(self, question_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

שליפת עקבות GraphRAG מלאים החל מ-URI של שאלה.

עוקבים אחר שרשרת המוצא: שאלה -> עיגון -> חקירה -> Focus -> סינתזה

**ארגומנטים:**

`question_uri`: ה-URI של ישות השאלה
`graph`: גרף (ברירת מחדל: urn:graph:retrieval)
`user`: מזהה משתמש/מרחב מפתחות
`collection`: מזהה אוסף
`api`: מופע של TrustGraph Api לגישה לספרן (אופציונלי)
`max_content`: אורך תוכן מקסימלי לסינתזה

**החזרות:** מילון עם ישויות שאלה, עיגון, חקירה, focus, סינתזה

### `list_sessions(self, graph: str | None = None, user: str | None = None, collection: str | None = None, limit: int = 50) -> List[trustgraph.api.explainability.Question]`

רשימת כל סשנים של הסברות (שאלות) באוסף.

**ארגומנטים:**

`graph`: גרף (ברירת מחדל: urn:graph:retrieval)
`user`: מזהה משתמש/מרחב מפתחות
`collection`: מזהה אוסף
`limit`: מספר הסשנים המקסימלי להחזרה

**החזרות:** רשימה של ישויות שאלה ממוינות לפי חותם זמן (חדש ביותר קודם)

### `resolve_edge_labels(self, edge: Dict[str, str], user: str | None = None, collection: str | None = None) -> Tuple[str, str, str]`

פתרון תוויות עבור כל רכיבים של משולש קצה.

**ארגומנטים:**

`edge`: מילון עם מפתחות "s", "p", "o"
`user`: מזהה משתמש/מרחב מפתחות
`collection`: מזהה אוסף

**החזרות:** טאפל של (s_label, p_label, o_label)

### `resolve_label(self, uri: str, user: str | None = None, collection: str | None = None) -> str`

פתרון rdfs:label עבור URI, עם שמירה במטמון.

**ארגומנטים:**

`uri`: ה-URI לקבלת התווית
`user`: מזהה משתמש/מרחב מפתחות
`collection`: מזהה אוסף

**החזרות:** התווית אם נמצאה, אחרת ה-URI עצמו


--

## `ExplainEntity`

```python
from trustgraph.api import ExplainEntity
```

מחלקה בסיסית עבור ישויות הסברתיות.

**שדות:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>

### שיטות

### `__init__(self, uri: str, entity_type: str = '') -> None`

אתחול עצמי. עיין ב-help(type(self)) לקבלת חתימה מדויקת.


--

## `Question`

```python
from trustgraph.api import Question
```

שאילתת משתמש - השאלה שהתחילה את הסשן.

**שדות:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`query`: <class 'str'>
`timestamp`: <class 'str'>
`question_type`: <class 'str'>

### שיטות

### `__init__(self, uri: str, entity_type: str = '', query: str = '', timestamp: str = '', question_type: str = '') -> None`

אתחול עצמי. עיין ב-help(type(self)) לקבלת חתימה מדויקת.


--

## `Exploration`

```python
from trustgraph.api import Exploration
```

ישות חקירה - קצוות/חלקים שאוחזרו ממאגר הידע.

**שדות:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`edge_count`: <class 'int'>
`chunk_count`: <class 'int'>
`entities`: typing.List[str]

### שיטות

### `__init__(self, uri: str, entity_type: str = '', edge_count: int = 0, chunk_count: int = 0, entities: List[str] = <factory>) -> None`

אתחול עצמי. עיין ב-help(type(self)) לקבלת חתימה מדויקת.


--

## `Focus`

```python
from trustgraph.api import Focus
```

ישות ממוקדת - קצוות נבחרים עם ניתוח באמצעות מודל שפה גדול (GraphRAG בלבד).

**שדות:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`selected_edge_uris`: typing.List[str]
`edge_selections`: typing.List[trustgraph.api.explainability.EdgeSelection]

### שיטות

### `__init__(self, uri: str, entity_type: str = '', selected_edge_uris: List[str] = <factory>, edge_selections: List[trustgraph.api.explainability.EdgeSelection] = <factory>) -> None`

אתחול עצמי. עיין ב-help(type(self)) לקבלת חתימה מדויקת.


--

## `Synthesis`

```python
from trustgraph.api import Synthesis
```

ישות סינתטית - התשובה הסופית.

**שדות:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`document`: <class 'str'>

### שיטות

### `__init__(self, uri: str, entity_type: str = '', document: str = '') -> None`

אתחול self. עיין ב-help(type(self)) לקבלת חתימה מדויקת.


--

## `Analysis`

```python
from trustgraph.api import Analysis
```

ישות ניתוח - מחזור מחשבה/פעולה/תצפית (לסוכן בלבד).

**שדות:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`action`: <class 'str'>
`arguments`: <class 'str'>
`thought`: <class 'str'>
`observation`: <class 'str'>

### שיטות

### `__init__(self, uri: str, entity_type: str = '', action: str = '', arguments: str = '', thought: str = '', observation: str = '') -> None`

אתחול עצמי. עיין ב-help(type(self)) לקבלת חתימה מדויקת.


--

## `Conclusion`

```python
from trustgraph.api import Conclusion
```

סיכום - תשובה סופית (לסוכן בלבד).

**שדות:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`document`: <class 'str'>

### שיטות

### `__init__(self, uri: str, entity_type: str = '', document: str = '') -> None`

אתחול self. עיין ב-help(type(self)) לקבלת חתימה מדויקת.


--

## `EdgeSelection`

```python
from trustgraph.api import EdgeSelection
```

צומת שנבחר עם הסבר משלב GraphRAG Focus.

**שדות:**

`uri`: <class 'str'>
`edge`: typing.Dict[str, str] | None
`reasoning`: <class 'str'>

### שיטות

### `__init__(self, uri: str, edge: Dict[str, str] | None = None, reasoning: str = '') -> None`

אתחול self.  עיין ב-help(type(self)) לקבלת חתימה מדויקת.


--

### `wire_triples_to_tuples(wire_triples: List[Dict[str, Any]]) -> List[Tuple[str, str, Any]]`

המרת משולשות בפורמט wire לטופלים (s, p, o).


--

### `extract_term_value(term: Dict[str, Any]) -> Any`

חילוץ ערך ממילון Term בפורמט wire.


--

## `Triple`

```python
from trustgraph.api import Triple
```

משפט גרף ידע המיוצג על ידי טריפל RDF.

**שדות:**

`s`: <class 'str'>
`p`: <class 'str'>
`o`: <class 'str'>

### שיטות

### `__init__(self, s: str, p: str, o: str) -> None`

אתחול self. עיין ב-help(type(self)) לקבלת חתימה מדויקת.


--

## `Uri`

```python
from trustgraph.api import Uri
```

str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

יצירת אובייקט מחרוזת חדש מהאובייקט הנתון. אם צוינו קידוד (encoding) או
טיפול בשגיאות (errors), אז האובייקט חייב לחשוף מאגר נתונים
שייקוד באמצעות הקידוד ומטפל השגיאות שצוינו.
אחרת, מוחזר התוצאה של object.__str__() (אם מוגדר)
או repr(object).
ברירת המחדל של הקידוד היא 'utf-8'.
ברירת המחדל של טיפול בשגיאות היא 'strict'.

### שיטות

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

יצירת אובייקט מחרוזת חדש מהאובייקט הנתון. אם צוינו קידוד (encoding) או
טיפול בשגיאות (errors), אז האובייקט חייב לחשוף מאגר נתונים
שייקוד באמצעות הקידוד ומטפל השגיאות שצוינו.
אחרת, מוחזר התוצאה של object.__str__() (אם מוגדר)
או repr(object).
ברירת המחדל של קידוד היא 'utf-8'.
ברירת המחדל של טיפול בשגיאות היא 'strict'.

### שיטות

### `is_literal(self)`

### `is_triple(self)`

### `is_uri(self)`


--

## `ConfigKey`

```python
from trustgraph.api import ConfigKey
```

מזהה מפתח תצורה.

**שדות:**

`type`: <class 'str'>
`key`: <class 'str'>

### שיטות

### `__init__(self, type: str, key: str) -> None`

אתחול self. עיין ב-help(type(self)) לקבלת חתימה מדויקת.


--

## `ConfigValue`

```python
from trustgraph.api import ConfigValue
```

זוג מפתח-ערך של תצורה.

**שדות:**

`type`: <class 'str'>
`key`: <class 'str'>
`value`: <class 'str'>

### שיטות

### `__init__(self, type: str, key: str, value: str) -> None`

אתחול self. עיין ב-help(type(self)) לקבלת חתימה מדויקת.


--

## `DocumentMetadata`

```python
from trustgraph.api import DocumentMetadata
```

מטא-נתונים עבור מסמך בספרייה.

**תכונות:**

`parent_id: Parent document ID for child documents (empty for top`: level docs)

**שדות:**

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

### שיטות

### `__init__(self, id: str, time: datetime.datetime, kind: str, title: str, comments: str, metadata: List[trustgraph.api.types.Triple], user: str, tags: List[str], parent_id: str = '', document_type: str = 'source') -> None`

אתחול self. עיין ב-help(type(self)) לקבלת חתימה מדויקת.


--

## `ProcessingMetadata`

```python
from trustgraph.api import ProcessingMetadata
```

מטא-נתונים עבור משימת עיבוד מסמכים פעילה.

**שדות:**

`id`: <class 'str'>
`document_id`: <class 'str'>
`time`: <class 'datetime.datetime'>
`flow`: <class 'str'>
`user`: <class 'str'>
`collection`: <class 'str'>
`tags`: typing.List[str]

### שיטות

### `__init__(self, id: str, document_id: str, time: datetime.datetime, flow: str, user: str, collection: str, tags: List[str]) -> None`

אתחול self. עיין ב-help(type(self)) לקבלת חתימה מדויקת.


--

## `CollectionMetadata`

```python
from trustgraph.api import CollectionMetadata
```

מטא-נתונים עבור אוסף נתונים.

אוספים מספקים קיבוץ והפרדה לוגיים עבור מסמכים ונתוני גרף ידע.


**תכונות:**

`name: Human`: שם אוסף הניתן לקריאה

**שדות:**

`user`: <class 'str'>
`collection`: <class 'str'>
`name`: <class 'str'>
`description`: <class 'str'>
`tags`: typing.List[str]

### שיטות

### `__init__(self, user: str, collection: str, name: str, description: str, tags: List[str]) -> None`

אתחול self. עיין ב-help(type(self)) לקבלת חתימה מדויקת.


--

## `StreamingChunk`

```python
from trustgraph.api import StreamingChunk
```

מחלקה בסיסית עבור חלקי תגובה בסטרימינג.

משמשת לפעולות סטרימינג מבוססות WebSocket שבהן התגובות מועברות
בהדרגה כשהן נוצרות.

**שדות:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>

### שיטות

### `__init__(self, content: str, end_of_message: bool = False) -> None`

אתחול עצמי. עיין ב-help(type(self)) לקבלת חתימה מדויקת.


--

## `AgentThought`

```python
from trustgraph.api import AgentThought
```

קטע של נימוקים/תהליך חשיבה של הסוכן.

מייצג את תהליך החשיבה או שלבי התכנון הפנימיים של הסוכן במהלך הביצוע.
קטעים אלה מראים כיצד הסוכן חושב על הבעיה.

**שדות:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>

### שיטות

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'thought') -> None`

אתחול עצמי. עיין ב-help(type(self)) לקבלת חתימה מדויקת.


--

## `AgentObservation`

```python
from trustgraph.api import AgentObservation
```

קטע תצפית על ביצוע כלי.

מייצג את התוצאה או התצפית מהפעלת כלי או פעולה.
קטעים אלה מציגים מה שהסוכן למד משימוש בכלים.

**שדות:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>

### שיטות

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'observation') -> None`

אתחול self. עיין ב-help(type(self)) לקבלת חתימה מדויקת.


--

## `AgentAnswer`

```python
from trustgraph.api import AgentAnswer
```

חלק תשובה סופי של הסוכן.

מייצג את התגובה הסופית של הסוכן למשאלה של המשתמש לאחר השלמת
הניתוח והשימוש בכלי.

**מאפיינים:**

`chunk_type: Always "final`: answer"

**שדות:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>
`end_of_dialog`: <class 'bool'>

### שיטות

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'final-answer', end_of_dialog: bool = False) -> None`

אתחול self.  עיין ב-help(type(self)) לקבלת חתימה מדויקת.


--

## `RAGChunk`

```python
from trustgraph.api import RAGChunk
```

מקטע סטרימינג של RAG (יצירת טקסט מועשרת בשליפה).

משמש למענה סטרימינג מ-RAG גרפי, RAG של מסמכים, השלמת טקסט,
ושירותי יצירה אחרים.

**שדות:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>
`end_of_stream`: <class 'bool'>
`error`: typing.Dict[str, str] | None

### שיטות

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'rag', end_of_stream: bool = False, error: Dict[str, str] | None = None) -> None`

אתחול עצמי. עיין ב-help(type(self)) לקבלת חתימה מדויקת.


--

## `ProvenanceEvent`

```python
from trustgraph.api import ProvenanceEvent
```

אירוע מקור עבור הסברתיות.

נשלח במהלך שאילתות GraphRAG כאשר מצב ההסבר מופעל.
כל אירוע מייצג צומת מקור שנוצר במהלך עיבוד השאילתה.

**שדות:**

`explain_id`: <class 'str'>
`explain_graph`: <class 'str'>
`event_type`: <class 'str'>

### שיטות

### `__init__(self, explain_id: str, explain_graph: str = '', event_type: str = '') -> None`

אתחול self. עיין ב-help(type(self)) לקבלת חתימה מדויקת.


--

## `ProtocolException`

```python
from trustgraph.api import ProtocolException
```

מופעל כאשר מתרחשות שגיאות בפרוטוקול WebSocket.


--

## `TrustGraphException`

```python
from trustgraph.api import TrustGraphException
```

מחלקה בסיסית עבור כל שגיאות השירות של TrustGraph.


--

## `AgentError`

```python
from trustgraph.api import AgentError
```

שגיאת שירות סוכן


--

## `ConfigError`

```python
from trustgraph.api import ConfigError
```

שגיאת שירות תצורה


--

## `DocumentRagError`

```python
from trustgraph.api import DocumentRagError
```

שגיאת שליפה של מסמכים.


--

## `FlowError`

```python
from trustgraph.api import FlowError
```

שגיאת ניהול זרימה


--

## `GatewayError`

```python
from trustgraph.api import GatewayError
```

שגיאת שער API


--

## `GraphRagError`

```python
from trustgraph.api import GraphRagError
```

שגיאת שליפה של גרף RAG


--

## `LLMError`

```python
from trustgraph.api import LLMError
```

שגיאת שירות מודל שפה גדול (LLM).


--

## `LoadError`

```python
from trustgraph.api import LoadError
```

שגיאת טעינת נתונים


--

## `LookupError`

```python
from trustgraph.api import LookupError
```

שגיאת חיפוש/איתור


--

## `NLPQueryError`

```python
from trustgraph.api import NLPQueryError
```

שגיאת שירות שאילתות NLP.


--

## `RowsQueryError`

```python
from trustgraph.api import RowsQueryError
```

שגיאת שירות שאילתות שורות


--

## `RequestError`

```python
from trustgraph.api import RequestError
```

שגיאת עיבוד בקשה


--

## `StructuredQueryError`

```python
from trustgraph.api import StructuredQueryError
```

שגיאת שירות שאילתות מובנה.


--

## `UnexpectedError`

```python
from trustgraph.api import UnexpectedError
```

שגיאה בלתי צפויה/לא ידועה


--

## `ApplicationException`

```python
from trustgraph.api import ApplicationException
```

מחלקה בסיסית עבור כל שגיאות השירות של TrustGraph.


--
