# Техническое описание: Поддержка многопользовательской среды

## Обзор

Обеспечьте поддержку многопользовательской среды, устранив несоответствия в именах параметров, которые препятствуют настройке очередей, и добавив параметризацию пространства ключей Cassandra.

## Контекст архитектуры

### Разрешение очередей на основе потоков

Система TrustGraph использует **архитектуру на основе потоков** для динамического разрешения очередей, что изначально поддерживает многопользовательскую среду:

**Определения потоков** хранятся в Cassandra и указывают имена очередей через определения интерфейсов.
**Имена очередей используют шаблоны** с переменными `{id}`, которые заменяются идентификаторами экземпляров потоков.
**Сервисы динамически разрешают очереди**, получая конфигурации потоков в момент запроса.
**Каждый пользователь может иметь уникальные потоки** с разными именами очередей, что обеспечивает изоляцию.

Пример определения интерфейса потока:
```json
{
  "interfaces": {
    "triples-store": "persistent://tg/flow/triples-store:{id}",
    "graph-embeddings-store": "persistent://tg/flow/graph-embeddings-store:{id}"
  }
}
```

Когда арендатор A запускает поток `tenant-a-prod`, а арендатор B запускает поток `tenant-b-prod`, они автоматически получают изолированные очереди:
`persistent://tg/flow/triples-store:tenant-a-prod`
`persistent://tg/flow/triples-store:tenant-b-prod`

**Сервисы, правильно разработанные для многоарендности:**
✅ **Knowledge Management (основные компоненты)** - Динамически определяет очереди из конфигурации потока, передаваемой в запросах

**Сервисы, требующие исправления:**
🔴 **Config Service** - Несоответствие имен параметров препятствует настройке очереди
🔴 **Librarian Service** - Жестко заданные темы управления хранилищем (описано ниже)
🔴 **Все сервисы** - Невозможно настроить пространство ключей Cassandra

## Описание проблемы

### Проблема #1: Несоответствие имен параметров в AsyncProcessor
**CLI определяет:** `--config-queue` (неясное наименование)
**Argparse преобразует в:** `config_queue` (в словаре параметров)
**Код ищет:** `config_push_queue`
**Результат:** Параметр игнорируется, используется значение по умолчанию `persistent://tg/config/config`
**Влияние:** Затрагивает все 32+ сервиса, наследующие от AsyncProcessor
**Препятствует:** Многоарендные развертывания не могут использовать очереди, специфичные для арендатора
**Решение:** Переименовать параметр CLI в `--config-push-queue` для ясности (разрыв обратной совместимости допустим, так как функция в настоящее время не работает)

### Проблема #2: Несоответствие имен параметров в Config Service
**CLI определяет:** `--push-queue` (двусмысленное наименование)
**Argparse преобразует в:** `push_queue` (в словаре параметров)
**Код ищет:** `config_push_queue`
**Результат:** Параметр игнорируется
**Влияние:** Сервис Config не может использовать пользовательскую очередь отправки
**Решение:** Переименовать параметр CLI в `--config-push-queue` для согласованности и ясности (разрыв обратной совместимости допустим)

### Проблема #3: Жестко заданное пространство ключей Cassandra
**Текущее состояние:** Пространство ключей жестко задано как `"config"`, `"knowledge"`, `"librarian"` в различных сервисах
**Результат:** Невозможно настроить пространство ключей для многоарендных развертываний
**Влияние:** Сервисы Config, основные компоненты и Librarian
**Препятствует:** Несколько арендаторов не могут использовать отдельные пространства ключей Cassandra

### Проблема #4: Архитектура управления коллекциями ✅ ВЫПОЛНЕНО
**Предыдущее состояние:** Коллекции хранились в пространстве ключей Cassandra Librarian через отдельную таблицу коллекций
**Предыдущее состояние:** Librarian использовал 4 жестко заданные темы управления хранилищем для координации создания/удаления коллекций:
  `vector_storage_management_topic`
  `object_storage_management_topic`
  `triples_storage_management_topic`
  `storage_management_response_topic`
**Проблемы (решены):**
  Жестко заданные темы не могли быть настроены для многоарендных развертываний
  Сложная асинхронная координация между Librarian и 4+ сервисами хранения
  Отдельная таблица Cassandra и инфраструктура управления
  Непостоянные очереди запросов/ответов для критических операций
**Решение реализовано:** Коллекции были перенесены в хранилище сервиса Config, используется отправка Config для распространения
**Статус:** Все хранилища были перенесены на шаблон `CollectionConfigHandler`

## Решение

Эта спецификация решает проблемы #1, #2, #3 и #4.

### Часть 1: Исправление несоответствий имен параметров

#### Изменение 1: Базовый класс AsyncProcessor - Переименование параметра CLI
**Файл:** `trustgraph-base/trustgraph/base/async_processor.py`
**Строка:** 260-264

**Текущее состояние:**
```python
parser.add_argument(
    '--config-queue',
    default=default_config_queue,
    help=f'Config push queue {default_config_queue}',
)
```

**Исправлено:**
```python
parser.add_argument(
    '--config-push-queue',
    default=default_config_queue,
    help=f'Config push queue (default: {default_config_queue})',
)
```

**Обоснование:**
Более понятное и явное наименование
Соответствует внутреннему имени переменной `config_push_queue`
Изменение, нарушающее обратную совместимость, допустимо, поскольку функция в настоящее время не функционирует
Не требуется изменение кода в params.get() - он уже ищет правильное имя

#### Изменение 2: Сервис конфигурации - Переименование параметра командной строки
**Файл:** `trustgraph-flow/trustgraph/config/service/service.py`
**Строка:** 276-279

**Текущее:**
```python
parser.add_argument(
    '--push-queue',
    default=default_config_push_queue,
    help=f'Config push queue (default: {default_config_push_queue})'
)
```

**Исправлено:**
```python
parser.add_argument(
    '--config-push-queue',
    default=default_config_push_queue,
    help=f'Config push queue (default: {default_config_push_queue})'
)
```

**Обоснование:**
Более понятное наименование - "config-push-queue" более явно, чем просто "push-queue".
Соответствует внутреннему имени переменной `config_push_queue`.
Соответствует параметру `--config-push-queue` класса AsyncProcessor.
Изменение, нарушающее обратную совместимость, допустимо, поскольку функция в настоящее время не работает.
Не требуется изменение кода в params.get() - он уже ищет правильное имя.

### Часть 2: Добавление параметризации пространства ключей Cassandra

#### Изменение 3: Добавление параметра пространства ключей в модуль cassandra_config
**Файл:** `trustgraph-base/trustgraph/base/cassandra_config.py`

**Добавление аргумента командной строки** (в функции `add_cassandra_args()`):
```python
parser.add_argument(
    '--cassandra-keyspace',
    default=None,
    help='Cassandra keyspace (default: service-specific)'
)
```

**Добавить поддержку переменных окружения** (в функции `resolve_cassandra_config()`):
```python
keyspace = params.get(
    "cassandra_keyspace",
    os.environ.get("CASSANDRA_KEYSPACE")
)
```

**Обновить возвращаемое значение** `resolve_cassandra_config()`:
В настоящее время возвращает: `(hosts, username, password)`
Изменить, чтобы возвращалось: `(hosts, username, password, keyspace)`

**Обоснование:**
Соответствует существующей схеме конфигурации Cassandra
Доступно всем сервисам через `add_cassandra_args()`
Поддерживает конфигурацию как через командную строку, так и через переменные окружения

#### Изменение 4: Сервис конфигурации - Использование параметризованных пространств ключей
**Файл:** `trustgraph-flow/trustgraph/config/service/service.py`

**Строка 30** - Удалить жестко закодированное пространство ключей:
```python
# DELETE THIS LINE:
keyspace = "config"
```

**Строки 69-73** - Обновление разрешения конфигурации Cassandra:

**Текущая версия:**
```python
cassandra_host, cassandra_username, cassandra_password = \
    resolve_cassandra_config(params)
```

**Исправлено:**
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="config")
```

**Обоснование:**
Обеспечивает обратную совместимость с "config" в качестве значения по умолчанию.
Позволяет переопределить значение с помощью `--cassandra-keyspace` или `CASSANDRA_KEYSPACE`.

#### Изменение 5: Основные компоненты/Сервис знаний - Использование параметризованных пространств ключей.
**Файл:** `trustgraph-flow/trustgraph/cores/service.py`

**Строка 37** - Удалить жестко закодированное пространство ключей:
```python
# DELETE THIS LINE:
keyspace = "knowledge"
```

**Обновление разрешения конфигурации Cassandra** (в том же месте, что и служба конфигурации):
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="knowledge")
```

#### Изменение 6: Сервис библиотекаря - Использование параметризованных пространств ключей.
**Файл:** `trustgraph-flow/trustgraph/librarian/service.py`

**Строка 51** - Удалить жестко закодированное пространство ключей:
```python
# DELETE THIS LINE:
keyspace = "librarian"
```

**Обновление разрешения конфигурации Cassandra** (в том же месте, что и служба конфигурации):
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="librarian")
```

### Часть 3: Перенос управления коллекциями в службу конфигураций

#### Обзор
Перенесите коллекции из пространства ключей Cassandra librarian в хранилище службы конфигураций. Это устраняет жестко закодированные темы управления хранилищем и упрощает архитектуру, используя существующий механизм распространения конфигураций.

#### Текущая архитектура
```
API Request → Gateway → Librarian Service
                            ↓
                    CollectionManager
                            ↓
                    Cassandra Collections Table (librarian keyspace)
                            ↓
                    Broadcast to 4 Storage Management Topics (hardcoded)
                            ↓
        Wait for 4+ Storage Service Responses
                            ↓
                    Response to Gateway
```

#### Новая архитектура
```
API Request → Gateway → Librarian Service
                            ↓
                    CollectionManager
                            ↓
                    Config Service API (put/delete/getvalues)
                            ↓
                    Cassandra Config Table (class='collections', key='user:collection')
                            ↓
                    Config Push (to all subscribers on config-push-queue)
                            ↓
        All Storage Services receive config update independently
```

#### Изменение 7: Менеджер коллекций - Использование API сервиса конфигурации
**Файл:** `trustgraph-flow/trustgraph/librarian/collection_manager.py`

**Удалить:**
Использование `LibraryTableStore` (строки 33, 40-41)
Инициализация производителей управления хранилищем (строки 86-140)
Метод `on_storage_response` (строки 400-430)
Отслеживание `pending_deletions` (строки 57, 90-96 и использование во всем коде)

**Добавить:**
Клиент сервиса конфигурации для вызовов API (шаблон запрос/ответ)

**Настройка клиента конфигурации:**
```python
# In __init__, add config request/response producers/consumers
from trustgraph.schema.services.config import ConfigRequest, ConfigResponse

# Producer for config requests
self.config_request_producer = Producer(
    client=pulsar_client,
    topic=config_request_queue,
    schema=ConfigRequest,
)

# Consumer for config responses (with correlation ID)
self.config_response_consumer = Consumer(
    taskgroup=taskgroup,
    client=pulsar_client,
    flow=None,
    topic=config_response_queue,
    subscriber=f"{id}-config",
    schema=ConfigResponse,
    handler=self.on_config_response,
)

# Tracking for pending config requests
self.pending_config_requests = {}  # request_id -> asyncio.Event
```

**Изменить `list_collections` (строки 145-180):**
```python
async def list_collections(self, user, tag_filter=None, limit=None):
    """List collections from config service"""
    # Send getvalues request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='getvalues',
        type='collections',
    )

    # Send request and wait for response
    response = await self.send_config_request(request)

    # Parse collections from response
    collections = []
    for key, value_json in response.values.items():
        if ":" in key:
            coll_user, collection = key.split(":", 1)
            if coll_user == user:
                metadata = json.loads(value_json)
                collections.append(CollectionMetadata(**metadata))

    # Apply tag filtering in-memory (as before)
    if tag_filter:
        collections = [c for c in collections if any(tag in c.tags for tag in tag_filter)]

    # Apply limit
    if limit:
        collections = collections[:limit]

    return collections

async def send_config_request(self, request):
    """Send config request and wait for response"""
    event = asyncio.Event()
    self.pending_config_requests[request.id] = event

    await self.config_request_producer.send(request)
    await event.wait()

    return self.pending_config_requests.pop(request.id + "_response")

async def on_config_response(self, message, consumer, flow):
    """Handle config response"""
    response = message.value()
    if response.id in self.pending_config_requests:
        self.pending_config_requests[response.id + "_response"] = response
        self.pending_config_requests[response.id].set()
```

**Изменить `update_collection` (строки 182-312):**
```python
async def update_collection(self, user, collection, name, description, tags):
    """Update collection via config service"""
    # Create metadata
    metadata = CollectionMetadata(
        user=user,
        collection=collection,
        name=name,
        description=description,
        tags=tags,
    )

    # Send put request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='put',
        type='collections',
        key=f'{user}:{collection}',
        value=json.dumps(metadata.to_dict()),
    )

    response = await self.send_config_request(request)

    if response.error:
        raise RuntimeError(f"Config update failed: {response.error.message}")

    # Config service will trigger config push automatically
    # Storage services will receive update and create collections
```

**Изменить `delete_collection` (строки 314-398):**
```python
async def delete_collection(self, user, collection):
    """Delete collection via config service"""
    # Send delete request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='delete',
        type='collections',
        key=f'{user}:{collection}',
    )

    response = await self.send_config_request(request)

    if response.error:
        raise RuntimeError(f"Config delete failed: {response.error.message}")

    # Config service will trigger config push automatically
    # Storage services will receive update and delete collections
```

**Формат метаданных коллекции:**
Хранится в таблице конфигурации как: `class='collections', key='user:collection'`
Значение является JSON-сериализованным объектом CollectionMetadata (без полей времени).
Поля: `user`, `collection`, `name`, `description`, `tags`
Пример: `class='collections', key='alice:my-docs', value='{"user":"alice","collection":"my-docs","name":"My Documents","description":"...","tags":["work"]}'`

#### Изменение 8: Сервис Librarian - Удаление инфраструктуры управления хранилищем
**Файл:** `trustgraph-flow/trustgraph/librarian/service.py`

**Удалить:**
Модули-производители управления хранилищем (строки 173-190):
  `vector_storage_management_producer`
  `object_storage_management_producer`
  `triples_storage_management_producer`
Потребитель ответов хранилища (строки 192-201)
Обработчик `on_storage_response` (строки 467-473)

**Изменить:**
Инициализация CollectionManager (строки 215-224) - удалить параметры модуля-производителя хранилища

**Примечание:** Внешний API для коллекций остается неизменным:
`list-collections`
`update-collection`
`delete-collection`

#### Изменение 9: Удаление таблицы Collections из LibraryTableStore
**Файл:** `trustgraph-flow/trustgraph/tables/library.py`

**Удалить:**
Оператор CREATE для таблицы Collections (строки 114-127)
Подготовленные операторы для Collections (строки 205-240)
Все методы для работы с коллекциями (строки 578-717):
  `ensure_collection_exists`
  `list_collections`
  `update_collection`
  `delete_collection`
  `get_collection`
  `create_collection`

**Обоснование:**
Коллекции теперь хранятся в таблице конфигурации.
Изменение, требующее обновления, приемлемо - миграция данных не требуется.
Значительно упрощает сервис Librarian.

#### Изменение 10: Сервисы хранения - Управление коллекциями на основе конфигурации ✅ ВЫПОЛНЕНО

**Статус:** Все 11 хранилищ были перенесены на использование `CollectionConfigHandler`.

**Затронутые сервисы (всего 11):**
Векторные представления документов: milvus, pinecone, qdrant
Векторные представления графов: milvus, pinecone, qdrant
Объектное хранилище: cassandra
Хранилище троек: cassandra, falkordb, memgraph, neo4j

**Файлы:**
`trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/pinecone/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/triples/falkordb/write.py`
`trustgraph-flow/trustgraph/storage/triples/memgraph/write.py`
`trustgraph-flow/trustgraph/storage/triples/neo4j/write.py`

**Шаблон реализации (для всех сервисов):**

1. **Зарегистрировать обработчик конфигурации в `__init__`:**
```python
# Add after AsyncProcessor initialization
self.register_config_handler(self.on_collection_config)
self.known_collections = set()  # Track (user, collection) tuples
```

2. **Реализовать обработчик конфигурации:**
```python
async def on_collection_config(self, config, version):
    """Handle collection configuration updates"""
    logger.info(f"Collection config version: {version}")

    if "collections" not in config:
        return

    # Parse collections from config
    # Key format: "user:collection" in config["collections"]
    config_collections = set()
    for key in config["collections"].keys():
        if ":" in key:
            user, collection = key.split(":", 1)
            config_collections.add((user, collection))

    # Determine changes
    to_create = config_collections - self.known_collections
    to_delete = self.known_collections - config_collections

    # Create new collections (idempotent)
    for user, collection in to_create:
        try:
            await self.create_collection_internal(user, collection)
            self.known_collections.add((user, collection))
            logger.info(f"Created collection: {user}/{collection}")
        except Exception as e:
            logger.error(f"Failed to create {user}/{collection}: {e}")

    # Delete removed collections (idempotent)
    for user, collection in to_delete:
        try:
            await self.delete_collection_internal(user, collection)
            self.known_collections.discard((user, collection))
            logger.info(f"Deleted collection: {user}/{collection}")
        except Exception as e:
            logger.error(f"Failed to delete {user}/{collection}: {e}")
```

3. **Инициализация известных коллекций при запуске:**
```python
async def start(self):
    """Start the processor"""
    await super().start()
    await self.sync_known_collections()

async def sync_known_collections(self):
    """Query backend to populate known_collections set"""
    # Backend-specific implementation:
    # - Milvus/Pinecone/Qdrant: List collections/indexes matching naming pattern
    # - Cassandra: Query keyspaces or collection metadata
    # - Neo4j/Memgraph/FalkorDB: Query CollectionMetadata nodes
    pass
```

4. **Рефакторинг существующих методов обработчиков:**
```python
# Rename and remove response sending:
# handle_create_collection → create_collection_internal
# handle_delete_collection → delete_collection_internal

async def create_collection_internal(self, user, collection):
    """Create collection (idempotent)"""
    # Same logic as current handle_create_collection
    # But remove response producer calls
    # Handle "already exists" gracefully
    pass

async def delete_collection_internal(self, user, collection):
    """Delete collection (idempotent)"""
    # Same logic as current handle_delete_collection
    # But remove response producer calls
    # Handle "not found" gracefully
    pass
```

5. **Удаление инфраструктуры управления хранилищем:**
   Удалить настройку и запуск `self.storage_request_consumer`
   Удалить настройку `self.storage_response_producer`
   Удалить метод диспетчера `on_storage_management`
   Удалить метрики для управления хранилищем
   Удалить импорты: `StorageManagementRequest`, `StorageManagementResponse`

**Особенности, специфичные для бэкенда:**

**Векторные хранилища (Milvus, Pinecone, Qdrant):** Отслеживать логическую `(user, collection)` в `known_collections`, но может создавать несколько бэкенд-коллекций для каждой размерности. Продолжить использование ленивой схемы создания. Операции удаления должны удалять все варианты размерностей.

**Объекты Cassandra:** Коллекции являются свойствами строк, а не структурами. Отслеживать информацию на уровне пространства ключей.

**Графовые хранилища (Neo4j, Memgraph, FalkorDB):** Запрашивать узлы `CollectionMetadata` при запуске. Создавать/удалять метаданные узлов при синхронизации.

**Тройки Cassandra:** Использовать API `KnowledgeGraph` для операций с коллекциями.

**Основные принципы проектирования:**

**Итоговая согласованность:** Отсутствует механизм запрос/ответ, конфигурация распространяется широковещанием.
**Идемпотентность:** Все операции создания/удаления должны быть безопасными для повторной попытки.
**Обработка ошибок:** Регистрировать ошибки, но не блокировать обновления конфигурации.
**Самовосстановление:** Неудачные операции будут повторены при следующем распространении конфигурации.
**Формат ключа коллекции:** `"user:collection"` в `config["collections"]`

#### Изменение 11: Обновление схемы коллекции - Удаление временных меток
**Файл:** `trustgraph-base/trustgraph/schema/services/collection.py`

**Изменить CollectionMetadata (строки 13-21):**
Удалить поля `created_at` и `updated_at`:
```python
class CollectionMetadata(Record):
    user = String()
    collection = String()
    name = String()
    description = String()
    tags = Array(String())
    # Remove: created_at = String()
    # Remove: updated_at = String()
```

**Изменить класс CollectionManagementRequest (строки 25-47):**
Удалить поля временной метки:
```python
class CollectionManagementRequest(Record):
    operation = String()
    user = String()
    collection = String()
    timestamp = String()
    name = String()
    description = String()
    tags = Array(String())
    # Remove: created_at = String()
    # Remove: updated_at = String()
    tag_filter = Array(String())
    limit = Integer()
```

**Обоснование:**
Временные метки не добавляют ценности для коллекций.
Сервис конфигурации самостоятельно отслеживает версии.
Упрощает схему и уменьшает объем хранения.

#### Преимущества миграции на сервис конфигурации

1. ✅ **Устраняет жестко закодированные темы управления хранилищем** - Решает проблему многопользовательской среды.
2. ✅ **Более простая координация** - Нет сложного асинхронного ожидания ответов от 4+ хранилищ.
3. ✅ **В конечном итоге согласованность** - Сервисы хранения обновляются независимо с помощью push-конфигурации.
4. ✅ **Более высокая надежность** - Постоянная push-конфигурация против неперсистентного запроса/ответа.
5. ✅ **Унифицированная модель конфигурации** - Коллекции рассматриваются как конфигурация.
6. ✅ **Уменьшает сложность** - Удаляет около 300 строк кода для координации.
7. ✅ **Готовность к многопользовательской среде** - Конфигурация уже поддерживает изоляцию пользователей с помощью пространств ключей.
8. ✅ **Отслеживание версий** - Механизм версионирования сервиса конфигурации обеспечивает аудит.

## Замечания по реализации

### Обратная совместимость

**Изменения параметров:**
Переименование параметров командной строки является серьезным изменением, но допустимо (функция в настоящее время не работает).
Сервисы работают без параметров (используются значения по умолчанию).
Значения по умолчанию для пространств ключей сохранены: "config", "knowledge", "librarian".
Значение по умолчанию для очереди: `persistent://tg/config/config`

**Управление коллекциями:**
**Серьезное изменение:** Таблица коллекций удалена из пространства ключей librarian.
**Миграция данных не предусмотрена** - приемлемо для этой фазы.
Внешний API для коллекций не изменен (операции list/update/delete).
Формат метаданных коллекций упрощен (временные метки удалены).

### Требования к тестированию

**Тестирование параметров:**
1. Проверить, работает ли параметр `--config-push-queue` для сервиса graph-embeddings.
2. Проверить, работает ли параметр `--config-push-queue` для сервиса text-completion.
3. Проверить, работает ли параметр `--config-push-queue` для сервиса конфигурации.
4. Проверить, работает ли параметр `--cassandra-keyspace` для сервиса конфигурации.
5. Проверить, работает ли параметр `--cassandra-keyspace` для сервиса cores.
6. Проверить, работает ли параметр `--cassandra-keyspace` для сервиса librarian.
7. Проверить, работают ли сервисы без параметров (используются значения по умолчанию).
8. Проверить развертывание в многопользовательской среде с использованием пользовательских имен очередей и пространств ключей.

**Тестирование управления коллекциями:**
9. Проверить операцию `list-collections` через сервис конфигурации.
10. Проверить, создает ли `update-collection` записи/обновления в таблице конфигурации.
11. Проверить, удаляет ли `delete-collection` записи из таблицы конфигурации.
12. Проверить, запускается ли push-конфигурации при обновлениях коллекций.
13. Проверить, работает ли фильтрация по тегам с использованием хранилища на основе конфигурации.
14. Проверить, работают ли операции с коллекциями без полей временных меток.

### Пример развертывания в многопользовательской среде
```bash
# Tenant: tg-dev
graph-embeddings \
  -p pulsar+ssl://broker:6651 \
  --pulsar-api-key <KEY> \
  --config-push-queue persistent://tg-dev/config/config

config-service \
  -p pulsar+ssl://broker:6651 \
  --pulsar-api-key <KEY> \
  --config-push-queue persistent://tg-dev/config/config \
  --cassandra-keyspace tg_dev_config
```

## Анализ влияния

### Сервисы, затронутые изменением 1-2 (Переименование параметра CLI)
Все сервисы, наследующие AsyncProcessor или FlowProcessor:
config-service
cores-service
librarian-service
graph-embeddings
document-embeddings
text-completion-* (все провайдеры)
extract-* (все экстракторы)
query-* (все сервисы запросов)
retrieval-* (все сервисы RAG)
storage-* (все сервисы хранения)
И еще 20+ сервисов

### Сервисы, затронутые изменениями 3-6 (Keyspace Cassandra)
config-service
cores-service
librarian-service

### Сервисы, затронутые изменениями 7-11 (Управление коллекциями)

**Немедленные изменения:**
librarian-service (collection_manager.py, service.py)
tables/library.py (удаление таблицы collections)
schema/services/collection.py (удаление метки времени)

**Выполненные изменения (изменение 10):** ✅
Все сервисы хранения (всего 11) - перенесены на push-конфигурацию для обновлений коллекций через `CollectionConfigHandler`
Схема управления хранилищем удалена из `storage.py`

## Будущие соображения

### Модель keyspace на уровне пользователя

Некоторые сервисы динамически используют **keyspace на уровне пользователя**, когда каждый пользователь получает свой собственный keyspace Cassandra:

**Сервисы с keyspace на уровне пользователя:**
1. **Сервис запросов Triple** (`trustgraph-flow/trustgraph/query/triples/cassandra/service.py:65`)
   Использует `keyspace=query.user`
2. **Сервис запросов объектов** (`trustgraph-flow/trustgraph/query/objects/cassandra/service.py:479`)
   Использует `keyspace=self.sanitize_name(user)`
3. **Прямой доступ к графу знаний** (`trustgraph-flow/trustgraph/direct/cassandra_kg.py:18`)
   Параметр по умолчанию `keyspace="trustgraph"`

**Статус:** Эти параметры **не изменяются** в этой спецификации.

**Требуется дальнейший анализ:**
Оценить, создает ли модель keyspace на уровне пользователя проблемы изоляции арендаторов
Рассмотреть, нужны ли многопользовательским развертываниям префиксы keyspace (например, `tenant_a_user1`)
Проверить на потенциальные конфликты идентификаторов пользователей между арендаторами
Оценить, является ли единый общий keyspace на арендатора с изоляцией строк на уровне пользователя более предпочтительным

**Примечание:** Это не блокирует текущую многопользовательскую реализацию, но должно быть рассмотрено перед производственными многопользовательскими развертываниями.

## Этапы реализации

### Этап 1: Исправление параметров (изменения 1-6)
Исправить именование параметра `--config-push-queue`
Добавить поддержку параметра `--cassandra-keyspace`
**Результат:** Многопользовательская очередь и конфигурация keyspace включены

### Этап 2: Миграция управления коллекциями (изменения 7-9, 11)
Перенести хранение коллекций в сервис конфигурации
Удалить таблицу collections из librarian
Обновить схему коллекций (удалить метки времени)
**Результат:** Устраняет жестко закодированные темы управления хранилищем, упрощает librarian

### Этап 3: Обновления сервисов хранения (изменение 10) ✅ ВЫПОЛНЕНО
Обновлены все сервисы хранения для использования push-конфигурации для коллекций через `CollectionConfigHandler`
Удалена инфраструктура запросов/ответов управления хранилищем
Удалены устаревшие определения схемы
**Результат:** Достигнуто полное управление коллекциями на основе конфигурации

## Ссылки
GitHub Issue: https://github.com/trustgraph-ai/trustgraph/issues/582
Связанные файлы:
  `trustgraph-base/trustgraph/base/async_processor.py`
  `trustgraph-base/trustgraph/base/cassandra_config.py`
  `trustgraph-base/trustgraph/schema/core/topic.py`
  `trustgraph-base/trustgraph/schema/services/collection.py`
  `trustgraph-flow/trustgraph/config/service/service.py`
  `trustgraph-flow/trustgraph/cores/service.py`
  `trustgraph-flow/trustgraph/librarian/service.py`
  `trustgraph-flow/trustgraph/librarian/collection_manager.py`
  `trustgraph-flow/trustgraph/tables/library.py`
