---
layout: default
title: "Техническая спецификация потоковой передачи ответов LLM"
parent: "Russian (Beta)"
---

# Техническая спецификация потоковой передачи ответов LLM

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Обзор

Эта спецификация описывает реализацию поддержки потоковой передачи для ответов LLM
в TrustGraph. Потоковая передача обеспечивает доставку сгенерированных
токенов в режиме реального времени по мере их создания LLM, а не после
завершения полной генерации ответа.

Эта реализация поддерживает следующие сценарии использования:

1. **Интерфейсы пользователя в реальном времени**: Передавайте токены в пользовательский интерфейс по мере их генерации,
   обеспечивая немедленную визуальную обратную связь.
2. **Сокращение времени до первого токена**: Пользователи видят вывод сразу,
   а не после полной генерации.
3. **Обработка очень длинных ответов**: Обрабатывайте очень длинные ответы, которые в противном случае
   могли бы привести к таймаутам или превышению лимитов памяти.
4. **Интерактивные приложения**: Обеспечьте отзывчивые чат-интерфейсы и интерфейсы агентов.

## Цели

**Обратная совместимость**: Существующие клиенты, не использующие потоковую передачу, продолжают работать
  без изменений.
**Согласованный дизайн API**: Потоковая передача и не потоковая передача используют одни и те же схемы
  с минимальными отклонениями.
**Гибкость для поставщиков**: Поддержка потоковой передачи, где это возможно, и плавный
  переход к не потоковой передаче, где это невозможно.
**Поэтапное внедрение**: Постепенная реализация для снижения рисков.
**Комплексная поддержка**: Потоковая передача от поставщика LLM до клиентских
  приложений через Pulsar, Gateway API и Python API.

## Обзор

### Текущая архитектура

Текущий процесс текстового завершения LLM работает следующим образом:

1. Клиент отправляет `TextCompletionRequest` с полями `system` и `prompt`.
2. Сервис LLM обрабатывает запрос и ожидает полной генерации.
3. Возвращается один `TextCompletionResponse` с полной строкой `response`.

Текущая схема (`trustgraph-base/trustgraph/schema/services/llm.py`):

```python
class TextCompletionRequest(Record):
    system = String()
    prompt = String()

class TextCompletionResponse(Record):
    error = Error()
    response = String()
    in_token = Integer()
    out_token = Integer()
    model = String()
```

### Текущие ограничения

**Задержка**: Пользователи должны ждать завершения генерации, прежде чем увидеть какой-либо результат.
**Риск превышения времени ожидания**: Длительная генерация может превысить лимиты времени ожидания клиента.
**Плохой пользовательский опыт**: Отсутствие обратной связи во время генерации создает ощущение медленной работы.
**Использование ресурсов**: Полные ответы должны быть буферизованы в памяти.

Эта спецификация решает эти ограничения, обеспечивая постепенную передачу ответа, при этом сохраняя полную обратную совместимость.


## Техническое проектирование

### Фаза 1: Инфраструктура

Фаза 1 закладывает основу для потоковой передачи путем изменения схем, API и инструментов командной строки.


#### Изменения в схемах

##### Схема LLM (`trustgraph-base/trustgraph/schema/services/llm.py`)

**Изменения в запросах:**

```python
class TextCompletionRequest(Record):
    system = String()
    prompt = String()
    streaming = Boolean()  # NEW: Default false for backward compatibility
```

`streaming`: Когда `true`, запрашивается потоковая доставка ответа.
По умолчанию: `false` (сохранено существующее поведение).

**Изменения в ответе:**

```python
class TextCompletionResponse(Record):
    error = Error()
    response = String()
    in_token = Integer()
    out_token = Integer()
    model = String()
    end_of_stream = Boolean()  # NEW: Indicates final message
```

`end_of_stream`: Когда `true`, указывает на то, что это окончательный (или единственный) ответ.
Для нестриминговых запросов: Один ответ с `end_of_stream=true`.
Для стриминговых запросов: Множественные ответы, все с `end_of_stream=false`,
  за исключением последнего.

##### Схема запроса (`trustgraph-base/trustgraph/schema/services/prompt.py`)

Сервис запросов оборачивает завершение текста, поэтому он следует той же схеме:

**Изменения в запросе:**

```python
class PromptRequest(Record):
    id = String()
    terms = Map(String())
    streaming = Boolean()  # NEW: Default false
```

**Изменения в ответе:**

```python
class PromptResponse(Record):
    error = Error()
    text = String()
    object = String()
    end_of_stream = Boolean()  # NEW: Indicates final message
```

#### Изменения API шлюза

API шлюз должен предоставлять возможности потоковой передачи данных для клиентов HTTP/WebSocket.

**Обновления REST API:**

`POST /api/v1/text-completion`: Принимать параметр `streaming` в теле запроса
Поведение ответа зависит от флага потоковой передачи:
  `streaming=false`: Одиночный ответ в формате JSON (текущее поведение)
  `streaming=true`: Поток событий от сервера (SSE) или сообщения WebSocket

**Формат ответа (потоковая передача):**

Каждый фрагмент, передаваемый потоком, имеет одинаковую структуру схемы:
```json
{
  "response": "partial text...",
  "end_of_stream": false,
  "model": "model-name"
}
```

Заключительный раздел:
```json
{
  "response": "final text chunk",
  "end_of_stream": true,
  "in_token": 150,
  "out_token": 500,
  "model": "model-name"
}
```

#### Изменения в API Python

API клиента Python должен поддерживать как потоковый, так и не потоковый режимы,
при этом сохраняя обратную совместимость.

**Обновления LlmClient** (`trustgraph-base/trustgraph/clients/llm_client.py`):

```python
class LlmClient(BaseClient):
    def request(self, system, prompt, timeout=300, streaming=False):
        """
        Non-streaming request (backward compatible).
        Returns complete response string.
        """
        # Existing behavior when streaming=False

    async def request_stream(self, system, prompt, timeout=300):
        """
        Streaming request.
        Yields response chunks as they arrive.
        """
        # New async generator method
```

**Обновления PromptClient** (`trustgraph-base/trustgraph/base/prompt_client.py`):

Аналогичный шаблон с параметром `streaming` и вариантом асинхронного генератора.

#### Изменения инструмента командной строки

**tg-invoke-llm** (`trustgraph-cli/trustgraph/cli/invoke_llm.py`):

```
tg-invoke-llm [system] [prompt] [--no-streaming] [-u URL] [-f flow-id]
```

По умолчанию включен режим потоковой передачи для улучшения интерактивного пользовательского опыта.
Флаг `--no-streaming` отключает режим потоковой передачи.
В режиме потоковой передачи: выводите токены в стандартный вывод по мере их поступления.
В режиме, когда потоковая передача отключена: дождитесь получения полного ответа, а затем выведите его.

**tg-invoke-prompt** (`trustgraph-cli/trustgraph/cli/invoke_prompt.py`):

```
tg-invoke-prompt [template-id] [var=value...] [--no-streaming] [-u URL] [-f flow-id]
```

Такой же шаблон, как у `tg-invoke-llm`.

#### Изменения базового класса LLM Service.

**LlmService** (`trustgraph-base/trustgraph/base/llm_service.py`):

```python
class LlmService(FlowProcessor):
    async def on_request(self, msg, consumer, flow):
        request = msg.value()
        streaming = getattr(request, 'streaming', False)

        if streaming and self.supports_streaming():
            async for chunk in self.generate_content_stream(...):
                await self.send_response(chunk, end_of_stream=False)
            await self.send_response(final_chunk, end_of_stream=True)
        else:
            response = await self.generate_content(...)
            await self.send_response(response, end_of_stream=True)

    def supports_streaming(self):
        """Override in subclass to indicate streaming support."""
        return False

    async def generate_content_stream(self, system, prompt, model, temperature):
        """Override in subclass to implement streaming."""
        raise NotImplementedError()
```

--

### Фаза 2: Проверка концепции VertexAI

Фаза 2 реализует потоковую передачу данных в одном провайдере (VertexAI) для проверки
инфраструктуры и обеспечения сквозного тестирования.

#### Реализация VertexAI

**Модуль:** `trustgraph-vertexai/trustgraph/model/text_completion/vertexai/llm.py`

**Изменения:**

1. Переопределить `supports_streaming()` для возврата `True`
2. Реализовать асинхронный генератор `generate_content_stream()`
3. Поддержка моделей Gemini и Claude (через VertexAI Anthropic API)

**Потоковая передача данных Gemini:**

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    model_instance = self.get_model(model, temperature)
    response = model_instance.generate_content(
        [system, prompt],
        stream=True  # Enable streaming
    )
    for chunk in response:
        yield LlmChunk(
            text=chunk.text,
            in_token=None,  # Available only in final chunk
            out_token=None,
        )
    # Final chunk includes token counts from response.usage_metadata
```

**Claude (через VertexAI Anthropic) в режиме потоковой передачи:**

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    with self.anthropic_client.messages.stream(...) as stream:
        for text in stream.text_stream:
            yield LlmChunk(text=text)
    # Token counts from stream.get_final_message()
```

#### Тестирование

Юнит-тесты для сборки потоковых ответов
Интеграционные тесты с VertexAI (Gemini и Claude)
Комплексные тесты: CLI -> Gateway -> Pulsar -> VertexAI -> back
Тесты обратной совместимости: Непотоковые запросы по-прежнему работают

--

### Фаза 3: Все провайдеры LLM

Фаза 3 расширяет поддержку потоковой передачи для всех провайдеров LLM в системе.

#### Статус реализации для каждого провайдера

Каждый провайдер должен либо:
1. **Полная поддержка потоковой передачи**: Реализовать `generate_content_stream()`
2. **Режим совместимости**: Правильно обрабатывать флаг `end_of_stream`
   (возвращать единый ответ с `end_of_stream=true`)

| Провайдер | Пакет | Поддержка потоковой передачи |
|----------|---------|-------------------|
| OpenAI | trustgraph-flow | Полная (нативная API потоковой передачи) |
| Claude/Anthropic | trustgraph-flow | Полная (нативная API потоковой передачи) |
| Ollama | trustgraph-flow | Полная (нативная API потоковой передачи) |
| Cohere | trustgraph-flow | Полная (нативная API потоковой передачи) |
| Mistral | trustgraph-flow | Полная (нативная API потоковой передачи) |
| Azure OpenAI | trustgraph-flow | Полная (нативная API потоковой передачи) |
| Google AI Studio | trustgraph-flow | Полная (нативная API потоковой передачи) |
| VertexAI | trustgraph-vertexai | Полная (Фаза 2) |
| Bedrock | trustgraph-bedrock | Полная (нативная API потоковой передачи) |
| LM Studio | trustgraph-flow | Полная (совместима с OpenAI) |
| LlamaFile | trustgraph-flow | Полная (совместима с OpenAI) |
| vLLM | trustgraph-flow | Полная (совместима с OpenAI) |
| TGI | trustgraph-flow | Будет определено |
| Azure | trustgraph-flow | Будет определено |

#### Шаблон реализации

Для провайдеров, совместимых с OpenAI (OpenAI, LM Studio, LlamaFile, vLLM):

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    response = await self.client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        stream=True
    )
    async for chunk in response:
        if chunk.choices[0].delta.content:
            yield LlmChunk(text=chunk.choices[0].delta.content)
```

--

### Фаза 4: API агента

Фаза 4 расширяет потоковую передачу на API агента. Это более сложный процесс, поскольку
API агента изначально предназначен для работы с несколькими сообщениями (мысль → действие → наблюдение
→ повтор → окончательный ответ).

#### Текущая схема агента

```python
class AgentStep(Record):
    thought = String()
    action = String()
    arguments = Map(String())
    observation = String()
    user = String()

class AgentRequest(Record):
    question = String()
    state = String()
    group = Array(String())
    history = Array(AgentStep())
    user = String()

class AgentResponse(Record):
    answer = String()
    error = Error()
    thought = String()
    observation = String()
```

#### Предлагаемые изменения схемы агента

**Запрос изменений:**

```python
class AgentRequest(Record):
    question = String()
    state = String()
    group = Array(String())
    history = Array(AgentStep())
    user = String()
    streaming = Boolean()  # NEW: Default false
```

**Изменения в ответах:**

Агент генерирует несколько типов выходных данных в процессе рассуждения:
Мысли (рассуждения)
Действия (вызовы инструментов)
Наблюдения (результаты работы инструментов)
Ответ (окончательный ответ)
Ошибки

Поскольку `chunk_type` указывает на тип передаваемого контента, отдельные
поля `answer`, `error`, `thought` и `observation` можно объединить в
одно поле `content`:

```python
class AgentResponse(Record):
    chunk_type = String()       # "thought", "action", "observation", "answer", "error"
    content = String()          # The actual content (interpretation depends on chunk_type)
    end_of_message = Boolean()  # Current thought/action/observation/answer is complete
    end_of_dialog = Boolean()   # Entire agent dialog is complete
```

**Семантика полей:**

`chunk_type`: Указывает, какой тип содержимого находится в поле `content`
  `"thought"`: Рассуждения/мысли агента
  `"action"`: Используемый инструмент/действие
  `"observation"`: Результат выполнения инструмента
  `"answer"`: Окончательный ответ на вопрос пользователя
  `"error"`: Сообщение об ошибке

`content`: Фактическое потоковое содержимое, интерпретируемое на основе `chunk_type`

`end_of_message`: Когда `true`, текущий тип фрагмента завершен
  Пример: Все токены для текущей мысли были отправлены
  Позволяет клиентам знать, когда переходить к следующему этапу

`end_of_dialog`: Когда `true`, все взаимодействие с агентом завершено
  Это последнее сообщение в потоке

#### Поведение потоковой передачи агента

Когда `streaming=true`:

1. **Потоковая передача мыслей:**
   Несколько фрагментов с `chunk_type="thought"`, `end_of_message=false`
   Последний фрагмент мысли содержит `end_of_message=true`
2. **Уведомление о действии:**
   Один фрагмент с `chunk_type="action"`, `end_of_message=true`
3. **Наблюдение:**
   Один или несколько фрагментов с `chunk_type="observation"`, последний содержит `end_of_message=true`
4. **Повторяйте** шаги 1-3, пока агент рассуждает
5. **Окончательный ответ:**
   `chunk_type="answer"` с окончательным ответом в `content`
   Последний фрагмент содержит `end_of_message=true`, `end_of_dialog=true`

**Пример последовательности потоковой передачи:**

```
{chunk_type: "thought", content: "I need to", end_of_message: false, end_of_dialog: false}
{chunk_type: "thought", content: " search for...", end_of_message: true, end_of_dialog: false}
{chunk_type: "action", content: "search", end_of_message: true, end_of_dialog: false}
{chunk_type: "observation", content: "Found: ...", end_of_message: true, end_of_dialog: false}
{chunk_type: "thought", content: "Based on this", end_of_message: false, end_of_dialog: false}
{chunk_type: "thought", content: " I can answer...", end_of_message: true, end_of_dialog: false}
{chunk_type: "answer", content: "The answer is...", end_of_message: true, end_of_dialog: true}
```

Когда `streaming=false`:
Текущее поведение сохранено
Единый ответ с полным ответом
`end_of_message=true`, `end_of_dialog=true`

#### Шлюз и Python API

Шлюз: Новый SSE/WebSocket endpoint для потоковой передачи данных от агента
Python API: Новый асинхронный генератор `agent_stream()`

--

## Соображения безопасности

**Отсутствие новых уязвимостей**: Потоковая передача использует ту же аутентификацию/авторизацию
**Ограничение скорости**: При необходимости применяйте ограничения скорости на токен или на фрагмент
**Обработка соединений**: Правильно завершайте потоки при отключении клиента
**Управление временем ожидания**: Запросы потоковой передачи требуют соответствующей обработки времени ожидания

## Соображения производительности

**Память**: Потоковая передача снижает пиковое использование памяти (без полной буферизации ответа)
**Задержка**: Время до первого токена значительно сокращено
**Накладные расходы на соединение**: Соединения SSE/WebSocket имеют накладные расходы на поддержание соединения
**Производительность Pulsar**: Несколько небольших сообщений против одного большого сообщения - компромисс
  tradeoff

## Стратегия тестирования

### Юнит-тесты
Сериализация/десериализация схемы с новыми полями
Обратная совместимость (отсутствующие поля используют значения по умолчанию)
Логика сборки фрагментов

### Интеграционные тесты
Реализация потоковой передачи каждого поставщика LLM
Потоковые конечные точки API шлюза
Методы потоковой передачи клиента на Python

### Комплексные тесты
Вывод потоковой передачи инструмента командной строки
Полный поток: Клиент → Шлюз → Pulsar → LLM → обратно
Смешанные потоковые и не потоковые рабочие нагрузки

### Тесты обратной совместимости
Существующие клиенты работают без изменений
Запросы без потоковой передачи ведут себя идентично

## План миграции

### Фаза 1: Инфраструктура
Развертывание изменений схемы (обратная совместимость)
Развертывание обновлений API шлюза
Развертывание обновлений Python API
Выпуск обновлений инструмента командной строки

### Фаза 2: VertexAI
Развернуть поточную реализацию VertexAI.
Проверить с помощью тестовых нагрузок.

### Фаза 3: Все провайдеры
Постепенно внедрять обновления для провайдеров.
Отслеживать наличие проблем.

### Фаза 4: API агента
Развернуть изменения схемы агента.
Развернуть поточную реализацию агента.
Обновить документацию.

## График

| Фаза | Описание | Зависимости |
|-------|-------------|--------------|
| Фаза 1 | Инфраструктура | Отсутствуют |
| Фаза 2 | VertexAI, пилотный проект | Фаза 1 |
| Фаза 3 | Все провайдеры | Фаза 2 |
| Фаза 4 | API агента | Фаза 3 |

## Принятые решения по проектированию

В процессе разработки спецификации были решены следующие вопросы:

1. **Количество токенов в потоке**: Количество токенов указывается как разница, а не как текущая сумма.
   Потребители могут суммировать их, если это необходимо. Это соответствует тому, как большинство провайдеров
   сообщают об использовании и упрощает реализацию.

2. **Обработка ошибок в потоках**: В случае возникновения ошибки, поле `error`
   заполняется, и другие поля не требуются. Ошибка всегда является последним
   сообщением - после ошибки не допускаются и не ожидаются последующие сообщения.
   Для потоков LLM/Prompt: `end_of_stream=true`. Для потоков Agent:
   `chunk_type="error"` с `end_of_dialog=true`.

3. **Восстановление после частичного ответа**: Протокол обмена сообщениями (Pulsar) устойчив,
   поэтому повторная отправка сообщений на уровне отдельных сообщений не требуется.
   Если клиент теряет отслеживание потока или отключается, он должен повторить
полный запрос с самого начала.
4. **Быстрая потоковая передача**: Потоковая передача поддерживается только для текстовых ответов (`text`).
   ответы, а не для структурированных (`object`) ответов. Сервис запросов знает заранее,
   будет ли вывод в формате JSON или текста, в зависимости от шаблона запроса. Если
   выполняется запрос на потоковую передачу для запроса, предназначенного для вывода JSON,
   сервис должен либо:
   Вернуть полный JSON в одном ответе с `end_of_stream=true`, или
   Отклонить запрос на потоковую передачу с ошибкой.

## Открытые вопросы

На данный момент их нет.

## Ссылки

Текущая схема LLM: `trustgraph-base/trustgraph/schema/services/llm.py`
Текущая схема запросов: `trustgraph-base/trustgraph/schema/services/prompt.py`
Текущая схема агента: `trustgraph-base/trustgraph/schema/services/agent.py`
Базовый URL службы LLM: `trustgraph-base/trustgraph/base/llm_service.py`
Провайдер VertexAI: `trustgraph-vertexai/trustgraph/model/text_completion/vertexai/llm.py`
API шлюза: `trustgraph-base/trustgraph/api/`
Инструменты CLI: `trustgraph-cli/trustgraph/cli/`
