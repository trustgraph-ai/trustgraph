---
layout: default
title: "Извлечение знаний из онтологий - Фаза 2, рефакторинг"
parent: "Russian (Beta)"
---

# Извлечение знаний из онтологий - Фаза 2, рефакторинг

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

**Статус**: Черновик
**Автор**: Аналитическая сессия 2025-12-03
**Связанные**: `ontology.md`, `ontorag.md`

## Обзор

Этот документ выявляет несоответствия в текущей системе извлечения знаний на основе онтологий и предлагает рефакторинг для повышения производительности LLM и снижения потери информации.

## Текущая реализация

### Как это работает сейчас

1. **Загрузка онтологии** (`ontology_loader.py`)
   Загружает JSON-файл онтологии с ключами, такими как `"fo/Recipe"`, `"fo/Food"`, `"fo/produces"`
   Идентификаторы классов включают префикс пространства имен в самом ключе
   Пример из `food.ontology`:
     ```json
     "classes": {
       "fo/Recipe": {
         "uri": "http://purl.org/ontology/fo/Recipe",
         "rdfs:comment": "A Recipe is a combination..."
       }
     }
     ```

2. **Построение запроса** (`extract.py:299-307`, `ontology-prompt.md`)
   Шаблон получает словари `classes`, `object_properties`, `datatype_properties`
   Шаблон выполняет итерацию: `{% for class_id, class_def in classes.items() %}`
   LLM видит: `**fo/Recipe**: A Recipe is a combination...`
   Пример формата вывода показывает:
     ```json
     {"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "Recipe"}
     {"subject": "recipe:cornish-pasty", "predicate": "has_ingredient", "object": "ingredient:flour"}
     ```

3. **Разбор ответа** (`extract.py:382-428`)
   Ожидается массив JSON: `[{"subject": "...", "predicate": "...", "object": "..."}]`
   Проверка на соответствие подмножеству онтологии
   Расширение URI с помощью `expand_uri()` (extract.py:473-521)

4. **Расширение URI** (`extract.py:473-521`)
   Проверяет, присутствует ли значение в словаре `ontology_subset.classes`
   Если найдено, извлекает URI из определения класса
   Если не найдено, создает URI: `f"https://trustgraph.ai/ontology/{ontology_id}#{value}"`

### Пример потока данных

**JSON онтологии → Загрузчик → Запрос:**
```
"fo/Recipe" → classes["fo/Recipe"] → LLM sees "**fo/Recipe**"
```

**Большая языковая модель → Парсер → Вывод:**
```
"Recipe" → not in classes["fo/Recipe"] → constructs URI → LOSES original URI
"fo/Recipe" → found in classes → uses original URI → PRESERVES URI
```

## Выявленные проблемы

### 1. **Несоответствие примеров в запросе**

**Проблема**: Шаблон запроса показывает идентификаторы классов с префиксами (`fo/Recipe`), но пример вывода использует имена классов без префиксов (`Recipe`).

**Местоположение**: `ontology-prompt.md:5-52`

```markdown
## Ontology Classes:
- **fo/Recipe**: A Recipe is...

## Example Output:
{"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "Recipe"}
```

**Влияние**: LLM получает противоречивые сигналы о том, какой формат использовать.

### 2. **Потеря информации при расширении URI**

**Проблема**: Когда LLM возвращает имена классов без префикса, следуя примеру, `expand_uri()` не может найти их в словаре онтологии и создает резервные URI, теряя исходные правильные URI.

**Местоположение**: `extract.py:494-500`

```python
if value in ontology_subset.classes:  # Looks for "Recipe"
    class_def = ontology_subset.classes[value]  # But key is "fo/Recipe"
    if isinstance(class_def, dict) and 'uri' in class_def:
        return class_def['uri']  # Never reached!
return f"https://trustgraph.ai/ontology/{ontology_id}#{value}"  # Fallback
```

**Влияние:**
Исходный URI: `http://purl.org/ontology/fo/Recipe`
Сформированный URI: `https://trustgraph.ai/ontology/food#Recipe`
Семантическое значение потеряно, нарушается совместимость.

### 3. **Неоднозначный формат экземпляра сущности**

**Проблема:** Отсутствуют четкие указания относительно формата URI экземпляра сущности.

**Примеры в запросе:**
`"recipe:cornish-pasty"` (префикс, похожий на пространство имен)
`"ingredient:flour"` (другой префикс)

**Фактическое поведение** (extract.py:517-520):
```python
# Treat as entity instance - construct unique URI
normalized = value.replace(" ", "-").lower()
return f"https://trustgraph.ai/{ontology_id}/{normalized}"
```

**Влияние**: LLM должна угадать соглашение о префиксах без контекста онтологии.

### 4. **Отсутствие рекомендаций по префиксам пространств имен**

**Проблема**: JSON-файл онтологии содержит определения пространств имен (строки 10-25 в food.ontology):
```json
"namespaces": {
  "fo": "http://purl.org/ontology/fo/",
  "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
  ...
}
```

Но эти данные никогда не передаются в языковую модель. Языковая модель не знает:
Что означает "fo"
Какой префикс использовать для сущностей
К каким элементам относится какое пространство имен

### 5. **Метки, не используемые в запросе**

**Проблема**: У каждого класса есть поля `rdfs:label` (например, `{"value": "Recipe", "lang": "en-gb"}`), но шаблон запроса их не использует.

**Текущая ситуация**: Отображаются только `class_id` и `comment`
```jinja
- **{{class_id}}**{% if class_def.comment %}: {{class_def.comment}}{% endif %}
```

**Доступно, но не используется**:
```python
"rdfs:label": [{"value": "Recipe", "lang": "en-gb"}]
```

**Влияние**: Может предоставить удобочитаемые имена наряду с техническими идентификаторами.

## Предлагаемые решения

### Вариант A: Нормализация до идентификаторов без префиксов

**Подход**: Удалять префиксы из идентификаторов классов перед отображением LLM.

**Изменения**:
1. Изменить `build_extraction_variables()` для преобразования ключей:
   ```python
   classes_for_prompt = {
       k.split('/')[-1]: v  # "fo/Recipe" → "Recipe"
       for k, v in ontology_subset.classes.items()
   }
   ```

2. Обновить пример запроса, чтобы он соответствовал (уже использует имена без префиксов).

3. Изменить `expand_uri()` для обработки обоих форматов:
   ```python
   # Try exact match first
   if value in ontology_subset.classes:
       return ontology_subset.classes[value]['uri']

   # Try with prefix
   for prefix in ['fo/', 'rdf:', 'rdfs:']:
       prefixed = f"{prefix}{value}"
       if prefixed in ontology_subset.classes:
           return ontology_subset.classes[prefixed]['uri']
   ```

**Преимущества:**
Более понятный и читаемый для человека.
Соответствует существующим примерам запросов.
Большие языковые модели (LLM) лучше работают с более простыми токенами.

**Недостатки:**
Конфликты имен классов, если несколько онтологий имеют одинаковое имя класса.
Потеря информации о пространстве имен.
Требуется логика обработки исключений для поиска.

### Вариант B: Использовать полные префиксные идентификаторы последовательно

**Подход:** Обновить примеры для использования префиксных идентификаторов, соответствующих тем, которые показаны в списке классов.

**Изменения:**
1. Обновить пример запроса (ontology-prompt.md:46-52):
   ```json
   [
     {"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "fo/Recipe"},
     {"subject": "recipe:cornish-pasty", "predicate": "rdfs:label", "object": "Cornish Pasty"},
     {"subject": "recipe:cornish-pasty", "predicate": "fo/produces", "object": "food:cornish-pasty"},
     {"subject": "food:cornish-pasty", "predicate": "rdf:type", "object": "fo/Food"}
   ]
   ```

2. Добавьте объяснение пространства имен в запрос:
   ```markdown
   ## Namespace Prefixes:
   - **fo/**: Food Ontology (http://purl.org/ontology/fo/)
   - **rdf:**: RDF Schema
   - **rdfs:**: RDF Schema

   Use these prefixes exactly as shown when referencing classes and properties.
   ```

3. Оставьте `expand_uri()` без изменений (это работает правильно, когда найдены совпадения).

**Преимущества:**
Согласованность входных и выходных данных.
Отсутствие потери информации.
Сохраняет семантику пространства имен.
Работает с несколькими онтологиями.

**Недостатки:**
Более многословные токены для LLM.
Требует от LLM отслеживания префиксов.

### Вариант C: Гибридный - Отображать и метку, и идентификатор.

**Подход:** Улучшить запрос, чтобы отображать как читаемые человеком метки, так и технические идентификаторы.

**Изменения:**
1. Обновить шаблон запроса:
   ```jinja
   {% for class_id, class_def in classes.items() %}
   - **{{class_id}}** (label: "{{class_def.labels[0].value if class_def.labels else class_id}}"){% if class_def.comment %}: {{class_def.comment}}{% endif %}
   {% endfor %}
   ```

   Пример вывода:
   ```markdown
   - **fo/Recipe** (label: "Recipe"): A Recipe is a combination...
   ```

2. Инструкции по обновлению:
   ```markdown
   When referencing classes:
   - Use the full prefixed ID (e.g., "fo/Recipe") in JSON output
   - The label (e.g., "Recipe") is for human understanding only
   ```

**Преимущества:**
Наиболее понятный формат для больших языковых моделей (LLM).
Сохраняет всю информацию.
Явно указывает, что использовать.

**Недостатки:**
Более длинный запрос.
Более сложный шаблон.

## Реализованный подход

**Упрощенный формат "Сущность-Отношение-Атрибут"** - полностью заменяет старый формат на основе троек.

Новый подход был выбран, потому что:

1. **Отсутствие потери информации:** Оригинальные URI сохраняются корректно.
2. **Более простая логика:** Не требуется преобразование, прямые запросы к словарям работают.
3. **Безопасность пространств имен:** Обрабатывает несколько онтологий без конфликтов.
4. **Семантическая корректность:** Сохраняет семантику RDF/OWL.

## Реализация завершена

### Что было создано:

1. **Новый шаблон запроса** (`prompts/ontology-extract-v2.txt`)
   ✅ Четкие разделы: Типы сущностей, Отношения, Атрибуты.
   ✅ Пример использования полных идентификаторов типов (`fo/Recipe`, `fo/has_ingredient`).
   ✅ Инструкции по использованию точных идентификаторов из схемы.
   ✅ Новый формат JSON с массивами сущностей/отношений/атрибутов.

2. **Нормализация сущностей** (`entity_normalizer.py`)
   ✅ `normalize_entity_name()` - Преобразует имена в формат, безопасный для URI.
   ✅ `normalize_type_identifier()` - Обрабатывает слеши в типах (`fo/Recipe` → `fo-recipe`).
   ✅ `build_entity_uri()` - Создает уникальные URI, используя кортеж (имя, тип).
   ✅ `EntityRegistry` - Отслеживает сущности для исключения дубликатов.

3. **JSON-парсер** (`simplified_parser.py`)
   ✅ Парсит новый формат: `{entities: [...], relationships: [...], attributes: [...]}`
   ✅ Поддерживает имена полей в формате kebab-case и snake_case.
   ✅ Возвращает структурированные классы данных.
   ✅ Корректная обработка ошибок с ведением журнала.

4. **Тройной преобразователь** (`triple_converter.py`)
   ✅ `convert_entity()` - Автоматически генерирует тройки типа + метки.
   ✅ `convert_relationship()` - Соединяет URI сущностей через свойства.
   ✅ `convert_attribute()` - Добавляет литеральные значения.
   ✅ Выполняет поиск полных URI из определений онтологии.

5. **Обновленный основной процессор** (`extract.py`)
   ✅ Удален старый код извлечения на основе троек.
   ✅ Добавлен метод `extract_with_simplified_format()`.
   ✅ Теперь использует только новый упрощенный формат.
   ✅ Вызывает запрос с идентификатором `extract-with-ontologies-v2`.

## Тестовые примеры

### Тест 1: Сохранение URI
```python
# Given ontology class
classes = {"fo/Recipe": {"uri": "http://purl.org/ontology/fo/Recipe", ...}}

# When LLM returns
llm_output = {"subject": "x", "predicate": "rdf:type", "object": "fo/Recipe"}

# Then expanded URI should be
assert expanded == "http://purl.org/ontology/fo/Recipe"
# Not: "https://trustgraph.ai/ontology/food#Recipe"
```

### Тест 2: Конфликт между несколькими онтологиями
```python
# Given two ontologies
ont1 = {"fo/Recipe": {...}}
ont2 = {"cooking/Recipe": {...}}

# LLM should use full prefix to disambiguate
llm_output = {"object": "fo/Recipe"}  # Not just "Recipe"
```

### Тест 3: Формат экземпляра сущности
```python
# Given prompt with food ontology
# LLM should create instances like
{"subject": "recipe:cornish-pasty"}  # Namespace-style
{"subject": "food:beef"}              # Consistent prefix
```

## Открытые вопросы

1. **Следует ли экземплярам сущностей использовать префиксы пространств имен?**
   Сейчас: `"recipe:cornish-pasty"` (произвольно)
   Альтернатива: Использовать префикс онтологии `"fo:cornish-pasty"`?
   Альтернатива: Без префикса, расширить в URI `"cornish-pasty"` → полный URI?

2. **Как обрабатывать область определения/область значений в запросе?**
   В настоящее время отображается: `(Recipe → Food)`
   Должно ли быть: `(fo/Recipe → fo/Food)`?

3. **Следует ли нам проверять ограничения области определения/области значений?**
   TODO комментарий в extract.py:470
   Это позволило бы выявлять больше ошибок, но было бы сложнее.

4. **Что касается обратных свойств и эквивалентностей?**
   В онтологии есть `owl:inverseOf`, `owl:equivalentClass`
   В настоящее время не используются при извлечении.
   Следует ли их использовать?

## Показатели успеха

✅ Отсутствие потери информации об URI (100% сохранение исходных URI).
✅ Формат вывода LLM соответствует формату входных данных.
✅ Отсутствие неоднозначных примеров в запросе.
✅ Тесты проходят с использованием нескольких онтологий.
✅ Улучшенное качество извлечения (измеряется процентом допустимых троек).

## Альтернативный подход: Упрощенный формат извлечения

### Философия

Вместо того, чтобы просить LLM понимать семантику RDF/OWL, попросите его делать то, что он умеет хорошо: **находить сущности и отношения в тексте**.

Пусть код занимается построением URI, преобразованием в RDF и формальностями семантической паутины.

### Пример: Классификация сущностей

**Исходный текст:**
```
Cornish pasty is a traditional British pastry filled with meat and vegetables.
```

**Схема онтологии (показана LLM):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method
- Food: A food is something that can be eaten
- Ingredient: An ingredient combines a quantity and a food
```

**Что возвращает большая языковая модель (простой JSON):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    }
  ]
}
```

**Что генерирует код (тройки RDF):**
```python
# 1. Normalize entity name + type to ID (type prevents collisions)
entity_id = "recipe-cornish-pasty"  # normalize("Cornish pasty", "Recipe")
entity_uri = "https://trustgraph.ai/food/recipe-cornish-pasty"

# Note: Same name, different type = different URI
# "Cornish pasty" (Recipe) → recipe-cornish-pasty
# "Cornish pasty" (Food) → food-cornish-pasty

# 2. Generate triples
triples = [
    # Type triple
    Triple(
        s=Value(value=entity_uri, is_uri=True),
        p=Value(value="http://www.w3.org/1999/02/22-rdf-syntax-ns#type", is_uri=True),
        o=Value(value="http://purl.org/ontology/fo/Recipe", is_uri=True)
    ),
    # Label triple (automatic)
    Triple(
        s=Value(value=entity_uri, is_uri=True),
        p=Value(value="http://www.w3.org/2000/01/rdf-schema#label", is_uri=True),
        o=Value(value="Cornish pasty", is_uri=False)
    )
]
```

### Преимущества

1. **LLM (большая языковая модель) не должна:**
   Понимать синтаксис URI
   Придумывать префиксы идентификаторов (`recipe:`, `ingredient:`)
   Знать о `rdf:type` или `rdfs:label`
   Конструировать идентификаторы семантической паутины

2. **LLM просто должна:**
   Находить сущности в тексте
   Сопоставлять их с классами онтологии
   Извлекать отношения и атрибуты

3. **Код обрабатывает:**
   Нормализацию и построение URI
   Генерацию триплетов RDF
   Автоматическое присвоение меток
   Управление пространствами имен

### Почему это работает лучше

**Более простой запрос** = меньше путаницы = меньше ошибок
**Согласованные идентификаторы** = код контролирует правила нормализации
**Автоматически сгенерированные метки** = нет отсутствующих триплетов rdfs:label
**LLM фокусируется на извлечении** = на том, что она действительно хороша

### Пример: Отношения между сущностями

**Исходный текст:**
```
Cornish pasty is a traditional British pastry filled with beef and potatoes.
```

**Схема онтологии (показана LLM):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method
- Food: A food is something that can be eaten
- Ingredient: An ingredient combines a quantity and a food

## Relationships:
- has_ingredient: Relates a recipe to an ingredient it uses (Recipe → Ingredient)
- food: Relates an ingredient to the food that is required (Ingredient → Food)
```

**Что возвращает большая языковая модель (простой JSON):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    },
    {
      "entity": "beef",
      "type": "Food"
    },
    {
      "entity": "potatoes",
      "type": "Food"
    }
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "beef",
      "object-type": "Food"
    },
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "potatoes",
      "object-type": "Food"
    }
  ]
}
```

**Что генерирует код (тройки RDF):**
```python
# Normalize entity names to URIs
cornish_pasty_uri = "https://trustgraph.ai/food/cornish-pasty"
beef_uri = "https://trustgraph.ai/food/beef"
potatoes_uri = "https://trustgraph.ai/food/potatoes"

# Look up relation URI from ontology
has_ingredient_uri = "http://purl.org/ontology/fo/ingredients"  # from fo/has_ingredient

triples = [
    # Entity type triples (as before)
    Triple(s=cornish_pasty_uri, p=rdf_type, o="http://purl.org/ontology/fo/Recipe"),
    Triple(s=cornish_pasty_uri, p=rdfs_label, o="Cornish pasty"),

    Triple(s=beef_uri, p=rdf_type, o="http://purl.org/ontology/fo/Food"),
    Triple(s=beef_uri, p=rdfs_label, o="beef"),

    Triple(s=potatoes_uri, p=rdf_type, o="http://purl.org/ontology/fo/Food"),
    Triple(s=potatoes_uri, p=rdfs_label, o="potatoes"),

    # Relationship triples
    Triple(
        s=Value(value=cornish_pasty_uri, is_uri=True),
        p=Value(value=has_ingredient_uri, is_uri=True),
        o=Value(value=beef_uri, is_uri=True)
    ),
    Triple(
        s=Value(value=cornish_pasty_uri, is_uri=True),
        p=Value(value=has_ingredient_uri, is_uri=True),
        o=Value(value=potatoes_uri, is_uri=True)
    )
]
```

**Основные моменты:**
LLM возвращает имена сущностей на естественном языке: `"Cornish pasty"`, `"beef"`, `"potatoes"`
LLM включает типы для устранения неоднозначности: `subject-type`, `object-type`
LLM использует имя отношения из схемы: `"has_ingredient"`
Код генерирует согласованные идентификаторы, используя (имя, тип): `("Cornish pasty", "Recipe")` → `recipe-cornish-pasty`
Код ищет URI отношения в онтологии: `fo/has_ingredient` → полный URI
Одна и та же (имя, тип) всегда получает один и тот же URI (дедупликация)

### Пример: Разрешение неоднозначности имени сущности

**Проблема:** Одно и то же имя может относиться к разным типам сущностей.

**Реальный пример:**
```
"Cornish pasty" can be:
- A Recipe (instructions for making it)
- A Food (the dish itself)
```

**Как это обрабатывается:**

LLM возвращает оба элемента как отдельные сущности:
```json
{
  "entities": [
    {"entity": "Cornish pasty", "type": "Recipe"},
    {"entity": "Cornish pasty", "type": "Food"}
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "produces",
      "object": "Cornish pasty",
      "object-type": "Food"
    }
  ]
}
```

**Разрешение кода:**
```python
# Different types → different URIs
recipe_uri = normalize("Cornish pasty", "Recipe")
# → "https://trustgraph.ai/food/recipe-cornish-pasty"

food_uri = normalize("Cornish pasty", "Food")
# → "https://trustgraph.ai/food/food-cornish-pasty"

# Relationship connects them correctly
triple = Triple(
    s=recipe_uri,  # The Recipe
    p="http://purl.org/ontology/fo/produces",
    o=food_uri     # The Food
)
```

**Почему это работает:**
Тип включен во ВСЕ ссылки (сущности, отношения, атрибуты).
Код использует кортеж `(name, type)` в качестве ключа поиска.
Отсутствие неоднозначности, отсутствие конфликтов.

### Пример: Атрибуты сущности

**Исходный текст:**
```
This Cornish pasty recipe serves 4-6 people and takes 45 minutes to prepare.
```

**Схема онтологии (показана LLM):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method

## Attributes:
- serves: Indicates what the recipe is intended to serve (Recipe → text)
- preparation_time: Time needed to prepare the recipe (Recipe → text)
```

**Что возвращает большая языковая модель (простой JSON):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty recipe",
      "type": "Recipe"
    }
  ],
  "attributes": [
    {
      "entity": "Cornish pasty recipe",
      "entity-type": "Recipe",
      "attribute": "serves",
      "value": "4-6 people"
    },
    {
      "entity": "Cornish pasty recipe",
      "entity-type": "Recipe",
      "attribute": "preparation_time",
      "value": "45 minutes"
    }
  ]
}
```

**Что генерирует код (тройки RDF):**
```python
# Normalize entity name to URI
recipe_uri = "https://trustgraph.ai/food/cornish-pasty-recipe"

# Look up attribute URIs from ontology
serves_uri = "http://purl.org/ontology/fo/serves"  # from fo/serves
prep_time_uri = "http://purl.org/ontology/fo/preparation_time"  # from fo/preparation_time

triples = [
    # Entity type triple
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=rdf_type, is_uri=True),
        o=Value(value="http://purl.org/ontology/fo/Recipe", is_uri=True)
    ),

    # Label triple (automatic)
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=rdfs_label, is_uri=True),
        o=Value(value="Cornish pasty recipe", is_uri=False)
    ),

    # Attribute triples (objects are literals, not URIs)
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=serves_uri, is_uri=True),
        o=Value(value="4-6 people", is_uri=False)  # Literal value!
    ),
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=prep_time_uri, is_uri=True),
        o=Value(value="45 minutes", is_uri=False)  # Literal value!
    )
]
```

**Основные моменты:**
LLM извлекает строковые значения: `"4-6 people"`, `"45 minutes"`
LLM включает тип сущности для устранения неоднозначности: `entity-type`
LLM использует имя атрибута из схемы: `"serves"`, `"preparation_time"`
Код ищет URI атрибута из свойств типа данных онтологии
**Объект является строковым значением** (`is_uri=False`), а не ссылкой URI
Значения остаются в виде обычного текста, нормализация не требуется

**Различия с отношениями:**
Отношения: и субъект, и объект являются сущностями (URI)
Атрибуты: субъект является сущностью (URI), объект является строковым значением (строка/число)

### Полный пример: Сущности + Отношения + Атрибуты

**Исходный текст:**
```
Cornish pasty is a savory pastry filled with beef and potatoes.
This recipe serves 4 people.
```

**Что возвращает большая языковая модель:**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    },
    {
      "entity": "beef",
      "type": "Food"
    },
    {
      "entity": "potatoes",
      "type": "Food"
    }
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "beef",
      "object-type": "Food"
    },
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "potatoes",
      "object-type": "Food"
    }
  ],
  "attributes": [
    {
      "entity": "Cornish pasty",
      "entity-type": "Recipe",
      "attribute": "serves",
      "value": "4 people"
    }
  ]
}
```

**Результат:** Сгенерировано 11 тройных наборов RDF:
3 тройных набора, определяющих тип сущности (rdf:type)
3 тройных набора, определяющих метку сущности (rdfs:label) - автоматически
2 тройных набора, описывающих отношения (has_ingredient)
1 тройной набор, описывающий атрибут (serves)

Все это получено из простых, естественных текстовых извлечений с помощью LLM!

## Ссылки

Текущая реализация: `trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`
Шаблон запроса: `ontology-prompt.md`
Тестовые примеры: `tests/unit/test_extract/test_ontology/`
Пример онтологии: `e2e/test-data/food.ontology`
