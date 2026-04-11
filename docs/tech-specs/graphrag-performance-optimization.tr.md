# GraphRAG Performans Optimizasyonu Teknik Özellikleri

## Genel Bakış

Bu özellik, TrustGraph'taki GraphRAG (Graf Çıkarım Destekli Üretim) algoritması için kapsamlı performans iyileştirmelerini açıklamaktadır. Mevcut uygulama, ölçeklenebilirliği ve yanıt sürelerini sınırlayan önemli performans darboğazlarına sahiptir. Bu özellik, dört birincil optimizasyon alanını ele almaktadır:

1. **Graf Gezinme Optimizasyonu**: Verimsiz yinelemeli veritabanı sorgularını ortadan kaldırın ve toplu grafik keşfi uygulayın.
2. **Etiket Çözümleme Optimizasyonu**: Sıralı etiket alma işlemlerini, paralel/toplu işlemlere dönüştürün.
3. **Önbellekleme Stratejisi İyileştirmesi**: LRU (En Son Kullanılmayan) çıkarma ve ön yükleme ile akıllı bir önbellekleme uygulayın.
4. **Sorgu Optimizasyonu**: İyileştirilmiş yanıt süreleri için sonuç memoizasyonu ve gömme önbelleği ekleyin.

## Hedefler

**Veritabanı Sorgusu Hacmini Azaltın**: Toplu işleme ve önbellekleme yoluyla toplam veritabanı sorgularında %50-80'lik bir azalma elde edin.
**Yanıt Sürelerini İyileştirin**: Alt grafik oluşturma için 3-5 kat daha hızlı ve etiket çözümleme için 2-3 kat daha hızlı hedefleyin.
**Ölçeklenebilirliği Artırın**: Daha iyi bellek yönetimi ile daha büyük bilgi grafiklerini destekleyin.
**Doğruluğu Koruyun**: Mevcut GraphRAG işlevselliğini ve sonuç kalitesini koruyun.
**Eşzamanlılığı Etkinleştirin**: Çoklu eşzamanlı istekler için paralel işleme yeteneklerini iyileştirin.
**Bellek Ayak İzini Azaltın**: Verimli veri yapıları ve bellek yönetimi uygulayın.
<<<<<<< HEAD
**Gözlemlenebilirliği Ekleyin**: Performans ölçümleri ve izleme yetenekleri ekleyin.
=======
**Gözlenebilirliği Ekleyin**: Performans ölçümleri ve izleme yetenekleri ekleyin.
>>>>>>> 82edf2d (New md files from RunPod)
**Güvenilirliği Sağlayın**: Uygun hata işleme ve zaman aşımı mekanizmaları ekleyin.

## Arka Plan

`trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py` içindeki mevcut GraphRAG uygulaması, sistem ölçeklenebilirliğini önemli ölçüde etkileyen çeşitli kritik performans sorunları sergilemektedir:

### Mevcut Performans Sorunları

**1. Verimsiz Graf Gezinme (`follow_edges` fonksiyonu, 79-127 satırlar)**
<<<<<<< HEAD
Her varlık için her derinlik seviyesinde 3 ayrı veritabanı sorgusu yapar.
Sorgu kalıbı: Her varlık için konu tabanlı, öznelik tabanlı ve nesne tabanlı sorgular.
Toplu işleme yok: Her sorgu yalnızca bir varlığı işler.
Döngü algılama yok: Aynı düğümlere birden çok kez geri dönülebilir.
Memoizasyon olmadan yinelemeli uygulama, üstel karmaşıklığa yol açar.
Zaman karmaşıklığı: O(varlıklar × max_path_length × triple_limit³)

**2. Sıralı Etiket Çözümleme (`get_labelgraph` fonksiyonu, 144-171 satırlar)**
Her üç bileşenli (konu, öznelik, nesne) üçlü öğeyi sırasıyla işler.
Her `maybe_label` çağrısı potansiyel olarak bir veritabanı sorgusu tetikler.
Etiket sorgularının paralel yürütülmesi veya toplu işlenmesi yoktur.
subgraph_size × 3 adet ayrı veritabanı çağrısına yol açar.

**3. Basit Önbellekleme Stratejisi (`maybe_label` fonksiyonu, 62-77 satırlar)**
Boyut sınırları veya TTL (Yaşam Süresi) olmadan basit bir sözlük önbelleği.
Önbellek çıkarma politikası olmaması, sınırsız bellek büyümesine yol açar.
Önbellek hataları, ayrı veritabanı sorgularını tetikler.
Ön yükleme veya akıllı önbellek önleme yoktur.

**4. Alt Optimum Sorgu Kalıpları**
Benzer istekler arasında varlık vektör benzerliği sorguları önbelleğe alınmaz.
Tekrarlayan sorgu kalıpları için sonuç memoizasyonu yoktur.
Yaygın erişim kalıpları için sorgu optimizasyonu eksiktir.
=======
Her varlık için 3 ayrı veritabanı sorgusu yapar.
Sorgu kalıbı: her varlık için konu tabanlı, öznelik tabanlı ve nesne tabanlı sorgular.
Toplu işleme yok: Her sorgu yalnızca bir varlığı işler.
Döngü algılama yok: Aynı düğümlere birden çok kez geri dönülebilir.
Memoizasyon olmadan yinelemeli uygulama, üstel karmaşıklığa yol açar.
Zaman karmaşıklığı: O(varlıklar × maks_yol_uzunluğu × üçlü_sınırı³)

**2. Sıralı Etiket Çözümleme (`get_labelgraph` fonksiyonu, 144-171 satırlar)**
Her üç bileşenli (konu, öznelik, nesne) sırayla işler.
Her `maybe_label` çağrısı potansiyel olarak bir veritabanı sorgusu tetikler.
Etiket sorgularının paralel yürütülmesi veya toplu işlenmesi yok.
subgraph_size × 3 adet ayrı veritabanı çağrısına yol açar.

**3. Basit Önbellekleme Stratejisi (`maybe_label` fonksiyonu, 62-77 satırlar)**
Boyut sınırları veya TTL (Yaşam Süresi Sonu) olmadan basit bir sözlük önbelleği.
Önbellek çıkarma politikası olmaması, sınırsız bellek büyümesine yol açar.
Önbellek hataları, ayrı veritabanı sorgularını tetikler.
Ön yükleme veya akıllı önbellek önleme yok.

**4. Alt Optimum Sorgu Kalıpları**
Benzer istekler arasında varlık vektör benzerliği sorguları önbelleğe alınmaz.
Tekrarlayan sorgu kalıpları için sonuç memoizasyonu yok.
Yaygın erişim kalıpları için sorgu optimizasyonu eksik.
>>>>>>> 82edf2d (New md files from RunPod)

**5. Kritik Nesne Ömrü Sorunları (`rag.py:96-102`)**
**GraphRag nesnesi her istek için yeniden oluşturulur**: Her sorgu için yeni bir örnek oluşturulur, böylece tüm önbellek avantajları kaybolur.
**Sorgu nesnesi son derece kısa ömürlüdür**: Tek bir sorgu yürütmesi içinde oluşturulur ve yok edilir (201-207 satırlar).
**Etiket önbelleği her istek için sıfırlanır**: Önbellek önleme ve birikmiş bilgi istekler arasında kaybolur.
**İstemci yeniden oluşturma ek yükü**: Veritabanı istemcileri potansiyel olarak her istek için yeniden oluşturulur.
<<<<<<< HEAD
**İstekler arası optimizasyon yok**: Sorgu kalıplarından veya sonuç paylaşımından yararlanamaz.
=======
**Çapraz istek optimizasyonu yok**: Sorgu kalıplarından veya sonuç paylaşımından yararlanamaz.
>>>>>>> 82edf2d (New md files from RunPod)

### Performans Etki Analizi

Tipik bir sorgu için mevcut en kötü senaryo:
**Varlık Alma**: 1 vektör benzerliği sorgusu.
<<<<<<< HEAD
**Graf Gezinme**: varlıklar × max_path_length × 3 × triple_limit sorgusu.
=======
**Graf Gezinme**: varlıklar × maks_yol_uzunluğu × 3 × üçlü_sınırı sorguları.
>>>>>>> 82edf2d (New md files from RunPod)
**Etiket Çözümleme**: subgraph_size × 3 adet ayrı etiket sorgusu.

Varsayılan parametreler için (50 varlık, yol uzunluğu 2, 30 üçlü sınırı, 150 alt grafik boyutu):
**Minimum sorgular**: 1 + (50 × 2 × 3 × 30) + (150 × 3) = **9.451 veritabanı sorgusu**
**Yanıt süresi**: Orta büyüklükteki grafikler için 15-30 saniye
**Bellek kullanımı**: Zamanla sınırsız önbellek büyümesi
**Önbellek etkinliği**: %0 - her istekte önbellekler sıfırlanır
<<<<<<< HEAD
**Nesne oluşturma ek yükü**: Her istek için oluşturulan/silinen GraphRag + Sorgu nesneleri
=======
**Nesne oluşturma ek yükü**: Her istek için GraphRag + Sorgu nesneleri oluşturulur/silinir
>>>>>>> 82edf2d (New md files from RunPod)

Bu özellik, toplu sorguları, akıllı önbelleği ve paralel işleme uygulayarak bu eksiklikleri giderir. Sorgu kalıplarını ve veri erişimini optimize ederek TrustGraph şunları yapabilir:
Milyonlarca varlığa sahip kurumsal ölçekli bilgi grafiklerini destekleyin
Tipik sorgular için saniyeden daha kısa yanıt süreleri sağlayın
Yüzlerce eşzamanlı GraphRAG isteğini işleyin
Grafik boyutu ve karmaşıklığıyla verimli bir şekilde ölçeklendirin

## Teknik Tasarım

### Mimari

GraphRAG performans optimizasyonu, aşağıdaki teknik bileşenleri gerektirir:

#### 1. **Nesne Ömrü Mimari Yeniden Düzenlemesi**
   **GraphRag'i uzun ömürlü hale getirin**: GraphRag örneğini, istekler arasında süreklilik sağlamak için İşlemci seviyesine taşıyın
   **Önbellekleri koruyun**: Etiket önbelleğini, gömme önbelleğini ve sorgu sonucu önbelleğini istekler arasında koruyun
   **Sorgu nesnesini optimize edin**: Sorguyu, veri kapsayıcısı değil, hafif bir yürütme bağlamı olarak yeniden düzenleyin
   **Bağlantı sürekliliği**: Veritabanı istemci bağlantılarını istekler arasında koruyun

   Modül: `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` (değiştirildi)

#### 2. **Optimize Edilmiş Grafik Gezinme Motoru**
   Özyinelemeli `follow_edges`'ı yinelemeli genişlik öncelikli arama ile değiştirin
   Her gezinme seviyesinde toplu varlık işleme uygulayın
   Ziyaret edilen düğüm takibi kullanarak döngü algılama ekleyin
   Sınırlar aşıldığında erken sonlandırma ekleyin

   Modül: `trustgraph-flow/trustgraph/retrieval/graph_rag/optimized_traversal.py`

#### 3. **Paralel Etiket Çözümleme Sistemi**
   Birden çok varlık için etiket sorgularını aynı anda toplu olarak sorgulayın
   Eşzamanlı veritabanı erişimi için asenkron/bekle kalıplarını uygulayın
   Yaygın etiket kalıpları için akıllı ön yükleme ekleyin
   Etiket önbelleği ısıtma stratejileri ekleyin

   Modül: `trustgraph-flow/trustgraph/retrieval/graph_rag/label_resolver.py`

#### 4. **Muhafazakar Etiket Önbelleği Katmanı**
   Performans ve tutarlılık dengesini sağlamak için yalnızca etiketler için kısa TTL'ye sahip LRU önbelleği (5 dakika)
   Önbellek metriklerini ve isabet oranını izleme
   **Gömme önbelleği yok**: Zaten her sorgu için önbelleğe alınmıştır, sorgular arası bir fayda yoktur
   **Sorgu sonucu önbelleği yok**: Grafik mutasyon tutarlılığı endişeleri nedeniyle

   Modül: `trustgraph-flow/trustgraph/retrieval/graph_rag/cache_manager.py`

#### 5. **Sorgu Optimizasyon Çerçevesi**
   Sorgu kalıbı analizi ve optimizasyon önerileri
   Veritabanı erişimi için toplu sorgu koordinatörü
   Bağlantı havuzu ve sorgu zaman aşımı yönetimi
   Performans izleme ve ölçüm toplama

   Modül: `trustgraph-flow/trustgraph/retrieval/graph_rag/query_optimizer.py`

### Veri Modelleri

#### Optimize Edilmiş Grafik Gezinme Durumu

Gezinme motoru, gereksiz işlemleri önlemek için durumu korur:

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

Bu yaklaşım şunları sağlar:
Ziyaret edilen varlıkları takip ederek verimli döngü tespiti
Her gezinme seviyesinde toplu sorgu hazırlama
Bellek verimli durum yönetimi
Boyut limitlerine ulaşıldığında erken sonlandırma

#### Gelişmiş Önbellek Yapısı

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

#### Toplu Sorgu Yapıları

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

### API'ler

#### Yeni API'ler:

**GraphTraversal API'si**
```python
async def optimized_follow_edges_batch(
    entities: List[str],
    max_depth: int,
    triple_limit: int,
    max_subgraph_size: int
) -> Set[Tuple[str, str, str]]
```

**Toplu Etiket Çözümleme API'si**
```python
async def resolve_labels_batch(
    entities: List[str],
    cache_manager: CacheManager
) -> Dict[str, str]
```

**Önbellek Yönetimi API'si**
```python
class CacheManager:
    async def get_or_fetch_label(self, entity: str) -> str
    async def get_or_fetch_embeddings(self, query: str) -> List[float]
    async def cache_query_result(self, query_hash: str, result: Any, ttl: int)
    def get_cache_statistics(self) -> CacheStatistics
```

#### Değiştirilmiş API'ler:

**GraphRag.query()** - Performans optimizasyonlarıyla geliştirildi:
Önbellek kontrolü için `cache_manager` parametresi eklendi.
Performans metriklerini içeren `performance_metrics` dönüş değeri eklendi.
Güvenilirlik için `query_timeout` parametresi eklendi.

**Query sınıfı** - Toplu işleme için yeniden düzenlendi:
Bireysel varlık işleme yerine toplu işlemler kullanıldı.
Kaynak temizliği için asenkron bağlam yöneticileri eklendi.
Uzun süren işlemler için ilerleme geri çağırmaları eklendi.

### Uygulama Detayları

#### Aşama 0: Kritik Mimari Yaşam Döngüsü Yeniden Düzenlemesi

**Mevcut Sorunlu Uygulama:**
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

**Optimize Edilmiş, Uzun Ömürlü Mimari:**
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

Bu mimari değişiklik şunları sağlar:
**Ortak ilişkileri olan grafikler için veritabanı sorgu sayısında %10-20'lik bir azalma** (şu anda %0'a kıyasla)
<<<<<<< HEAD
Her istek için **ortadan kaldırılan nesne oluşturma ek yükü**
=======
Her istek için **oluşturulan nesnelerin getirdiği ek yükün ortadan kaldırılması**
>>>>>>> 82edf2d (New md files from RunPod)
**Sürekli bağlantı havuzu** ve istemci yeniden kullanımı
Önbellek TTL (Yaşam Süresi) aralıkları içinde **istemler arası optimizasyon**

**Önemli Önbellek Tutarlılık Sınırlaması:**
<<<<<<< HEAD
Uzun süreli önbellekleme, temel grafikteki varlıkların/etiketlerin silindiği veya değiştirildiği durumlarda, güncelliği kaybetme riski oluşturur. LRU (En Son Kullanılmayan) önbelleği, performans kazanımları ile veri tazeliği arasında bir denge sağlarken, gerçek zamanlı grafik değişikliklerini tespit edemez.
=======
Uzun süreli önbellekleme, temel grafikteki varlıkların/etiketlerin silindiği veya değiştirildiği durumlarda, verilerin güncelliğini yitirme riski oluşturur. LRU (En Son Kullanılmayan) önbelleği, performans artışları ve veri tazeliği arasında bir denge sağlar, ancak gerçek zamanlı grafik değişikliklerini tespit edemez.
>>>>>>> 82edf2d (New md files from RunPod)

#### 1. Aşama: Grafik Gezinme Optimizasyonu

**Mevcut Uygulama Sorunları:**
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

**Optimize Edilmiş Uygulama:**
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

#### 2. Aşama: Paralel Etiket Çözümlemesi

**Mevcut Sıralı Uygulama:**
```python
# INEFFICIENT: Sequential processing
for edge in subgraph:
    s = await self.maybe_label(edge[0])  # Individual query
    p = await self.maybe_label(edge[1])  # Individual query
    o = await self.maybe_label(edge[2])  # Individual query
```

**Optimize Edilmiş Paralel Uygulama:**
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

#### 3. Aşama: Gelişmiş Önbellekleme Stratejisi

**TTL ile LRU Önbelleği:**
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

#### 4. Aşama: Sorgu Optimizasyonu ve İzleme

**Performans Metrikleri Toplama:**
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

**Sorgu Zaman Aşımı ve Devre Kesici:**
```python
async def execute_with_timeout(self, query_func, timeout: int = 30):
    try:
        return await asyncio.wait_for(query_func(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"Query timeout after {timeout}s")
        raise GraphRagTimeoutError(f"Query exceeded timeout of {timeout}s")
```

## Önbellek Tutarlılık Hususları

**Veri Güncelliği Dengesi:**
**Etiket önbelleği (5 dakika TTL):** Silinmiş/yeniden adlandırılmış varlık etiketlerini sunma riski.
**Gömme önbelleği yok:** Gerekli değil - gömmeler zaten her sorgu için önbelleğe alınmıştır.
**Sonuç önbelleği yok:** Silinmiş varlıklar/ilişkilerden kaynaklanan eski alt grafik sonuçlarını önler.

**Azaltma Stratejileri:**
**Muhafazakar TTL değerleri:** Performans kazanımları (10-20%) ile veri güncelliği arasındaki denge.
<<<<<<< HEAD
**Önbellek geçersiz kılma kancaları:** İsteğe bağlı olarak grafik mutasyon olaylarıyla entegrasyon.
=======
**Önbellek geçersiz kılma mekanizmaları:** Grafik mutasyon olaylarıyla isteğe bağlı entegrasyon.
>>>>>>> 82edf2d (New md files from RunPod)
**İzleme panoları:** Önbellek isabet oranlarını, veri güncelliği sorunlarıyla karşılaştırarak izleyin.
**Yapılandırılabilir önbellek politikaları:** Mutasyon sıklığına göre dağıtıma özel ayarlamalar yapılmasına izin verir.

**Grafik Mutasyon Oranına Göre Önerilen Önbellek Yapılandırması:**
**Yüksek mutasyon (>100 değişiklik/saat):** TTL=60s, daha küçük önbellek boyutları.
**Orta mutasyon (10-100 değişiklik/saat):** TTL=300s (varsayılan).
**Düşük mutasyon (<10 değişiklik/saat):** TTL=600s, daha büyük önbellek boyutları.

## Güvenlik Hususları

<<<<<<< HEAD
**Sorgu Enjeksiyonunu Önleme:**
=======
**Sorgu Enjeksiyonu Önleme:**
>>>>>>> 82edf2d (New md files from RunPod)
Tüm varlık tanımlayıcılarını ve sorgu parametrelerini doğrulayın.
Tüm veritabanı etkileşimleri için parametreli sorgular kullanın.
DoS saldırılarını önlemek için sorgu karmaşıklığı limitleri uygulayın.

**Kaynak Koruması:**
<<<<<<< HEAD
Maksimum alt grafik boyutları limitlerini uygulayın.
Kaynak tükenmesini önlemek için sorgu zaman aşımlarını uygulayın.
=======
Maksimum alt grafik boyutları için limitler uygulayın.
Kaynak tükenmesini önlemek için sorgu zaman aşımları uygulayın.
>>>>>>> 82edf2d (New md files from RunPod)
Bellek kullanımı izleme ve limitleri ekleyin.

**Erişim Kontrolü:**
Mevcut kullanıcı ve koleksiyon izolasyonunu koruyun.
Performansı etkileyen işlemler için denetim kaydı ekleyin.
Pahalı işlemler için hız sınırlaması uygulayın.

## Performans Hususları

### Beklenen Performans İyileştirmeleri

**Sorgu Azaltma:**
<<<<<<< HEAD
Mevcut: Tipik bir istek için ~9.000+ sorgu.
=======
Mevcut: Tipik bir istek için ~9.000'den fazla sorgu.
>>>>>>> 82edf2d (New md files from RunPod)
Optimize edilmiş: ~50-100 toplu sorgu (98% azalma).

**Yanıt Süresi İyileştirmeleri:**
Grafik geçişi: 15-20s → 3-5s (4-5 kat daha hızlı).
Etiket çözümü: 8-12s → 2-4s (3 kat daha hızlı).
Genel sorgu: 25-35s → 6-10s (3-4 kat iyileşme).

**Bellek Verimliliği:**
Sınırlı önbellek boyutları, bellek sızıntılarını önler.
Verimli veri yapıları, bellek ayak izini yaklaşık %40 azaltır.
Uygun kaynak temizliği sayesinde daha iyi çöp toplama.

**Gerçekçi Performans Beklentileri:**
**Etiket önbelleği:** Ortak ilişkilere sahip grafikler için sorgu azaltmada %10-20.
**Toplu optimizasyon:** %50-80 sorgu azaltma (birincil optimizasyon).
**Nesne ömrü optimizasyonu:** Her istekte oluşturma ek yükünü ortadan kaldırır.
**Genel iyileşme:** Toplu işlemden kaynaklanan 3-4 kat yanıt süresi iyileşmesi.

**Ölçeklenebilirlik İyileştirmeleri:**
<<<<<<< HEAD
3-5 kat daha büyük bilgi grafiklerini destekler (önbellek tutarlılık ihtiyaçları ile sınırlıdır).
=======
3-5 kat daha büyük bilgi grafiklerini destekler (önbellek tutarlılık gereksinimleriyle sınırlıdır).
>>>>>>> 82edf2d (New md files from RunPod)
3-5 kat daha yüksek eşzamanlı istek kapasitesi.
Bağlantı yeniden kullanımı sayesinde daha iyi kaynak kullanımı.

### Performans İzleme

**Gerçek Zamanlı Metrikler:**
İşlem türüne göre sorgu yürütme süreleri.
Önbellek isabet oranları ve etkinliği.
Veritabanı bağlantı havuzu kullanımı.
Bellek kullanımı ve çöp toplama etkisi.

**Performans Karşılaştırması:**
Otomatik performans gerileme testi
Gerçekçi veri hacimleriyle yük testi
Mevcut uygulamaya karşı karşılaştırma testleri

## Test Stratejisi

### Birim Testi
Gezinme, önbellekleme ve etiket çözümleme için bireysel bileşen testi
Performans testi için sahte veritabanı etkileşimleri
Önbellek temizleme ve TTL (Yaşam Süresi) sonlandırma testi
Hata işleme ve zaman aşımı senaryoları

### Entegrasyon Testi
Optimizasyonlarla uçtan uca GraphRAG sorgu testi
<<<<<<< HEAD
Gerçek verilerle veritabanı etkileşim testi
=======
Gerçek verilerle veritabanı etkileşimi testi
>>>>>>> 82edf2d (New md files from RunPod)
Eşzamanlı istek işleme ve kaynak yönetimi
Bellek sızıntısı tespiti ve kaynak temizleme doğrulaması

### Performans Testi
Mevcut uygulamaya karşı karşılaştırma testi
Farklı grafik boyutları ve karmaşıklıklarla yük testi
Bellek ve bağlantı limitleri için stres testi
Performans iyileştirmeleri için regresyon testi

### Uyumluluk Testi
Mevcut GraphRAG API uyumluluğunu doğrulayın
Çeşitli grafik veritabanı arka uçlarıyla test yapın
Mevcut uygulamaya kıyasla sonuç doğruluğunu doğrulayın

## Uygulama Planı

### Doğrudan Uygulama Yaklaşımı
API'lerin değişmesine izin verildiğinden, geçiş karmaşıklığı olmadan doğrudan optimizasyonları uygulayın:

1. **`follow_edges` yöntemini değiştirin**: Yinelemeli toplu işleme ile yeniden yazın
<<<<<<< HEAD
2. **`get_labelgraph`'ı optimize edin**: Paralel etiket çözümlemeyi uygulayın
3. **Uzun ömürlü GraphRag ekleyin**: Kalıcı bir örnek tutmak için İşlemci'yi değiştirin
4. **Etiket önbelleğini uygulayın**: GraphRag sınıfına TTL ile LRU (En Son Kullanılan) önbelleği ekleyin
=======
2. **`get_labelgraph`'ı optimize edin**: Paralel etiket çözümlemesini uygulayın
3. **Uzun ömürlü GraphRag ekleyin**: Kalıcı bir örnek tutmak için İşlemci'yi değiştirin
4. **Etiket önbelleklemesini uygulayın**: GraphRag sınıfına TTL ile LRU (En Son Kullanılan) önbelleği ekleyin
>>>>>>> 82edf2d (New md files from RunPod)

### Değişiklik Kapsamı
**Sorgu sınıfı**: `follow_edges` içinde ~50 satırı değiştirin, toplu işleme için ~30 satır ekleyin
**GraphRag sınıfı**: Önbellekleme katmanı ekleyin (~40 satır)
**İşlemci sınıfı**: Kalıcı bir GraphRag örneği kullanmak için değiştirin (~20 satır)
**Toplam**: Odaklanmış değişikliklerin ~140 satırı, çoğunlukla mevcut sınıfların içinde

## Zaman Çizelgesi

**1. Hafta: Temel Uygulama**
`follow_edges`'ı toplu yinelemeli gezinmeyle değiştirin
<<<<<<< HEAD
`get_labelgraph` içinde paralel etiket çözümlemeyi uygulayın
=======
`get_labelgraph` içinde paralel etiket çözümlemesini uygulayın
>>>>>>> 82edf2d (New md files from RunPod)
İşlemci'ye uzun ömürlü GraphRag örneği ekleyin
Etiket önbellekleme katmanı uygulayın

**2. Hafta: Test ve Entegrasyon**
Yeni gezinme ve önbellekleme mantığı için birim testleri
Mevcut uygulamaya karşı performans karşılaştırması
Gerçek grafik verileriyle entegrasyon testi
Kod incelemesi ve optimizasyon

**3. Hafta: Dağıtım**
Optimize edilmiş uygulamayı dağıtın
Performans iyileştirmelerini izleyin
<<<<<<< HEAD
Gerçek kullanım temelinde önbellek TTL'sini ve toplu boyutları ayarlayın
=======
Gerçek kullanım bazında önbellek TTL'sini ve toplu boyutları ayarlayın
>>>>>>> 82edf2d (New md files from RunPod)

## Açık Sorular

**Veritabanı Bağlantı Havuzu**: Özel bir bağlantı havuzu mu uygulamalıyız yoksa mevcut veritabanı istemci havuzuna mı güvenmeliyiz?
**Önbellek Kalıcılığı**: Etiket ve gömme önbellekleri hizmet yeniden başlatmalarında kalıcı mı olmalı?
**Dağıtılmış Önbellekleme**: Çok örnekli dağıtımlar için Redis/Memcached ile dağıtılmış önbellekleme mi uygulamalıyız?
**Sorgu Sonucu Formatı**: Daha iyi bellek verimliliği için dahili üçlü gösterimi optimize etmeli miyiz?
**İzleme Entegrasyonu**: Hangi ölçümler mevcut izleme sistemlerine (Prometheus, vb.) maruz bırakılmalıdır?

## Referanslar

[GraphRAG Orijinal Uygulaması](trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py)
[TrustGraph Mimari Prensipleri](architecture-principles.md)
[Koleksiyon Yönetimi Özellikleri](collection-management.md)
