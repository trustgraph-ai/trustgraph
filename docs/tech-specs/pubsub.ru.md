---
layout: default
title: "Инфраструктура Pub/Sub"
parent: "Russian (Beta)"
---

# Инфраструктура Pub/Sub

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Обзор

Этот документ содержит описание всех соединений между кодовой базой TrustGraph и инфраструктурой pub/sub. В настоящее время система жестко запрограммирована на использование Apache Pulsar. Этот анализ определяет все точки интеграции для будущей рефакторизации в сторону конфигурируемой абстракции pub/sub.

## Текущее состояние: точки интеграции Pulsar

### 1. Прямое использование клиента Pulsar

**Местоположение:** `trustgraph-flow/trustgraph/gateway/service.py`

API-шлюз напрямую импортирует и создает экземпляр клиента Pulsar:

**Строка 20:** `import pulsar`
**Строки 54-61:** Прямая инициализация `pulsar.Client()` с необязательными параметрами `pulsar.AuthenticationToken()`
**Строки 33-35:** Конфигурация хоста Pulsar по умолчанию из переменных окружения
**Строки 178-192:** Аргументы командной строки для `--pulsar-host`, `--pulsar-api-key` и `--pulsar-listener`
**Строки 78, 124:** Передача `pulsar_client` в `ConfigReceiver` и `DispatcherManager`

Это единственное место, где напрямую создается экземпляр клиента Pulsar за пределами слоя абстракции.

### 2. Базовая платформа процессоров

**Местоположение:** `trustgraph-base/trustgraph/base/async_processor.py`

Базовый класс для всех процессоров обеспечивает подключение к Pulsar:

**Строка 9:** `import _pulsar` (для обработки исключений)
**Строка 18:** `from . pubsub import PulsarClient`
**Строка 38:** Создание `pulsar_client_object = PulsarClient(**params)`
**Строки 104-108:** Свойства, предоставляющие доступ к `pulsar_host` и `pulsar_client`
**Строка 250:** Статический метод `add_args()` вызывает `PulsarClient.add_args(parser)` для аргументов командной строки
**Строки 223-225:** Обработка исключений для `_pulsar.Interrupted`

Все процессоры наследуются от `AsyncProcessor`, что делает это центральной точкой интеграции.

### 3. Абстракция потребителя

**Местоположение:** `trustgraph-base/trustgraph/base/consumer.py`

Потребляет сообщения из очередей и вызывает функции обработчиков:

**Импорты Pulsar:**
**Строка 12:** `from pulsar.schema import JsonSchema`
**Строка 13:** `import pulsar`
**Строка 14:** `import _pulsar`

**Использование, специфичное для Pulsar:**
**Строки 100, 102:** `pulsar.InitialPosition.Earliest` / `pulsar.InitialPosition.Latest`
**Строка 108:** Обертка `JsonSchema(self.schema)`
**Строка 110:** `pulsar.ConsumerType.Shared`
**Строки 104-111:** `self.client.subscribe()` с параметрами, специфичными для Pulsar
**Строки 143, 150, 65:** Методы `consumer.unsubscribe()` и `consumer.close()`
**Строка 162:** Исключение `_pulsar.Timeout`
**Строки 182, 205, 232:** `consumer.acknowledge()` / `consumer.negative_acknowledge()`

**Спецификационный файл:** `trustgraph-base/trustgraph/base/consumer_spec.py`
**Строка 22:** Ссылка на `processor.pulsar_client`

### 4. Абстракция производителя

**Местоположение:** `trustgraph-base/trustgraph/base/producer.py`

Отправляет сообщения в очереди:

**Импорты Pulsar:**
**Строка 2:** `from pulsar.schema import JsonSchema`

**Использование, специфичное для Pulsar:**
**Строка 49:** Обертка `JsonSchema(self.schema)`
**Строки 47-51:** `self.client.create_producer()` с параметрами, специфичными для Pulsar (тема, схема, включение фрагментации)
**Строки 31, 76:** Метод `producer.close()`
**Строки 64-65:** `producer.send()` с сообщением и свойствами

**Спецификационный файл:** `trustgraph-base/trustgraph/base/producer_spec.py`
**Строка 18:** Ссылка на `processor.pulsar_client`

### 5. Абстракция издателя

**Местоположение:** `trustgraph-base/trustgraph/base/publisher.py`

Асинхронная публикация сообщений с буферизацией очереди:

**Импорты Pulsar:**
**Строка 2:** `from pulsar.schema import JsonSchema`
**Строка 6:** `import pulsar`

**Использование, специфичное для Pulsar:**
**Строка 52:** Обертка `JsonSchema(self.schema)`
**Строки 50-54:** `self.client.create_producer()` с параметрами, специфичными для Pulsar
**Строки 101, 103:** `producer.send()` с сообщением и необязательными свойствами
**Строки 106-107:** Методы `producer.flush()` и `producer.close()`

### 6. Абстракция подписчика

**Местоположение:** `trustgraph-base/trustgraph/base/subscriber.py`

Предоставляет распределение сообщений для нескольких получателей из очередей:

**Импорт Pulsar:**
**Строка 6:** `from pulsar.schema import JsonSchema`
**Строка 8:** `import _pulsar`

**Использование, специфичное для Pulsar:**
**Строка 55:** `JsonSchema(self.schema)` wrapper
**Строка 57:** `self.client.subscribe(**subscribe_args)`
**Строки 101, 136, 160, 167-172:** Исключения Pulsar: `_pulsar.Timeout`, `_pulsar.InvalidConfiguration`, `_pulsar.AlreadyClosed`
**Строки 159, 166, 170:** Методы потребителя: `negative_acknowledge()`, `unsubscribe()`, `close()`
**Строки 247, 251:** Подтверждение сообщений: `acknowledge()`, `negative_acknowledge()`

**Файл спецификации:** `trustgraph-base/trustgraph/base/subscriber_spec.py`
**Строка 19:** Ссылается на `processor.pulsar_client`

### 7. Система схем (Heart of Darkness)

**Расположение:** `trustgraph-base/trustgraph/schema/`

Каждая схема сообщения в системе определяется с использованием фреймворка схем Pulsar.

**Основные примитивы:** `schema/core/primitives.py`
**Строка 2:** `from pulsar.schema import Record, String, Boolean, Array, Integer`
Все схемы наследуются от базового класса Pulsar `Record`
Все типы полей являются типами Pulsar: `String()`, `Integer()`, `Boolean()`, `Array()`, `Map()`, `Double()`

**Примеры схем:**
`schema/services/llm.py` (Строка 2): `from pulsar.schema import Record, String, Array, Double, Integer, Boolean`
`schema/services/config.py` (Строка 2): `from pulsar.schema import Record, Bytes, String, Boolean, Array, Map, Integer`

**Именование тем:** `schema/core/topic.py`
**Строки 2-3:** Формат темы: `{kind}://{tenant}/{namespace}/{topic}`
Эта структура URI специфична для Pulsar (например, `persistent://tg/flow/config`)

**Влияние:**
Все определения сообщений запроса/ответа во всем коде используют схемы Pulsar
Это включает в себя сервисы для: config, flow, llm, prompt, query, storage, agent, collection, diagnosis, library, lookup, nlp_query, objects_query, retrieval, structured_query
Определения схем импортируются и используются во всех процессорах и сервисах.

## Краткое описание

### Зависимости Pulsar по категориям

1. **Инициализация клиента:**
   Прямая: `gateway/service.py`
   Абстрактная: `async_processor.py` → `pubsub.py` (PulsarClient)

2. **Транспортировка сообщений:**
   Потребитель: `consumer.py`, `consumer_spec.py`
   Издатель: `producer.py`, `producer_spec.py`
   Публикатор: `publisher.py`
   Подписчик: `subscriber.py`, `subscriber_spec.py`

3. **Система схем:**
   Базовые типы: `schema/core/primitives.py`
   Все схемы сервисов: `schema/services/*.py`
   Именование тем: `schema/core/topic.py`

4. **Требуются концепции, специфичные для Pulsar:**
   Сообщения на основе тем
   Система схем (Record, типы полей)
   Общие подписки
   Подтверждение сообщений (положительное/отрицательное)
   Позиционирование потребителя (самое начало/последнее)
   Свойства сообщений
   Начальные позиции и типы потребителей
   Поддержка разбиения на части
   Постоянные и непостоянные темы

### Проблемы рефакторинга

Хорошая новость: слой абстракции (Consumer, Producer, Publisher, Subscriber) обеспечивает четкую инкапсуляцию большинства взаимодействий с Pulsar.

Проблемы:
1. **Всепроникающая система схем:** Каждое определение сообщения использует `pulsar.schema.Record` и типы Pulsar.
2. **Перечисления, специфичные для Pulsar:** `InitialPosition`, `ConsumerType`
3. **Исключения Pulsar:** `_pulsar.Timeout`, `_pulsar.Interrupted`, `_pulsar.InvalidConfiguration`, `_pulsar.AlreadyClosed`
4. **Сигнатуры методов:** `acknowledge()`, `negative_acknowledge()`, `subscribe()`, `create_producer()` и т.д.
5. **Формат URI темы:** Структура Pulsar `kind://tenant/namespace/topic`

### Следующие шаги

Чтобы сделать инфраструктуру публикации/подписки настраиваемой, нам нужно:

1. Создать интерфейс абстракции для системы клиента/схем.
2. Абстрагировать перечисления и исключения, специфичные для Pulsar.
3. Создать обертки для схем или альтернативные определения схем.
4. Реализовать интерфейс как для Pulsar, так и для альтернативных систем (Kafka, RabbitMQ, Redis Streams и т.д.).
5. Обновить `pubsub.py`, чтобы он был настраиваемым и поддерживал несколько бэкендов.
6. Предоставить путь миграции для существующих развертываний.

## Предварительный черновик подхода 1: Шаблон адаптера со слоем перевода схем

### Ключевое понимание
**Система схем** является наиболее глубокой точкой интеграции - от нее зависит все остальное. Мы должны решить эту проблему в первую очередь, иначе нам придется переписывать весь код.

### Стратегия: Минимальное нарушение с помощью адаптеров

**1. Сохраняйте схемы Pulsar в качестве внутреннего представления**
Не переписывайте все определения схем.
Схемы остаются `pulsar.schema.Record` во внутреннем представлении.
Используйте адаптеры для преобразования данных на границе между нашим кодом и бэкендом pub/sub.

**2. Создайте абстрактный слой pub/sub:**

```
┌─────────────────────────────────────┐
│   Existing Code (unchanged)         │
│   - Uses Pulsar schemas internally  │
│   - Consumer/Producer/Publisher     │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│   PubSubFactory (configurable)      │
│   - Creates backend-specific client │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
┌───────▼─────┐  ┌────▼─────────┐
│ PulsarAdapter│  │ KafkaAdapter │  etc...
│ (passthrough)│  │ (translates) │
└──────────────┘  └──────────────┘
```

**3. Определение абстрактных интерфейсов:**
`PubSubClient` - клиентское подключение
`PubSubProducer` - отправка сообщений
`PubSubConsumer` - получение сообщений
`SchemaAdapter` - преобразование схем Pulsar в/из JSON или форматы, специфичные для бэкенда

**4. Детали реализации:**

Для **адаптера Pulsar**: Практически без изменений, минимальное преобразование.

Для **других бэкендов** (Kafka, RabbitMQ и т.д.):
Сериализация объектов Pulsar Record в JSON/байты.
Отображение понятий, таких как:
  `InitialPosition.Earliest/Latest` → auto.offset.reset в Kafka
  `acknowledge()` → commit в Kafka
  `negative_acknowledge()` → Паттерн повторной отправки или DLQ (Dead Letter Queue)
  URI тем → Имена тем, специфичные для бэкенда.

### Анализ

**Преимущества:**
✅ Минимальные изменения существующего кода.
✅ Схемы остаются без изменений (без необходимости масштабной переработки).
✅ Постепенный путь миграции.
✅ Пользователи Pulsar не заметят разницы.
✅ Новые бэкенды добавляются через адаптеры.

**Недостатки:**
⚠️ Все еще присутствует зависимость от Pulsar (для определений схем).
⚠️ Некоторые несовместимости при преобразовании понятий.

### Альтернативное решение

Создать **систему схем TrustGraph**, которая является агностической к pub/sub (используя dataclasses или Pydantic), а затем генерировать схемы Pulsar/Kafka/и т.д. из нее. Это требует переписывания каждого файла схемы и может привести к несовместимым изменениям.

### Рекомендации для версии 1

Начните с **подхода с использованием адаптеров**, потому что:
1. Это практичный подход, который работает с существующим кодом.
2. Подтверждает концепцию с минимальным риском.
3. Может быть усовершенствован до нативной системы схем в будущем, если это необходимо.
4. Управление конфигурацией: одна переменная окружения переключает бэкенды.

## Подход, версия 2: Система схем, независимая от бэкенда, с использованием dataclasses

### Основная концепция

Используйте Python **dataclasses** в качестве нейтрального формата определения схемы. Каждый бэкенд pub/sub предоставляет свой собственный механизм сериализации/десериализации для dataclasses, что устраняет необходимость сохранения схем Pulsar в кодовой базе.

### Полиморфизм схем на уровне фабрики

Вместо преобразования схем Pulsar, **каждый бэкенд предоставляет собственную обработку схем**, которая работает со стандартными Python dataclasses.

### Поток публикации

```python
# 1. Get the configured backend from factory
pubsub = get_pubsub()  # Returns PulsarBackend, MQTTBackend, etc.

# 2. Get schema class from the backend
# (Can be imported directly - backend-agnostic)
from trustgraph.schema.services.llm import TextCompletionRequest

# 3. Create a producer/publisher for a specific topic
producer = pubsub.create_producer(
    topic="text-completion-requests",
    schema=TextCompletionRequest  # Tells backend what schema to use
)

# 4. Create message instances (same API regardless of backend)
request = TextCompletionRequest(
    system="You are helpful",
    prompt="Hello world",
    streaming=False
)

# 5. Send the message
producer.send(request)  # Backend serializes appropriately
```

### Поток пользователей

```python
# 1. Get the configured backend
pubsub = get_pubsub()

# 2. Create a consumer
consumer = pubsub.subscribe(
    topic="text-completion-requests",
    schema=TextCompletionRequest  # Tells backend how to deserialize
)

# 3. Receive and deserialize
msg = consumer.receive()
request = msg.value()  # Returns TextCompletionRequest dataclass instance

# 4. Use the data (type-safe access)
print(request.system)   # "You are helpful"
print(request.prompt)   # "Hello world"
print(request.streaming)  # False
```

### Что происходит за кулисами

**Для бэкенда Pulsar:**
`create_producer()` → создает производителя Pulsar с JSON-схемой или динамически генерируемой записью
`send(request)` → сериализует dataclass в формат JSON/Pulsar, отправляет в Pulsar
`receive()` → получает сообщение Pulsar, десериализует обратно в dataclass

**Для бэкенда MQTT:**
`create_producer()` → подключается к MQTT-брокеру, регистрация схемы не требуется
`send(request)` → преобразует dataclass в JSON, публикует в MQTT-топик
`receive()` → подписывается на MQTT-топик, десериализует JSON в dataclass

**Для бэкенда Kafka:**
`create_producer()` → создает производителя Kafka, регистрирует схему Avro, если необходимо
`send(request)` → сериализует dataclass в формат Avro, отправляет в Kafka
`receive()` → получает сообщение Kafka, десериализует Avro обратно в dataclass

### Ключевые моменты проектирования

1. **Создание объекта схемы**: Экземпляр dataclass (`TextCompletionRequest(...)`) идентичен независимо от бэкенда
2. **Бэкенд обрабатывает кодирование**: Каждый бэкенд знает, как сериализовать свой dataclass в формат для передачи данных
3. **Определение схемы при создании**: При создании производителя/потребителя вы указываете тип схемы
4. **Сохранение типобезопасности**: Вы получаете правильный объект `TextCompletionRequest`, а не словарь
5. **Отсутствие утечек бэкенда**: Код приложения никогда не импортирует библиотеки, специфичные для бэкенда

### Пример преобразования

**Текущий (специфичный для Pulsar):**
```python
# schema/services/llm.py
from pulsar.schema import Record, String, Boolean, Integer

class TextCompletionRequest(Record):
    system = String()
    prompt = String()
    streaming = Boolean()
```

**Новое (независимое от бэкенда):**
```python
# schema/services/llm.py
from dataclasses import dataclass

@dataclass
class TextCompletionRequest:
    system: str
    prompt: str
    streaming: bool = False
```

### Интеграция с бэкендом

Каждый бэкенд отвечает за сериализацию/десериализацию dataclasses:

**Бэкенд Pulsar:**
Динамически генерирует классы `pulsar.schema.Record` из dataclasses
Или сериализует dataclasses в JSON и использует JSON-схему Pulsar
Обеспечивает совместимость с существующими развертываниями Pulsar

**Бэкенд MQTT/Redis:**
Прямая сериализация в JSON экземпляров dataclass
Использует `dataclasses.asdict()` / `from_dict()`
Легковесный, не требуется реестр схем

**Бэкенд Kafka:**
Генерирует схемы Avro из определений dataclass
Использует реестр схем Confluent
Типобезопасная сериализация с поддержкой эволюции схемы

### Архитектура

```
┌─────────────────────────────────────┐
│   Application Code                  │
│   - Uses dataclass schemas          │
│   - Backend-agnostic                │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│   PubSubFactory (configurable)      │
│   - get_pubsub() returns backend    │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
┌───────▼─────────┐  ┌────▼──────────────┐
│ PulsarBackend   │  │ MQTTBackend       │
│ - JSON schema   │  │ - JSON serialize  │
│ - or dynamic    │  │ - Simple queues   │
│   Record gen    │  │                   │
└─────────────────┘  └───────────────────┘
```

### Детали реализации

**1. Определение схем:** Простые классы данных с подсказками типов
   `str`, `int`, `bool`, `float` для примитивов
   `list[T]` для массивов
   `dict[str, T]` для словарей
   Вложенные классы данных для сложных типов

**2. Каждый бэкенд предоставляет:**
   Сериализатор: `dataclass → bytes/wire format`
   Десериализатор: `bytes/wire format → dataclass`
   Регистрация схемы (если необходимо, например, для Pulsar/Kafka)

**3. Абстракция потребителя/производителя:**
   Уже существует (consumer.py, producer.py)
   Обновление для использования сериализации бэкенда
   Удаление прямых импортов Pulsar

**4. Отображение типов:**
   Pulsar `String()` → Python `str`
   Pulsar `Integer()` → Python `int`
   Pulsar `Boolean()` → Python `bool`
   Pulsar `Array(T)` → Python `list[T]`
   Pulsar `Map(K, V)` → Python `dict[K, V]`
   Pulsar `Double()` → Python `float`
   Pulsar `Bytes()` → Python `bytes`

### Путь миграции

1. **Создайте версии классов данных** для всех схем в `trustgraph/schema/`
2. **Обновите классы бэкенда** (Consumer, Producer, Publisher, Subscriber) для использования сериализации, предоставляемой бэкендом
3. **Реализуйте PulsarBackend** с использованием JSON-схемы или динамической генерации записей
4. **Протестируйте с Pulsar**, чтобы обеспечить обратную совместимость с существующими развертываниями
5. **Добавьте новые бэкенды** (MQTT, Kafka, Redis и т. д.) по мере необходимости
6. **Удалите импорты Pulsar** из файлов схем

### Преимущества

✅ **Отсутствие зависимости от pub/sub** в определениях схем
✅ **Стандартный Python** - легко понять, проверить типы, документировать
✅ **Современные инструменты** - работает с mypy, автодополнением IDE, линтерами
✅ **Оптимизировано для бэкенда** - каждый бэкенд использует собственную сериализацию
✅ **Отсутствие накладных расходов на преобразование** - прямая сериализация, без адаптеров
✅ **Безопасность типов** - реальные объекты с правильными типами
✅ **Простая проверка** - можно использовать Pydantic, если необходимо

### Проблемы и решения

**Проблема:** У `Record` Pulsar есть проверка полей во время выполнения
**Решение:** Используйте классы данных Pydantic для проверки, если это необходимо, или функции Python 3.10+ для классов данных с `__post_init__`

**Проблема:** Некоторые специфичные для Pulsar функции (например, тип `Bytes`)
**Решение:** Отобразите на тип `bytes` в классе данных, бэкенд обрабатывает кодирование соответствующим образом

**Проблема:** Именование тем (`persistent://tenant/namespace/topic`)
**Решение:** Абстрагируйте имена тем в определениях схем, бэкенд преобразует в правильный формат

**Проблема:** Эволюция и версионирование схем
**Решение:** Каждый бэкенд обрабатывает это в соответствии со своими возможностями (версии схем Pulsar, реестр схем Kafka и т. д.)

**Проблема:** Вложенные сложные типы
**Решение:** Используйте вложенные классы данных, бэкенды рекурсивно сериализуют/десериализуют

### Принятые решения

1. **Обычные классы данных или Pydantic?**
   ✅ **Решение: Используйте обычные классы данных Python**
   Проще, без дополнительных зависимостей
   Проверка не требуется на практике
   Легче понять и поддерживать

2. **Эволюция схемы:**
   ✅ **Решение: Механизм версионирования не требуется**
   Схемы стабильны и долговечны
   Обновления обычно добавляют новые поля (обратная совместимость)
   Бэкенды обрабатывают эволюцию схемы в соответствии со своими возможностями

3. **Обратная совместимость:**
   ✅ **Решение: Изменение основной версии, обратная совместимость не требуется**
   Это будет изменение, нарушающее обратную совместимость, с инструкциями по миграции
   Чистый разрыв позволяет лучше спроектировать систему
   Будет предоставлено руководство по миграции для существующих развертываний

4. **Вложенные типы и сложные структуры:**
   ✅ **Решение: Используйте вложенные классы данных естественным образом**
   Классы данных Python отлично справляются с вложенностью
   `list[T]` для массивов, `dict[K, V]` для словарей
   Бэкенды рекурсивно сериализуют/десериализуют
   Пример:
     ```python
     @dataclass
     class Value:
         value: str
         is_uri: bool

     @dataclass
     class Triple:
         s: Value              # Nested dataclass
         p: Value
         o: Value

     @dataclass
     class GraphQuery:
         triples: list[Triple]  # Array of nested dataclasses
         metadata: dict[str, str]
     ```

5. **Значения по умолчанию и необязательные поля:**
   ✅ **Решение: Комбинация обязательных, полей со значениями по умолчанию и необязательных полей**
   Обязательные поля: Не имеют значения по умолчанию.
   Поля со значениями по умолчанию: Всегда присутствуют, имеют разумные значения по умолчанию.
   Действительно необязательные поля: `T | None = None`, опускаются при сериализации, когда `None`
   Пример:
     ```python
     @dataclass
     class TextCompletionRequest:
         system: str              # Required, no default
         prompt: str              # Required, no default
         streaming: bool = False  # Optional with default value
         metadata: dict | None = None  # Truly optional, can be absent
     ```

   **Важные семантические аспекты сериализации:**

   Когда `metadata = None`:
   ```json
   {
       "system": "...",
       "prompt": "...",
       "streaming": false
       // metadata field NOT PRESENT
   }
   ```

   Когда `metadata = {}` (явно пусто):
   ```json
   {
       "system": "...",
       "prompt": "...",
       "streaming": false,
       "metadata": {}  // Field PRESENT but empty
   }
   ```

   **Ключевое отличие:**
   `None` → поле отсутствует в JSON (не сериализуется)
   Пустое значение (`{}`, `[]`, `""`) → поле присутствует со значением "пусто"
   Это имеет семантическое значение: "не предоставлено" против "явно пусто"
   Механизмы сериализации должны пропускать поля `None`, а не кодировать их как `null`

## Предварительный вариант 3: Детали реализации

### Универсальный формат именования очередей

Замените специфичные для каждого бэкенда имена очередей на универсальный формат, который бэкенды могут сопоставить соответствующим образом.

**Формат:** `{qos}/{tenant}/{namespace}/{queue-name}`

Где:
`qos`: Уровень качества обслуживания (QoS)
  `q0` = best-effort (отправка без подтверждения)
  `q1` = at-least-once (требуется подтверждение)
  `q2` = exactly-once (двухфазное подтверждение)
`tenant`: Логическая группировка для многопользовательской среды
`namespace`: Подгруппа внутри арендатора
`queue-name`: Фактическое имя очереди/топика

**Примеры:**
```
q1/tg/flow/text-completion-requests
q2/tg/config/config-push
q0/tg/metrics/stats
```

### Отображение тем для бэкенда

Каждый бэкенд преобразует общий формат в свой собственный формат:

**Бэкенд Pulsar:**
```python
def map_topic(self, generic_topic: str) -> str:
    # Parse: q1/tg/flow/text-completion-requests
    qos, tenant, namespace, queue = generic_topic.split('/', 3)

    # Map QoS to persistence
    persistence = 'persistent' if qos in ['q1', 'q2'] else 'non-persistent'

    # Return Pulsar URI: persistent://tg/flow/text-completion-requests
    return f"{persistence}://{tenant}/{namespace}/{queue}"
```

**Бэкэнд MQTT:**
```python
def map_topic(self, generic_topic: str) -> tuple[str, int]:
    # Parse: q1/tg/flow/text-completion-requests
    qos, tenant, namespace, queue = generic_topic.split('/', 3)

    # Map QoS level
    qos_level = {'q0': 0, 'q1': 1, 'q2': 2}[qos]

    # Build MQTT topic including tenant/namespace for proper namespacing
    mqtt_topic = f"{tenant}/{namespace}/{queue}"

    return mqtt_topic, qos_level
```

### Обновленная вспомогательная функция для темы

```python
# schema/core/topic.py
def topic(queue_name, qos='q1', tenant='tg', namespace='flow'):
    """
    Create a generic topic identifier that can be mapped by backends.

    Args:
        queue_name: The queue/topic name
        qos: Quality of service
             - 'q0' = best-effort (no ack)
             - 'q1' = at-least-once (ack required)
             - 'q2' = exactly-once (two-phase ack)
        tenant: Tenant identifier for multi-tenancy
        namespace: Namespace within tenant

    Returns:
        Generic topic string: qos/tenant/namespace/queue_name

    Examples:
        topic('my-queue')  # q1/tg/flow/my-queue
        topic('config', qos='q2', namespace='config')  # q2/tg/config/config
    """
    return f"{qos}/{tenant}/{namespace}/{queue_name}"
```

### Конфигурация и инициализация

**Аргументы командной строки + переменные окружения:**

```python
# In base/async_processor.py - add_args() method
@staticmethod
def add_args(parser):
    # Pub/sub backend selection
    parser.add_argument(
        '--pubsub-backend',
        default=os.getenv('PUBSUB_BACKEND', 'pulsar'),
        choices=['pulsar', 'mqtt'],
        help='Pub/sub backend (default: pulsar, env: PUBSUB_BACKEND)'
    )

    # Pulsar-specific configuration
    parser.add_argument(
        '--pulsar-host',
        default=os.getenv('PULSAR_HOST', 'pulsar://localhost:6650'),
        help='Pulsar host (default: pulsar://localhost:6650, env: PULSAR_HOST)'
    )

    parser.add_argument(
        '--pulsar-api-key',
        default=os.getenv('PULSAR_API_KEY', None),
        help='Pulsar API key (env: PULSAR_API_KEY)'
    )

    parser.add_argument(
        '--pulsar-listener',
        default=os.getenv('PULSAR_LISTENER', None),
        help='Pulsar listener name (env: PULSAR_LISTENER)'
    )

    # MQTT-specific configuration
    parser.add_argument(
        '--mqtt-host',
        default=os.getenv('MQTT_HOST', 'localhost'),
        help='MQTT broker host (default: localhost, env: MQTT_HOST)'
    )

    parser.add_argument(
        '--mqtt-port',
        type=int,
        default=int(os.getenv('MQTT_PORT', '1883')),
        help='MQTT broker port (default: 1883, env: MQTT_PORT)'
    )

    parser.add_argument(
        '--mqtt-username',
        default=os.getenv('MQTT_USERNAME', None),
        help='MQTT username (env: MQTT_USERNAME)'
    )

    parser.add_argument(
        '--mqtt-password',
        default=os.getenv('MQTT_PASSWORD', None),
        help='MQTT password (env: MQTT_PASSWORD)'
    )
```

**Фабричная функция:**

```python
# In base/pubsub.py or base/pubsub_factory.py
def get_pubsub(**config) -> PubSubBackend:
    """
    Create and return a pub/sub backend based on configuration.

    Args:
        config: Configuration dict from command-line args
                Must include 'pubsub_backend' key

    Returns:
        Backend instance (PulsarBackend, MQTTBackend, etc.)
    """
    backend_type = config.get('pubsub_backend', 'pulsar')

    if backend_type == 'pulsar':
        return PulsarBackend(
            host=config.get('pulsar_host'),
            api_key=config.get('pulsar_api_key'),
            listener=config.get('pulsar_listener'),
        )
    elif backend_type == 'mqtt':
        return MQTTBackend(
            host=config.get('mqtt_host'),
            port=config.get('mqtt_port'),
            username=config.get('mqtt_username'),
            password=config.get('mqtt_password'),
        )
    else:
        raise ValueError(f"Unknown pub/sub backend: {backend_type}")
```

**Использование в AsyncProcessor:**

```python
# In async_processor.py
class AsyncProcessor:
    def __init__(self, **params):
        self.id = params.get("id")

        # Create backend from config (replaces PulsarClient)
        self.pubsub = get_pubsub(**params)

        # Rest of initialization...
```

### Интерфейс бэкенда

```python
class PubSubBackend(Protocol):
    """Protocol defining the interface all pub/sub backends must implement."""

    def create_producer(self, topic: str, schema: type, **options) -> BackendProducer:
        """
        Create a producer for a topic.

        Args:
            topic: Generic topic format (qos/tenant/namespace/queue)
            schema: Dataclass type for messages
            options: Backend-specific options (e.g., chunking_enabled)

        Returns:
            Backend-specific producer instance
        """
        ...

    def create_consumer(
        self,
        topic: str,
        subscription: str,
        schema: type,
        initial_position: str = 'latest',
        consumer_type: str = 'shared',
        **options
    ) -> BackendConsumer:
        """
        Create a consumer for a topic.

        Args:
            topic: Generic topic format (qos/tenant/namespace/queue)
            subscription: Subscription/consumer group name
            schema: Dataclass type for messages
            initial_position: 'earliest' or 'latest' (MQTT may ignore)
            consumer_type: 'shared', 'exclusive', 'failover' (MQTT may ignore)
            options: Backend-specific options

        Returns:
            Backend-specific consumer instance
        """
        ...

    def close(self) -> None:
        """Close the backend connection."""
        ...
```

```python
class BackendProducer(Protocol):
    """Protocol for backend-specific producer."""

    def send(self, message: Any, properties: dict = {}) -> None:
        """Send a message (dataclass instance) with optional properties."""
        ...

    def flush(self) -> None:
        """Flush any buffered messages."""
        ...

    def close(self) -> None:
        """Close the producer."""
        ...
```

```python
class BackendConsumer(Protocol):
    """Protocol for backend-specific consumer."""

    def receive(self, timeout_millis: int = 2000) -> Message:
        """
        Receive a message from the topic.

        Raises:
            TimeoutError: If no message received within timeout
        """
        ...

    def acknowledge(self, message: Message) -> None:
        """Acknowledge successful processing of a message."""
        ...

    def negative_acknowledge(self, message: Message) -> None:
        """Negative acknowledge - triggers redelivery."""
        ...

    def unsubscribe(self) -> None:
        """Unsubscribe from the topic."""
        ...

    def close(self) -> None:
        """Close the consumer."""
        ...
```

```python
class Message(Protocol):
    """Protocol for a received message."""

    def value(self) -> Any:
        """Get the deserialized message (dataclass instance)."""
        ...

    def properties(self) -> dict:
        """Get message properties/metadata."""
        ...
```

### Рефакторинг существующих классов

Существующие классы `Consumer`, `Producer`, `Publisher`, `Subscriber` остаются в основном без изменений:

**Текущие обязанности (сохранить):**
Асинхронная модель потоков и группы задач
Логика повторного подключения и обработка повторных попыток
Сбор метрик
Ограничение скорости
Управление параллелизмом

**Необходимые изменения:**
Удалить прямые импорты Pulsar (`pulsar.schema`, `pulsar.InitialPosition` и т.д.)
Принимать `BackendProducer`/`BackendConsumer` вместо клиента Pulsar
Передавать фактические операции публикации/подписки на экземпляры бэкенда
Отображать общие концепции на вызовы бэкенда

**Пример рефакторинга:**

```python
# OLD - consumer.py
class Consumer:
    def __init__(self, client, topic, subscriber, schema, ...):
        self.client = client  # Direct Pulsar client
        # ...

    async def consumer_run(self):
        # Uses pulsar.InitialPosition, pulsar.ConsumerType
        self.consumer = self.client.subscribe(
            topic=self.topic,
            schema=JsonSchema(self.schema),
            initial_position=pulsar.InitialPosition.Earliest,
            consumer_type=pulsar.ConsumerType.Shared,
        )

# NEW - consumer.py
class Consumer:
    def __init__(self, backend_consumer, schema, ...):
        self.backend_consumer = backend_consumer  # Backend-specific consumer
        self.schema = schema
        # ...

    async def consumer_run(self):
        # Backend consumer already created with right settings
        # Just use it directly
        while self.running:
            msg = await asyncio.to_thread(
                self.backend_consumer.receive,
                timeout_millis=2000
            )
            await self.handle_message(msg)
```

### Специфические для бэкенда особенности

**Бэкенд Pulsar:**
Отображает `q0` → `non-persistent://`, `q1`/`q2` → `persistent://`
Поддерживает все типы потребителей (shared, exclusive, failover)
Поддерживает начальную позицию (earliest/latest)
Поддержка подтверждения получения сообщений
Поддержка реестра схем

**Бэкенд MQTT:**
Отображает `q0`/`q1`/`q2` → уровни качества обслуживания (QoS) MQTT 0/1/2
Включает арендатора/пространство имен в путь темы для обеспечения разделения имен
Автоматически генерирует идентификаторы клиентов из имен подписок
Игнорирует начальную позицию (нет истории сообщений в базовом MQTT)
Игнорирует тип потребителя (MQTT использует идентификаторы клиентов, а не группы потребителей)
Простая модель публикации/подписки

### Краткое описание принятых решений

1. ✅ **Универсальное именование очередей**: формат `qos/tenant/namespace/queue-name`
2. ✅ **QoS в идентификаторе очереди**: определяется определением очереди, а не конфигурацией
3. ✅ **Повторное подключение**: обрабатывается классами Consumer/Producer, а не бэкендами
4. ✅ **Темы MQTT**: включают арендатора/пространство имен для правильного разделения имен
5. ✅ **История сообщений**: MQTT игнорирует параметр `initial_position` (будущее улучшение)
6. ✅ **Идентификаторы клиентов**: бэкенд MQTT автоматически генерирует из имени подписки

### Будущие улучшения

**История сообщений MQTT:**
Можно добавить необязательный слой постоянного хранения (например, сохраненные сообщения, внешний хранилище)
Это позволит поддерживать `initial_position='earliest'`
Не требуется для первоначальной реализации
