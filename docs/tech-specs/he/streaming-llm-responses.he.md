---
layout: default
title: "מפרט טכני לתגובות LLM בסטרימינג"
parent: "Hebrew (Beta)"
---

# מפרט טכני לתגובות LLM בסטרימינג

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## סקירה כללית

מפרט זה מתאר את יישום התמיכה בסטרימינג עבור תגובות LLM
ב-TrustGraph. סטרימינג מאפשר העברה בזמן אמת של טוקנים שנוצרו
ככל שהם מיוצרים על ידי ה-LLM, במקום לחכות להשלמת יצירת
התגובה.

יישום זה תומך בתרחישי שימוש הבאים:

1. **ממשקי משתמש בזמן אמת**: העברת טוקנים לממשק המשתמש בזמן יצירתם,
   תוך מתן משוב ויזואלי מיידי.
2. **זמן עד לטוקן הראשון מופחת**: המשתמש רואה את הפלט מיד
   ולא מחכה ליצירה מלאה.
3. **טיפול בתגובות ארוכות**: טיפול בפלטים ארוכים מאוד שעלולים
   אחרת לגרום לחריגה מהזמן או לחרוג ממגבלות הזיכרון.
4. **יישומים אינטראקטיביים**: אפשור ממשקי צ'אט וסוכנים מגיבים.

## מטרות

**תאימות לאחור**: לקוחות קיימים שאינם משתמשים בסטרימינג ממשיכים
  לעבוד ללא שינוי.
**עיצוב API עקבי**: סטרימינג ולא סטרימינג משתמשים באותם דפוסי
  סכימה עם סטייה מינימלית.
**גמישות ספק**: תמיכה בסטרימינג כאשר הוא זמין, מעבר חלק
  כאשר הוא אינו זמין.
**פריסה מדורגת**: יישום הדרגתי להפחתת סיכונים.
**תמיכה מקצה לקצה**: סטרימינג מספק ה-LLM דרך ליישומי לקוח
  באמצעות Pulsar, Gateway API ו-Python API.

## רקע

### ארכיטקטורה נוכחית

זרימת השלמת הטקסט הנוכחית של ה-LLM פועלת באופן הבא:

1. לקוח שולח `TextCompletionRequest` עם שדות `system` ו-`prompt`.
2. שירות ה-LLM מעבד את הבקשה וממתין להשלמת היצירה.
3. `TextCompletionResponse` יחיד מוחזר עם מחרוזת `response` מלאה.

סכימה נוכחית (`trustgraph-base/trustgraph/schema/services/llm.py`):

```python
class TextCompletionRequest(Record):
    system = String()
    prompt = String()

class TextCompletionResponse(Record):
    error = Error()
    response = String()
    in_token = Integer()
    out_token = Integer()
    model = String()
```

### מגבלות נוכחיות

**השהייה (Latency)**: משתמשים חייבים לחכות לסיום יצירת התוכן לפני שהם רואים פלט כלשהו.
**סיכון לחריגת זמן (Timeout)**: יצירת תוכן ארוכה עלולה לחרוג מספי זמן המוגדר בלקוח.
**חוויית משתמש ירודה (Poor UX)**: היעדר משוב במהלך היצירה יוצר תחושה של איטיות.
**שימוש במשאבים**: תגובות מלאות חייבות להיות מאוחסנות בזיכרון.

מפרט זה מתייחס למגבלות אלה על ידי אפשור העברת תגובה הדרגתית תוך שמירה על תאימות מלאה לאחור.


## עיצוב טכני

### שלב 1: תשתית

שלב 1 מקיים את הבסיס להעברה באמצעות שינוי סכימות, ממשקי API וכלי שורת פקודה.


#### שינויים בסכימה

##### סכימת LLM (`trustgraph-base/trustgraph/schema/services/llm.py`)

**שינויים בבקשה:**

```python
class TextCompletionRequest(Record):
    system = String()
    prompt = String()
    streaming = Boolean()  # NEW: Default false for backward compatibility
```

`streaming`: כאשר `true`, מבקשים משלוח תגובה בסטרימינג.
ברירת מחדל: `false` (ההתנהגות הקיימת נשמרת).

**שינויים בתגובה:**

```python
class TextCompletionResponse(Record):
    error = Error()
    response = String()
    in_token = Integer()
    out_token = Integer()
    model = String()
    end_of_stream = Boolean()  # NEW: Indicates final message
```

`end_of_stream`: כאשר `true`, מציין שזו התגובה הסופית (או היחידה).
עבור בקשות שאינן סטרימינג: תגובה יחידה עם `end_of_stream=true`.
עבור בקשות סטרימינג: מספר תגובות, כולן עם `end_of_stream=false`.
  מלבד התגובה האחרונה.

##### סכימת הפרומפט (`trustgraph-base/trustgraph/schema/services/prompt.py`)

שירות הפרומפט עוטף השלמת טקסט, ולכן הוא משקף את אותו דפוס:

**שינויים בבקשה:**

```python
class PromptRequest(Record):
    id = String()
    terms = Map(String())
    streaming = Boolean()  # NEW: Default false
```

**שינויים בתגובה:**

```python
class PromptResponse(Record):
    error = Error()
    text = String()
    object = String()
    end_of_stream = Boolean()  # NEW: Indicates final message
```

#### שינויים בממשק ה-Gateway API

ממשק ה-Gateway API חייב לחשוף יכולות סטרימינג ללקוחות HTTP/WebSocket.

**עדכונים לממשק ה-REST API:**

`POST /api/v1/text-completion`: קבלת פרמטר `streaming` בגוף הבקשה
התנהגות התגובה תלויה בדגל הסטרימינג:
  `streaming=false`: תגובת JSON בודדת (ההתנהגות הנוכחית)
  `streaming=true`: זרם Server-Sent Events (SSE) או הודעות WebSocket

**פורמט תגובה (סטרימינג):**

כל חלק בזרם עוקב אחר מבנה הסכימה זהה:
```json
{
  "response": "partial text...",
  "end_of_stream": false,
  "model": "model-name"
}
```

חלק אחרון:
```json
{
  "response": "final text chunk",
  "end_of_stream": true,
  "in_token": 150,
  "out_token": 500,
  "model": "model-name"
}
```

#### שינויים בממשק ה-API של Python

ממשק ה-API של הלקוח ב-Python חייב לתמוך הן במצב סטרימינג והן במצב לא-סטרימינג
תוך שמירה על תאימות לאחור.

**עדכונים ל-LlmClient** (`trustgraph-base/trustgraph/clients/llm_client.py`):

```python
class LlmClient(BaseClient):
    def request(self, system, prompt, timeout=300, streaming=False):
        """
        Non-streaming request (backward compatible).
        Returns complete response string.
        """
        # Existing behavior when streaming=False

    async def request_stream(self, system, prompt, timeout=300):
        """
        Streaming request.
        Yields response chunks as they arrive.
        """
        # New async generator method
```

**עדכונים עבור PromptClient** (`trustgraph-base/trustgraph/base/prompt_client.py`):

דפוס דומה עם הפרמטר `streaming` וגרסה אסינכרונית של מחולל.

#### שינויים בכלי שורת הפקודה

**tg-invoke-llm** (`trustgraph-cli/trustgraph/cli/invoke_llm.py`):

```
tg-invoke-llm [system] [prompt] [--no-streaming] [-u URL] [-f flow-id]
```

הפעלת סטרימינג כברירת מחדל לשיפור חוויית משתמש אינטראקטיבית.
הדגל `--no-streaming` משבית את הסטרימינג.
כאשר הסטרימינג מופעל: פלט טוקנים לפלט סטנדרטי כשהם מגיעים.
כאשר הסטרימינג אינו מופעל: ממתינים לתגובה מלאה, ולאחר מכן מבצעים פלט.

**tg-invoke-prompt** (`trustgraph-cli/trustgraph/cli/invoke_prompt.py`):

```
tg-invoke-prompt [template-id] [var=value...] [--no-streaming] [-u URL] [-f flow-id]
```

אותו דפוס כמו `tg-invoke-llm`.

#### שינויים במחלקת הבסיס של שירות מודל שפה גדול (LLM).

**LlmService** (`trustgraph-base/trustgraph/base/llm_service.py`):

```python
class LlmService(FlowProcessor):
    async def on_request(self, msg, consumer, flow):
        request = msg.value()
        streaming = getattr(request, 'streaming', False)

        if streaming and self.supports_streaming():
            async for chunk in self.generate_content_stream(...):
                await self.send_response(chunk, end_of_stream=False)
            await self.send_response(final_chunk, end_of_stream=True)
        else:
            response = await self.generate_content(...)
            await self.send_response(response, end_of_stream=True)

    def supports_streaming(self):
        """Override in subclass to indicate streaming support."""
        return False

    async def generate_content_stream(self, system, prompt, model, temperature):
        """Override in subclass to implement streaming."""
        raise NotImplementedError()
```

--

### שלב 2: הוכחת היתכנות של VertexAI

שלב 2 מיישם סטרימינג בספק יחיד (VertexAI) כדי לאמת את
התשתית ולאפשר בדיקות מקצה לקצה.

#### יישום VertexAI

**מודול:** `trustgraph-vertexai/trustgraph/model/text_completion/vertexai/llm.py`

**שינויים:**

1. החלפה של `supports_streaming()` כדי להחזיר `True`
2. יישום מחולל אסינכרוני `generate_content_stream()`
3. טיפול גם במודלים של Gemini וגם של Claude (דרך ממשק ה-API של VertexAI Anthropic)

**סטרימינג של Gemini:**

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    model_instance = self.get_model(model, temperature)
    response = model_instance.generate_content(
        [system, prompt],
        stream=True  # Enable streaming
    )
    for chunk in response:
        yield LlmChunk(
            text=chunk.text,
            in_token=None,  # Available only in final chunk
            out_token=None,
        )
    # Final chunk includes token counts from response.usage_metadata
```

**קלוד (דרך VertexAI של חברת Anthropic) - סטרימינג:**

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    with self.anthropic_client.messages.stream(...) as stream:
        for text in stream.text_stream:
            yield LlmChunk(text=text)
    # Token counts from stream.get_final_message()
```

#### בדיקות

בדיקות יחידה עבור הרכבת תגובות סטרימינג
בדיקות אינטגרציה עם VertexAI (Gemini ו-Claude)
בדיקות מקצה לקצה: CLI -> Gateway -> Pulsar -> VertexAI -> חזרה
בדיקות תאימות לאחור: בקשות שאינן סטרימינג עדיין עובדות

--

### שלב 3: כל ספקי מודלי שפה גדולים (LLM)

שלב 3 מרחיב את תמיכת הסטרימינג לכל ספקי מודלי השפה הגדולים במערכת.

#### סטטוס יישום ספק

כל ספק חייב לבצע אחת מהפעולות הבאות:
1. **תמיכה מלאה בסטרימינג**: ליישם `generate_content_stream()`
2. **מצב תאימות**: לטפל בדגל `end_of_stream` בצורה נכונה
   (להחזיר תגובה בודדת עם `end_of_stream=true`)

| ספק | חבילה | תמיכה בסטרימינג |
|----------|---------|-------------------|
| OpenAI | trustgraph-flow | מלא (ממשק סטרימינג מקורי) |
| Claude/Anthropic | trustgraph-flow | מלא (ממשק סטרימינג מקורי) |
| Ollama | trustgraph-flow | מלא (ממשק סטרימינג מקורי) |
| Cohere | trustgraph-flow | מלא (ממשק סטרימינג מקורי) |
| Mistral | trustgraph-flow | מלא (ממשק סטרימינג מקורי) |
| Azure OpenAI | trustgraph-flow | מלא (ממשק סטרימינג מקורי) |
| Google AI Studio | trustgraph-flow | מלא (ממשק סטרימינג מקורי) |
| VertexAI | trustgraph-vertexai | מלא (שלב 2) |
| Bedrock | trustgraph-bedrock | מלא (ממשק סטרימינג מקורי) |
| LM Studio | trustgraph-flow | מלא (תואם ל-OpenAI) |
| LlamaFile | trustgraph-flow | מלא (תואם ל-OpenAI) |
| vLLM | trustgraph-flow | מלא (תואם ל-OpenAI) |
| TGI | trustgraph-flow | מצומצם |
| Azure | trustgraph-flow | מצומצם |

#### תבנית יישום

עבור ספקים התואמים ל-OpenAI (OpenAI, LM Studio, LlamaFile, vLLM):

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    response = await self.client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        stream=True
    )
    async for chunk in response:
        if chunk.choices[0].delta.content:
            yield LlmChunk(text=chunk.choices[0].delta.content)
```

--

### שלב 4: ממשק API של הסוכן

שלב 4 מרחיב את הסטרימינג לממשק ה-API של הסוכן. זה מורכב יותר מכיוון שה-
ממשק ה-API של הסוכן הוא כבר מטבעו רב-הודעות (מחשבה → פעולה → תצפית
→ חזור → תשובה סופית).

#### הסכימה הנוכחית של הסוכן

```python
class AgentStep(Record):
    thought = String()
    action = String()
    arguments = Map(String())
    observation = String()
    user = String()

class AgentRequest(Record):
    question = String()
    state = String()
    group = Array(String())
    history = Array(AgentStep())
    user = String()

class AgentResponse(Record):
    answer = String()
    error = Error()
    thought = String()
    observation = String()
```

#### שינויים מוצעים בסכימת הסוכן

**בקשות לשינויים:**

```python
class AgentRequest(Record):
    question = String()
    state = String()
    group = Array(String())
    history = Array(AgentStep())
    user = String()
    streaming = Boolean()  # NEW: Default false
```

**שינויים בתגובה:**

הסוכן מייצר סוגים שונים של פלט במהלך מחזור החשיבה שלו:
מחשבות (היגיון)
פעולות (קריאות לכלי)
תצפיות (תוצאות של כלי)
תשובה (תגובה סופית)
שגיאות

מכיוון ש-`chunk_type` מציין איזה סוג תוכן נשלח, השדות הנפרדים
`answer`, `error`, `thought` ו-`observation` יכולים להיות מקובצים לשדה
`content` יחיד:

```python
class AgentResponse(Record):
    chunk_type = String()       # "thought", "action", "observation", "answer", "error"
    content = String()          # The actual content (interpretation depends on chunk_type)
    end_of_message = Boolean()  # Current thought/action/observation/answer is complete
    end_of_dialog = Boolean()   # Entire agent dialog is complete
```

**סמנטיקה של שדות:**

`chunk_type`: מציין איזה סוג תוכן נמצא בשדה `content`
  `"thought"`: חשיבה/היגיון של הסוכן
  `"action"`: כלי/פעולה המופעלת
  `"observation"`: תוצאה מהפעלת הכלי
  `"answer"`: תשובה סופית לשאלה של המשתמש
  `"error"`: הודעת שגיאה

`content`: התוכן המועבר בפועל, המפורש בהתאם ל-`chunk_type`

`end_of_message`: כאשר `true`, סוג החלק הנוכחי הושלם
  דוגמה: כל הטוקנים עבור המחשבה הנוכחית נשלחו
  מאפשר ללקוחות לדעת מתי לעבור לשלב הבא

`end_of_dialog`: כאשר `true`, האינטראקציה כולה של הסוכן הושלמה
  זו ההודעה האחרונה בזרם

#### התנהגות סטרימינג של הסוכן

כאשר `streaming=true`:

1. **סטרימינג של מחשבות:**
   מספר חלקים עם `chunk_type="thought"`, `end_of_message=false`
   החלק האחרון של המחשבה מכיל `end_of_message=true`
2. **הודעת פעולה:**
   חלק יחיד עם `chunk_type="action"`, `end_of_message=true`
3. **תצפית:**
   חלק/ים עם `chunk_type="observation"`, האחרון מכיל `end_of_message=true`
4. **חזור** על שלבים 1-3 כאשר הסוכן מסיק מסקנות
5. **תשובה סופית:**
   `chunk_type="answer"` עם התגובה הסופית ב-`content`
   החלק האחרון מכיל `end_of_message=true`, `end_of_dialog=true`

**רצף סטרימינג לדוגמה:**

```
{chunk_type: "thought", content: "I need to", end_of_message: false, end_of_dialog: false}
{chunk_type: "thought", content: " search for...", end_of_message: true, end_of_dialog: false}
{chunk_type: "action", content: "search", end_of_message: true, end_of_dialog: false}
{chunk_type: "observation", content: "Found: ...", end_of_message: true, end_of_dialog: false}
{chunk_type: "thought", content: "Based on this", end_of_message: false, end_of_dialog: false}
{chunk_type: "thought", content: " I can answer...", end_of_message: true, end_of_dialog: false}
{chunk_type: "answer", content: "The answer is...", end_of_message: true, end_of_dialog: true}
```

כאשר `streaming=false`:
התנהגות נוכחית נשמרת
תגובה אחת עם תשובה מלאה
`end_of_message=true`, `end_of_dialog=true`

#### שער (Gateway) ו-API בפייתון

שער: נקודת קצה חדשה של SSE/WebSocket עבור סטרימינג של סוכן
API בפייתון: שיטת גנרטור אסינכרונית חדשה `agent_stream()`

--

## שיקולי אבטחה

**ללא נקודות תורפה חדשות**: סטרימינג משתמש באותה אימות/הרשאה
**הגבלת קצב**: יש להחיל מגבלות קצב פר-טוקן או פר-חלק במידת הצורך
**טיפול בחיבורים**: יש לסיים חיבורים בצורה תקינה בעת ניתוק הלקוח
**ניהול תזמון**: בקשות סטרימינג דורשות טיפול מתאים בתזמון

## שיקולי ביצועים

**זיכרון**: סטרימינג מפחית את השימוש בזיכרון המקסימלי (ללא אחסון מלא של התגובה)
**השהיה**: זמן עד לקבלת הטוקן הראשון קטן משמעותית
**תקורה של חיבורים**: לחיבורי SSE/WebSocket יש תקורה של שמירה על חיבור פעיל
**תפוקת Pulsar**: מספר הודעות קטנות לעומת הודעה גדולה אחת
  פשרה

## אסטרטגיית בדיקות

### בדיקות יחידה
סריאליזציה/דה-סריאליזציה של סכימה עם שדות חדשים
תאימות לאחור (שדות חסרים משתמשים בערכי ברירת מחדל)
לוגיקת הרכבת חלקים

### בדיקות אינטגרציה
יישום הסטרימינג של כל ספק מודלי שפה גדולים (LLM)
נקודות קצה של סטרימינג של API בשער
שיטות סטרימינג של לקוח בפייתון

### בדיקות מקצה לקצה
פלט סטרימינג של כלי שורת הפקודה (CLI)
זרימה מלאה: לקוח → שער → Pulsar → LLM → חזרה
עומסי עבודה מעורבים של סטרימינג/לא סטרימינג

### בדיקות תאימות לאחור
לקוחות קיימים עובדים ללא שינוי
בקשות לא סטרימינג מתנהגות באופן זהה

## תוכנית מעבר

### שלב 1: תשתית
פריסת שינויי סכימה (תואמת לאחור)
פריסת עדכוני API בשער
פריסת עדכוני API בפייתון
שחרור עדכוני כלי שורת הפקודה

### שלב 2: VertexAI
הטמעת יישום סטרימינג של VertexAI
אימות באמצעות עומסי עבודה לבדיקה

### שלב 3: כל הספקים
הטמעת עדכוני ספק באופן הדרגתי
ניטור לאיתור בעיות

### שלב 4: ממשק API של סוכן
הטמעת שינויים בסכימת הסוכן
הטמעת יישום סטרימינג של סוכן
עדכון התיעוד

## ציר זמן

| שלב | תיאור | תלויות |
|-------|-------------|--------------|
| שלב 1 | תשתית | אין |
| שלב 2 | הוכחת היתכנות של VertexAI | שלב 1 |
| שלב 3 | כל הספקים | שלב 2 |
| שלב 4 | ממשק API של סוכן | שלב 3 |

## החלטות עיצוב

השאלות הבאות נפתרו במהלך המפרט:

1. **ספירת טוקנים בסטרימינג**: ספירת הטוקנים היא הפרשים, ולא סכומים מצטברים.
   צרכנים יכולים לחבר אותם אם יש צורך. זה תואם לאופן שבו רוב הספקים מדווחים
   על שימוש ומפשט את היישום.

2. **טיפול בשגיאות בזרמים**: אם מתרחשת שגיאה, השדה `error` מאוכלס ושאר השדות אינם נחוצים. שגיאה היא תמיד ההודעה האחרונה - אסור לשלוח או לצפות להודעות נוספות לאחר מכן.
   
   
   שגיאה. עבור זרמי מודלים שפתיים (LLM) / הנחיות, `end_of_stream=true`. עבור זרמי סוכנים,
   `chunk_type="error"` עם `end_of_dialog=true`.

3. **התאוששות מתגובה חלקית**: פרוטוקול העברת ההודעות (Pulsar) עמיד,
   ולכן אין צורך בניסיונות חוזרים ברמת ההודעה. אם לקוח מאבד את המעקב אחר הזרם
   או מתנתק, עליו לנסות שוב את כל הבקשה מההתחלה.

4. **שירות מהיר עם סטרימינג**: סטרימינג נתמך רק עבור טקסט (`text`)
   תשובות, ולא עבור תשובות מובנות (`object`). שירות הפרומפט יודע מראש
   האם הפלט יהיה JSON או טקסט, בהתבסס על תבנית הפרומפט. אם מתבצעת
   בקשת סטרימינג עבור פרומפט שפלטו הוא JSON, אז...
   השירות צריך או:
   להחזיר את קובץ ה-JSON השלם בתגובה אחת עם `end_of_stream=true`, או
   לדחות את בקשת הסטרימינג עם שגיאה

## שאלות פתוחות

אין כרגע.

## הפניות

סכימת מודל שפה גדול (LLM) נוכחית: `trustgraph-base/trustgraph/schema/services/llm.py`
סכימת הנחיה נוכחית: `trustgraph-base/trustgraph/schema/services/prompt.py`
סכימת סוכן נוכחית: `trustgraph-base/trustgraph/schema/services/agent.py`
שירות LLM בסיסי: `trustgraph-base/trustgraph/base/llm_service.py`
ספק VertexAI: `trustgraph-vertexai/trustgraph/model/text_completion/vertexai/llm.py`
ממשק API של שער: `trustgraph-base/trustgraph/api/`
כלי שורת פקודה: `trustgraph-cli/trustgraph/cli/`
