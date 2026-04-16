---
layout: default
title: "Техническая спецификация поддержки потоковой передачи для RAG"
parent: "Russian (Beta)"
---

# Техническая спецификация поддержки потоковой передачи для RAG

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Обзор

Эта спецификация описывает добавление поддержки потоковой передачи для сервисов GraphRAG и DocumentRAG, позволяя получать ответы по частям (токен за токеном) для запросов из графа знаний и документов. Это расширяет существующую архитектуру потоковой передачи, уже реализованную для LLM-сервисов для завершения текста, запросов и агентов.

## Цели

- **Консистентный UX потоковой передачи**: Обеспечить одинаковый опыт потоковой передачи для всех сервисов TrustGraph.
- **Минимальные изменения API**: Добавить поддержку потоковой передачи с помощью одного флага `streaming`, следуя установленным шаблонам.
- **Совместимость со старыми версиями**: Поддерживать существующее поведение без потоковой передачи по умолчанию.
- **Использование существующей инфраструктуры**: Использовать существующую функциональность потоковой передачи PromptClient.
- **Поддержка Gateways**: Включить потоковую передачу через websocket Gateway для клиентских приложений.

## Предыстория

Текущие сервисы, поддерживающие потоковую передачу:
- **Сервис завершения текста LLM**: Фаза 1 - потоковая передача от LLM-провайдеров.
- **Сервис запросов**: Фаза 2 - потоковая передача через шаблоны запросов.
- **Сервис агента**: Фазы 3-4 - потоковая передача ReAct с последовательными частями/данными/ответами.

Текущие ограничения для сервисов RAG:
- GraphRAG и DocumentRAG поддерживают только не потоковые ответы.
- Пользователям необходимо ждать полного ответа LLM, прежде чем видеть какой-либо результат.
- Плохой UX для длинных ответов из запросов к графу знаний или документам.
- Несогласованный опыт по сравнению с другими сервисами TrustGraph.

Эта спецификация решает эти проблемы, добавляя поддержку потоковой передачи для GraphRAG и DocumentRAG.  Благодаря потоковой передаче по частям, TrustGraph может:
- Обеспечить консистентный UX потоковой передачи для всех типов запросов.
- Снизить воспринимаемую задержку для запросов RAG.
- Обеспечить лучший прогресс для длительных запросов.
- Поддерживать отображение в реальном времени в клиентских приложениях.

## Технический дизайн

### Архитектура

Реализация потоковой передачи для RAG использует существующую инфраструктуру:

1. **PromptClient Streaming** (Уже реализовано)
   - `kg_prompt()` и `document_prompt()` уже принимают параметры `streaming` и `chunk_callback`.
   - Эти вызывают `prompt()` с поддержкой потоковой передачи.
   - Изменения не требуются для PromptClient.

   Модуль: `trustgraph-base/trustgraph/base/prompt_client.py`

2. **Сервис GraphRAG** (Требуется передача параметра `streaming`)
   - Добавить параметр `streaming` к методу `query()`.
   - Передавать флаг `streaming` и обратные вызовы в `prompt_client.kg_prompt()`.
   - Схема GraphRagRequest должна иметь поле `streaming`.

   Модули:
   - `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py`
   - `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` (Обработчик)
   - `trustgraph-base/trustgraph/schema/graph_rag.py` (Схема запроса)
   - `trustgraph-flow/trustgraph/gateway/dispatch/graph_rag.py` (Gateway)

3. **Сервис DocumentRAG** (Требуется передача параметра `streaming`)
   - Добавить параметр `streaming` к методу `query()`.
   - Передавать флаг `streaming` и обратные вызовы в `prompt_client.document_prompt()`.
   - Схема DocumentRagRequest должна иметь поле `streaming`.

   Модули:
   - `trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py`
   - `trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` (Обработчик)
   - `trustgraph-base/trustgraph/schema/document_rag.py` (Схема запроса)
   - `trustgraph-flow/trustgraph/gateway/dispatch/document_rag.py` (Gateway)

### Поток данных

**Не потоковая передача (текущая)**:
```
Клиент → Gateway → Сервис RAG → PromptClient.kg_prompt(streaming=False)
                                   ↓
                                Сервис запросов → LLM
                                   ↓
                                Полный ответ
                                   ↓
Клиент ← Gateway ← Сервис RAG ←  Ответ
```

**Потоковая передача (предлагаемая)**:
```
Клиент → Gateway → Сервис RAG → PromptClient.kg_prompt(streaming=True, chunk_callback=cb)
                                   ↓
                                Сервис запросов → LLM (streaming)
                                   ↓
                                Часть → обратный вызов → Ответ RAG (часть)
                                   ↓                       ↓
Клиент ← Gateway ← ────────────────────────────────── Поток ответа
```

### API

**Изменения для GraphRAG**:

1. **GraphRag.query()** - Добавлены параметры потоковой передачи
```python
async def query(
    self, query, user, collection,
    verbose=False, streaming=False, chunk_callback=None  # NEW
):
    # ... существующая работа с сущностями/триплетами ...

    if streaming and chunk_callback:
        resp = await self.prompt_client.kg_prompt(
            query, kg,
            streaming=True,
            chunk_callback=chunk_callback
        )
    else:
        resp = await self.prompt_client.kg_prompt(query, kg)

    return resp
```

2. **GraphRagRequest schema** - Добавлен параметр `streaming`
```python
class GraphRagRequest(Record):
    query = String()
    user = String()
    collection = String()
    streaming = Boolean()  # NEW
```

3. **GraphRagResponse schema** - Добавлены поля для потоковой передачи (следовать паттерну Agent)
```python
class GraphRagResponse(Record):
    response = String()    # Legacy: полный ответ
    chunk = String()       # NEW: часть для потоковой передачи
    end_of_stream = Boolean()  # NEW: указывает, что это последняя часть
```

4. **Обработчик** - Передача потоковой передачи
```python
async def handle(self, ...):
    # ... существующий код ...
    response = await self.query(...)
    if response and streaming:
        # ... логика для отправки части
    else:
        # ... логика для отправки полного ответа
```

**Изменения для DocumentRAG**: Аналогично GraphRAG.

## График миграции

Не требуется миграция:
- Поддержка потоковой передачи является опцией (по умолчанию отключена)
- Существующие клиенты продолжают работать без изменений.
- Новые клиенты могут включить поддержку потоковой передачи.

## Сроки

Оценка времени реализации: 4-6 часов
- Фаза 1 (2 часа): Поддержка потоковой передачи для GraphRAG.
- Фаза 2 (2 часа): Поддержка потоковой передачи для DocumentRAG.
- Фаза 3 (1-2 часа): Обновления Gateway и флаги командной строки.
- Тестирование: Встроено в каждую фазу.

## Открытые вопросы

- Должна ли также поддерживаться потоковая передача для сервиса NLP Query?
- Хотим ли мы передавать только выход LLM (например, "Извлечь сущности...", "Запрос к графу...") или только его?
- Должны ли ответы GraphRAG/DocumentRAG содержать метаданные части (например, номер части, общее количество)?

## Ссылки

- Существующая реализация: `docs/tech-specs/streaming-llm-responses.md`
- Потоковая передача LLM: `trustgraph-flow/trustgraph/agent/react/agent_manager.py`
- Потоковая передача PromptClient: `trustgraph-base/trustgraph/base/prompt_client.py`
