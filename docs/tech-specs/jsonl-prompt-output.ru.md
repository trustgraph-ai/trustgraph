# Техническая спецификация формата вывода JSONL для запросов

## Обзор

Эта спецификация описывает реализацию формата вывода JSONL (JSON Lines) для ответов на запросы в TrustGraph. JSONL обеспечивает устойчивость к усечению при извлечении структурированных данных из ответов LLM, решая критические проблемы, связанные с повреждением выходных массивов JSON, когда ответы LLM достигают лимита токенов.





Эта реализация поддерживает следующие сценарии использования:

1. **Извлечение, устойчивое к усечению**: Извлекайте допустимые частичные результаты, даже когда
   вывод LLM усекается в середине ответа.
<<<<<<< HEAD
2. **Извлечение в больших масштабах**: Обрабатывайте извлечение большого количества элементов без риска
=======
2. **Масштабное извлечение**: Обрабатывайте извлечение большого количества элементов без риска
>>>>>>> 82edf2d (New md files from RunPod)
   полной сбоя из-за ограничений на количество токенов.
3. **Извлечение данных разных типов**: Поддерживайте извлечение нескольких типов сущностей
   (определения, отношения, сущности, атрибуты) в одном запросе.
4. **Вывод, совместимый со стримингом**: Обеспечьте возможность будущей потоковой/инкрементной
   обработки результатов извлечения.

## Цели

**Обратная совместимость**: Существующие запросы, использующие `response-type: "text"` и
  `response-type: "json"`, продолжают работать без изменений.
**Устойчивость к усечению**: Частичные выходные данные LLM приводят к частичным, но допустимым результатам,
  а не к полному сбою.
**Проверка схемы**: Поддержка проверки JSON-схемы для отдельных объектов.
**Дискриминированные объединения**: Поддержка выходных данных смешанных типов с использованием поля `type`
  в качестве дискриминатора.
<<<<<<< HEAD
**Минимальные изменения API**: Расширение существующей конфигурации запросов с добавлением нового
  типа ответа и ключа схемы.

## Обзор
=======
**Минимальные изменения API**: Расширение существующей конфигурации запросов с помощью нового
  типа ответа и ключа схемы.

## Контекст
>>>>>>> 82edf2d (New md files from RunPod)

### Текущая архитектура

Сервис запросов поддерживает два типа ответов:

1. `response-type: "text"` - Необработанный текстовый ответ, возвращаемый как есть.
2. `response-type: "json"` - JSON, полученный из ответа и проверенный на соответствие
   необязательной `schema`.

Текущая реализация в `trustgraph-flow/trustgraph/template/prompt_manager.py`:

```python
class Prompt:
    def __init__(self, template, response_type = "text", terms=None, schema=None):
        self.template = template
        self.response_type = response_type
        self.terms = terms
        self.schema = schema
```

### Текущие ограничения

Когда запросы извлечения требуют вывод в виде массивов JSON (`[{...}, {...}, ...]`):

**Повреждение из-за усечения**: Если языковая модель достигает лимита выходных токенов в середине массива,
  весь ответ становится недействительным JSON и не может быть проанализирован.
**Анализ "все или ничего"**: Необходимо получить полный вывод перед анализом.
**Нет частичных результатов**: Усеченный ответ дает нулевые полезные данные.
**Ненадежно для больших извлечений**: Чем больше извлеченных элементов, тем выше риск сбоя.

Данная спецификация решает эти ограничения, вводя формат JSONL для
запросов извлечения, где каждый извлеченный элемент является полным JSON-объектом на своей
строке.

## Техническое проектирование

### Расширение типа ответа

Добавьте новый тип ответа `"jsonl"` наряду с существующими типами `"text"` и `"json"`.

#### Изменения конфигурации

**Новое значение типа ответа:**

```
"response-type": "jsonl"
```

**Интерпретация схемы:**

Существующий ключ `"schema"` используется как для `"json"`, так и для `"jsonl"` типов ответов.
Интерпретация зависит от типа ответа:

`"json"`: Схема описывает весь ответ (обычно массив или объект).
`"jsonl"`: Схема описывает каждую отдельную строку/объект.

```json
{
  "response-type": "jsonl",
  "schema": {
    "type": "object",
    "properties": {
      "entity": { "type": "string" },
      "definition": { "type": "string" }
    },
    "required": ["entity", "definition"]
  }
}
```

Это позволяет избежать изменений в инструментах и редакторах конфигурации подсказок.

### Спецификация формата JSONL

#### Простое извлечение

Для подсказок, извлекающих один тип объекта (определения, отношения,
темы, строки), вывод представляет собой один объект JSON на строку без обертки:

**Формат вывода подсказки:**
```
{"entity": "photosynthesis", "definition": "Process by which plants convert sunlight"}
{"entity": "chlorophyll", "definition": "Green pigment in plants"}
{"entity": "mitochondria", "definition": "Powerhouse of the cell"}
```

**Контраст с предыдущим форматом JSON-массива:**
```json
[
  {"entity": "photosynthesis", "definition": "Process by which plants convert sunlight"},
  {"entity": "chlorophyll", "definition": "Green pigment in plants"},
  {"entity": "mitochondria", "definition": "Powerhouse of the cell"}
]
```

Если LLM обрезает текст после строки 2, формат массива JSON приводит к недействительному JSON,
в то время как JSONL дает два допустимых объекта.

#### Извлечение данных смешанных типов (дискриминированные объединения)

Для запросов, извлекающих несколько типов объектов (например, определения и
отношения, или сущности, отношения и атрибуты), используйте поле `"type"`
в качестве дискриминатора:

**Формат вывода запроса:**
```
{"type": "definition", "entity": "DNA", "definition": "Molecule carrying genetic instructions"}
{"type": "relationship", "subject": "DNA", "predicate": "located_in", "object": "cell nucleus", "object-entity": true}
{"type": "definition", "entity": "RNA", "definition": "Molecule that carries genetic information"}
{"type": "relationship", "subject": "RNA", "predicate": "transcribed_from", "object": "DNA", "object-entity": true}
```

**Схема для дискриминированных объединений использует `oneOf`:**
```json
{
  "response-type": "jsonl",
  "schema": {
    "oneOf": [
      {
        "type": "object",
        "properties": {
          "type": { "const": "definition" },
          "entity": { "type": "string" },
          "definition": { "type": "string" }
        },
        "required": ["type", "entity", "definition"]
      },
      {
        "type": "object",
        "properties": {
          "type": { "const": "relationship" },
          "subject": { "type": "string" },
          "predicate": { "type": "string" },
          "object": { "type": "string" },
          "object-entity": { "type": "boolean" }
        },
        "required": ["type", "subject", "predicate", "object", "object-entity"]
      }
    ]
  }
}
```

#### Извлечение онтологии

Для извлечения онтологии на основе сущностей, связей и атрибутов:

**Формат вывода запроса:**
```
{"type": "entity", "entity": "Cornish pasty", "entity_type": "fo/Recipe"}
{"type": "entity", "entity": "beef", "entity_type": "fo/Food"}
{"type": "relationship", "subject": "Cornish pasty", "subject_type": "fo/Recipe", "relation": "fo/has_ingredient", "object": "beef", "object_type": "fo/Food"}
{"type": "attribute", "entity": "Cornish pasty", "entity_type": "fo/Recipe", "attribute": "fo/serves", "value": "4 people"}
```

### Детали реализации

#### Класс Prompt

Существующий класс `Prompt` не требует изменений. Поле `schema` используется повторно
<<<<<<< HEAD
для JSONL, а его интерпретация определяется `response_type`:
=======
для JSONL, и его интерпретация определяется `response_type`:
>>>>>>> 82edf2d (New md files from RunPod)

```python
class Prompt:
    def __init__(self, template, response_type="text", terms=None, schema=None):
        self.template = template
        self.response_type = response_type
        self.terms = terms
        self.schema = schema  # Interpretation depends on response_type
```

#### PromptManager.load_config

Изменения не требуются - существующая загрузка конфигурации уже обрабатывает
ключ `schema`.

#### Разбор JSONL

Добавлен новый метод разбора ответов в формате JSONL:

```python
def parse_jsonl(self, text):
    """
    Parse JSONL response, returning list of valid objects.

    Invalid lines (malformed JSON, empty lines) are skipped with warnings.
    This provides truncation resilience - partial output yields partial results.
    """
    results = []

    for line_num, line in enumerate(text.strip().split('\n'), 1):
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip markdown code fence markers if present
        if line.startswith('```'):
            continue

        try:
            obj = json.loads(line)
            results.append(obj)
        except json.JSONDecodeError as e:
            # Log warning but continue - this provides truncation resilience
            logger.warning(f"JSONL parse error on line {line_num}: {e}")

    return results
```

#### Изменения в PromptManager.invoke

Расширить метод invoke для обработки нового типа ответа:

```python
async def invoke(self, id, input, llm):
    logger.debug("Invoking prompt template...")

    terms = self.terms | self.prompts[id].terms | input
    resp_type = self.prompts[id].response_type

    prompt = {
        "system": self.system_template.render(terms),
        "prompt": self.render(id, input)
    }

    resp = await llm(**prompt)

    if resp_type == "text":
        return resp

    if resp_type == "json":
        try:
            obj = self.parse_json(resp)
        except:
            logger.error(f"JSON parse failed: {resp}")
            raise RuntimeError("JSON parse fail")

        if self.prompts[id].schema:
            try:
                validate(instance=obj, schema=self.prompts[id].schema)
                logger.debug("Schema validation successful")
            except Exception as e:
                raise RuntimeError(f"Schema validation fail: {e}")

        return obj

    if resp_type == "jsonl":
        objects = self.parse_jsonl(resp)

        if not objects:
            logger.warning("JSONL parse returned no valid objects")
            return []

        # Validate each object against schema if provided
        if self.prompts[id].schema:
            validated = []
            for i, obj in enumerate(objects):
                try:
                    validate(instance=obj, schema=self.prompts[id].schema)
                    validated.append(obj)
                except Exception as e:
                    logger.warning(f"Object {i} failed schema validation: {e}")
            return validated

        return objects

    raise RuntimeError(f"Response type {resp_type} not known")
```

### Затронутые запросы

Следующие запросы должны быть перенесены в формат JSONL:

| Идентификатор запроса | Описание | Тип поля |
|-----------|-------------|------------|
| `extract-definitions` | Извлечение сущностей/определений | Нет (один тип) |
| `extract-relationships` | Извлечение отношений | Нет (один тип) |
| `extract-topics` | Извлечение темы/определения | Нет (один тип) |
| `extract-rows` | Извлечение структурированных строк | Нет (один тип) |
| `agent-kg-extract` | Комбинированное извлечение определений + отношений | Да: `"definition"`, `"relationship"` |
| `extract-with-ontologies` / `ontology-extract` | Извлечение на основе онтологии | Да: `"entity"`, `"relationship"`, `"attribute"` |

### Изменения API

#### Точка зрения клиента

Разбор JSONL прозрачен для вызывающих API сервиса запросов. Разбор происходит
на стороне сервера в сервисе запросов, и ответ возвращается через стандартное
поле `PromptResponse.object` в виде сериализованного массива JSON.

Когда клиенты вызывают сервис запросов (через `PromptClient.prompt()` или аналогично):

**`response-type: "json"`** с схемой массива → клиент получает Python `list`
**`response-type: "jsonl"`** → клиент получает Python `list`

С точки зрения клиента, оба возвращают идентичные структуры данных. Разница заключается только в том, как вывод LLM разбирается на стороне сервера:


Формат массива JSON: Один вызов `json.loads()`; полностью завершается с ошибкой, если усечен
Формат JSONL: Разбор построчно; дает частичные результаты, если усечен

Это означает, что существующий клиентский код, ожидающий список от запросов извлечения,
не требует изменений при переносе запросов из формата JSON в формат JSONL.

#### Возвращаемое значение сервера

Для `response-type: "jsonl"` метод `PromptManager.invoke()` возвращает
`list[dict]`, содержащий все успешно разобранные и проверенные объекты. Этот
список затем сериализуется в JSON для поля `PromptResponse.object`.

### Обработка ошибок

Пустые результаты: Возвращает пустой список `[]` с предупреждением в журнале
Частная ошибка разбора: Возвращает список успешно разобранных объектов с
  предупреждениями в журналах об ошибках
Полная ошибка разбора: Возвращает пустой список `[]` с предупреждениями в журналах

Это отличается от `response-type: "json"`, который вызывает `RuntimeError` при
ошибке разбора. Легкое поведение для JSONL намеренно, чтобы обеспечить
устойчивость к усечению.

### Пример конфигурации

Полный пример конфигурации запроса:

```json
{
  "prompt": "Extract all entities and their definitions from the following text. Output one JSON object per line.\n\nText:\n{{text}}\n\nOutput format per line:\n{\"entity\": \"<name>\", \"definition\": \"<definition>\"}",
  "response-type": "jsonl",
  "schema": {
    "type": "object",
    "properties": {
      "entity": {
        "type": "string",
        "description": "The entity name"
      },
      "definition": {
        "type": "string",
        "description": "A clear definition of the entity"
      }
    },
    "required": ["entity", "definition"]
  }
}
```

## Соображения безопасности

**Проверка входных данных**: Разбор JSON использует стандартную `json.loads()`, что безопасно
  от атак внедрения.
**Проверка схемы**: Используется `jsonschema.validate()` для обеспечения соответствия схеме.
**Отсутствие новых уязвимостей**: Разбор JSONL значительно безопаснее, чем разбор JSON-массивов,
  благодаря обработке построчно.

## Соображения производительности

**Память**: Построчный разбор использует меньше пиковой памяти, чем загрузка полных
  JSON-массивов.
**Задержка**: Производительность разбора сопоставима с разбором JSON-массивов.
**Проверка**: Проверка схемы выполняется для каждого объекта, что добавляет накладные
  расходы, но позволяет получать частичные результаты в случае сбоя проверки.

## Стратегия тестирования

### Юнит-тесты

Разбор JSONL с допустимыми входными данными.
Разбор JSONL с пустыми строками.
<<<<<<< HEAD
Разбор JSONL с блоками форматированного текста Markdown.
=======
Разбор JSONL с блоками кода Markdown.
>>>>>>> 82edf2d (New md files from RunPod)
Разбор JSONL с обрезанной последней строкой.
Разбор JSONL со строками, содержащими недопустимый JSON.
Проверка схемы с использованием `oneOf` для дискриминируемых объединений.
Обратная совместимость: существующие `"text"` и `"json"` подсказки не изменены.

### Интеграционные тесты

<<<<<<< HEAD
Комплексная извлечение данных с использованием подсказок JSONL.
Извлечение данных с имитацией усечения (искусственно ограниченный ответ).
Извлечение данных смешанных типов с использованием дискриминатора типов.
Извлечение данных онтологии со всеми тремя типами.

### Тесты качества извлечения данных.
=======
Комплексная извлечение с подсказками JSONL.
Извлечение с имитацией усечения (искусственно ограниченный ответ).
Извлечение смешанных типов с использованием дискриминатора типа.
Извлечение онтологии со всеми тремя типами.

### Тесты качества извлечения.
>>>>>>> 82edf2d (New md files from RunPod)

Сравнение результатов извлечения: формат JSONL против массива JSON.
Проверка устойчивости к усечению: JSONL возвращает частичные результаты, в то время как JSON - нет.

## План миграции

### Этап 1: Реализация

1. Реализовать метод `parse_jsonl()` в `PromptManager`.
2. Расширить `invoke()` для обработки `response-type: "jsonl"`.
3. Добавить модульные тесты.

### Этап 2: Миграция подсказок

1. Обновить подсказку `extract-definitions` и конфигурацию.
2. Обновить подсказку `extract-relationships` и конфигурацию.
3. Обновить подсказку `extract-topics` и конфигурацию.
4. Обновить подсказку `extract-rows` и конфигурацию.
5. Обновить подсказку `agent-kg-extract` и конфигурацию.
6. Обновить подсказку `extract-with-ontologies` и конфигурацию.

### Этап 3: Обновления для последующих этапов

1. Обновить любой код, использующий результаты извлечения, чтобы он мог обрабатывать возвращаемый тип списка.
2. Обновить код, который категоризует извлечения смешанных типов, используя поле `type`.
3. Обновить тесты, которые проверяют формат выходных данных извлечения.

## Открытые вопросы

На данный момент нет.

## Ссылки

Текущая реализация: `trustgraph-flow/trustgraph/template/prompt_manager.py`
Спецификация JSON Lines: https://jsonlines.org/
Схема JSON `oneOf`: https://json-schema.org/understanding-json-schema/reference/combining.html#oneof
Связанная спецификация: Streaming LLM Responses (`docs/tech-specs/streaming-llm-responses.md`)
