# שינויים בסכימת נתונים מובנית עבור פולסר

## סקירה כללית

בהתבסס על מפרט ה-STRUCTURED_DATA.md, המסמך מציע את התוספות והשינויים הנדרשים בסכימת פולסר כדי לתמוך ביכולות נתונים מובנות ב-TrustGraph.

## שינויים בסכימה נדרשים

### 1. שיפורים בסכימה הליבה

#### הגדרת שדה משופרת
המחלקה `Field` הקיימת בקובץ `core/primitives.py` זקוקה לתכונות נוספות:

```python
class Field(Record):
    name = String()
    type = String()  # int, string, long, bool, float, double, timestamp
    size = Integer()
    primary = Boolean()
    description = String()
    # שדות חדשים:
    required = Boolean()  # האם השדה נדרש
    enum_values = Array(String())  # עבור סוגי שדות enum
    indexed = Boolean()  # האם השדה צריך להיות מצביע
```

### 2. סכימות ידע חדשות

#### 2.1 שליחת נתונים מובנים
קובץ חדש: `knowledge/structured.py`

```python
from pulsar.schema import Record, String, Bytes, Map
from ..core.metadata import Metadata

class StructuredDataSubmission(Record):
    metadata = Metadata()
    format = String()  # "json", "csv", "xml"
    schema_name = String()  # הפניה לסכימה בקונפיגורציה
    data = Bytes()  # נתונים גולמיים לשליחה
    options = Map(String())  # אפשרויות ספציפיות לפורמט
```

#### 3. סכימות שירות חדשות

#### 3.1 שירות שאילתות NLP לנתונים מובנים
קובץ חדש: `services/nlp_query.py`

```python
from pulsar.schema import Record, String, Array, Map, Integer, Double
from ..core.primitives import Error

class NLPToStructuredQueryRequest(Record):
    natural_language_query = String()
    max_results = Integer()
    context_hints = Map(String())  # הקשר אופציונלי לשליפת שאילתה

class NLPToStructuredQueryResponse(Record):
    error = Error()
    graphql_query = String()  # שאילתת GraphQL שנוצרה
    variables = Map(String())  # משתני GraphQL אם יש
    detected_schemas = Array(String())  # אילו סכימות השאילתה מכוונות
    confidence = Double()
```

#### 3.2 שירות שאילתות מובנות
קובץ חדש: `services/structured_query.py`

```python
from pulsar.schema import Record, String, Map, Array
from ..core.primitives import Error

class StructuredQueryRequest(Record):
    query = String()  # שאילתת GraphQL
    variables = Map(String())  # משתני GraphQL
    operation_name = String()  # שם פעולה אופציונלי למסמכים מרובי פעולות

class StructuredQueryResponse(Record):
    error = Error()
    data = String()  # נתוני התגובה של GraphQL מקודדים ב-JSON
    errors = Array(String())  # שגיאות GraphQL אם יש
```

#### 2.2 פלט חילוץ אובייקטים
קובץ חדש: `knowledge/object.py`

```python
from pulsar.schema import Record, String, Map, Double
from ..core.metadata import Metadata

class ExtractedObject(Record):
    metadata = Metadata()
    schema_name = String()  # לאיזו סכימה השם הזה שייך
    values = Map(String())  # שם שדה -> ערך
    confidence = Double()
    source_span = String()  # טקסט השדה בו נמצא האובייקט
```

### 4. סכימות ידע משופרות

#### 4.1 שיפור אמצעי הטבע
עדכן את `knowledge/embeddings.py` כדי לתמוך טוב יותר באמצעי הטבע מובנים:

```python
class StructuredObjectEmbedding(Record):
    metadata = Metadata()
    vectors = Array(Array(Double()))
    schema_name = String()
    object_id = String()  # ערך מפתח ראשי
    field_embeddings = Map(Array(Double()))  # אמצעי הטבע לכל שדה
```

## נקודות אינטגרציה

### אינטגרציה של זרימה

הסכימות ישמשו על ידי מודולי זרימה חדשים:
- `trustgraph-flow/trustgraph/decoding/structured` - משתמש ב-StructuredDataSubmission
- `trustgraph-flow/trustgraph/query/nlp_query/cassandra` - משתמש בסכימות שאילתות NLP
- `trustgraph-flow/trustgraph/query/objects/cassandra` - משתמש בסכימות שאילתות מובנות
- `trustgraph-flow/trustgraph/extract/object/row/` - צורך Chunk, מייצר ExtractedObject
- `trustgraph-flow/trustgraph/storage/objects/cassandra` - משתמש בסכימה Rows
- `trustgraph-flow/trustgraph/embeddings/object_embeddings/qdrant` - משתמש בסכימות אמצעי הטבע

## הערות על יישום

1. **גרסת סכימה**: כדאי להוסיף שדה `version` ל-RowSchema לתמיכה בעדכונים עתידיים.
2. **מערכת סוגים**: ה-`Field.type` צריך לתמוך בכל סוגי הנתונים המקוריים של Cassandra.
3. **פעולות אצווה**: רוב השירותים צריכים לתמוך הן בפעולות בודדות והן בפעולות אצווה.
4. **טיפול בשגיאות**: דיווח אחיד על שגיאות בכל השירותים החדשים.
5. **תאימות לאחור**: הסכימות הקיימות נשארות ללא שינוי, מלבד שיפורים קטנים בשדות.

## שלבים הבאים

1. יישום קבצי הסכימה במבנה החדש.
2. עדכון שירותים קיימים כדי לזהות סוגי סכימה חדשים.
3. יישום מודולי זרימה המשתמשים בסכימות אלה.
4. הוספת סיומות גשר/rev-גשר לשירותים החדשים.
5. יצירת בדיקות יחידה עבור אימות סכימה.