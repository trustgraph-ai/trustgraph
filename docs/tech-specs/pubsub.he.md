# תשתית Pub/Sub

## סקירה כללית

מסמך זה מפרט את כל החיבורים בין בסיס הקוד של TrustGraph לתשתית ה-pub/sub. כיום, המערכת מקודדת בצורה קבועה לשימוש ב-Apache Pulsar. ניתוח זה מזהה את כל נקודות האינטגרציה כדי ליידע שינויים עתידיים לכיוון הפשטה של pub/sub הניתנת לתצורה.

## מצב נוכחי: נקודות אינטגרציה של Pulsar

### 1. שימוש ישיר בלקוח Pulsar

**מיקום:** `trustgraph-flow/trustgraph/gateway/service.py`

שער ה-API מייבא ויוצר ישירות את לקוח ה-Pulsar:

**שורה 20:** `import pulsar`
**שורות 54-61:** יצירה ישירה של `pulsar.Client()` עם `pulsar.AuthenticationToken()` אופציונלי
**שורות 33-35:** תצורת מארח ברירת מחדל של Pulsar ממשתני סביבה
**שורות 178-192:** ארגומנטים של שורת הפקודה עבור `--pulsar-host`, `--pulsar-api-key` ו-`--pulsar-listener`
**שורות 78, 124:** מעביר `pulsar_client` ל-`ConfigReceiver` ו-`DispatcherManager`

זה המיקום היחיד שבו נוצר ישירות לקוח Pulsar מחוץ לשכבת ההפשטה.

### 2. מסגרת מעבד בסיסית

**מיקום:** `trustgraph-base/trustgraph/base/async_processor.py`

המחלקה הבסיסית לכל המעבדים מספקת קישוריות ל-Pulsar:

**שורה 9:** `import _pulsar` (לטיפול בחריגים)
**שורה 18:** `from . pubsub import PulsarClient`
**שורה 38:** יוצר `pulsar_client_object = PulsarClient(**params)`
**שורות 104-108:** מאפיינים החושפים `pulsar_host` ו-`pulsar_client`
**שורה 250:** שיטה סטטית `add_args()` קוראת ל-`PulsarClient.add_args(parser)` עבור ארגומנטים של שורת הפקודה
**שורות 223-225:** טיפול בחריגים עבור `_pulsar.Interrupted`

כל המעבדים יורשים מ-`AsyncProcessor`, מה שהופך זאת לנקודת האינטגרציה המרכזית.

### 3. הפשטת צרכן

**מיקום:** `trustgraph-base/trustgraph/base/consumer.py`

צורך הודעות מתורים ומפעיל פונקציות מטפלות:

**ייבוא של Pulsar:**
**שורה 12:** `from pulsar.schema import JsonSchema`
**שורה 13:** `import pulsar`
**שורה 14:** `import _pulsar`

**שימוש ספציפי ל-Pulsar:**
**שורות 100, 102:** `pulsar.InitialPosition.Earliest` / `pulsar.InitialPosition.Latest`
**שורה 108:** עטיפה של `JsonSchema(self.schema)`
**שורה 110:** `pulsar.ConsumerType.Shared`
**שורות 104-111:** `self.client.subscribe()` עם פרמטרים ספציפיים ל-Pulsar
**שורות 143, 150, 65:** שיטות `consumer.unsubscribe()` ו-`consumer.close()`
**שורה 162:** חריגה של `_pulsar.Timeout`
**שורות 182, 205, 232:** `consumer.acknowledge()` / `consumer.negative_acknowledge()`

**קובץ מפרט:** `trustgraph-base/trustgraph/base/consumer_spec.py`
**שורה 22:** מפנה ל-`processor.pulsar_client`

### 4. הפשטת מפרסם

**מיקום:** `trustgraph-base/trustgraph/base/producer.py`

שולח הודעות לתורים:

**ייבוא של Pulsar:**
**שורה 2:** `from pulsar.schema import JsonSchema`

**שימוש ספציפי ל-Pulsar:**
**שורה 49:** עטיפה של `JsonSchema(self.schema)`
**שורות 47-51:** `self.client.create_producer()` עם פרמטרים ספציפיים ל-Pulsar (נושא, סכימה, הפעלה של חלוקה לחלקים)
**שורות 31, 76:** שיטה `producer.close()`
**שורות 64-65:** `producer.send()` עם הודעה ומאפיינים

**קובץ מפרט:** `trustgraph-base/trustgraph/base/producer_spec.py`
**שורה 18:** מפנה ל-`processor.pulsar_client`

### 5. הפשטת מפרסם

**מיקום:** `trustgraph-base/trustgraph/base/publisher.py`

פרסום הודעות אסינכרוני עם חיץ תורים:

**ייבוא של Pulsar:**
**שורה 2:** `from pulsar.schema import JsonSchema`
**שורה 6:** `import pulsar`

**שימוש ספציפי ל-Pulsar:**
**שורה 52:** עטיפה של `JsonSchema(self.schema)`
**שורות 50-54:** `self.client.create_producer()` עם פרמטרים ספציפיים ל-Pulsar
**שורות 101, 103:** `producer.send()` עם הודעה ומאפיינים אופציונליים
**שורות 106-107:** שיטות `producer.flush()` ו-`producer.close()`

### 6. הפשטת מנוי

**מיקום:** `trustgraph-base/trustgraph/base/subscriber.py`

מספק הפצת הודעות למספר נמענים ממחזורים:

**ייבוא מ-Pulsar:**
**שורה 6:** `from pulsar.schema import JsonSchema`
**שורה 8:** `import _pulsar`

**שימוש ספציפי ל-Pulsar:**
**שורה 55:** `JsonSchema(self.schema)` wrapper
**שורה 57:** `self.client.subscribe(**subscribe_args)`
**שורות 101, 136, 160, 167-172:** חריגות של Pulsar: `_pulsar.Timeout`, `_pulsar.InvalidConfiguration`, `_pulsar.AlreadyClosed`
**שורות 159, 166, 170:** שיטות צרכן: `negative_acknowledge()`, `unsubscribe()`, `close()`
**שורות 247, 251:** אישור הודעות: `acknowledge()`, `negative_acknowledge()`

**קובץ מפרט:** `trustgraph-base/trustgraph/base/subscriber_spec.py`
**שורה 19:** מפנה ל-`processor.pulsar_client`

### 7. מערכת סכימות (Heart of Darkness)

**מיקום:** `trustgraph-base/trustgraph/schema/`

כל סכימת הודעה במערכת מוגדרת באמצעות מסגרת הסכימות של Pulsar.

**אלמנטים בסיסיים:** `schema/core/primitives.py`
**שורה 2:** `from pulsar.schema import Record, String, Boolean, Array, Integer`
כל הסכימות יורשות מהמחלקה הבסיסית של Pulsar `Record`
כל סוגי השדות הם סוגי Pulsar: `String()`, `Integer()`, `Boolean()`, `Array()`, `Map()`, `Double()`

**דוגמאות לסכימות:**
`schema/services/llm.py` (שורה 2): `from pulsar.schema import Record, String, Array, Double, Integer, Boolean`
`schema/services/config.py` (שורה 2): `from pulsar.schema import Record, Bytes, String, Boolean, Array, Map, Integer`

**שמות נושאים:** `schema/core/topic.py`
**שורות 2-3:** פורמט נושא: `{kind}://{tenant}/{namespace}/{topic}`
מבנה ה-URI הזה ספציפי ל-Pulsar (לדוגמה, `persistent://tg/flow/config`)

**השפעה:**
כל הגדרות הודעות בקשות/תגובות בכל בסיס הקוד משתמשות בסכימות של Pulsar
זה כולל שירותים עבור: config, flow, llm, prompt, query, storage, agent, collection, diagnosis, library, lookup, nlp_query, objects_query, retrieval, structured_query
הגדרות סכימות מיובאות ומשמשות באופן נרחב בכל המעבדים והשירותים

## סיכום

### תלויות של Pulsar לפי קטגוריה

1. **יצירת מופע לקוח:**
   ישיר: `gateway/service.py`
   מופשט: `async_processor.py` → `pubsub.py` (PulsarClient)

2. **העברת הודעות:**
   צרכן: `consumer.py`, `consumer_spec.py`
   מפיק: `producer.py`, `producer_spec.py`
   מפרסם: `publisher.py`
   מנוי: `subscriber.py`, `subscriber_spec.py`

3. **מערכת סכימות:**
   סוגים בסיסיים: `schema/core/primitives.py`
   כל סכימות השירות: `schema/services/*.py`
   שמות נושאים: `schema/core/topic.py`

4. **מושגים ספציפיים ל-Pulsar הנדרשים:**
   העברת הודעות מבוססת נושאים
   מערכת סכימות (Record, סוגי שדות)
   מנויים משותפים
   אישור הודעות (חיובי/שלילי)
   מיקום צרכן (מוקדם/מאוחר)
   מאפייני הודעות
   מיקומים התחלתיים וסוגי צרכנים
   תמיכה בפיצול
   נושאים קבועים לעומת לא קבועים

### אתגרי שינוי מבנה

החדשות הטובות: שכבת ההפשטה (צרכן, מפיק, מפרסם, מנוי) מספקת אריזה נקייה של רוב האינטראקציות של Pulsar.

האתגרים:
1. **הנחת סכימות נרחבת:** כל הגדרת הודעה משתמשת ב-`pulsar.schema.Record` ובסוגי Pulsar
2. **אנונימים ספציפיים ל-Pulsar:** `InitialPosition`, `ConsumerType`
3. **חריגות של Pulsar:** `_pulsar.Timeout`, `_pulsar.Interrupted`, `_pulsar.InvalidConfiguration`, `_pulsar.AlreadyClosed`
4. **חתימות שיטות:** `acknowledge()`, `negative_acknowledge()`, `subscribe()`, `create_producer()`, וכו'.
5. **פורמט URI של נושא:** מבנה `kind://tenant/namespace/topic` של Pulsar

### שלבים הבאים

כדי להפוך את התשתית של pub/sub לכזו שניתן להגדיר, עלינו:

1. ליצור ממשק הפשטה עבור מערכת הלקוח/סכימות
2. להפשיט אנונימים ספציפיים ל-Pulsar וחריגות
3. ליצור עטיפות סכימות או הגדרות סכימות חלופיות
4. ליישם את הממשק הן עבור Pulsar והן עבור מערכות חלופיות (Kafka, RabbitMQ, Redis Streams, וכו')
5. לעדכן את `pubsub.py` כך שניתן יהיה להגדיר אותו ולתמוך במספר מערכות אחוריות
6. לספק נתיב מעבר לפריסות קיימות

## טיוטת גישה 1: תבנית מתאם עם שכבת תרגום סכימות

### הערה


### אסטרטגיה: הפרעה מינימלית באמצעות מתאמים

**1. שמירה על סכימות Pulsar כייצוג הפנימי**
אין לשכתב את כל הגדרות הסכימות.
הסכימות נשארות `pulsar.schema.Record` באופן פנימי.
השתמשו במתאמים כדי לתרגם בגבול בין הקוד שלנו לבין ה-backend של ה-pub/sub.

**2. יצירת שכבת הפשטה עבור pub/sub:**

```
┌─────────────────────────────────────┐
│   Existing Code (unchanged)         │
│   - Uses Pulsar schemas internally  │
│   - Consumer/Producer/Publisher     │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│   PubSubFactory (configurable)      │
│   - Creates backend-specific client │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
┌───────▼─────┐  ┌────▼─────────┐
│ PulsarAdapter│  │ KafkaAdapter │  etc...
│ (passthrough)│  │ (translates) │
└──────────────┘  └──────────────┘
```

**3. הגדרת ממשקים מופשטים:**
`PubSubClient` - חיבור לקוח
`PubSubProducer` - שליחת הודעות
`PubSubConsumer` - קבלת הודעות
`SchemaAdapter` - המרת סכימות Pulsar ל-JSON או פורמטים ספציפיים ל-backend

**4. פרטי יישום:**

עבור **מתאם Pulsar**: כמעט העברה ישירה, המרה מינימלית

עבור **backends אחרים** (Kafka, RabbitMQ, וכו'):
סריאליזציה של אובייקטי Pulsar Record ל-JSON/bytes
מיפוי מושגים כמו:
  `InitialPosition.Earliest/Latest` → auto.offset.reset של Kafka
  `acknowledge()` → commit של Kafka
  `negative_acknowledge()` → תבנית Re-queue או DLQ
  URIs של נושאים → שמות נושאים ספציפיים ל-backend

### ניתוח

**יתרונות:**
✅ שינויים מינימליים בקוד של שירותים קיימים
✅ הסכימות נשארות כפי שהן (ללא כתיבה מחדש מסיבית)
✅ מסלול מעבר הדרגתי
✅ משתמשי Pulsar לא רואים הבדל
✅ backends חדשים מתווספים באמצעות מתאמים

**חסרונות:**
⚠️ עדיין כולל תלות ב-Pulsar (לצרכי הגדרות סכימה)
⚠️ חוסר התאמה מסוים בהמרת מושגים

### שיקול חלופי

ליצור **מערכת סכימות TrustGraph** שאינה תלויה ב-pub/sub ספציפי (תוך שימוש ב-dataclasses או Pydantic), ולאחר מכן ליצור סכימות Pulsar/Kafka/וכו מתוך זה. זה דורש כתיבה מחדש של כל קובץ סכימה ועלול לגרום לשינויים משמעותיים.

### המלצה עבור טיוטה 1

להתחיל עם **גישת המתאם** מכיוון ש:
1. זה פרגמטי - עובד עם קוד קיים
2. מוכיח את הקונספט עם סיכון מינימלי
3. ניתן להתפתח למערכת סכימה מקומית יותר בעתיד אם יש צורך
4. מונחה תצורה: משתנה סביבה אחד משנה את ה-backends

## גישה טיוטה 2: מערכת סכימות עצמאית מ-backend באמצעות Dataclasses

### מושג מרכזי

להשתמש ב-**dataclasses** של Python כפורמט הגדרת סכימה ניטרלי. כל backend של pub/sub מספק את הסריאליזציה/דה-סריאליזציה שלו עבור dataclasses, מה שמבטל את הצורך לשמור על סכימות Pulsar בקוד הבסיס.

### פולימורפיזם של סכימה ברמת המפעל

במקום להמיר סכימות Pulsar, **כל backend מספק את הטיפול שלו בסכימות** שעובד עם dataclasses סטנדרטיים של Python.

### זרימת פרסום

```python
# 1. Get the configured backend from factory
pubsub = get_pubsub()  # Returns PulsarBackend, MQTTBackend, etc.

# 2. Get schema class from the backend
# (Can be imported directly - backend-agnostic)
from trustgraph.schema.services.llm import TextCompletionRequest

# 3. Create a producer/publisher for a specific topic
producer = pubsub.create_producer(
    topic="text-completion-requests",
    schema=TextCompletionRequest  # Tells backend what schema to use
)

# 4. Create message instances (same API regardless of backend)
request = TextCompletionRequest(
    system="You are helpful",
    prompt="Hello world",
    streaming=False
)

# 5. Send the message
producer.send(request)  # Backend serializes appropriately
```

### זרימת לקוח

```python
# 1. Get the configured backend
pubsub = get_pubsub()

# 2. Create a consumer
consumer = pubsub.subscribe(
    topic="text-completion-requests",
    schema=TextCompletionRequest  # Tells backend how to deserialize
)

# 3. Receive and deserialize
msg = consumer.receive()
request = msg.value()  # Returns TextCompletionRequest dataclass instance

# 4. Use the data (type-safe access)
print(request.system)   # "You are helpful"
print(request.prompt)   # "Hello world"
print(request.streaming)  # False
```

### מה קורה מאחורי הקלעים

**עבור ה-backend של Pulsar:**
`create_producer()` → יוצר יצרן Pulsar עם סכימה JSON או רשומה שנוצרה באופן דינמי
`send(request)` → ממיר את מחלקת הנתונים לפורמט JSON/Pulsar, שולח ל-Pulsar
`receive()` → מקבל הודעת Pulsar, ממיר חזרה למחלקת נתונים

**עבור ה-backend של MQTT:**
`create_producer()` → מתחבר ל-MQTT broker, אין צורך ברישום סכימה
`send(request)` → ממיר מחלקת נתונים ל-JSON, מפרסם לנושא MQTT
`receive()` → נרשם לנושא MQTT, ממיר JSON למחלקת נתונים

**עבור ה-backend של Kafka:**
`create_producer()` → יוצר יצרן Kafka, רושם סכימת Avro במידת הצורך
`send(request)` → ממיר מחלקת נתונים לפורמט Avro, שולח ל-Kafka
`receive()` → מקבל הודעת Kafka, ממיר Avro חזרה למחלקת נתונים

### נקודות עיצוב מרכזיות

1. **יצירת אובייקט סכימה**: מופע מחלקת הנתונים (`TextCompletionRequest(...)`) זהה ללא קשר ל-backend
2. **ה-backend מטפל בקידוד**: כל backend יודע כיצד לתרגם את מחלקת הנתונים לפורמט הנתונים
3. **הגדרת סכימה ביצירה**: בעת יצירת יצרן/צרכן, מציינים את סוג הסכימה
4. **שמירה על בטיחות טיפוסים**: מקבלים בחזרה אובייקט `TextCompletionRequest` תקין, ולא מילון
5. **ללא חשיפה ל-backend**: קוד האפליקציה לעולם לא מייבא ספריות ספציפיות ל-backend

### דוגמה לטרנספורמציה

**נוכחי (ספציפי ל-Pulsar):**
```python
# schema/services/llm.py
from pulsar.schema import Record, String, Boolean, Integer

class TextCompletionRequest(Record):
    system = String()
    prompt = String()
    streaming = Boolean()
```

**חדש (בלתי תלוי בטכנולוגיית השרת):**
```python
# schema/services/llm.py
from dataclasses import dataclass

@dataclass
class TextCompletionRequest:
    system: str
    prompt: str
    streaming: bool = False
```

### אינטגרציה עם השרת האחורי

כל שרת אחורי מטפל בסריאליזציה/דה-סריאליזציה של מחלקות נתונים:

**שרת אחורי של Pulsar:**
יצירת מחלקות `pulsar.schema.Record` באופן דינמי ממחלקות נתונים
או סריאליזציה של מחלקות נתונים ל-JSON ושימוש בסכימה של JSON של Pulsar
שומר על תאימות לפריסות Pulsar קיימות

**שרת אחורי של MQTT/Redis:**
סריאליזציה ישירה של מופעים של מחלקות נתונים ל-JSON
שימוש ב-`dataclasses.asdict()` / `from_dict()`
קל משקל, לא נדרש רישום סכימות

**שרת אחורי של Kafka:**
יצירת סכימות Avro מהגדרות של מחלקות נתונים
שימוש ברישום סכימות של Confluent
סריאליזציה בטוחה עם תמיכה באבולוציה של סכימות

### ארכיטקטורה

```
┌─────────────────────────────────────┐
│   Application Code                  │
│   - Uses dataclass schemas          │
│   - Backend-agnostic                │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│   PubSubFactory (configurable)      │
│   - get_pubsub() returns backend    │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
┌───────▼─────────┐  ┌────▼──────────────┐
│ PulsarBackend   │  │ MQTTBackend       │
│ - JSON schema   │  │ - JSON serialize  │
│ - or dynamic    │  │ - Simple queues   │
│   Record gen    │  │                   │
└─────────────────┘  └───────────────────┘
```

### פרטי יישום

**1. הגדרות סכימה:** מחלקות נתונים פשוטות עם רמזי סוג
   `str`, `int`, `bool`, `float` עבור ערכים בסיסיים
   `list[T]` עבור מערכים
   `dict[str, T]` עבור מפות
   מחלקות נתונים מקוננות עבור סוגים מורכבים

**2. כל ממשק מספק:**
   ממיר: `dataclass → bytes/wire format`
   ממיר הפוך: `bytes/wire format → dataclass`
   רישום סכימה (אם נדרש, כמו Pulsar/Kafka)

**3. הפשטה של צרכן/משדר:**
   כבר קיים (consumer.py, producer.py)
   עדכון לשימוש בשימוש בשידור של הממשק
   הסרת יבוא ישיר של Pulsar

**4. התאמות סוג:**
   Pulsar `String()` → Python `str`
   Pulsar `Integer()` → Python `int`
   Pulsar `Boolean()` → Python `bool`
   Pulsar `Array(T)` → Python `list[T]`
   Pulsar `Map(K, V)` → Python `dict[K, V]`
   Pulsar `Double()` → Python `float`
   Pulsar `Bytes()` → Python `bytes`

### נתיב מעבר

1. **צור גרסאות של מחלקות נתונים** עבור כל הסכימות ב-`trustgraph/schema/`
2. **עדכן מחלקות ממשק** (צרכן, משדר, מפרסם, מנוי) לשימוש בשידור שמסופק על ידי הממשק
3. **יישם PulsarBackend** עם סכימה ב-JSON או יצירת רשומות דינמית
4. **בדוק עם Pulsar** כדי להבטיח תאימות לאחור עם פריסות קיימות
5. **הוסף ממשקים חדשים** (MQTT, Kafka, Redis, וכו') לפי הצורך
6. **הסר יבוא של Pulsar** מקבצי סכימה

### יתרונות

✅ **ללא תלות ב-pub/sub** בהגדרות סכימה
✅ **Python סטנדרטי** - קל להבנה, בדיקת סוגים, תיעוד
✅ **כלים מודרניים** - עובד עם mypy, השלמה אוטומטית של IDE, כלי ניתוח
✅ **מותאם לממשק** - כל ממשק משתמש בשידור מקומי
✅ **ללא תקורה של תרגום** - שידור ישיר, ללא מתאמים
✅ **בטיחות סוג** - אובייקטים אמיתיים עם סוגים מתאימים
✅ **אימות קל** - ניתן להשתמש ב-Pydantic אם נדרש

### אתגרים ופתרונות

**אתגר:** ל-Pulsar יש `Record` עם אימות שדה בזמן ריצה
**פתרון:** השתמש במחלקות נתונים של Pydantic לאימות אם נדרש, או בתכונות של מחלקת נתונים של Python 3.10+ עם `__post_init__`

**אתגר:** תכונות ספציפיות של Pulsar (כמו סוג `Bytes`)
**פתרון:** התאם לסוג `bytes` במחלקת נתונים, הממשק מטפל בקידוד המתאים

**אתגר:** שמות נושא (`persistent://tenant/namespace/topic`)
**פתרון:** הפשט שמות נושא בהגדרות סכימה, הממשק ממיר לפורמט המתאים

**אתגר:** אבולוציה וגרסאות של סכימה
**פתרון:** כל ממשק מטפל בכך בהתאם ליכולות שלו (גרסאות סכימה של Pulsar, רישום סכימה של Kafka, וכו')

**אתגר:** סוגים מורכבים מקוננים
**פתרון:** השתמש במחלקות נתונים מקוננות, הממשקים מבצעים שידור/פענוח רקורסיבי

### החלטות עיצוב

1. **מחלקות נתונים פשוטות או Pydantic?**
   ✅ **החלטה: השתמש במחלקות נתונים של Python פשוטות**
   פשוט יותר, ללא תלויות נוספות
   אימות אינו נדרש בפועל
   קל יותר להבנה ולתחזוקה

2. **אבולוציה של סכימה:**
   ✅ **החלטה: לא נדרש מנגנון גרסאות**
   הסכימות יציבות וקיימות לאורך זמן
   עדכונים בדרך כלל מוסיפים שדות חדשים (תואמים לאחור)
   ממשקים מטפלים באבולוציה של סכימה בהתאם ליכולות שלהם

3. **תאימות לאחור:**
   ✅ **החלטה: שינוי גרסה עיקרית, תאימות לאחור אינה נדרשת**
   יהיה שינוי משמעותי עם הוראות מעבר
   ניתוק נקי מאפשר עיצוב טוב יותר
   מדריך מעבר יסופק עבור פריסות קיימות

4. **סוגים מקוננים ומבנים מורכבים:**
   ✅ **החלטה: השתמש במחלקות נתונים מקוננות באופן טבעי**
   מחלקות נתונים של Python מטפלות בקינון בצורה מושלמת
   `list[T]` עבור מערכים, `dict[K, V]` עבור מפות
   ממשקים מבצעים שידור/פענוח רקורסיבי
   דוגמה:
     ```python
     @dataclass
     class Value:
         value: str
         is_uri: bool

     @dataclass
     class Triple:
         s: Value              # Nested dataclass
         p: Value
         o: Value

     @dataclass
     class GraphQuery:
         triples: list[Triple]  # Array of nested dataclasses
         metadata: dict[str, str]
     ```

5. **ערכים ברירת מחדל ושדות אופציונליים:**
   ✅ **החלטה: שילוב של שדות חובה, ערכי ברירת מחדל ושדות אופציונליים**
   שדות חובה: ללא ערך ברירת מחדל
   שדות עם ערכי ברירת מחדל: תמיד נוכחים, בעלי ערך ברירת מחדל הגיוני
   שדות אופציונליים לחלוטין: `T | None = None`, מושמטים מסריאליזציה כאשר `None`
   דוגמה:
     ```python
     @dataclass
     class TextCompletionRequest:
         system: str              # Required, no default
         prompt: str              # Required, no default
         streaming: bool = False  # Optional with default value
         metadata: dict | None = None  # Truly optional, can be absent
     ```

   **סמנטיקה חשובה של סריאליזציה:**

   כאשר `metadata = None`:
   ```json
   {
       "system": "...",
       "prompt": "...",
       "streaming": false
       // metadata field NOT PRESENT
   }
   ```

   כאשר `metadata = {}` (ריק במפורש):
   ```json
   {
       "system": "...",
       "prompt": "...",
       "streaming": false,
       "metadata": {}  // Field PRESENT but empty
   }
   ```

   **ההבחנה העיקרית:**
   `None` → שדה שאינו קיים ב-JSON (לא מיוצא)
   ערך ריק (`{}`, `[]`, `""`) → שדה קיים עם ערך ריק
   זה חשוב מבחינה סמנטית: "לא סופק" לעומת "ריק באופן מפורש"
   מערכות הקידוד חייבות לדלג על שדות `None`, ולא לקודד אותם כ-`null`

## טיוטה 3 של הגישה: פרטי יישום

### פורמט שם תור גנרי

החליפו שמות תורים ספציפיים לכל מערכת קידוד בפורמט גנרי שמערכות הקידוד יכולות למפות בהתאם.

**פורמט:** `{qos}/{tenant}/{namespace}/{queue-name}`

כאשר:
`qos`: רמת שירות (Quality of Service)
  `q0` = מאמץ מינימלי (שליחה ללא אישור)
  `q1` = לפחות פעם אחת (דורש אישור)
  `q2` = בדיוק פעם אחת (אישור בשני שלבים)
`tenant`: קיבוץ לוגי עבור ריבוי דיירים
`namespace`: תת-קיבוץ בתוך דייר
`queue-name`: שם התור/נושא בפועל

**דוגמאות:**
```
q1/tg/flow/text-completion-requests
q2/tg/config/config-push
q0/tg/metrics/stats
```

### מיפוי נושאים בצד השרת

כל צד שרת ממפה את הפורמט הכללי לפורמט הייחודי שלו:

**צד שרת Pulsar:**
```python
def map_topic(self, generic_topic: str) -> str:
    # Parse: q1/tg/flow/text-completion-requests
    qos, tenant, namespace, queue = generic_topic.split('/', 3)

    # Map QoS to persistence
    persistence = 'persistent' if qos in ['q1', 'q2'] else 'non-persistent'

    # Return Pulsar URI: persistent://tg/flow/text-completion-requests
    return f"{persistence}://{tenant}/{namespace}/{queue}"
```

**שרת MQTT:**
```python
def map_topic(self, generic_topic: str) -> tuple[str, int]:
    # Parse: q1/tg/flow/text-completion-requests
    qos, tenant, namespace, queue = generic_topic.split('/', 3)

    # Map QoS level
    qos_level = {'q0': 0, 'q1': 1, 'q2': 2}[qos]

    # Build MQTT topic including tenant/namespace for proper namespacing
    mqtt_topic = f"{tenant}/{namespace}/{queue}"

    return mqtt_topic, qos_level
```

### פונקציית עזר מעודכנת לנושא

```python
# schema/core/topic.py
def topic(queue_name, qos='q1', tenant='tg', namespace='flow'):
    """
    Create a generic topic identifier that can be mapped by backends.

    Args:
        queue_name: The queue/topic name
        qos: Quality of service
             - 'q0' = best-effort (no ack)
             - 'q1' = at-least-once (ack required)
             - 'q2' = exactly-once (two-phase ack)
        tenant: Tenant identifier for multi-tenancy
        namespace: Namespace within tenant

    Returns:
        Generic topic string: qos/tenant/namespace/queue_name

    Examples:
        topic('my-queue')  # q1/tg/flow/my-queue
        topic('config', qos='q2', namespace='config')  # q2/tg/config/config
    """
    return f"{qos}/{tenant}/{namespace}/{queue_name}"
```

### הגדרות ואתחול

**ארגומנטים של שורת הפקודה + משתני סביבה:**

```python
# In base/async_processor.py - add_args() method
@staticmethod
def add_args(parser):
    # Pub/sub backend selection
    parser.add_argument(
        '--pubsub-backend',
        default=os.getenv('PUBSUB_BACKEND', 'pulsar'),
        choices=['pulsar', 'mqtt'],
        help='Pub/sub backend (default: pulsar, env: PUBSUB_BACKEND)'
    )

    # Pulsar-specific configuration
    parser.add_argument(
        '--pulsar-host',
        default=os.getenv('PULSAR_HOST', 'pulsar://localhost:6650'),
        help='Pulsar host (default: pulsar://localhost:6650, env: PULSAR_HOST)'
    )

    parser.add_argument(
        '--pulsar-api-key',
        default=os.getenv('PULSAR_API_KEY', None),
        help='Pulsar API key (env: PULSAR_API_KEY)'
    )

    parser.add_argument(
        '--pulsar-listener',
        default=os.getenv('PULSAR_LISTENER', None),
        help='Pulsar listener name (env: PULSAR_LISTENER)'
    )

    # MQTT-specific configuration
    parser.add_argument(
        '--mqtt-host',
        default=os.getenv('MQTT_HOST', 'localhost'),
        help='MQTT broker host (default: localhost, env: MQTT_HOST)'
    )

    parser.add_argument(
        '--mqtt-port',
        type=int,
        default=int(os.getenv('MQTT_PORT', '1883')),
        help='MQTT broker port (default: 1883, env: MQTT_PORT)'
    )

    parser.add_argument(
        '--mqtt-username',
        default=os.getenv('MQTT_USERNAME', None),
        help='MQTT username (env: MQTT_USERNAME)'
    )

    parser.add_argument(
        '--mqtt-password',
        default=os.getenv('MQTT_PASSWORD', None),
        help='MQTT password (env: MQTT_PASSWORD)'
    )
```

**פונקציית יצירה:**

```python
# In base/pubsub.py or base/pubsub_factory.py
def get_pubsub(**config) -> PubSubBackend:
    """
    Create and return a pub/sub backend based on configuration.

    Args:
        config: Configuration dict from command-line args
                Must include 'pubsub_backend' key

    Returns:
        Backend instance (PulsarBackend, MQTTBackend, etc.)
    """
    backend_type = config.get('pubsub_backend', 'pulsar')

    if backend_type == 'pulsar':
        return PulsarBackend(
            host=config.get('pulsar_host'),
            api_key=config.get('pulsar_api_key'),
            listener=config.get('pulsar_listener'),
        )
    elif backend_type == 'mqtt':
        return MQTTBackend(
            host=config.get('mqtt_host'),
            port=config.get('mqtt_port'),
            username=config.get('mqtt_username'),
            password=config.get('mqtt_password'),
        )
    else:
        raise ValueError(f"Unknown pub/sub backend: {backend_type}")
```

**שימוש ב-AsyncProcessor:**

```python
# In async_processor.py
class AsyncProcessor:
    def __init__(self, **params):
        self.id = params.get("id")

        # Create backend from config (replaces PulsarClient)
        self.pubsub = get_pubsub(**params)

        # Rest of initialization...
```

### ממשק צד שרת

```python
class PubSubBackend(Protocol):
    """Protocol defining the interface all pub/sub backends must implement."""

    def create_producer(self, topic: str, schema: type, **options) -> BackendProducer:
        """
        Create a producer for a topic.

        Args:
            topic: Generic topic format (qos/tenant/namespace/queue)
            schema: Dataclass type for messages
            options: Backend-specific options (e.g., chunking_enabled)

        Returns:
            Backend-specific producer instance
        """
        ...

    def create_consumer(
        self,
        topic: str,
        subscription: str,
        schema: type,
        initial_position: str = 'latest',
        consumer_type: str = 'shared',
        **options
    ) -> BackendConsumer:
        """
        Create a consumer for a topic.

        Args:
            topic: Generic topic format (qos/tenant/namespace/queue)
            subscription: Subscription/consumer group name
            schema: Dataclass type for messages
            initial_position: 'earliest' or 'latest' (MQTT may ignore)
            consumer_type: 'shared', 'exclusive', 'failover' (MQTT may ignore)
            options: Backend-specific options

        Returns:
            Backend-specific consumer instance
        """
        ...

    def close(self) -> None:
        """Close the backend connection."""
        ...
```

```python
class BackendProducer(Protocol):
    """Protocol for backend-specific producer."""

    def send(self, message: Any, properties: dict = {}) -> None:
        """Send a message (dataclass instance) with optional properties."""
        ...

    def flush(self) -> None:
        """Flush any buffered messages."""
        ...

    def close(self) -> None:
        """Close the producer."""
        ...
```

```python
class BackendConsumer(Protocol):
    """Protocol for backend-specific consumer."""

    def receive(self, timeout_millis: int = 2000) -> Message:
        """
        Receive a message from the topic.

        Raises:
            TimeoutError: If no message received within timeout
        """
        ...

    def acknowledge(self, message: Message) -> None:
        """Acknowledge successful processing of a message."""
        ...

    def negative_acknowledge(self, message: Message) -> None:
        """Negative acknowledge - triggers redelivery."""
        ...

    def unsubscribe(self) -> None:
        """Unsubscribe from the topic."""
        ...

    def close(self) -> None:
        """Close the consumer."""
        ...
```

```python
class Message(Protocol):
    """Protocol for a received message."""

    def value(self) -> Any:
        """Get the deserialized message (dataclass instance)."""
        ...

    def properties(self) -> dict:
        """Get message properties/metadata."""
        ...
```

### שינוי מבנה מחלקות קיימות

המחלקות הקיימות `Consumer`, `Producer`, `Publisher`, `Subscriber` נשארות ברובן ללא שינוי:

**אחריות נוכחית (לשמור):**
מודל תהליכים אסינכרוניים וקבוצות משימות
לוגיקת חיבור מחדש וטיפול בכישלונות
איסוף מדדים
הגבלת קצב
ניהול תחרות

**שינויים נדרשים:**
הסרת יבוא ישיר של Pulsar (`pulsar.schema`, `pulsar.InitialPosition`, וכו')
קבלת `BackendProducer`/`BackendConsumer` במקום לקוח Pulsar
העברת פעולות פרסום/מנוי בפועל לאינסטנסים אחוריים
התאמת מושגים כלליים לפעולות אחוריות

**דוגמה לשינוי מבנה:**

```python
# OLD - consumer.py
class Consumer:
    def __init__(self, client, topic, subscriber, schema, ...):
        self.client = client  # Direct Pulsar client
        # ...

    async def consumer_run(self):
        # Uses pulsar.InitialPosition, pulsar.ConsumerType
        self.consumer = self.client.subscribe(
            topic=self.topic,
            schema=JsonSchema(self.schema),
            initial_position=pulsar.InitialPosition.Earliest,
            consumer_type=pulsar.ConsumerType.Shared,
        )

# NEW - consumer.py
class Consumer:
    def __init__(self, backend_consumer, schema, ...):
        self.backend_consumer = backend_consumer  # Backend-specific consumer
        self.schema = schema
        # ...

    async def consumer_run(self):
        # Backend consumer already created with right settings
        # Just use it directly
        while self.running:
            msg = await asyncio.to_thread(
                self.backend_consumer.receive,
                timeout_millis=2000
            )
            await self.handle_message(msg)
```

### התנהגויות ספציפיות לצד האחורי (Backend)

**צד אחורי Pulsar:**
ממפה `q0` → `non-persistent://`, `q1`/`q2` → `persistent://`
תומך בכל סוגי הצרכנים (משותף, בלעדי, גיבוי)
תומך בעמדה התחלתית (הכי מוקדם/הכי מאוחר)
אישור הודעות מקורי
תמיכה ברישום סכימות

**צד אחורי MQTT:**
ממפה `q0`/`q1`/`q2` → רמות QoS של MQTT 0/1/2
כולל שוכר/מרחב שם בנתיב הנושא לצורך הפרדה
מייצר באופן אוטומטי מזהי לקוח משמות מנויים
מתעלם מעמדה התחלתית (אין היסטוריית הודעות ב-MQTT בסיסי)
מתעלם מסוג צרכן (MQTT משתמש במזהי לקוח, לא בקבוצות צרכנים)
מודל פרסום/מנוי פשוט

### סיכום החלטות עיצוב

1. ✅ **שמות תורים גנריים**: פורמט `qos/tenant/namespace/queue-name`
2. ✅ **רמת QoS במזהה תור**: נקבעת על ידי הגדרת התור, ולא על ידי תצורה
3. ✅ **חיבור מחדש**: מטופל על ידי מחלקות צרכן/מפיק, ולא על ידי הצד האחורי
4. ✅ **נושאים של MQTT**: כוללים שוכר/מרחב שם לצורך הפרדה תקינה
5. ✅ **היסטוריית הודעות**: MQTT מתעלם מהפרמטר `initial_position` (שיפור עתידי)
6. ✅ **מזהי לקוח**: צד אחורי MQTT מייצר באופן אוטומטי משם מנוי

### שיפורים עתידיים

**היסטוריית הודעות של MQTT:**
ניתן להוסיף שכבת שמירה אופציונלית (לדוגמה, הודעות שמורות, אחסון חיצוני)
יאפשר תמיכה ב-`initial_position='earliest'`
לא נדרש ליישום ראשוני

