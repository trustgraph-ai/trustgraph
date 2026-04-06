# Технические спецификации: Оптимизация производительности базы знаний Cassandra

**Статус:** Черновик
**Автор:** Ассистент
**Дата:** 2025-09-18

## Обзор

Данная спецификация рассматривает проблемы производительности в реализации базы знаний TrustGraph на Cassandra и предлагает оптимизации для хранения и запросов RDF-тройных.

## Текущая реализация

### Структура данных

Текущая реализация использует структуру данных с одной таблицей в `trustgraph-flow/trustgraph/direct/cassandra_kg.py`:

```sql
CREATE TABLE triples (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY (collection, s, p, o)
);
```

**Вторичные индексы:**
`triples_s` по `s` (субъект)
`triples_p` по `p` (предикат)
`triples_o` по `o` (объект)

### Шаблоны запросов

Текущая реализация поддерживает 8 различных шаблонов запросов:

1. **get_all(collection, limit=50)** - Получить все тройки для коллекции
   ```sql
   SELECT s, p, o FROM triples WHERE collection = ? LIMIT 50
   ```

2. **get_s(collection, s, limit=10)** - Запрос по теме.
   ```sql
   SELECT p, o FROM triples WHERE collection = ? AND s = ? LIMIT 10
   ```

3. **get_p(collection, p, limit=10)** - Запрос по предикату.
   ```sql
   SELECT s, o FROM triples WHERE collection = ? AND p = ? LIMIT 10
   ```

4. **get_o(collection, o, limit=10)** - Запрос по объекту.
   ```sql
   SELECT s, p FROM triples WHERE collection = ? AND o = ? LIMIT 10
   ```

5. **get_sp(collection, s, p, limit=10)** - Запрос по субъекту + предикату.
   ```sql
   SELECT o FROM triples WHERE collection = ? AND s = ? AND p = ? LIMIT 10
   ```

6. **get_po(collection, p, o, limit=10)** - Запрос по предикату + объекту ⚠️
   ```sql
   SELECT s FROM triples WHERE collection = ? AND p = ? AND o = ? LIMIT 10 ALLOW FILTERING
   ```

7. **get_os(collection, o, s, limit=10)** - Запрос по объекту + субъекту ⚠️
   ```sql
   SELECT p FROM triples WHERE collection = ? AND o = ? AND s = ? LIMIT 10 ALLOW FILTERING
   ```

8. **get_spo(collection, s, p, o, limit=10)** - Точное соответствие тройке.
   ```sql
   SELECT s as x FROM triples WHERE collection = ? AND s = ? AND p = ? AND o = ? LIMIT 10
   ```

### Текущая архитектура

**Файл: `trustgraph-flow/trustgraph/direct/cassandra_kg.py`**
Один класс `KnowledgeGraph`, обрабатывающий все операции
Объединение подключений через глобальный список `_active_clusters`
Фиксированное имя таблицы: `"triples"`
Пространство ключей для каждой модели пользователя
Репликация SimpleStrategy с коэффициентом 1

**Точки интеграции:**
**Путь записи:** `trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
**Путь запроса:** `trustgraph-flow/trustgraph/query/triples/cassandra/service.py`
**Хранилище знаний:** `trustgraph-flow/trustgraph/tables/knowledge.py`

## Выявленные проблемы с производительностью

### Проблемы на уровне схемы

1. **Неэффективный дизайн первичного ключа**
   Текущий: `PRIMARY KEY (collection, s, p, o)`
   Приводит к плохой кластеризации для распространенных шаблонов доступа
   Заставляет использовать дорогостоящие вторичные индексы

2. **Чрезмерное использование вторичных индексов** ⚠️
   Три вторичных индекса на столбцах с высокой кардинальностью (s, p, o)
   Вторичные индексы в Cassandra дороги и плохо масштабируются
   Запросы 6 и 7 требуют `ALLOW FILTERING`, что указывает на плохое моделирование данных

3. **Риск "горячих" разделов**
   Один ключ раздела `collection` может создавать "горячие" разделы
   Большие коллекции будут концентрироваться на отдельных узлах
   Отсутствует стратегия распределения для балансировки нагрузки

### Проблемы на уровне запросов

1. **Использование ALLOW FILTERING** ⚠️
   Два типа запросов (get_po, get_os) требуют `ALLOW FILTERING`
   Эти запросы сканируют несколько разделов и чрезвычайно дороги
   Производительность ухудшается линейно с увеличением объема данных

2. **Неэффективные шаблоны доступа**
   Отсутствует оптимизация для распространенных шаблонов запросов RDF
   Отсутствуют составные индексы для часто используемых комбинаций запросов
   Не учитываются шаблоны обхода графов

3. **Отсутствие оптимизации запросов**
   Отсутствует кэширование подготовленных выражений
   Отсутствуют подсказки или стратегии оптимизации запросов
   Не учитывается постраничная навигация, кроме простого LIMIT

## Описание проблемы

Текущая реализация базы знаний Cassandra имеет два критических узких места в производительности:

### 1. Неэффективная производительность запроса get_po

Запрос `get_po(collection, p, o)` крайне неэффективен, поскольку требует `ALLOW FILTERING`:

```sql
SELECT s FROM triples WHERE collection = ? AND p = ? AND o = ? LIMIT 10 ALLOW FILTERING
```

**Почему это является проблемой:**
`ALLOW FILTERING` заставляет Cassandra сканировать все разделы внутри коллекции.
Производительность ухудшается линейно с увеличением размера данных.
Это распространенный шаблон запросов RDF (поиск объектов, имеющих определенную связь "субъект-предикат-объект").
Это создает значительную нагрузку на кластер по мере роста данных.

### 2. Неоптимальная стратегия кластеризации

Текущий первичный ключ `PRIMARY KEY (collection, s, p, o)` обеспечивает минимальные преимущества кластеризации:

**Проблемы с текущей кластеризацией:**
`collection` в качестве ключа раздела не обеспечивает эффективное распределение данных.
Большинство коллекций содержат разнообразные данные, что делает кластеризацию неэффективной.
Отсутствует учет типичных шаблонов доступа в запросах RDF.
Большие коллекции создают "горячие" разделы на отдельных узлах.
Столбцы кластеризации (s, p, o) не оптимизированы для типичных шаблонов обхода графа.

**Влияние:**
Запросы не получают выгоды от локальности данных.
Плохое использование кэша.
Неравномерное распределение нагрузки между узлами кластера.
"Узкие места" масштабируемости по мере роста коллекций.

## Предлагаемое решение: Стратегия денормализации с использованием 4 таблиц

### Обзор

Замените одну таблицу `triples` на четыре специализированные таблицы, каждая из которых оптимизирована для конкретных шаблонов запросов. Это устраняет необходимость во вторичных индексах и использовании ALLOW FILTERING, обеспечивая при этом оптимальную производительность для всех типов запросов. Четвертая таблица обеспечивает эффективное удаление коллекций, несмотря на составные ключи разделов.

### Новая структура схемы

**Таблица 1: Запросы, ориентированные на субъекты (triples_s)**
```sql
CREATE TABLE triples_s (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY ((collection, s), p, o)
);
```
**Оптимизирует:** get_s, get_sp, get_os
**Ключ разделения:** (collection, s) - Обеспечивает лучшую распределенность, чем только collection.
**Кластеризация:** (p, o) - Обеспечивает эффективный поиск по предикатам/объектам для субъекта.

**Таблица 2: Запросы предикат-объект (triples_p)**
```sql
CREATE TABLE triples_p (
    collection text,
    p text,
    o text,
    s text,
    PRIMARY KEY ((collection, p), o, s)
);
```
**Оптимизирует:** get_p, get_po (исключает ALLOW FILTERING!)
**Ключ партиции:** (collection, p) - Прямой доступ по предикату
**Кластеризация:** (o, s) - Эффективный обход объектов и субъектов

**Таблица 3: Объектно-ориентированные запросы (triples_o)**
```sql
CREATE TABLE triples_o (
    collection text,
    o text,
    s text,
    p text,
    PRIMARY KEY ((collection, o), s, p)
);
```
**Оптимизирует:** get_o
**Ключ разделения:** (collection, o) - Прямой доступ по объекту
**Кластеризация:** (s, p) - Эффективный обход по субъекту-предикату

**Таблица 4: Управление коллекциями и запросы SPO (triples_collection)**
```sql
CREATE TABLE triples_collection (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY (collection, s, p, o)
);
```
**Оптимизирует:** get_spo, delete_collection
**Разделительный ключ:** только коллекция - Обеспечивает эффективные операции на уровне коллекций.
**Кластеризация:** (s, p, o) - Стандартный порядок троек.
**Назначение:** Двойное использование для точного поиска SPO и в качестве индекса удаления.

### Отображение запросов

| Исходный запрос | Целевая таблица | Улучшение производительности |
|----------------|-------------|------------------------|
| get_all(collection) | triples_s | ALLOW FILTERING (приемлемо для сканирования) |
| get_s(collection, s) | triples_s | Прямой доступ к разделу |
| get_p(collection, p) | triples_p | Прямой доступ к разделу |
| get_o(collection, o) | triples_o | Прямой доступ к разделу |
| get_sp(collection, s, p) | triples_s | Раздел + кластеризация |
| get_po(collection, p, o) | triples_p | **Больше не требуется ALLOW FILTERING!** |
| get_os(collection, o, s) | triples_o | Раздел + кластеризация |
| get_spo(collection, s, p, o) | triples_collection | Точный поиск по ключу |
| delete_collection(collection) | triples_collection | Чтение индекса, пакетное удаление всех |

### Стратегия удаления коллекций

С составными раздельными ключами мы не можем просто выполнить `DELETE FROM table WHERE collection = ?`. Вместо этого:

1. **Фаза чтения:** Запрос `triples_collection` для перечисления всех троек:
   ```sql
   SELECT s, p, o FROM triples_collection WHERE collection = ?
   ```
   Это эффективно, поскольку `collection` является ключом секции для этой таблицы.

2. **Фаза удаления:** Для каждой тройки (s, p, o) удалите из всех 4 таблиц, используя полные ключи секций:
   ```sql
   DELETE FROM triples_s WHERE collection = ? AND s = ? AND p = ? AND o = ?
   DELETE FROM triples_p WHERE collection = ? AND p = ? AND o = ? AND s = ?
   DELETE FROM triples_o WHERE collection = ? AND o = ? AND s = ? AND p = ?
   DELETE FROM triples_collection WHERE collection = ? AND s = ? AND p = ? AND o = ?
   ```
   Обрабатывается пакетами по 100 элементов для повышения эффективности.

**Анализ компромиссов:**
✅ Поддерживает оптимальную производительность запросов с использованием распределенных разделов.
✅ Отсутствуют "горячие" разделы для больших коллекций.
❌ Более сложная логика удаления (чтение, а затем удаление).
❌ Время удаления пропорционально размеру коллекции.

### Преимущества

1. **Устраняет ALLOW FILTERING** - Каждый запрос имеет оптимальный путь доступа (за исключением полного сканирования).
2. **Не требуются вторичные индексы** - Каждая таблица ЯВЛЯЕТСЯ индексом для своего шаблона запросов.
3. **Более равномерное распределение данных** - Композитные ключи разделов эффективно распределяют нагрузку.
4. **Предсказуемая производительность** - Время выполнения запроса пропорционально размеру результата, а не общему объему данных.
5. **Использует сильные стороны Cassandra** - Разработана с учетом архитектуры Cassandra.
6. **Позволяет удалять коллекции** - `triples_collection` служит индексом для удаления.

## План реализации

### Файлы, требующие изменений

#### Основной файл реализации

**`trustgraph-flow/trustgraph/direct/cassandra_kg.py`** - Требуется полная переработка.

**Методы, требующие рефакторинга:**
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

#### Интеграционные файлы (изменения в логике не требуются)

**`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`**
Изменения не требуются - используется существующий API KnowledgeGraph.
Автоматически получает преимущества от улучшений производительности.

**`trustgraph-flow/trustgraph/query/triples/cassandra/service.py`**
Изменения не требуются - используется существующий API KnowledgeGraph.
Автоматически получает преимущества от улучшений производительности.

### Файлы для тестирования, требующие обновления

#### Юнит-тесты
**`tests/unit/test_storage/test_triples_cassandra_storage.py`**
Обновить ожидаемые результаты тестов в связи с изменениями схемы.
Добавить тесты для обеспечения согласованности между несколькими таблицами.
Проверить отсутствие использования ALLOW FILTERING в планах запросов.

**`tests/unit/test_query/test_triples_cassandra_query.py`**
Обновить утверждения о производительности.
Протестировать все 8 шаблонов запросов для новых таблиц.
Проверить маршрутизацию запросов к правильным таблицам.

#### Интеграционные тесты
**`tests/integration/test_cassandra_integration.py`**
Комплексное тестирование с новой схемой.
Сравнение результатов бенчмаркинга производительности.
Проверка согласованности данных между таблицами.

**`tests/unit/test_storage/test_cassandra_config_integration.py`**
Обновить тесты проверки схемы.
Протестировать сценарии миграции.

### Стратегия реализации

#### Фаза 1: Схема и основные методы
1. **Переписать метод `init()`** - Создать четыре таблицы вместо одной.
2. **Переписать метод `insert()`** - Выполнять пакетные записи во все четыре таблицы.
3. **Реализовать подготовленные запросы** - Для оптимальной производительности.
4. **Добавить логику маршрутизации таблиц** - Направлять запросы к оптимальным таблицам.
5. **Реализовать удаление коллекций** - Читать из triples_collection, пакетно удалять из всех таблиц.

#### Фаза 2: Оптимизация методов запросов
1. **Переписать каждый метод get_*** для использования оптимальной таблицы.
2. **Удалить все случаи использования ALLOW FILTERING**.
3. **Реализовать эффективное использование ключей кластеризации**.
4. **Добавить логирование производительности запросов**.

#### Фаза 3: Управление коллекциями
1. **Обновить `delete_collection()`** - Удалить из всех трех таблиц.
2. **Добавить проверку согласованности** - Обеспечить синхронизацию всех таблиц.
3. **Реализовать пакетные операции** - Для атомарных операций с несколькими таблицами.

### Ключевые детали реализации

#### Стратегия пакетной записи
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

#### Логика маршрутизации запросов
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

#### Логика удаления коллекции
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

#### Оптимизация подготовленных выражений
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

## Стратегия миграции

### Подход к миграции данных

#### Вариант 1: Развертывание Blue-Green (Рекомендуется)
1. **Разверните новую схему параллельно с существующей** - Временно используйте разные имена таблиц.
2. **Период двойной записи** - Записывайте данные как в старую, так и в новую схемы во время перехода.
3. **Фоновая миграция** - Скопируйте существующие данные в новые таблицы.
4. **Перенаправление операций чтения** - Направляйте запросы к новым таблицам после миграции данных.
5. **Удаление старых таблиц** - После периода проверки.

#### Вариант 2: Миграция на месте
1. **Добавление схемы** - Создайте новые таблицы в существующем пространстве ключей.
2. **Скрипт миграции данных** - Пакетная копия из старой таблицы в новые таблицы.
3. **Обновление приложения** - Разверните новый код после завершения миграции.
4. **Очистка старой таблицы** - Удалите старую таблицу и индексы.

### Обратная совместимость

#### Стратегия развертывания
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

#### Скрипт миграции
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

### Стратегия проверки

#### Проверки согласованности данных
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

## Стратегия тестирования

### Тестирование производительности

#### Сценарии для бенчмаркинга
1. **Сравнение производительности запросов**
   Показатели производительности до и после для всех 8 типов запросов
   Акцент на улучшении производительности запроса `get_po` (удаление `ALLOW FILTERING`)
   Измерение задержки запросов при различных объемах данных

2. **Тестирование нагрузки**
   Одновременное выполнение запросов
   Скорость записи с использованием пакетных операций
   Использование памяти и ЦП

3. **Тестирование масштабируемости**
   Производительность при увеличении размеров коллекций
   Распределение запросов по нескольким коллекциям
   Использование узлов кластера

#### Наборы тестовых данных
**Маленький:** 10 тысяч троек на коллекцию
**Средний:** 100 тысяч троек на коллекцию
**Большой:** 1 миллион и более троек на коллекцию
**Несколько коллекций:** Тестирование распределения партиций

### Функциональное тестирование

#### Обновления модульных тестов
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

#### Обновления результатов интеграционного тестирования
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

### План отката

#### Быстрая стратегия отката
1. **Переключение переменной окружения** - Немедленный возврат к устаревшим таблицам.
2. **Сохранение устаревших таблиц** - Не удалять до тех пор, пока производительность не будет подтверждена.
3. **Сигналы мониторинга** - Автоматический запуск отката на основе показателей ошибок/задержек.

#### Проверка отката
```python
def rollback_to_legacy():
    # Set environment variable
    os.environ['CASSANDRA_USE_LEGACY'] = 'true'

    # Restart services to pick up change
    restart_cassandra_services()

    # Validate functionality
    run_smoke_tests()
```

## Риски и соображения

### Риски производительности
**Увеличение времени записи** - 4 операции записи на каждую вставку (на 33% больше, чем при использовании 3-х таблиц)
**Избыточность хранения** - В 4 раза больше места для хранения (на 33% больше, чем при использовании 3-х таблиц)
**Сбои пакетной записи** - Требуется правильная обработка ошибок
**Сложность удаления** - Удаление коллекции требует цикла "чтение-удаление"

### Операционные риски
**Сложность миграции** - Миграция данных для больших наборов данных
**Проблемы с согласованностью** - Обеспечение синхронизации всех таблиц
**Недостаточность мониторинга** - Необходимы новые метрики для операций с несколькими таблицами

### Стратегии смягчения
1. **Постепенное внедрение** - Начните с небольших коллекций
2. **Комплексный мониторинг** - Отслеживайте все метрики производительности
3. **Автоматизированная проверка** - Постоянная проверка согласованности
4. **Возможность быстрого отката** - Выбор таблицы на основе среды

## Критерии успеха

### Улучшения производительности
[ ] **Устранение ALLOW FILTERING** - Запросы get_po и get_os выполняются без фильтрации
[ ] **Сокращение задержки запросов** - Улучшение времени отклика запросов на 50% или более
[ ] **Более равномерное распределение нагрузки** - Отсутствие "горячих" партиций, равномерная нагрузка на узлы кластера
[ ] **Масштабируемая производительность** - Время запроса пропорционально размеру результата, а не общему объему данных

### Функциональные требования
[ ] **Совместимость API** - Весь существующий код продолжает работать без изменений
[ ] **Согласованность данных** - Все три таблицы остаются синхронизированными
[ ] **Отсутствие потери данных** - Миграция сохраняет все существующие тройки
[ ] **Обратная совместимость** - Возможность отката к устаревшей схеме

### Операционные требования
[ ] **Безопасная миграция** - Развертывание по принципу "синий-зеленый" с возможностью отката
[ ] **Покрытие мониторингом** - Комплексные метрики для операций с несколькими таблицами
[ ] **Покрытие тестами** - Все шаблоны запросов протестированы с использованием эталонных показателей производительности
[ ] **Документация** - Обновленные процедуры развертывания и эксплуатации

## План

### Фаза 1: Реализация
[ ] Переписать `cassandra_kg.py` с использованием схемы нескольких таблиц
[ ] Реализовать пакетные операции записи
[ ] Добавить оптимизацию с использованием подготовленных выражений
[ ] Обновить модульные тесты

### Фаза 2: Интеграционное тестирование
[ ] Обновить интеграционные тесты
[ ] Эталонное тестирование производительности
[ ] Тестирование нагрузки с использованием реалистичных объемов данных
[ ] Скрипты проверки согласованности данных

### Фаза 3: Планирование миграции
[ ] Скрипты развертывания по принципу "синий-зеленый"
[ ] Инструменты миграции данных
[ ] Обновления панели мониторинга
[ ] Процедуры отката

### Фаза 4: Развертывание в производственной среде
[ ] Поэтапное развертывание в производственной среде
[ ] Мониторинг и проверка производительности
[ ] Очистка устаревших таблиц
[ ] Обновление документации

## Заключение

Эта стратегия денормализации с использованием нескольких таблиц напрямую решает две критические проблемы производительности:

1. **Устраняет дорогостоящий ALLOW FILTERING**, предоставляя оптимальные структуры таблиц для каждого шаблона запроса
2. **Улучшает эффективность кластеризации** за счет составных ключей партиций, которые правильно распределяют нагрузку

Этот подход использует сильные стороны Cassandra, сохраняя при этом полную совместимость API, что обеспечивает автоматическое получение преимуществ от улучшений производительности для существующего кода.
