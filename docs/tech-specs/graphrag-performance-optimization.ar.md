# GraphRAG Performance Optimisation Technical Specification

## Overview

يصف هذا المستند تفصيليًا تحسينات الأداء الشاملة لخوارزمية GraphRAG (Graph Retrieval-Augmented Generation) في TrustGraph. تعاني التنفيذ الحالي من نقاط اختناق أداء كبيرة تحد من قابلية التوسع وأوقات الاستجابة. يتناول هذا المستند أربعة مجالات رئيسية للتحسين:

1. **تحسين اجتياز الرسم البياني**: التخلص من استعلامات قاعدة البيانات المتكررة غير الفعالة وتنفيذ استكشاف الرسم البياني المجمّع.
2. **تحسين حل التسميات**: استبدال استرداد التسميات التسلسلي بعمليات متوازية/مجمعة.
3. **تحسين استراتيجية التخزين المؤقت**: تنفيذ تخزين مؤقت ذكي مع إخلاء LRU والتعبئة المسبقة.
4. **تحسين الاستعلام**: إضافة تدوين النتائج وتخزين تضمينات الاستعلام لتحسين أوقات الاستجابة.

## الأهداف

**تقليل حجم استعلامات قاعدة البيانات**: تحقيق تقليل بنسبة 50-80٪ في إجمالي استعلامات قاعدة البيانات من خلال التجميع والتخزين المؤقت.
<<<<<<< HEAD
**تحسين أوقات الاستجابة**: استهداف سرعة بناء الرسوم البيانية الفرعية بمقدار 3-5 مرات وسرعة حل التسميات بمقدار 2-3 مرات.
**تعزيز قابلية التوسع**: دعم رسوم بيانية معرفية أكبر مع إدارة أفضل للذاكرة.
=======
**تحسين أوقات الاستجابة**: استهداف سرعة بناء الرسوم البيانية الفرعية 3-5 مرات أسرع وسرعة حل التسميات 2-3 مرات أسرع.
**تعزيز قابلية التوسع**: دعم رسوم بيانية معرفية أكبر مع إدارة ذاكرة أفضل.
>>>>>>> 82edf2d (New md files from RunPod)
**الحفاظ على الدقة**: الحفاظ على وظائف GraphRAG الحالية وجودة النتائج.
**تمكين التزامن**: تحسين إمكانيات المعالجة المتوازية للطلبات المتزامنة المتعددة.
**تقليل البصمة الذاكرة**: تنفيذ هياكل بيانات وإدارة ذاكرة فعالة.
**إضافة إمكانية المراقبة**: تضمين مقاييس الأداء وقدرات المراقبة.
**ضمان الموثوقية**: إضافة معالجة مناسبة للأخطاء وآليات المهلة.

## الخلفية

يُظهر التنفيذ الحالي لـ GraphRAG في `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py` العديد من مشكلات الأداء الهامة التي تؤثر بشدة على قابلية توسع النظام:

### المشكلات الحالية في الأداء

**1. اجتياز الرسم البياني غير الفعال (دالة `follow_edges`، الأسطر 79-127)**
يقوم بإجراء 3 استعلامات لقاعدة البيانات لكل كيان لكل مستوى عمق.
نمط الاستعلام: استعلامات تعتمد على الموضوع، واستعلامات تعتمد على الرابط، واستعلامات تعتمد على الكائن لكل كيان.
لا يوجد تجميع: يعالج كل استعلام كيانًا واحدًا فقط في كل مرة.
<<<<<<< HEAD
لا يوجد اكتشاف دورات: يمكن إعادة زيارة نفس العقد عدة مرات.
=======
لا يوجد اكتشاف للدورات: يمكن إعادة زيارة نفس العقد عدة مرات.
>>>>>>> 82edf2d (New md files from RunPod)
يؤدي التنفيذ المتكرر بدون تدوين إلى تعقيد أسي.
التعقيد الزمني: O(entities × max_path_length × triple_limit³)

**2. حل تسلسلي للتسميات (دالة `get_labelgraph`، الأسطر 144-171)**
يعالج كل مكون ثلاثي (موضوع، رابط، كائن) بالتسلسل.
قد يؤدي كل استدعاء لـ `maybe_label` إلى استعلام لقاعدة البيانات.
لا يوجد تنفيذ متوازي أو تجميع لاستعلامات التسمية.
<<<<<<< HEAD
يؤدي إلى ما يصل إلى 3 × استعلامات قاعدة بيانات فردية بحجم الرسم البياني الفرعي.
=======
يؤدي إلى ما يصل إلى 3 × استعلامات قاعدة البيانات الفردية لحجم الرسم البياني الفرعي.
>>>>>>> 82edf2d (New md files from RunPod)

**3. استراتيجية تخزين مؤقت بدائية (دالة `maybe_label`، الأسطر 62-77)**
ذاكرة تخزين مؤقت بسيطة للقواميس بدون حدود حجم أو TTL.
لا توجد سياسة إخلاء للتخزين المؤقت تؤدي إلى نمو غير محدود للذاكرة.
تؤدي أخطاء التخزين المؤقت إلى استعلامات قاعدة بيانات فردية.
لا يوجد تعبئة مسبقة أو تخزين مؤقت ذكي.

**4. أنماط استعلام دون المستوى الأمثل**
استعلامات تشابه متجه الكيان غير مخزنة مؤقتًا بين الطلبات المتشابهة.
لا يوجد تدوين للنتائج لأنماط الاستعلام المتكررة.
<<<<<<< HEAD
أنماط استعلام مفقودة للوصول الشائع.
=======
أنماط استعلام مفقودة للتحسين للأنماط الشائعة للوصول.
>>>>>>> 82edf2d (New md files from RunPod)

**5. مشكلات حرجة في عمر الكائن (`rag.py:96-102`)**
**يتم إعادة إنشاء كائن GraphRag لكل طلب**: يتم إنشاء نسخة جديدة لكل استعلام، مما يفقد جميع فوائد التخزين المؤقت.
**عمر كائن الاستعلام قصير للغاية**: يتم إنشاؤه وتدميره داخل تنفيذ استعلام واحد (الأسطر 201-207).
**يتم إعادة تعيين ذاكرة التخزين المؤقت للتسميات لكل طلب**: يتم فقد التخزين المؤقت والتراكم المعرفي بين الطلبات.
**نفقات إعادة إنشاء العميل**: قد يتم إعادة إنشاء عملاء قاعدة البيانات لكل طلب.
**لا يوجد تحسين عبر الطلبات**: لا يمكن الاستفادة من أنماط الاستعلام أو مشاركة النتائج.

### تحليل تأثير الأداء

السيناريو الأسوأ الحالي لطلب نموذجي:
**استرداد الكيان**: استعلام واحد لتقارب المتجهات.
**اجتياز الرسم البياني**: entities × max_path_length × 3 × triple_limit استعلامات.
**حل التسميات**: subgraph_size × 3 استعلامات تسمية فردية.

<<<<<<< HEAD
للإعدادات الافتراضية (50 كيانًا، وطول المسار 2، وقيود على 30 ثلاثية، وحجم الرسم البياني الفرعي 150):
**عدد الاستعلامات:** 1 + (50 × 2 × 3 × 30) + (150 × 3) = **9451 استعلامًا لقاعدة البيانات**
=======
للإعدادات الافتراضية (50 كيانًا، وطول المسار 2، وقيود على 30 ثلاثية، وحجم الرسوم البيانية الفرعية 150):
**الاستعلامات الدنيا:** 1 + (50 × 2 × 3 × 30) + (150 × 3) = **9451 استعلامًا لقاعدة البيانات**
>>>>>>> 82edf2d (New md files from RunPod)
**وقت الاستجابة:** 15-30 ثانية للرسوم البيانية متوسطة الحجم
**استخدام الذاكرة:** نمو غير محدود لذاكرة التخزين المؤقت بمرور الوقت
**فعالية التخزين المؤقت:** 0% - يتم إعادة تعيين ذاكرة التخزين المؤقت في كل طلب
**تكلفة إنشاء الكائنات:** يتم إنشاء كائنات GraphRag + Query وتدميرها لكل طلب

تعالج هذه المواصفات هذه الثغرات من خلال تنفيذ الاستعلامات المجمعة، والتخزين المؤقت الذكي، والمعالجة المتوازية. من خلال تحسين أنماط الاستعلام والوصول إلى البيانات، يمكن لـ TrustGraph:
<<<<<<< HEAD
دعم رسوم بيانية معرفية على نطاق المؤسسات تحتوي على ملايين الكيانات
توفير أوقات استجابة أقل من ثانية للاستعلامات النموذجية
التعامل مع مئات طلبات GraphRAG المتزامنة
التوسع بكفاءة مع حجم الرسم البياني وتعقيده
=======
دعم الرسوم البيانية المعرفية على نطاق المؤسسات مع ملايين الكيانات
توفير أوقات استجابة أقل من ثانية للاستعلامات النموذجية
التعامل مع مئات طلبات GraphRAG المتزامنة
التوسع بكفاءة مع حجم وتعقيد الرسم البياني
>>>>>>> 82edf2d (New md files from RunPod)

## التصميم الفني

### البنية

يتطلب تحسين أداء GraphRAG المكونات الفنية التالية:

#### 1. **إعادة هيكلة دورة حياة الكائنات**
   **جعل GraphRag يعمل لفترة أطول:** نقل مثيل GraphRag إلى مستوى المعالج للاستمرارية عبر الطلبات
   **الحفاظ على ذاكرة التخزين المؤقت:** الحفاظ على ذاكرة التخزين المؤقت للتسميات، وذاكرة التخزين المؤقت للتضمينات، وذاكرة التخزين المؤقت لنتائج الاستعلام بين الطلبات
   **تحسين كائن الاستعلام:** إعادة هيكلة الاستعلام كسياق تنفيذ خفيف الوزن، وليس حاوية بيانات
<<<<<<< HEAD
   **استمرارية الاتصال:** الحفاظ على اتصالات عميل قاعدة البيانات عبر الطلبات

   الوحدة: `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` (تم التعديل)

#### 2. **محرك اجتياز الرسم البياني المحسن**
   استبدال `follow_edges` التكراري ببحث عرضي تكراري
   تنفيذ معالجة مجمعة للكيانات في كل مستوى من مستويات الاجتياز
=======
   **استمرار الاتصال:** الحفاظ على اتصالات عميل قاعدة البيانات عبر الطلبات

   الوحدة: `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` (تم التعديل)

#### 2. **محرك اجتياز الرسوم البيانية المحسن**
   استبدال `follow_edges` التكراري ببحث عرضي تكراري
   تنفيذ معالجة الكيانات المجمعة في كل مستوى من مستويات الاجتياز
>>>>>>> 82edf2d (New md files from RunPod)
   إضافة اكتشاف الدورات باستخدام تتبع العقد التي تمت زيارتها
   تضمين الإنهاء المبكر عند الوصول إلى الحدود

   الوحدة: `trustgraph-flow/trustgraph/retrieval/graph_rag/optimized_traversal.py`

#### 3. **نظام حل التسميات المتوازي**
   تجميع استعلامات التسميات لعدة كيانات في وقت واحد
   تنفيذ أنماط async/await للوصول المتزامن إلى قاعدة البيانات
   إضافة استرجاع استباقي لأنماط التسميات الشائعة
   تضمين استراتيجيات تسخين ذاكرة التخزين المؤقت للتسميات

   الوحدة: `trustgraph-flow/trustgraph/retrieval/graph_rag/label_resolver.py`

#### 4. **طبقة تخزين مؤقت محافظة للتسميات**
<<<<<<< HEAD
   ذاكرة تخزين مؤقت LRU مع TTL قصيرة للتسميات فقط (5 دقائق) لتحقيق التوازن بين الأداء والاتساق
   مراقبة مقاييس ذاكرة التخزين المؤقت ونسبة النجاح
   **لا يوجد تخزين مؤقت للتضمينات:** يتم تخزينها بالفعل لكل استعلام، ولا يوجد فائدة عبر الاستعلامات
   **لا يوجد تخزين مؤقت لنتائج الاستعلام:** بسبب مخاوف اتساق تغييرات الرسم البياني
=======
   ذاكرة تخزين مؤقت LRU مع TTL قصيرة للتسميات فقط (5 دقائق) لتحقيق التوازن بين الأداء مقابل الاتساق
   مراقبة مقاييس ذاكرة التخزين المؤقت ونسبة الإصابة
   **لا يوجد تخزين مؤقت للتضمينات:** يتم تخزينها بالفعل لكل استعلام، ولا يوجد فائدة عبر الاستعلامات
   **لا يوجد تخزين مؤقت لنتائج الاستعلام:** بسبب مخاوف اتساق تعديل الرسم البياني
>>>>>>> 82edf2d (New md files from RunPod)

   الوحدة: `trustgraph-flow/trustgraph/retrieval/graph_rag/cache_manager.py`

#### 5. **إطار تحسين الاستعلام**
   تحليل الاستعلام واقتراحات التحسين
   منسق استعلامات مجمعة للوصول إلى قاعدة البيانات
   تجميع الاتصالات وإدارة مهلة الاستعلام
   مراقبة الأداء وجمع المقاييس

   الوحدة: `trustgraph-flow/trustgraph/retrieval/graph_rag/query_optimizer.py`

### نماذج البيانات

<<<<<<< HEAD
#### حالة اجتياز الرسم البياني المحسنة
=======
#### حالة اجتياز الرسوم البيانية المحسنة
>>>>>>> 82edf2d (New md files from RunPod)

يحتفظ محرك الاجتياز بالحالة لتجنب العمليات المتكررة:

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

تسمح هذه الطريقة بما يلي:
الكشف الفعال عن الدورات من خلال تتبع الكيانات التي تمت زيارتها.
إعداد استعلامات مجمعة في كل مستوى من مستويات التكرار.
إدارة حالة فعالة من حيث الذاكرة.
الإنهاء المبكر عند الوصول إلى حدود الحجم.

#### هيكل ذاكرة تخزين مؤقتة مُحسّن

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

#### هياكل الاستعلامات المجمعة

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

### واجهات برمجة التطبيقات (APIs)

#### واجهات برمجة تطبيقات جديدة:

**واجهة برمجة تطبيقات GraphTraversal**
```python
async def optimized_follow_edges_batch(
    entities: List[str],
    max_depth: int,
    triple_limit: int,
    max_subgraph_size: int
) -> Set[Tuple[str, str, str]]
```

**واجهة برمجة تطبيقات (API) لحل مشكلات التسمية الدفعية.**
```python
async def resolve_labels_batch(
    entities: List[str],
    cache_manager: CacheManager
) -> Dict[str, str]
```

**واجهة برمجة تطبيقات إدارة ذاكرة التخزين المؤقت**
```python
class CacheManager:
    async def get_or_fetch_label(self, entity: str) -> str
    async def get_or_fetch_embeddings(self, query: str) -> List[float]
    async def cache_query_result(self, query_hash: str, result: Any, ttl: int)
    def get_cache_statistics(self) -> CacheStatistics
```

#### واجهات برمجة التطبيقات (APIs) المعدلة:

**GraphRag.query()** - تم تحسينها مع تحسينات في الأداء:
إضافة معلمة `cache_manager` للتحكم في التخزين المؤقت.
تضمين قيمة الإرجاع `performance_metrics`.
إضافة معلمة `query_timeout` للموثوقية.

**فئة Query** - تم إعادة هيكلتها لمعالجة الدفعات:
استبدال معالجة الكيانات الفردية بعمليات الدفعات.
إضافة مديري سياق غير متزامنين لتنظيف الموارد.
<<<<<<< HEAD
تضمين استدعاءات رد الاتصال للتقدم لعمليات طويلة الأمد.
=======
تضمين ردود اتصال التقدم للعمليات التي تستغرق وقتًا طويلاً.
>>>>>>> 82edf2d (New md files from RunPod)

### تفاصيل التنفيذ

#### المرحلة 0: إعادة هيكلة عمرية معمارية حاسمة

**التنفيذ الحالي الذي يمثل مشكلة:**
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

**هيكل معماري مُحسّن وعالي الأداء:**
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

هذا التغيير المعماري يوفر:
**تقليل بنسبة 10-20٪ في استعلامات قاعدة البيانات** للرسوم البيانية التي تحتوي على علاقات شائعة (مقارنة بـ 0٪ حاليًا).
**إزالة تكلفة إنشاء الكائنات** لكل طلب.
**تجميع الاتصالات المستمرة وإعادة استخدام العملاء**.
**تحسينات عبر الطلبات** ضمن إطارات زمنية للتخزين المؤقت (TTL).

**قيود مهمة تتعلق بتناسق التخزين المؤقت:**
<<<<<<< HEAD
يؤدي التخزين المؤقت طويل الأجل إلى خطر حدوث بيانات قديمة عندما يتم حذف الكيانات/التصنيفات أو تعديلها في الرسم البياني الأساسي. يوفر التخزين المؤقت الأقل استخدامًا (LRU) مع إطار زمني للتخزين (TTL) توازنًا بين مكاسب الأداء وحداثة البيانات، ولكنه لا يمكنه اكتشاف تغييرات الرسم البياني في الوقت الفعلي.
=======
يؤدي التخزين المؤقت طويل الأجل إلى خطر حدوث بيانات قديمة عندما يتم حذف الكيانات/التصنيفات أو تعديلها في الرسم البياني الأساسي. يوفر التخزين المؤقت الأقل استخدامًا (LRU) مع TTL توازنًا بين مكاسب الأداء وحداثة البيانات، ولكنه لا يمكنه اكتشاف تغييرات الرسم البياني في الوقت الفعلي.
>>>>>>> 82edf2d (New md files from RunPod)

#### المرحلة الأولى: تحسين اجتياز الرسم البياني.

**مشاكل التنفيذ الحالية:**
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

**التنفيذ الأمثل:**
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

#### المرحلة الثانية: حل التسميات المتوازية

**التنفيذ التسلسلي الحالي:**
```python
# INEFFICIENT: Sequential processing
for edge in subgraph:
    s = await self.maybe_label(edge[0])  # Individual query
    p = await self.maybe_label(edge[1])  # Individual query
    o = await self.maybe_label(edge[2])  # Individual query
```

**التنفيذ المتوازي المُحسّن:**
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

#### المرحلة الثالثة: استراتيجية التخزين المؤقت المتقدمة

**ذاكرة تخزين مؤقت LRU مع TTL:**
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

#### المرحلة الرابعة: تحسين الاستعلامات والمراقبة

**جمع مقاييس الأداء:**
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

**مهلة الاستعلام وقاطع الدائرة:**
```python
async def execute_with_timeout(self, query_func, timeout: int = 30):
    try:
        return await asyncio.wait_for(query_func(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"Query timeout after {timeout}s")
        raise GraphRagTimeoutError(f"Query exceeded timeout of {timeout}s")
```

## اعتبارات تناسق ذاكرة التخزين المؤقت

**موازنات بين قدوم البيانات:**
**ذاكرة تخزين مؤقت للتسميات (TTL مدته 5 دقائق):** خطر عرض تسميات الكيانات المحذوفة/المُعادة تسميتها.
**لا يوجد تخزين مؤقت للتضمينات:** غير ضروري - يتم تخزين التضمينات بالفعل لكل استعلام.
**لا يوجد تخزين مؤقت للنتائج:** يمنع النتائج الفرعية غير المستقرة من الرسوم البيانية الناتجة عن الكيانات/العلاقات المحذوفة.

**استراتيجيات التخفيف:**
**قيم TTL محافظة:** الموازنة بين مكاسب الأداء (10-20٪) مع تحديث البيانات.
**خطافات إبطال ذاكرة التخزين المؤقت:** تكامل اختياري مع أحداث تعديل الرسم البياني.
**لوحات مراقبة:** تتبع معدلات نجاح ذاكرة التخزين المؤقت مقابل حوادث عدم الاستقرار.
**سياسات ذاكرة تخزين مؤقت قابلة للتكوين:** السماح بضبط لكل توزيع بناءً على تكرار التعديل.

<<<<<<< HEAD
**تكوين ذاكرة التخزين المؤقت الموصى به بناءً على معدل تعديل الرسم البياني:**
=======
**تكوين ذاكرة التخزين المؤقت الموصى به حسب معدل تعديل الرسم البياني:**
>>>>>>> 82edf2d (New md files from RunPod)
**تعديل مرتفع (>100 تغيير/ساعة):** TTL=60 ثانية، أحجام ذاكرة تخزين مؤقت أصغر.
**تعديل متوسط (10-100 تغيير/ساعة):** TTL=300 ثانية (افتراضي).
**تعديل منخفض (<10 تغيير/ساعة):** TTL=600 ثانية، أحجام ذاكرة تخزين مؤقت أكبر.

## اعتبارات الأمان

**منع حقن الاستعلام:**
التحقق من صحة جميع معرفات الكيانات ومعلمات الاستعلام.
استخدم استعلامات مُعلمات لجميع التفاعلات مع قاعدة البيانات.
تنفيذ حدود تعقيد الاستعلام لمنع هجمات الحرمان من الخدمة.

**حماية الموارد:**
<<<<<<< HEAD
فرض حدود قصوى لحجم الرسم البياني.
=======
فرض حدود قصوى لحجم الرسم البياني الفرعي.
>>>>>>> 82edf2d (New md files from RunPod)
تنفيذ مهلات الاستعلام لمنع استنفاد الموارد.
إضافة مراقبة حدود استخدام الذاكرة.

**التحكم في الوصول:**
الحفاظ على عزل المستخدمين والمجموعات الحالي.
إضافة تسجيل تدقيق للعمليات التي تؤثر على الأداء.
تنفيذ تحديد المعدل للعمليات المكلفة.

## اعتبارات الأداء

### التحسينات المتوقعة في الأداء

**تقليل عدد الاستعلامات:**
الحالي: ~9000+ استعلام للطلب النموذجي.
مُحسَّن: ~50-100 استعلام مجمعة (تقليل بنسبة 98٪).

**تحسينات في وقت الاستجابة:**
اجتياز الرسم البياني: 15-20 ثانية → 3-5 ثوانٍ (أسرع بـ 4-5 مرات).
<<<<<<< HEAD
حل التسميات: 8-12 ثانية → 2-4 ثوانٍ (أسرع بـ 3 مرات).
الاستعلام الإجمالي: 25-35 ثانية → 6-10 ثوانٍ (تحسين بنسبة 3-4 مرات).
=======
حل التسمية: 8-12 ثانية → 2-4 ثوانٍ (أسرع بـ 3 مرات).
الاستعلام الإجمالي: 25-35 ثانية → 6-10 ثوانٍ (تحسين بـ 3-4 مرات).
>>>>>>> 82edf2d (New md files from RunPod)

**كفاءة الذاكرة:**
تمنع أحجام ذاكرة التخزين المؤقت المحددة تسرب الذاكرة.
تقلل الهياكل البيانية الفعالة من البصمة الذاكرة بنسبة ~40٪.
<<<<<<< HEAD
جمع القمامة بشكل أفضل من خلال التنظيف المناسب للموارد.
=======
تحسين جمع البيانات المهملة من خلال التنظيف المناسب للموارد.
>>>>>>> 82edf2d (New md files from RunPod)

**توقعات واقعية للأداء:**
**ذاكرة تخزين مؤقت للتسميات:** تقليل استعلام بنسبة 10-20٪ للرسوم البيانية ذات العلاقات الشائعة.
**تحسين التجميع:** تقليل استعلام بنسبة 50-80٪ (التحسين الأساسي).
**تحسين عمر الكائن:** إزالة النفقات العامة لإنشاء الطلبات لكل طلب.
<<<<<<< HEAD
**تحسين إجمالي:** تحسين وقت الاستجابة بنسبة 3-4 مرات بشكل أساسي من خلال التجميع.
=======
**تحسين إجمالي:** تحسين وقت الاستجابة بـ 3-4 مرات بشكل أساسي من خلال التجميع.
>>>>>>> 82edf2d (New md files from RunPod)

**تحسينات قابلية التوسع:**
دعم رسوم بيانية معرفية أكبر بـ 3-5 مرات (محدود بمتطلبات تناسق ذاكرة التخزين المؤقت).
سعة أعلى للطلبات المتزامنة بـ 3-5 مرات.
استخدام أفضل للموارد من خلال إعادة استخدام الاتصالات.

### مراقبة الأداء

**مقاييس في الوقت الفعلي:**
أوقات تنفيذ الاستعلام حسب نوع العملية.
نسب نجاح ذاكرة التخزين المؤقت وفعاليتها.
استخدام مجموعة اتصالات قاعدة البيانات.
<<<<<<< HEAD
استخدام الذاكرة وتأثير جمع القمامة.
=======
استخدام الذاكرة وتأثير جمع البيانات المهملة.
>>>>>>> 82edf2d (New md files from RunPod)

**قياس الأداء:**
اختبارات انحدار الأداء الآلية
اختبارات التحميل باستخدام أحجام بيانات واقعية
معايير مقارنة مقابل التنفيذ الحالي

## استراتيجية الاختبار

<<<<<<< HEAD
### اختبارات الوحدة
اختبار المكونات الفردية للتنقل والتخزين المؤقت وحل التسميات
محاكاة تفاعلات قاعدة البيانات لأغراض اختبار الأداء
اختبار إزالة التخزين المؤقت وانتهاء صلاحية TTL
معالجة الأخطاء وسيناريوهات المهلة الزمنية

### اختبار التكامل
اختبار شامل لاستعلامات GraphRAG مع التحسينات
=======
### اختبار الوحدة
اختبار المكونات الفردية للتنقل والتخزين المؤقت وحل التسميات
محاكاة تفاعلات قاعدة البيانات لأغراض اختبار الأداء
اختبار إزالة التخزين المؤقت وانتهاء صلاحية TTL
معالجة الأخطاء وسيناريوهات المهلة

### اختبار التكامل
اختبار شامل لاستعلام GraphRAG مع التحسينات
>>>>>>> 82edf2d (New md files from RunPod)
اختبار تفاعلات قاعدة البيانات باستخدام بيانات حقيقية
معالجة الطلبات المتزامنة وإدارة الموارد
اكتشاف تسرب الذاكرة والتحقق من تنظيف الموارد

### اختبار الأداء
اختبارات قياس الأداء مقابل التنفيذ الحالي
<<<<<<< HEAD
اختبارات التحميل بأحجام وتعقيدات رسومية مختلفة
=======
اختبارات التحميل بأحجام وتعقيدات رسوم بيانية مختلفة
>>>>>>> 82edf2d (New md files from RunPod)
اختبارات الضغط لحدود الذاكرة والاتصالات
اختبارات الانحدار لتحسينات الأداء

### اختبار التوافق
التحقق من توافق واجهة برمجة تطبيقات GraphRAG الحالية
<<<<<<< HEAD
الاختبار مع قواعد بيانات رسومية مختلفة
=======
الاختبار مع قواعد بيانات رسوم بيانية مختلفة
>>>>>>> 82edf2d (New md files from RunPod)
التحقق من دقة النتائج مقارنة بالتنفيذ الحالي

## خطة التنفيذ

### نهج التنفيذ المباشر
نظرًا لأن واجهات برمجة التطبيقات مسموح لها بالتغيير، قم بتنفيذ التحسينات مباشرةً دون تعقيد الترحيل:

<<<<<<< HEAD
1. **استبدال `follow_edges`:** أعد كتابة باستخدام تجول دفعي تكراري
=======
1. **استبدال `follow_edges`:** أعد كتابة باستخدام تجول مجمّع تكراري
>>>>>>> 82edf2d (New md files from RunPod)
2. **تحسين `get_labelgraph`:** قم بتنفيذ حل تسميات متوازي
3. **إضافة GraphRag طويل الأمد:** قم بتعديل المعالج للحفاظ على مثيل دائم
4. **تنفيذ التخزين المؤقت للتسميات:** أضف ذاكرة تخزين مؤقت LRU مع TTL إلى فئة GraphRag

### نطاق التغييرات
<<<<<<< HEAD
**فئة الاستعلام:** استبدل ~50 سطرًا في `follow_edges`، وأضف ~30 سطرًا لمعالجة الدفعات
=======
**فئة الاستعلام:** استبدل ~50 سطرًا في `follow_edges`، وأضف ~30 سطرًا لمعالجة الدُفعات
>>>>>>> 82edf2d (New md files from RunPod)
**فئة GraphRag:** أضف طبقة التخزين المؤقت (~40 سطرًا)
**فئة المعالج:** قم بتعديل لاستخدام مثيل GraphRag دائم (~20 سطرًا)
**الإجمالي:** ~140 سطرًا من التغييرات المركزة، معظمها داخل الفئات الحالية

## الجدول الزمني

<<<<<<< HEAD
**الأسبوع 1: التنفيذ الأساسي**
استبدل `follow_edges` بالتجول الدفعي التكراري
=======
**الأسبوع الأول: التنفيذ الأساسي**
استبدل `follow_edges` بتجول تكراري مجمّع
>>>>>>> 82edf2d (New md files from RunPod)
قم بتنفيذ حل تسميات متوازي في `get_labelgraph`
أضف مثيل GraphRag طويل الأمد إلى المعالج
قم بتنفيذ طبقة التخزين المؤقت للتسميات

<<<<<<< HEAD
**الأسبوع 2: الاختبار والتكامل**
اختبارات الوحدة لمنطق التجول والتخزين المؤقت الجديد
قياس أداء مقابل التنفيذ الحالي
اختبار التكامل مع بيانات رسومية حقيقية
مراجعة التعليمات البرمجية والتحسين

**الأسبوع 3: النشر**
نشر التنفيذ المحسن
مراقبة تحسينات الأداء
ضبط TTL للتخزين المؤقت وأحجام الدفعات بناءً على الاستخدام الفعلي
=======
**الأسبوع الثاني: الاختبار والتكامل**
اختبارات الوحدة لمنطق التجول والتخزين المؤقت الجديد
قياس أداء مقابل التنفيذ الحالي
اختبارات التكامل مع بيانات الرسم البياني الحقيقية
مراجعة التعليمات البرمجية والتحسين

**الأسبوع الثالث: النشر**
نشر التنفيذ المحسن
مراقبة تحسينات الأداء
ضبط TTL للتخزين المؤقت وأحجام الدُفعات بناءً على الاستخدام الفعلي
>>>>>>> 82edf2d (New md files from RunPod)

## أسئلة مفتوحة

**تجميع الاتصالات بقاعدة البيانات:** هل يجب علينا تنفيذ تجميع اتصالات مخصص أم الاعتماد على تجميع عملاء قاعدة البيانات الحالي؟
**استمرارية التخزين المؤقت:** هل يجب أن تستمر ذاكرات التخزين المؤقت للتسميات والتضمينات عبر عمليات إعادة تشغيل الخدمة؟
**التخزين المؤقت الموزع:** بالنسبة لنشرات متعددة المثيلات، هل يجب علينا تنفيذ تخزين مؤقت موزع باستخدام Redis/Memcached؟
**تنسيق نتيجة الاستعلام:** هل يجب علينا تحسين التمثيل الداخلي للثلاثيات لتحسين كفاءة الذاكرة؟
**تكامل المراقبة:** ما هي المقاييس التي يجب عرضها على أنظمة المراقبة الحالية (Prometheus، إلخ)؟

## المراجع

[التنفيذ الأصلي لـ GraphRAG](trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py)
<<<<<<< HEAD
[مبادئ معمارية TrustGraph](architecture-principles.md)
[مواصفات إدارة المجموعة](collection-management.md)
=======
[مبادئ بنية TrustGraph](architecture-principles.md)
[مواصفات إدارة المجموعات](collection-management.md)
>>>>>>> 82edf2d (New md files from RunPod)
