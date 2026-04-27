---
layout: default
title: "Спецификация OpenAPI - Техническая спецификация"
parent: "Russian (Beta)"
---

# Спецификация OpenAPI - Техническая спецификация

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Цель

Создать всеобъемлющую, модульную спецификацию OpenAPI 3.1 для шлюза REST API TrustGraph, которая:
Документирует все конечные точки REST
Использует внешние `$ref` для модульности и удобства обслуживания
Непосредственно соответствует коду переводчика сообщений
Предоставляет точные схемы запросов/ответов

## Источник истины

API определяется следующим:
**Переводчики сообщений**: `trustgraph-base/trustgraph/messaging/translators/*.py`
**Менеджер диспетчера**: `trustgraph-flow/trustgraph/gateway/dispatch/manager.py`
**Менеджер конечных точек**: `trustgraph-flow/trustgraph/gateway/endpoint/manager.py`

## Структура каталогов

```
openapi/
├── openapi.yaml                          # Main entry point
├── paths/
│   ├── config.yaml                       # Global services
│   ├── flow.yaml
│   ├── librarian.yaml
│   ├── knowledge.yaml
│   ├── collection-management.yaml
│   ├── flow-services/                    # Flow-hosted services
│   │   ├── agent.yaml
│   │   ├── document-rag.yaml
│   │   ├── graph-rag.yaml
│   │   ├── text-completion.yaml
│   │   ├── prompt.yaml
│   │   ├── embeddings.yaml
│   │   ├── mcp-tool.yaml
│   │   ├── triples.yaml
│   │   ├── objects.yaml
│   │   ├── nlp-query.yaml
│   │   ├── structured-query.yaml
│   │   ├── structured-diag.yaml
│   │   ├── graph-embeddings.yaml
│   │   ├── document-embeddings.yaml
│   │   ├── text-load.yaml
│   │   └── document-load.yaml
│   ├── import-export/
│   │   ├── core-import.yaml
│   │   ├── core-export.yaml
│   │   └── flow-import-export.yaml      # WebSocket import/export
│   ├── websocket.yaml
│   └── metrics.yaml
├── components/
│   ├── schemas/
│   │   ├── config/
│   │   ├── flow/
│   │   ├── librarian/
│   │   ├── knowledge/
│   │   ├── collection/
│   │   ├── ai-services/
│   │   ├── common/
│   │   └── errors/
│   ├── parameters/
│   ├── responses/
│   └── examples/
└── security/
    └── bearerAuth.yaml
```

## Отображение сервисов

### Глобальные сервисы (`/api/v1/{kind}`)
`config` - Управление конфигурацией
`flow` - Жизненный цикл потока
`librarian` - Библиотека документов
`knowledge` - Базы знаний
`collection-management` - Метаданные коллекции

### Сервисы, размещенные в потоке (`/api/v1/flow/{flow}/service/{kind}`)

**Запрос/Ответ:**
`agent`, `text-completion`, `prompt`, `mcp-tool`
`graph-rag`, `document-rag`
`embeddings`, `graph-embeddings`, `document-embeddings`
`triples`, `objects`, `nlp-query`, `structured-query`, `structured-diag`

**Отправка и получение (Fire-and-Forget):**
`text-load`, `document-load`

### Импорт/Экспорт
`/api/v1/import-core` (POST)
`/api/v1/export-core` (GET)
`/api/v1/flow/{flow}/import/{kind}` (WebSocket)
`/api/v1/flow/{flow}/export/{kind}` (WebSocket)

### Другое
`/api/v1/socket` (Множественный WebSocket)
`/api/metrics` (Prometheus)

## Подход

### Фаза 1: Настройка
1. Создание структуры каталогов
2. Создание основного файла `openapi.yaml` с метаданными, серверами, безопасностью
3. Создание многократно используемых компонентов (ошибок, общих параметров, схем безопасности)

### Фаза 2: Общие схемы
Создание общих схем, используемых во всех сервисах:
`RdfValue`, `Triple` - RDF/структуры троек
`ErrorObject` - Ответ об ошибке
`DocumentMetadata`, `ProcessingMetadata` - Структуры метаданных
Общие параметры: `FlowId`, `User`, `Collection`

### Фаза 3: Глобальные сервисы
Для каждого глобального сервиса (конфигурация, поток, библиотека, знания, управление коллекцией):
1. Создание файла пути в `paths/`
2. Создание схемы запроса в `components/schemas/{service}/`
3. Создание схемы ответа
4. Добавление примеров
5. Ссылка из основного файла `openapi.yaml`

### Фаза 4: Сервисы, размещенные в потоке
Для каждого сервиса, размещенного в потоке:
1. Создание файла пути в `paths/flow-services/`
2. Создание схем запроса/ответа в `components/schemas/ai-services/`
3. Добавление документации о флаге потоковой передачи, где это применимо
4. Ссылка из основного файла `openapi.yaml`

### Фаза 5: Импорт/Экспорт и WebSocket
1. Документирование основных конечных точек импорта/экспорта
2. Документирование шаблонов протокола WebSocket
3. Документирование конечных точек импорта/экспорта WebSocket на уровне потока

### Фаза 6: Валидация
1. Проверка с помощью инструментов валидации OpenAPI
2. Тестирование с помощью Swagger UI
3. Убедитесь, что все переводчики охвачены

## Соглашение об именовании полей

Все поля JSON используют **kebab-case**:
`flow-id`, `blueprint-name`, `doc-limit`, `entity-limit` и т. д.

## Создание файлов схем

Для каждого переводчика в `trustgraph-base/trustgraph/messaging/translators/`:

1. **Прочитать метод переводчика `to_pulsar()`** - Определяет схему запроса
2. **Прочитать метод переводчика `from_pulsar()`** - Определяет схему ответа
3. **Извлечь имена и типы полей**
4. **Создать схему OpenAPI** с:
   Имена полей (kebab-case)
   Типы (string, integer, boolean, object, array)
   Обязательные поля
   Значения по умолчанию
   Описания

### Пример процесса сопоставления

```python
# From retrieval.py DocumentRagRequestTranslator
def to_pulsar(self, data: Dict[str, Any]) -> DocumentRagQuery:
    return DocumentRagQuery(
        query=data["query"],                              # required string
        user=data.get("user", "trustgraph"),             # optional string, default "trustgraph"
        collection=data.get("collection", "default"),     # optional string, default "default"
        doc_limit=int(data.get("doc-limit", 20)),        # optional integer, default 20
        streaming=data.get("streaming", False)            # optional boolean, default false
    )
```

Соответствует:

```yaml
# components/schemas/ai-services/DocumentRagRequest.yaml
type: object
required:
  - query
properties:
  query:
    type: string
    description: Search query
  user:
    type: string
    default: trustgraph
  collection:
    type: string
    default: default
  doc-limit:
    type: integer
    default: 20
    description: Maximum number of documents to retrieve
  streaming:
    type: boolean
    default: false
    description: Enable streaming responses
```

## Потоковые ответы

Сервисы, поддерживающие потоковую передачу, возвращают несколько ответов с флагом `end_of_stream`:
`agent`, `text-completion`, `prompt`
`document-rag`, `graph-rag`

Опишите эту схему в схеме ответа каждого сервиса.

## Ответы об ошибках

Все сервисы могут возвращать:
```yaml
error:
  oneOf:
    - type: string
    - $ref: '#/components/schemas/ErrorObject'
```

Где `ErrorObject` находится:
```yaml
type: object
properties:
  type:
    type: string
  message:
    type: string
```

## Ссылки

Переводчики: `trustgraph-base/trustgraph/messaging/translators/`
Отображение диспетчера: `trustgraph-flow/trustgraph/gateway/dispatch/manager.py`
Маршрутизация конечных точек: `trustgraph-flow/trustgraph/gateway/endpoint/manager.py`
Обзор сервисов: `API_SERVICES_SUMMARY.md`
