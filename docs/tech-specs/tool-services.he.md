# שירותי כלים: כלים דינמיים הניתנים לחיבור

## סטטוס

מיושם

## סקירה כללית

מפרט זה מגדיר מנגנון לכלים דינמיים הניתנים לחיבור הנקראים "שירותי כלים". בניגוד לסוגי הכלים המובנים הקיימים (`KnowledgeQueryImpl`, `McpToolImpl`, וכו'), שירותי כלים מאפשרים להציג כלים חדשים על ידי:

1. פריסת שירות חדש המבוסס על Pulsar
2. הוספת תיאור תצורה המציין לסוכן כיצד להפעיל אותו

זה מאפשר הרחבה מבלי לשנות את מסגרת התגובה הבסיסית של הסוכן.

## מונחים

| מונח | הגדרה |
|------|------------|
| **כלי מובנה** | סוגי כלים קיימים עם יישומים מוגדרים מראש ב-`tools.py` |
| **שירות כלי** | שירות Pulsar שניתן להפעיל ככלי סוכן, המוגדר על ידי תיאור שירות |
| **כלי** | מופע מוגדר המתייחס לשירות כלי, החשוף לסוכן/LLM |

זהו מודל דו-שכבתי, אנלוגי לכלי MCP:
MCP: שרת MCP מגדיר את ממשק הכלי → תצורת הכלי מתייחסת אליו
שירותי כלים: שירות הכלי מגדיר את ממשק Pulsar → תצורת הכלי מתייחסת אליו

## רקע: כלים קיימים

### יישום כלי מובנה

כלי מוגדרים כיום ב-`trustgraph-flow/trustgraph/agent/react/tools.py` עם יישומים מטיפוסים:

```python
class KnowledgeQueryImpl:
    async def invoke(self, question):
        client = self.context("graph-rag-request")
        return await client.rag(question, self.collection)
```

כל סוג כלי:
כולל שירות Pulsar מובנה שהוא קורא אליו (לדוגמה: `graph-rag-request`)
יודע בדיוק את השיטה לקריאה בלקוח (לדוגמה: `client.rag()`)
מכיל ארגומנטים מוגדרים בסביבת היישום

### רישום כלים (service.py:105-214)

כלים נטענים מקובץ תצורה עם שדה `type` שממפה ליישום:

```python
if impl_id == "knowledge-query":
    impl = functools.partial(KnowledgeQueryImpl, collection=data.get("collection"))
elif impl_id == "text-completion":
    impl = TextCompletionImpl
# ... etc
```

## ארכיטקטורה

### מודל דו-שכבתי

#### שכבה 1: תיאור שירות כלי

שירות כלי מגדיר ממשק שירות של פולסר. הוא מכריז על:
תורי הפולסר עבור בקשות/תגובות
פרמטרי תצורה שהוא דורש מכלי המשתמשים בו

```json
{
  "id": "custom-rag",
  "request-queue": "non-persistent://tg/request/custom-rag",
  "response-queue": "non-persistent://tg/response/custom-rag",
  "config-params": [
    {"name": "collection", "required": true}
  ]
}
```

שירות כלי שאינו דורש פרמטרים של תצורה:

```json
{
  "id": "calculator",
  "request-queue": "non-persistent://tg/request/calc",
  "response-queue": "non-persistent://tg/response/calc",
  "config-params": []
}
```

#### שכבה 2: תיאור כלי

כלי מפנה לשירות כלי ומספק:
ערכי פרמטרים של תצורה (העונים על דרישות השירות)
מטא-נתונים של הכלי עבור הסוכן (שם, תיאור)
הגדרות ארגומנטים עבור מודל השפה הגדול (LLM)

```json
{
  "type": "tool-service",
  "name": "query-customers",
  "description": "Query the customer knowledge base",
  "service": "custom-rag",
  "collection": "customers",
  "arguments": [
    {
      "name": "question",
      "type": "string",
      "description": "The question to ask about customers"
    }
  ]
}
```

מספר כלים יכולים להתייחס לאותה שירות עם תצורות שונות:

```json
{
  "type": "tool-service",
  "name": "query-products",
  "description": "Query the product knowledge base",
  "service": "custom-rag",
  "collection": "products",
  "arguments": [
    {
      "name": "question",
      "type": "string",
      "description": "The question to ask about products"
    }
  ]
}
```

### פורמט בקשה

כאשר כלי מופעל, הבקשה לשירות הכלי כוללת:
`user`: מהבקשה של הסוכן (ריבוי דיירים)
`config`: ערכי תצורה מקודדים ב-JSON מהתיאור של הכלי
`arguments`: ארגומנטים מקודדים ב-JSON מהמודל הלשוני הגדול (LLM)

```json
{
  "user": "alice",
  "config": "{\"collection\": \"customers\"}",
  "arguments": "{\"question\": \"What are the top customer complaints?\"}"
}
```

השירות של הכלי מקבל זאת כ-dicts שעברו ניתוח בשיטה `invoke`.

### יישום כללי של שירות הכלי

מחלקה `ToolServiceImpl` מפעילה שירותי כלי בהתבסס על תצורה:

```python
class ToolServiceImpl:
    def __init__(self, context, request_queue, response_queue, config_values, arguments, processor):
        self.request_queue = request_queue
        self.response_queue = response_queue
        self.config_values = config_values  # e.g., {"collection": "customers"}
        # ...

    async def invoke(self, **arguments):
        client = await self._get_or_create_client()
        response = await client.call(user, self.config_values, arguments)
        if isinstance(response, str):
            return response
        else:
            return json.dumps(response)
```

## החלטות עיצוב

### מודל תצורה דו-שכבתי

שירותי כלים פועלים לפי מודל דו-שכבתי הדומה לכלי MCP:

1. **שירות כלי**: מגדיר את ממשק השירות של Pulsar (נושא, פרמטרי תצורה נדרשים)
2. **כלי**: מפנה לשירות כלי, מספק ערכי תצורה, מגדיר ארגומנטים של LLM

הפרדה זו מאפשרת:
שירות כלי אחד יכול לשמש מספר כלים עם תצורות שונות
הבחנה ברורה בין ממשק השירות לתצורת הכלי
שימוש חוזר בהגדרות שירות

### מיפוי בקשות: העברה עם מעטפה

הבקשה לשירות כלי היא מעטפה מובנית המכילה:
`user`: מועבר מבקשת הסוכן עבור ריבוי דיירים
ערכי תצורה: מתיאור הכלי (לדוגמה, `collection`)
`arguments`: ארגומנטים המסופקים על ידי LLM, מועברים כמילון

מנהל הסוכן מנתח את התגובה של ה-LLM ל-`act.arguments` כמילון (`agent_manager.py:117-154`). מילון זה כלול במעטפת הבקשה.

### טיפול בסכימה: לא מסווג

בקשות ותגובות משתמשות במילונים לא מסווגים. אין אימות סכימה ברמת הסוכן - שירות הכלי אחראי לאימות הקלט שלו. זה מספק גמישות מרבית בהגדרת שירותים חדשים.

### ממשק לקוח: נושאים ישירים של Pulsar

שירותי כלים משתמשים בנושאים ישירים של Pulsar מבלי לדרוש תצורת זרימה. תיאור שירות הכלי מציין את שמות התורים המלאים:

```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [...]
}
```

זה מאפשר לארח שירותים בכל מרחב שם.

### טיפול בשגיאות: מוסכמות שגיאות סטנדרטיות

תגובות של שירותי כלים עוקבות אחר מוסכמות הסכימה הקיימות עם שדה `error`:

```python
@dataclass
class Error:
    type: str = ""
    message: str = ""
```

מבנה תגובה:
הצלחה: `error` הוא `None`, התגובה מכילה תוצאה
שגיאה: `error` מאוכלס עם `type` ו- `message`

זה תואם לדפוס המשמש בכל סכימות השירות הקיימות (לדוגמה, `PromptResponse`, `QueryResponse`, `AgentResponse`).

### התאמה בין בקשה לתגובה

בקשות ותגובות משויכות באמצעות `id` במאפייני הודעות Pulsar:

בקשה כוללת `id` במאפיינים: `properties={"id": id}`
התגובות כוללות את אותו `id`: `properties={"id": id}`

זה עוקב אחר הדפוס הקיים המשמש בכל בסיס הקוד (לדוגמה, `agent_service.py`, `llm_service.py`).

### תמיכה בסטרימינג

שירותי כלים יכולים להחזיר תגובות בסטרימינג:

הודעות תגובה מרובות עם אותו `id` במאפיינים
כל תגובה כוללת את השדה `end_of_stream: bool`
התגובה הסופית כוללת את `end_of_stream: True`

זה תואם לדפוס המשמש ב- `AgentResponse` ובשירותי סטרימינג אחרים.

### טיפול בתגובה: החזרת מחרוזת

כל הכלים הקיימים עוקבים אחר אותו דפוס: **קבלת ארגומנטים כמילון, החזרת התצפית כמחרוזת**.

| כלי | טיפול בתגובה |
|------|------------------|
| `KnowledgeQueryImpl` | מחזיר את `client.rag()` ישירות (מחרוזת) |
| `TextCompletionImpl` | מחזיר את `client.question()` ישירות (מחרוזת) |
| `McpToolImpl` | מחזיר מחרוזת, או `json.dumps(output)` אם אינה מחרוזת |
| `StructuredQueryImpl` | מעצב את התוצאה למחרוזת |
| `PromptImpl` | מחזיר את `client.prompt()` ישירות (מחרוזת) |

שירותי כלים עוקבים אחר אותו חוזה:
השירות מחזיר תגובת מחרוזת (התצפית)
אם התגובה אינה מחרוזת, היא מומרת באמצעות `json.dumps()`
אין צורך בתצורת חילוץ במגדיר

זה שומר על המגדיר פשוט ומעביר את האחריות לשירות להחזיר תגובת טקסט מתאימה עבור הסוכן.

## מדריך תצורה

כדי להוסיף שירות כלי חדש, נדרשים שני פריטי תצורה:

### 1. תצורת שירות כלי

מאוחסן תחת מפתח התצורה `tool-service`. מגדיר את תורי Pulsar ואת פרמטרי התצורה הזמינים.

| שדה | נדרש | תיאור |
|-------|----------|-------------|
| `id` | כן | מזהה ייחודי עבור שירות הכלי |
| `request-queue` | כן | נושא Pulsar מלא עבור בקשות (לדוגמה, `non-persistent://tg/request/joke`) |
| `response-queue` | כן | נושא Pulsar מלא עבור תגובות (לדוגמה, `non-persistent://tg/response/joke`) |
| `config-params` | לא | מערך של פרמטרי תצורה שהשירות מקבל |

ניתן לציין כל פרמטר תצורה:
`name`: שם הפרמטר (נדרש)
`required`: האם הפרמטר חייב להיות מסופק על ידי כלים (ברירת מחדל: false)

דוגמה:
```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [
    {"name": "style", "required": false}
  ]
}
```

### 2. תצורת כלי

שמור תחת מפתח התצורה `tool`. מגדיר כלי שהסוכן יכול להשתמש בו.

| שדה | נדרש | תיאור |
|-------|----------|-------------|
| `type` | כן | חייב להיות `"tool-service"` |
| `name` | כן | שם הכלי החשוף ל-LLM |
| `description` | כן | תיאור של מה הכלי עושה (מוצג ל-LLM) |
| `service` | כן | מזהה של שירות הכלי לביצוע |
| `arguments` | לא | מערך של הגדרות ארגומנטים עבור ה-LLM |
| *(פרמטרי תצורה)* | משתנה | כל פרמטרי תצורה המוגדרים על ידי השירות |

כל ארגומנט יכול לציין:
`name`: שם הארגומנט (נדרש)
`type`: סוג נתונים, לדוגמה, `"string"` (נדרש)
`description`: תיאור המוצג ל-LLM (נדרש)

דוגמה:
```json
{
  "type": "tool-service",
  "name": "tell-joke",
  "description": "Tell a joke on a given topic",
  "service": "joke-service",
  "style": "pun",
  "arguments": [
    {
      "name": "topic",
      "type": "string",
      "description": "The topic for the joke (e.g., programming, animals, food)"
    }
  ]
}
```

### טעינת הגדרות

השתמשו ב-`tg-put-config-item` כדי לטעון הגדרות:

```bash
# Load tool-service config
tg-put-config-item tool-service/joke-service < joke-service.json

# Load tool config
tg-put-config-item tool/tell-joke < tell-joke.json
```

יש להפעיל מחדש את מנהל הסוכן כדי לקלוט הגדרות חדשות.

## פרטי יישום

### סכימה

סוגי בקשות ותגובות ב-`trustgraph-base/trustgraph/schema/services/tool_service.py`:

```python
@dataclass
class ToolServiceRequest:
    user: str = ""           # User context for multi-tenancy
    config: str = ""         # JSON-encoded config values from tool descriptor
    arguments: str = ""      # JSON-encoded arguments from LLM

@dataclass
class ToolServiceResponse:
    error: Error | None = None
    response: str = ""       # String response (the observation)
    end_of_stream: bool = False
```

### צד שרת: DynamicToolService

מחלקה בסיסית ב-`trustgraph-base/trustgraph/base/dynamic_tool_service.py`:

```python
class DynamicToolService(AsyncProcessor):
    """Base class for implementing tool services."""

    def __init__(self, **params):
        topic = params.get("topic", default_topic)
        # Constructs topics: non-persistent://tg/request/{topic}, non-persistent://tg/response/{topic}
        # Sets up Consumer and Producer

    async def invoke(self, user, config, arguments):
        """Override this method to implement the tool's logic."""
        raise NotImplementedError()
```

### צד לקוח: ToolServiceImpl

יישום ב-`trustgraph-flow/trustgraph/agent/react/tools.py`:

```python
class ToolServiceImpl:
    def __init__(self, context, request_queue, response_queue, config_values, arguments, processor):
        # Uses the provided queue paths directly
        # Creates ToolServiceClient on first use

    async def invoke(self, **arguments):
        client = await self._get_or_create_client()
        response = await client.call(user, config_values, arguments)
        return response if isinstance(response, str) else json.dumps(response)
```

### קבצים

| קובץ | מטרה |
|------|---------|
| `trustgraph-base/trustgraph/schema/services/tool_service.py` | סכימות בקשה/תגובה |
| `trustgraph-base/trustgraph/base/tool_service_client.py` | לקוח להפעלת שירותים |
| `trustgraph-base/trustgraph/base/dynamic_tool_service.py` | מחלקה בסיסית ליישום שירות |
| `trustgraph-flow/trustgraph/agent/react/tools.py` | מחלקה `ToolServiceImpl` |
| `trustgraph-flow/trustgraph/agent/react/service.py` | טעינת תצורה |

### דוגמה: שירות בדיחות

דוגמה לשירות ב-`trustgraph-flow/trustgraph/tool_service/joke/`:

```python
class Processor(DynamicToolService):
    async def invoke(self, user, config, arguments):
        style = config.get("style", "pun")
        topic = arguments.get("topic", "")
        joke = pick_joke(topic, style)
        return f"Hey {user}! Here's a {style} for you:\n\n{joke}"
```

תצורת שירות הכלי:
```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [{"name": "style", "required": false}]
}
```

הגדרות כלי:
```json
{
  "type": "tool-service",
  "name": "tell-joke",
  "description": "Tell a joke on a given topic",
  "service": "joke-service",
  "style": "pun",
  "arguments": [
    {"name": "topic", "type": "string", "description": "The topic for the joke"}
  ]
}
```

### תאימות לאחור

סוגי כלים מובנים קיימים ממשיכים לעבוד ללא שינוי.
`tool-service` הוא סוג כלי חדש לצד סוגים קיימים (`knowledge-query`, `mcp-tool`, וכו').

## שיקולים עתידיים

### שירותים המצהירים על עצמם

שיפור עתידי יכול לאפשר לשירותים לפרסם את התיאורים שלהם:

שירותים מפרסמים לנושא `tool-descriptors` ידוע בעת ההפעלה.
הסוכן נרשם ורושם כלים באופן דינמי.
מאפשר חיבור והפעלה אמיתיים ללא שינויי תצורה.

זה מחוץ לתחום של המימוש הראשוני.

## הפניות

יישום כלי נוכחי: `trustgraph-flow/trustgraph/agent/react/tools.py`
רישום כלים: `trustgraph-flow/trustgraph/agent/react/service.py:105-214`
סכימות סוכן: `trustgraph-base/trustgraph/schema/services/agent.py`
