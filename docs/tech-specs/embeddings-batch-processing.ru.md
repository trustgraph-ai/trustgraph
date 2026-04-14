---
layout: default
title: "Техническая спецификация пакетной обработки эмбеддингов"
parent: "Russian (Beta)"
---

# Техническая спецификация пакетной обработки эмбеддингов

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Обзор

Эта спецификация описывает оптимизации для сервиса эмбеддингов, предназначенные для поддержки пакетной обработки нескольких текстов в одном запросе. Текущая реализация обрабатывает один текст за раз, что не позволяет использовать значительные преимущества, которые предоставляют модели эмбеддингов при обработке пакетов.

1. **Неэффективность обработки одного текста**: Текущая реализация оборачивает отдельные тексты в список, что не позволяет в полной мере использовать возможности пакетной обработки FastEmbed.
2. **Накладные расходы на запрос для каждого текста**: Для каждого текста требуется отдельная передача сообщения Pulsar.
3. **Неэффективность вывода модели**: Модели эмбеддингов имеют фиксированные накладные расходы на пакет; небольшие пакеты приводят к неэффективному использованию ресурсов GPU/CPU.
4. **Последовательная обработка в вызывающих сервисах**: Основные сервисы перебирают элементы и вызывают эмбеддинги по одному.

## Цели

**Поддержка пакетного API**: Обеспечить возможность обработки нескольких текстов в одном запросе.
**Обратная совместимость**: Сохранить поддержку запросов для обработки одного текста.
**Значительное повышение производительности**: Стремиться к увеличению производительности в 5-10 раз для массовых операций.
**Снижение задержки на текст**: Уменьшить среднюю задержку при создании эмбеддингов для нескольких текстов.
**Эффективность использования памяти**: Обрабатывать пакеты без чрезмерного потребления памяти.
**Независимость от провайдера**: Поддерживать пакетную обработку для FastEmbed, Ollama и других провайдеров.
**Миграция вызывающих сервисов**: Обновить все сервисы, вызывающие эмбеддинги, для использования пакетного API, где это целесообразно.

## Контекст

### Текущая реализация - Сервис эмбеддингов

Реализация эмбеддингов в `trustgraph-flow/trustgraph/embeddings/fastembed/processor.py` демонстрирует значительную неэффективность:

```python
# fastembed/processor.py line 56
async def on_embeddings(self, text, model=None):
    use_model = model or self.default_model
    self._load_model(use_model)

    vecs = self.embeddings.embed([text])  # Single text wrapped in list

    return [v.tolist() for v in vecs]
```

**Проблемы:**

1. **Размер пакета 1**: Метод `embed()` FastEmbed оптимизирован для пакетной обработки, но мы всегда вызываем его с `[text]` - пакетом размера 1.

2. **Накладные расходы на каждый запрос**: Каждый запрос на получение эмбеддингов влечет за собой:
   Сериализацию/десериализацию сообщения Pulsar.
   Задержку сетевого обмена.
   Накладные расходы на запуск инференса модели.
   Накладные расходы на асинхронное планирование Python.

3. **Ограничение схемы**: Схема `EmbeddingsRequest` поддерживает только один текстовый фрагмент:
   ```python
   @dataclass
   class EmbeddingsRequest:
       text: str = ""  # Single text only
   ```

### Текущие вызывающие стороны - последовательная обработка

#### 1. API-шлюз

**Файл:** `trustgraph-flow/trustgraph/gateway/dispatch/embeddings.py`

Шлюз принимает запросы на однострочное создание векторных представлений через HTTP/WebSocket и перенаправляет их в сервис создания векторных представлений. В настоящее время нет пакетного интерфейса.

```python
class EmbeddingsRequestor(ServiceRequestor):
    # Handles single EmbeddingsRequest -> EmbeddingsResponse
    request_schema=EmbeddingsRequest,  # Single text only
    response_schema=EmbeddingsResponse,
```

**Влияние:** Внешние клиенты (веб-приложения, скрипты) должны выполнять N HTTP-запросов для встраивания N текстов.

#### 2. Сервис встраивания документов

**Файл:** `trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py`

Обрабатывает фрагменты документов по одному.

```python
async def on_message(self, msg, consumer, flow):
    v = msg.value()

    # Single chunk per request
    resp = await flow("embeddings-request").request(
        EmbeddingsRequest(text=v.chunk)
    )
    vectors = resp.vectors
```

**Влияние:** Каждый фрагмент документа требует отдельного вызова для создания эмбеддинга. Документ, состоящий из 100 фрагментов, = 100 запросов на создание эмбеддингов.

#### 3. Сервис создания графовых эмбеддингов

**Файл:** `trustgraph-flow/trustgraph/embeddings/graph_embeddings/embeddings.py`

Выполняет итерации по сущностям и создает эмбеддинг для каждой из них последовательно:

```python
async def on_message(self, msg, consumer, flow):
    for entity in v.entities:
        # Serial embedding - one entity at a time
        vectors = await flow("embeddings-request").embed(
            text=entity.context
        )
        entities.append(EntityEmbeddings(
            entity=entity.entity,
            vectors=vectors,
            chunk_id=entity.chunk_id,
        ))
```

**Влияние:** Сообщение, содержащее 50 сущностей, приводит к 50 последовательным запросам на создание векторных представлений. Это серьезное препятствие при построении графа знаний.

#### 4. Сервис создания векторных представлений строк

**Файл:** `trustgraph-flow/trustgraph/embeddings/row_embeddings/embeddings.py`

Выполняет итерации по уникальным текстам и создает векторное представление для каждого из них последовательно:

```python
async def on_message(self, msg, consumer, flow):
    for text, (index_name, index_value) in texts_to_embed.items():
        # Serial embedding - one text at a time
        vectors = await flow("embeddings-request").embed(text=text)

        embeddings_list.append(RowIndexEmbedding(
            index_name=index_name,
            index_value=index_value,
            text=text,
            vectors=vectors
        ))
```

**Влияние:** Обработка таблицы с 100 уникальными индексированными значениями = 100 последовательных запросов на создание векторных представлений.

#### 5. EmbeddingsClient (Базовый клиент)

**Файл:** `trustgraph-base/trustgraph/base/embeddings_client.py`

Клиент, используемый всеми процессорами потоков, поддерживает только создание векторных представлений для одного текстового фрагмента:

```python
class EmbeddingsClient(RequestResponse):
    async def embed(self, text, timeout=30):
        resp = await self.request(
            EmbeddingsRequest(text=text),  # Single text
            timeout=timeout
        )
        return resp.vectors
```

**Влияние:** Все клиенты, использующие этот компонент, ограничены операциями с одним текстовым фрагментом.

#### 6. Инструменты командной строки

**Файл:** `trustgraph-cli/trustgraph/cli/invoke_embeddings.py`

Инструмент командной строки принимает один текстовый аргумент:

```python
def query(url, flow_id, text, token=None):
    result = flow.embeddings(text=text)  # Single text
    vectors = result.get("vectors", [])
```

**Влияние:** Пользователи не могут выполнять пакетную вставку из командной строки. Обработка файла текстов требует N вызовов.

#### 7. Python SDK

Python SDK предоставляет два клиентских класса для взаимодействия со службами TrustGraph. Оба поддерживают только вставку одного текста.

**Файл:** `trustgraph-base/trustgraph/api/flow.py`

```python
class FlowInstance:
    def embeddings(self, text):
        """Get embeddings for a single text"""
        input = {"text": text}
        return self.request("service/embeddings", input)["vectors"]
```

**Файл:** `trustgraph-base/trustgraph/api/socket_client.py`

```python
class SocketFlowInstance:
    def embeddings(self, text: str, **kwargs: Any) -> Dict[str, Any]:
        """Get embeddings for a single text via WebSocket"""
        request = {"text": text}
        return self.client._send_request_sync(
            "embeddings", self.flow_id, request, False
        )
```

**Влияние:** Разработчикам Python, использующим SDK, необходимо перебирать тексты и выполнять N отдельных API-запросов. Поддержка пакетной обработки векторов для пользователей SDK отсутствует.

### Влияние на производительность

Для типичного извлечения данных (1000 текстовых фрагментов):
**Текущая ситуация:** 1000 отдельных запросов, 1000 вызовов модели для получения векторов.
**Пакетная обработка (batch_size=32):** 32 запроса, 32 вызова модели для получения векторов (снижение на 96,8%).

Для получения векторов графа (сообщение с 50 сущностями):
**Текущая ситуация:** 50 последовательных вызовов `await`, ~5-10 секунд.
**Пакетная обработка:** 1-2 пакетных вызова, ~0,5-1 секунда (улучшение в 5-10 раз).

Библиотеки FastEmbed и аналогичные достигают почти линейного увеличения производительности при увеличении размера пакета до пределов аппаратного обеспечения (обычно 32-128 текстов на пакет).

## Техническое проектирование

### Архитектура

Оптимизация пакетной обработки векторов требует изменений в следующих компонентах:

#### 1. **Улучшение схемы данных**
   Расширить `EmbeddingsRequest` для поддержки нескольких текстов.
   Расширить `EmbeddingsResponse` для возврата нескольких наборов векторов.
   Сохранить обратную совместимость с запросами для одного текста.

   Модуль: `trustgraph-base/trustgraph/schema/services/llm.py`

#### 2. **Улучшение базового сервиса**
   Обновить `EmbeddingsService` для обработки пакетных запросов.
   Добавить конфигурацию размера пакета.
   Реализовать обработку запросов с учетом пакетной обработки.

   Модуль: `trustgraph-base/trustgraph/base/embeddings_service.py`

#### 3. **Обновления для процессоров провайдеров**
   Обновить процессор FastEmbed для передачи полного пакета в `embed()`.
   Обновить процессор Ollama для обработки пакетов (если поддерживается).
   Добавить последовательную обработку в качестве запасного варианта для провайдеров, не поддерживающих пакетную обработку.

   Модули:
   `trustgraph-flow/trustgraph/embeddings/fastembed/processor.py`
   `trustgraph-flow/trustgraph/embeddings/ollama/processor.py`

#### 4. **Улучшение клиентской библиотеки**
   Добавить метод пакетной обработки векторов в `EmbeddingsClient`.
   Поддерживать как одиночные, так и пакетные API.
   Добавить автоматическую пакетную обработку для больших входных данных.

   Модуль: `trustgraph-base/trustgraph/base/embeddings_client.py`

#### 5. **Обновления для вызывающего кода - процессоров потоков**
   Обновить `graph_embeddings` для пакетной обработки контекстов сущностей.
   Обновить `row_embeddings` для пакетной обработки текстов для индексации.
   Обновить `document_embeddings`, если пакетная обработка сообщений возможна.

   Модули:
   `trustgraph-flow/trustgraph/embeddings/graph_embeddings/embeddings.py`
   `trustgraph-flow/trustgraph/embeddings/row_embeddings/embeddings.py`
   `trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py`

#### 6. **Улучшение API-шлюза**
   Добавить конечную точку для пакетной обработки векторов.
   Поддерживать массив текстов в теле запроса.

   Модуль: `trustgraph-flow/trustgraph/gateway/dispatch/embeddings.py`

#### 7. **Улучшение инструмента командной строки (CLI)**
   Добавить поддержку нескольких текстов или ввода из файла.
   Добавить параметр размера пакета.

   Модуль: `trustgraph-cli/trustgraph/cli/invoke_embeddings.py`

#### 8. **Улучшение Python SDK**
   Добавить метод `embeddings_batch()` в `FlowInstance`.
   Добавить метод `embeddings_batch()` в `SocketFlowInstance`.
   Поддерживать как одиночные, так и пакетные API для пользователей SDK.

   Модули:
   `trustgraph-base/trustgraph/api/flow.py`
   `trustgraph-base/trustgraph/api/socket_client.py`

### Модели данных

#### EmbeddingsRequest

```python
@dataclass
class EmbeddingsRequest:
    texts: list[str] = field(default_factory=list)
```

Использование:
Одиночный текст: `EmbeddingsRequest(texts=["hello world"])`
Пакетный режим: `EmbeddingsRequest(texts=["text1", "text2", "text3"])`

#### EmbeddingsResponse

```python
@dataclass
class EmbeddingsResponse:
    error: Error | None = None
    vectors: list[list[list[float]]] = field(default_factory=list)
```

Структура ответа:
`vectors[i]` содержит набор векторов для `texts[i]`
Каждый набор векторов имеет размер `list[list[float]]` (модели могут возвращать несколько векторов для одного текста)
Пример: 3 текста → `vectors` имеет 3 записи, каждая из которых содержит векторные представления этого текста

### API

#### EmbeddingsClient

```python
class EmbeddingsClient(RequestResponse):
    async def embed(
        self,
        texts: list[str],
        timeout: float = 300,
    ) -> list[list[list[float]]]:
        """
        Embed one or more texts in a single request.

        Args:
            texts: List of texts to embed
            timeout: Timeout for the operation

        Returns:
            List of vector sets, one per input text
        """
        resp = await self.request(
            EmbeddingsRequest(texts=texts),
            timeout=timeout
        )
        if resp.error:
            raise RuntimeError(resp.error.message)
        return resp.vectors
```

#### Конечная точка API Gateway для встраиваемых объектов

Обновленная конечная точка, поддерживающая однократную или пакетную генерацию встраиваемых объектов:

```
POST /api/v1/embeddings
Content-Type: application/json

{
    "texts": ["text1", "text2", "text3"],
    "flow_id": "default"
}

Response:
{
    "vectors": [
        [[0.1, 0.2, ...]],
        [[0.3, 0.4, ...]],
        [[0.5, 0.6, ...]]
    ]
}
```

### Детали реализации

#### Этап 1: Изменения схемы

**EmbeddingsRequest:**
```python
@dataclass
class EmbeddingsRequest:
    texts: list[str] = field(default_factory=list)
```

**Ответ Embeddings:**
```python
@dataclass
class EmbeddingsResponse:
    error: Error | None = None
    vectors: list[list[list[float]]] = field(default_factory=list)
```

**Обновлен класс EmbeddingsService.on_request:**
```python
async def on_request(self, msg, consumer, flow):
    request = msg.value()
    id = msg.properties()["id"]
    model = flow("model")

    vectors = await self.on_embeddings(request.texts, model=model)
    response = EmbeddingsResponse(error=None, vectors=vectors)

    await flow("response").send(response, properties={"id": id})
```

#### Фаза 2: Обновление процессора FastEmbed

**Текущая (неэффективная):**
```python
async def on_embeddings(self, text, model=None):
    use_model = model or self.default_model
    self._load_model(use_model)
    vecs = self.embeddings.embed([text])  # Batch of 1
    return [v.tolist() for v in vecs]
```

**Обновлено:**
```python
async def on_embeddings(self, texts: list[str], model=None):
    """Embed texts - processes all texts in single model call"""
    if not texts:
        return []

    use_model = model or self.default_model
    self._load_model(use_model)

    # FastEmbed handles the full batch efficiently
    all_vecs = list(self.embeddings.embed(texts))

    # Return list of vector sets, one per input text
    return [[v.tolist()] for v in all_vecs]
```

#### Фаза 3: Обновление сервиса графовых вложений

**Текущая (последовательная):**
```python
async def on_message(self, msg, consumer, flow):
    entities = []
    for entity in v.entities:
        vectors = await flow("embeddings-request").embed(text=entity.context)
        entities.append(EntityEmbeddings(...))
```

**Обновлено (пакетно):**
```python
async def on_message(self, msg, consumer, flow):
    # Collect all contexts
    contexts = [entity.context for entity in v.entities]

    # Single batch embedding call
    all_vectors = await flow("embeddings-request").embed(texts=contexts)

    # Pair results with entities
    entities = [
        EntityEmbeddings(
            entity=entity.entity,
            vectors=vectors[0],  # First vector from the set
            chunk_id=entity.chunk_id,
        )
        for entity, vectors in zip(v.entities, all_vectors)
    ]
```

#### Фаза 4: Обновление сервиса встраивания данных.

**Текущая (последовательная):**
```python
for text, (index_name, index_value) in texts_to_embed.items():
    vectors = await flow("embeddings-request").embed(text=text)
    embeddings_list.append(RowIndexEmbedding(...))
```

**Обновлено (пакетно):**
```python
# Collect texts and metadata
texts = list(texts_to_embed.keys())
metadata = list(texts_to_embed.values())

# Single batch embedding call
all_vectors = await flow("embeddings-request").embed(texts=texts)

# Pair results
embeddings_list = [
    RowIndexEmbedding(
        index_name=meta[0],
        index_value=meta[1],
        text=text,
        vectors=vectors[0]  # First vector from the set
    )
    for text, meta, vectors in zip(texts, metadata, all_vectors)
]
```

#### Фаза 5: Улучшение инструмента командной строки (CLI).

**Обновленный CLI:**
```python
def main():
    parser = argparse.ArgumentParser(...)

    parser.add_argument(
        'text',
        nargs='*',  # Zero or more texts
        help='Text(s) to convert to embedding vectors',
    )

    parser.add_argument(
        '-f', '--file',
        help='File containing texts (one per line)',
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='Batch size for processing (default: 32)',
    )
```

Использование:
```bash
# Single text (existing)
tg-invoke-embeddings "hello world"

# Multiple texts
tg-invoke-embeddings "text one" "text two" "text three"

# From file
tg-invoke-embeddings -f texts.txt --batch-size 64
```

#### Фаза 6: Улучшение SDK для Python

**FlowInstance (HTTP-клиент):**

```python
class FlowInstance:
    def embeddings(self, texts: list[str]) -> list[list[list[float]]]:
        """
        Get embeddings for one or more texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of vector sets, one per input text
        """
        input = {"texts": texts}
        return self.request("service/embeddings", input)["vectors"]
```

**SocketFlowInstance (клиент WebSocket):**

```python
class SocketFlowInstance:
    def embeddings(self, texts: list[str], **kwargs: Any) -> list[list[list[float]]]:
        """
        Get embeddings for one or more texts via WebSocket.

        Args:
            texts: List of texts to embed

        Returns:
            List of vector sets, one per input text
        """
        request = {"texts": texts}
        response = self.client._send_request_sync(
            "embeddings", self.flow_id, request, False
        )
        return response["vectors"]
```

**Примеры использования SDK:**

```python
# Single text
vectors = flow.embeddings(["hello world"])
print(f"Dimensions: {len(vectors[0][0])}")

# Batch embedding
texts = ["text one", "text two", "text three"]
all_vectors = flow.embeddings(texts)

# Process results
for text, vecs in zip(texts, all_vectors):
    print(f"{text}: {len(vecs[0])} dimensions")
```

## Соображения безопасности

**Ограничения на размер запроса**: Установите максимальный размер пакета для предотвращения исчерпания ресурсов.
**Обработка таймаутов**: Адаптируйте таймауты в соответствии с размером пакета.
**Ограничения памяти**: Отслеживайте использование памяти для больших пакетов.
**Проверка входных данных**: Проверяйте все тексты в пакете перед обработкой.

## Соображения производительности

### Ожидаемые улучшения

**Производительность:**
Для одного текста: ~10-50 текстов/секунду (в зависимости от модели).
Для пакета (размер 32): ~200-500 текстов/секунду (улучшение в 5-10 раз).

**Задержка на текст:**
Для одного текста: 50-200 мс на текст.
Для пакета (размер 32): 5-20 мс на текст (в среднем).

**Улучшения для конкретных сервисов:**

| Сервис | Текущее значение | Пакетный режим | Улучшение |
|---------|---------|---------|-------------|
| Векторные представления графов (50 сущностей) | 5-10 секунд | 0.5-1 секунда | 5-10x |
| Векторные представления строк (100 текстов) | 10-20 секунд | 1-2 секунды | 5-10x |
| Импорт документов (1000 фрагментов) | 100-200 секунд | 10-30 секунд | 5-10x |

### Параметры конфигурации

```python
# Recommended defaults
DEFAULT_BATCH_SIZE = 32
MAX_BATCH_SIZE = 128
BATCH_TIMEOUT_MULTIPLIER = 2.0
```

## Стратегия тестирования

### Модульное тестирование
Обработка однострочных вложений (обратная совместимость)
Обработка пустых пакетов
Применение максимального размера пакета
Обработка ошибок при частичных сбоях пакета

### Интеграционное тестирование
Полная обработка пакетов через Pulsar
Обработка пакетов сервисом графовых вложений
Обработка пакетов сервисом строковых вложений
API-шлюз для пакетных операций

### Тестирование производительности
Сравнение производительности при обработке отдельных элементов и пакетов
Использование памяти при различных размерах пакетов
Анализ распределения задержек

## План миграции

Это версия с критическими изменениями. Все этапы реализованы одновременно.

### Этап 1: Изменения схемы
Заменить `text: str` на `texts: list[str]` в EmbeddingsRequest
Изменить тип `vectors` на `list[list[list[float]]]` в EmbeddingsResponse

### Этап 2: Обновление процессоров
Обновить сигнатуру `on_embeddings` в процессорах FastEmbed и Ollama
Обрабатывать полный пакет за один вызов модели

### Этап 3: Обновление клиентской части
Обновить `EmbeddingsClient.embed()` для приема `texts: list[str]`

### Этап 4: Обновление вызывающего кода
Обновить graph_embeddings для пакетной обработки контекстов сущностей
Обновить row_embeddings для пакетной обработки текстов индекса
Обновить document_embeddings для использования новой схемы
Обновить инструмент командной строки

### Этап 5: API-шлюз
Обновить конечную точку для вложений в соответствии с новой схемой

### Этап 6: Python SDK
Обновить сигнатуру `FlowInstance.embeddings()`
Обновить сигнатуру `SocketFlowInstance.embeddings()`

## Открытые вопросы

**Потоковая передача больших пакетов**: Следует ли нам поддерживать потоковую передачу результатов для очень больших пакетов (>100 текстов)?
**Ограничения, специфичные для поставщиков**: Как нам обрабатывать поставщиков с разными максимальными размерами пакетов?
**Обработка частичных сбоев**: Если один текст в пакете завершается сбоем, следует ли нам завершать весь пакет или возвращать частичные результаты?
**Пакетная обработка документов**: Следует ли нам выполнять пакетную обработку по нескольким сообщениям Chunk или сохранять обработку для каждого сообщения?

## Ссылки

[Документация FastEmbed](https://github.com/qdrant/fastembed)
[API вложений Ollama](https://github.com/ollama/ollama)
[Реализация сервиса вложений](trustgraph-base/trustgraph/base/embeddings_service.py)
[Оптимизация производительности GraphRAG](graphrag-performance-optimization.md)
