# מפרט טכני: תמיכה בריבוי דיירים

## סקירה כללית

אפשר ריבוי פריסות דיירים על ידי תיקון חוסר התאמות בשמות הפרמטרים שמונע התאמה אישית של תורים, והוספת פרמטריזציה של מרחבי מפתחות Cassandra.

## הקשר ארכיטקטוני

### פתרון תורים מבוסס זרימה

מערכת TrustGraph משתמשת בארכיטקטורה **מבוססת זרימה** לפתרון דינמי של תורים, התומכת באופן מובנה בריבוי דיירים:

**הגדרות זרימה** מאוחסנות ב-Cassandra ומציינות שמות תורים באמצעות הגדרות ממשק.
**שמות התורים משתמשים בתבניות** עם משתנים `{id}` שמוחלפים במזהי מופעי זרימה.
**השירותים פותרים באופן דינמי את התורים** על ידי חיפוש תצורות זרימה בזמן בקשה.
**לכל דייר יכולות להיות זרימות ייחודיות** עם שמות תורים שונים, המספקות בידוד.

דוגמה להגדרת ממשק זרימה:
```json
{
  "interfaces": {
    "triples-store": "persistent://tg/flow/triples-store:{id}",
    "graph-embeddings-store": "persistent://tg/flow/graph-embeddings-store:{id}"
  }
}
```

כאשר שוכר א מתחיל זרימה `tenant-a-prod` ושוכר ב מתחיל זרימה `tenant-b-prod`, הם באופן אוטומטי מקבלים תורים מבודדים:
`persistent://tg/flow/triples-store:tenant-a-prod`
`persistent://tg/flow/triples-store:tenant-b-prod`

**שירותים המעוצבים כראוי עבור ריבוי שוכרים:**
✅ **ניהול ידע (ליבה)** - פותר באופן דינמי תורים מהגדרת הזרימה המועברת בבקשות

**שירותים הדורשים תיקונים:**
🔴 **שירות תצורה** - חוסר התאמה בשם הפרמטר מונע התאמה אישית של תורים
🔴 **שירות ספרית** - נושאים של ניהול אחסון מקודדים (נדון בהמשך)
🔴 **כל השירותים** - לא ניתן להתאים אישית את מרחב המפתחות של Cassandra

## הצהרת בעיה

### בעיה #1: חוסר התאמה בשם פרמטר ב-AsyncProcessor
**הגדרות CLI:** `--config-queue` (שם לא ברור)
**Argparse ממיר ל:** `config_queue` (במילון הפרמטרים)
**הקוד מחפש:** `config_push_queue`
**תוצאה:** הפרמטר מתעלם, ברירת מחדל ל-`persistent://tg/config/config`
**השפעה:** משפיע על כל 32+ שירותים היורשים מ-AsyncProcessor
**חוסם:** פריסות מרובות שוכרים לא יכולות להשתמש בתורי תצורה ספציפיים לשוכר
**פתרון:** לשנות את שם הפרמטר ב-CLI ל-`--config-push-queue` לצורך בהירות (שינוי שבירה מקובל מכיוון שהתכונה שבורה כרגע)

### בעיה #2: חוסר התאמה בשם פרמטר בשירות התצורה
**הגדרות CLI:** `--push-queue` (שם מעורפל)
**Argparse ממיר ל:** `push_queue` (במילון הפרמטרים)
**הקוד מחפש:** `config_push_queue`
**תוצאה:** הפרמטר מתעלם
**השפעה:** שירות התצורה לא יכול להשתמש בתור דחיפה מותאם אישית
**פתרון:** לשנות את שם הפרמטר ב-CLI ל-`--config-push-queue` לצורך עקביות ובהירות (שינוי שבירה מקובל)

### בעיה #3: מרחב מפתחות Cassandra מקודד
**נוכחי:** מרחב המפתחות מקודד כ-`"config"`, `"knowledge"`, `"librarian"` בשירותים שונים
**תוצאה:** לא ניתן להתאים אישית את מרחב המפתחות עבור פריסות מרובות שוכרים
**השפעה:** שירותי תצורה, ליבה וספריה
**חוסם:** מספר שוכרים לא יכולים להשתמש במרחבי מפתחות Cassandra נפרדים

### בעיה #4: ארכיטקטורת ניהול אוספים ✅ הושלם
**קודם:** אוספים שמורים במרחב המפתחות של Cassandra של הספריה באמצעות טבלת אוספים נפרדת
**קודם:** הספריה השתמשה ב-4 נושאים מקודדים לניהול אחסון לתאם יצירה/מחיקה של אוספים:
  `vector_storage_management_topic`
  `object_storage_management_topic`
  `triples_storage_management_topic`
  `storage_management_response_topic`
**בעיות (טופלו):**
  נושאים מקודדים לא ניתן להתאים אישית עבור פריסות מרובות שוכרים
  תיאום אסינכרוני מורכב בין הספריה לבין 4+ שירותי אחסון
  טבלה נפרדת ותשתית ניהול
  תורי בקשה/תגובה לא מתמידים עבור פעולות קריטיות
**פתרון מיושם:** העברנו אוספים לשירות האחסון של התצורה, השתמשנו בדחיפה של תצורה להפצה
**סטטוס:** כל בסיסי האחסון עברו לדפוס `CollectionConfigHandler`

## פתרון

מפרט זה מתייחס לבעיות #1, #2, #3 ו-#4.

### חלק 1: תיקון חוסר התאמה בשמות פרמטרים

#### שינוי 1: מחלקת בסיס AsyncProcessor - שינוי שם פרמטר CLI
**קובץ:** `trustgraph-base/trustgraph/base/async_processor.py`
**שורה:** 260-264

**נוכחי:**
```python
parser.add_argument(
    '--config-queue',
    default=default_config_queue,
    help=f'Config push queue {default_config_queue}',
)
```

**קבוע:**
```python
parser.add_argument(
    '--config-push-queue',
    default=default_config_queue,
    help=f'Config push queue (default: {default_config_queue})',
)
```

**הסבר:**
שם ברור וחד יותר
תואם לשם המשתנה הפנימי `config_push_queue`
שינוי משמעותי מקובל מכיוון שהפיצ'ר אינו פעיל כרגע
אין צורך בשינוי קוד בפונקציה params.get() - היא כבר מחפשת את השם הנכון

#### שינוי 2: שירות תצורה - שינוי שם פרמטר שורת הפקודה
**קובץ:** `trustgraph-flow/trustgraph/config/service/service.py`
**שורה:** 276-279

**נוכחי:**
```python
parser.add_argument(
    '--push-queue',
    default=default_config_push_queue,
    help=f'Config push queue (default: {default_config_push_queue})'
)
```

**קבוע:**
```python
parser.add_argument(
    '--config-push-queue',
    default=default_config_push_queue,
    help=f'Config push queue (default: {default_config_push_queue})'
)
```

**הסבר:**
שמות ברורים יותר - "config-push-queue" מפורט יותר מ-"push-queue" בלבד.
תואם לשם המשתנה הפנימי `config_push_queue`.
עקבי עם הפרמטר `--config-push-queue` של AsyncProcessor.
שינוי שעלול לשבור תאימות מקובל מכיוון שהפיצ'ר אינו פונקציונלי כרגע.
אין צורך בשינוי קוד בפונקציה params.get() - היא כבר מחפשת את השם הנכון.

### חלק 2: הוספת פרמטריזציה של Keyspace של Cassandra

#### שינוי 3: הוספת פרמטר Keyspace למודול cassandra_config
**קובץ:** `trustgraph-base/trustgraph/base/cassandra_config.py`

**הוספת ארגומנט שורת פקודה** (בפונקציה `add_cassandra_args()`):
```python
parser.add_argument(
    '--cassandra-keyspace',
    default=None,
    help='Cassandra keyspace (default: service-specific)'
)
```

**הוספת תמיכה במשתני סביבה** (בפונקציה `resolve_cassandra_config()`):
```python
keyspace = params.get(
    "cassandra_keyspace",
    os.environ.get("CASSANDRA_KEYSPACE")
)
```

**עדכון ערך ההחזרה** של `resolve_cassandra_config()`:
כרגע מחזיר: `(hosts, username, password)`
לשנות כך שיחזיר: `(hosts, username, password, keyspace)`

**הצדקה:**
עקבי עם תבנית התצורה הקיימת של Cassandra
זמין לכל השירותים דרך `add_cassandra_args()`
תומך בתצורה הן דרך שורת הפקודה והן דרך משתני סביבה

#### שינוי 4: שירות תצורה - שימוש במפתחות מרחב (Keyspace) מוגדרים
**קובץ:** `trustgraph-flow/trustgraph/config/service/service.py`

**שורה 30** - הסרת שם מרחב (Keyspace) מקודד:
```python
# DELETE THIS LINE:
keyspace = "config"
```

**שורות 69-73** - עדכון פתרון תצורת Cassandra:

**נוכחי:**
```python
cassandra_host, cassandra_username, cassandra_password = \
    resolve_cassandra_config(params)
```

**קבוע:**
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="config")
```

**הסבר:**
שומר על תאימות לאחור עם "config" כברירת מחדל.
מאפשר ביטול באמצעות `--cassandra-keyspace` או `CASSANDRA_KEYSPACE`.

#### שינוי 5: שירות ליבה/ידע - שימוש במרחבי מפתחות מוגדרים
**קובץ:** `trustgraph-flow/trustgraph/cores/service.py`

**שורה 37** - הסרת מרחב מפתחות מקודד:
```python
# DELETE THIS LINE:
keyspace = "knowledge"
```

**עדכון פתרון תצורת Cassandra** (במיקום דומה לשירות התצורה):
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="knowledge")
```

#### שינוי 6: שירות סוכן מידע - שימוש במפתחות פרמטריים
**קובץ:** `trustgraph-flow/trustgraph/librarian/service.py`

**שורה 51** - הסרת מרחב מפתחות מקודד:
```python
# DELETE THIS LINE:
keyspace = "librarian"
```

**עדכון פתרון תצורת Cassandra** (במיקום דומה לשירות התצורה):
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="librarian")
```

### חלק 3: העברת ניהול אוספים לשירות התצורה

#### סקירה כללית
העברת אוספים ממערכת ה-Cassandra librarian keyspace לאחסון בשירות התצורה. פעולה זו מבטלת נושאים מובנים לניהול אחסון ומפשטת את הארכיטקטורה על ידי שימוש במנגנון הדחיפה הקיים של התצורה לצורך הפצה.

#### ארכיטקטורה נוכחית
```
API Request → Gateway → Librarian Service
                            ↓
                    CollectionManager
                            ↓
                    Cassandra Collections Table (librarian keyspace)
                            ↓
                    Broadcast to 4 Storage Management Topics (hardcoded)
                            ↓
        Wait for 4+ Storage Service Responses
                            ↓
                    Response to Gateway
```

#### ארכיטקטורה חדשה
```
API Request → Gateway → Librarian Service
                            ↓
                    CollectionManager
                            ↓
                    Config Service API (put/delete/getvalues)
                            ↓
                    Cassandra Config Table (class='collections', key='user:collection')
                            ↓
                    Config Push (to all subscribers on config-push-queue)
                            ↓
        All Storage Services receive config update independently
```

#### שינוי 7: מנהל אוספים - שימוש ב-API של שירות התצורה
**קובץ:** `trustgraph-flow/trustgraph/librarian/collection_manager.py`

**הסרה:**
שימוש ב-`LibraryTableStore` (שורות 33, 40-41)
אתחול מפיקי ניהול אחסון (שורות 86-140)
שיטה `on_storage_response` (שורות 400-430)
מעקב `pending_deletions` (שורות 57, 90-96 ושימוש לאורך כל הקוד)

**הוספה:**
לקוח שירות תצורה עבור קריאות API (תבנית בקשה/תגובה)

**הגדרת לקוח תצורה:**
```python
# In __init__, add config request/response producers/consumers
from trustgraph.schema.services.config import ConfigRequest, ConfigResponse

# Producer for config requests
self.config_request_producer = Producer(
    client=pulsar_client,
    topic=config_request_queue,
    schema=ConfigRequest,
)

# Consumer for config responses (with correlation ID)
self.config_response_consumer = Consumer(
    taskgroup=taskgroup,
    client=pulsar_client,
    flow=None,
    topic=config_response_queue,
    subscriber=f"{id}-config",
    schema=ConfigResponse,
    handler=self.on_config_response,
)

# Tracking for pending config requests
self.pending_config_requests = {}  # request_id -> asyncio.Event
```

**שנה את `list_collections` (שורות 145-180):**
```python
async def list_collections(self, user, tag_filter=None, limit=None):
    """List collections from config service"""
    # Send getvalues request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='getvalues',
        type='collections',
    )

    # Send request and wait for response
    response = await self.send_config_request(request)

    # Parse collections from response
    collections = []
    for key, value_json in response.values.items():
        if ":" in key:
            coll_user, collection = key.split(":", 1)
            if coll_user == user:
                metadata = json.loads(value_json)
                collections.append(CollectionMetadata(**metadata))

    # Apply tag filtering in-memory (as before)
    if tag_filter:
        collections = [c for c in collections if any(tag in c.tags for tag in tag_filter)]

    # Apply limit
    if limit:
        collections = collections[:limit]

    return collections

async def send_config_request(self, request):
    """Send config request and wait for response"""
    event = asyncio.Event()
    self.pending_config_requests[request.id] = event

    await self.config_request_producer.send(request)
    await event.wait()

    return self.pending_config_requests.pop(request.id + "_response")

async def on_config_response(self, message, consumer, flow):
    """Handle config response"""
    response = message.value()
    if response.id in self.pending_config_requests:
        self.pending_config_requests[response.id + "_response"] = response
        self.pending_config_requests[response.id].set()
```

**שנה את `update_collection` (שורות 182-312):**
```python
async def update_collection(self, user, collection, name, description, tags):
    """Update collection via config service"""
    # Create metadata
    metadata = CollectionMetadata(
        user=user,
        collection=collection,
        name=name,
        description=description,
        tags=tags,
    )

    # Send put request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='put',
        type='collections',
        key=f'{user}:{collection}',
        value=json.dumps(metadata.to_dict()),
    )

    response = await self.send_config_request(request)

    if response.error:
        raise RuntimeError(f"Config update failed: {response.error.message}")

    # Config service will trigger config push automatically
    # Storage services will receive update and create collections
```

**שנה את `delete_collection` (שורות 314-398):**
```python
async def delete_collection(self, user, collection):
    """Delete collection via config service"""
    # Send delete request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='delete',
        type='collections',
        key=f'{user}:{collection}',
    )

    response = await self.send_config_request(request)

    if response.error:
        raise RuntimeError(f"Config delete failed: {response.error.message}")

    # Config service will trigger config push automatically
    # Storage services will receive update and delete collections
```

**פורמט מטא-דאטה לאוספים:**
נשמר בטבלת התצורה כ: `class='collections', key='user:collection'`
הערך הוא CollectionMetadata ממוין ב-JSON (ללא שדות תאריך ושעה)
שדות: `user`, `collection`, `name`, `description`, `tags`
דוגמה: `class='collections', key='alice:my-docs', value='{"user":"alice","collection":"my-docs","name":"My Documents","description":"...","tags":["work"]}'`

#### שינוי 8: שירות הספרייה - הסרת תשתית ניהול אחסון
**קובץ:** `trustgraph-flow/trustgraph/librarian/service.py`

**הסרה:**
מפיקי ניהול אחסון (שורות 173-190):
  `vector_storage_management_producer`
  `object_storage_management_producer`
  `triples_storage_management_producer`
צרכן תגובות אחסון (שורות 192-201)
מטפל `on_storage_response` (שורות 467-473)

**שינוי:**
אתחול CollectionManager (שורות 215-224) - הסרת פרמטרים של מפיק אחסון

**הערה:** ממשק ה-API החיצוני לאוספים נשאר ללא שינוי:
`list-collections`
`update-collection`
`delete-collection`

#### שינוי 9: הסרת טבלת האוספים מ-LibraryTableStore
**קובץ:** `trustgraph-flow/trustgraph/tables/library.py`

**מחיקה:**
הצהרת CREATE של טבלת האוספים (שורות 114-127)
הצהרות מוכנות של האוספים (שורות 205-240)
כל שיטות האוספים (שורות 578-717):
  `ensure_collection_exists`
  `list_collections`
  `update_collection`
  `delete_collection`
  `get_collection`
  `create_collection`

**הצדקה:**
האוספים כעת מאוחסנים בטבלת התצורה
שינוי שמשפיע על השינויים - אין צורך בהעברת נתונים
מפשט את שירות הספרייה באופן משמעותי

#### שינוי 10: שירותי אחסון - ניהול אוספים מבוסס תצורה ✅ הושלם

**סטטוס:** כל 11 ה-backends של האחסון עברו לשימוש ב-`CollectionConfigHandler`.

**שירותים מושפעים (סה"כ 11):**
הטמעות מסמכים: milvus, pinecone, qdrant
הטמעות גרפים: milvus, pinecone, qdrant
אחסון אובייקטים: cassandra
אחסון משולשות: cassandra, falkordb, memgraph, neo4j

**קבצים:**
`trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/pinecone/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/triples/falkordb/write.py`
`trustgraph-flow/trustgraph/storage/triples/memgraph/write.py`
`trustgraph-flow/trustgraph/storage/triples/neo4j/write.py`

**תבנית יישום (לכל השירותים):**

1. **רישום מטפל תצורה ב-`__init__`:**
```python
# Add after AsyncProcessor initialization
self.register_config_handler(self.on_collection_config)
self.known_collections = set()  # Track (user, collection) tuples
```

2. **יישום מנהל תצורה:**
```python
async def on_collection_config(self, config, version):
    """Handle collection configuration updates"""
    logger.info(f"Collection config version: {version}")

    if "collections" not in config:
        return

    # Parse collections from config
    # Key format: "user:collection" in config["collections"]
    config_collections = set()
    for key in config["collections"].keys():
        if ":" in key:
            user, collection = key.split(":", 1)
            config_collections.add((user, collection))

    # Determine changes
    to_create = config_collections - self.known_collections
    to_delete = self.known_collections - config_collections

    # Create new collections (idempotent)
    for user, collection in to_create:
        try:
            await self.create_collection_internal(user, collection)
            self.known_collections.add((user, collection))
            logger.info(f"Created collection: {user}/{collection}")
        except Exception as e:
            logger.error(f"Failed to create {user}/{collection}: {e}")

    # Delete removed collections (idempotent)
    for user, collection in to_delete:
        try:
            await self.delete_collection_internal(user, collection)
            self.known_collections.discard((user, collection))
            logger.info(f"Deleted collection: {user}/{collection}")
        except Exception as e:
            logger.error(f"Failed to delete {user}/{collection}: {e}")
```

3. **אתחול אוספים ידועים בעת ההפעלה:**
```python
async def start(self):
    """Start the processor"""
    await super().start()
    await self.sync_known_collections()

async def sync_known_collections(self):
    """Query backend to populate known_collections set"""
    # Backend-specific implementation:
    # - Milvus/Pinecone/Qdrant: List collections/indexes matching naming pattern
    # - Cassandra: Query keyspaces or collection metadata
    # - Neo4j/Memgraph/FalkorDB: Query CollectionMetadata nodes
    pass
```

4. **שכתוב של שיטות טיפול קיימות:**
```python
# Rename and remove response sending:
# handle_create_collection → create_collection_internal
# handle_delete_collection → delete_collection_internal

async def create_collection_internal(self, user, collection):
    """Create collection (idempotent)"""
    # Same logic as current handle_create_collection
    # But remove response producer calls
    # Handle "already exists" gracefully
    pass

async def delete_collection_internal(self, user, collection):
    """Delete collection (idempotent)"""
    # Same logic as current handle_delete_collection
    # But remove response producer calls
    # Handle "not found" gracefully
    pass
```

5. **הסרת תשתית ניהול אחסון:**
   הסרת הגדרות והתחלה של `self.storage_request_consumer`
   הסרת הגדרות של `self.storage_response_producer`
   הסרת שיטת ה-dispatcher של `on_storage_management`
   הסרת מדדים לניהול אחסון
   הסרת יבוא: `StorageManagementRequest`, `StorageManagementResponse`

**שיקולים ספציפיים ל-Backend:**

**מאגרי וקטורים (Milvus, Pinecone, Qdrant):** לעקוב אחר `(user, collection)` לוגי ב-`known_collections`, אך ייתכן שייווצרו מספר אוספים ב-backend עבור כל מימד. להמשיך בדפוס היצירה המאוחרת. פעולות מחיקה חייבות להסיר את כל הווריאציות של המימד.

**Cassandra Objects:** אוספים הם מאפייני שורות, ולא מבנים. לעקוב אחר מידע ברמת ה-keyspace.

**מאגרי גרפים (Neo4j, Memgraph, FalkorDB):** לשאול צמתים של `CollectionMetadata` בעת ההפעלה. ליצור/למחוק צמתי מטא-נתונים בעת הסנכרון.

**Cassandra Triples:** להשתמש ב-API של `KnowledgeGraph` עבור פעולות אוסף.

**נקודות עיצוב מרכזיות:**

**עקביות בסופו של דבר:** אין מנגנון בקשה/תגובה, דחיפת תצורה משודרת
**אידמפוטנטיות:** כל פעולות היצירה/מחיקה חייבות להיות בטוחות לניסיון חוזר
**טיפול בשגיאות:** לרשום שגיאות אך לא לחסום עדכוני תצורה
**ריפוי עצמי:** פעולות שנכשלו ינסו שוב בדחיפת התצורה הבאה
**פורמט מפתח אוסף:** `"user:collection"` ב-`config["collections"]`

#### שינוי 11: עדכון סכימת האוסף - הסרת חותמות זמן
**קובץ:** `trustgraph-base/trustgraph/schema/services/collection.py`

**שינוי CollectionMetadata (שורות 13-21):**
להסיר את השדות `created_at` ו-`updated_at`:
```python
class CollectionMetadata(Record):
    user = String()
    collection = String()
    name = String()
    description = String()
    tags = Array(String())
    # Remove: created_at = String()
    # Remove: updated_at = String()
```

**שינוי ב-CollectionManagementRequest (שורות 25-47):**
הסרת שדות חותמת זמן:
```python
class CollectionManagementRequest(Record):
    operation = String()
    user = String()
    collection = String()
    timestamp = String()
    name = String()
    description = String()
    tags = Array(String())
    # Remove: created_at = String()
    # Remove: updated_at = String()
    tag_filter = Array(String())
    limit = Integer()
```

**ההצדקה:**
חותמות זמן אינן מוסיפות ערך לאוספים
שירות התצורה שומר על מעקב גרסאות משלו
מפשט את הסכימה ומקטין את נפח האחסון

#### יתרונות של מעבר לשירות התצורה

1. ✅ **מבטל נושאים של ניהול אחסון מקודדים קשות** - פותר את החסימה של ריבוי דיירים
2. ✅ **תיאום פשוט יותר** - אין המתנה אסינכרונית מורכבת לתגובות של 4+ שירותי אחסון
3. ✅ **עקביות בסופו של דבר** - שירותי האחסון מתעדכנים באופן עצמאי באמצעות דחיפה של תצורה
4. ✅ **אמינות טובה יותר** - דחיפה קבועה של תצורה לעומת בקשה/תגובה לא קבועה
5. ✅ **מודל תצורה מאוחד** - אוספים מטופלים כתצורה
6. ✅ **מפחית מורכבות** - מסיר כ-300 שורות של קוד תיאום
7. ✅ **מוכן לריבוי דיירים** - התצורה כבר תומכת בבידוד דיירים באמצעות מרחבי מפתחות
8. ✅ **מעקב גרסאות** - מנגנון גרסאות של שירות התצורה מספק תיעוד ביקורת

## הערות יישום

### תאימות לאחור

**שינויים בפרמטרים:**
שינויי שמות של פרמטרים בשורת הפקודה הם שינויים שוברים אך מקובלים (התכונה אינה פונקציונלית כרגע)
השירותים עובדים ללא פרמטרים (משתמשים בברירות המחדל)
מרחבי מפתחות ברירת מחדל נשמרו: "config", "knowledge", "librarian"
תור ברירת מחדל: `persistent://tg/config/config`

**ניהול אוספים:**
**שינוי שובר:** הטבלה של האוספים הוסרה מממרחב המפתחות של librarian
**לא סופקה העברת נתונים** - מקובל לשלב זה
ממשק API חיצוני לאוספים לא השתנה (פעולות רשימה/עדכון/מחיקה)
פורמט מטא-נתונים של אוספים פושט (הוסרו חותמות זמן)

### דרישות בדיקה

**בדיקת פרמטרים:**
1. ודאו שהפרמטר `--config-push-queue` עובד בשירות graph-embeddings
2. ודאו שהפרמטר `--config-push-queue` עובד בשירות text-completion
3. ודאו שהפרמטר `--config-push-queue` עובד בשירות התצורה
4. ודאו שהפרמטר `--cassandra-keyspace` עובד עבור שירות התצורה
5. ודאו שהפרמטר `--cassandra-keyspace` עובד עבור שירות cores
6. ודאו שהפרמטר `--cassandra-keyspace` עובד עבור שירות librarian
7. ודאו שהשירותים עובדים ללא פרמטרים (משתמשים בברירות המחדל)
8. ודאו פריסה מרובת דיירים עם שמות תורים ומרחבי מפתחות מותאמים אישית

**בדיקת ניהול אוספים:**
9. ודאו את הפעולה `list-collections` באמצעות שירות התצורה
10. ודאו ש-`update-collection` יוצר/מעדכן בטבלת התצורה
11. ודאו ש-`delete-collection` מסיר מטבלת התצורה
12. ודאו שדחיפה של תצורה מופעלת בעת עדכונים של אוספים
13. ודאו שסינון תגים עובד עם אחסון מבוסס תצורה
14. ודאו שפעולות על אוספים עובדות ללא שדות חותמות זמן

### דוגמה לפריסה מרובת דיירים
```bash
# Tenant: tg-dev
graph-embeddings \
  -p pulsar+ssl://broker:6651 \
  --pulsar-api-key <KEY> \
  --config-push-queue persistent://tg-dev/config/config

config-service \
  -p pulsar+ssl://broker:6651 \
  --pulsar-api-key <KEY> \
  --config-push-queue persistent://tg-dev/config/config \
  --cassandra-keyspace tg_dev_config
```

## ניתוח השפעה

### שירותים המושפעים משינוי 1-2 (שינוי שם פרמטר CLI)
כל השירותים היורשים מ-AsyncProcessor או FlowProcessor:
config-service
cores-service
librarian-service
graph-embeddings
document-embeddings
text-completion-* (כל הספקיות)
extract-* (כל ה-extractors)
query-* (כל שירותי השאילתות)
retrieval-* (כל שירותי ה-RAG)
storage-* (כל שירותי האחסון)
ועוד 20+ שירותים

### שירותים המושפעים משינויים 3-6 (Keyspace של Cassandra)
config-service
cores-service
librarian-service

### שירותים המושפעים משינויים 7-11 (ניהול אוספים)

**שינויים מיידיים:**
librarian-service (collection_manager.py, service.py)
tables/library.py (הסרת טבלת אוספים)
schema/services/collection.py (הסרת חותמת זמן)

**שינויים שהושלמו (שינוי 10):** ✅
כל שירותי האחסון (11 בסך הכל) - עברו ל-config push לעדכוני אוספים דרך `CollectionConfigHandler`
סכימת ניהול האחסון הוסרה מ-`storage.py`

## שיקולים עתידיים

### מודל Keyspace מבוסס משתמש

חלק מהשירותים משתמשים באופן דינמי ב-**keyspace מבוסס משתמש**, כאשר לכל משתמש יש את ה-keyspace של Cassandra שלו:

**שירותים עם keyspace מבוסס משתמש:**
1. **Triples Query Service** (`trustgraph-flow/trustgraph/query/triples/cassandra/service.py:65`)
   משתמש ב-`keyspace=query.user`
2. **Objects Query Service** (`trustgraph-flow/trustgraph/query/objects/cassandra/service.py:479`)
   משתמש ב-`keyspace=self.sanitize_name(user)`
3. **KnowledgeGraph Direct Access** (`trustgraph-flow/trustgraph/direct/cassandra_kg.py:18`)
   פרמטר ברירת מחדל `keyspace="trustgraph"`

**סטטוס:** אלה **לא משתנים** במפרט זה.

**נדרשת בדיקה עתידית:**
להעריך האם מודל ה-keyspace מבוסס משתמש יוצר בעיות בידוד שוכרים
לשקול האם פריסות מרובות שוכרים צריכות דפוסי קידומת keyspace (לדוגמה, `tenant_a_user1`)
לבדוק לגבי התנגשות פוטנציאלית של מזהי משתמש בין שוכרים
להעריך האם keyspace משותף יחיד לכל שוכר עם בידוד שורות מבוסס משתמש עדיף

**הערה:** זה לא חוסם את יישום הריבוי שוכרים הנוכחי, אך יש לבדוק אותו לפני פריסות ריבוי שוכרים לייצור.

## שלבי יישום

### שלב 1: תיקוני פרמטרים (שינויים 1-6)
לתקן את שם הפרמטר `--config-push-queue`
להוסיף תמיכה בפרמטר `--cassandra-keyspace`
**תוצאה:** תצורה של תור ו-keyspace מרובי שוכרים מופעלת

### שלב 2: הגירת ניהול אוספים (שינויים 7-9, 11)
להגר את אחסון האוספים לשירות התצורה
להסיר את טבלת האוספים מ-librarian
לעדכן את סכימת האוספים (להסיר חותמות זמן)
**תוצאה:** מבטלת את נושאי ניהול האחסון המקודדים קשות, מפשטת את librarian

### שלב 3: עדכוני שירותי אחסון (שינוי 10) ✅ הושלם
עדכנו את כל שירותי האחסון להשתמש ב-config push עבור אוספים דרך `CollectionConfigHandler`
הסרנו את תשתית הבקשות/תגובות לניהול אחסון
הסרנו הגדרות סכימה מיושנות
**תוצאה:** השגת ניהול אוספים מבוסס תצורה מלא

## הפניות
GitHub Issue: https://github.com/trustgraph-ai/trustgraph/issues/582
קבצים קשורים:
  `trustgraph-base/trustgraph/base/async_processor.py`
  `trustgraph-base/trustgraph/base/cassandra_config.py`
  `trustgraph-base/trustgraph/schema/core/topic.py`
  `trustgraph-base/trustgraph/schema/services/collection.py`
  `trustgraph-flow/trustgraph/config/service/service.py`
  `trustgraph-flow/trustgraph/cores/service.py`
  `trustgraph-flow/trustgraph/librarian/service.py`
  `trustgraph-flow/trustgraph/librarian/collection_manager.py`
  `trustgraph-flow/trustgraph/tables/library.py`
