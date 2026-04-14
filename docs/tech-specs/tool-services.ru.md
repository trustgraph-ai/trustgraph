---
layout: default
title: "Сервисы инструментов: Динамически подключаемые инструменты для агентов"
parent: "Russian (Beta)"
---

# Сервисы инструментов: Динамически подключаемые инструменты для агентов

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Статус

Реализовано

## Обзор

Эта спецификация определяет механизм динамически подключаемых инструментов для агентов, называемых "сервисами инструментов". В отличие от существующих встроенных типов инструментов (`KnowledgeQueryImpl`, `McpToolImpl` и т.д.), сервисы инструментов позволяют добавлять новые инструменты путем:

1. Развертывания нового сервиса на базе Pulsar
2. Добавления описания конфигурации, которое сообщает агенту, как его вызывать

Это обеспечивает расширяемость без изменения основной структуры агента.

## Терминология

| Термин | Определение |
|------|------------|
| **Встроенный инструмент** | Существующие типы инструментов с жестко закодированными реализациями в `tools.py` |
| **Сервис инструмента** | Сервис Pulsar, который может быть вызван как инструмент для агента, определенный описанием сервиса |
| **Инструмент** | Настроенный экземпляр, который ссылается на сервис инструмента и предоставляется агенту/LLM |

Это двухзвенная модель, аналогичная инструментам MCP:
MCP: MCP-сервер определяет интерфейс инструмента → Конфигурация инструмента ссылается на него
Сервисы инструментов: Сервис инструмента определяет интерфейс Pulsar → Конфигурация инструмента ссылается на него

## Обзор: Существующие инструменты

### Реализация встроенного инструмента

Инструменты в настоящее время определены в `trustgraph-flow/trustgraph/agent/react/tools.py` с типизированными реализациями:

```python
class KnowledgeQueryImpl:
    async def invoke(self, question):
        client = self.context("graph-rag-request")
        return await client.rag(question, self.collection)
```

Каждый тип инструмента:
Имеет жестко заданный сервис Pulsar, к которому он обращается (например, `graph-rag-request`)
Знает точный метод, который нужно вызвать у клиента (например, `client.rag()`)
Имеет типизированные аргументы, определенные в реализации

### Регистрация инструментов (service.py:105-214)

Инструменты загружаются из конфигурации с помощью поля `type`, которое сопоставляется с реализацией:

```python
if impl_id == "knowledge-query":
    impl = functools.partial(KnowledgeQueryImpl, collection=data.get("collection"))
elif impl_id == "text-completion":
    impl = TextCompletionImpl
# ... etc
```

## Архитектура

### Двухуровневая модель

#### Уровень 1: Описание сервиса инструмента

Сервис инструмента определяет интерфейс сервиса Pulsar. Он объявляет:
Очереди Pulsar для запросов/ответов
Параметры конфигурации, которые он требует от инструментов, использующих его

```json
{
  "id": "custom-rag",
  "request-queue": "non-persistent://tg/request/custom-rag",
  "response-queue": "non-persistent://tg/response/custom-rag",
  "config-params": [
    {"name": "collection", "required": true}
  ]
}
```

Сервис, который не требует параметров конфигурации:

```json
{
  "id": "calculator",
  "request-queue": "non-persistent://tg/request/calc",
  "response-queue": "non-persistent://tg/response/calc",
  "config-params": []
}
```

#### Уровень 2: Описание инструмента

Инструмент ссылается на сервис инструмента и предоставляет:
Значения параметров конфигурации (соответствующие требованиям сервиса)
Метаданные инструмента для агента (название, описание)
Определения аргументов для LLM

```json
{
  "type": "tool-service",
  "name": "query-customers",
  "description": "Query the customer knowledge base",
  "service": "custom-rag",
  "collection": "customers",
  "arguments": [
    {
      "name": "question",
      "type": "string",
      "description": "The question to ask about customers"
    }
  ]
}
```

Несколько инструментов могут ссылаться на один и тот же сервис с разными конфигурациями:

```json
{
  "type": "tool-service",
  "name": "query-products",
  "description": "Query the product knowledge base",
  "service": "custom-rag",
  "collection": "products",
  "arguments": [
    {
      "name": "question",
      "type": "string",
      "description": "The question to ask about products"
    }
  ]
}
```

### Формат запроса

Когда вызывается инструмент, запрос к службе инструмента включает в себя:
`user`: Из запроса агента (многопользовательский режим)
`config`: Значения конфигурации, закодированные в формате JSON, из описания инструмента
`arguments`: Аргументы, закодированные в формате JSON, из LLM

```json
{
  "user": "alice",
  "config": "{\"collection\": \"customers\"}",
  "arguments": "{\"question\": \"What are the top customer complaints?\"}"
}
```

Сервис инструментов получает это в виде разобранных словарей в методе `invoke`.

### Общая реализация сервиса инструментов

Класс `ToolServiceImpl` вызывает сервисы инструментов на основе конфигурации:

```python
class ToolServiceImpl:
    def __init__(self, context, request_queue, response_queue, config_values, arguments, processor):
        self.request_queue = request_queue
        self.response_queue = response_queue
        self.config_values = config_values  # e.g., {"collection": "customers"}
        # ...

    async def invoke(self, **arguments):
        client = await self._get_or_create_client()
        response = await client.call(user, self.config_values, arguments)
        if isinstance(response, str):
            return response
        else:
            return json.dumps(response)
```

## Принятые решения по проектированию

### Модель конфигурации с двумя уровнями

Сервисы инструментов следуют двухслойной модели, аналогичной инструментам MCP:

1. **Сервис инструмента**: Определяет интерфейс сервиса Pulsar (тема, необходимые параметры конфигурации).
2. **Инструмент**: Ссылается на сервис инструмента, предоставляет значения конфигурации, определяет аргументы LLM.

Это разделение позволяет:
Использовать один сервис инструмента несколькими инструментами с разными конфигурациями.
Четко различать интерфейс сервиса и конфигурацию инструмента.
Повторное использование определений сервисов.

### Отображение запросов: Прямая передача с оболочкой

Запрос к сервису инструмента представляет собой структурированную оболочку, содержащую:
`user`: Передается из запроса агента для поддержки многопользовательской среды.
Значения конфигурации: Из описателя инструмента (например, `collection`).
`arguments`: Аргументы, предоставленные LLM, передаются в виде словаря.

Менеджер агента анализирует ответ LLM в `act.arguments` в виде словаря (`agent_manager.py:117-154`). Этот словарь включается в оболочку запроса.

### Обработка схем: Без типов

Запросы и ответы используют нетипизированные словари. Отсутствует проверка схемы на уровне агента - сервис инструмента отвечает за проверку своих входных данных. Это обеспечивает максимальную гибкость при определении новых сервисов.

### Клиентский интерфейс: Прямые темы Pulsar

Сервисы инструментов используют прямые темы Pulsar без необходимости настройки потоков. Описатель сервиса инструмента указывает полные имена очередей:

```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [...]
}
```

Это позволяет размещать сервисы в любом пространстве имен.

### Обработка ошибок: Стандартная конвенция для ошибок

Ответы сервисов инструментов соответствуют существующей схеме с полем `error`:

```python
@dataclass
class Error:
    type: str = ""
    message: str = ""
```

Структура ответа:
Успех: `error` имеет значение `None`, ответ содержит результат
Ошибка: `error` заполняется значениями `type` и `message`

Это соответствует шаблону, используемому во всех существующих схемах сервисов (например, `PromptResponse`, `QueryResponse`, `AgentResponse`).

### Корреляция запросов и ответов

Корреляция запросов и ответов осуществляется с использованием `id` в свойствах сообщения Pulsar:

Запрос включает `id` в свойствах: `properties={"id": id}`
Ответы включают тот же `id`: `properties={"id": id}`

Это соответствует существующему шаблону, используемому во всей кодовой базе (например, `agent_service.py`, `llm_service.py`).

### Поддержка потоковой передачи

Сервисы инструментов могут возвращать потоковые ответы:

Несколько сообщений ответа с тем же `id` в свойствах
Каждый ответ включает поле `end_of_stream: bool`
Заключительный ответ имеет `end_of_stream: True`

Это соответствует шаблону, используемому в `AgentResponse` и других сервисах потоковой передачи.

### Обработка ответов: Возврат строки

Все существующие инструменты следуют одному и тому же шаблону: **получение аргументов в виде словаря, возврат наблюдения в виде строки**.

| Инструмент | Обработка ответов |
|------|------------------|
| `KnowledgeQueryImpl` | Возвращает `client.rag()` напрямую (строка) |
| `TextCompletionImpl` | Возвращает `client.question()` напрямую (строка) |
| `McpToolImpl` | Возвращает строку, или `json.dumps(output)`, если это не строка |
| `StructuredQueryImpl` | Форматирует результат в строку |
| `PromptImpl` | Возвращает `client.prompt()` напрямую (строка) |

Сервисы инструментов следуют тому же контракту:
Сервис возвращает строковый ответ (наблюдение)
Если ответ не является строкой, он преобразуется с помощью `json.dumps()`
Не требуется конфигурация извлечения в дескрипторе

Это упрощает дескриптор и возлагает ответственность на сервис по возврату соответствующего текстового ответа для агента.

## Руководство по настройке

Для добавления нового сервиса инструмента требуются два элемента конфигурации:

### 1. Конфигурация сервиса инструмента

Хранится под ключом конфигурации `tool-service`. Определяет очереди Pulsar и доступные параметры конфигурации.

| Поле | Обязательно | Описание |
|-------|----------|-------------|
| `id` | Да | Уникальный идентификатор для сервиса инструмента |
| `request-queue` | Да | Полная тема Pulsar для запросов (например, `non-persistent://tg/request/joke`) |
| `response-queue` | Да | Полная тема Pulsar для ответов (например, `non-persistent://tg/response/joke`) |
| `config-params` | Нет | Массив параметров конфигурации, которые принимает сервис |

Каждый параметр конфигурации может указывать:
`name`: Имя параметра (обязательно)
`required`: Должен ли параметр предоставляться инструментами (по умолчанию: false)

Пример:
```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [
    {"name": "style", "required": false}
  ]
}
```

### 2. Конфигурация инструмента

Хранится под ключом конфигурации `tool`. Определяет инструмент, которым может пользоваться агент.

| Поле | Обязательно | Описание |
|-------|----------|-------------|
| `type` | Да | Должно быть `"tool-service"` |
| `name` | Да | Название инструмента, доступное для LLM |
| `description` | Да | Описание того, что делает инструмент (отображается для LLM) |
| `service` | Да | ID сервиса инструмента, который необходимо вызвать |
| `arguments` | Нет | Массив определений аргументов для LLM |
| *(параметры конфигурации)* | Зависит | Любые параметры конфигурации, определенные сервисом |

Каждый аргумент может содержать:
`name`: Имя аргумента (обязательно)
`type`: Тип данных, например, `"string"` (обязательно)
`description`: Описание, отображаемое для LLM (обязательно)

Пример:
```json
{
  "type": "tool-service",
  "name": "tell-joke",
  "description": "Tell a joke on a given topic",
  "service": "joke-service",
  "style": "pun",
  "arguments": [
    {
      "name": "topic",
      "type": "string",
      "description": "The topic for the joke (e.g., programming, animals, food)"
    }
  ]
}
```

### Загрузка конфигурации

Используйте `tg-put-config-item` для загрузки конфигураций:

```bash
# Load tool-service config
tg-put-config-item tool-service/joke-service < joke-service.json

# Load tool config
tg-put-config-item tool/tell-joke < tell-joke.json
```

Агент-менеджер должен быть перезапущен для применения новых конфигураций.

## Детали реализации

### Схема

Типы запросов и ответов в `trustgraph-base/trustgraph/schema/services/tool_service.py`:

```python
@dataclass
class ToolServiceRequest:
    user: str = ""           # User context for multi-tenancy
    config: str = ""         # JSON-encoded config values from tool descriptor
    arguments: str = ""      # JSON-encoded arguments from LLM

@dataclass
class ToolServiceResponse:
    error: Error | None = None
    response: str = ""       # String response (the observation)
    end_of_stream: bool = False
```

### Серверная часть: DynamicToolService

Базовый класс в `trustgraph-base/trustgraph/base/dynamic_tool_service.py`:

```python
class DynamicToolService(AsyncProcessor):
    """Base class for implementing tool services."""

    def __init__(self, **params):
        topic = params.get("topic", default_topic)
        # Constructs topics: non-persistent://tg/request/{topic}, non-persistent://tg/response/{topic}
        # Sets up Consumer and Producer

    async def invoke(self, user, config, arguments):
        """Override this method to implement the tool's logic."""
        raise NotImplementedError()
```

### Клиентская часть: ToolServiceImpl

Реализация в `trustgraph-flow/trustgraph/agent/react/tools.py`:

```python
class ToolServiceImpl:
    def __init__(self, context, request_queue, response_queue, config_values, arguments, processor):
        # Uses the provided queue paths directly
        # Creates ToolServiceClient on first use

    async def invoke(self, **arguments):
        client = await self._get_or_create_client()
        response = await client.call(user, config_values, arguments)
        return response if isinstance(response, str) else json.dumps(response)
```

### Файлы

| Файл | Назначение |
|------|---------|
| `trustgraph-base/trustgraph/schema/services/tool_service.py` | Схемы запросов/ответов |
| `trustgraph-base/trustgraph/base/tool_service_client.py` | Клиент для вызова сервисов |
| `trustgraph-base/trustgraph/base/dynamic_tool_service.py` | Базовый класс для реализации сервиса |
| `trustgraph-flow/trustgraph/agent/react/tools.py` | Класс `ToolServiceImpl` |
| `trustgraph-flow/trustgraph/agent/react/service.py` | Загрузка конфигурации |

### Пример: Сервис шуток

Пример сервиса на `trustgraph-flow/trustgraph/tool_service/joke/`:

```python
class Processor(DynamicToolService):
    async def invoke(self, user, config, arguments):
        style = config.get("style", "pun")
        topic = arguments.get("topic", "")
        joke = pick_joke(topic, style)
        return f"Hey {user}! Here's a {style} for you:\n\n{joke}"
```

Конфигурация сервиса инструментов:
```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [{"name": "style", "required": false}]
}
```

Конфигурация инструмента:
```json
{
  "type": "tool-service",
  "name": "tell-joke",
  "description": "Tell a joke on a given topic",
  "service": "joke-service",
  "style": "pun",
  "arguments": [
    {"name": "topic", "type": "string", "description": "The topic for the joke"}
  ]
}
```

### Обратная совместимость

Существующие встроенные типы инструментов продолжают работать без изменений.
`tool-service` - это новый тип инструмента, который существует наряду с существующими типами (`knowledge-query`, `mcp-tool` и т.д.).

## Будущие соображения

### Сервисы с автоматическим оповещением

В будущем можно будет реализовать функцию, позволяющую сервисам публиковать свои собственные описания:

Сервисы публикуют информацию при запуске в определенной теме `tool-descriptors`.
Агент подписывается и динамически регистрирует инструменты.
Это обеспечивает возможность подключения и использования без изменения конфигурации.

Это выходит за рамки первоначальной реализации.

## Ссылки

Текущая реализация инструментов: `trustgraph-flow/trustgraph/agent/react/tools.py`
Регистрация инструментов: `trustgraph-flow/trustgraph/agent/react/service.py:105-214`
Схемы агента: `trustgraph-base/trustgraph/schema/services/agent.py`
