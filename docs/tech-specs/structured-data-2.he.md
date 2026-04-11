---
layout: default
title: "מפרט טכני של נתונים מובנים (חלק 2)"
parent: "Hebrew (Beta)"
---

# מפרט טכני של נתונים מובנים (חלק 2)

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## סקירה כללית

מפרט זה עוסק בנושאים ופערים שזוהו במהלך יישום ראשוני של שילוב נתונים מובנים של TrustGraph, כפי שמתואר ב-`structured-data.md`.

## הצגת בעיות

### 1. חוסר עקביות בשמות: "אובייקט" לעומת "שורה"

יישום נוכחי משתמש בטרמינולוגיה של "אובייקט" בכל מקום (לדוגמה, `ExtractedObject`, חילוץ אובייקטים, הטמעות אובייקטים). שם זה כללי מדי וגורם לבלבול:

"אובייקט" הוא מונח מוגדר מראש בתוכנה (אובייקטים בפייתון, אובייקטים ב-JSON, וכו')
הנתונים המטופלים הם למעשה טבלאיים - שורות בטבלאות עם סכימות מוגדרות
"שורה" מתארת ​​במדויק יותר את מודל הנתונים ומתאימה לטרמינולוגיה של מסדי נתונים

חוסר עקביות זה מופיע בשמות מודולים, שמות מחלקות, סוגי הודעות ובתעוד.

### 2. מגבלות שאילתות של אחסון שורות

ליישום הנוכחי של אחסון שורות יש מגבלות שאילתות משמעותיות:

**אי התאמה לשפה טבעית**: שאילתות מתקשות עם וריאציות של נתונים מהעולם האמיתי. לדוגמה:
קשה למצוא מסד נתונים של רחובות המכיל `"CHESTNUT ST"` כאשר שואלים על `"Chestnut Street"`
קיצורים, הבדלי רישיות ווריאציות בפורמט שוברים שאילתות התאמה מדויקת
משתמשים מצפים להבנה סמנטית, אך המאגר מספק התאמה מילולית

**בעיות בהתפתחות סכימה**: שינוי סכימות גורם לבעיות:
נתונים קיימים עשויים שלא להתאים לסכימות מעודכנות
שינויים במבנה הטבלה עלולים לשבור שאילתות ושלמות נתונים
אין מסלול מעבר ברור לעדכוני סכימה

### 3. הטמעות שורות נדרשות

בהקשר לבעיה 2, המערכת זקוקה להטמעות וקטוריות עבור נתוני שורה כדי לאפשר:

חיפוש סמנטי בנתונים מובנים (מציאת "Chestnut Street" כאשר הנתונים מכילים "CHESTNUT ST")
התאמת דמיון לשאילתות מעורפלות
חיפוש היברידי המשלב מסננים מובנים עם דמיון סמנטי
תמיכה טובה יותר בשפה טבעית

שירות ההטמעה הוגדר אך לא יושם.

### 4. הטמעה של נתוני שורה לא שלמה

צינור ההטמעה של נתונים מובנים אינו פעיל במלואו:

קיימות הנחיות אבחון כדי לסווג פורמטים של קלט (CSV, JSON, וכו')
שירות ההטמעה המשתמש בהנחיות אלה אינו מחובר למערכת
אין מסלול מקצה לקצה לטעינת נתונים מובנים לאחסון השורות

## מטרות

**גמישות סכימה**: לאפשר התפתחות סכימה מבלי לשבור נתונים קיימים או לדרוש מעברים
**שמות עקביים**: לתקנן על "שורה" בכל בסיס הקוד
**יכולת שאילתא סמנטית**: לתמוך בהתאמה מעורפלת/סמנטית באמצעות הטמעות שורות
**צינור הטמעה שלם**: לספק מסלול מקצה לקצה לטעינת נתונים מובנים

## עיצוב טכני

### סכימת אחסון שורות מאוחדת

יישום קודם יצר טבלת Cassandra נפרדת עבור כל סכימה. זה גרם לבעיות כאשר הסכימות התפתחו, מכיוון ששינויים במבנה הטבלה דרשו מעברים.

העיצוב החדש משתמש בטבלה מאוחדת אחת עבור כל נתוני שורה:

```sql
CREATE TABLE rows (
    collection text,
    schema_name text,
    index_name text,
    index_value frozen<list<text>>,
    data map<text, text>,
    source text,
    PRIMARY KEY ((collection, schema_name, index_name), index_value)
)
```

#### הגדרות עמודות

| עמודה | סוג | תיאור |
|--------|------|-------------|
| `collection` | `text` | מזהה איסוף/ייבוא נתונים (ממטא-נתונים) |
| `schema_name` | `text` | שם הסכימה אליה השורה הזו מתאימה |
| `index_name` | `text` | שם השדה/ים המאומדד, מחובר באמצעות פסיק עבור אינדקסים מורכבים |
| `index_value` | `frozen<list<text>>` | ערכי האינדקס כרשימה |
| `data` | `map<text, text>` | נתוני השורה כזוגות מפתח-ערך |
| `source` | `text` | URI אופציונלי המקשר למידע על מקור בגרף הידע. מחרוזת ריקה או NULL מציינים שאין מקור. |

#### טיפול באינדקסים

כל שורה מאוחסנת מספר פעמים - פעם אחת עבור כל שדה מאומדד המוגדר בסכימה. שדות המפתח הראשוניים מטופלים כאינדקס ללא סימון מיוחד, מה שמספק גמישות עתידית.

**דוגמה לאינדקס של שדה בודד:**
הסכימה מגדירה את `email` כמאומדד
`index_name = "email"`
`index_value = ['foo@bar.com']`

**דוגמה לאינדקס מורכב:**
הסכימה מגדירה אינדקס מורכב על `region` ו-`status`
`index_name = "region,status"` (שמות השדות ממוינים ומחוברים באמצעות פסיק)
`index_value = ['US', 'active']` (הערכים באותו סדר כמו שמות השדות)

**דוגמה למפתח ראשי:**
הסכימה מגדירה את `customer_id` כמפתח ראשי
`index_name = "customer_id"`
`index_value = ['CUST001']`

#### תבניות שאילתה

כל השאילתות עוקבות אחר אותו תבנית, ללא קשר לאיזה אינדקס משתמשים:

```sql
SELECT * FROM rows
WHERE collection = 'import_2024'
  AND schema_name = 'customers'
  AND index_name = 'email'
  AND index_value = ['foo@bar.com']
```

#### פשרות עיצוביות

**יתרונות:**
שינויים בסכימה אינם מחייבים שינויים במבנה הטבלה
נתוני השורה אינם גלויים ל-Cassandra - הוספות/הסרות שדות הן שקופות
דפוס שאילתות עקבי לכל שיטות הגישה
אין אינדקסים משניים של Cassandra (שיכולים להיות איטיים בקנה מידה גדול)
סוגי Cassandra מקוריים בכל מקום (`map`, `frozen<list>`)

**פשרות:**
הגברה בכתיבה: כל הוספת שורה = N הוספות (אחת לכל שדה מועדן)
תקורה של אחסון עקב שכפול נתוני שורה
מידע על סוגים מאוחסן בתצורת הסכימה, המרה בשכבת האפליקציה

#### מודל עקביות

העיצוב מקבל מספר פישוטים:

1. **אין עדכוני שורות**: המערכת היא רק להוספה. זה מבטל חששות לגבי עקביות בעדכון עותקים מרובים של אותה שורה.

2. **סובלנות לשינויי סכימה**: כאשר הסכימות משתנות (לדוגמה, הוספת/הסרת אינדקסים), שורות קיימות שומרות על האינדוקס המקורי שלהן. שורות ישנות לא יהיו ניתנות לגילוי באמצעות אינדקסים חדשים. משתמשים יכולים למחוק וליצור מחדש סכימה כדי להבטיח עקביות במידת הצורך.

### מעקב ומחיקת מחיצות

#### הבעיה

עם מפתח המחיצה `(collection, schema_name, index_name)`, מחיקה יעילה דורשת ידיעת כל מפתחות המחיצה למחיקה. מחיקה רק לפי `collection` או `collection + schema_name` דורשת ידיעת כל ערכי `index_name` שיש להם נתונים.

#### טבלת מעקב מחיצות

טבלת חיפוש משנית עוקבת אחר אילו מחיצות קיימות:

```sql
CREATE TABLE row_partitions (
    collection text,
    schema_name text,
    index_name text,
    PRIMARY KEY ((collection), schema_name, index_name)
)
```

זה מאפשר גילוי יעיל של מחיצות עבור פעולות מחיקה.

#### התנהגות של כותב שורות

כותב השורות שומר מטמון בזיכרון של זוגות `(collection, schema_name)` רשומים. בעת עיבוד שורה:

1. בדוק אם `(collection, schema_name)` נמצא במטמון
2. אם לא שמור במטמון (השורה הראשונה עבור זוג זה):
   חפש את תצורת הסכימה כדי לקבל את כל שמות האינדקסים
   הכנס ערכים ל-`row_partitions` עבור כל `(collection, schema_name, index_name)`
   הוסף את הזוג למטמון
3. המשך בכתיבת נתוני השורה

כותב השורות גם עוקב אחר אירועי שינוי בתצורת הסכימה. כאשר סכימה משתנה, רשומות מטמון רלוונטיות נמחקים כך שהשורה הבאה תגרום לרישום מחדש עם שמות האינדקסים המעודכנים.

גישה זו מבטיחה:
כתיבות לטבלת חיפוש מתרחשות פעם אחת לכל זוג `(collection, schema_name)`, ולא לכל שורה
טבלת החיפוש משקפת את האינדקסים שהיו פעילים בעת כתיבת הנתונים
שינויי סכימה במהלך הייבוא מזוהים כראוי

#### פעולות מחיקה

**מחיקת אוסף:**
```sql
-- 1. Discover all partitions
SELECT schema_name, index_name FROM row_partitions WHERE collection = 'X';

-- 2. Delete each partition from rows table
DELETE FROM rows WHERE collection = 'X' AND schema_name = '...' AND index_name = '...';
-- (repeat for each discovered partition)

-- 3. Clean up the lookup table
DELETE FROM row_partitions WHERE collection = 'X';
```

**מחיקת אוסף וסכימה:**
```sql
-- 1. Discover partitions for this schema
SELECT index_name FROM row_partitions WHERE collection = 'X' AND schema_name = 'Y';

-- 2. Delete each partition from rows table
DELETE FROM rows WHERE collection = 'X' AND schema_name = 'Y' AND index_name = '...';
-- (repeat for each discovered partition)

-- 3. Clean up the lookup table entries
DELETE FROM row_partitions WHERE collection = 'X' AND schema_name = 'Y';
```

### הטמעות שורות

הטמעות שורות מאפשרות התאמה סמנטית/עמומה על ערכים מוענקים, תוך פתרון בעיית אי ההתאמה בשפה טבעית (לדוגמה, מציאת "CHESTNUT ST" בעת חיפוש עבור "Chestnut Street").

#### סקירה כללית של העיצוב

כל ערך מוענק מוטמע ונשמר במאגר וקטורים (Qdrant). בזמן שאילתה, השאילתה מוטמעת, וקטורים דומים נמצאים, ומטא-הנתונים המשויכים משמשים לאחזור השורות בפועל ב-Cassandra.

#### מבנה אוסף Qdrant

אוסף Qdrant אחד לכל טופל `(user, collection, schema_name, dimension)`:

**שם האוסף:** `rows_{user}_{collection}_{schema_name}_{dimension}`
השמות עוברים סינון (תווים שאינם אלפא-נומריים מוחלפים ב-`_`, אותיות קטנות, קידומות מספריות מקבלות קידומת `r_`)
**ההצדקה:** מאפשר מחיקה נקייה של מופע `(user, collection, schema_name)` על ידי מחיקת אוספי Qdrant תואמים; הסיומת של הממד מאפשרת למודלי הטמעה שונים להתקיים יחד.

#### מה מוטמע

הייצוג הטקסטואלי של ערכי אינדקס:

| סוג אינדקס | דוגמה `index_value` | טקסט להטמעה |
|------------|----------------------|---------------|
| שדה בודד | `['foo@bar.com']` | `"foo@bar.com"` |
| מורכב | `['US', 'active']` | `"US active"` (מחוברים באמצעות רווח) |

#### מבנה נקודה

כל נקודה ב-Qdrant מכילה:

```json
{
  "id": "<uuid>",
  "vector": [0.1, 0.2, ...],
  "payload": {
    "index_name": "street_name",
    "index_value": ["CHESTNUT ST"],
    "text": "CHESTNUT ST"
  }
}
```

| שדה מטען | תיאור |
|---------------|-------------|
| `index_name` | השדות המאופיינים בהטמעה זו |
| `index_value` | הרשימה המקורית של הערכים (לחיפוש בקסנדרה) |
| `text` | הטקסט שהוטמע (לצרכי ניפוי באגים/הצגה) |

הערה: `user`, `collection` ו-`schema_name` משתמעים משם האוסף של Qdrant.

#### זרימת שאילתה

1. משתמש מבקש מידע על "Chestnut Street" בתוך משתמש U, אוסף X, סכימה Y.
2. הטמע את טקסט השאילתה.
3. קבע את שם/שמות האוסף של Qdrant התואמים לפריט `rows_U_X_Y_`.
4. חפש באוספי Qdrant התואמים את הווקטורים הקרובים ביותר.
5. קבל נקודות תואמות עם מטענים המכילים `index_name` ו-`index_value`.
6. שאילתת קסנדרה:
   ```sql
   SELECT * FROM rows
   WHERE collection = 'X'
     AND schema_name = 'Y'
     AND index_name = '<from payload>'
     AND index_value = <from payload>
   ```
7. החזרת שורות תואמות

#### אופציונלי: סינון לפי שם אינדקס

שאילתות יכולות, באופן אופציונלי, לסנן לפי `index_name` ב-Qdrant כדי לחפש רק שדות ספציפיים:

**"מצא כל שדה התואם ל-'Chestnut'"** → חיפוש בכל הווקטורים באוסף
**"מצא את street_name התואם ל-'Chestnut'"** → סינון כאשר `payload.index_name = 'street_name'`

#### ארכיטקטורה

הטמעות שורות עוקבות את ה**תבנית בשני שלבים** המשמשת את GraphRAG (graph-embeddings, document-embeddings):

**שלב 1: חישוב הטמעה** (`trustgraph-flow/trustgraph/embeddings/row_embeddings/`) - צורך `ExtractedObject`, מחשב הטמעות באמצעות שירות ההטמעות, מוציא `RowEmbeddings`
**שלב 2: אחסון הטמעה** (`trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/`) - צורך `RowEmbeddings`, כותב וקטורים ל-Qdrant

כותב השורות של Cassandra הוא צרכן מקבילי נפרד:

**כותב שורות Cassandra** (`trustgraph-flow/trustgraph/storage/rows/cassandra`) - צורך `ExtractedObject`, כותב שורות ל-Cassandra

שלושת השירותים צורכים מאותו זרימה, תוך שמירה על הפרדה ביניהם. זה מאפשר:
התאמה עצמאית של כתיבת Cassandra לעומת יצירת הטמעות לעומת אחסון וקטורים
ניתן להשבית שירותי הטמעות אם אינם נחוצים
כשל בשירות אחד לא משפיע על השירותים האחרים
ארכיטקטורה עקבית עם צינורות GraphRAG

#### נתיב כתיבה

**שלב 1 (מעבד הטמעות שורות):** בעת קבלת `ExtractedObject`:

1. חפש את הסכימה כדי למצוא שדות מודדים
2. עבור כל שדה מודד:
   בנה את הייצוג הטקסטואלי של ערך האינדקס
   חשב הטמעה באמצעות שירות ההטמעות
3. הפק פלט הודעה `RowEmbeddings` המכילה את כל הווקטורים שחושבו

**שלב 2 (כתיבת הטמעות שורות ל-Qdrant):** בעת קבלת `RowEmbeddings`:

1. עבור כל הטמעה בהודעה:
   קבע את האוסף של Qdrant מ-`(user, collection, schema_name, dimension)`
   צור אוסף אם יש צורך (יצירה עצלה בכתיבה הראשונה)
   הוסף נקודה עם וקטור ו-payload

#### סוגי הודעות

```python
@dataclass
class RowIndexEmbedding:
    index_name: str              # The indexed field name(s)
    index_value: list[str]       # The field value(s)
    text: str                    # Text that was embedded
    vectors: list[list[float]]   # Computed embedding vectors

@dataclass
class RowEmbeddings:
    metadata: Metadata
    schema_name: str
    embeddings: list[RowIndexEmbedding]
```

#### אינטגרציה של מחיקה

אוספי Qdrant מתגלים באמצעות התאמה מקדימה של תבנית שם האוסף:

**מחיקת `(user, collection)`:**
1. רשום את כל אוספי Qdrant התואמים לקידומת `rows_{user}_{collection}_`
2. מחק כל אוסף תואם
3. מחק מחיצות שורות Cassandra (כפי שמפורט לעיל)
4. נקה רשומות `row_partitions`

**מחיקת `(user, collection, schema_name)`:**
1. רשום את כל אוספי Qdrant התואמים לקידומת `rows_{user}_{collection}_{schema_name}_`
2. מחק כל אוסף תואם (מטפל בממדים מרובים)
3. מחק מחיצות שורות Cassandra
4. נקה `row_partitions`

#### מיקומי מודולים

| שלב | מודול | נקודת כניסה |
|-------|--------|-------------|
| שלב 1 | `trustgraph-flow/trustgraph/embeddings/row_embeddings/` | `row-embeddings` |
| שלב 2 | `trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/` | `row-embeddings-write-qdrant` |

### API לשאילתות הטמעות שורות

שאילתת הטמעות השורות היא **API נפרד** משירות שאילתות השורות GraphQL:

| API | מטרה | בסיס נתונים |
|-----|---------|---------|
| שאילתת שורות (GraphQL) | התאמה מדויקת בשדות מועדנים | Cassandra |
| שאילתת הטמעות שורות | התאמה מעורפלת/סמנטית | Qdrant |

הפרדה זו שומרת על הפרדת אחריות:
שירות GraphQL מתמקד בשאילתות מדויקות ומובנות
ממשק הטמעות מטפל בדמיון סמנטי
זרימת עבודה של משתמש: חיפוש מעורפל באמצעות הטמעות כדי למצוא מועמדים, ולאחר מכן שאילתה מדויקת כדי לקבל את נתוני השורה המלאים

#### סכימת בקשה/תגובה

```python
@dataclass
class RowEmbeddingsRequest:
    vectors: list[list[float]]    # Query vectors (pre-computed embeddings)
    user: str = ""
    collection: str = ""
    schema_name: str = ""
    index_name: str = ""          # Optional: filter to specific index
    limit: int = 10               # Max results per vector

@dataclass
class RowIndexMatch:
    index_name: str = ""          # The matched index field(s)
    index_value: list[str] = []   # The matched value(s)
    text: str = ""                # Original text that was embedded
    score: float = 0.0            # Similarity score

@dataclass
class RowEmbeddingsResponse:
    error: Error | None = None
    matches: list[RowIndexMatch] = []
```

#### מעבד שאילתות

מודול: `trustgraph-flow/trustgraph/query/row_embeddings/qdrant`

נקודת כניסה: `row-embeddings-query-qdrant`

המעבד:
1. מקבל `RowEmbeddingsRequest` עם וקטורי שאילתה
2. מוצא את אוסף Qdrant המתאים באמצעות התאמה מקדימה
3. מחפש את הווקטורים הקרובים ביותר עם מסנן אופציונלי `index_name`
4. מחזיר `RowEmbeddingsResponse` עם מידע אינדקס תואם

#### אינטגרציה עם שער API

השער חושף שאילתות הטבעה של שורות באמצעות תבנית בקשה/תגובה סטנדרטית:

| רכיב | מיקום |
|-----------|----------|
| מפזר | `trustgraph-flow/trustgraph/gateway/dispatch/row_embeddings_query.py` |
| רישום | הוסף `"row-embeddings"` ל-`request_response_dispatchers` ב-`manager.py` |

שם ממשק זרימה: `row-embeddings`

הגדרת ממשק בתרשים זרימה:
```json
{
  "interfaces": {
    "row-embeddings": {
      "request": "non-persistent://tg/request/row-embeddings:{id}",
      "response": "non-persistent://tg/response/row-embeddings:{id}"
    }
  }
}
```

#### תמיכה ב-SDK של Python

ה-SDK מספק שיטות לשאילתות הטמעות שורות:

```python
# Flow-scoped query (preferred)
api = Api(url)
flow = api.flow().id("default")

# Query with text (SDK computes embeddings)
matches = flow.row_embeddings_query(
    text="Chestnut Street",
    collection="my_collection",
    schema_name="addresses",
    index_name="street_name",  # Optional filter
    limit=10
)

# Query with pre-computed vectors
matches = flow.row_embeddings_query(
    vectors=[[0.1, 0.2, ...]],
    collection="my_collection",
    schema_name="addresses"
)

# Each match contains:
for match in matches:
    print(match.index_name)   # e.g., "street_name"
    print(match.index_value)  # e.g., ["CHESTNUT ST"]
    print(match.text)         # e.g., "CHESTNUT ST"
    print(match.score)        # e.g., 0.95
```

#### כלי שורת הפקודה

פקודה: `tg-invoke-row-embeddings`

```bash
# Query by text (computes embedding automatically)
tg-invoke-row-embeddings \
  --text "Chestnut Street" \
  --collection my_collection \
  --schema addresses \
  --index street_name \
  --limit 10

# Query by vector file
tg-invoke-row-embeddings \
  --vectors vectors.json \
  --collection my_collection \
  --schema addresses

# Output formats
tg-invoke-row-embeddings --text "..." --format json
tg-invoke-row-embeddings --text "..." --format table
```

#### דוגמה טיפוסית לשימוש

שאילתת הטמעות השורות משמשת בדרך כלל כחלק מזרימת חיפוש "מעורפל" לחיפוש מדויק:

```python
# Step 1: Fuzzy search via embeddings
matches = flow.row_embeddings_query(
    text="chestnut street",
    collection="geo",
    schema_name="streets"
)

# Step 2: Exact lookup via GraphQL for full row data
for match in matches:
    query = f'''
    query {{
        streets(where: {{ {match.index_name}: {{ eq: "{match.index_value[0]}" }} }}) {{
            street_name
            city
            zip_code
        }}
    }}
    '''
    rows = flow.rows_query(query, collection="geo")
```

דפוס בן שני שלבים זה מאפשר:
מציאת "CHESTNUT ST" כאשר המשתמש מחפש "Chestnut Street"
שליפת נתוני שורה שלמים עם כל השדות
שילוב של דמיון סמנטי עם גישה לנתונים מובנים

### קליטת נתוני שורה

נדחה לשלב מאוחר יותר. יתוכנן יחד עם שינויי קליטה אחרים.

## השפעה על יישום

### ניתוח מצב נוכחי

ליישום הקיים יש שני מרכיבים עיקריים:

| רכיב | מיקום | שורות | תיאור |
|-----------|----------|-------|-------------|
| שירות שאילתות | `trustgraph-flow/trustgraph/query/objects/cassandra/service.py` | ~740 | מונוליטי: יצירת סכימת GraphQL, ניתוח פילטרים, שאילתות Cassandra, טיפול בבקשות |
| כותב | `trustgraph-flow/trustgraph/storage/objects/cassandra/write.py` | ~540 | יצירת טבלאות לפי סכימה, אינדקסים משניים, הוספה/מחיקה |

**דפוס שאילתות נוכחי:**
```sql
SELECT * FROM {keyspace}.o_{schema_name}
WHERE collection = 'X' AND email = 'foo@bar.com'
ALLOW FILTERING
```

**תבנית שאילתה חדשה:**
```sql
SELECT * FROM {keyspace}.rows
WHERE collection = 'X' AND schema_name = 'customers'
  AND index_name = 'email' AND index_value = ['foo@bar.com']
```

### שינויים מרכזיים

1. **הפשטת סמנטיקת שאילתות**: הסכימה החדשה תומכת רק בהתאמות מדויקות עבור `index_value`. מסנני ה-GraphQL הנוכחיים (`gt`, `lt`, `contains`, וכו') או:
   הופכים לסינון לאחר קבלת הנתונים (אם עדיין נדרש)
   מוסרים לטובת שימוש ב-API של הטמעות (embeddings) לביצוע התאמות משוערות

2. **קוד GraphQL משולב הדוק**: ה-`service.py` הנוכחי כולל יצירת טיפוסים של Strawberry, ניתוח מסננים ושאילתות ספציפיות ל-Cassandra. הוספת בסיס נתונים טבלאי נוסף תכפיל כ-400 שורות של קוד GraphQL.

### שינוי מבנה מוצע

השינוי המבני כולל שני חלקים:

#### 1. הפרדת קוד GraphQL

חילוץ רכיבי GraphQL שניתן לעשות בהם שימוש חוזר למודול משותף:

```
trustgraph-flow/trustgraph/query/graphql/
├── __init__.py
├── types.py        # Filter types (IntFilter, StringFilter, FloatFilter)
├── schema.py       # Dynamic schema generation from RowSchema
└── filters.py      # Filter parsing utilities
```

זה מאפשר:
שימוש חוזר בין בסיסי נתונים שונים
הפרדה נקייה יותר של תחומים
בדיקה קלה יותר של לוגיקת GraphQL באופן עצמאי

#### 2. יישום סכימת טבלה חדשה

שינוי הקוד הספציפי ל-Cassandra לשימוש בטבלה המאוחדת:

**כותב** (`trustgraph-flow/trustgraph/storage/rows/cassandra/`):
טבלה אחת של `rows` במקום טבלאות לכל סכימה
כתיבת N עותקים לשורה (אחד לכל אינדקס)
רישום לטבלה `row_partitions`
יצירת טבלה פשוטה יותר (הגדרה חד-פעמית)

**שירות שאילתות** (`trustgraph-flow/trustgraph/query/rows/cassandra/`):
שאילתא של הטבלה המאוחדת `rows`
שימוש במודול GraphQL חלץ ליצירת סכימה
טיפול פשוט יותר בסינון (התאמה מדויקת בלבד ברמת מסד הנתונים)

### שינוי שמות מודולים

כחלק מניקוי השמות מ-"object" ל-"row":

| נוכחי | חדש |
|---------|-----|
| `storage/objects/cassandra/` | `storage/rows/cassandra/` |
| `query/objects/cassandra/` | `query/rows/cassandra/` |
| `embeddings/object_embeddings/` | `embeddings/row_embeddings/` |

### מודולים חדשים

| מודול | מטרה |
|--------|---------|
| `trustgraph-flow/trustgraph/query/graphql/` | כלי GraphQL משותפים |
| `trustgraph-flow/trustgraph/query/row_embeddings/qdrant/` | ממשק API לשאילתות הטמעות שורות |
| `trustgraph-flow/trustgraph/embeddings/row_embeddings/` | חישוב הטמעות שורות (שלב 1) |
| `trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/` | אחסון הטמעות שורות (שלב 2) |

## הפניות

[מפרט טכני של נתונים מובנים](structured-data.md)
