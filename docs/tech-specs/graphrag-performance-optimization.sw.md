<<<<<<< HEAD
# Vipimo vya Ufanisi wa GraphRAG kwa Uboreshaji wa Kawaida
=======
# Vipimo vya Ufanisi wa GraphRAG kwa Uboreshaji wa Kiufundi
>>>>>>> 82edf2d (New md files from RunPod)

## Maelezo

<<<<<<< HEAD
Hati hii inaeleza uboreshaji wa kina wa utendaji wa algorithm ya GraphRAG (Graph Retrieval-Augmented Generation) katika TrustGraph. Utaratibu wa sasa una matatizo makubwa ya utendaji ambayo yanapunguza uwezo wa kupanuka na wakati wa majibu. Hati hii inashughulikia maeneo manne makuu ya uboreshaji:

1. **Uboreshaji wa Ufuatiliaji wa Grafu**: Ondoa maswali ya hivi karibuni ya hivi karibuni ya hivi karibuni na tekeleza utafutaji wa grafu wa kikundi
2. **Uboreshaji wa Utatuzi wa Lebo**: Badilisha upekuzi wa hivi karibuni wa lebo na shughuli za sambamba/za kikundi
3. **Uboreshaji wa Mkakati wa Kumbukumbu**: Tekeleza kumbukumbu mahiri na kuondoa kwa LRU na utabiri
4. **Uboreshaji wa Ulipaji**: Ongeza kumbukumbu ya matokeo na kumbukumbu ya uingizaji kwa kuboresha wakati wa majibu

## Lengo

**Punguza Kiasi cha Maswali ya Hivi Karibuni**: Pata kupunguzwa kwa 50-80% katika jumla ya maswali ya hivi karibuni kupitia kikundi na kumbukumbu
**Boresha Wakati wa Majibu**: Lenga ujenzi wa subgrafu wa haraka 3-5x na utatuzi wa lebo wa haraka 2-3x
**Boresha Uwezo wa Kupanuka**: Unga grafu kubwa za maarifa na usimamizi bora wa kumbukumbu
**Dumishe Usahihi**: Dumishe utendaji na ubora wa matokeo ya GraphRAG iliyopo
**Wezesha Ulinganifu**: Boresha uwezo wa usindikaji sambamba kwa maombi mengi ya sambamba
**Punguza Uzito wa Kumbukumbu**: Tekeleza miundo ya data na usimamizi wa kumbukumbu bora
**Ongeza Ufuatiliaji**: Jumuisha metriki za utendaji na uwezo wa ufuatiliaji
**Hakikisha Utendaji**: Ongeza ushughulikiaji sahihi wa makosa na mitambo ya muda
=======
Maelekezo haya yanaelezea uboreshaji wa kina wa utendaji kwa algorithm ya GraphRAG (Graph Retrieval-Augmented Generation) katika TrustGraph. Utaratibu wa sasa una matatizo makubwa ya utendaji ambayo yanapunguza uwezo wa kupanuka na wakati wa majibu. Maelekezo haya yanaangazia maeneo manne makuu ya uboreshaji:

1. **Uboreshaji wa Ufuatiliaji wa Grafu**: Ondoa maswali ya hivi karibuni ya hivi karibuni ya hivi karibuni na tekeleza utafutaji wa grafu wa kikundi.
2. **Uboreshaji wa Utatuzi wa Lebo**: Badilisha upekuzi wa lebo wa mfululizo na shughuli za sambamba/za kikundi.
3. **Uboreshaji wa Mkakati wa Kumbukumbu**: Tekeleza kumbukumbu mahiri na kuondoa kwa LRU na utabiri.
4. **Uboreshaji wa Ulipaji**: Ongeza kumbukumbu ya matokeo na kumbukumbu ya uingizaji kwa kuboresha wakati wa majibu.

## Lengo

**Punguza Kiasi cha Maswali ya Hivi Karibuni**: Pata kupunguzwa kwa 50-80% katika jumla ya maswali ya hivi karibuni kupitia kikundi na kumbukumbu.
**Boresha Wakati wa Majibu**: Lenga ujenzi wa subgraph wa haraka 3-5x na utatuzi wa lebo wa haraka 2-3x.
**Boresha Uwezo wa Kupanuka**: Unga grafu kubwa za maarifa na usimamizi bora wa kumbukumbu.
**Dumishe Usahihi**: Dumishe utendaji na ubora wa matokeo ya GraphRAG iliyopo.
**Wezesha Ulinganifu**: Boresha uwezo wa usindikaji sambamba kwa maombi mengi ya sambamba.
**Punguza Uzito wa Kumbukumbu**: Tekeleza miundo ya data na usimamizi wa kumbukumbu bora.
**Ongeza Ufuatiliaji**: Jumuisha metriki za utendaji na uwezo wa ufuatiliaji.
**Hakikisha Utendaji**: Ongeza ushughulikiaji sahihi wa makosa na mitambo ya muda.
>>>>>>> 82edf2d (New md files from RunPod)

## Asili

Utaratibu wa sasa wa GraphRAG katika `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py` una masuala muhimu ya utendaji ambayo yanaathiri sana uwezo wa kupanuka wa mfumo:

### Matatizo ya Sasa ya Utendaji

**1. Ufuatiliaji Usio na Ufanisi wa Grafu (kitendaji cha `follow_edges`, mistari 79-127)**
<<<<<<< HEAD
Hufanya maswali 3 tofauti ya hivi karibuni kwa kila kitu kwa kila kiwango cha kina
Mfumo wa swali: maswali ya msingi ya mada, maswali ya msingi ya tabia, na maswali ya msingi ya kitu kwa kila kitu
Hakuna kikundi: Kila swali huchakata kitu kimoja wakati mmoja
Hakuna utambuzi wa mzunguko: Inaweza kurudi kwenye nodi sawa mara nyingi
Utaratibu wa hivi karibuni bila kumbukumbu husababisha utata wa kielelekevu
Utata wa wakati: O(vitabu × urefu_max_ya_njia × triple_limit³)

**2. Utatuzi wa Hivi Karibuni wa Lebo (kitendaji cha `get_labelgraph`, mistari 144-171)**
Huchakata kila sehemu ya tatu (mhusika, tabia, kitu) kwa hivi karibuni
Kila wito wa `maybe_label` inaweza kusababisha swali la hivi karibuni la hivi karibuni
Hakuna utekelezaji sambamba au kikundi cha maswali ya lebo
Hupelekea hadi simu 3 × ya hivi karibuni ya hivi karibuni ya hivi karibuni.

**3. Mkakati wa Kumbukumbu wa Msingi (kitendaji cha `maybe_label`, mistari 62-77)**
Kumbukumbu rahisi ya kamusi bila mipaka ya saizi au TTL
Hakuna sera ya kuondoa kumbukumbu inayosababisha ukuaji usio na kikomo wa kumbukumbu
Kupoteza kumbukumbu hutuma maswali ya hivi karibuni ya hivi karibuni ya hivi karibuni
Hakuna utabiri au uongezaji mahiri wa kumbukumbu

**4. Mfumo Usio na Ufanisi wa Maswali**
Maswali ya ufanano wa vekta ya kitu hayahifadhiwi kati ya maombi sawa
Hakuna kumbukumbu ya matokeo kwa mifumo ya swali iliyorudiwa
Uboreshaji wa swali unaokosekana kwa mifumo ya kawaida ya ufikiaji

**5. Masuala Muhimu ya Maisha ya Kitu (`rag.py:96-102`)**
**Kitu cha GraphRag kinaundwa kwa kila ombi**: Toleo jipya huundwa kwa kila swali, na kupoteza faida zote za kumbukumbu
**Kitu cha swali kina muda mfupi sana**: Huundwa na kuharibiwa ndani ya utekelezaji wa swali moja (mistari 201-207)
**Kumbukumbu ya lebo inarejeshwa kwa kila ombi**: Uongezaji wa kumbukumbu na maarifa yaliyokusanywa yanapotea kati ya maombi
**Upeo wa upya wa mteja**: Wateja wa hivi karibuni wanaweza kuanzishwa tena kwa kila ombi
**Hakuna uboreshaji wa kati ya maombi**: Haiwezi kufaidika na mifumo ya swali au ushirikishwaji wa matokeo
=======
Hufanya maswali 3 tofauti ya hivi karibuni kwa kila kitu kwa kila ngazi ya kina.
Mfumo wa swali: maswali ya msingi ya mada, maswali ya msingi ya tabia, na maswali ya msingi ya kitu kwa kila kitu.
Hakuna kikundi: Kila swali huchakata kitu kimoja wakati mmoja.
Hakuna utambuzi wa mzunguko: Inaweza kurudi kwenye nodi sawa mara nyingi.
Utaratibu wa hivi karibuni bila kumbukumbu husababisha utata wa kielelekeo.
Utata wa muda: O(vitabu × urefu_max_wa_njia × kikomo_cha_triple³)

**2. Utatuzi wa Msingi wa Lebo (kitendaji cha `get_labelgraph`, mistari 144-171)**
Huchakata kila sehemu ya triple (mhusika, tabia, kitu) kwa utaratibu.
Kila wito wa `maybe_label` inaweza kusababisha swali la hivi karibuni.
Hakuna utekelezaji sambamba au kikundi cha maswali ya lebo.
Hupelekea hadi simu 3 × ya hivi karibuni ya mtu binafsi ya hivi karibuni.

**3. Mkakati wa Kumbukumbu ya Msingi (kitendaji cha `maybe_label`, mistari 62-77)**
Kumbukumbu rahisi ya kamusi bila mipaka ya ukubwa au TTL.
Hakuna sera ya kuondoa kumbukumbu inayosababisha ukuaji usio na kikomo wa kumbukumbu.
Kupoteza kumbukumbu hutuma maswali ya hivi karibuni ya mtu binafsi ya hivi karibuni.
Hakuna utabiri au uongezaji mahiri wa kumbukumbu.

**4. Mfumo Usio na Ufanisi wa Maswali**
Maswali ya ufanano wa vekta ya kitu hayahifadhiwi kati ya maombi sawa.
Hakuna kumbukumbu ya matokeo kwa mifumo ya swali iliyorudiwa.
Uboreshaji wa swali unaokosekana kwa mifumo ya kawaida ya ufikiaji.

**5. Masuala Muhimu ya Muda wa Kitu (`rag.py:96-102`)**
**Kitu cha GraphRag kinaundwa kila maombi**: Mfano mpya huundwa kwa kila swali, ukipoteza faida zote za kumbukumbu.
**Kitu cha swali kina muda mfupi sana**: Huundwa na kuharibiwa ndani ya utekelezaji wa swali moja (mistari 201-207).
**Kumbukumbu ya lebo inarejeshwa kwa kila maombi**: Uongezaji wa kumbukumbu na maarifa yaliyokusanywa hupotea kati ya maombi.
**Upekee wa upya wa mteja**: Wateja wa hivi karibuni wanaweza kuanzishwa tena kwa kila maombi.
**Hakuna uboreshaji wa maombi**: Haiwezi kufaidika na mifumo ya swali au ushirikishwaji wa matokeo.
>>>>>>> 82edf2d (New md files from RunPod)

### Uchambuzi wa Athari ya Utendaji

Hali mbaya zaidi ya sasa kwa swali la kawaida:
<<<<<<< HEAD
**Upekuzi wa Kitu**: swali 1 la ufanano wa vekta
**Ufuatiliaji wa Grafu**: vitu × urefu_max_ya_njia × 3 × maswali ya hivi karibuni ya hivi karibuni ya hivi karibuni
**Utatuzi wa Lebo**: maswali ya hivi karibuni ya hivi karibuni ya hivi karibuni ya subgrafu_size × 3

Kwa vigezo chache (vitu 50, urefu wa njia 2, kikomo cha triplet 30, saizi ya subgraph 150):
**Maswali ya chini**: 1 + (50 × 2 × 3 × 30) + (150 × 3) = **maswali 9,451 ya hifadhidata**
**Wakati wa majibu**: Sekunde 15-30 kwa vielelezo vya saizi ya wastani
**Matumizi ya kumbukumbu**: Ukubwa wa kumbukumbu unaoongezeka bila kikomo baada ya muda
**Ufanisi wa kumbukumbu**: 0% - kumbukumbu hurejeshwa kila ombi
=======
**Upekuzi wa Kitu**: swali 1 la ufanano wa vekta.
**Ufuatiliaji wa Grafu**: vitabu × urefu_max_wa_njia × 3 × maswali ya hivi karibuni ya triple.
**Utatuzi wa Lebo**: maswali ya mtu binafsi ya hivi karibuni ya lebo ya subgraph_size × 3.

Kwa vigezo chaguvi (vitu 50, urefu wa njia 2, kikomo cha triplet 30, saizi ya subgraph 150):
**Maswali ya chini**: 1 + (50 × 2 × 3 × 30) + (150 × 3) = **maswali 9,451 ya hifadhidata**
**Wakati wa majibu**: sekunde 15-30 kwa vielelezo vya saizi ya wastani
**Matumizi ya kumbukumbu**: ukuaji usio na kikomo wa kumbukumbu kwa muda
**Ufanisi wa kumbukumbu**: 0% - kumbukumbu hurekebishwa kila mara
>>>>>>> 82edf2d (New md files from RunPod)
**Utozo wa kuunda vitu**: Vitu vya GraphRag + Query vinaundwa/vinaharibiwa kwa kila ombi

Maelezo haya yanaangazia pengo hizi kwa kutumia maswali ya kikundi, uhifadhi mahiri, na usindikaji wa sambamba. Kwa kuboresha mifumo ya maswali na ufikiaji wa data, TrustGraph inaweza:
Kusaidia vielelezo vya maarifa vya kiwango cha shirika na mamilioni ya vitu
Kutoa wakati wa majibu ya chini ya sekunde kwa maswali ya kawaida
Kushughulikia maombi mamia ya GraphRAG kwa wakati mmoja
Kuongezeka kwa ufanisi na saizi na utata wa vielelezo

## Muundo wa Kiufundi

### Usanifu

Uboreshaji wa utendaji wa GraphRAG unahitaji vipengele hivi vya kiufundi:

#### 1. **Urekebishaji wa Usanifu wa Muda wa Vitu**
<<<<<<< HEAD
   **Fanya GraphRag iwe na muda mrefu**: Hamisha mfano wa GraphRag hadi ngazi ya Processor ili kudumu katika maombi
   **Ondoa kumbukumbu**: Dumishe kumbukumbu ya lebo, kumbukumbu ya uingizaji, na kumbukumbu ya matokeo ya swali kati ya maombi
   **Boresha kitu cha Swali**: Rekebisha Swali ili iwe mfumo wa utekelezaji mwepesi, sio chombo cha data
   **Usaidizi wa muunganisho**: Dumishe miunganisho ya mteja wa hifadhidata katika maombi
=======
   **Fanya GraphRag iwe ya muda mrefu**: Hamisha mfano wa GraphRag hadi ngazi ya Processor ili kudumu katika ombi
   **Ondoa kumbukumbu**: Dumishe kumbukumbu ya lebo, kumbukumbu ya uingizaji, na kumbukumbu ya matokeo ya swali kati ya ombi
   **Boresha kitu cha Swali**: Rekebisha Swali ili iwe muktadha wa utekelezaji mwepesi, sio chombo cha data
   **Usaidizi wa muunganisho**: Dumishe miunganisho ya mteja wa hifadhidata katika ombi
>>>>>>> 82edf2d (New md files from RunPod)

   Moduli: `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` (iliyorekebishwa)

#### 2. **Injini Iliyoboreshwa ya Ufuatiliaji wa Vielelezo**
   Badilisha `follow_edges` ya kurudia na utafutaji wa upana wa mara kwa mara
   Tekeleza usindikaji wa kikundi wa vitu katika kila ngazi ya ufuatiliaji
   Ongeza ugunduzi wa mzunguko kwa kufuatilia nodi zilizotembelewa
   Jumuisha kumalizika mapema wakati mipaka inafikiwa

   Moduli: `trustgraph-flow/trustgraph/retrieval/graph_rag/optimized_traversal.py`

<<<<<<< HEAD
#### 3. **Mfumo wa Ufafanuzi wa Lebo Sambamba**
   Kikundi maswali ya lebo kwa vitu vingi kwa wakati mmoja
   Tekeleza mifumo ya async/await kwa ufikiaji sambamba wa hifadhidata
   Ongeza upakiaji wa akili kwa mifumo ya kawaida ya lebo
   Jumuisha mikakati ya ukausha wa kumbukumbu ya lebo

   Moduli: `trustgraph-flow/trustgraph/retrieval/graph_rag/label_resolver.py`

#### 4. **Nafasi ya Kumbukumbu ya Lebo Iliyohifadhiwa**
   Kumbukumbu ya LRU na TTL fupi kwa lebo pekee (dakika 5) ili kusawazisha utendaji na uthabiti
   Fuatilia metriki na uwiano wa hit
   **Hakuna ukaushaji wa uingizaji**: Tayari umehifadhiwa kwa kila swali, hakuna faida ya kati ya maswali
   **Hakuna ukaushaji wa matokeo ya swali**: Kutokana na wasiwasi wa uthabiti wa mabadiliko ya vielelezo
=======
#### 3. **Mfumo wa Suluhisho la Lebo Sambamba**
   Kikundi maswali ya lebo kwa vitu vingi kwa wakati mmoja
   Tekeleza mifumo ya async/await kwa ufikiaji sambamba wa hifadhidata
   Ongeza utabiri wa kupata kwa mifumo ya kawaida ya lebo
   Jumuisha mikakati ya kupasha joto ya kumbukumbu ya lebo

   Moduli: `trustgraph-flow/trustgraph/retrieval/graph_rag/label_resolver.py`

#### 4. **Nafasi Hifadhi ya Lebo**
   Kumbukumbu ya LRU na TTL fupi kwa lebo pekee (dakika 5) ili kusawazisha utendaji dhidi ya uthabiti
   Fuatilia metriki na uwiano wa hit
   **Hakuna kumbukumbu ya uingizaji**: Tayari imehifadhiwa kwa kila swali, hakuna faida ya kati ya maswali
   **Hakuna kumbukumbu ya matokeo ya swali**: Kutokana na wasiwasi wa uthabiti wa mabadiliko ya vielelezo
>>>>>>> 82edf2d (New md files from RunPod)

   Moduli: `trustgraph-flow/trustgraph/retrieval/graph_rag/cache_manager.py`

#### 5. **Mfumo wa Uboreshaji wa Swali**
   Uchambuzi na mapendekezo ya uboreshaji wa mfumo wa swali
   Mratibu wa swali la kikundi kwa ufikiaji wa hifadhidata
   Uunganisho wa mabwawa na usimamaji wa muda wa swali
   Ufuatiliaji wa utendaji na ukusanyaji wa metriki

   Moduli: `trustgraph-flow/trustgraph/retrieval/graph_rag/query_optimizer.py`

### Mifano ya Data

#### Hali Iliyoboreshwa ya Ufuatiliaji wa Vielelezo

<<<<<<< HEAD
Injini ya ufuatiliaji inahifadhi hali ili kuepuka shughuli za ziada:
=======
Injini ya ufuatiliaji inadumisha hali ili kuepuka shughuli za ziada:
>>>>>>> 82edf2d (New md files from RunPod)

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

Mbinu hii inaruhusu:
<<<<<<< HEAD
Uchunguzi wa haraka wa mzunguko kupitia kufuatilia vitu vilivyotembelewa
Maandalizi ya maswali kwa wingi katika kila ngazi ya utafutaji
Usimamizi wa hali unaohifadhi kumbukumbu
Kukomesha mapema wakati mipaka ya ukubwa inafikiwa
=======
Uchunguzi wa haraka wa mzunguko kupitia kufuatilia vitu vilivyotembelewa.
Maandalizi ya maswali kwa wingi katika kila ngazi ya utafutaji.
Usimamizi wa hali unaohifadhi kumbukumbu.
Kukomesha mapema wakati mipaka ya ukubwa inafikiwa.
>>>>>>> 82edf2d (New md files from RunPod)

#### Muundo Ulioboreshwa wa Kumbukumbu (Cache)

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

<<<<<<< HEAD
#### Muundo wa Maswali ya Kundi
=======
#### Muundo wa Maswali kwa Wingi
>>>>>>> 82edf2d (New md files from RunPod)

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

### API

#### API mpya:

**API ya GraphTraversal**
```python
async def optimized_follow_edges_batch(
    entities: List[str],
    max_depth: int,
    triple_limit: int,
    max_subgraph_size: int
) -> Set[Tuple[str, str, str]]
```

**API ya Utatuzi wa Lebo za Kundi**
```python
async def resolve_labels_batch(
    entities: List[str],
    cache_manager: CacheManager
) -> Dict[str, str]
```

**API ya Usimamizi wa Kumbukumbu (Cache)**
```python
class CacheManager:
    async def get_or_fetch_label(self, entity: str) -> str
    async def get_or_fetch_embeddings(self, query: str) -> List[float]
    async def cache_query_result(self, query_hash: str, result: Any, ttl: int)
    def get_cache_statistics(self) -> CacheStatistics
```

#### API Zilizobadilishwa:

**GraphRag.query()** - Imeboreshwa kwa matumizi bora:
Ongeza parameter ya `cache_manager` kwa udhibiti wa kumbukumbu.
Jumuisha thamani ya kurudiwa ya `performance_metrics`.
Ongeza parameter ya `query_timeout` kwa uaminifu.

<<<<<<< HEAD
**Darasa la `Query`** - Limepangwa upya kwa usindikaji wa jumla:
Badilisha usindikaji wa kila kitu kwa shughuli za jumla.
Ongeza menejeri wa muktadha wa async kwa usafi wa rasilimali.
Jumuisha miongozo ya maendeleo kwa operesheni za muda mrefu.

### Maelezo ya Utendaji

#### Awamu ya 0: Urekebishaji Muhimu wa Muundo na Muda wa Maisha
=======
**Kifaa cha `Query`** - Kimepangwa upya kwa usindikaji wa jumla:
Badilisha usindikaji wa kila kitu kwa shughuli za jumla.
Ongeza menejimenti ya muktadha wa async kwa usafi wa rasilimali.
Jumuisha miongozo ya maendeleo kwa shughuli za muda mrefu.

### Maelezo ya Utendaji

#### Awamu ya 0: Urekebishaji Muhimu wa Muundo na Muda
>>>>>>> 82edf2d (New md files from RunPod)

**Utendaji Sasa Usiofaa:**
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

<<<<<<< HEAD
**Muundo Ulioboreshwa na Umeundwa Kudumu:**
=======
**Muundo Uliounganishwa Vizuri na Umeundwa kwa Muda Mrefu:**
>>>>>>> 82edf2d (New md files from RunPod)
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

Mabadiliko haya ya usanifu yanatoa:
**Punguuzo la 10-20% la maswali ya hifadhidata** kwa grafu zilizo na uhusiano wa kawaida (kulinganisha na 0% kwa sasa)
<<<<<<< HEAD
**Kuondolewa kwa gharama ya ziada ya uundaji wa vitu** kwa kila ombi
**Uunganishaji wa kudumu na matumizi ya upya** kwa wateja
**Uboreshaji wa ombi hadi ombi** ndani ya vipindi vya muda wa kuhifadhi (TTL)

**Kizuia Muhimu cha Utangamano wa Kumbukumbu:**
Uhifadhi wa muda mrefu unaweza kusababisha data kuwa potofu wakati vitu/lebo zinafutwa au kubadilishwa katika grafu iliyoko. Kumbukumbu ya LRU yenye TTL hutoa usawa kati ya faida za utendaji na usafi wa data, lakini haiwezi kuchunguza mabadiliko ya grafu ya wakati halisi.
=======
**Kuondolewa kwa gharama ya utengenezaji wa kitu** kwa kila ombi
**Uunganishaji wa kudumu na matumizi ya mteja tena**
**Uboreshaji wa ombi hadi ombi** ndani ya vipindi vya muda wa kuhifadhi (TTL)

**Kizuia Muhimu cha Utangamano wa Kumbukumbu:**
Uhifadhi wa muda mrefu unaweza kusababisha hatari ya data kuwa potofu wakati vitu/lebo zinafutwa au kubadilishwa katika grafu iliyoko. Kumbukumbu ya LRU yenye TTL hutoa usawa kati ya faida za utendaji na uongevu wa data, lakini haiwezi kuchunguza mabadiliko ya grafu ya wakati halisi.
>>>>>>> 82edf2d (New md files from RunPod)

#### Awamu ya 1: Uboreshaji wa Ufuatiliaji wa Grafu

**Matatizo ya Utendaji wa Sasa:**
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

**Utekelezaji Ulioboreshwa:**
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

#### Awamu ya 2: Utatuzi wa Lebo Sambamba

<<<<<<< HEAD
**Utendaji wa Sasa wa Mfululizo:**
=======
**Utaratibu wa Sasa wa Utendaji:**
>>>>>>> 82edf2d (New md files from RunPod)
```python
# INEFFICIENT: Sequential processing
for edge in subgraph:
    s = await self.maybe_label(edge[0])  # Individual query
    p = await self.maybe_label(edge[1])  # Individual query
    o = await self.maybe_label(edge[2])  # Individual query
```

**Utekelezaji Ufuatao Mfumo Sambamba Uliorekebishwa:**
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

<<<<<<< HEAD
#### Awamu ya 3: Mkakati wa Kupanua Data (Caching) wa Juu

**Kupanua Data (Cache) la LRU pamoja na TTL:**
=======
#### Awamu ya 3: Mbinu Iliyoboreshwa ya Kuhifadhi Data

**Kifaa cha Kuhifadhi Data cha LRU (Least Recently Used) pamoja na TTL (Time To Live):**
>>>>>>> 82edf2d (New md files from RunPod)
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

<<<<<<< HEAD
#### Awamu ya 4: Ubora wa Ufuatiliaji na Ufuatiliaji
=======
#### Awamu ya 4: Ubora wa Ufuatiliaji na Usimamizi
>>>>>>> 82edf2d (New md files from RunPod)

**Ukusanyaji wa Vipimo vya Utendaji:**
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

**Mipangilio ya Muda wa Muda na Mfumo wa Kuzuia:**
```python
async def execute_with_timeout(self, query_func, timeout: int = 30):
    try:
        return await asyncio.wait_for(query_func(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"Query timeout after {timeout}s")
        raise GraphRagTimeoutError(f"Query exceeded timeout of {timeout}s")
```

<<<<<<< HEAD
## Mawasilisho ya Ulinganishaji wa Kumbukumbu (Cache)

**Ulinganishaji wa Uharibifu wa Data:**
**Kumbukumbu ya lebo (TTL ya dakika 5)**: Hatari ya kuonyesha lebo za vitu ambazo zimefutwa/kubadilishwa
**Hakuna uwekaji kumbukumbu wa embeddings**: Haihitajiki - embeddings tayari zimehifadhiwa kwa kila swali
**Hakuna uwekaji kumbukumbu wa matokeo**: Inazuia matokeo ya subgrafu ya zamani kutoka kwa vitu/uhusiano ambao wamefutwa

**Mikakati ya Kupunguza Madhara:**
**Manufaa ya TTL ya kihafidhia:** Kusawazisha faida za utendaji (10-20%) na usafi wa data
**Viunganishi vya kutengua kumbukumbu:** Uunganishi wa hiari na matukio ya mabadiliko ya grafu
**Dashibodi za ufuatiliaji:** Kufuatilia viwango vya hit ya kumbukumbu dhidi ya matukio ya usafi
**Mawasilisho ya kumbukumbu yanayoweza kusanidi:** Kuruhusu urekebishaji kwa kila usakinishaji kulingana na masafa ya mabadiliko

**Mawasilisho Yanayopendekezwa ya Kumbukumbu Kulingana na Kasi ya Mabadiliko ya Grafu:**
**Mabadiliko ya juu (>100 mabadiliko/saa)**: TTL=60s, saizi ndogo za kumbukumbu
**Mabadiliko ya wastani (10-100 mabadiliko/saa)**: TTL=300s (ya kawaida)
**Mabadiliko ya chini (<10 mabadiliko/saa)**: TTL=600s, saizi kubwa za kumbukumbu

## Mawasilisho ya Usalama

**Kuzuia Uingizwaji wa Swali:**
=======
## Mawasilisho ya Ulinganishaji wa Hifadhi (Cache)

**Ulinganishaji wa Uharibifu wa Data:**
**Hifadhi ya lebo (TTL ya dakika 5)**: Hatari ya kuonyesha lebo za vitu ambazo zimefutwa/kubadilishwa
**Hakuna uhifadhi wa embeddings**: Haihitajiki - embeddings tayari zimehifadhiwa kwa kila swali
**Hakuna uhifadhi wa matokeo**: Inazuia matokeo ya subgrafu ya zamani kutoka kwa vitu/uhusiano ambao umeondolewa

**Mikakati ya Kupunguza Madhara:**
**Manufaa ya TTL ya kiuchunguzi:** Kusawazisha faida za utendaji (10-20%) na usafi wa data
**Viunganishi vya kutengua hifadhi:** Unganisho wa hiari na matukio ya mabadiliko ya grafu
**Dashibodi za ufuatiliaji:** Kufuatilia viwango vya hit ya hifadhi dhidi ya matukio ya uharibifu
**Mbinu za hifadhi zinazoweza kusanidi:** Kuruhusu urekebishaji wa kila usakinishaji kulingana na masafa ya mabadiliko

**Mazingatio Yanayopendekezwa ya Hifadhi Kulingana na Kasi ya Mabadiliko ya Grafu:**
**Mabadiliko ya juu (>100 mabadiliko/saa)**: TTL=60s, saizi ndogo za hifadhi
**Mabadiliko ya wastani (10-100 mabadiliko/saa)**: TTL=300s (ya kawaida)
**Mabadiliko ya chini (<10 mabadiliko/saa)**: TTL=600s, saizi kubwa za hifadhi

## Masuala ya Usalama

**Kuzuia Uingizwaji wa Maswali:**
>>>>>>> 82edf2d (New md files from RunPod)
Thibitisha kitambulisho vyote vya vitu na vigezo vya swali
Tumia maswali yaliyoparametishwa kwa mwingiliano wote wa hifadhidata
Tekeleza mipaka ya utata wa swali ili kuzuia mashambulizi ya aina ya kukataa huduma (DoS)

**Ulinzi wa Rasilimali:**
Enforce mipaka ya juu ya saizi ya subgrafu
<<<<<<< HEAD
Tekeleza muda wa mwisho wa swali ili kuzuia kutokuwa na rasilimali
Ongeza ufuatiliaji na mipaka ya matumizi ya kumbukumbu

**Kidhibiti cha Ufikiaji:**
Endeleza kutengwa kwa watumiaji na ukusanyaji iliyopo
=======
Tekeleza muda wa mwisho wa swali ili kuzuia uchovu wa rasilimali
Ongeza ufuatiliaji na mipaka ya matumizi ya kumbukumbu

**Kidhibiti cha Ufikiaji:**
Endeleza kutengwa kwa watumiaji na mkusanyiko iliyopo
>>>>>>> 82edf2d (New md files from RunPod)
Ongeza uandikaji wa ukaguzi kwa operesheni zinazoathiri utendaji
Tekeleza kikomo cha kiwango kwa operesheni ghali

## Mawasilisho ya Utendaji

### Maboresho Yanayotarajiwa ya Utendaji

<<<<<<< HEAD
**Upunguzaji wa Swali:**
Sasa: ~9,000+ maswali kwa ombi la kawaida
Yaliyoboreshwa: ~50-100 maswali yaliyunganishwa (upunguzaji wa 98%)
=======
**Upunguzaji wa Maswali:**
Sasa: ~9,000+ maswali kwa ombi la kawaida
Yaliyoboreshwa: ~50-100 maswali yaliyogawanywa (upunguzaji wa 98%)
>>>>>>> 82edf2d (New md files from RunPod)

**Maboresho ya Muda wa Jibu:**
Ufuatiliaji wa grafu: 15-20s → 3-5s (haraka 4-5x)
Utatuzi wa lebo: 8-12s → 2-4s (haraka 3x)
Swali kamili: 25-35s → 6-10s (maboresho ya 3-4x)

**Ufanisi wa Kumbukumbu:**
<<<<<<< HEAD
Saizi zilizokadiriwa za kumbukumbu inazuia uvujaji wa kumbukumbu
=======
Saizi zilizokadiriwa za hifadhi inazuia uvujaji wa kumbukumbu
>>>>>>> 82edf2d (New md files from RunPod)
Miundo ya data inayofaa hupunguza athari ya kumbukumbu kwa ~40%
Urekebishaji wa taka bora kupitia usafi sahihi wa rasilimali

**Mataifa ya Kweli ya Utendaji:**
<<<<<<< HEAD
**Kumbukumbu ya lebo**: Upunguzaji wa 10-20% wa swali kwa grafu zilizo na uhusiano wa kawaida
**Uboreshaji wa uunganisho**: Upunguzaji wa 50-80% wa swali (uboresho mkuu)
**Uboreshaji wa maisha ya kitu**: Ondoa gharama ya kila ombi
**Maboresho ya jumla**: Maboresho ya 3-4x ya muda wa jibu hasa kutoka kwa uunganisho

**Maboresho ya Uwezo wa Kupanuka:**
Usaidizi wa grafu za maarifa kubwa 3-5x (vikomo na mahitaji ya ulinganishaji wa utendaji)
=======
**Hifadhi ya lebo**: Upunguzaji wa 10-20% wa maswali kwa grafu zilizo na uhusiano wa kawaida
**Uboreshaji wa uainishaji**: Upunguzaji wa 50-80% wa maswali (uboresho mkuu)
**Uboreshaji wa maisha ya kitu**: Ondoa gharama ya kila ombi
**Maboresho ya jumla**: Maboresho ya 3-4x ya muda wa jibu hasa kutoka kwa uainishaji

**Maboresho ya Uwezo wa Kupanuka:**
Usaidizi wa grafu za maarifa kubwa 3-5x (mdogo na mahitaji ya ulinganishaji wa data)
>>>>>>> 82edf2d (New md files from RunPod)
Uwezo wa juu 3-5x wa ombi la wakati mmoja
Matumizi bora ya rasilimali kupitia matumizi ya upya ya muunganisho

### Ufuatiliaji wa Utendaji

<<<<<<< HEAD
**Hesabu za Muda Halisi:**
Muda wa utekelezaji wa swali kwa aina ya operesheni
Viwango vya hit na ufanisi wa kumbukumbu
Matumizi ya kikundi cha muunganisho wa hifadhidata
=======
**Mataifa ya Muda Halisi:**
Muda wa utekelezaji wa swali kwa aina ya operesheni
Viwango vya hit na ufanisi wa hifadhi
Matumizi ya dimbidi ya muunganisho wa hifadhidata
>>>>>>> 82edf2d (New md files from RunPod)
Matumizi ya kumbukumbu na athari ya urekebishaji wa taka

**Ufuatiliaji wa Utendaji:**
Mtihirika wa kiotomatiki wa utendaji
<<<<<<< HEAD
Mtihirika wa mzigo ukitumia data halisi
Viwango vya utendaji dhidi ya utekelezaji wa sasa
=======
Mtihirika wa mzigo kwa matumizi halisi ya data
Viwango vya kulinganisho dhidi ya utekelezaji wa sasa
>>>>>>> 82edf2d (New md files from RunPod)

## Mkakati wa Mtihirika

### Mtihirika wa Vitengo
Mtihirika wa vipengele vya mtu binafsi kwa ajili ya utekelezaji, kuhifadhi, na utatuzi wa lebo
<<<<<<< HEAD
Mwingiliano wa bandarini ya bandarini kwa ajili ya mtihirika wa utendaji
Mtihirika wa kuondoa data kutoka kwa kumbukumbu na muda wa kumalizika
Usimamizi wa makosa na hali za muda

### Mtihirika wa Uunganisho
Mtihirika wa mwisho hadi mwisho wa swali la GraphRAG ukiwa na uboreshaji
Mtihirika wa mwingiliano wa bandarini ya bandarini ukitumia data halisi
=======
Mwingiliano wa bandarini ya hila kwa ajili ya mtihirika wa utendaji
Mtihirika wa kuondoa data kutoka kwa kumbukumbu na kumalizika kwa muda
Usimamizi wa makosa na hali za muda

### Mtihirika wa Uunganisho
Mtihirika wa mwisho hadi mwisho wa swali la GraphRAG na uboreshaji
Mtihirika wa mwingiliano wa bandarini ya data halisi
>>>>>>> 82edf2d (New md files from RunPod)
Usimamizi wa ombi la wakati mmoja na rasilimali
Udagano wa uvujaji wa kumbukumbu na uthibitisho wa kusafisha rasilimali

### Mtihirika wa Utendaji
Mtihirika dhidi ya utekelezaji wa sasa
<<<<<<< HEAD
Mtihirika wa mzigo ukitumia saizi na utata tofauti wa grafu
Mtihirika wa shinikizo kwa mipaka ya kumbukumbu na uunganisho
Mtihirika wa utendaji kwa uboreshaji

### Mtihirika wa Ulinganishi
Thibitisha ulinganishi wa API ya GraphRAG iliyopo
Mtihirika ukitumia bandarini ya bandarini tofauti za bandarini ya grafu
=======
Mtihirika wa mzigo kwa saizi na utata tofauti wa grafu
Mtihirika wa shinikizo kwa mipaka ya kumbukumbu na uunganisho
Mtihirika wa marejesho kwa maboresho ya utendaji

### Mtihirika wa Ulinganishi
Thibitisha ulinganishi wa API ya GraphRAG iliyopo
Mtihirika na bandarini tofauti za hifadhi ya grafu
>>>>>>> 82edf2d (New md files from RunPod)
Thibitisha usahihi wa matokeo ikilinganishwa na utekelezaji wa sasa

## Mpango wa Utendaji

### Mbinu ya Utendaji Moja kwa Moja
Kwa kuwa API zinaweza kubadilika, tekeleza uboreshaji moja kwa moja bila utata wa uhamishaji:

<<<<<<< HEAD
1. **Badilisha `follow_edges` mbinu**: Andika upya ukitumia utekelezaji wa kikundi
2. **Boresha `get_labelgraph`**: Tepeleza utatuzi wa lebo kwa wingi
=======
1. **Badilisha `follow_edges` mbinu**: Andika upya kwa utekelezaji wa kikundi
2. **Boresha `get_labelgraph`**: Tepeleza utatuzi wa lebo kwa njia ya sambamba
>>>>>>> 82edf2d (New md files from RunPod)
3. **Ongeza GraphRag ya muda mrefu**: Badilisha Processor ili kudumisha mfano wa kudumu
4. **Tepeleza uhifadhi wa lebo**: Ongeza kumbukumbu ya LRU na TTL kwa darasa la GraphRag

### Wigo wa Mabadiliko
**Darasa la swali**: Badilisha mistari ~50 katika `follow_edges`, ongeza mistari ~30 ya utunzaji wa kikundi
**Darasa la GraphRag**: Ongeza safu ya kuhifadhi (~mistari 40)
**Darasa la Processor**: Badilisha ili kutumia mfano wa kudumu wa GraphRag (~mistari 20)
**Jumla**: ~mistari 140 ya mabadiliko, hasa ndani ya madarasa yaliyopo

## Ratiba

**Wiki ya 1: Utendaji wa Msingi**
<<<<<<< HEAD
Badilisha `follow_edges` ukitumia utekelezaji wa kikundi
Tepeleza utatuzi wa lebo kwa wingi katika `get_labelgraph`
=======
Badilisha `follow_edges` kwa utekelezaji wa kikundi
Tepeleza utatuzi wa lebo kwa njia ya sambamba katika `get_labelgraph`
>>>>>>> 82edf2d (New md files from RunPod)
Ongeza mfano wa GraphRag wa muda mrefu kwa Processor
Tepeleza safu ya uhifadhi

**Wiki ya 2: Mtihirika na Uunganisho**
Mtihirika wa vitengo kwa ajili ya utekelezaji mpya wa utekelezaji na uhifadhi
<<<<<<< HEAD
Ufuatiliaji wa utendaji dhidi ya utekelezaji wa sasa
Mtihirika wa uunganisho ukitumia data halisi ya grafu
Mtihirika wa msimamizi na uboreshaji

**Wiki ya 3: Utekelezaji**
Tepeleza utekelezaji ulioboreshwa
Fuatilia uboreshaji wa utendaji
Punguza muda wa TTL wa kumbukumbu na saizi za kikundi kulingana na matumizi halisi

## Maswali ya Funguo

**Uunganisho wa Bandarini**: Je, tunapaswa kutekeleza uunganisho wa bandarini maalum au kutegemea uunganisho wa bandarini wa bandarini ya bandarini iliyopo?
**Ukurasa wa Kumbukumbu**: Je, kumbukumbu za lebo na uwekaji wa kumbukumbu zinapaswa kudumu katika kuanzishwa upya za huduma?
**Ukurasa Uliogawanyika**: Kwa matoleo mengi, je, tunapaswa kutekeleza ukurasa uliogawanyika ukitumia Redis/Memcached?
**Muundo wa Matokeo ya Swali**: Je, tunapaswa kuboresha uwakilishi wa ndani wa triple ili kuboresha ufanisi wa kumbukumbu?
**Uunganisho wa Ufuatiliaji**: Vipimo vipi vinapaswa kuonyeshwa kwa mifumo ya ufuatiliaji iliyopo (Prometheus, n.k.)?
=======
Mtihirika wa utendaji dhidi ya utekelezaji wa sasa
Mtihirika wa uunganisho na data halisi ya grafu
Mtihirika wa msimamizi na uboreshaji

**Wiki ya 3: Uwekaji**
Weka utekelezaji ulioboreshwa
Fuatilia maboresho ya utendaji
Punguza muda wa uhifadhi na saizi za kikundi kulingana na matumizi halisi

## Maswali ya Funguo

**Uunganisho wa Bandarini**: Je, tunapaswa kutekeleza bandarini ya uunganisho maalum au kutegemea bandarini ya mteja wa hifadhi iliyopo?
**Ukurasa wa Uhifadhi**: Je, uhifadhi wa lebo na uwekaji unapaswa kudumu katika kuanzishwa upya huduma?
**Ukurasa Uliogawanyika**: Kwa matoleo mengi, je, tunapaswa kutekeleza ukurasa uliogawanyika na Redis/Memcached?
**Muundo wa Matokeo ya Swali**: Je, tunapaswa kuboresha uwakilishi wa ndani wa utatu kwa ufanisi bora wa kumbukumbu?
**Uunganisho wa Ufuatiliaji**: Ni metri gani ambazo zinapaswa kuonyeshwa kwa mifumo ya ufuatiliaji iliyopo (Prometheus, n.k.)?
>>>>>>> 82edf2d (New md files from RunPod)

## Marejeleo

[Utekelezaji Asili wa GraphRAG](trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py)
<<<<<<< HEAD
[Kanuni za Usanifu wa TrustGraph](architecture-principles.md)
=======
[Kanuni za Usawa wa TrustGraph](architecture-principles.md)
>>>>>>> 82edf2d (New md files from RunPod)
[Maelekezo ya Usimamizi wa Mkusanyiko](collection-management.md)
