# Структурированные данные Pulsar: Изменения схемы

## Обзор

На основе спецификации `STRUCTURED_DATA.md`, этот документ предлагает необходимые дополнения и изменения схемы Pulsar для поддержки возможностей работы со структурированными данными в TrustGraph.

## Необходимые изменения схемы

### 1. Улучшения основной схемы

#### Улучшенное определение поля
Сущность `Field` в файле `core/primitives.py` требует дополнительных свойств:

```python
class Field(Record):
    name = String()
    type = String()  # int, string, long, bool, float, double, timestamp
    size = Integer()
    primary = Boolean()
    description = String()
    # НОВЫЕ ПОЛЯ:
    required = Boolean()  # Требуется ли поле
    enum_values = Array(String())  # Для полей типа enum
    indexed = Boolean()  # Нужно ли индексировать поле
```

### 2. Новые схемы знаний

#### 2.1 Отправка структурированных данных
Новый файл: `knowledge/structured.py`

```python
from pulsar.schema import Record, String, Bytes, Map
from ..core.metadata import Metadata

class StructuredDataSubmission(Record):
    metadata = Metadata()
    format = String()  # "json", "csv", "xml"
    schema_name = String()  # Ссылка на схему в конфигурации
    data = Bytes()  # Сырые данные для обработки
    options = Map(String())  # Опции, специфичные для формата
```

#### 2.2 Структурированный запрос

#### 3.1 Преобразование NLP в структурированный запрос
Новый файл: `services/nlp_query.py`

```python
from pulsar.schema import Record, String, Array, Map, Integer, Double
from ..core.primitives import Error

class NLPToStructuredQueryRequest(Record):
    natural_language_query = String()
    max_results = Integer()
    context_hints = Map(String())  # Дополнительный контекст для генерации запроса

class NLPToStructuredQueryResponse(Record):
    error = Error()
    graphql_query = String()  # Сгенерированный GraphQL запрос
    variables = Map(String())  # Переменные GraphQL, если есть
    detected_schemas = Array(String())  # Какие схемы затрагивает запрос
    confidence = Double()
```

#### 3.2 Структурированный запрос
Новый файл: `services/structured_query.py`

```python
from pulsar.schema import Record, String, Map, Array
from ..core.primitives import Error

class StructuredQueryRequest(Record):
    query = String()  # GraphQL запрос
    variables = Map(String())  # Переменные GraphQL
    operation_name = String()  # Дополнительное имя операции для документов с несколькими операциями

class StructuredQueryResponse(Record):
    error = Error()
    data = String()  # JSON-кодированный формат данных GraphQL
    errors = Array(String())  # Ошибки GraphQL, если есть
```

#### 2.2 Вывод извлечения объектов
Новый файл: `knowledge/object.py`

```python
from pulsar.schema import Record, String, Map, Double
from ..core.metadata import Metadata

class ExtractedObject(Record):
    metadata = Metadata()
    schema_name = String()  # Какая схема принадлежит этому объекту
    values = Map(String())  # Имя поля -> значение
    confidence = Double()
    source_span = String()  # Текстовый фрагмент, где был найден объект
```

### 4. Улучшенные схемы знаний

#### 4.1 Улучшение встраивания объектов
Обновите `knowledge/embeddings.py` для лучшей поддержки встраивания структурированных объектов:

```python
class StructuredObjectEmbedding(Record):
    metadata = Metadata()
    vectors = Array(Array(Double()))
    schema_name = String()
    object_id = String()  # Основной ключ
    field_embeddings = Map(Array(Double()))  # Встраивание для каждого поля
```

## Точки интеграции

### Интеграция потоков

Схемы будут использоваться в новых модулях потоков:
- `trustgraph-flow/trustgraph/decoding/structured` - Использует StructuredDataSubmission
- `trustgraph-flow/trustgraph/query/nlp_query/cassandra` - Использует схемы запросов NLP
- `trustgraph-flow/trustgraph/query/objects/cassandra` - Использует схемы структурированных запросов
- `trustgraph-flow/trustgraph/extract/object/row/` - Потребляет Chunk, производит ExtractedObject
- `trustgraph-flow/trustgraph/storage/objects/cassandra` - Использует схему Rows
- `trustgraph-flow/trustgraph/embeddings/object_embeddings/qdrant` - Использует схемы встраивания объектов

## Примечания по реализации

1. **Версионирование схемы**: Рассмотрите возможность добавления поля `version` к схеме RowSchema для поддержки будущих миграций.
2. **Система типов**: `Field.type` должна поддерживать все родные типы Cassandra.
3. **Операции пакета**: Большинство сервисов должны поддерживать как одиночные, так и пакетные операции.
4. **Обработка ошибок**: Необходимо обеспечить единообразное сообщение об ошибках во всех новых сервисах.
5. **Совместимость с существующими схемами**: Существующие схемы остаются неизменными, за исключением незначительных улучшений поля.

## Следующие шаги

1. Реализуйте файлы схем в новой структуре.
2. Обновите существующие сервисы для распознавания новых типов схем.
3. Реализуйте модули потоков, использующие эти схемы.
4. Добавьте конечные точки gateway/rev-gateway для новых сервисов.
5. Создайте модульные тесты для проверки схемы.