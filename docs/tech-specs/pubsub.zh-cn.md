# Pub/Sub 基础设施

## 概述

本文档记录了 TrustGraph 代码库与 pub/sub 基础设施之间的所有连接。目前，系统是硬编码为使用 Apache Pulsar。此分析识别了所有集成点，以促进未来向可配置的 pub/sub 抽象的重构。

## 当前状态：Pulsar 集成点

### 1. 直接 Pulsar 客户端使用

**位置：** `trustgraph-flow/trustgraph/gateway/service.py`

API 网关直接导入和实例化 Pulsar 客户端：

**第 20 行：** `import pulsar`
**第 54-61 行：** 直接实例化 `pulsar.Client()`，带可选 `pulsar.AuthenticationToken()`
**第 33-35 行：** 从环境变量获取默认 Pulsar 主机配置
**第 178-192 行：** CLI 参数，用于 `--pulsar-host`、`--pulsar-api-key` 和 `--pulsar-listener`
**第 78、124 行：** 将 `pulsar_client` 传递给 `ConfigReceiver` 和 `DispatcherManager`

这是唯一直接在抽象层之外实例化 Pulsar 客户端的位置。

### 2. 基础处理器框架

**位置：** `trustgraph-base/trustgraph/base/async_processor.py`

所有处理器的基本类提供 Pulsar 连接：

**第 9 行：** `import _pulsar` (用于异常处理)
**第 18 行：** `from . pubsub import PulsarClient`
**第 38 行：** 创建 `pulsar_client_object = PulsarClient(**params)`
**第 104-108 行：** 暴露 `pulsar_host` 和 `pulsar_client` 的属性
**第 250 行：** 静态方法 `add_args()` 调用 `PulsarClient.add_args(parser)` 以获取 CLI 参数
**第 223-225 行：** `_pulsar.Interrupted` 的异常处理

所有处理器都继承自 `AsyncProcessor`，使其成为主要的集成点。

### 3. 消费者抽象

**位置：** `trustgraph-base/trustgraph/base/consumer.py`

从队列中消耗消息并调用处理函数：

**Pulsar 导入：**
**第 12 行：** `from pulsar.schema import JsonSchema`
**第 13 行：** `import pulsar`
**第 14 行：** `import _pulsar`

**Pulsar 特定的用法：**
**第 100、102 行：** `pulsar.InitialPosition.Earliest` / `pulsar.InitialPosition.Latest`
**第 108 行：** `JsonSchema(self.schema)` 包装器
**第 110 行：** `pulsar.ConsumerType.Shared`
**第 104-111 行：** `self.client.subscribe()`，带有 Pulsar 特定的参数
**第 143、150、65 行：** `consumer.unsubscribe()` 和 `consumer.close()` 方法
**第 162 行：** `_pulsar.Timeout` 异常
**第 182、205、232 行：** `consumer.acknowledge()` / `consumer.negative_acknowledge()`

**Spec 文件：** `trustgraph-base/trustgraph/base/consumer_spec.py`
**第 22 行：** 引用 `processor.pulsar_client`

### 4. 生产者抽象

**位置：** `trustgraph-base/trustgraph/base/producer.py`

向队列发送消息：

**Pulsar 导入：**
**第 2 行：** `from pulsar.schema import JsonSchema`

**Pulsar 特定的用法：**
**第 49 行：** `JsonSchema(self.schema)` 包装器
**第 47-51 行：** `self.client.create_producer()`，带有 Pulsar 特定的参数 (topic, schema, chunking_enabled)
**第 31、76 行：** `producer.close()` 方法
**第 64-65 行：** `producer.send()`，带有消息和属性

**Spec 文件：** `trustgraph-base/trustgraph/base/producer_spec.py`
**第 18 行：** 引用 `processor.pulsar_client`

### 5. 发布者抽象

**位置：** `trustgraph-base/trustgraph/base/publisher.py`

具有队列缓冲的异步消息发布：

**Pulsar 导入：**
**第 2 行：** `from pulsar.schema import JsonSchema`
**第 6 行：** `import pulsar`

**Pulsar 特定的用法：**
**第 52 行：** `JsonSchema(self.schema)` 包装器
**第 50-54 行：** `self.client.create_producer()`，带有 Pulsar 特定的参数
**第 101、103 行：** `producer.send()`，带有消息和可选属性
**第 106-107 行：** `producer.flush()` 和 `producer.close()` 方法

### 6. 订阅者抽象

**位置：** `trustgraph-base/trustgraph/base/subscriber.py`

提供从队列分发给多个接收者的消息功能：

**Pulsar 导入：**
**第 6 行：** `from pulsar.schema import JsonSchema`
**第 8 行：** `import _pulsar`

**Pulsar 特定的用法：**
**第 55 行：** `JsonSchema(self.schema)` 包装器
**第 57 行：** `self.client.subscribe(**subscribe_args)`
**第 101、136、160、167-172 行：** Pulsar 异常：`_pulsar.Timeout`, `_pulsar.InvalidConfiguration`, `_pulsar.AlreadyClosed`
**第 159、166、170 行：** 消费者方法：`negative_acknowledge()`, `unsubscribe()`, `close()`
**第 247、251 行：** 消息确认：`acknowledge()`, `negative_acknowledge()`

**Spec 文件：** `trustgraph-base/trustgraph/base/subscriber_spec.py`
**第 19 行：** 引用 `processor.pulsar_client`

### 7. Schema 系统 (黑暗之心)

**位置：** `trustgraph-base/trustgraph/schema/`

系统中的每个消息模式都使用 Pulsar 的模式框架定义。

**核心原语：** `schema/core/primitives.py`
**第 2 行：** `from pulsar.schema import Record, String, Boolean, Array, Integer`
所有模式都继承自 Pulsar 的 `Record` 基类
所有字段类型都是 Pulsar 类型：`String()`, `Integer()`, `Boolean()`, `Array()`, `Map()`, `Double()`

**示例模式：**
`schema/services/llm.py` (第 2 行)：`from pulsar.schema import Record, String, Array, Double, Integer, Boolean`
`schema/services/config.py` (第 2 行)：`from pulsar.schema import Record, Bytes, String, Boolean, Array, Map, Integer`

**主题命名：** `schema/core/topic.py`
**第 2-3 行：** 主题格式：`{kind}://{tenant}/{namespace}/{topic}`
此 URI 结构是 Pulsar 特定的（例如，`persistent://tg/flow/config`）

**影响：**
代码库中所有请求/响应消息定义都使用 Pulsar 模式
这包括用于：config、flow、llm、prompt、query、storage、agent、collection、diagnosis、library、lookup、nlp_query、objects_query、retrieval、structured_query 的服务
模式定义被导入并广泛地用于所有处理器和服务中

## 总结

### Pulsar 依赖项按类别划分

1. **客户端实例化：**
   直接：`gateway/service.py`
   抽象：`async_processor.py` → `pubsub.py` (PulsarClient)

2. **消息传输：**
   消费者：`consumer.py`, `consumer_spec.py`
   生产者：`producer.py`, `producer_spec.py`
   发布者：`publisher.py`
   订阅者：`subscriber.py`, `subscriber_spec.py`

3. **模式系统：**
   基本类型：`schema/core/primitives.py`
   所有服务模式：`schema/services/*.py`
   主题命名：`schema/core/topic.py`

4. **需要 Pulsar 特定的概念：**
   基于主题的消息
   模式系统 (Record, 字段类型)
   共享订阅
   消息确认 (肯定/否定)
   消费者定位 (最早/最新)
   消息属性
   初始位置和消费者类型
   分块支持
   持久化与非持久化主题

### 重构挑战

好的消息：抽象层 (Consumer, Producer, Publisher, Subscriber) 提供了一个干净的 Pulsar 交互的封装。

挑战：
1. **模式系统的普遍性：** 每个消息定义都使用 `pulsar.schema.Record` 和 Pulsar 字段类型
2. **Pulsar 特定的枚举：** `InitialPosition`, `ConsumerType`
3. **Pulsar 异常：** `_pulsar.Timeout`, `_pulsar.Interrupted`, `_pulsar.InvalidConfiguration`, `_pulsar.AlreadyClosed`
4. **方法签名：** `acknowledge()`, `negative_acknowledge()`, `subscribe()`, `create_producer()`, 等等。
5. **主题 URI 格式：** Pulsar 的 `kind://tenant/namespace/topic` 结构

### 下一步

为了使 pub/sub 基础设施可配置，我们需要：

1. 为客户端/模式系统创建抽象接口
2. 抽象 Pulsar 特定的枚举和异常
3. 创建模式包装器或替代模式定义
4. 为 Pulsar 和其他系统（Kafka、RabbitMQ、Redis Streams 等）实现该接口
5. 更新 `pubsub.py` 以使其可配置并支持多个后端
6. 提供现有部署的迁移路径

## 方法草案 1：带模式转换层的适配器模式

### 关键洞察
**模式系统** 是最深入的集成点 - 其他一切都由此而产生。 我们需要首先解决这个问题，否则我们将重写整个代码库。

### 策略：通过适配器实现最小的干扰

**1. 保持 Pulsar 模式作为内部表示**
不要重写所有的模式定义
模式在内部仍然是 `pulsar.schema.Record`
使用适配器在我们的代码和发布/订阅后端之间的边界进行转换

**2. 创建一个发布/订阅抽象层：**

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

**3. 定义抽象接口:**
`PubSubClient` - 客户端连接
`PubSubProducer` - 发送消息
`PubSubConsumer` - 接收消息
`SchemaAdapter` - 将 Pulsar 模式转换为 JSON 或后端特定的格式，反之亦然

**4. 实现细节:**

对于 **Pulsar 适配器**: 几乎是直通模式，最小化转换

对于 **其他后端** (Kafka, RabbitMQ 等):
将 Pulsar Record 对象序列化为 JSON/字节
映射概念，例如：
  `InitialPosition.Earliest/Latest` → Kafka 的 auto.offset.reset
  `acknowledge()` → Kafka 的 commit
  `negative_acknowledge()` → 重试或 DLQ 模式
  Topic URI → 后端特定的主题名称

### 分析

**优点:**
✅ 对现有服务的代码更改最小
✅ 模式保持不变 (无需大规模重写)
✅ 逐步迁移路径
✅ Pulsar 用户不会看到任何差异
✅ 通过适配器添加新的后端

**缺点:**
⚠️ 仍然依赖 Pulsar (用于模式定义)
⚠️ 在转换概念时存在一些阻抗不匹配

### 替代方案

创建一个 **TrustGraph 模式系统**，该系统与 pub/sub 无关 (使用 dataclasses 或 Pydantic)，然后从该系统生成 Pulsar/Kafka/等的模式。 这需要重写每个模式文件，并且可能导致不兼容的更改。

### 草案 1 的建议

从 **适配器方法** 开始，因为：
1. 它实用 - 与现有代码兼容
2. 以最小的风险验证概念
3. 如果需要，可以演变为原生模式系统
4. 基于配置：一个环境变量切换后端

## 草案 2 方法：具有 Dataclasses 的后端无关模式系统

### 核心概念

使用 Python **dataclasses** 作为中立的模式定义格式。 每个 pub/sub 后端都提供自己的序列化/反序列化，以处理 dataclasses，从而无需在代码库中保留 Pulsar 模式。

### 工厂级别的模式多态

而是翻译 Pulsar 模式，**每个后端都提供自己的模式处理**，该处理方式适用于标准的 Python dataclasses。

### 发布者流程

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

### 消费者流程

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

### 幕后发生了什么

**对于 Pulsar 后端：**
`create_producer()` → 创建具有 JSON 模式或动态生成的记录的 Pulsar 生产者。
`send(request)` → 将数据类序列化为 JSON/Pulsar 格式，并发送到 Pulsar。
`receive()` → 获取 Pulsar 消息，将其反序列化回数据类。

**对于 MQTT 后端：**
`create_producer()` → 连接到 MQTT 代理，无需注册模式。
`send(request)` → 将数据类转换为 JSON，并发布到 MQTT 主题。
`receive()` → 订阅 MQTT 主题，并将 JSON 反序列化为数据类。

**对于 Kafka 后端：**
`create_producer()` → 创建 Kafka 生产者，如果需要，注册 Avro 模式。
`send(request)` → 将数据类序列化为 Avro 格式，并发送到 Kafka。
`receive()` → 获取 Kafka 消息，并将 Avro 反序列化回数据类。

### 关键设计点

1. **模式对象创建：** 数据类实例 (`TextCompletionRequest(...)`) 无论后端如何都是相同的。
2. **后端处理编码：** 每个后端都知道如何将数据类序列化为线格式。
3. **在创建时定义模式：** 在创建生产者/消费者时，您指定模式类型。
4. **保留类型安全：** 您会得到一个正确的 `TextCompletionRequest` 对象，而不是一个字典。
5. **没有后端泄漏：** 应用程序代码永远不会导入特定于后端的库。

### 示例转换

**当前（特定于 Pulsar）：**
```python
# schema/services/llm.py
from pulsar.schema import Record, String, Boolean, Integer

class TextCompletionRequest(Record):
    system = String()
    prompt = String()
    streaming = Boolean()
```

**新功能（与后端无关）：**
```python
# schema/services/llm.py
from dataclasses import dataclass

@dataclass
class TextCompletionRequest:
    system: str
    prompt: str
    streaming: bool = False
```

### 后端集成

每个后端负责数据类的序列化/反序列化：

**Pulsar 后端：**
从数据类动态生成 `pulsar.schema.Record` 类
或者将数据类序列化为 JSON，并使用 Pulsar 的 JSON 模式
保持与现有 Pulsar 部署的兼容性

**MQTT/Redis 后端：**
直接对数据类实例进行 JSON 序列化
使用 `dataclasses.asdict()` / `from_dict()`
轻量级，无需模式注册表

**Kafka 后端：**
从数据类定义生成 Avro 模式
使用 Confluent 的模式注册表
具有模式演进支持的类型安全序列化

### 架构

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

### 实现细节

**1. 模式定义：** 使用带有类型提示的简单数据类
   `str`, `int`, `bool`, `float` 用于基本类型
   `list[T]` 用于数组
   `dict[str, T]` 用于映射
   用于复杂类型的嵌套数据类

**2. 每个后端提供：**
   序列化器：`dataclass → bytes/wire format`
   反序列化器：`bytes/wire format → dataclass`
   模式注册（如果需要，例如 Pulsar/Kafka）

**3. 消费者/生产者抽象：**
   已经存在 (consumer.py, producer.py)
   更新以使用后端的序列化
   移除直接的 Pulsar 导入

**4. 类型映射：**
   Pulsar `String()` → Python `str`
   Pulsar `Integer()` → Python `int`
   Pulsar `Boolean()` → Python `bool`
   Pulsar `Array(T)` → Python `list[T]`
   Pulsar `Map(K, V)` → Python `dict[K, V]`
   Pulsar `Double()` → Python `float`
   Pulsar `Bytes()` → Python `bytes`

### 迁移路径

1. **创建所有模式的数据类版本**，位于 `trustgraph/schema/`
2. **更新后端类**（Consumer, Producer, Publisher, Subscriber），以使用后端提供的序列化
3. **实现 PulsarBackend**，使用 JSON 模式或动态 Record 生成
4. **使用 Pulsar 进行测试**，以确保与现有部署的向后兼容性
5. **添加新的后端**（MQTT, Kafka, Redis 等），如果需要
6. **从模式文件中移除 Pulsar 导入**

### 优点

✅ **模式定义中没有 pub/sub 依赖**
✅ **标准 Python** - 易于理解、类型检查和记录
✅ **现代工具** - 与 mypy、IDE 自动完成、linter 兼容
✅ **后端优化** - 每个后端使用本机序列化
✅ **没有翻译开销** - 直接序列化，没有适配器
✅ **类型安全** - 具有正确类型的真实对象
✅ **易于验证** - 如果需要，可以使用 Pydantic

### 挑战与解决方案

**挑战：** Pulsar 的 `Record` 具有运行时字段验证
**解决方案：** 如果需要，可以使用 Pydantic 数据类进行验证，或者使用 Python 3.10+ 数据类功能，并结合 `__post_init__`

**挑战：** 一些 Pulsar 特定的功能（例如 `Bytes` 类型）
**解决方案：** 将其映射到数据类中的 `bytes` 类型，后端负责适当的编码

**挑战：** 主题命名（`persistent://tenant/namespace/topic`）
**解决方案：** 在模式定义中抽象主题名称，后端将其转换为正确的格式

**挑战：** 模式演化和版本控制
**解决方案：** 每个后端根据其功能处理此问题（Pulsar 模式版本、Kafka 模式注册等）

**挑战：** 嵌套的复杂类型
**解决方案：** 使用嵌套的数据类，后端递归地序列化/反序列化

### 设计决策

1. **使用纯数据类还是 Pydantic？**
   ✅ **决策：使用纯 Python 数据类**
   更简单，没有额外的依赖
   实际上不需要验证
   更容易理解和维护

2. **模式演化：**
   ✅ **决策：不需要版本机制**
   模式是稳定且持久的
   更新通常会添加新字段（向后兼容）
   后端根据其功能处理模式演化

3. **向后兼容性：**
   ✅ **决策：进行主要版本更改，不需要向后兼容**
   这将是一个破坏性更改，并提供迁移说明
   清理的断开允许更好的设计
   将为现有部署提供迁移指南

4. **嵌套类型和复杂结构：**
   ✅ **决策：自然地使用嵌套的数据类**
   Python 数据类完美地处理嵌套
   `list[T]` 用于数组，`dict[K, V]` 用于映射
   后端递归地序列化/反序列化
   示例：
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

5. **默认值和可选字段：**
   ✅ **决策：强制、默认和可选字段的组合**
   强制字段：没有默认值
   具有默认值的字段：始终存在，具有合理的默认值
   真正可选的字段：`T | None = None`，当`None`时，从序列化中省略
   示例：
     ```python
     @dataclass
     class TextCompletionRequest:
         system: str              # Required, no default
         prompt: str              # Required, no default
         streaming: bool = False  # Optional with default value
         metadata: dict | None = None  # Truly optional, can be absent
     ```

   **重要的序列化语义：**

   当 `metadata = None`:
   ```json
   {
       "system": "...",
       "prompt": "...",
       "streaming": false
       // metadata field NOT PRESENT
   }
   ```

   当 `metadata = {}` (显式为空):
   ```json
   {
       "system": "...",
       "prompt": "...",
       "streaming": false,
       "metadata": {}  // Field PRESENT but empty
   }
   ```

   **关键区别：**
   `None` → JSON 中不存在的字段（未序列化）
   空值（`{}`, `[]`, `""`）→ 字段存在，但值为空
   这在语义上很重要：“未提供”与“显式为空”
   序列化后端必须跳过 `None` 字段，而不是将其编码为 `null`

## 方案草案 3：实现细节

### 通用队列命名格式

将后端特定的队列名称替换为一种通用格式，以便后端可以进行适当的映射。

**格式：** `{qos}/{tenant}/{namespace}/{queue-name}`

其中：
`qos`：服务质量级别
  `q0` = 尽力而为（发送并忘记，无需确认）
  `q1` = 至少一次（需要确认）
  `q2` = 恰好一次（两阶段确认）
`tenant`：多租户逻辑分组
`namespace`：租户内的子分组
`queue-name`：实际的队列/主题名称

**示例：**
```
q1/tg/flow/text-completion-requests
q2/tg/config/config-push
q0/tg/metrics/stats
```

### 后端主题映射

每个后端将通用格式映射到其原生格式：

**Pulsar 后端：**
```python
def map_topic(self, generic_topic: str) -> str:
    # Parse: q1/tg/flow/text-completion-requests
    qos, tenant, namespace, queue = generic_topic.split('/', 3)

    # Map QoS to persistence
    persistence = 'persistent' if qos in ['q1', 'q2'] else 'non-persistent'

    # Return Pulsar URI: persistent://tg/flow/text-completion-requests
    return f"{persistence}://{tenant}/{namespace}/{queue}"
```

**MQTT 后端：**
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

### 更新后的主题辅助函数

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

### 配置和初始化

**命令行参数 + 环境变量：**

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

**工厂函数：**

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

**在 AsyncProcessor 中的用法：**

```python
# In async_processor.py
class AsyncProcessor:
    def __init__(self, **params):
        self.id = params.get("id")

        # Create backend from config (replaces PulsarClient)
        self.pubsub = get_pubsub(**params)

        # Rest of initialization...
```

### 后端接口

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

### 现有类的重构

现有的 `Consumer`、`Producer`、`Publisher`、`Subscriber` 类在很大程度上保持不变：

**当前职责（保留）：**
异步线程模型和任务组
重连逻辑和重试处理
指标收集
速率限制
并发管理

**需要更改的内容：**
移除直接的 Pulsar 导入（`pulsar.schema`、`pulsar.InitialPosition` 等）
接受 `BackendProducer`/`BackendConsumer` 而不是 Pulsar 客户端
将实际的发布/订阅操作委托给后端实例
将通用概念映射到后端调用

**重构示例：**

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

### 后端特定行为

**Pulsar 后端：**
将 `q0` 映射到 `non-persistent://`，将 `q1`/`q2` 映射到 `persistent://`
支持所有类型的消费者（共享、独占、故障转移）
支持初始位置（最早/最新）
原生消息确认
模式注册支持

**MQTT 后端：**
将 `q0`/`q1`/`q2` 映射到 MQTT QoS 等级 0/1/2
在主题路径中包含租户/命名空间，以进行命名空间划分
根据订阅名称自动生成客户端 ID
忽略初始位置（基本的 MQTT 中没有消息历史）
忽略消费者类型（MQTT 使用客户端 ID，而不是消费者组）
简单的发布/订阅模型

### 设计决策摘要

1. ✅ **通用队列命名：** `qos/tenant/namespace/queue-name` 格式
2. ✅ **队列 ID 中的 QoS：** 由队列定义确定，而不是配置
3. ✅ **重连：** 由 Consumer/Producer 类处理，而不是后端
4. ✅ **MQTT 主题：** 包含租户/命名空间以进行正确的命名空间划分
5. ✅ **消息历史：** MQTT 忽略 `initial_position` 参数（未来增强）
6. ✅ **客户端 ID：** MQTT 后端根据订阅名称自动生成

### 未来增强

**MQTT 消息历史：**
可以添加可选的持久层（例如，保留的消息、外部存储）
将允许支持 `initial_position='earliest'`
不适用于初始实现

