# מפרט טכני: שיפור ביצועים של בסיס הידע Cassandra

**סטטוס:** טיוטה
**כותב:** עוזר
**תאריך:** 2025-09-18

## סקירה כללית

מפרט זה עוסק בבעיות ביצועים ביישום בסיס הידע Cassandra של TrustGraph ומציע אופטימיזציות לאחסון ושליפה של משולשות RDF.

## יישום נוכחי

### עיצוב הסכימה

היישום הנוכחי משתמש בעיצוב טבלה יחידה ב-`trustgraph-flow/trustgraph/direct/cassandra_kg.py`:

```sql
CREATE TABLE triples (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY (collection, s, p, o)
);
```

**אינדקסים משניים:**
`triples_s` על `s` (נושא)
`triples_p` על `p` (נשוא)
`triples_o` על `o` (אובייקט)

### תבניות שאילתה

המימוש הנוכחי תומך ב-8 תבניות שאילתה מובחנות:

1. **get_all(collection, limit=50)** - שליפה של כל השלשות עבור אוסף
   ```sql
   SELECT s, p, o FROM triples WHERE collection = ? LIMIT 50
   ```

2. **get_s(collection, s, limit=10)** - שאילתה לפי נושא.
   ```sql
   SELECT p, o FROM triples WHERE collection = ? AND s = ? LIMIT 10
   ```

3. **get_p(collection, p, limit=10)** - שאילתה לפי תנאי.
   ```sql
   SELECT s, o FROM triples WHERE collection = ? AND p = ? LIMIT 10
   ```

4. **get_o(collection, o, limit=10)** - שאילתה לפי אובייקט.
   ```sql
   SELECT s, p FROM triples WHERE collection = ? AND o = ? LIMIT 10
   ```

5. **get_sp(collection, s, p, limit=10)** - שאילתה לפי נושא + טענה
   ```sql
   SELECT o FROM triples WHERE collection = ? AND s = ? AND p = ? LIMIT 10
   ```

6. **get_po(collection, p, o, limit=10)** - שאילתה לפי תנאי + אובייקט ⚠️
   ```sql
   SELECT s FROM triples WHERE collection = ? AND p = ? AND o = ? LIMIT 10 ALLOW FILTERING
   ```

7. **get_os(collection, o, s, limit=10)** - שאילתה לפי אובייקט + נושא ⚠️
   ```sql
   SELECT p FROM triples WHERE collection = ? AND o = ? AND s = ? LIMIT 10 ALLOW FILTERING
   ```

8. **get_spo(collection, s, p, o, limit=10)** - התאמה מדויקת לשלושה חלקים (subject, predicate, object).
   ```sql
   SELECT s as x FROM triples WHERE collection = ? AND s = ? AND p = ? AND o = ? LIMIT 10
   ```

### ארכיטקטורה נוכחית

**קובץ: `trustgraph-flow/trustgraph/direct/cassandra_kg.py`**
מחלקה יחידה `KnowledgeGraph` המטפלת בכל הפעולות
בריכת חיבורים באמצעות רשימה גלובלית `_active_clusters`
שם טבלה קבוע: `"triples"`
מרחב מפתחות לכל מודל משתמש
שכפול SimpleStrategy עם גורם 1

**נקודות אינטגרציה:**
**נתיב כתיבה:** `trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
**נתיב שאילתה:** `trustgraph-flow/trustgraph/query/triples/cassandra/service.py`
**מאגר ידע:** `trustgraph-flow/trustgraph/tables/knowledge.py`

## בעיות ביצועים שזוהו

### בעיות ברמת הסכימה

1. **עיצוב מפתח ראשי לא יעיל**
   נוכחי: `PRIMARY KEY (collection, s, p, o)`
   גורם לקיבוץ לקוי עבור דפוסי גישה נפוצים
   מחייב שימוש באינדקסים משניים יקרים

2. **שימוש יתר באינדקסים משניים** ⚠️
   שלושה אינדקסים משניים על עמודות עם קרדינליות גבוהה (s, p, o)
   אינדקסים משניים ב-Cassandra הם יקרים ואינם מתאימים להרחבה
   שאילתות 6 ו-7 דורשות `ALLOW FILTERING` המצביע על מודל נתונים לקוי

3. **סיכון לחלוקות חמות**
   מפתח חלוקה יחיד `collection` יכול ליצור חלוקות חמות
   אוספים גדולים יתרכזו בצמתים בודדים
   אין אסטרטגיית חלוקה לאיזון עומסים

### בעיות ברמת השאילתה

1. **שימוש ב-ALLOW FILTERING** ⚠️
   שני סוגי שאילתות (get_po, get_os) דורשים `ALLOW FILTERING`
   שאילתות אלו סורקות מספר חלוקות ויקרות מאוד
   הביצועים יורדים באופן ליניארי עם גודל הנתונים

2. **דפוסי גישה לא יעילים**
   אין אופטימיזציה עבור דפוסי שאילתות RDF נפוצים
   חסרים אינדקסים מורכבים עבור שילובים תכופים של שאילתות
   אין התחשבות בדפוסי מעבר גרפים

3. **חוסר באופטימיזציה של שאילתות**
   אין שמירת מטמון של הצהרות מוכנות
   אין רמזים או אסטרטגיות אופטימיזציה לשאילתות
   אין התחשבות בדף אחרי דף מעבר לפונקציית LIMIT פשוטה

## הצהרת בעיה

ליישום בסיס הידע הנוכחי של Cassandra ישנם שני צווארי בקבוק ביצועים קריטיים:

### 1. ביצועים לא יעילים של שאילתת get_po

השאילתה `get_po(collection, p, o)` אינה יעילה מאוד מכיוון שהיא דורשת `ALLOW FILTERING`:

```sql
SELECT s FROM triples WHERE collection = ? AND p = ? AND o = ? LIMIT 10 ALLOW FILTERING
```

**מדוע זה בעייתי:**
`ALLOW FILTERING` גורם לקסנדרה לסרוק את כל המחיצות בתוך האוסף.
הביצועים יורדים באופן ליניארי עם גודל הנתונים.
זהו דפוס שאילתות RDF נפוץ (מציאת נושאים שיש להם קשר ספציפי של נשוא-פועל-מושא).
זה יוצר עומס משמעותי על האשכול ככל שהנתונים גדלים.

### 2. אסטרטגיית קיבוץ לקויה

המפתח הראשי הנוכחי `PRIMARY KEY (collection, s, p, o)` מספק יתרונות קיבוץ מינימליים:

**בעיות עם הקיבוץ הנוכחי:**
`collection` כמפתח מחיצה לא מפזר את הנתונים בצורה יעילה.
רוב האוספים מכילים נתונים מגוונים, מה שהופך את הקיבוץ ללא יעיל.
אין התחשבות בדפוסי גישה נפוצים בשאילתות RDF.
אוספים גדולים יוצרים מחיצות "חמות" על צמתים בודדים.
עמודות הקיבוץ (s, p, o) אינן מייעלות עבור דפוסי מעבר גרפים טיפוסיים.

**השפעה:**
שאילתות אינן נהנות ממיקום נתונים.
ניצולת מטמון לקויה.
חלוקת עומסים לא אחידה בין צמתי האשכול.
צווארי בקבוק של יכולת הרחבה ככל שהאוספים גדלים.

## פתרון מוצע: אסטרטגיית דה-נורמליזציה של 4 טבלאות

### סקירה כללית

החליפו את הטבלה הבודדת `triples` בארבע טבלאות ייעודיות, כל אחת מותאמת לדפוסי שאילתות ספציפיים. זה מבטל את הצורך באינדקסים משניים וב-ALLOW FILTERING תוך מתן ביצועים אופטימליים לכל סוגי השאילתות. הטבלה הרביעית מאפשרת מחיקת אוספים יעילה למרות מפתחות מחיצה מורכבים.

### עיצוב סכימה חדש

**טבלה 1: שאילתות ממוקדות בנושא (triples_s)**
```sql
CREATE TABLE triples_s (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY ((collection, s), p, o)
);
```
**משפר:** get_s, get_sp, get_os
**מפתח מחיצה:** (collection, s) - פיזור טוב יותר מאשר רק collection
**קיבוץ:** (p, o) - מאפשר חיפושים יעילים של טווחים/אובייקטים עבור נושא

**טבלה 2: שאילתות של טריפלטים (predicate-object) (triples_p)**
```sql
CREATE TABLE triples_p (
    collection text,
    p text,
    o text,
    s text,
    PRIMARY KEY ((collection, p), o, s)
);
```
**משפר:** get_p, get_po (מבטל את ALLOW FILTERING!)
**מפתח מחיצה:** (collection, p) - גישה ישירה באמצעות תנאי
**קיבוץ:** (o, s) - מעבר יעיל בין אובייקט לנושא

**טבלה 3: שאילתות ממוקדות אובייקט (triples_o)**
```sql
CREATE TABLE triples_o (
    collection text,
    o text,
    s text,
    p text,
    PRIMARY KEY ((collection, o), s, p)
);
```
**אופטימיזציה:** get_o
**מפתח מחיצה:** (collection, o) - גישה ישירה באמצעות אובייקט
**קיבוץ:** (s, p) - מעבר יעיל בין נושא ופועל

**טבלה 4: ניהול אוספים ושאילתות SPO (triples_collection)**
```sql
CREATE TABLE triples_collection (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY (collection, s, p, o)
);
```
**אופטימיזציה:** get_spo, delete_collection
**מפתח מחיצה:** רק אוסף - מאפשר פעולות יעילות ברמת האוסף.
**קיבוץ:** (s, p, o) - סדר משולש סטנדרטי.
**מטרה:** שימוש כפול לחיפושים מדויקים של SPO וגם כמדד למחיקה.

### מיפוי שאילתות

| שאילתה מקורית | טבלה יעד | שיפור ביצועים |
|----------------|-------------|------------------------|
| get_all(collection) | triples_s | ALLOW FILTERING (מתאים לסריקה) |
| get_s(collection, s) | triples_s | גישה ישירה למחיצה |
| get_p(collection, p) | triples_p | גישה ישירה למחיצה |
| get_o(collection, o) | triples_o | גישה ישירה למחיצה |
| get_sp(collection, s, p) | triples_s | מחיצה + קיבוץ |
| get_po(collection, p, o) | triples_p | **אין יותר ALLOW FILTERING!** |
| get_os(collection, o, s) | triples_o | מחיצה + קיבוץ |
| get_spo(collection, s, p, o) | triples_collection | חיפוש מפתח מדויק |
| delete_collection(collection) | triples_collection | קריאת מדד, מחיקה אצווה של הכל |

### אסטרטגיית מחיקת אוסף

עם מפתחות מחיצה מורכבים, אי אפשר פשוט לבצע `DELETE FROM table WHERE collection = ?`. במקום זאת:

1. **שלב קריאה:** שאילתא `triples_collection` כדי לרשום את כל המשולשים:
   ```sql
   SELECT s, p, o FROM triples_collection WHERE collection = ?
   ```
   זה יעיל מכיוון ש-`collection` הוא מפתח החלוקה עבור הטבלה הזו.

2. **שלב המחיקה:** עבור כל שלישייה (s, p, o), מחקו מכל 4 הטבלאות תוך שימוש במפתחות חלוקה מלאים:
   ```sql
   DELETE FROM triples_s WHERE collection = ? AND s = ? AND p = ? AND o = ?
   DELETE FROM triples_p WHERE collection = ? AND p = ? AND o = ? AND s = ?
   DELETE FROM triples_o WHERE collection = ? AND o = ? AND s = ? AND p = ?
   DELETE FROM triples_collection WHERE collection = ? AND s = ? AND p = ? AND o = ?
   ```
   מחולק לקבוצות של 100 רשומות לטובת יעילות.

**ניתוח פשרות:**
✅ שומר על ביצועי שאילתות אופטימליים עם מחיצות מבוזרות.
✅ אין מחיצות עמוסות עבור אוספים גדולים.
❌ לוגיקת מחיקה מורכבת יותר (קריאה ואז מחיקה).
❌ זמן מחיקה תלוי בגודל האוסף.

### יתרונות

1. **מבטל את ALLOW FILTERING** - לכל שאילתה יש נתיב גישה אופטימלי (מלבד סריקת get_all).
2. **ללא אינדקסים משניים** - כל טבלה היא האינדקס לדפוס השאילתה שלה.
3. **הפצת נתונים טובה יותר** - מפתחות מחיצה מורכבים מפזרים את העומס בצורה יעילה.
4. **ביצועים צפויים** - זמן שאילתה תלוי בגודל התוצאה, ולא בגודל הנתונים הכולל.
5. **מנצל את החוזקות של Cassandra** - תוכנן עבור ארכיטקטורת Cassandra.
6. **מאפשר מחיקת אוספים** - triples_collection משמש כמחירון מחיקה.

## תוכנית יישום

### קבצים הדורשים שינוי

#### קובץ יישום ראשי

**`trustgraph-flow/trustgraph/direct/cassandra_kg.py`** - נדרש כתיבה מחדש מלאה.

**שיטות שיש לשכתב:**
```python
# Schema initialization
def init(self) -> None  # Replace single table with three tables

# Insert operations
def insert(self, collection, s, p, o) -> None  # Write to all three tables

# Query operations (API unchanged, implementation optimized)
def get_all(self, collection, limit=50)      # Use triples_by_subject
def get_s(self, collection, s, limit=10)     # Use triples_by_subject
def get_p(self, collection, p, limit=10)     # Use triples_by_po
def get_o(self, collection, o, limit=10)     # Use triples_by_object
def get_sp(self, collection, s, p, limit=10) # Use triples_by_subject
def get_po(self, collection, p, o, limit=10) # Use triples_by_po (NO ALLOW FILTERING!)
def get_os(self, collection, o, s, limit=10) # Use triples_by_subject
def get_spo(self, collection, s, p, o, limit=10) # Use triples_by_subject

# Collection management
def delete_collection(self, collection) -> None  # Delete from all three tables
```

#### קבצי אינטגרציה (אין צורך בשינויים לוגיים)

**`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`**
אין צורך בשינויים - משתמשים ב-API של KnowledgeGraph הקיים
נהנים אוטומטית משיפורי ביצועים

**`trustgraph-flow/trustgraph/query/triples/cassandra/service.py`**
אין צורך בשינויים - משתמשים ב-API של KnowledgeGraph הקיים
נהנים אוטומטית משיפורי ביצועים

### קבצי בדיקה הדורשים עדכונים

#### בדיקות יחידה
**`tests/unit/test_storage/test_triples_cassandra_storage.py`**
עדכון ציפיות הבדיקה עבור שינויים בסכימה
הוספת בדיקות עבור עקביות בין טבלאות מרובות
אימות היעדר ALLOW FILTERING בתוכניות שאילתות

**`tests/unit/test_query/test_triples_cassandra_query.py`**
עדכון טענות ביצועים
בדיקת כל 8 דפוסי השאילתות מול טבלאות חדשות
אימות ניתוב השאילתות לטבלאות הנכונות

#### בדיקות אינטגרציה
**`tests/integration/test_cassandra_integration.py`**
בדיקות מקצה לקצה עם סכימה חדשה
השוואות ביצועים
אימות עקביות נתונים בין טבלאות

**`tests/unit/test_storage/test_cassandra_config_integration.py`**
עדכון בדיקות אימות סכימה
בדיקת תרחישי מעבר

### אסטרטגיית יישום

#### שלב 1: סכימה ושיטות ליבה
1. **כתיבת מחדש של `init()`** - יצירת ארבע טבלאות במקום אחת
2. **כתיבת מחדש של `insert()`** - כתיבה באצווה לכל ארבע הטבלאות
3. **יישום הצהרות מוכנות** - לביצועים אופטימליים
4. **הוספת לוגיקת ניתוב טבלאות** - הפניית שאילתות לטבלאות האופטימליות
5. **יישום מחיקת אוספים** - קריאה מ-triples_collection, מחיקה באצווה מכל הטבלאות

#### שלב 2: אופטימיזציה של שיטות שאילתה
1. **כתיבת מחדש של כל שיטת get_*** לשימוש בטבלה האופטימלית
2. **הסרת כל השימושים ב-ALLOW FILTERING**
3. **יישום שימוש יעיל במפתח מיון**
4. **הוספת רישום ביצועי שאילתות**

#### שלב 3: ניהול אוספים
1. **עדכון `delete_collection()`** - הסרה מכל שלושת הטבלאות
2. **הוספת אימות עקביות** - הבטחת סנכרון בין כל הטבלאות
3. **יישום פעולות באצווה** - לפעולות מרובות טבלאות אטומיות

### פרטי יישום מרכזיים

#### אסטרטגיית כתיבה באצווה
```python
def insert(self, collection, s, p, o):
    batch = BatchStatement()

    # Insert into all four tables
    batch.add(self.insert_subject_stmt, (collection, s, p, o))
    batch.add(self.insert_po_stmt, (collection, p, o, s))
    batch.add(self.insert_object_stmt, (collection, o, s, p))
    batch.add(self.insert_collection_stmt, (collection, s, p, o))

    self.session.execute(batch)
```

#### לוגיקת ניתוב שאילתות
```python
def get_po(self, collection, p, o, limit=10):
    # Route to triples_p table - NO ALLOW FILTERING!
    return self.session.execute(
        self.get_po_stmt,
        (collection, p, o, limit)
    )

def get_spo(self, collection, s, p, o, limit=10):
    # Route to triples_collection table for exact SPO lookup
    return self.session.execute(
        self.get_spo_stmt,
        (collection, s, p, o, limit)
    )
```

#### לוגיקת מחיקת אוספים
```python
def delete_collection(self, collection):
    # Step 1: Read all triples from collection table
    rows = self.session.execute(
        f"SELECT s, p, o FROM {self.collection_table} WHERE collection = %s",
        (collection,)
    )

    # Step 2: Batch delete from all 4 tables
    batch = BatchStatement()
    count = 0

    for row in rows:
        s, p, o = row.s, row.p, row.o

        # Delete using full partition keys for each table
        batch.add(SimpleStatement(
            f"DELETE FROM {self.subject_table} WHERE collection = ? AND s = ? AND p = ? AND o = ?"
        ), (collection, s, p, o))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.po_table} WHERE collection = ? AND p = ? AND o = ? AND s = ?"
        ), (collection, p, o, s))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.object_table} WHERE collection = ? AND o = ? AND s = ? AND p = ?"
        ), (collection, o, s, p))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.collection_table} WHERE collection = ? AND s = ? AND p = ? AND o = ?"
        ), (collection, s, p, o))

        count += 1

        # Execute every 100 triples to avoid oversized batches
        if count % 100 == 0:
            self.session.execute(batch)
            batch = BatchStatement()

    # Execute remaining deletions
    if count % 100 != 0:
        self.session.execute(batch)

    logger.info(f"Deleted {count} triples from collection {collection}")
```

#### אופטימיזציה של הצהרת הכנה (Prepared Statement)
```python
def prepare_statements(self):
    # Cache prepared statements for better performance
    self.insert_subject_stmt = self.session.prepare(
        f"INSERT INTO {self.subject_table} (collection, s, p, o) VALUES (?, ?, ?, ?)"
    )
    self.insert_po_stmt = self.session.prepare(
        f"INSERT INTO {self.po_table} (collection, p, o, s) VALUES (?, ?, ?, ?)"
    )
    self.insert_object_stmt = self.session.prepare(
        f"INSERT INTO {self.object_table} (collection, o, s, p) VALUES (?, ?, ?, ?)"
    )
    self.insert_collection_stmt = self.session.prepare(
        f"INSERT INTO {self.collection_table} (collection, s, p, o) VALUES (?, ?, ?, ?)"
    )
    # ... query statements
```

## אסטרטגיית מעבר

### גישת מעבר נתונים

#### אפשרות 1: פריסה בצבע כחול-ירוק (מומלץ)
1. **פריסת הסכימה החדשה לצד הקיימת** - השתמש בשמות טבלאות שונים באופן זמני
2. **תקופת כתיבה כפולה** - כתיבה גם לסכימה הישנה וגם לחדשה במהלך המעבר
3. **מעבר נתונים ברקע** - העתקת נתונים קיימים לטבלאות חדשות
4. **הפניית שאילתות** - הפניית שאילתות לטבלאות החדשות לאחר שהנתונים עברו
5. **מחיקת הטבלאות הישנות** - לאחר תקופת אימות

#### אפשרות 2: מעבר במקום
1. **הוספת סכימה** - יצירת טבלאות חדשות במרחב מפתחות קיים
2. **סקריפט מעבר נתונים** - העתקה באצווה מטבלה ישנה לטבלאות חדשות
3. **עדכון יישום** - פריסת קוד חדש לאחר השלמת המעבר
4. **ניקוי הטבלה הישנה** - הסרת הטבלה הישנה והאינדקסים

### תאימות לאחור

#### אסטרטגיית פריסה
```python
# Environment variable to control table usage during migration
USE_LEGACY_TABLES = os.getenv('CASSANDRA_USE_LEGACY', 'false').lower() == 'true'

class KnowledgeGraph:
    def __init__(self, ...):
        if USE_LEGACY_TABLES:
            self.init_legacy_schema()
        else:
            self.init_optimized_schema()
```

#### סקריפט הגירה
```python
def migrate_data():
    # Read from old table
    old_triples = session.execute("SELECT collection, s, p, o FROM triples")

    # Batch write to new tables
    for batch in batched(old_triples, 100):
        batch_stmt = BatchStatement()
        for row in batch:
            # Add to all three new tables
            batch_stmt.add(insert_subject_stmt, row)
            batch_stmt.add(insert_po_stmt, (row.collection, row.p, row.o, row.s))
            batch_stmt.add(insert_object_stmt, (row.collection, row.o, row.s, row.p))
        session.execute(batch_stmt)
```

### אסטרטגיית אימות

#### בדיקות עקביות נתונים
```python
def validate_migration():
    # Count total records in old vs new tables
    old_count = session.execute("SELECT COUNT(*) FROM triples WHERE collection = ?", (collection,))
    new_count = session.execute("SELECT COUNT(*) FROM triples_by_subject WHERE collection = ?", (collection,))

    assert old_count == new_count, f"Record count mismatch: {old_count} vs {new_count}"

    # Spot check random samples
    sample_queries = generate_test_queries()
    for query in sample_queries:
        old_result = execute_legacy_query(query)
        new_result = execute_optimized_query(query)
        assert old_result == new_result, f"Query results differ for {query}"
```

## אסטרטגיית בדיקות

### בדיקות ביצועים

#### תרחישי ביצוע
1. **השוואת ביצועי שאילתות**
   מדדי ביצועים לפני ואחרי עבור כל 8 סוגי השאילתות
   התמקדות בשיפור ביצועים של שאילתת get_po (הסרת ALLOW FILTERING)
   מדידת השהייה של שאילתות בתנאי גדלי נתונים שונים

2. **בדיקות עומסים**
   ביצוע שאילתות במקביל
   קצב כתיבה עם פעולות אצווה
   ניצול זיכרון ו-CPU

3. **בדיקות סקלאביליות**
   ביצועים עם גדלי אוספים גדלים
   חלוקת שאילתות בין אוספים מרובים
   ניצול צמתים באשכול

#### סטי נתוני בדיקה
**קטן:** 10 אלף משולשים לאוסף
**בינוני:** 100 אלף משולשים לאוסף
**גדול:** 1 מיליון+ משולשים לאוסף
**אוספים מרובים:** בדיקת חלוקת מחיצות

### בדיקות פונקציונליות

#### עדכוני בדיקות יחידה
```python
# Example test structure for new implementation
class TestCassandraKGPerformance:
    def test_get_po_no_allow_filtering(self):
        # Verify get_po queries don't use ALLOW FILTERING
        with patch('cassandra.cluster.Session.execute') as mock_execute:
            kg.get_po('test_collection', 'predicate', 'object')
            executed_query = mock_execute.call_args[0][0]
            assert 'ALLOW FILTERING' not in executed_query

    def test_multi_table_consistency(self):
        # Verify all tables stay in sync
        kg.insert('test', 's1', 'p1', 'o1')

        # Check all tables contain the triple
        assert_triple_exists('triples_by_subject', 'test', 's1', 'p1', 'o1')
        assert_triple_exists('triples_by_po', 'test', 'p1', 'o1', 's1')
        assert_triple_exists('triples_by_object', 'test', 'o1', 's1', 'p1')
```

#### עדכונים לבדיקות אינטגרציה
```python
class TestCassandraIntegration:
    def test_query_performance_regression(self):
        # Ensure new implementation is faster than old
        old_time = benchmark_legacy_get_po()
        new_time = benchmark_optimized_get_po()
        assert new_time < old_time * 0.5  # At least 50% improvement

    def test_end_to_end_workflow(self):
        # Test complete write -> query -> delete cycle
        # Verify no performance degradation in integration
```

### תוכנית חזרה אחורה

#### אסטרטגיה מהירה לחזרה אחורה
1. **החלפת משתנה סביבה** - חזרה מיידית לטבלאות הישנות.
2. **שמירה על הטבלאות הישנות** - לא למחוק עד שיוכח שיפור בביצועים.
3. **התראות ניטור** - הפעלת חזרה אוטומטית בהתבסס על שיעורי שגיאות/השהייה.

#### אימות חזרה אחורה
```python
def rollback_to_legacy():
    # Set environment variable
    os.environ['CASSANDRA_USE_LEGACY'] = 'true'

    # Restart services to pick up change
    restart_cassandra_services()

    # Validate functionality
    run_smoke_tests()
```

## סיכונים ושיקולים

### סיכוני ביצועים
**עלייה בלעדי כתיבה** - 4 פעולות כתיבה לכל הוספה (33% יותר מהגישה של 3 טבלאות)
**תקורת אחסון** - דרישת אחסון של 4x (33% יותר מהגישה של 3 טבלאות)
**כשלים בכתיבה אצווה** - יש צורך בטיפול תקין בשגיאות
**מורכבות מחיקה** - מחיקת אוסף דורשת לולאה של קריאה ולאחר מכן מחיקה

### סיכונים תפעוליים
**מורכבות העברה** - העברת נתונים עבור מערכי נתונים גדולים
**אתגרים של עקביות** - הבטחת סנכרון של כל הטבלאות
**פערים בניטור** - יש צורך במדדים חדשים עבור פעולות מרובות טבלאות

### אסטרטגיות הפחתת סיכונים
1. **פריסה הדרגתית** - התחילו עם אוספים קטנים
2. **ניטור מקיף** - מעקב אחר כל מדדי הביצועים
3. **אימות אוטומטי** - בדיקת עקביות רציפה
4. **יכולת ביטול מהירה** - בחירת טבלה מבוססת סביבה

## קריטריוני הצלחה

### שיפורי ביצועים
[ ] **ביטול ALLOW FILTERING** - שאילתות get_po ו-get_os פועלות ללא סינון
[ ] **הפחתת השהייה בשאילתות** - שיפור של 50%+ בזמני תגובה של שאילתות
[ ] **חלוקת עומסים טובה יותר** - ללא מחיצות "חמות", חלוקת עומסים שווה על פני צמתים בקלאסטר
[ ] **ביצועים ניתנים להרחבה** - זמן שאילתה תלוי בגודל התוצאה, ולא בנפח הנתונים הכולל

### דרישות פונקציונליות
[ ] **תאימות API** - כל הקוד הקיים ממשיך לעבוד ללא שינוי
[ ] **עקביות נתונים** - שלוש הטבלאות נשארות מסונכרנות
[ ] **אפס אובדן נתונים** - העברה שומרת על כל הטרפלים הקיימים
[ ] **תאימות לאחור** - אפשרות לחזור לסקמה הישנה

### דרישות תפעוליות
[ ] **העברה בטוחה** - פריסה בצורה כחולה-ירוקה עם יכולת ביטול
[ ] **כיסוי ניטור** - מדדים מקיפים עבור פעולות מרובות טבלאות
[ ] **כיסוי בדיקות** - כל דפוסי השאילתות נבדקו עם מדדי ביצועים
[ ] **תיעוד** - עדכון נהלי פריסה ותפעול

## ציר זמן

### שלב 1: יישום
[ ] כתיבה מחדש של `cassandra_kg.py` עם סכימת טבלאות מרובות
[ ] יישום פעולות כתיבה אצווה
[ ] הוספת אופטימיזציה של הצהרות מוכנות
[ ] עדכון בדיקות יחידה

### שלב 2: בדיקות אינטגרציה
[ ] עדכון בדיקות אינטגרציה
[ ] מדידת ביצועים
[ ] בדיקת עומסים עם נפחי נתונים ריאליים
[ ] סקריפטים לאימות עקביות נתונים

### שלב 3: תכנון העברה
[ ] סקריפטים לפריסה בצורה כחולה-ירוקה
[ ] כלים להעברת נתונים
[ ] עדכוני לוח מחוונים לניטור
[ ] נהלי ביטול

### שלב 4: פריסה לייצור
[ ] פריסה הדרגתית לסביבת ייצור
[ ] ניטור ואימות ביצועים
[ ] ניקוי טבלאות ישנות
[ ] עדכוני תיעוד

## מסקנה

אסטרטגיית הדה-נורמליזציה מרובת טבלאות פותרת ישירות את שני צווארי הבקבוק הקריטיים בביצועים:

1. **מבטלת את ALLOW FILTERING היקר** על ידי מתן מבני טבלאות אופטימליים עבור כל דפוס שאילתה
2. **משפרת את יעילות הקיבוץ** באמצעות מפתחות מחיצה מורכבים שמפיצים את העומס כראוי

הגישה ממנפת את החוזקות של Cassandra תוך שמירה על תאימות API מלאה, ומבטיחה שלקוד הקיים יש יתרונות אוטומטיים משיפורי הביצועים.
