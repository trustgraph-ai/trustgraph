# Техническая спецификация оптимизации производительности GraphRAG

## Обзор

Эта спецификация описывает комплексные оптимизации производительности для алгоритма GraphRAG (Graph Retrieval-Augmented Generation) в TrustGraph. Текущая реализация страдает от значительных узких мест в производительности, которые ограничивают масштабируемость и время отклика. Эта спецификация охватывает четыре основные области оптимизации:

1. **Оптимизация обхода графа**: Исключение неэффективных рекурсивных запросов к базе данных и реализация пакетной обработки графа.
2. **Оптимизация разрешения меток**: Замена последовательной загрузки меток параллельными/пакетными операциями.
3. **Улучшение стратегии кэширования**: Реализация интеллектуального кэширования с вытеснением по принципу LRU и предварительной загрузкой.
4. **Оптимизация запросов**: Добавление мемоизации результатов и кэширования вложений для повышения скорости отклика.

## Цели

**Сокращение объема запросов к базе данных**: Достижение снижения общего количества запросов к базе данных на 50-80% за счет пакетной обработки и кэширования.
**Улучшение времени отклика**: Целевое увеличение скорости построения подграфов в 3-5 раз и ускорение разрешения меток в 2-3 раза.
**Повышение масштабируемости**: Поддержка более крупных графов знаний с улучшением управления памятью.
**Сохранение точности**: Сохранение существующей функциональности GraphRAG и качества результатов.
**Обеспечение параллельности**: Улучшение возможностей параллельной обработки для нескольких одновременных запросов.
**Уменьшение объема памяти**: Реализация эффективных структур данных и управления памятью.
**Добавление возможностей мониторинга**: Включение показателей производительности и возможностей мониторинга.
**Обеспечение надежности**: Добавление надлежащей обработки ошибок и механизмов таймаута.

## Предыстория

Текущая реализация GraphRAG в `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py` имеет несколько критических проблем с производительностью, которые серьезно влияют на масштабируемость системы:

### Текущие проблемы с производительностью

**1. Неэффективный обход графа (функция `follow_edges`, строки 79-127)**
Выполняет 3 отдельных запроса к базе данных для каждой сущности на каждом уровне глубины.
Шаблон запроса: запросы на основе субъекта, запросы на основе предиката и запросы на основе объекта для каждой сущности.
Без пакетной обработки: Каждый запрос обрабатывает только одну сущность за раз.
Без обнаружения циклов: Может повторно посещать одни и те же узлы несколько раз.
Рекурсивная реализация без мемоизации приводит к экспоненциальной сложности.
Временная сложность: O(entities × max_path_length × triple_limit³)

**2. Последовательное разрешение меток (функция `get_labelgraph`, строки 144-171)**
Обрабатывает каждый компонент тройки (субъект, предикат, объект) последовательно.
Каждый вызов `maybe_label` потенциально вызывает запрос к базе данных.
Без параллельного выполнения или пакетной обработки запросов меток.
В результате получается до 3 × subgraph_size отдельных вызовов базы данных.

**3. Примитивная стратегия кэширования (функция `maybe_label`, строки 62-77)**
Простой кэш в виде словаря без ограничений размера или TTL.
Отсутствие политики вытеснения кэша приводит к неограниченному росту памяти.
Пропуски кэша вызывают отдельные запросы к базе данных.
Без предварительной загрузки или интеллектуального подогрева кэша.

**4. Субоптимальные шаблоны запросов**
Запросы на сравнение векторного сходства сущностей не кэшируются между похожими запросами.
Без мемоизации результатов для повторяющихся шаблонов запросов.
Отсутствие оптимизации запросов для распространенных шаблонов доступа.

**5. Критические проблемы с жизненным циклом объектов (`rag.py:96-102`)**
**Объект GraphRag создается для каждого запроса**: Новый экземпляр создается для каждого запроса, что приводит к потере всех преимуществ кэша.
**Объект запроса имеет очень короткий срок службы**: Создается и уничтожается в течение выполнения одного запроса (строки 201-207).
**Кэш меток сбрасывается для каждого запроса**: Подогрев кэша и накопленные знания теряются между запросами.
**Накладные расходы на повторное создание клиента**: Клиенты базы данных потенциально повторно устанавливаются для каждого запроса.
**Без оптимизации между запросами**: Невозможно извлечь выгоду из шаблонов запросов или совместного использования результатов.

### Анализ влияния на производительность

Текущий наихудший сценарий для типичного запроса:
**Извлечение сущности**: 1 запрос на сравнение векторного сходства.
**Обход графа**: entities × max_path_length × 3 × triple_limit запросов.
**Разрешение меток**: subgraph_size × 3 отдельных запросов на разрешение меток.

Для параметров по умолчанию (50 сущностей, длина пути 2, ограничение в 30 тройки, размер подграфа 150):
**Минимальное количество запросов**: 1 + (50 × 2 × 3 × 30) + (150 × 3) = **9451 запрос к базе данных**
**Время отклика**: 15-30 секунд для графов среднего размера
**Использование памяти**: Неограниваемый рост кэша со временем
**Эффективность кэша**: 0% - кэши сбрасываются при каждом запросе
**Накладные расходы на создание объектов**: Объекты GraphRag + Query создаются/удаляются для каждого запроса

Эта спецификация решает эти проблемы, реализуя пакетные запросы, интеллектуальное кэширование и параллельную обработку. Оптимизируя шаблоны запросов и доступ к данным, TrustGraph может:
Поддерживать графы знаний корпоративного уровня с миллионами сущностей
Обеспечивать время отклика менее 1 секунды для типичных запросов
Обрабатывать сотни одновременных запросов GraphRAG
Эффективно масштабироваться в зависимости от размера и сложности графа

## Технический дизайн

### Архитектура

Оптимизация производительности GraphRAG требует следующих технических компонентов:

#### 1. **Архитектурная реорганизация жизненного цикла объектов**
   **Сделать GraphRag долгоживущим**: Переместить экземпляр GraphRag на уровень Processor для сохранения между запросами
   **Сохранять кэши**: Поддерживать кэш меток, кэш вложений и кэш результатов запросов между запросами
   **Оптимизировать объект Query**: Переработать Query как легковесный контекст выполнения, а не контейнер данных
   **Сохранять подключения к базе данных**: Поддерживать подключения к базе данных между запросами

   Модуль: `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` (изменен)

#### 2. **Оптимизированный движок обхода графа**
   Заменить рекурсивную `follow_edges` на итеративный поиск в ширину
   Реализовать пакетную обработку сущностей на каждом уровне обхода
   Добавить обнаружение циклов с помощью отслеживания посещенных узлов
   Включить раннее завершение при достижении лимитов

   Модуль: `trustgraph-flow/trustgraph/retrieval/graph_rag/optimized_traversal.py`

#### 3. **Параллельная система разрешения меток**
   Пакетные запросы меток для нескольких сущностей одновременно
   Реализовать шаблоны async/await для параллельного доступа к базе данных
   Добавить интеллектуальную предварительную загрузку для распространенных шаблонов меток
   Включить стратегии предварительного заполнения кэша меток

   Модуль: `trustgraph-flow/trustgraph/retrieval/graph_rag/label_resolver.py`

#### 4. **Консервативный слой кэширования меток**
   Кэш LRU с коротким TTL только для меток (5 минут) для баланса между производительностью и согласованностью
   Мониторинг метрик кэша и коэффициента попадания
   **Без кэширования вложений**: Уже кэшируются для каждого запроса, нет преимуществ для межзапросных данных
   **Без кэширования результатов запросов**: Из-за проблем согласованности изменений графа

   Модуль: `trustgraph-flow/trustgraph/retrieval/graph_rag/cache_manager.py`

#### 5. **Фреймворк оптимизации запросов**
   Анализ шаблонов запросов и предложения по оптимизации
   Пакетный координатор запросов для доступа к базе данных
   Управление пулами соединений и временем ожидания запросов
   Мониторинг производительности и сбор метрик

   Модуль: `trustgraph-flow/trustgraph/retrieval/graph_rag/query_optimizer.py`

### Модели данных

#### Оптимизированное состояние обхода графа

Движок обхода поддерживает состояние для предотвращения избыточных операций:

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

Этот подход позволяет:
Эффективное обнаружение циклов за счет отслеживания посещенных сущностей.
Подготовку запросов пакетами на каждом уровне обхода.
Экономичное использование памяти для управления состоянием.
Раннее завершение, когда достигнуты ограничения по размеру.

#### Улучшенная структура кэша

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

#### Структуры пакетных запросов

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

#### Новые API:

**API GraphTraversal**
```python
async def optimized_follow_edges_batch(
    entities: List[str],
    max_depth: int,
    triple_limit: int,
    max_subgraph_size: int
) -> Set[Tuple[str, str, str]]
```

**API для разрешения меток пакетов**
```python
async def resolve_labels_batch(
    entities: List[str],
    cache_manager: CacheManager
) -> Dict[str, str]
```

**API управления кэшем**
```python
class CacheManager:
    async def get_or_fetch_label(self, entity: str) -> str
    async def get_or_fetch_embeddings(self, query: str) -> List[float]
    async def cache_query_result(self, query_hash: str, result: Any, ttl: int)
    def get_cache_statistics(self) -> CacheStatistics
```

#### Измененные API:

**GraphRag.query()** - Улучшено с оптимизациями производительности:
Добавлен параметр cache_manager для управления кэшем.
Добавлено возвращаемое значение performance_metrics.
Добавлен параметр query_timeout для повышения надежности.

**Класс Query** - Рефакторинг для пакетной обработки:
Замена обработки отдельных сущностей на пакетные операции.
Добавлены асинхронные контекстные менеджеры для очистки ресурсов.
Добавлены обратные вызовы для отслеживания прогресса длительных операций.

### Детали реализации

#### Фаза 0: Критическая архитектурная реорганизация жизненного цикла

**Текущая проблемная реализация:**
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

**Оптимизированная архитектура с длительным сроком службы:**
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

Это архитектурное изменение обеспечивает:
**Сокращение количества запросов к базе данных на 10-20%** для графов с общими связями (по сравнению с текущими 0%)
**Устранение накладных расходов на создание объектов** для каждого запроса
**Постоянное использование пула соединений и повторное использование клиентов**
**Оптимизация между запросами** в пределах временных окон TTL кэша

**Важное ограничение согласованности кэша:**
Долгосрочное кэширование создает риск устаревания данных, когда сущности/метки удаляются или изменяются в базовом графе. Кэш LRU с TTL обеспечивает баланс между повышением производительности и актуальностью данных, но не может обнаруживать изменения в графе в режиме реального времени.

#### Фаза 1: Оптимизация обхода графа

**Проблемы текущей реализации:**
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

**Оптимизированная реализация:**
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

#### Фаза 2: Параллельное разрешение меток

**Текущая последовательная реализация:**
```python
# INEFFICIENT: Sequential processing
for edge in subgraph:
    s = await self.maybe_label(edge[0])  # Individual query
    p = await self.maybe_label(edge[1])  # Individual query
    o = await self.maybe_label(edge[2])  # Individual query
```

**Оптимизированная параллельная реализация:**
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

#### Фаза 3: Продвинутая стратегия кэширования

**Кэш LRU с TTL:**
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

#### Фаза 4: Оптимизация запросов и мониторинг

**Сбор показателей производительности:**
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

**Тайм-аут запроса и предохранитель:**
```python
async def execute_with_timeout(self, query_func, timeout: int = 30):
    try:
        return await asyncio.wait_for(query_func(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"Query timeout after {timeout}s")
        raise GraphRagTimeoutError(f"Query exceeded timeout of {timeout}s")
```

## Соображения по обеспечению согласованности кэша

**Компромиссы между актуальностью данных:**
**Кэш меток (TTL 5 минут):** Риск предоставления устаревших меток сущностей (удаленных или переименованных).
**Отсутствие кэширования вложений:** Не требуется, так как вложения уже кэшируются для каждого запроса.
**Отсутствие кэширования результатов:** Предотвращает получение устаревших результатов подграфов из-за удаленных сущностей/связей.

**Стратегии смягчения:**
**Консервативные значения TTL:** Баланс между приростом производительности (10-20%) и актуальностью данных.
**Хуки для аннулирования кэша:** Необязательная интеграция с событиями изменения графа.
**Панели мониторинга:** Отслеживание показателей попадания в кэш по сравнению с инцидентами устаревания данных.
**Настраиваемые политики кэширования:** Возможность тонкой настройки для каждого развертывания в зависимости от частоты изменений.

**Рекомендуемая конфигурация кэша в зависимости от частоты изменений графа:**
**Высокая частота изменений (>100 изменений/час):** TTL=60 секунд, меньшие размеры кэша.
**Средняя частота изменений (10-100 изменений/час):** TTL=300 секунд (по умолчанию).
**Низкая частота изменений (<10 изменений/час):** TTL=600 секунд, большие размеры кэша.

## Соображения безопасности

**Предотвращение внедрения запросов:**
Проверка всех идентификаторов сущностей и параметров запроса.
Использование параметризованных запросов для всех взаимодействий с базой данных.
Реализация ограничений на сложность запросов для предотвращения атак типа "отказ в обслуживании" (DoS).

**Защита ресурсов:**
Применение ограничений на максимальный размер подграфа.
Реализация таймаутов запросов для предотвращения исчерпания ресурсов.
Добавление мониторинга и ограничений использования памяти.

**Контроль доступа:**
Поддержание существующей изоляции пользователей и коллекций.
Добавление ведения журнала аудита для операций, влияющих на производительность.
Реализация ограничения скорости для дорогостоящих операций.

## Соображения производительности

### Ожидаемые улучшения производительности

**Сокращение количества запросов:**
Сейчас: ~9000+ запросов для типичного запроса.
Оптимизировано: ~50-100 пакетных запросов (снижение на 98%).

**Улучшение времени отклика:**
Обход графа: 15-20 секунд → 3-5 секунд (в 4-5 раза быстрее).
Разрешение меток: 8-12 секунд → 2-4 секунды (в 3 раза быстрее).
Общий запрос: 25-35 секунд → 6-10 секунд (улучшение в 3-4 раза).

**Эффективность использования памяти:**
Ограниченные размеры кэша предотвращают утечки памяти.
Эффективные структуры данных уменьшают объем используемой памяти примерно на 40%.
Улучшен сбор мусора благодаря правильной очистке ресурсов.

**Реалистичные ожидания производительности:**
**Кэш меток:** Уменьшение количества запросов на 10-20% для графов с общими связями.
**Оптимизация пакетной обработки:** Уменьшение количества запросов на 50-80% (основная оптимизация).
**Оптимизация времени жизни объектов:** Исключение накладных расходов на создание объектов для каждого запроса.
**Общее улучшение:** Улучшение времени отклика в 3-4 раза, в основном за счет пакетной обработки.

**Улучшения масштабируемости:**
Поддержка графов знаний в 3-5 раза большего размера (ограничено потребностями согласованности кэша).
Увеличение количества одновременных запросов в 3-5 раза.
Лучшее использование ресурсов благодаря повторному использованию соединений.

### Мониторинг производительности

**Метрики в реальном времени:**
Время выполнения запросов по типу операции.
Показатели попадания в кэш и его эффективность.
Использование пула соединений с базой данных.
Использование памяти и влияние сборки мусора.

**Бенчмаркинг производительности:**
Автоматизированное регрессионное тестирование производительности
Тестирование нагрузки с использованием реалистичных объемов данных
Сравнительные тесты с текущей реализацией

## Стратегия тестирования

### Модульное тестирование
Тестирование отдельных компонентов для обхода графа, кэширования и разрешения меток
Эмуляция взаимодействия с базой данных для тестирования производительности
Тестирование вытеснения из кэша и истечения срока действия TTL
Обработка ошибок и сценарии таймаутов

### Интеграционное тестирование
Комплексное тестирование запросов GraphRAG с оптимизациями
Тестирование взаимодействия с базой данных с использованием реальных данных
Обработка одновременных запросов и управление ресурсами
Обнаружение утечек памяти и проверка очистки ресурсов

### Тестирование производительности
Тестирование производительности по сравнению с текущей реализацией
Тестирование нагрузки с различными размерами и сложностью графов
Стресс-тестирование для проверки лимитов памяти и соединений
Регрессионное тестирование для проверки улучшений производительности

### Тестирование совместимости
Проверка совместимости существующего API GraphRAG
Тестирование с различными бэкендами графовых баз данных
Проверка точности результатов по сравнению с текущей реализацией

## План реализации

### Прямой подход к реализации
Поскольку API могут изменяться, реализуйте оптимизации напрямую без сложности миграции:

1. **Замените метод `follow_edges`**: Перепишите с использованием пакетного итеративного обхода
2. **Оптимизируйте `get_labelgraph`**: Реализуйте параллельное разрешение меток
3. **Добавьте долгоживущий GraphRag**: Измените Processor для поддержания постоянной инстанции
4. **Реализуйте кэширование меток**: Добавьте кэш LRU с TTL в класс GraphRag

### Область изменений
**Класс запроса**: Замените ~50 строк в `follow_edges`, добавьте ~30 строк для обработки пакетов
**Класс GraphRag**: Добавьте слой кэширования (~40 строк)
**Класс Processor**: Измените для использования постоянной инстанции GraphRag (~20 строк)
**Всего**: ~140 строк целенаправленных изменений, в основном в существующих классах

## Временная шкала

**Неделя 1: Основная реализация**
Замените `follow_edges` пакетным итеративным обходом
Реализуйте параллельное разрешение меток в `get_labelgraph`
Добавьте долгоживущую инстанцию GraphRag в Processor
Реализуйте слой кэширования меток

**Неделя 2: Тестирование и интеграция**
Модульные тесты для новой логики обхода и кэширования
Бенчмаркинг производительности по сравнению с текущей реализацией
Интеграционное тестирование с реальными данными графа
Проверка кода и оптимизация

**Неделя 3: Развертывание**
Разверните оптимизированную реализацию
Отслеживайте улучшения производительности
Тонкая настройка TTL кэша и размеров пакетов на основе реального использования

## Открытые вопросы

**Пул соединений с базой данных**: Следует ли нам реализовать собственный пул соединений или использовать существующий пул соединений от клиента базы данных?
**Постоянство кэша**: Должны ли кэши меток и внедрений сохраняться после перезапуска службы?
**Распределенное кэширование**: Для развернутых в нескольких экземплярах систем следует ли нам реализовать распределенное кэширование с использованием Redis/Memcached?
**Формат результата запроса**: Следует ли нам оптимизировать внутреннее представление тройки для повышения эффективности использования памяти?
**Интеграция мониторинга**: Какие метрики следует предоставлять существующим системам мониторинга (Prometheus и т. д.)?

## Ссылки

[Оригинальная реализация GraphRAG](trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py)
[Принципы архитектуры TrustGraph](architecture-principles.md)
[Спецификация управления коллекциями](collection-management.md)
