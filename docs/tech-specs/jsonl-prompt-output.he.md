# מפרט טכני של פלט JSONL

## סקירה כללית

מפרט זה מתאר את יישום פורמט הפלט JSONL (JSON Lines)
עבור תשובות לשאילתות ב-TrustGraph. JSONL מאפשר חילוץ עמיד לקיטוע
של נתונים מובנים מתשובות של מודלי שפה גדולים (LLM), תוך התמודדות עם בעיות
<<<<<<< HEAD
קריטיות שבהן פלט מערך JSON נפגע כאשר תשובות ה-LLM מגיעות למגבלות
של מספר הטוקנים.
=======
קריטיות שבהן מערכי JSON יוצאים מכלל שימוש כאשר תשובות ה-LLM מגיעות
למגבלות מספר הטוקנים.
>>>>>>> 82edf2d (New md files from RunPod)

יישום זה תומך בתרחישי שימוש הבאים:

1. **חילוץ עמיד לקיטוע**: חילוץ תוצאות חלקיות ותקינות גם כאשר
   פלט ה-LLM מקוטע באמצע התגובה.
2. **חילוץ בקנה מידה גדול**: טיפול בחילוץ של פריטים רבים מבלי
<<<<<<< HEAD
   להסתכן בכשל מוחלט עקב מגבלות טוקנים.
=======
   להסתכן בכשל מוחלט עקב מגבלות מספר הטוקנים.
>>>>>>> 82edf2d (New md files from RunPod)
3. **חילוץ מסוגים מעורבים**: תמיכה בחילוץ של סוגי ישויות מרובים
   (הגדרות, קשרים, ישויות, תכונות) בשאילתה אחת.
4. **פלט תואם לסטרימינג**: אפשור עיבוד עתידי של תוצאות החילוץ
   בצורה של סטרימינג/הדרגתית.

## מטרות

**תאימות לאחור**: שאילתות קיימות המשתמשות ב-`response-type: "text"` ו-
  `response-type: "json"` ממשיכות לעבוד ללא שינוי.
**עמידות לקיטוע**: פלטים חלקיים של LLM מניבים תוצאות חלקיות ותקינות
  במקום כשל מוחלט.
**אימות סכימה**: תמיכה באימות סכימה של JSON עבור אובייקטים בודדים.
**איחודים מובחנים**: תמיכה בפלטים מסוגים מעורבים באמצעות שדה `type`
  מפריד.
**שינויים מינימליים ב-API**: הרחבת תצורת השאילתה הקיימת עם סוג
  תגובה חדש ומפתח סכימה.

## רקע

### ארכיטקטורה נוכחית

<<<<<<< HEAD
שירות השאילתות תומך בשני סוגי תגובה:

1. `response-type: "text"` - תגובה טקסטואלית גולמית המוחזרת כפי שהיא.
2. `response-type: "json"` - JSON המנותח מהתגובה, ומאומת כנגד
=======
שירות השאילתות תומך בשני סוגי תגובות:

1. `response-type: "text"` - תגובה טקסטואלית גולמית המוחזרת כפי שהיא.
2. `response-type: "json"` - JSON המנותח מהתגובה, ומאומת מול
>>>>>>> 82edf2d (New md files from RunPod)
   `schema` אופציונלי.

יישום נוכחי ב-`trustgraph-flow/trustgraph/template/prompt_manager.py`:

```python
class Prompt:
    def __init__(self, template, response_type = "text", terms=None, schema=None):
        self.template = template
        self.response_type = response_type
        self.terms = terms
        self.schema = schema
```

### מגבלות נוכחיות

כאשר הנחיות החילוץ מבקשות פלט כמערכים מסוג JSON (`[{...}, {...}, ...]`):

<<<<<<< HEAD
**שחיתות עקב קיטום**: אם מודל השפה (LLM) מגיע למגבלת מספר הטוקנים במהלך יצירת המערך,
=======
**שחיתות עקב קיטוע:** אם מודל השפה (LLM) מגיע למגבלת מספר הטוקנים במהלך יצירת המערך,
>>>>>>> 82edf2d (New md files from RunPod)
  התגובה כולה הופכת ל-JSON לא חוקי ואי אפשר לנתח אותה.
**ניתוח "הכל או כלום":** יש לקבל את הפלט השלם לפני הניתוח.
**אין תוצאות חלקיות:** תגובה מקוטעת מניבה אפס נתונים שניתן להשתמש בהם.
**לא אמין עבור חילוצים גדולים:** ככל שיותר פריטים מחולצים, כך גדל הסיכון לכישלון.

מפרט זה מתייחס למגבלות אלה על ידי הצגת פורמט JSONL עבור
הנחיות חילוץ, כאשר כל פריט מחולץ הוא אובייקט JSON שלם בשורה
משלו.

## עיצוב טכני

### הרחבת סוג התגובה

הוסף סוג תגובה חדש `"jsonl"` לצד סוגי `"text"` ו-`"json"` הקיימים.

#### שינויי תצורה

<<<<<<< HEAD
**ערך חדש עבור סוג התגובה:**
=======
**ערך סוג תגובה חדש:**
>>>>>>> 82edf2d (New md files from RunPod)

```
"response-type": "jsonl"
```

**פרשנות של הסכימה:**

המפתח הקיים `"schema"` משמש הן עבור סוג התגובה `"json"` והן עבור סוג התגובה `"jsonl"`.
הפרשנות תלויה בסוג התגובה:

`"json"`: הסכימה מתארת את כל התגובה (בדרך כלל מערך או אובייקט).
`"jsonl"`: הסכימה מתארת כל שורה/אובייקט בנפרד.

```json
{
  "response-type": "jsonl",
  "schema": {
    "type": "object",
    "properties": {
      "entity": { "type": "string" },
      "definition": { "type": "string" }
    },
    "required": ["entity", "definition"]
  }
}
```

זה מונע שינויים בכלי התצורה ובתוכנות העריכה.

### מפרט פורמט JSONL

#### חילוץ פשוט

עבור שאילתות המפיקות סוג אחד של אובייקט (הגדרות, קשרים,
נושאים, שורות), הפלט הוא אובייקט JSON אחד בכל שורה, ללא עטיפה:

**פורמט פלט של השאילתה:**
```
{"entity": "photosynthesis", "definition": "Process by which plants convert sunlight"}
{"entity": "chlorophyll", "definition": "Green pigment in plants"}
{"entity": "mitochondria", "definition": "Powerhouse of the cell"}
```

<<<<<<< HEAD
**ניגוד לפורמט מערך JSON הקודם:**
=======
**השוואה לפורמט מערך JSON הקודם:**
>>>>>>> 82edf2d (New md files from RunPod)
```json
[
  {"entity": "photosynthesis", "definition": "Process by which plants convert sunlight"},
  {"entity": "chlorophyll", "definition": "Green pigment in plants"},
  {"entity": "mitochondria", "definition": "Powerhouse of the cell"}
]
```

אם מודל השפה הגדול (LLM) מקצר אחרי השורה 2, פורמט מערך ה-JSON ייתן JSON לא תקין,
בעוד ש-JSONL ייתן שני אובייקטים תקינים.

<<<<<<< HEAD
#### חילוץ של טיפוסים מעורבים (איחודים מובחנים)

עבור הנחיות המפיקות מספר סוגים של אובייקטים (לדוגמה, גם הגדרות וגם
קשרים, או ישויות, קשרים ומאפיינים), השתמש בשדה `"type"`
=======
#### חילוץ מסוגים מעורבים (איחודים מובחנים)

עבור הנחיות המפיקות סוגים מרובים של אובייקטים (לדוגמה, גם הגדרות וגם
קשרים, או ישויות, קשרים ומאפיינים), השתמשו בשדה `"type"`
>>>>>>> 82edf2d (New md files from RunPod)
כמבחין:

**פורמט פלט של ההנחיה:**
```
{"type": "definition", "entity": "DNA", "definition": "Molecule carrying genetic instructions"}
{"type": "relationship", "subject": "DNA", "predicate": "located_in", "object": "cell nucleus", "object-entity": true}
{"type": "definition", "entity": "RNA", "definition": "Molecule that carries genetic information"}
{"type": "relationship", "subject": "RNA", "predicate": "transcribed_from", "object": "DNA", "object-entity": true}
```

**הסכימה עבור איחודים מובחנים משתמשת ב-`oneOf`:**
```json
{
  "response-type": "jsonl",
  "schema": {
    "oneOf": [
      {
        "type": "object",
        "properties": {
          "type": { "const": "definition" },
          "entity": { "type": "string" },
          "definition": { "type": "string" }
        },
        "required": ["type", "entity", "definition"]
      },
      {
        "type": "object",
        "properties": {
          "type": { "const": "relationship" },
          "subject": { "type": "string" },
          "predicate": { "type": "string" },
          "object": { "type": "string" },
          "object-entity": { "type": "boolean" }
        },
        "required": ["type", "subject", "predicate", "object", "object-entity"]
      }
    ]
  }
}
```

#### חילוץ אונטולוגיה

עבור חילוץ המבוסס על אונטולוגיה, הכולל ישויות, קשרים ומאפיינים:

**פורמט פלט של ההנחיה:**
```
{"type": "entity", "entity": "Cornish pasty", "entity_type": "fo/Recipe"}
{"type": "entity", "entity": "beef", "entity_type": "fo/Food"}
{"type": "relationship", "subject": "Cornish pasty", "subject_type": "fo/Recipe", "relation": "fo/has_ingredient", "object": "beef", "object_type": "fo/Food"}
{"type": "attribute", "entity": "Cornish pasty", "entity_type": "fo/Recipe", "attribute": "fo/serves", "value": "4 people"}
```

### פרטי יישום

#### מחלקת Prompt

המחלקה הקיימת `Prompt` אינה דורשת שינויים. השדה `schema` משמש מחדש
עבור JSONL, והפרשנות שלו נקבעת על ידי `response_type`:

```python
class Prompt:
    def __init__(self, template, response_type="text", terms=None, schema=None):
        self.template = template
        self.response_type = response_type
        self.terms = terms
        self.schema = schema  # Interpretation depends on response_type
```

#### PromptManager.load_config

אין צורך בשינויים - הטעינה הקיימת של התצורה כבר מטפלת במפתח
`schema`.

#### ניתוח JSONL

הוסף שיטת ניתוח חדשה לתגובות JSONL:

```python
def parse_jsonl(self, text):
    """
    Parse JSONL response, returning list of valid objects.

    Invalid lines (malformed JSON, empty lines) are skipped with warnings.
    This provides truncation resilience - partial output yields partial results.
    """
    results = []

    for line_num, line in enumerate(text.strip().split('\n'), 1):
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip markdown code fence markers if present
        if line.startswith('```'):
            continue

        try:
            obj = json.loads(line)
            results.append(obj)
        except json.JSONDecodeError as e:
            # Log warning but continue - this provides truncation resilience
            logger.warning(f"JSONL parse error on line {line_num}: {e}")

    return results
```

#### שינויים ב-PromptManager.invoke

<<<<<<< HEAD
הרחב את השיטה invoke כדי לטפל בסוג התגובה החדש:
=======
הרחב את המיפעל invoke כדי לטפל בסוג התגובה החדש:
>>>>>>> 82edf2d (New md files from RunPod)

```python
async def invoke(self, id, input, llm):
    logger.debug("Invoking prompt template...")

    terms = self.terms | self.prompts[id].terms | input
    resp_type = self.prompts[id].response_type

    prompt = {
        "system": self.system_template.render(terms),
        "prompt": self.render(id, input)
    }

    resp = await llm(**prompt)

    if resp_type == "text":
        return resp

    if resp_type == "json":
        try:
            obj = self.parse_json(resp)
        except:
            logger.error(f"JSON parse failed: {resp}")
            raise RuntimeError("JSON parse fail")

        if self.prompts[id].schema:
            try:
                validate(instance=obj, schema=self.prompts[id].schema)
                logger.debug("Schema validation successful")
            except Exception as e:
                raise RuntimeError(f"Schema validation fail: {e}")

        return obj

    if resp_type == "jsonl":
        objects = self.parse_jsonl(resp)

        if not objects:
            logger.warning("JSONL parse returned no valid objects")
            return []

        # Validate each object against schema if provided
        if self.prompts[id].schema:
            validated = []
            for i, obj in enumerate(objects):
                try:
                    validate(instance=obj, schema=self.prompts[id].schema)
                    validated.append(obj)
                except Exception as e:
                    logger.warning(f"Object {i} failed schema validation: {e}")
            return validated

        return objects

    raise RuntimeError(f"Response type {resp_type} not known")
```

### הנחיות מושפעות

ההנחיות הבאות צריכות להיות מועברות לפורמט JSONL:

| מזהה הנחיה | תיאור | שדה סוג |
|-----------|-------------|------------|
| `extract-definitions` | חילוץ ישויות/הגדרות | לא (סוג בודד) |
| `extract-relationships` | חילוץ קשרים | לא (סוג בודד) |
| `extract-topics` | חילוץ נושא/הגדרה | לא (סוג בודד) |
| `extract-rows` | חילוץ שורה מובנית | לא (סוג בודד) |
| `agent-kg-extract` | חילוץ משולב של הגדרה + קשר | כן: `"definition"`, `"relationship"` |
| `extract-with-ontologies` / `ontology-extract` | חילוץ מבוסס אונטולוגיה | כן: `"entity"`, `"relationship"`, `"attribute"` |

### שינויים ב-API

#### נקודת מבט של הלקוח

ניתוח JSONL שקוף למשתמשי ה-API של שירות ההנחיות. הניתוח מתבצע
<<<<<<< HEAD
בצד השרת בשירות ההנחיות, והתגובה מוחזרת באמצעות השדה הסטנדרטי
=======
בצד השרת בשירות ההנחיות, והתגובה מוחזרת דרך השדה הסטנדרטי
>>>>>>> 82edf2d (New md files from RunPod)
`PromptResponse.object` כמערך JSON מוסרי.

כאשר לקוחות קוראים לשירות ההנחיות (דרך `PromptClient.prompt()` או דומה):

**`response-type: "json"`** עם סכימת מערך → הלקוח מקבל `list` בפייתון
**`response-type: "jsonl"`** → הלקוח מקבל `list` בפייתון

מנקודת מבטו של הלקוח, שתי השיטות מחזירות מבני נתונים זהים. ההבדל
<<<<<<< HEAD
הוא אך ורק באופן שבו פלט ה-LLM מנותח בצד השרת:

פורמט מערך JSON: קריאה אחת ל-`json.loads()`; נכשל לחלוטין אם הוא חתוך
פורמט JSONL: ניתוח שורה אחר שורה; מייצר תוצאות חלקיות אם הוא חתוך
=======
הוא אך ורק באופן שבו הפלט של מודל השפה הגדול (LLM) מנותח בצד השרת:

פורמט מערך JSON: קריאה אחת ל-`json.loads()`; נכשל לחלוטין אם הוא חתוך.
פורמט JSONL: ניתוח שורה אחר שורה; מייצר תוצאות חלקיות אם הוא חתוך.
>>>>>>> 82edf2d (New md files from RunPod)

המשמעות היא שקוד לקוח קיים שמצפה לרשימה מהנחיות חילוץ
אינו דורש שינויים בעת העברת הנחיות מפורמט JSON לפורמט JSONL.

#### ערך החזרה של השרת

עבור `response-type: "jsonl"`, השיטה `PromptManager.invoke()` מחזירה
`list[dict]` המכיל את כל האובייקטים שנותחו ואומתו בהצלחה.
רשימה זו מוסרת אז ל-JSON עבור השדה `PromptResponse.object`.

#### טיפול בשגיאות

<<<<<<< HEAD
תוצאות ריקות: מחזיר רשימה ריקה `[]` עם רישום אזהרה
כשל חלקי בניתוח: מחזיר רשימה של אובייקטים שנותחו בהצלחה עם
  רישומי אזהרה עבור כשלים
כשל מוחלט בניתוח: מחזיר רשימה ריקה `[]` עם רישומי אזהרה
=======
תוצאות ריקות: מחזיר רשימה ריקה `[]` עם רישום אזהרה.
כשל חלקי בניתוח: מחזיר רשימה של אובייקטים שנותחו בהצלחה עם
  רישומי אזהרה עבור כשלים.
כשל מוחלט בניתוח: מחזיר רשימה ריקה `[]` עם רישומי אזהרה.
>>>>>>> 82edf2d (New md files from RunPod)

זה שונה מ-`response-type: "json"` שמגביר `RuntimeError`
בעת כשל בניתוח. ההתנהגות הסלחנית עבור JSONL היא מכוונת כדי לספק
עמידות לחיתוך.

### דוגמה לתצורה

דוגמה מלאה לתצורה של הנחיה:

```json
{
  "prompt": "Extract all entities and their definitions from the following text. Output one JSON object per line.\n\nText:\n{{text}}\n\nOutput format per line:\n{\"entity\": \"<name>\", \"definition\": \"<definition>\"}",
  "response-type": "jsonl",
  "schema": {
    "type": "object",
    "properties": {
      "entity": {
        "type": "string",
        "description": "The entity name"
      },
      "definition": {
        "type": "string",
        "description": "A clear definition of the entity"
      }
    },
    "required": ["entity", "definition"]
  }
}
```

## שיקולי אבטחה

<<<<<<< HEAD
**בדיקת תקינות קלט**: ניתוח JSON משתמש ב-`json.loads()` הסטנדרטי, שהוא בטוח
  מפני התקפות הזרקה.
**בדיקת תאימות סכימה**: משתמש ב-`jsonschema.validate()` לאכיפת סכימה.
**ללא משטח תקיפה חדש**: ניתוח JSONL בטוח יותר מניתוח מערך JSON
=======
**בדיקת קלט**: ניתוח JSON משתמש ב-`json.loads()` הסטנדרטי, שהוא בטוח
  מפני התקפות הזרקה.
**בדיקת סכימה**: משתמש ב-`jsonschema.validate()` לאכיפת סכימה.
**ללא נקודות תורפה חדשות**: ניתוח JSONL בטוח יותר מניתוח מערך JSON
>>>>>>> 82edf2d (New md files from RunPod)
  בשל עיבוד שורה אחר שורה.

## שיקולי ביצועים

<<<<<<< HEAD
**זיכרון**: ניתוח שורה אחר שורה משתמש בפחות זיכרון שיא בהשוואה לטעינת מערכי JSON שלמים.
  
**השהיה**: ביצועי הניתוח דומים לניתוח מערך JSON.
**בדיקת תאימות**: בדיקת תאימות סכימה מתבצעת עבור כל אובייקט, מה שמוסיף תקורה אך
  מאפשר תוצאות חלקיות במקרה של כשל בבדיקת התאימות.
=======
**זיכרון**: ניתוח שורה אחר שורה משתמש בפחות זיכרון שיא בהשוואה לטעינת
  מערכי JSON שלמים.
**השהיה**: ביצועי הניתוח דומים לניתוח מערך JSON.
**בדיקה**: בדיקת סכימה מתבצעת עבור כל אובייקט, מה שמוסיף תקורה אך
  מאפשר תוצאות חלקיות במקרה של כשל בבדיקה.
>>>>>>> 82edf2d (New md files from RunPod)

## אסטרטגיית בדיקות

### בדיקות יחידה

ניתוח JSONL עם קלט תקין.
ניתוח JSONL עם שורות ריקות.
ניתוח JSONL עם גדרות קוד Markdown.
ניתוח JSONL עם שורה אחרונה חתוכה.
ניתוח JSONL עם שורות JSON לא תקינות המפוזרות.
<<<<<<< HEAD
בדיקת תאימות סכימה עם איחודים מובחנים של `oneOf`.
=======
בדיקת סכימה עם איחודים מובחנים של `oneOf`.
>>>>>>> 82edf2d (New md files from RunPod)
תאימות לאחור: הנחיות `"text"` ו-`"json"` קיימות אינן משתנות.

### בדיקות אינטגרציה

חילוץ מקצה לקצה עם הנחיות JSONL.
חילוץ עם קיצוץ מדומם (תגובה מוגבלת באופן מלאכותי).
חילוץ מסוגים מעורבים עם מפריד סוגים.
חילוץ אונטולוגיה עם שלושת הסוגים.

### בדיקות איכות חילוץ

השוואת תוצאות חילוץ: פורמט JSONL לעומת מערך JSON.
<<<<<<< HEAD
בדיקת עמידות בפני קיטוע: JSONL מניב תוצאות חלקיות כאשר JSON נכשל.
=======
בדיקת עמידות בפני קיטוע: פורמט JSONL מספק תוצאות חלקיות כאשר פורמט JSON נכשל.
>>>>>>> 82edf2d (New md files from RunPod)

## תוכנית מעבר

### שלב 1: הטמעה

1. הטמעת שיטה `parse_jsonl()` ב-`PromptManager`.
2. הרחבת `invoke()` כדי לטפל ב-`response-type: "jsonl"`.
3. הוספת בדיקות יחידה.

### שלב 2: מעבר להנחיות

1. עדכון ההנחיה והתצורה של `extract-definitions`.
2. עדכון ההנחיה והתצורה של `extract-relationships`.
3. עדכון ההנחיה והתצורה של `extract-topics`.
4. עדכון ההנחיה והתצורה של `extract-rows`.
5. עדכון ההנחיה והתצורה של `agent-kg-extract`.
6. עדכון ההנחיה והתצורה של `extract-with-ontologies`.

### שלב 3: עדכונים במערכות משימתיות

<<<<<<< HEAD
1. עדכון כל קוד המשתמש בתוצאות החילוץ כדי לטפל בסוג החזרה של רשימה.
2. עדכון קוד המקטלג חילוצים מסוגים מעורבים לפי שדה `type`.
=======
1. עדכון כל קוד הצורך בתוצאות החילוץ כדי לטפל בסוג החזרה של רשימה.
2. עדכון קוד שמקטלג חילוצים מסוגים מעורבים לפי שדה `type`.
>>>>>>> 82edf2d (New md files from RunPod)
3. עדכון בדיקות המאמתות את פורמט הפלט של החילוץ.

## שאלות פתוחות

אין כרגע.

## הפניות

יישום נוכחי: `trustgraph-flow/trustgraph/template/prompt_manager.py`.
מפרט JSON Lines: https://jsonlines.org/.
סכימת JSON `oneOf`: https://json-schema.org/understanding-json-schema/reference/combining.html#oneof.
מפרט קשור: Streaming LLM Responses (`docs/tech-specs/streaming-llm-responses.md`).
