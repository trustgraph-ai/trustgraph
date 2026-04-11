# Объяснимость во время выполнения запроса

## Статус

Реализовано

## Обзор

Эта спецификация описывает, как GraphRAG записывает и передает данные об объяснимости во время выполнения запроса. Цель - полная отслеживаемость: от окончательного ответа до выбранных ребер и исходных документов.

Объяснимость во время выполнения запроса фиксирует действия, которые выполняет конвейер GraphRAG во время рассуждений. Она связана с информацией о происхождении, которая записывается во время извлечения и фиксирует, откуда взялись факты графа знаний.

## Терминология

| Термин | Определение |
|------|------------|
| **Объяснимость** | Запись о том, как был получен результат |
| **Сессия** | Одиночное выполнение запроса GraphRAG |
| **Выбор ребра** | Выбор релевантных ребер с использованием LLM и обоснованием |
| **Цепь происхождения** | Путь от ребра → фрагмента → страницы → документа |

## Архитектура

### Поток объяснимости

```
GraphRAG Query
    │
    ├─► Session Activity
    │       └─► Query text, timestamp
    │
    ├─► Retrieval Entity
    │       └─► All edges retrieved from subgraph
    │
    ├─► Selection Entity
    │       └─► Selected edges with LLM reasoning
    │           └─► Each edge links to extraction provenance
    │
    └─► Answer Entity
            └─► Reference to synthesized response (in librarian)
```

### Двухэтапная конвейерная обработка GraphRAG

1. **Выбор ребер**: LLM выбирает релевантные ребра из подграфа, предоставляя обоснование для каждого.
2. **Синтез**: LLM генерирует ответ, используя только выбранные ребра.

Такое разделение обеспечивает объяснимость - мы точно знаем, какие ребра внесли вклад.

### Хранилище

Тройки, обеспечивающие объяснимость, хранятся в настраиваемой коллекции (по умолчанию: `explainability`).
Используется онтология PROV-O для отношений происхождения.
RDF-star для ссылок на ребра.
Содержимое ответа хранится в сервисе librarian (не встроено - слишком большой объем).

### Потоковая передача в реальном времени

События, обеспечивающие объяснимость, передаются клиенту в процессе выполнения запроса:

1. Создание сессии → событие отправлено.
2. Получение ребер → событие отправлено.
3. Выбор ребер с обоснованием → событие отправлено.
4. Синтез ответа → событие отправлено.

Клиент получает `explain_id` и `explain_collection` для получения полной информации.

## Структура URI

Все URI используют пространство имен `urn:trustgraph:` с UUID:

| Сущность | Шаблон URI |
|--------|-------------|
| Сессия | `urn:trustgraph:session:{uuid}` |
| Получение | `urn:trustgraph:prov:retrieval:{uuid}` |
| Выбор | `urn:trustgraph:prov:selection:{uuid}` |
| Ответ | `urn:trustgraph:prov:answer:{uuid}` |
| Выбор ребра | `urn:trustgraph:prov:edge:{uuid}:{index}` |

## Модель RDF (PROV-O)

### Сессия активности

```turtle
<session-uri> a prov:Activity ;
    rdfs:label "GraphRAG query session" ;
    prov:startedAtTime "2024-01-15T10:30:00Z" ;
    tg:query "What was the War on Terror?" .
```

### Получение сущности

```turtle
<retrieval-uri> a prov:Entity ;
    rdfs:label "Retrieved edges" ;
    prov:wasGeneratedBy <session-uri> ;
    tg:edgeCount 50 .
```

### Выбор сущности

```turtle
<selection-uri> a prov:Entity ;
    rdfs:label "Selected edges" ;
    prov:wasDerivedFrom <retrieval-uri> ;
    tg:selectedEdge <edge-sel-0> ;
    tg:selectedEdge <edge-sel-1> .

<edge-sel-0> tg:edge << <s> <p> <o> >> ;
    tg:reasoning "This edge establishes the key relationship..." .
```

### Ответная сущность

```turtle
<answer-uri> a prov:Entity ;
    rdfs:label "GraphRAG answer" ;
    prov:wasDerivedFrom <selection-uri> ;
    tg:document <urn:trustgraph:answer:{uuid}> .
```

`tg:document` ссылается на ответ, хранящийся в сервисе librarian.

## Константы пространства имен

Определены в `trustgraph-base/trustgraph/provenance/namespaces.py`:

| Константа | URI |
|----------|-----|
| `TG_QUERY` | `https://trustgraph.ai/ns/query` |
| `TG_EDGE_COUNT` | `https://trustgraph.ai/ns/edgeCount` |
| `TG_SELECTED_EDGE` | `https://trustgraph.ai/ns/selectedEdge` |
| `TG_EDGE` | `https://trustgraph.ai/ns/edge` |
| `TG_REASONING` | `https://trustgraph.ai/ns/reasoning` |
| `TG_CONTENT` | `https://trustgraph.ai/ns/content` |
| `TG_DOCUMENT` | `https://trustgraph.ai/ns/document` |

## Схема GraphRagResponse

```python
@dataclass
class GraphRagResponse:
    error: Error | None = None
    response: str = ""
    end_of_stream: bool = False
    explain_id: str | None = None
    explain_collection: str | None = None
    message_type: str = ""  # "chunk" or "explain"
    end_of_session: bool = False
```

### Типы сообщений

| message_type | Назначение |
|--------------|---------|
| `chunk` | Текстовый ответ (потоковый или окончательный) |
| `explain` | Событие, связанное с объяснимостью, с ссылкой IRI |

### Жизненный цикл сессии

1. Несколько сообщений `explain` (сессия, получение, выбор, ответ)
2. Несколько сообщений `chunk` (потоковый ответ)
3. Окончательное сообщение `chunk` с `end_of_session=True`

## Формат выбора ребер

LLM возвращает JSONL с выбранными ребрами:

```jsonl
{"id": "edge-hash-1", "reasoning": "This edge shows the key relationship..."}
{"id": "edge-hash-2", "reasoning": "Provides supporting evidence..."}
```

`id` является хешем `(labeled_s, labeled_p, labeled_o)`, вычисленным с помощью `edge_id()`.

## Сохранение URI

### Проблема

GraphRAG отображает для LLM удобочитаемые метки, но для отслеживания происхождения необходимы исходные URI.

### Решение

`get_labelgraph()` возвращает следующее:
`labeled_edges`: Список `(label_s, label_p, label_o)` для LLM
`uri_map`: Словарь, сопоставляющий `edge_id(labels)` → `(uri_s, uri_p, uri_o)`

При хранении данных для объяснения используются URI из `uri_map`.

## Отслеживание происхождения

### От узла к источнику

Выбранные узлы можно проследить до исходных документов:

1. Запрос для получения содержащего подграфа: `?subgraph tg:contains <<s p o>>`
2. Переход по цепочке `prov:wasDerivedFrom` к корневому документу
3. Каждый шаг в цепочке: фрагмент → страница → документ

### Поддержка тройных наборов в Cassandra

Сервис запросов Cassandra поддерживает сопоставление тройных наборов:

```python
# In get_term_value():
elif term.type == TRIPLE:
    return serialize_triple(term.triple)
```

Это позволяет выполнять запросы, такие как:
```
?subgraph tg:contains <<http://example.org/s http://example.org/p "value">>
```

## Использование интерфейса командной строки

```bash
tg-invoke-graph-rag --explainable -q "What was the War on Terror?"
```

### Формат вывода

```
[session] urn:trustgraph:session:abc123

[retrieval] urn:trustgraph:prov:retrieval:abc123

[selection] urn:trustgraph:prov:selection:abc123
    Selected 12 edge(s)
      Edge: (Guantanamo, definition, A detention facility...)
        Reason: Directly connects Guantanamo to the War on Terror
        Source: Chunk 1 → Page 2 → Beyond the Vigilant State

[answer] urn:trustgraph:prov:answer:abc123

Based on the provided knowledge statements...
```

### Особенности

События объяснения в реальном времени во время запроса.
Разрешение меток для компонентов ребер с помощью `rdfs:label`.
Отслеживание цепочки источников с помощью `prov:wasDerivedFrom`.
Кэширование меток для предотвращения повторных запросов.

## Реализованные файлы

| Файл | Назначение |
|------|---------|
| `trustgraph-base/trustgraph/provenance/uris.py` | Генераторы URI |
| `trustgraph-base/trustgraph/provenance/namespaces.py` | Константы пространства имен RDF |
| `trustgraph-base/trustgraph/provenance/triples.py` | Конструкторы троек |
| `trustgraph-base/trustgraph/schema/services/retrieval.py` | Схема GraphRagResponse |
| `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py` | Основной GraphRAG с сохранением URI |
| `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` | Сервис с интеграцией с библиотекарем |
| `trustgraph-flow/trustgraph/query/triples/cassandra/service.py` | Поддержка запросов троек в кавычках |
| `trustgraph-cli/trustgraph/cli/invoke_graph_rag.py` | CLI с отображением объяснений |

## Ссылки

PROV-O (W3C Provenance Ontology): https://www.w3.org/TR/prov-o/
RDF-star: https://w3c.github.io/rdf-star/
Происхождение во время извлечения: `docs/tech-specs/extraction-time-provenance.md`
