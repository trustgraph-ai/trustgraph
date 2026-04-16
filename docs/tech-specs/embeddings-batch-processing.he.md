---
layout: default
title: "מפרט טכני לעיבוד אצווה של הטמעות (Embeddings)"
parent: "Hebrew (Beta)"
---

# מפרט טכני לעיבוד אצווה של הטמעות (Embeddings)

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## סקירה כללית

מפרט זה מתאר אופטימיזציות עבור שירות ההטמעות כדי לתמוך בעיבוד אצווה של מספר טקסטים בבקשה אחת. היישום הנוכחי מעבד טקסט אחד בכל פעם, ואינו מנצל את היתרונות המשמעותיים בביצועים שמודלי הטמעה מספקים בעת עיבוד אצוות.

1. **חוסר יעילות בעיבוד טקסט בודד**: היישום הנוכחי עוטף טקסטים בודדים ברשימה, ובכך אינו מנצל את יכולות האצווה של FastEmbed.
2. **תקורה של בקשה לטקסט**: כל טקסט דורש הודעת Pulsar נפרדת הלוך ושוב.
3. **חוסר יעילות בהסקת מודל**: למודלי הטמעה יש תקורה קבועה לכל אצווה; אצוות קטנות מבזבזות משאבי GPU/CPU.
4. **עיבוד סדרתי בלקוחות**: שירותים מרכזיים עוברים בלולאה על פריטים וקוראים להטמעות אחד בכל פעם.

## מטרות

**תמיכה בממשק API לאצוות**: לאפשר עיבוד של מספר טקסטים בבקשה אחת.
**תאימות לאחור**: לשמור על תמיכה בבקשות לטקסט בודד.
**שיפור משמעותי בביצועים**: לכוון לשיפור של 5-10x בביצועים עבור פעולות אצווה.
**הפחתת השהייה לטקסט**: להוריד את ההשהייה הממוצעת בעת הטמעת מספר טקסטים.
**יעילות בשימוש בזיכרון**: לעבד אצוות מבלי לצרוך כמות מוגזמת של זיכרון.
**אי-תלות בספק**: לתמוך באצוות בין FastEmbed, Ollama וספקים אחרים.
**מעבר של לקוחות**: לעדכן את כל לקוחות ההטמעות כדי להשתמש בממשק ה-API לאצוות כאשר זה מועיל.

## רקע

### יישום נוכחי - שירות הטמעות

היישום של ההטמעות ב-`trustgraph-flow/trustgraph/embeddings/fastembed/processor.py` מציג חוסר יעילות משמעותי בביצועים:

```python
# fastembed/processor.py line 56
async def on_embeddings(self, text, model=None):
    use_model = model or self.default_model
    self._load_model(use_model)

    vecs = self.embeddings.embed([text])  # Single text wrapped in list

    return [v.tolist() for v in vecs]
```

**בעיות:**

1. **גודל אצווה 1**: השיטה `embed()` של FastEmbed מותאמת לעיבוד באצווה, אך אנו תמיד משתמשים בה עם `[text]` - אצווה בגודל 1.

2. **תקורה לכל בקשה:** כל בקשת הטמעה כרוכה ב:
   סריאליזציה/דה-סריאליזציה של הודעת Pulsar
   השהייה של תקשורת רשת
   תקורה של אתחול הסקה של המודל
   תקורה של תזמון אסינכרוני של Python

3. **מגבלת סכימה:** הסכימה `EmbeddingsRequest` תומכת רק בטקסט אחד:
   ```python
   @dataclass
   class EmbeddingsRequest:
       text: str = ""  # Single text only
   ```

### לקוחות נוכחיים - עיבוד סדרתי

#### 1. שער API

**קובץ:** `trustgraph-flow/trustgraph/gateway/dispatch/embeddings.py`

השער מקבל בקשות להטמעה של טקסט בודד באמצעות HTTP/WebSocket ומעביר אותן לשירות ההטמעה. כרגע אין נקודת קצה לעיבוד אצווה.

```python
class EmbeddingsRequestor(ServiceRequestor):
    # Handles single EmbeddingsRequest -> EmbeddingsResponse
    request_schema=EmbeddingsRequest,  # Single text only
    response_schema=EmbeddingsResponse,
```

**השפעה:** לקוחות חיצוניים (אפליקציות אינטרנט, סקריפטים) חייבים לבצע N בקשות HTTP כדי להטמיע N טקסטים.

#### 2. שירות הטמעת מסמכים

**קובץ:** `trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py`

מעבד פיסות של מסמכים אחת בכל פעם:

```python
async def on_message(self, msg, consumer, flow):
    v = msg.value()

    # Single chunk per request
    resp = await flow("embeddings-request").request(
        EmbeddingsRequest(text=v.chunk)
    )
    vectors = resp.vectors
```

**השפעה:** כל חלק במסמך דורש קריאת הטמעה נפרדת. מסמך עם 100 חלקים = 100 בקשות הטמעה.

#### 3. שירות הטמעת גרפים

**קובץ:** `trustgraph-flow/trustgraph/embeddings/graph_embeddings/embeddings.py`

עובר בלולאה על ישויות ומטמיע כל אחת בנפרד:

```python
async def on_message(self, msg, consumer, flow):
    for entity in v.entities:
        # Serial embedding - one entity at a time
        vectors = await flow("embeddings-request").embed(
            text=entity.context
        )
        entities.append(EntityEmbeddings(
            entity=entity.entity,
            vectors=vectors,
            chunk_id=entity.chunk_id,
        ))
```

**השפעה:** הודעה עם 50 ישויות = 50 בקשות הטמעה סדרתיות. זהו צוואר בקבוק משמעותי במהלך בניית גרף ידע.

#### 4. שירות הטמעת שורות

**קובץ:** `trustgraph-flow/trustgraph/embeddings/row_embeddings/embeddings.py`

חוזר על טקסטים ייחודיים ומטמיע כל אחד מהם באופן סדרתי:

```python
async def on_message(self, msg, consumer, flow):
    for text, (index_name, index_value) in texts_to_embed.items():
        # Serial embedding - one text at a time
        vectors = await flow("embeddings-request").embed(text=text)

        embeddings_list.append(RowIndexEmbedding(
            index_name=index_name,
            index_value=index_value,
            text=text,
            vectors=vectors
        ))
```

**השפעה:** עיבוד טבלה עם 100 ערכים ייחודיים עם אינדקס = 100 בקשות הטמעה סדרתיות.

#### 5. EmbeddingsClient (לקוח בסיסי)

**קובץ:** `trustgraph-base/trustgraph/base/embeddings_client.py`

הלקוח המשמש את כל מעבדי הזרימה תומך רק בהטמעה של טקסט בודד:

```python
class EmbeddingsClient(RequestResponse):
    async def embed(self, text, timeout=30):
        resp = await self.request(
            EmbeddingsRequest(text=text),  # Single text
            timeout=timeout
        )
        return resp.vectors
```

**השפעה:** כל המשתמשים בלקוח זה מוגבלים לפעולות טקסט יחידות.

#### 6. כלי שורת הפקודה

**קובץ:** `trustgraph-cli/trustgraph/cli/invoke_embeddings.py`

כלי שורת הפקודה מקבל ארגומנט טקסט יחיד:

```python
def query(url, flow_id, text, token=None):
    result = flow.embeddings(text=text)  # Single text
    vectors = result.get("vectors", [])
```

**השפעה:** משתמשים אינם יכולים לבצע הטמעה אצווה משורת הפקודה. עיבוד קובץ של טקסטים דורש N הפעלות.

#### 7. ערכת פיתוח תוכנה (SDK) עבור Python

ערכת הפיתוח תוכנה עבור Python מספקת שתי מחלקות לקוח לצורך אינטראקציה עם שירותי TrustGraph. שתיהן תומכות רק בהטמעה של טקסט בודד.

**קובץ:** `trustgraph-base/trustgraph/api/flow.py`

```python
class FlowInstance:
    def embeddings(self, text):
        """Get embeddings for a single text"""
        input = {"text": text}
        return self.request("service/embeddings", input)["vectors"]
```

**קובץ:** `trustgraph-base/trustgraph/api/socket_client.py`

```python
class SocketFlowInstance:
    def embeddings(self, text: str, **kwargs: Any) -> Dict[str, Any]:
        """Get embeddings for a single text via WebSocket"""
        request = {"text": text}
        return self.client._send_request_sync(
            "embeddings", self.flow_id, request, False
        )
```

**השפעה:** מפתחי Python המשתמשים ב-SDK חייבים לעבור על הטקסטים ולבצע N קריאות API נפרדות. אין תמיכה בהטמעה באצווה עבור משתמשי ה-SDK.

### השפעה על הביצועים

עבור הכנסת מסמכים טיפוסית (1000 מקטעי טקסט):
**נוכחי**: 1000 בקשות נפרדות, 1000 קריאות למודל
**באצווה (batch_size=32)**: 32 בקשות, 32 קריאות למודל (הפחתה של 96.8%)

עבור הטמעת גרפים (הודעה עם 50 ישויות):
**נוכחי**: 50 קריאות await סדרתיות, ~5-10 שניות
**באצווה**: 1-2 קריאות באצווה, ~0.5-1 שניה (שיפור של 5-10x)

ספריות כמו FastEmbed ודומות משיגות התרחבות כמעט ליניארית של התפוקה עם גודל האצווה עד לגבולות החומרה (בדרך כלל 32-128 טקסטים לאצווה).

## עיצוב טכני

### ארכיטקטורה

אופטימיזציה של עיבוד אצווה להטמעות דורשת שינויים ברכיבים הבאים:

#### 1. **שיפור סכימה**
   הרחבת `EmbeddingsRequest` לתמיכה במספר טקסטים
   הרחבת `EmbeddingsResponse` להחזרת מספר סטים של וקטורים
   שמירה על תאימות לאחור לבקשות טקסט בודדות

   מודול: `trustgraph-base/trustgraph/schema/services/llm.py`

#### 2. **שיפור שירות בסיסי**
   עדכון `EmbeddingsService` לטיפול בבקשות באצווה
   הוספת תצורת גודל אצווה
   יישום טיפול בבקשות מודע לאצווה

   מודול: `trustgraph-base/trustgraph/base/embeddings_service.py`

#### 3. **עדכוני מעבד ספק**
   עדכון מעבד FastEmbed להעברת אצווה שלמה ל-`embed()`
   עדכון מעבד Ollama לטיפול באצווה (אם נתמך)
   הוספת עיבוד רציף כברירת מחדל עבור ספקים שאינם תומכים באצווה

   מודולים:
   `trustgraph-flow/trustgraph/embeddings/fastembed/processor.py`
   `trustgraph-flow/trustgraph/embeddings/ollama/processor.py`

#### 4. **שיפור לקוח**
   הוספת שיטה להטמעה באצווה ל-`EmbeddingsClient`
   תמיכה גם ב-API של טקסט בודד וגם ב-API של אצווה
   הוספת אצווה אוטומטית עבור קלט גדול

   מודול: `trustgraph-base/trustgraph/base/embeddings_client.py`

#### 5. **עדכוני קוראים - מעבדי זרימה**
   עדכון `graph_embeddings` לאצווה של הקשרים של ישויות
   עדכון `row_embeddings` לאצווה של טקסטים לאינדקס
   עדכון `document_embeddings` אם אצווה של הודעות אפשרית

   מודולים:
   `trustgraph-flow/trustgraph/embeddings/graph_embeddings/embeddings.py`
   `trustgraph-flow/trustgraph/embeddings/row_embeddings/embeddings.py`
   `trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py`

#### 6. **שיפור שער API**
   הוספת נקודת קצה להטמעה באצווה
   תמיכה במערך של טקסטים בגוף הבקשה

   מודול: `trustgraph-flow/trustgraph/gateway/dispatch/embeddings.py`

#### 7. **שיפור כלי שורת הפקודה**
   הוספת תמיכה במספר טקסטים או קלט של קובץ
   הוספת פרמטר גודל אצווה

   מודול: `trustgraph-cli/trustgraph/cli/invoke_embeddings.py`

#### 8. **שיפור SDK של Python**
   הוספת שיטה `embeddings_batch()` ל-`FlowInstance`
   הוספת שיטה `embeddings_batch()` ל-`SocketFlowInstance`
   תמיכה גם ב-API של טקסט בודד וגם ב-API של אצווה עבור משתמשי SDK

   מודולים:
   `trustgraph-base/trustgraph/api/flow.py`
   `trustgraph-base/trustgraph/api/socket_client.py`

### מודלים של נתונים

#### EmbeddingsRequest

```python
@dataclass
class EmbeddingsRequest:
    texts: list[str] = field(default_factory=list)
```

שימוש:
טקסט בודד: `EmbeddingsRequest(texts=["hello world"])`
אצווה: `EmbeddingsRequest(texts=["text1", "text2", "text3"])`

#### EmbeddingsResponse

```python
@dataclass
class EmbeddingsResponse:
    error: Error | None = None
    vectors: list[list[list[float]]] = field(default_factory=list)
```

מבנה התגובה:
`vectors[i]` מכיל את קבוצת הווקטורים עבור `texts[i]`
כל קבוצת וקטורים היא `list[list[float]]` (מודלים עשויים להחזיר מספר וקטורים עבור כל טקסט)
דוגמה: 3 טקסטים → `vectors` מכיל 3 רשומות, כאשר כל רשומה מכילה את הטבעות של הטקסט המתאים

### ממשקי API

#### EmbeddingsClient

```python
class EmbeddingsClient(RequestResponse):
    async def embed(
        self,
        texts: list[str],
        timeout: float = 300,
    ) -> list[list[list[float]]]:
        """
        Embed one or more texts in a single request.

        Args:
            texts: List of texts to embed
            timeout: Timeout for the operation

        Returns:
            List of vector sets, one per input text
        """
        resp = await self.request(
            EmbeddingsRequest(texts=texts),
            timeout=timeout
        )
        if resp.error:
            raise RuntimeError(resp.error.message)
        return resp.vectors
```

#### נקודת קצה של הטמעות (Embeddings) עבור שער API

נקודת קצה מעודכנת התומכת בהטמעה בודדת או באצווה:

```
POST /api/v1/embeddings
Content-Type: application/json

{
    "texts": ["text1", "text2", "text3"],
    "flow_id": "default"
}

Response:
{
    "vectors": [
        [[0.1, 0.2, ...]],
        [[0.3, 0.4, ...]],
        [[0.5, 0.6, ...]]
    ]
}
```

### פרטי יישום

#### שלב 1: שינויי סכימה

**EmbeddingsRequest:**
```python
@dataclass
class EmbeddingsRequest:
    texts: list[str] = field(default_factory=list)
```

**תגובת הטבעה (EmbeddingsResponse):**
```python
@dataclass
class EmbeddingsResponse:
    error: Error | None = None
    vectors: list[list[list[float]]] = field(default_factory=list)
```

**עדכון של EmbeddingsService.on_request:**
```python
async def on_request(self, msg, consumer, flow):
    request = msg.value()
    id = msg.properties()["id"]
    model = flow("model")

    vectors = await self.on_embeddings(request.texts, model=model)
    response = EmbeddingsResponse(error=None, vectors=vectors)

    await flow("response").send(response, properties={"id": id})
```

#### שלב 2: עדכון מעבד FastEmbed

**נוכחי (לא יעיל):**
```python
async def on_embeddings(self, text, model=None):
    use_model = model or self.default_model
    self._load_model(use_model)
    vecs = self.embeddings.embed([text])  # Batch of 1
    return [v.tolist() for v in vecs]
```

**עדכון:**
```python
async def on_embeddings(self, texts: list[str], model=None):
    """Embed texts - processes all texts in single model call"""
    if not texts:
        return []

    use_model = model or self.default_model
    self._load_model(use_model)

    # FastEmbed handles the full batch efficiently
    all_vecs = list(self.embeddings.embed(texts))

    # Return list of vector sets, one per input text
    return [[v.tolist()] for v in all_vecs]
```

#### שלב 3: עדכון שירות הטמעת גרפים

**נוכחי (סדרתי):**
```python
async def on_message(self, msg, consumer, flow):
    entities = []
    for entity in v.entities:
        vectors = await flow("embeddings-request").embed(text=entity.context)
        entities.append(EntityEmbeddings(...))
```

**עדכון (אצווה):**
```python
async def on_message(self, msg, consumer, flow):
    # Collect all contexts
    contexts = [entity.context for entity in v.entities]

    # Single batch embedding call
    all_vectors = await flow("embeddings-request").embed(texts=contexts)

    # Pair results with entities
    entities = [
        EntityEmbeddings(
            entity=entity.entity,
            vectors=vectors[0],  # First vector from the set
            chunk_id=entity.chunk_id,
        )
        for entity, vectors in zip(v.entities, all_vectors)
    ]
```

#### שלב 4: עדכון שירות הטמעת שורות

**נוכחי (סדרתי):**
```python
for text, (index_name, index_value) in texts_to_embed.items():
    vectors = await flow("embeddings-request").embed(text=text)
    embeddings_list.append(RowIndexEmbedding(...))
```

**עדכון (אצווה):**
```python
# Collect texts and metadata
texts = list(texts_to_embed.keys())
metadata = list(texts_to_embed.values())

# Single batch embedding call
all_vectors = await flow("embeddings-request").embed(texts=texts)

# Pair results
embeddings_list = [
    RowIndexEmbedding(
        index_name=meta[0],
        index_value=meta[1],
        text=text,
        vectors=vectors[0]  # First vector from the set
    )
    for text, meta, vectors in zip(texts, metadata, all_vectors)
]
```

#### שלב 5: שיפור כלי שורת הפקודה

**שורת פקודה מעודכנת:**
```python
def main():
    parser = argparse.ArgumentParser(...)

    parser.add_argument(
        'text',
        nargs='*',  # Zero or more texts
        help='Text(s) to convert to embedding vectors',
    )

    parser.add_argument(
        '-f', '--file',
        help='File containing texts (one per line)',
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='Batch size for processing (default: 32)',
    )
```

שימוש:
```bash
# Single text (existing)
tg-invoke-embeddings "hello world"

# Multiple texts
tg-invoke-embeddings "text one" "text two" "text three"

# From file
tg-invoke-embeddings -f texts.txt --batch-size 64
```

#### שלב 6: שיפור ערכת הפיתוח של Python

**FlowInstance (לקוח HTTP):**

```python
class FlowInstance:
    def embeddings(self, texts: list[str]) -> list[list[list[float]]]:
        """
        Get embeddings for one or more texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of vector sets, one per input text
        """
        input = {"texts": texts}
        return self.request("service/embeddings", input)["vectors"]
```

**SocketFlowInstance (לקוח WebSocket):**

```python
class SocketFlowInstance:
    def embeddings(self, texts: list[str], **kwargs: Any) -> list[list[list[float]]]:
        """
        Get embeddings for one or more texts via WebSocket.

        Args:
            texts: List of texts to embed

        Returns:
            List of vector sets, one per input text
        """
        request = {"texts": texts}
        response = self.client._send_request_sync(
            "embeddings", self.flow_id, request, False
        )
        return response["vectors"]
```

**דוגמאות לשימוש ב-SDK:**

```python
# Single text
vectors = flow.embeddings(["hello world"])
print(f"Dimensions: {len(vectors[0][0])}")

# Batch embedding
texts = ["text one", "text two", "text three"]
all_vectors = flow.embeddings(texts)

# Process results
for text, vecs in zip(texts, all_vectors):
    print(f"{text}: {len(vecs[0])} dimensions")
```

## שיקולי אבטחה

**מגבלות גודל בקשה**: אכוף גודל מקסימלי לאצווה כדי למנוע מיצוי משאבים
**טיפול בזמני המתנה**: התאם את זמני ההמתנה בהתאם לגודל האצווה
**מגבלות זיכרון**: עקוב אחר השימוש בזיכרון עבור אצוות גדולות
**אימות קלט**: אשר את כל הטקסטים באצווה לפני העיבוד

## שיקולי ביצועים

### שיפורים צפויים

**קצב העברה (Throughput):**
טקסט בודד: ~10-50 טקסטים/שנייה (תלוי במודל)
אצווה (גודל 32): ~200-500 טקסטים/שנייה (שיפור של 5-10x)

**זמן תגובה לטקסט:**
טקסט בודד: 50-200ms לטקסט
אצווה (גודל 32): 5-20ms לטקסט (ממוצע)

**שיפורים ספציפיים לשירות:**

| שירות | נוכחי | באצווה | שיפור |
|---------|---------|---------|-------------|
| הטמעת גרפים (50 ישויות) | 5-10 שניות | 0.5-1 שניות | 5-10x |
| הטמעת שורות (100 טקסטים) | 10-20 שניות | 1-2 שניות | 5-10x |
| קליטת מסמכים (1000 מקטעים) | 100-200 שניות | 10-30 שניות | 5-10x |

### פרמטרי תצורה

```python
# Recommended defaults
DEFAULT_BATCH_SIZE = 32
MAX_BATCH_SIZE = 128
BATCH_TIMEOUT_MULTIPLIER = 2.0
```

## אסטרטגיית בדיקות

### בדיקות יחידה
הטמעה של טקסט בודד (תאימות לאחור)
טיפול באצווה ריקה
אכיפת גודל אצווה מקסימלי
טיפול בשגיאות עבור כשלים חלקיים באצווה

### בדיקות אינטגרציה
הטמעת אצווה מקצה לקצה דרך Pulsar
עיבוד אצווה בשירות הטמעת גרפים
עיבוד אצווה בשירות הטמעת שורות
נקודת קצה של אצווה בשער ה-API

### בדיקות ביצועים
השוואת תפוקה של הטמעה בודדת לעומת אצווה
שימוש בזיכרון בגדלי אצווה שונים
ניתוח התפלגות השהייה

## תוכנית מעבר

זו גרסה הכוללת שינויים משמעותיים. כל השלבים מיושמים יחד.

### שלב 1: שינויי סכימה
החלפת `text: str` ב-`texts: list[str]` ב-EmbeddingsRequest
שינוי סוג של `vectors` ל-`list[list[list[float]]]` ב-EmbeddingsResponse

### שלב 2: עדכוני מעבד
עדכון חתימה של `on_embeddings` במעבדים FastEmbed ו-Ollama
עיבוד אצווה שלמה בפעילת מודל אחת

### שלב 3: עדכוני לקוח
עדכון `EmbeddingsClient.embed()` כדי לקבל `texts: list[str]`

### שלב 4: עדכוני משתמשים
עדכון graph_embeddings להטמעת הקשרים של ישויות באצווה
עדכון row_embeddings לעיבוד אצווה של טקסטים באינדקס
עדכון document_embeddings לשימוש בסכימה החדשה
עדכון כלי שורת הפקודה

### שלב 5: שער API
עדכון נקודת קצה של הטמעה עבור סכימה חדשה

### שלב 6: SDK של Python
עדכון חתימה של `FlowInstance.embeddings()`
עדכון חתימה של `SocketFlowInstance.embeddings()`

## שאלות פתוחות

**הטמעת אצוות גדולות**: האם עלינו לתמוך בהעברת תוצאות עבור אצוות גדולות מאוד (>100 טקסטים)?
**מגבלות ספציפיות לספק**: כיצד עלינו להתמודד עם ספקים עם גודל אצווה מקסימלי שונה?
**טיפול בכשלים חלקיים**: אם טקסט אחד באצווה נכשל, האם עלינו לגרום לכשל באצווה כולה או להחזיר תוצאות חלקיות?
**הטמעת מסמכים באצווה**: האם עלינו לבצע אצווה בין הודעות Chunk מרובות או לשמור על עיבוד פר-הודעה?

## הפניות

[תיעוד FastEmbed](https://github.com/qdrant/fastembed)
[ממשק API של הטמעות Ollama](https://github.com/ollama/ollama)
[יישום של EmbeddingsService](trustgraph-base/trustgraph/base/embeddings_service.py)
[אופטימיזציה של ביצועים של GraphRAG](graphrag-performance-optimization.md)
