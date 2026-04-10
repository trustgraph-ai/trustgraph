# מפרט טכני לשיפור ביצועי GraphRAG

## סקירה כללית

מפרט זה מתאר שיפורי ביצועים מקיפים עבור אלגוריתם GraphRAG (Graph Retrieval-Augmented Generation) ב-TrustGraph. יישום הנוכחי סובל מבעיות ביצועים משמעותיות המגבילות את יכולת ההרחבה וזמני התגובה. מפרט זה מתייחס לארבעה תחומים עיקריים של אופטימיזציה:

1. **אופטימיזציה של מעבר גרפים**: ביטול שאילתות מסד נתונים רקורסיביות לא יעילות ויישום חקר גרפים באצווה.
2. **אופטימיזציה של פתרון תגיות**: החלפת אחזור תגיות רציף בפעולות מקבילות/באצווה.
3. **שיפור אסטרטגיית אחסון במטמון**: יישום אחסון במטמון חכם עם פינוי LRU וטעינה מראש.
4. **אופטימיזציה של שאילתות**: הוספת שמירת תוצאות במטמון ואחסון במטמון של הטמעות לשיפור זמני התגובה.

## מטרות

**הפחתת נפח שאילתות מסד הנתונים**: השגת הפחתה של 50-80% בסך כל שאילתות מסד הנתונים באמצעות אצווה ואחסון במטמון.
**שיפור זמני תגובה**: יעד לבניית תת-גרפים מהירה פי 3-5 ופתרון תגיות מהיר פי 2-3.
**שיפור יכולת הרחבה**: תמיכה בגרפי ידע גדולים יותר עם ניהול זיכרון טוב יותר.
**שמירה על דיוק**: שמירה על פונקציונליות ואיכות תוצאות GraphRAG הקיימות.
**אפשרות לעיבוד מקבילי**: שיפור יכולות עיבוד מקבילי עבור בקשות מרובות בו-זמנית.
**הפחתת טביעת רגל של זיכרון**: יישום מבני נתונים וניהול זיכרון יעילים.
**הוספת יכולת ניטור**: הכללת מדדי ביצועים ויכולות ניטור.
**הבטחת אמינות**: הוספת טיפול בשגיאות ומנגנוני תזמון מתאימים.

## רקע

יישום GraphRAG הנוכחי ב-`trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py` מציג מספר בעיות ביצועים קריטיות המשפיעות באופן משמעותי על יכולת ההרחבה של המערכת:

### בעיות ביצועים נוכחיות

**1. מעבר גרפים לא יעיל (פונקציה `follow_edges`, שורות 79-127)**
מבצע 3 שאילתות נפרדות למסד הנתונים עבור כל ישות בכל רמת עומק.
תבנית שאילתה: שאילתות מבוססות נושא, מבוססות פרידיקט ומבוססות אובייקט עבור כל ישות.
ללא אצווה: כל שאילתה מעבדת רק ישות אחת בכל פעם.
ללא זיהוי מעגלים: ניתן לחזור על צמתים זהים מספר פעמים.
יישום רקורסיבי ללא שמירה במטמון מוביל למורכבות אקספוננציאלית.
מורכבות זמן: O(entities × max_path_length × triple_limit³)

**2. פתרון תגיות רציף (פונקציה `get_labelgraph`, שורות 144-171)**
מעבד כל רכיב משולש (נושא, פרידיקט, אובייקט) ברצף.
כל קריאה ל-`maybe_label` עלולה לגרום לשאילתה למסד הנתונים.
ללא ביצוע מקבילי או אצווה של שאילתות תגיות.
גורם עד ל-3 × קריאות אישיות למסד הנתונים עבור גודל תת-גרף.

**3. אסטרטגיית אחסון במטמון בסיסית (פונקציה `maybe_label`, שורות 62-77)**
מטמון מילון פשוט ללא מגבלות גודל או TTL.
מדיניות פינוי מטמון חסרת גבולות מובילה לצמיחה בלתי מוגבלת של זיכרון.
החסרה במטמון גורמת לשאילתות נפרדות למסד הנתונים.
ללא טעינה מראש או אחסון במטמון חכם.

**4. תבניות שאילתות לא אופטימליות**
שאילתות דמיון וקטורי לישויות אינן מאוחסנות במטמון בין בקשות דומות.
ללא שמירת תוצאות במטמון לתבניות שאילתות חוזרות.
חסרים אופטימיזציות שאילתות לתבניות גישה נפוצות.

**5. בעיות קריטיות של חיי אובייקט (`rag.py:96-102`)**
**אובייקט GraphRag נוצר מחדש עבור כל בקשה**: מופע חדש נוצר עבור כל שאילתה, תוך אובדן כל יתרונות המטמון.
**אובייקט שאילתה בעל אורך חיים קצר ביותר**: נוצר ונהרס בתוך ביצוע שאילתה יחיד (שורות 201-207).
**מטמון תגיות מאופס עבור כל בקשה**: חימום מטמון וידע שנצבר אובדים בין בקשות.
**תקורה של יצירת לקוח מחדש**: לקוחות מסד נתונים פוטנציאליים מוקמים מחדש עבור כל בקשה.
**ללא אופטימיזציה חוצה בקשות**: לא ניתן להפיק תועלת מתבניות שאילתות או שיתוף תוצאות.

### ניתוח השפעת ביצועים

תרחיש גרוע ביותר נוכחי עבור שאילתה טיפוסית:
**אחזור ישות**: שאילתת דמיון וקטורית אחת.
**מעבר גרפים**: entities × max_path_length × 3 × שאילתות triple_limit.
**פתרון תגיות**: 3 × שאילתות תגיות אישיות עבור גודל תת-גרף.
פלט חוזה (יש לעקוב אחר הפורמט המדויק).
עבור פרמטרים ברירת מחדל (50 ישויות, אורך נתיב 2, מגבלת 30 משולשים, גודל תת-גרף 150):
**מספר שאילתות מינימלי**: 1 + (50 × 2 × 3 × 30) + (150 × 3) = **9,451 שאילתות למסד נתונים**
**זמן תגובה**: 15-30 שניות עבור גרפים בגודל בינוני
**שימוש בזיכרון**: צמיחה בלתי מוגבלת של מטמון לאורך זמן
**יעילות מטמון**: 0% - המטמון מאופס בכל בקשה
**תקורה של יצירת אובייקטים**: אובייקטי GraphRag + שאילתה נוצרים/נמחקים עבור כל בקשה

מפרט זה מתייחס לפערים אלה על ידי יישום שאילתות באצווה, מטמון חכם ועיבוד מקבילי. על ידי אופטימיזציה של דפוסי שאילתות וגישה לנתונים, TrustGraph יכולה:
לתמוך בגרפי ידע בקנה מידה ארגוני עם מיליוני ישויות
לספק זמני תגובה של פחות משנייה עבור שאילתות טיפוסיות
לטפל במאות בקשות GraphRAG מקבילות
להתרחב ביעילות עם גודל ומורכבות הגרף

## עיצוב טכני

### ארכיטקטורה

אופטימיזציית הביצועים של GraphRAG דורשת את הרכיבים הטכניים הבאים:

#### 1. **שינוי ארכיטקטורה של משך חיי אובייקטים**
   **הפוך את GraphRag לבעל חיים ארוך**: העבר את המופע של GraphRag לרמה של המעבד לצורך שמירה בין בקשות
   **שמור על מטמון**: שמור על מטמון תוויות, מטמון הטבעות ומטמון תוצאות שאילתה בין בקשות
   **אופטימיזציה של אובייקט שאילתה**: שנה את מבנה אובייקט השאילתה כהקשר ביצוע קל משקל, ולא כמכל נתונים
   **שמירה על חיבורים**: שמור על חיבורי לקוח למסד הנתונים בין בקשות

   מודול: `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` (עודכן)

#### 2. **מנוע מעבר גרפים מותאם**
   החלף את `follow_edges` רקורסיבי בחיפוש רוחב-ראשוני איטרטיבי
   הטמעת עיבוד אצווה של ישויות בכל רמת מעבר
   הוסף זיהוי מעגלים באמצעות מעקב אחר צמתים מבקרים
   כלול סיום מוקדם כאשר מגיעים למגבלות

   מודול: `trustgraph-flow/trustgraph/retrieval/graph_rag/optimized_traversal.py`

#### 3. **מערכת פתרון תוויות מקבילה**
   שאילתות תוויות באצווה עבור מספר ישויות בו-זמנית
   הטמעת דפוסי async/await לגישה מקבילה למסד הנתונים
   הוסף אחזור מוקדם לדפוסי תוויות נפוצים
   כלול אסטרטגיות חימום מטמון תוויות

   מודול: `trustgraph-flow/trustgraph/retrieval/graph_rag/label_resolver.py`

#### 4. **שכבת מטמון תוויות שמרנית**
   מטמון LRU עם TTL קצר עבור תוויות בלבד (5 דקות) כדי לאזן בין ביצועים ועקביות
   ניטור מדדי מטמון ויחס פגיעות
   **ללא מטמון הטבעות**: כבר שמורים עבור כל שאילתה, אין יתרון בין שאילתות
   **ללא מטמון תוצאות שאילתה**: עקב חששות לגבי עקביות שינוי גרף

   מודול: `trustgraph-flow/trustgraph/retrieval/graph_rag/cache_manager.py`

#### 5. **מסגרת אופטימיזציה של שאילתות**
   ניתוח אופטימיזציה של דפוסי שאילתות והצעות
   מתאם שאילתות באצווה לגישה למסד הנתונים
   ניהול בריכת חיבורים וזמן קצוב של שאילתות
   ניטור ביצועים ואיסוף מדדים

   מודול: `trustgraph-flow/trustgraph/retrieval/graph_rag/query_optimizer.py`

### מודלים של נתונים

#### מצב מעבר גרפים מותאם

מנוע המעבר שומר על מצב כדי להימנע מפעולות מיותרות:

```python
@dataclass
class TraversalState:
    visited_entities: Set[str]
    current_level_entities: Set[str]
    next_level_entities: Set[str]
    subgraph: Set[Tuple[str, str, str]]
    depth: int
    query_batch: List[TripleQuery]
```

גישה זו מאפשרת:
זיהוי יעיל של מעגלים באמצעות מעקב אחר ישויות שביקרו
הכנת שאילתות באצווה בכל רמת מעבר
ניהול מצב חסכוני בזיכרון
סיום מוקדם כאשר מגיעים למגבלות גודל

#### מבנה מטמון משופר

```python
@dataclass
class CacheEntry:
    value: Any
    timestamp: float
    access_count: int
    ttl: Optional[float]

class CacheManager:
    label_cache: LRUCache[str, CacheEntry]
    embedding_cache: LRUCache[str, CacheEntry]
    query_result_cache: LRUCache[str, CacheEntry]
    cache_stats: CacheStatistics
```

#### מבני שאילתות אצווה

```python
@dataclass
class BatchTripleQuery:
    entities: List[str]
    query_type: QueryType  # SUBJECT, PREDICATE, OBJECT
    limit_per_entity: int

@dataclass
class BatchLabelQuery:
    entities: List[str]
    predicate: str = LABEL
```

### ממשקי API

#### ממשקי API חדשים:

**ממשק GraphTraversal API**
```python
async def optimized_follow_edges_batch(
    entities: List[str],
    max_depth: int,
    triple_limit: int,
    max_subgraph_size: int
) -> Set[Tuple[str, str, str]]
```

**ממשק API לפתרון תגיות אצווה**
```python
async def resolve_labels_batch(
    entities: List[str],
    cache_manager: CacheManager
) -> Dict[str, str]
```

**ממשק ניהול מטמון (Cache Management API)**
```python
class CacheManager:
    async def get_or_fetch_label(self, entity: str) -> str
    async def get_or_fetch_embeddings(self, query: str) -> List[float]
    async def cache_query_result(self, query_hash: str, result: Any, ttl: int)
    def get_cache_statistics(self) -> CacheStatistics
```

#### ממשקי API שעודכנו:

**GraphRag.query()** - שופר עם אופטימיזציות ביצועים:
הוסף פרמטר cache_manager לשליטה על המטמון
הוסף ערך החזרה performance_metrics
הוסף פרמטר query_timeout לאמינות

**מחלקה Query** - שופרה לעיבוד באצווה:
החלף עיבוד ישויות בודדות בפעולות באצווה
הוסף מנהלי הקשר אסינכרוניים לניקוי משאבים
הוסף פונקציות החזרה (callbacks) להתקדמות עבור פעולות ארוכות

### פרטי יישום

#### שלב 0: שינוי ארכיטקטורה קריטי

**יישום בעייתי נוכחי:**
```python
# INEFFICIENT: GraphRag recreated every request
class Processor(FlowProcessor):
    async def on_request(self, msg, consumer, flow):
        # PROBLEM: New GraphRag instance per request!
        self.rag = GraphRag(
            embeddings_client = flow("embeddings-request"),
            graph_embeddings_client = flow("graph-embeddings-request"),
            triples_client = flow("triples-request"),
            prompt_client = flow("prompt-request"),
            verbose=True,
        )
        # Cache starts empty every time - no benefit from previous requests
        response = await self.rag.query(...)

# VERY SHORT-LIVED: Query object created/destroyed per request
class GraphRag:
    async def query(self, query, user="trustgraph", collection="default", ...):
        q = Query(rag=self, user=user, collection=collection, ...)  # Created
        kg = await q.get_labelgraph(query)  # Used briefly
        # q automatically destroyed when function exits
```

**ארכיטקטורה ארוכת טווח ומותאמת:**
```python
class Processor(FlowProcessor):
    def __init__(self, **params):
        super().__init__(**params)
        self.rag_instance = None  # Will be initialized once
        self.client_connections = {}

    async def initialize_rag(self, flow):
        """Initialize GraphRag once, reuse for all requests"""
        if self.rag_instance is None:
            self.rag_instance = LongLivedGraphRag(
                embeddings_client=flow("embeddings-request"),
                graph_embeddings_client=flow("graph-embeddings-request"),
                triples_client=flow("triples-request"),
                prompt_client=flow("prompt-request"),
                verbose=True,
            )
        return self.rag_instance

    async def on_request(self, msg, consumer, flow):
        # REUSE the same GraphRag instance - caches persist!
        rag = await self.initialize_rag(flow)

        # Query object becomes lightweight execution context
        response = await rag.query_with_context(
            query=v.query,
            execution_context=QueryContext(
                user=v.user,
                collection=v.collection,
                entity_limit=entity_limit,
                # ... other params
            )
        )

class LongLivedGraphRag:
    def __init__(self, ...):
        # CONSERVATIVE caches - balance performance vs consistency
        self.label_cache = LRUCacheWithTTL(max_size=5000, ttl=300)  # 5min TTL for freshness
        # Note: No embedding cache - already cached per-query, no cross-query benefit
        # Note: No query result cache due to consistency concerns
        self.performance_metrics = PerformanceTracker()

    async def query_with_context(self, query: str, context: QueryContext):
        # Use lightweight QueryExecutor instead of heavyweight Query object
        executor = QueryExecutor(self, context)  # Minimal object
        return await executor.execute(query)

@dataclass
class QueryContext:
    """Lightweight execution context - no heavy operations"""
    user: str
    collection: str
    entity_limit: int
    triple_limit: int
    max_subgraph_size: int
    max_path_length: int

class QueryExecutor:
    """Lightweight execution context - replaces old Query class"""
    def __init__(self, rag: LongLivedGraphRag, context: QueryContext):
        self.rag = rag
        self.context = context
        # No heavy initialization - just references

    async def execute(self, query: str):
        # All heavy lifting uses persistent rag caches
        return await self.rag.execute_optimized_query(query, self.context)
```

שינוי ארכיטקטורה זה מספק:
**הפחתת שאילתות מסד נתונים ב-10-20%** עבור גרפים עם קשרים נפוצים (בהשוואה ל-0% כיום)
**ביטול תקורה של יצירת אובייקטים** עבור כל בקשה
**בריכת חיבורים קבועה** ושימוש חוזר בלקוח
**אופטימיזציה בין בקשות** בתוך חלונות TTL של מטמון

**מגבלה חשובה של עקביות מטמון:**
אחסון מטמון לטווח ארוך מכניס סיכון של מידע מיושן כאשר ישויות/תוויות נמחקים או משתנים בגרף הבסיסי. מטמון LRU עם TTL מספק איזון בין שיפורי ביצועים ורעננות נתונים, אך אינו יכול לזהות שינויים בזמן אמת בגרף.

#### שלב 1: אופטימיזציה של מעבר גרפים

**בעיות ביישום הנוכחי:**
```python
# INEFFICIENT: 3 queries per entity per level
async def follow_edges(self, ent, subgraph, path_length):
    # Query 1: s=ent, p=None, o=None
    res = await self.rag.triples_client.query(s=ent, p=None, o=None, limit=self.triple_limit)
    # Query 2: s=None, p=ent, o=None
    res = await self.rag.triples_client.query(s=None, p=ent, o=None, limit=self.triple_limit)
    # Query 3: s=None, p=None, o=ent
    res = await self.rag.triples_client.query(s=None, p=None, o=ent, limit=self.triple_limit)
```

**יישום אופטימלי:**
```python
async def optimized_traversal(self, entities: List[str], max_depth: int) -> Set[Triple]:
    visited = set()
    current_level = set(entities)
    subgraph = set()

    for depth in range(max_depth):
        if not current_level or len(subgraph) >= self.max_subgraph_size:
            break

        # Batch all queries for current level
        batch_queries = []
        for entity in current_level:
            if entity not in visited:
                batch_queries.extend([
                    TripleQuery(s=entity, p=None, o=None),
                    TripleQuery(s=None, p=entity, o=None),
                    TripleQuery(s=None, p=None, o=entity)
                ])

        # Execute all queries concurrently
        results = await self.execute_batch_queries(batch_queries)

        # Process results and prepare next level
        next_level = set()
        for result in results:
            subgraph.update(result.triples)
            next_level.update(result.new_entities)

        visited.update(current_level)
        current_level = next_level - visited

    return subgraph
```

#### שלב 2: פתרון מקבילי של תגיות

**יישום סדרתי נוכחי:**
```python
# INEFFICIENT: Sequential processing
for edge in subgraph:
    s = await self.maybe_label(edge[0])  # Individual query
    p = await self.maybe_label(edge[1])  # Individual query
    o = await self.maybe_label(edge[2])  # Individual query
```

**יישום מקבילי אופטימלי:**
```python
async def resolve_labels_parallel(self, subgraph: List[Triple]) -> List[Triple]:
    # Collect all unique entities needing labels
    entities_to_resolve = set()
    for s, p, o in subgraph:
        entities_to_resolve.update([s, p, o])

    # Remove already cached entities
    uncached_entities = [e for e in entities_to_resolve if e not in self.label_cache]

    # Batch query for all uncached labels
    if uncached_entities:
        label_results = await self.batch_label_query(uncached_entities)
        self.label_cache.update(label_results)

    # Apply labels to subgraph
    return [
        (self.label_cache.get(s, s), self.label_cache.get(p, p), self.label_cache.get(o, o))
        for s, p, o in subgraph
    ]
```

#### שלב 3: אסטרטגיית אחסון מטמון מתקדמת

**מטמון LRU עם TTL:**
```python
class LRUCacheWithTTL:
    def __init__(self, max_size: int, default_ttl: int = 3600):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.access_times = {}

    async def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            # Check TTL expiration
            if time.time() - self.access_times[key] > self.default_ttl:
                del self.cache[key]
                del self.access_times[key]
                return None

            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    async def put(self, key: str, value: Any):
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.max_size:
                # Remove least recently used
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                del self.access_times[oldest_key]

        self.cache[key] = value
        self.access_times[key] = time.time()
```

#### שלב 4: אופטימיזציה וניטור של שאילתות

**איסוף מדדי ביצועים:**
```python
@dataclass
class PerformanceMetrics:
    total_queries: int
    cache_hits: int
    cache_misses: int
    avg_response_time: float
    subgraph_construction_time: float
    label_resolution_time: float
    total_entities_processed: int
    memory_usage_mb: float
```

**זמן תגובה מקסימלי ומנגנון ניתוב מחדש:**
```python
async def execute_with_timeout(self, query_func, timeout: int = 30):
    try:
        return await asyncio.wait_for(query_func(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"Query timeout after {timeout}s")
        raise GraphRagTimeoutError(f"Query exceeded timeout of {timeout}s")
```

## שיקולים בנוגע לעקביות מטמון

**פשרות בנוגע לרעננות נתונים:**
**מטמון תוויות (TTL של 5 דקות)**: סיכון להצגת תוויות של ישויות שנמחקו/ששמותיהן שונו.
**ללא שמירת מטמון של הטמעות (embeddings)**: לא נדרש - הטמעות כבר שמורות מטמון עבור כל שאילתה.
**ללא שמירת מטמון של תוצאות**: מונע קבלת תוצאות תת-גרף לא עדכניות מישויות/קשרים שנמחקו.

**אסטרטגיות הפחתה:**
**ערכי TTL שמרניים**: איזון בין שיפורי ביצועים (10-20%) לבין רעננות נתונים.
**מנגנוני ביטול מטמון**: שילוב אופציונלי עם אירועי שינוי בגרף.
**לוחות מחוונים לניטור**: מעקב אחר אחוזי פגיעה במטמון (cache hit rates) לעומת מקרים של נתונים לא עדכניים.
**מדיניות מטמון הניתנות לתצורה**: אפשרות לכוונון פר-פריסה בהתאם לתדירות השינויים.

**תצורת מטמון מומלצת בהתאם לקצב שינויים בגרף:**
**קצב שינויים גבוה (>100 שינויים/שעה)**: TTL=60 שניות, גדלי מטמון קטנים יותר.
**קצב שינויים בינוני (10-100 שינויים/שעה)**: TTL=300 שניות (ברירת מחדל).
**קצב שינויים נמוך (<10 שינויים/שעה)**: TTL=600 שניות, גדלי מטמון גדולים יותר.

## שיקולים בנוגע לאבטחה

**מניעת הזרקת שאילתות:**
אימות כל מזהי ישויות ופרמטרים של שאילתות.
שימוש בשאילתות מפורמטות עבור כל אינטראקציות עם מסד הנתונים.
יישום מגבלות על מורכבות השאילתות כדי למנוע התקפות מניעת שירות (DoS).

**הגנה על משאבים:**
אכיפת מגבלות על גודל תת-גרף מקסימלי.
יישום זמני קצבה לשאילתות כדי למנוע מיצוי משאבים.
הוספת ניטור מגבלות לשימוש בזיכרון.

**בקרת גישה:**
שמירה על בידוד משתמשים ואוספים קיימים.
הוספת רישום ביקורת עבור פעולות המשפיעות על הביצועים.
יישום הגבלת קצב עבור פעולות יקרות.

## שיקולים בנוגע לביצועים

### שיפורי ביצועים צפויים

**הפחתת מספר שאילתות:**
נוכחי: ~9,000+ שאילתות עבור בקשה טיפוסית.
אופטימלי: ~50-100 שאילתות מקובצות (הפחתה של 98%).

**שיפורי זמן תגובה:**
מעבר בגרף: 15-20 שניות → 3-5 שניות (מהיר פי 4-5).
פתרון תוויות: 8-12 שניות → 2-4 שניות (מהיר פי 3).
שאילתה כוללת: 25-35 שניות → 6-10 שניות (שיפור של פי 3-4).

**יעילות זיכרון:**
גדלי מטמון מוגבלים מונעים דליפות זיכרון.
מבני נתונים יעילים מפחיתים את טביעת הרגל של הזיכרון בערך ב-40%.
איסוף אשפה טוב יותר באמצעות ניקוי משאבים נכון.

**ציפיות ריאליות בנוגע לביצועים:**
**מטמון תוויות**: הפחתה של 10-20% במספר השאילתות עבור גרפים עם קשרים נפוצים.
**אופטימיזציה של קיבוץ**: הפחתה של 50-80% במספר השאילתות (אופטימיזציה עיקרית).
**אופטימיזציה של חיי אובייקט**: ביטול תקורה של יצירה מחדש בכל בקשה.
**שיפור כולל**: שיפור של פי 3-4 בזמן התגובה בעיקר בזכות קיבוץ.

**שיפורי יכולת הרחבה:**
תמיכה בגרפי ידע גדולים פי 3-5 (מוגבל על ידי צרכי עקביות מטמון).
קיבולת גבוהה יותר פי 3-5 של בקשות מקבילות.
ניצול טוב יותר של משאבים באמצעות שימוש חוזר בחיבורים.

### ניטור ביצועים

**מדדים בזמן אמת:**
זמני ביצוע שאילתות לפי סוג פעולה.
אחוזי פגיעה במטמון ויעילות.
שימוש בבריכת חיבורים למסד הנתונים.
שימוש בזיכרון והשפעת איסוף אשפה.

**בדיקות ביצועים:**
בדיקות רגרסיה אוטומטיות לביצועים
בדיקות עומסים עם נפחי נתונים ריאליים
השוואות ביצועים מול המימוש הנוכחי

## אסטרטגיית בדיקות

### בדיקות יחידה
בדיקת רכיבים בודדים עבור מעבר, אחסון במטמון ופתרון תגיות
הדמיית אינטראקציות עם מסד נתונים לצורך בדיקות ביצועים
בדיקת פינוי מטמון ותפוגה של זמן תפוגה (TTL)
בדיקת טיפול בשגיאות ותסריטי תזמון

### בדיקות אינטגרציה
בדיקות מקצה לקצה של שאילתות GraphRAG עם אופטימיזציות
בדיקת אינטראקציות עם מסד נתונים עם נתונים אמיתיים
טיפול בבקשות מקבילות וניהול משאבים
זיהוי דליפות זיכרון ואימות ניקוי משאבים

### בדיקות ביצועים
בדיקות ביצועים מול המימוש הנוכחי
בדיקות עומסים עם גדלים ומורכבויות גרף משתנים
בדיקות לחץ עבור מגבלות זיכרון וחיבורים
בדיקות רגרסיה לשיפורי ביצועים

### בדיקות תאימות
אימות תאימות של ממשקי API קיימים של GraphRAG
בדיקה עם מנועי גרפים שונים
אימות דיוק התוצאות בהשוואה למימוש הנוכחי

## תוכנית יישום

### גישת יישום ישירה
מכיוון שמותר לשנות ממשקי API, ליישם אופטימיזציות ישירות ללא מורכבות של העברה:

1. **החלפת `follow_edges`:** כתיבה מחדש עם מעבר אצווה איטרטיבי
2. **אופטימיזציה של `get_labelgraph`:** יישום פתרון תגיות מקבילי
3. **הוספת GraphRag ארוך טווח:** שינוי של מעבד כדי לשמור על מופע קבוע
4. **יישום אחסון במטמון של תגיות:** הוספת מטמון LRU עם TTL למחלקת GraphRag

### היקף השינויים
**מחלקה של שאילתות:** החלפת כ-50 שורות ב-`follow_edges`, הוספת כ-30 שורות לטיפול באצווה
**מחלקה של GraphRag:** הוספת שכבת אחסון במטמון (כ-40 שורות)
**מחלקה של מעבד:** שינוי לשימוש במופע קבוע של GraphRag (כ-20 שורות)
**סה"כ:** כ-140 שורות של שינויים ממוקדים, בעיקר בתוך מחלקות קיימות

## ציר זמן

**שבוע 1: יישום ליבה**
החלפת `follow_edges` עם מעבר אצווה איטרטיבי
יישום פתרון תגיות מקבילי ב-`get_labelgraph`
הוספת מופע GraphRag ארוך טווח למעבד
יישום שכבת אחסון במטמון של תגיות

**שבוע 2: בדיקות ושילוב**
בדיקות יחידה ללוגיקה חדשה של מעבר ואחסון במטמון
בדיקות ביצועים מול המימוש הנוכחי
בדיקות אינטגרציה עם נתוני גרף אמיתיים
סקירת קוד ואופטימיזציה

**שבוע 3: פריסה**
פריסת המימוש המותאם
ניטור שיפורי ביצועים
כוונון עדין של זמן תפוגה של מטמון וגדלי אצווה בהתבסס על שימוש אמיתי

## שאלות פתוחות

**בריכת חיבורים למסד נתונים:** האם עלינו ליישם בריכת חיבורים מותאמת אישית או להסתמך על בריכת חיבורים קיימת של לקוח מסד נתונים?
**שימור מטמון:** האם מטמון התגיות וההטבעות צריך להתמיד בין הפעלות מחדש של השירות?
**אחסון במטמון מבוזר:** עבור פריסות מרובות מופעים, האם עלינו ליישם אחסון במטמון מבוזר עם Redis/Memcached?
**פורמט תוצאות שאילתה:** האם עלינו לייעל את הייצוג הפנימי של משולש לטובת יעילות זיכרון טובה יותר?
**שילוב ניטור:** אילו מדדים יש לחשוף למערכות ניטור קיימות (Prometheus, וכו')?

## הפניות

[מימוש מקורי של GraphRAG](trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py)
[עקרונות ארכיטקטורה של TrustGraph](architecture-principles.md)
[מפרט ניהול אוספים](collection-management.md)
