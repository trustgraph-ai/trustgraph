---
layout: default
title: "Изменения в API Gateway: v1.8 до v2.1"
parent: "Russian (Beta)"
---

# Изменения в API Gateway: v1.8 до v2.1

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Обзор

API Gateway получил новые диспетчеры WebSocket для запросов на основе встраивания, новый REST-endpoint для потоковой передачи содержимого документов, и претерпел значительные изменения в формате представления данных, перейдя с `Value` на `Term`. Сервис "objects" был переименован в "rows".

---

## Новые диспетчеры WebSocket

Это новые сервисы запросов/ответов, доступные через WebSocket-мультиплексор по адресу `/api/v1/socket` (с фокусом на flow):

| Ключ сервиса | Описание |
|---|---|
| `document-embeddings` | Запросы на фрагменты документов по текстовому сходству. Используются схемы `DocumentEmbeddingsRequest`/`DocumentEmbeddingsResponse`. |
| `row-embeddings` | Запросы на структурированные данные по текстовому сходству по индексированным полям. Используются схемы `RowEmbeddingsRequest`/`RowEmbeddingsResponse`. |

Эти диспетчеры работают вместе с существующим диспетчером `graph-embeddings` (который уже был в v1.8, но мог быть обновлен).

### Полный список диспетчеров WebSocket (v2.1)

Сервисы запросов/ответов (через `/api/v1/flow/{flow}/service/{kind}` или WebSocket-мультиплексор):

- `agent`, `text-completion`, `prompt`, `mcp-tool`
- `graph-rag`, `document-rag`
- `embeddings`, `graph-embeddings`, `document-embeddings`
- `triples`, `rows`, `nlp-query`, `structured-query`, `structured-diag`
- `row-embeddings`

---

## Новый REST Endpoint

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/api/v1/document-stream` | Потоковая передача содержимого документов из библиотеки в виде сырых байтов. Параметры запроса: `user` (обязательно), `document-id` (обязательно), `chunk-size` (необязательно, значение по умолчанию 1MB). Возвращает содержимое документа в коде transfer encoding, который декодируется из base64 внутри. |

---

## Переименованный сервис: "objects" в "rows"

| v1.8 | v2.1 | Примечания |
|---|---|---|
| `objects_query.py` / `ObjectsQueryRequestor` | `rows_query.py` / `RowsQueryRequestor` | Схема изменена с `ObjectsQueryRequest`/`ObjectsQueryResponse` на `RowsQueryRequest`/`RowsQueryResponse`. |
| `objects_import.py` / `ObjectsImport` | `rows_import.py` / `RowsImport` | Импорт для структурированных данных. |

Ключ WebSocket-сервиса изменился с `"objects"` на `"rows"`, а ключ импорт-диспатчера аналогично — с `"objects"` на `"rows"`.

---

## Изменение формата представления данных: Value на Term

Слой сериализации (`serialize.py`) был переписан для использования нового типа `Term` вместо старого типа `Value`.

### Старый формат (v1.8 — `Value`)

```json
{"v": "http://example.org/entity", "e": true}
```

- `v`: значение (строка)
- `e`: булевский флаг, указывающий, является ли значение URI

### Новый формат (v2.1 — `Term`)

URI:
```json
{"t": "i", "i": "http://example.org/entity"}
```

Литералы:
```json
{"t": "l", "v": "some text", "d": "datatype-uri", "l": "en"}
```

Тройки, указанные в кавычках (RDF-star):
```json
{"t": "r", "r": {"s": {...}, "p": {...}, "o": {...}}}
```

- `t`: дискриминатор типа — `"i"` (URI), `"l"` (литерал), `"r"` (тройка), `"b"` (blank node)
- Сериализация теперь делегируется `TermTranslator` и `TripleTranslator` из `trustgraph.messaging.translators.primitives`

### Другие изменения в сериализации

| Поле | v1.8 | v2.1 |
|---|---|---|
| Metadata | `metadata.metadata` (подграфа) | `metadata.root` (простое значение) |
| Graph embeddings entity | `entity.vectors` (множественное) | `entity.vector` (одиночное) |
| Document embeddings chunk | `chunk.vectors` + `chunk.chunk` (текст) | `chunk.vector` + `chunk.chunk_id` (ссылка на ID) |

---

## Изменения, требующие внимания

- **Формат представления данных Value в Term**: Все клиенты, отправляющие/получающие тройки, встраивания или контексты сущностей через gateway, должны обновиться до нового формата Term.
- **Переименование объектов в rows**: Изменился ключ WebSocket-сервиса и ключ импорт-диспатчера.
- **Изменение поля metadata**: `metadata.metadata` (сериализованная подграфа) заменено на `metadata.root` (простое значение).
- **Изменения полей embeddings**: `vectors` (множественное) стало `vector` (одиночное); теперь встраивания документов ссылаются на `chunk_id` вместо inline `chunk`.
- **Новый endpoint `/api/v1/document-stream`**: Дополнительный, не является "breaking".
